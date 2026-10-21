#include "beryllium_fdt.h"

#define MAX_DEPTH 64
#define MAX_BLOB (2u * 1024 * 1024)
struct props {
    const unsigned char *reg;
    uint32_t reglen, width, height, stride, phandle, region;
    unsigned parent_ac, parent_sc, ac, sc;
    int chosen, reserved, simple, format, device, disabled;
};
struct region { uint32_t id; uint64_t base, size; };

static uint32_t be(const unsigned char *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 |
           (uint32_t)p[2] << 8 | p[3];
}
static int eq(const unsigned char *s, size_t n, const char *v)
{
    size_t i = 0;
    while (i < n && s[i] && v[i] && s[i] == (unsigned char)v[i]) i++;
    return i < n && s[i] == 0 && v[i] == 0;
}
static int member(const unsigned char *s, size_t n, const char *v)
{
    size_t i = 0;
    if (!n || s[n - 1]) return 0;
    while (i < n) {
        if (eq(s + i, n - i, v)) return 1;
        while (i < n && s[i]) i++;
        i++;
    }
    return 0;
}
static int regvalue(const struct props *p, uint64_t *base, uint64_t *size)
{
    unsigned a = p->parent_ac, s = p->parent_sc;
    if (!p->reg || a < 1 || a > 2 || s < 1 || s > 2 ||
        p->reglen != 4 * (a + s)) return 0;
    *base = be(p->reg);
    if (a == 2) *base = (*base << 32) | be(p->reg + 4);
    *size = be(p->reg + 4 * a);
    if (s == 2) *size = (*size << 32) | be(p->reg + 4 * (a + 1));
    return 1;
}

int beryllium_framebuffer(const void *blob, size_t available,
                         struct beryllium_fb *out)
{
    const unsigned char *b = blob;
    struct props stack[MAX_DEPTH] = {0}, fb = {0};
    struct region regions[64];
    unsigned nr = 0, depth = 0, matches = 0;
    int device = 0, ended = 0, root_seen = 0;
    if (!b || !out || available < 40 || be(b) != 0xd00dfeed) return 0;
    uint32_t total = be(b + 4), so = be(b + 8), no = be(b + 12);
    uint32_t ns = be(b + 32), ss = be(b + 36);
    if (total > available || total > MAX_BLOB || total < 40 ||
        be(b + 20) < 17 || be(b + 24) > 17 || so < 40 || (so & 3) ||
        no < 40 || so > total || no > total || ss > total - so ||
        ns > total - no || (so < no + ns && no < so + ss)) return 0;
    size_t pos = so, end = so + ss;
    while (pos + 4 <= end) {
        uint32_t token = be(b + pos); pos += 4;
        if (token == 1) {
            if (depth == MAX_DEPTH || (!depth && root_seen)) return 0;
            size_t start = pos;
            while (pos < end && b[pos]) pos++;
            if (pos == end) return 0;
            struct props p = {0};
            p.ac = 2; p.sc = 1;
            if (depth) {
                p.parent_ac = stack[depth - 1].ac;
                p.parent_sc = stack[depth - 1].sc;
                p.chosen = stack[depth - 1].chosen;
                p.reserved = stack[depth - 1].reserved;
            } else {
                if (pos != start) return 0;
                root_seen = 1;
            }
            if (depth == 1) {
                p.chosen = eq(b + start, pos - start + 1, "chosen");
                p.reserved = eq(b + start, pos - start + 1, "reserved-memory");
            }
            stack[depth++] = p;
            pos = (pos + 4) & ~(size_t)3;
            if (pos > end) return 0;
        } else if (token == 2) {
            if (!depth) return 0;
            struct props p = stack[--depth];
            if (!depth) device = p.device;
            if (p.simple && p.chosen) { fb = p; matches++; }
            if (p.phandle && p.reserved) {
                uint64_t base, size;
                if (!regvalue(&p, &base, &size) || nr == 64) return 0;
                for (unsigned i = 0; i < nr; i++)
                    if (regions[i].id == p.phandle) return 0;
                regions[nr++] = (struct region){p.phandle, base, size};
            }
        } else if (token == 3) {
            if (!depth || pos + 8 > end) return 0;
            uint32_t len = be(b + pos), off = be(b + pos + 4); pos += 8;
            if (len > end - pos || off >= ns) return 0;
            const unsigned char *name = b + no + off, *v = b + pos;
            size_t n = ns - off, k = 0;
            while (k < n && name[k]) k++;
            if (k == n) return 0;
            struct props *p = &stack[depth - 1];
            if (eq(name, n, "compatible")) {
                p->simple = member(v, len, "simple-framebuffer");
                if (depth == 1) p->device = member(v, len, "xiaomi,beryllium");
            } else if (eq(name, n, "reg")) { p->reg = v; p->reglen = len; }
            else if (eq(name, n, "format")) p->format = eq(v, len, "a8r8g8b8");
            else if (eq(name, n, "status"))
                p->disabled = !eq(v, len, "okay") && !eq(v, len, "ok");
            else if (len == 4) {
                uint32_t x = be(v);
                if (eq(name, n, "#address-cells")) p->ac = x;
                else if (eq(name, n, "#size-cells")) p->sc = x;
                else if (eq(name, n, "width")) p->width = x;
                else if (eq(name, n, "height")) p->height = x;
                else if (eq(name, n, "stride")) p->stride = x;
                else if (eq(name, n, "phandle")) p->phandle = x;
                else if (eq(name, n, "memory-region")) p->region = x;
            }
            pos = (pos + len + 3) & ~(size_t)3;
            if (pos > end) return 0;
        } else if (token == 4) continue;
        else if (token == 9) { if (depth || !root_seen) return 0; ended = 1; break; }
        else return 0;
    }
    if (!ended || !device || matches != 1 || fb.disabled || !fb.format || fb.width != 1080 ||
        fb.height != 2246 || fb.stride != 4320) return 0;
    uint64_t base = 0, size = 0;
    if (fb.reg) {
        if (!regvalue(&fb, &base, &size)) return 0;
    } else {
        for (unsigned i = 0; i < nr; i++)
            if (regions[i].id == fb.region) { base = regions[i].base; size = regions[i].size; }
    }
    /* Restrict the initial probe to the published Poco splash reservation.
     * A different live layout requires review, never a guessed address. */
    if (base != 0x9d400000 || size < (uint64_t)4320 * 2246 ||
        size > 0x2400000) return 0;
    out->base = base; out->size = size;
    return 1;
}

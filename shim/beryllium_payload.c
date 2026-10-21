#include <stddef.h>
#include "loader.h"

#define PHYS_BASE 0x140000000ULL
#define MEMORY_SIZE 0x0ff00000ULL
#define PAGE 0x4000ULL

static int overlaps(uint64_t a, uint64_t an, uint64_t b, uint64_t bn)
{
    return an && bn && a < b + bn && b < a + an;
}
const char *beryllium_payload_check(const struct payload *p, uint64_t length,
                                   uint64_t initrd_start)
{
    if ((initrd_start & 7) || !p || length < sizeof(*p)) return "short payload header";
    for (unsigned i = 0; i < 8; i++)
        if (p->magic[i] != "SWEETXNU"[i]) return "wrong payload magic";
    if (p->version != 1 || !p->nsegs || p->nsegs > 64 ||
        p->nsegs > (length - sizeof(*p)) / sizeof(struct payload_seg))
        return "invalid segment table";
    uint64_t table = sizeof(*p) + p->nsegs * sizeof(struct payload_seg);
    if (p->phys_base != PHYS_BASE || p->mem_size != MEMORY_SIZE)
        return "wrong Poco RAM window";
    if (initrd_start > UINT64_MAX - length ||
        overlaps(initrd_start, length, PHYS_BASE, MEMORY_SIZE))
        return "initrd overlaps kernel RAM";
    if ((p->virt_base & 0x1ffffff) || p->virt_base < 0xffff000000000000ULL ||
        p->virt_base > UINT64_MAX - MEMORY_SIZE)
        return "invalid kernel virtual window";
    if (p->kernel_end < p->virt_base ||
        p->kernel_end - p->virt_base > MEMORY_SIZE || (p->kernel_end & (PAGE - 1)))
        return "invalid kernel end";
    if ((p->adt_off & 7) || p->adt_off < table || p->adt_off > length ||
        !p->adt_size || p->adt_size > 65536 ||
        ((p->adt_size + 7) & ~7ULL) > length - p->adt_off)
        return "invalid ADT range";
    uint64_t used = p->kernel_end - p->virt_base;
    if (p->adt_size > MEMORY_SIZE - used) return "ADT outside kernel RAM";
    uint64_t args = (used + p->adt_size + PAGE - 1) & ~(PAGE - 1);
    if (args > MEMORY_SIZE - PAGE) return "boot arguments outside kernel RAM";
    int terminated = 0, entry = 0;
    for (unsigned i = 0; i < BOOT_LINE_LENGTH; i++)
        if (!p->cmdline[i]) { terminated = 1; break; }
    if (!terminated) return "unterminated command line";
    if (p->entry_va & 3) return "unaligned kernel entry";
    for (unsigned i = 0; i < p->nsegs; i++) {
        const struct payload_seg *s = &p->segs[i];
        if (s->vmaddr < p->virt_base || !s->vmsize || (s->vmaddr & 7))
            return "invalid segment address";
        uint64_t offset = s->vmaddr - p->virt_base;
        if (offset > MEMORY_SIZE || s->vmsize > MEMORY_SIZE - offset ||
            s->vmaddr + s->vmsize > p->kernel_end)
            return "segment outside kernel RAM";
        if ((s->file_off & 7) || s->file_off < table || s->file_off > length ||
            s->file_size > length - s->file_off || s->file_size > s->vmsize ||
            s->file_size > UINT64_MAX - 7 ||
            ((s->file_size + 7) & ~7ULL) > length - s->file_off ||
            ((s->file_size + 7) & ~7ULL) > s->vmsize)
            return "invalid segment file range";
        if (overlaps(s->file_off, s->file_size, p->adt_off, p->adt_size))
            return "segment file overlaps ADT";
        for (unsigned j = 0; j < i; j++)
            if (overlaps(s->vmaddr, s->vmsize, p->segs[j].vmaddr, p->segs[j].vmsize))
                return "overlapping kernel segments";
        if (p->entry_va >= s->vmaddr && p->entry_va - s->vmaddr < s->file_size)
            entry = 1;
    }
    if (!entry) return "kernel entry outside loaded bytes";
    return NULL;
}

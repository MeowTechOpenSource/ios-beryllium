/* Stage zero only: no storage, PMIC, interrupt-controller or regulator access.
 * Device/geometry validation must succeed before touching the framebuffer. */
#include "console.h"
#include "beryllium_fdt.h"
#ifdef BERYLLIUM_XNU
#include "loader.h"
#endif

static int framebuffer_ready;
/* Debugger-visible outcome: 0 = rejected/incomplete, 1 = reached, 2 = fault. */
volatile uint32_t beryllium_probe_result;
/* Freestanding compiler support; no host runtime is linked. */
void *memset(void *dst, int value, size_t n)
{
    volatile unsigned char *d = dst;
    for (size_t i = 0; i < n; i++) d[i] = value;
    return dst;
}
void *memcpy(void *dst, const void *src, size_t n)
{
    volatile unsigned char *d = dst;
    const volatile unsigned char *s = src;
    for (size_t i = 0; i < n; i++) d[i] = s[i];
    return dst;
}
static void __attribute__((noreturn)) halt(void)
{
    for (;;) __asm__ volatile("wfe");
}
void secondary_main(uint64_t unused) { (void)unused; halt(); }
void exc_handler(uint64_t slot, uint64_t *regs)
{
    (void)regs;
    beryllium_probe_result = 2;
    if (framebuffer_ready) {
        con_str("FAULT", "diagnostic halted");
        con_hex("VECTOR", slot);
        uint64_t esr, far, elr;
        __asm__ volatile("mrs %0, esr_el1" : "=r"(esr));
        __asm__ volatile("mrs %0, far_el1" : "=r"(far));
        __asm__ volatile("mrs %0, elr_el1" : "=r"(elr));
        con_hex("ESR", esr); con_hex("FAR", far); con_hex("ELR", elr);
    }
    halt();
}
#ifdef BERYLLIUM_RAM_PROBE
/* Selected only after host validation of this phone's live memory map.
 * Touch two words at each sample, then restore them before continuing.
 * This does not prove the entire window is free of firmware protections. */
static int probe_ram(void)
{
    for (unsigned i = 0; i < 5; i++) {
        uint64_t address = i == 4 ? 0x14fffc000ULL : 0x140000000ULL + (uint64_t)i * 0x4000000;
        volatile uint64_t *p = (volatile uint64_t *)(uintptr_t)address;
        con_hex("RAM TEST", address);
        uint64_t a = p[0], b = p[1];
        p[0] = 0x55aa33cccc33aa55ULL;
        p[1] = 0xaa55cc3333cc55aaULL;
        __asm__ volatile("dsb sy" ::: "memory");
        int ok = p[0] == 0x55aa33cccc33aa55ULL && p[1] == 0xaa55cc3333cc55aaULL;
        p[0] = a; p[1] = b;
        __asm__ volatile("dsb sy" ::: "memory");
        ok = ok && p[0] == a && p[1] == b;
        con_str("RAM", ok ? "sample restored OK" : "sample failed");
        if (!ok) return 0;
    }
    return 1;
}
#endif
void shim_main(uint64_t dtb)
{
    struct beryllium_fb fb;
    /* ABL supplies a mapped FDT pointer in x0. The parser limits accesses to
     * the declared blob and rejects totals above 2 MiB. */
#ifdef BERYLLIUM_EARLY_MARKER
    /* Opt-in test for the already identified physical phone only. The splash
     * reservation was read from its live FDT and its panel mode from DRM.
     * This diagnostic intentionally draws before profile validation so a
     * rejection is observable. The default probe retains its no-write guard. */
    con_fb = (volatile uint32_t *)(uintptr_t)0x9d400000;
    framebuffer_ready = 1;
    con_clear(RED);
    con_str("ENTRY", "Poco CPU reached C");
    con_hex("DTB", dtb);
#endif
    if (!beryllium_framebuffer((const void *)dtb, 2 * 1024 * 1024, &fb)) {
#ifdef BERYLLIUM_EARLY_MARKER
        con_str("FDT", "profile rejected");
#endif
        halt();
    }
    con_fb = (volatile uint32_t *)(uintptr_t)fb.base;
    framebuffer_ready = 1;
    con_clear(BLUE);
    con_str("TARGET", "Poco F1 / beryllium");
    con_str("STAGE", "CPU and display probe");
    con_str("STORAGE", "not accessed");
    con_hex("FB", fb.base);
    uint64_t mpidr, mmfr0, freq, el;
    __asm__ volatile("mrs %0, mpidr_el1" : "=r"(mpidr));
    __asm__ volatile("mrs %0, id_aa64mmfr0_el1" : "=r"(mmfr0));
    __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(freq));
    __asm__ volatile("mrs %0, CurrentEL" : "=r"(el));
    con_hex("MPIDR", mpidr); con_hex("MMFR0", mmfr0);
    con_hex("CNTFRQ", freq); con_hex("EL", el >> 2);
#ifdef BERYLLIUM_RAM_PROBE
    if (!probe_ram()) { beryllium_probe_result = 3; halt(); }
    con_str("RAM", "five samples passed");
#endif
    con_str("RESULT", "diagnostic reached");
    con_str("NEXT", "XNU not started yet");
    beryllium_probe_result = 1;
#ifdef BERYLLIUM_XNU
    con_str("XNU", "validating payload");
    const char *why = loader_boot(dtb);
    con_str("LOADER", why);
#endif
    halt();
}

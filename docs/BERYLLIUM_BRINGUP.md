# Poco F1 / beryllium bring-up

This target is a port in progress. **iOS/XNU has not booted on a Poco F1 in this checkout.** The upstream sweet kernel and boot image are not compatible by default.

## Stage zero implementation

`shim/beryllium_probe.c` uses the upstream arm64 entry and text renderer, but does not call the sweet loader or its hardware probes. It reports CPU registers and draws a diagnostic screen only after the supplied live FDT validates. It does not invoke storage, PMIC, RPMh, GIC or PSCI operations. It halts afterward; it does not boot XNU.

The bounded parser in `shim/beryllium_fdt.c` requires:

- Root compatibility containing `xiaomi,beryllium`.
- Exactly one enabled `simple-framebuffer` below `/chosen`.
- `a8r8g8b8`, 1080 × 2246, stride 4320.
- An explicit `reg`, or a resolvable `memory-region` phandle into `/reserved-memory`.
- A region starting at 0x9d400000, large enough for the screen and no larger than the published 0x2400000 splash reservation.

The last restriction is deliberate: a different live layout requires investigation before framebuffer writes. An absent or different simple-framebuffer node produces a silent halt, not an address fallback. The parser assumes a readable FDT pointer supplied by the bootloader; it is not a protected-memory validator. No actual phone DTB has been collected yet.

Hardware references are upstream Linux `sdm845-xiaomi-beryllium-common.dtsi`, `sdm845-xiaomi-beryllium-tianma.dts` and `sdm845-xiaomi-beryllium-ebbg.dts`. They identify Novatek and FocalTech touch variants; the upstream sweet Goodix driver cannot be assumed to work.

## Build and verification

Use a Python environment containing `ziglang==0.17.0`:

```
python tools/build-beryllium-probe.py
python tools/test-beryllium-fdt.py
```

Outputs are ignored under `shim/out/beryllium-probe/`: `probe.elf` and `Image`. The build checks the Linux arm64 header and pads to its image size, including BSS/stacks. Explicit `_head` entry and disabled section GC retain the Linux Image header with this linker.

The C parser tests exercise direct and indirect framebuffer addresses, wrong hardware/format/geometry, disabled/duplicate framebuffers, every truncation of a valid blob, and malformed header ranges. They compile the real parser on the host with undefined-behavior sanitization.

An optional actual ARM64 execution smoke test requires `unicorn==2.1.4`:

```
python tools/test-beryllium-probe.py
```

It loads the compiled Image at two different addresses and supplies synthetic valid/wrong-device FDTs. Only image RAM, FDT RAM and the display reservation are mapped, so other MMIO accesses fail. Passing is emulator evidence only, not hardware validation. On this macOS host the emulator's initialization faults inside the sandbox, so it must be run outside it.

## Before hardware boot

1. Establish USB enumeration and fastboot access. The current computer has repeatedly seen only the USB hub; there is no verified Poco device connection.
2. Read product/unlock variables. User reports unlocked; this has not been independently verified.
3. Obtain the actual boot header and live DTB, preserving per-device backups.
4. Review the entry environment and live framebuffer metadata; package a temporary boot image using the phone's own layout.
5. Run the diagnostic on-device and capture the displayed results.
6. Port XNU memory/interrupt/CPU/storage/input support; only then attempt userland.

No Android boot image is packaged yet. There are no automated fastboot or flashing commands in these tools. Upstream userdata installation is destructive; upstream author approvals are not approvals for this Poco. No user data has been erased or written.

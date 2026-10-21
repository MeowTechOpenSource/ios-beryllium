# Poco F1 / beryllium bring-up

## Hardware milestone, 21 October 2026

- Authorized ADB identified beryllium / SDM845. Android's locked/green properties were misleading: fastboot getvar unlocked and oem device-info both confirmed unlocked and critical-unlocked.
- Official TWRP 3.7.0_9-0 was checksum-verified and booted with `fastboot boot` (temporary, not flashed). Root ADB and the visible TWRP screen were verified. Android's installed-recovery reboot had only returned to Android.
- Boot, recovery, DTBO, VBMeta, persist, modemst1, modemst2, fsg and fsc backups were read, checked against block-device sizes and hashed under ignored backup/poco-f1/. A dd transfer initially included its remote status in stdout and was rejected by the exact-size check; it was replaced with a clean cat transfer. All saved partition images passed exact-size checks.
- Recovery automatically mounted cache and userdata read/write. Both were then unmounted successfully. No flash, erase or explicit partition-write command was issued, but this does not imply recovery made no automatic filesystem writes before unmounting.
- Actual recovery FDT: Beryllium MP v2.1, Qualcomm SoC ID 321 / revision 0x20001, board ID 69/0. Tianma NT36672A display selected in bootargs; active DRM mode 1080x2246 at 60 Hz. Splash reservation 0x9d400000 / 0x2400000. No simple-framebuffer node exists.
- The C parser now supports that exact downstream board/model/SoC/panel/reservation tuple as well as the earlier mainline simple-framebuffer path. Unrelated dynamic reserved-memory nodes need not have a reg property.
- Six parser test methods pass. Four ARM64 execution methods pass, including the actual private captured FDT, synthetic downstream layout, two relocation addresses, wrong-device rejection and explicit completion markers. Final emulator run: 38.994 seconds. These remain emulator checks.
- tools/pack-beryllium-probe.py generated a 569344-byte Android boot-v1 candidate using the backed-up boot layout, compiled Image, captured FDT and an empty cpio ramdisk. Round-trip extraction, input bytes and SHA1 header digest checked. Candidate SHA256: 24f502e953bb14aa5285f5e0f9206a34fbc90a1f8bd132ef06dfa5039be6295a.
- The custom diagnostic has NOT been sent: ADB and the USB 2.1 hub disappeared before adb reboot bootloader could run. Last inventory sees only the USB 3.1 hub. User reports the phone is still on the TWRP screen. Reconnect the previously working data path, then RAM-boot the candidate and obtain screen evidence before claiming any custom hardware boot.

This target is a port in progress. **iOS/XNU has not booted on a Poco F1 in this checkout.** The upstream sweet kernel and boot image are not compatible by default.

## First custom hardware attempt

The original diagnostic candidate was sent with `fastboot boot` after rechecking product and unlock state. The bootloader reported successful transfer and boot. The user saw the POCO logo or a black screen, so there is no evidence of diagnostic completion on hardware. XNU/iOS remain unbooted.

An explicit `--early-marker` build now draws a red entry screen using this phone's verified splash reservation before validating its FDT, and shows the rejection or fault path. Accepted FDTs turn the screen blue. This mode is for this identified physical unit only; it must not be used to discover an unknown device's framebuffer. The default build keeps its guard. Early outputs are under `shim/out/beryllium-probe-early/`; the new image has not yet been sent. The next step is a working fastboot data connection and screen evidence from the early probe.

## Confirmed custom-code hardware milestone

The early-marker gzip candidate was RAM-booted after renewed ADB connectivity and direct product/unlock verification. The user reports the blue diagnostic screen on the Poco. This confirms execution and rendering of the custom diagnostic on hardware. Exact CPU register and RESULT text is still requested. XNU and iOS have not started. Both early-marker code and gzip packaging changed since the first unsuccessful screen observation, so the cause is not isolated to compression alone.

## Stage zero implementation

`shim/beryllium_probe.c` uses the upstream arm64 entry and text renderer, but does not call the sweet loader or its hardware probes. It reports CPU registers and draws a diagnostic screen only after the supplied live FDT validates. It does not invoke storage, PMIC, RPMh, GIC or PSCI operations. It halts afterward; it does not boot XNU.

The bounded parser in `shim/beryllium_fdt.c` requires:

- Root compatibility containing `xiaomi,beryllium`.
- Exactly one enabled `simple-framebuffer` below `/chosen`.
- `a8r8g8b8`, 1080 × 2246, stride 4320.
- An explicit `reg`, or a resolvable `memory-region` phandle into `/reserved-memory`.
- A region starting at 0x9d400000, large enough for the screen and no larger than the published 0x2400000 splash reservation.

The last restriction is deliberate: a different live layout requires investigation before framebuffer writes. An absent or different simple-framebuffer node produces a silent halt, not an address fallback. The parser assumes a readable FDT pointer supplied by the bootloader; it is not a protected-memory validator. The actual recovery FDT has now been collected privately; see the hardware milestone above.

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

A local temporary diagnostic boot image is now packaged; it has not been booted on hardware. There are no automated fastboot or flashing commands in these tools. Upstream userdata installation is destructive; upstream author approvals are not approvals for this Poco. No erase or explicit partition-write command has been issued; recovery automatic mounts are documented above.

## UniXNU reference

UniXNU source at 97de9e715e06d77b8ebe7b80f6e556ee7ab9a7e9 uses a UEFI/GOP-based loader chain. Its public supported-device list does not provide a Poco F1 port. Porting the whole stack would require Poco-specific UEFI, platform and driver work.

The immediately relevant finding is packaging: scripts/unixnu/bootimg.py uses gzip(payload)+DTB with round-trip checks. The actual Poco Android boot image and working temporary TWRP also contain gzip kernels; the first custom probe used a raw Image. That difference is not proven causal. The packer now offers --gzip-kernel to change compression while preserving the backed-up phone's header-v1 offsets. The new boot-gzip.img candidate has not been sent. Compressed bytes, uncompressed Image, appended FDT and Android header digest have been verified.

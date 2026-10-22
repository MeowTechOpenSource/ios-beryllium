# Poco F1 / beryllium bring-up

Current component status and source references: [ports/beryllium/STATUS.md](../ports/beryllium/STATUS.md).
Detailed chronological hardware evidence and active handoff: [NOTES.md](../NOTES.md).

## Confirmed milestones

- Unlocked physical Poco identified through fastboot; critical partitions privately backed up.
- Verified live MP v2.1 FDT, Tianma 1080×2246 framebuffer, EL1 entry, 19.2 MHz counter, 16K page support.
- Custom diagnostic and restored RAM samples execute on the phone.
- XNU 0083 reaches our static PID 1 and timed heartbeats on the phone.
- Read-only UFS root attempt reports an HFS signature failure on Android F2FS (screen report).
- Matching QEMU virt profile reaches static PID 1 and repeated heartbeats offline.
- Apple launchd, iOS UI, real Wi-Fi/audio, accelerated graphics and physical touch have not been demonstrated.

## Device-free regression

```
python3 tools/mkberylliumqemuadt.py shim/out/beryllium-xnu/qemu.adt
python3 tools/mkpayload.py xnu/out-beryllium-0083/kernel.development.sweet shim/out/beryllium-xnu/qemu.adt shim/out/beryllium-xnu/payload-qemu.bin --ramdisk shim/out/beryllium-xnu/poco-init --cmdline 'debug=0xc serial=3 cpus=1 rd=md0 keepsyms=1 sweettouch=0 sweetkeys=0 sweetusb=0'
python3 tools/qemu-sweet.py shim/out/beryllium-xnu/payload-qemu.bin research/qemu-beryllium --profile beryllium --secs 60 --kernel xnu/out-beryllium-0083/kernel.development.sweet --fail-on-panic --expect-text 'POCO test userspace: init running as PID 1' --expect-text 'POCO test init: still alive'
```

Use the exact matching kernel artifact; 0082 fixes early framebuffer placement,
0083 fixes Kryo385 CPU-driver matching. QEMU ADT substitutes virt's GIC/timer and
must never be used on the phone. The phone ADT contains actual hardware resources;
it cannot be passed unchanged to QEMU.

The QEMU wrapper supports macOS symbol extraction with `xcrun nm`, places its
monitor socket under a short temporary path, and tags results as emulator evidence.
Framebuffer text is circular. `no_panic_observed` alone does not prove userspace;
check for the explicit PID1/heartbeat messages.

## Graphics and transport work

Poco overlay 0084 contains a boot-geometry-based HID viewport and opt-in
`beryllium_fbtest=1` CPU-rendered bars with a white one-pixel border. This mutes
normal console drawing; omit the flag to test text or PID1. Touch hardware remains
disabled. No Adreno acceleration is implied.

Portable HTC/APR codecs and display helpers are in `ports/beryllium/support/`.
Their sanitizer tests run through `beryllium-support` CI. They are not yet bound
to Wi-Fi firmware transport or audio hardware.

## Installation state

The user explicitly authorized userdata formatting/writes on 2026-10-22. Prepared
local HFS image ownership and read-only filesystem checks pass. The first flash
attempt failed on the host (`Failed reading from userdata`) before a reported
send/write. No completed flash exists. The user then requested offline work because
the phone is unavailable. Keep hardware operations stopped until it returns.

Private FDTs, partition backups, Apple firmware, images, serials and credentials
remain outside git. Upstream historical permissions are not used as this user's
authorization. Keep bootloaders, recovery, modem and persist intact.

With the 0084 kernel and `beryllium_fbtest=1` in the payload command line, run the
wrapper with `--expect-pattern` (without text expectations) to check band colors
and the panel border directly. Missing expectations return exit code 4.

## Prepared sparse installation image (no phone required)

`tools/mkandroidsparse.py` streams RAW/FILL chunks and verifies the expanded SHA256.
It never emits undefined DONT_CARE regions and never invokes fastboot. This avoids
loading the raw 16GiB image in memory during conversion. The prepared sparse image
has the same expanded SHA256 as the validated HFS image. AOSP's independent
`simg_dump.py` accepts its 4,194,304 output blocks and 28,209 chunks.

The [AOSP AVB-footer copy path](https://android.googlesource.com/platform/system/core/+/refs/heads/main/fastboot/fastboot.cpp)
reads a non-sparse image into a string and produces the observed error text when
that fails; it skips that path for sparse files. This explains a likely host-side
cause, but a successful future device flash is still needed to confirm resolution.
The sparse format is checked against [AOSP sparse_format.h](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/sparse_format.h).

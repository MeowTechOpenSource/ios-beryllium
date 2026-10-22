# ios-beryllium

XNU / iOS bring-up for the **Xiaomi Poco F1 (`beryllium`, Snapdragon 845 / Kryo 385)**,
derived from [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet).

**The physical Poco runs XNU and our static diagnostic PID 1, including timed
heartbeats. Apple's launchd, SpringBoard and an interactive iOS UI have not yet
been demonstrated.** Upstream Redmi screenshots and milestones are not Poco results.

## What works on this target

| Component | Verified state |
| --- | --- |
| Boot | Temporary boot through the unlocked bootloader; EL1 entry and 16K-page support verified. |
| CPU / memory | Kryo 385 driver matching; single-CPU diagnostic userspace on hardware. Five RAM samples restored successfully in the approved 256 MiB window. |
| Display | Physical boot console at 1080×2246, stride 4320, framebuffer `0x9d400000`. Updated CPU-rendered bars pass every-pixel checks in QEMU; that update awaits hardware testing. |
| UFS | Read-only root probe reached an unknown-volume-signature report on existing Android storage. Prepared iOS filesystem flashed to userdata; XNU mount/launchd result pending. |
| Wi-Fi / audio | Tested portable HTC/APR protocol foundations; hardware transport and functional drivers remain unfinished. |
| GPU | CPU framebuffer only; no Adreno 630 acceleration. |
| Touch / keys / USB | Physical XNU drivers disabled. Android/recovery USB support does not establish XNU USB support. |
| Battery | Static fallback; no genuine gauge readings. |
| iOS apps / UI | Not reached. The diagnostic PID 1 is our own test program. |

See the [device-specific support matrix](ports/beryllium/STATUS.md) for evidence,
[bring-up guide](docs/BERYLLIUM_BRINGUP.md) for commands, and
[working notes](NOTES.md) for the chronological handoff.

## Build and offline checks

The `xnu` GitHub Actions workflow defaults to `hardware_target=beryllium` and applies
`ports/beryllium/xnu/` after the shared XNU patches. Use the published fork's
`poco-bringup` branch. The shared XNU machine configuration is still `SWEET`, so its
artifact is named `kernel.development.sweet`; select the beryllium hardware target
rather than inferring hardware from that filename.

```sh
python3 tools/test-beryllium-fdt.py
python3 tools/test-beryllium-payload.py
python3 tools/test-androidsparse.py
python3 tools/test-qemu-pattern.py
clang -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined tools/test-beryllium-display.c -o /tmp/beryllium-display
/tmp/beryllium-display
clang -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined ports/beryllium/support/transport.c tools/test-beryllium-transport.c -o /tmp/beryllium-transport
/tmp/beryllium-transport
```

`tools/beryllium-init.S` is the Poco diagnostic userspace source; `tools/mkinit.py`
wraps its assembled object into a static signed Mach-O. The
[bring-up guide](docs/BERYLLIUM_BRINGUP.md) describes making an emulator payload and
checking explicit PID 1 / heartbeat messages with `tools/qemu-beryllium.py`.
That tool defaults to Poco geometry. `tools/qemu-sweet.py` remains a compatibility
entry point with the original Redmi profile.

QEMU `virt` substitutes its own interrupt controller and timer. It is **not an
SDM845 emulator** and cannot establish Poco Wi-Fi, sound, touch or GPU support.
Never boot its generated device tree on the phone.

## Names inherited from upstream

The Poco target uses `BERYLLIUM` diagnostic messages for its adapted/reused CPU,
early console, platform, framebuffer, UFS and common userspace-support components
through overlay 0085. This is a source change; earlier kernel builds and screenshots
retain their original messages until rebuilt.

Internal `Sweet*` classes, `SWEET` compiler flags, `sweet_*` symbols, existing
`sweetfb_*` / peripheral boot arguments, device-tree compatibility names and the
8-byte `SWEETXNU` payload magic remain shared compatibility interfaces. Changing
those independently would break matching or existing payloads. Unported Redmi
hardware drivers and historical upstream patches retain their original names;
a renamed log does not certify new hardware functionality.

## Installation state

The verified 16 GiB iOS filesystem sparse image was flashed to the Poco's userdata
on 2026-10-22: all 15 sends/writes reported `OKAY`, and fastboot exited successfully.
After reconnection, temporary kernel transfer and bootloader handoff succeeded; a successful flash does not establish
an XNU filesystem mount, Apple launchd or iOS UI. GPT, bootloaders, recovery, modem,
persist and private backups were preserved.

Device trees captured from the phone, backups, serials, credentials and Apple
firmware/filesystem images are excluded from this repository. iOS is Apple's
software and is not distributed here.

## Credits

Poco adaptation builds on [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet),
Apple's open-source XNU, IOHIDFamily, libpthread and HFS releases,
[BearSSL](https://bearssl.org),
[blacktop/darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build),
[ipsw](https://github.com/blacktop/ipsw), Qualcomm/Xiaomi's published Linux sources,
and [OrangeFox Recovery](https://orangefox.download).

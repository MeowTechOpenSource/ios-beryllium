# Poco F1 / beryllium port status

Target: SDM845 / Kryo 385, captured MP v2.1 board, Tianma NT36672A panel.
This is an XNU/iOS port. Linux driver support is a reference, not an XNU driver.

| Component | Actual Poco evidence | Offline implementation / remaining work |
|---|---|---|
| Boot / CPU | Custom shim and XNU execute at EL1; static PID 1 prints heartbeats | Single CPU; 16K pages. SMP beyond boot CPU untested on Poco. |
| Timer / scheduling | PID 1 wakes repeatedly from select | QEMU also reaches PID 1 with repeated wakeups. |
| RAM | Five samples restored successfully in approved 256 MiB window | Not an exhaustive test. Kernel currently has 255 MiB plus 1 MiB panic reserve. |
| Display console | Actual 1080×2246 console at 0x9d400000 | Poco early-console overlay and matching QEMU framebuffer. |
| IOSurface / display service | AppleCLCD and IOCoreSurfaceRoot registration observed | Existing CPU compositor; no hardware proof of iOS frames or swaps. Opt-in test pattern and geometry correction in 0084. |
| Adreno 630 acceleration | None | No XNU GPU driver. Requires GMU, firmware/secure setup, power, IOMMU, command submission and an iOS graphics frontend. |
| Wi-Fi WCN3990 | None under XNU | HTC RX envelope and READY→CONNECT_SERVICE negotiation tested with wire fixtures. No SNOC/CE DMA, QMI/firmware boot, WMI/HTT, association or iOS network interface yet. |
| Audio WCD9340 / ADSP | None under XNU | Bounded APR encode/decode tested. No GLINK/rpmsg, ADSP boot, AFE/ASM routing, SLIMbus codec or iOS audio service yet. Speaker amplifier/routing still needs target verification. |
| UFS | Read-only root attempt reaches HFS signature failure on existing Android filesystem, per screen report | Target host map supplied; verified sparse filesystem flashed to userdata (15 chunks, fastboot exit 0); iOS HFS boot unconfirmed. |
| Touch / physical keys | None under XNU | HID services register; upstream Redmi hardware drivers disabled. Poco geometry correction does not port its touch controller. |
| Battery | No genuine gauge reading | Existing static 100% fallback is a placeholder. |
| USB | Android ADB / temporary TWRP / fastboot verified previously | XNU USB driver disabled; QEMU virtual devices do not establish Poco USB support. |
| Apple iOS userland / SpringBoard | Not reached | Apple startup reaches launchd_cache_loader PID 22 after the platform-argument fix, then exits with Unable to find AMFI. Next cache-loader development argument prepared; no UI yet. |

## Emulator scope

QEMU `virt` uses an emulated GIC and architected timer, and RAM for the framebuffer.
The Poco kernel's display dimensions, CPU driver match and high-memory layout are
selected, but the CPU model remains Cortex-A76. It is not an SDM845/WCN3990/WCD9340/
Adreno hardware model. No Wi-Fi, sound or GPU claim follows from a QEMU pass.

## References pinned for implementation

- [Poco board, Linux v6.12](https://github.com/torvalds/linux/blob/v6.12/arch/arm64/boot/dts/qcom/sdm845-xiaomi-beryllium-common.dtsi): board IDs, WCD9340 SLIM playback/capture, ADSP and a630_zap firmware, Wi-Fi supplies.
- [HTC wire layout, Linux v6.12](https://github.com/torvalds/linux/blob/v6.12/drivers/net/wireless/ath/ath10k/htc.h): 8-byte HTC header, 4-byte trailer-record header, endpoint bounds.
- [APR wire layout, Linux v6.12](https://github.com/torvalds/linux/blob/v6.12/include/linux/soc/qcom/apr.h): 20-byte v0 header, message type, packet size, token and opcode.
- [WCN3990 Poco board-file submission](https://lists.infradead.org/pipermail/ath10k/2023-December/015068.html): target calibration variant; do not substitute another phone's calibration.

## Next functional milestones

1. Completed offline: 0084c framebuffer pattern passes whole-frame pixel/border checks; normal mode passes explicit PID 1/heartbeat regression. Hardware confirmation remains pending.
2. Boot Apple launchd from HFS in an emulator with a suitable block backend or compact RAM root.
3. Wi-Fi: implement SMEM/GLINK + QMI and SNOC CE rings before WMI/HTT and network service integration.
4. Audio: implement ADSP remoteproc/GLINK and bind the tested APR completion path before PCM buffers, AFE/ASM/codec routing and iOS frontend.
5. GPU: first obtain validated GMU/power/IOMMU/firmware state; retain the CPU display path until actual command submission is proven.

No fake Wi-Fi, audio or GPU service is published as working hardware.

## Verified offline results (2026-10-22)

- Kernel [CI 39720237145](https://github.com/MeowTechOpenSource/ios-beryllium/actions/runs/39720237145) passes, source 852e6316c21ece45ba5390b700a9aaa6b51f823e, target beryllium. SHA256 `20a0d85541dc3175e146a5daad2aff9e10b7aa41bac3dad7a7f9dba9edb0b55c`.
- QEMU 45-second graphics run: all 2,425,680 pixels match the expected color bars and border at 1080×2246 (`pattern_mismatched_pixels=0`). Use `beryllium_fbtest=1 -noprogress` to suppress text and boot-progress overlays. The first diagnostic caught console overwrites; the final kernel suppresses both console paths in explicit pattern mode, retaining panic output.
- QEMU 60-second normal run: explicit PID 1 and repeated heartbeat expectations pass, zero undecodable glyphs, no visible panic. Pattern mode is disabled for this run.
- Portable [CI 39720470788](https://github.com/MeowTechOpenSource/ios-beryllium/actions/runs/39720470788) passes display, HTC/APR, loader-guard and sparse-format tests. HTC control includes READY/service negotiation tests; parser suite includes 20,000 malformed inputs under ASan/UBSan. ARM64 freestanding compilation also passes locally.
- The prepared sparse filesystem expands to the validated 16GiB raw-image SHA256 and is independently accepted by AOSP simg_dump. On the phone's return, the verified sparse image flashed successfully: 15 chunks, exit 0. After reconnection, temporary bootloader handoff succeeded; screen evidence for XNU mount/Apple userspace is pending.

Source naming: overlay 0085 uses BERYLLIUM diagnostic labels for adapted/reused components. The verified kernel runs above predate this overlay; renaming does not add peripheral support.

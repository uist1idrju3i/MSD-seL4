# seL4 の検証済み構成と証明の範囲

[索引へ戻る](../README.md)

## 一次資料から確かめたこと

`vendor/seL4/configs/ARM_bcm2837_verified.cmake` は `configs/include/ARM_verified_include.cmake` を読み込み、`KernelPlatform=bcm2837` を設定します。主な値は次のとおりです。

| CMake の変数 | 値 |
|---|---|
| `KernelSel4Arch` | `aarch32` |
| `KernelVerificationBuild` | `ON` |
| `KernelBinaryVerificationBuild` | `ON` |
| `KernelAArch32FPUEnableContextSwitch` | `OFF` |
| `KernelMaxNumNodes` | `1` |
| `KernelOptimisation` | `-O2` |
| `KernelOptimisationCloneFunctions` | `OFF` |
| `KernelFastpath` | `ON` |
| `KernelPrinting` | `OFF` |
| `KernelIPCBufferLocation` | `threadID_register` |
| `KernelRetypeFanOutLimit` | `256` |
| `KernelNumDomains` | `16` |
| `KernelBenchmarks` | `none` |
| `KernelDangerousCodeInjection` | `OFF` |

`src/plat/bcm2837/config.cmake` は、Raspberry Pi 3 が歴史的な理由で AArch32 を既定にすることを記しています。CPU は Cortex-A53、timer は ARM generic timer（19.2 MHz）、割り込み controller は `bcm2836-armctrl-ic` です（GIC はありません）。`src/plat/bcm2837/overlay-rpi3.dts` は、kernel が使う device を mini UART（`serial1`）、2 つの割り込み controller、timer に限り、RAM を既定で 128 MiB とし、先頭の 4 KiB を予約します。

公式の [Verified Configurations](https://docs.sel4.systems/projects/sel4/verified-configurations.html)（2026-11-11 取得）は、AArch32（EL1、FPU なし、hypervisor なし）の対象に Raspberry Pi 3-b を挙げ、次の性質を検証済みとしています。

- C レベルの機能正当性（fastpath を含む）
- 完全性と可用性（アクセス制御）
- 機密性（情報フロー）
- バイナリ正当性（C レベルの検証がある関数）
- capDL によるユーザーレベルのシステム初期化（root task）のモデルレベルの機能正当性

同じページによると、どの検証済み構成も SMMU/IOMMU、debug・profiling・printing、kernel の起動処理を対象にしていません。MCS の証明（`ARM_MCS`、`AARCH64_MCS`）は進行中です。AArch32 の hypervisor 構成（`ARM_HYP`）の対象は Jetson TK1 だけで、証明は C レベルの機能正当性だけです。

AArch64 の検証済み構成（`configs/include/AARCH64_verified_include.cmake`）は hypervisor（EL2）が前提で、対象に `bcm2711`・`bcm2712` はありますが `bcm2837` はありません。

[What the Proofs Assume](https://sel4.systems/Verification/assumptions.html) によると、証明はハードウェアが正しく改ざんされていないこと、cache・TLB の扱い、boot code と一部のアセンブリ・機械語の正しさを前提にします。

[Rpi3 のページ](https://docs.sel4.systems/Hardware/Rpi3.html) は、rpi3 の移植を「experimental port, not guaranteed to work」とし、Raspberry Pi 4B を勧めています。仮想化と SMMU には対応しておらず、Proof configs は `ARM` です。

## 判断（推測を含む）

- CardputerZero で証明を最大限に生かせる構成は `ARM_bcm2837_verified` だけです。この構成を既定にしました（D1）。
- 単一コアのため、BCM2837 の残り 3 コアは使いません。
- FPU の context switch がないため、userland は浮動小数点を使わない設計にするか、FPU の扱いを別に決める必要があります。音声、暗号、画像の処理の性能に影響する可能性があります（未確認）。
- hypervisor 構成を使えないため、Linux を VM として動かしてその driver を借りる方式は取りません。driver はすべてユーザー空間に自作します。
- CardputerZero の RAM は 512 MB ですが、upstream の overlay は 128 MiB です。firmware の設定、DTS、elfloader の扱いを、vendor を編集せずに合わせる方法を調べる必要があります（未確認）。

## 未確認

- 実機（CardputerZero）と QEMU で、seL4 17.0.0 の AArch32 kernel が起動するか。
- capDL loader と userland の基盤を、AArch32 の rpi3 で使えるか（[userland-frameworks.md](userland-frameworks.md)）。

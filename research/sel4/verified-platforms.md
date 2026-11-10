# 形式検証済みのアーキテクチャと CPU・SoC の一覧

seL4 kernel の証明が、どのアーキテクチャのどの platform（SoC・CPU）に対してあるかをまとめます。CardputerZero（BCM2837、Cortex-A53）を AArch32 の検証済み構成で使う判断（D1）の根拠と、ほかの選択肢の位置を示すための資料です。

## 一次資料

- `vendor/seL4`（tag `17.0.0`、`62e345c2`）の `configs/*_verified.cmake`、`configs/include/*_verified_include.cmake`、`src/plat/<platform>/config.cmake`。
- seL4 の文書のリポジトリ（`seL4/docs`、commit `97021d2f`、2026-11-03）の `projects/sel4/verified-configurations.md` と `Hardware/*.md` の front matter（`platform`、`soc`、`cpu`、`verification`、`Maintained`）。

表の CPU は、Arm では `src/plat/<platform>/config.cmake` の `KernelArmCortex*` から取りました。RISC-V と SoC の名前は `Hardware/*.md` の記載です。

## アーキテクチャごとの証明

| 構成の接頭辞 | アーキテクチャと特権 | FPU | hypervisor | 証明された性質 |
|---|---|---|---|---|
| `ARM` | ARMv7-A 32-bit（ARMv8-A の AArch32 を含む）、EL1 | なし | なし | C の機能正当性（fastpath を含む）、完全性と可用性（access control）、機密性（information flow）、バイナリ正当性（C で証明した関数）、capDL の初期化子の model での機能正当性 |
| `ARM_HYP` | ARMv7-A 32-bit、EL2 | なし | あり | C の機能正当性（fastpath を含む） |
| `AARCH64` | ARMv8-A 64-bit、EL2 | あり | あり | C の機能正当性（fastpath を含む）、完全性と可用性、機密性 |
| `RISCV64` | RISC-V 64-bit | なし（`KernelRiscvExtF`・`D` は OFF） | なし | C の機能正当性（fastpath を除く）、完全性と可用性、機密性 |
| `X64` | Intel x86-64 | あり | なし（VT-x なし） | C の機能正当性（fastpath を除く） |
| `*_MCS` | ARM、AARCH64、RISCV64 の MCS 版 | | | 証明は進行中で、まだ完了していない |

構成の include から読み取れる共通点です。

- すべての検証済み構成は `KernelMaxNumNodes 1`（single core）、`KernelPrinting OFF`、`KernelOptimisation -O2`、`KernelVerificationBuild ON` です。
- `KernelBinaryVerificationBuild ON` は `ARM`（`ARM_HYP` も同じ include を使う）と `RISCV64` にあり、`AARCH64` にはありません。文書のとおり、AArch64 のバイナリ正当性はまだありません。
- `AARCH64` は `KernelArmSMMU OFF`、`KernelAllowSMCCalls ON` です。
- どの構成も、SMMU・IOMMU、debug・profiling・printing、起動時の kernel の初期化（boot code）を証明の対象にしていません。

## platform の一覧（seL4 17.0.0）

### ARM（AArch32、EL1）

| 構成 | 機材 | SoC | CPU |
|---|---|---|---|
| `ARM_verified`（`imx6`） | Sabre Lite | NXP i.MX6 | Cortex-A9 |
| `ARM_am335x_verified` | BeagleBone Black / Blue | TI AM335x | Cortex-A8 |
| `ARM_bcm2837_verified` | Raspberry Pi 3-b（CardputerZero の CM0 と同じ SoC） | Broadcom BCM2837 | Cortex-A53（AArch32 で動かす） |
| `ARM_exynos5410_verified` | OdroidXU | Samsung Exynos5410 | Cortex-A15 |
| `ARM_exynos5422_verified` | OdroidXU4 | Samsung Exynos5422 | Cortex-A15 |
| `ARM_imx8mm_verified` | i.MX8M Mini EVK | NXP i.MX8M Mini | Cortex-A53（AArch32） |
| `ARM_omap3_verified` | BeagleBoard | TI OMAP3 | Cortex-A8 |
| `ARM_tk1_verified` | Jetson TK1 | NVIDIA Tegra K1 | Cortex-A15 |
| `ARM_zynq7000_verified` | Zynq-7000 ZC706 | AMD（Xilinx）Zynq-7000 | Cortex-A9 |
| `ARM_zynqmp_verified` | Zynq ZCU102 / ZCU106 | AMD（Xilinx）Zynq UltraScale+ MPSoC | Cortex-A53（AArch32） |
| `ARM_MCS_verified`（`imx6`、証明は進行中） | Sabre Lite | NXP i.MX6 | Cortex-A9 |

### ARM_HYP（AArch32、EL2）

| 構成 | 機材 | SoC | CPU |
|---|---|---|---|
| `ARM_HYP_verified`（`tk1`） | Jetson TK1、TK1-SOM | NVIDIA Tegra K1 | Cortex-A15 |
| `ARM_HYP_exynos5410_verified` | OdroidXU | Samsung Exynos5410 | Cortex-A15 |
| `ARM_HYP_exynos5_verified`（`exynos5422`） | OdroidXU4 | Samsung Exynos5422 | Cortex-A15 |

### AARCH64（EL2）

| 構成 | 機材 | SoC | CPU |
|---|---|---|---|
| `AARCH64_verified`（`tx2`） | Jetson TX2 | NVIDIA Tegra X2 | Cortex-A57（`KernelArmCortexA57`。SoC は Denver も持つ） |
| `AARCH64_bcm2711_verified` | Raspberry Pi 4B | Broadcom BCM2711 | Cortex-A72 |
| `AARCH64_bcm2712_verified` | Raspberry Pi 5B | Broadcom BCM2712 | Cortex-A76 |
| `AARCH64_imx8mm_verified` | i.MX8M Mini EVK | NXP i.MX8M Mini | Cortex-A53 |
| `AARCH64_imx8mq_verified` | i.MX8M Quad EVK（MCIMX8M-EVKB） | NXP i.MX8MQ | Cortex-A53 |
| `AARCH64_imx93_verified` | i.MX93 EVK | NXP i.MX93 | Cortex-A55 |
| `AARCH64_maaxboard_verified` | Avnet MaaXBoard | NXP i.MX8MQ | Cortex-A53 |
| `AARCH64_odroidc2_verified` | Odroid-C2 | Amlogic S905 | Cortex-A53 |
| `AARCH64_odroidc4_verified` | Odroid-C4 | Amlogic S905X3 | Cortex-A55 |
| `AARCH64_rockpro64_verified` | ROCKPro64 | Rockchip RK3399 | Cortex-A53（`KernelArmCortexA53`） |
| `AARCH64_stm32mp2_verified` | STM32MP25 EV1 | ST STM32MP25 | Cortex-A35 |
| `AARCH64_tqma_verified`（`tqma8xqp1gb`） | TQMa8XQP 1GB | NXP i.MX8X Quad Plus | Cortex-A35 |
| `AARCH64_tx1_verified` | Jetson TX1 | NVIDIA Tegra X1 | Cortex-A57 |
| `AARCH64_ultra96v2_verified` | Ultra96v2 | AMD（Xilinx）Zynq UltraScale+ MPSoC | Cortex-A53 |
| `AARCH64_zynqmp_verified` | Zynq ZCU102 / ZCU106 | AMD（Xilinx）Zynq UltraScale+ MPSoC | Cortex-A53 |
| `AARCH64_MCS_verified`（`tx2`、証明は進行中） | Jetson TX2 | NVIDIA Tegra X2 | Cortex-A57 |

### RISCV64

| 構成 | 機材 | SoC | CPU（hart） |
|---|---|---|---|
| `RISCV64_verified`（`hifive`） | HiFive Unleashed | SiFive Freedom U540 | U54-MC（E51） |
| `RISCV64_ariane_verified` | Ariane | （FPGA） | Ariane（CVA6） |
| `RISCV64_bananapi-f3_verified` | Banana Pi BPI-F3 | SpacemiT K1 | X60 |
| `RISCV64_cheshire_verified` | Cheshire | （FPGA） | Cheshire（CVA6 系） |
| `RISCV64_hifive-p550_verified` | HiFive Premier P550 | ESWIN EIC7700X | P550 |
| `RISCV64_polarfire_verified` | PolarFire Icicle Kit | Microchip PolarFire SoC FPGA | U54-MC（E51） |
| `RISCV64_rocketchip_verified` | Rocketchip | （FPGA） | Rocket |
| `RISCV64_rocketchip-zcu102_verified` | Rocketchip（ZCU102 上） | （FPGA） | Rocket |
| `RISCV64_star64_verified` | Pine64 Star64 | StarFive JH7110 | U74-MC（E24） |
| `RISCV64_MCS_verified`（`hifive`、証明は進行中） | HiFive Unleashed | SiFive Freedom U540 | U54-MC |

Cheshire の「CVA6 系」は、文書の CPU 欄（`Cheshire`）からの推測です。

### X64

| 構成 | 機材 | CPU |
|---|---|---|
| `X64_verified`（`pc99`、`x86_64`） | PC99 互換機 | Intel x86-64（VT-x なし） |

## 文書と 17.0.0 の構成の食い違い

`Hardware/*.md` の `verification` 欄は、次の platform を検証の対象としています。ただし、17.0.0 の `configs/` に対応する `*_verified.cmake` がありません。

| 文書の platform | `verification` 欄 | 17.0.0 の状態 |
|---|---|---|
| i.MX8M Plus（Cortex-A53） | `AARCH64` | `*_verified.cmake` なし |
| Rock3b（RK3568、Cortex-A55） | `AARCH64` | `src/plat/rk3568` はあるが、`*_verified.cmake` なし |
| HiKey（Kirin 620、Cortex-A53） | `AARCH64` | 保守されていない（`Maintained: false`） |
| Arndale（Exynos5、Cortex-A15） | `ARM_HYP` | 保守されていない |
| OdroidX（Exynos4412、Cortex-A9） | `ARM` | 保守されていない |

これらは、`seL4/l4v` の該当版で証明が通るかを確かめるまで「検証済み」と扱いません（未確認）。QEMU の `virt`、Spike、IA32、KZM（ARMv6）は `verification` が空で、検証の対象外です。

## CardputerZero への意味

- BCM2837（Cortex-A53）の検証済み構成は `ARM_bcm2837_verified`（AArch32、EL1）だけです。`AARCH64` の一覧に BCM2837 はありません。AArch64 で動かすと、kernel は検証の対象外になります。
- `ARM` は、5 つの性質がすべてそろうアーキテクチャです（バイナリ正当性と capDL の初期化子を含みます）。`AARCH64` には、バイナリ正当性も capDL の初期化子の証明もまだありません。D1 で AArch32 を選んだ理由の一つです。
- `ARM` には FPU の context switch がありません。音声の処理や camera の画像処理のように浮動小数点を使う userland の部品は、固定小数点で書くか、検証済み構成からの差分として記録します（[verified-config-deviations.md](verified-config-deviations.md)）。
- 同じ SoC 系列で AArch64 の証明がある Raspberry Pi 4B（BCM2711）と 5B（BCM2712）は、CM0 と pin 互換ではありません。CardputerZero では使えません。

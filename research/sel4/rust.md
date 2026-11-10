# seL4 の Rust の対応状況（rust-sel4）

[索引へ戻る](../README.md) ・ 採用の検討は [rust-adoption.md](rust-adoption.md)

seL4 の userland を Rust で書くための crate 群（rust-sel4）が、どの構成に対応しているかをまとめます。本リポジトリの検証済み構成 `ARM_bcm2837_verified` への対応と、それ以外の構成への対応を分けて書きます。各項目では、一次資料の記載、本リポジトリでの実測、推測、未確認を区別します。

## 調査の基準

- 調べた日: 2026-11-11
- rust-sel4: release `v6.0.0`（2026-10-30、commit `c819c27b076130cba9821c4555f23773e4b0bffd`）と、その時点の `main`（`f631577eb7def6fe6fb57afc7b8fd61bf144fcc`）
- 一次資料: [rust-sel4 の repository](https://github.com/seL4/rust-sel4)、[対応する構成](https://docs.sel4.systems/projects/rust/supported-configurations.html)、[使い方](https://docs.sel4.systems/projects/rust/how-to-use.html)、[release の一覧](https://docs.sel4.systems/projects/rust/releases.html)、[Microkit が対応する platform](https://docs.sel4.systems/projects/microkit/platforms.html)
- 実測: [QEMU raspi3b での Rust の root task の起動](../experiments/2026-11-11-rust-root-task-qemu.md)

## 一次資料が述べる対応範囲

文書の記載（原文）:

> The Rust crates maintained by the seL4 Foundation support all configurations (that is, all platforms and combinations of CMake options) that are supported by the kernel itself, except those based on 32-bit x86. The Microkit-related crates support all Microkit configurations.

これは上流の方針の記載です。どの構成を CI で試しているかは別に確かめる必要があります（次の節）。

各 release は、特定の seL4 と Microkit の版に合わせてあります（release の一覧より）。

| rust-sel4 | seL4 | Microkit |
|---|---|---|
| 6.0.0（最新） | 17.0.0 | 2.4.0 |
| 5.0.0 | 16.0.0 | 2.3.0 |
| 4.0.0 | 15.0.0 | 2.2.0 |
| 3.0.0 | 14.0.0 | 2.1.0 |
| 2.0.0 | 13.0.0 | 2.0.1 |
| 1.0.0 | 13.0.0 | 1.3.0 |

本リポジトリの seL4 17.0.0 に合うのは 6.0.0 です。crate は crates.io にまだ公開されておらず、Git か path で依存を指定します。nightly の機能を使うため、release ごとの `rust-toolchain.toml` にある nightly を使います（6.0.0 は `nightly-2026-08-21`、調べた時点の `main` は `nightly-2026-10-28`）。

## 主な crate

| crate | 役割 | ライセンス（Cargo.toml） |
|---|---|---|
| `sel4-sys` | libsel4 の header と interface 定義から bindgen で作る生の binding | BSD-2-Clause |
| `sel4` | capability の型付き wrapper、IPC、BootInfo、object の blueprint、VSpace | MIT |
| `sel4-config` | kernel の構成の値を Rust の `cfg` として使う macro | BSD-2-Clause |
| `sel4-root-task` | root task の runtime（入口、stack、TLS、panic、unwinding、heap） | BSD-2-Clause |
| `sel4-microkit` | Microkit の protection domain の runtime と libmicrokit の実装 | BSD-2-Clause |
| `sel4-capdl-initializer` | capDL の仕様から system を組み立てる Rust の initializer | BSD-2-Clause |
| `sel4-kernel-loader` | Rust の kernel loader（AArch32・AArch64・RISC-V の code がある） | BSD-2-Clause |
| `sel4-sync`、`sel4-shared-memory`、async、sDDF・LionsOS 向けの crate | 同期、共有メモリ、非同期、driver の interface | MIT または BSD-2-Clause など |

一部の crate は `MIT OR Apache-2.0`、`Apache-2.0 OR ISC OR MIT`、`BSD-2-Clause AND GPL-2.0-only` です。採用する crate ごとに確かめます（[rust-adoption.md](rust-adoption.md) のライセンスの節）。

## 構成ごとの対応状況

「上流の CI」は、rust-sel4 の `hacking/nix/scope/worlds.nix` に world として定義され、`hacking/nix/top-level/aggregates.nix` から build される構成を指します。world の定義があっても、すべての test が実行されているとは限りません（aggregate には `# TODO broken` で外された sel4test の項目があります）。

| 構成 | 文書の記載 | 上流の CI | 本リポジトリでの確認 | 検証済み構成か |
|---|---|---|---|---|
| AArch32 `bcm2837`（`ARM_bcm2837_verified`、本リポジトリの既定） | 対応（全構成の記載に含まれる） | world なし | QEMU raspi3b で root task が動いた（FPU の patch あり）。実機は未確認 | はい |
| AArch32 `qemu-arm-virt`（単一コア、非 MCS、Cortex-A15） | 対応 | あり（AArch32 の既定の world、simulate できる） | なし | いいえ |
| AArch32 `qemu-arm-virt` の SMP（2 コア） | 対応 | world あり | なし | いいえ |
| AArch32 `qemu-arm-virt` の MCS | 対応 | world あり | なし | いいえ（AArch32 の MCS は検証済み構成にない） |
| AArch32 `bcm2711`（Raspberry Pi 4、4 コア、hypervisor なし） | 対応 | world あり | なし | いいえ |
| AArch64 `bcm2837`（Raspberry Pi 3 を 64 bit で使う） | 対応 | world なし | なし | いいえ |
| AArch64 `qemu-arm-virt` と Microkit | 対応 | あり（AArch64 の既定の world と Microkit の world） | なし | いいえ（[verified-platforms.md](verified-platforms.md) を参照） |
| AArch64 `bcm2711` | 対応 | world あり | なし | はい（`AARCH64_bcm2711_verified`。AArch64 にはバイナリ正当性と capDL の初期化の証明がない） |
| RISC-V 64 bit の qemu と Microkit | 対応 | あり | なし | いいえ（RISCV64 の検証済み構成は `hifive`） |
| RISC-V 32 bit の qemu | 対応 | あり | なし | いいえ |
| x86_64 の pc99 と Microkit | 対応 | あり | なし | `X64` の検証済み構成は C の機能正当性だけ（[verified-platforms.md](verified-platforms.md)） |
| 32-bit x86（ia32） | **非対応**（文書で除外） | なし | なし | - |

検証済み構成の欄は kernel の証明についてで、Rust の crate が証明されているという意味ではありません。rust-sel4 の crate は、どの構成でも形式検証されていません。

## 本リポジトリの構成に固有の確認

`ARM_bcm2837_verified` の設定と rust-sel4 の前提を一つずつ照らし合わせました。

| 項目 | 本リポジトリの値 | rust-sel4 の前提 | 判断 |
|---|---|---|---|
| アーキテクチャ | AArch32、EL1 | target `armv7a-sel4-roottask`（`armv7a-none-eabi`、`target-pointer-width=32`） | 合う（実測） |
| TLS の register | `KernelArmTLSReg=tpidru`（Arm の名前で TPIDRURW） | `sel4-initialize-tls` と `sel4-runtime-common` が `mcr/mrc p15, 0, …, c13, c0, 2`（TPIDRURW）を使う | 合う（source と実測） |
| IPC buffer の場所 | `KernelIPCBufferLocation=threadID_register`（TPIDRURO） | `sel4` crate は IPC buffer の pointer を thread local の変数に置く | 衝突しない。TLS と別の register |
| FPU | context switch なし（`KernelAArch32FPUEnableContextSwitch=OFF`） | target が `+soft-float,-neon` | 合う。浮動小数点の命令を出さない |
| コア数 | 1（`KernelMaxNumNodes=1`） | 単一コアでも複数コアでも可 | 合う |
| MCS | なし | `sel4_cfg(KERNEL_MCS)` で API が切り替わる | 合う（MCS の API は使えない） |
| printing | `KernelPrinting=OFF` | `debug_println!` は `sel4_cfg(PRINTING)` のときだけある | 使えない。出力は UART の driver で行う（実測では PL011 に直接書いた） |
| kernel の source | seL4 17.0.0 に FPU の patch を当てた写し | rust-sel4 は libsel4 の header だけを読む | 影響しない。patch は kernel の起動処理だけで、libsel4 の header は変わらない（推測。header の差分は比べていない） |

このほか、`SEL4_INCLUDE_DIRS` に CMake の build が作る libsel4 の header（`gen_config`、`autoconf` を含む）を渡せば、`sel4-sys` は検証済み構成の値で binding を作ります。`projects/rust-smoke/build.sh` がその手順です。

## 周辺の基盤との関係

- **Microkit**: 文書は「AArch64 と RISC-V の board に対応、x86_64 は予定」としており（表には x86_64 の項目もある）、AArch32 には対応しません。このため `sel4-microkit` は本リポジトリの構成では使えません。Microkit を AArch32 に移植しない限り同じです（[userland-frameworks.md](userland-frameworks.md) の案 D）。
- **sDDF と LionsOS**: どちらも Microkit の上に作られ、AArch64 と RISC-V が前提です。rust-sel4 の sDDF 向けの crate も Microkit を前提とするため、本リポジトリでは考え方だけを取り入れます。
- **capDL**: `sel4-capdl-initializer` は `ARCH_AARCH32` の分岐を持ち（`memory.rs` で AArch32 の page の placeholder を 64 KiB に揃えるなど）、AArch32 を想定した code があります。AArch32 での実行は本リポジトリでは確かめていません。C の `capdl-loader-app` と違い、初期化の証明はありません。
- **CAmkES**: rust-sel4 の repository に CAmkES と組み合わせる code や文書は見つかりませんでした（`camkes` の文字列で検索）。CAmkES の component を Rust で書く公式の方法は確認できていません。
- **kernel loader**: 本リポジトリは C の elfloader（`vendor/seL4_tools`）を使います。`sel4-kernel-loader` に AArch32 の code はありますが、`bcm2837` の platform info で動くかは確かめていません。

## 未確認のこと

- 実機の CardputerZero（BCM2837）での Rust の root task の起動。
- `sel4-capdl-initializer` と、本リポジトリの capDL generator が作る仕様の組み合わせ。
- Rust の component を `capdl-loader-app` の下で動かすこと（root task ではない thread としての TLS と IPC buffer の初期化。`sel4-root-task` は root task 専用の runtime なので、別の runtime が要る）。
- 同じ入力から同じ binary ができるか（再現できる build か）。
- rust-sel4 の上流 CI の結果のうち、AArch32 で実際に実行されている test の範囲。

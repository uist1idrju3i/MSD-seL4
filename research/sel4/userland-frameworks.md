# userland の基盤の比較

[索引へ戻る](../README.md)

## 現在の決定（2026-11-12、利用者の判断）

root task を rust-sel4 `c819c27b` の `sel4-capdl-initializer` に変更します。system description は TOML とし、小さな generator から capDL を作る方針です。generator は次の PR で実装します。`parse-capDL` は schema が合う coliasgroup/capdl `26b8d39` を、専用の Docker build stage で作ります。[capDL の採用と設定](capdl.md)に互換性、toolchain、証明範囲を記録しています。

理由は、検証済み kernel の TLS 設定を変えずに Rust initializer が QEMU で部品を起動できたことと、musl の TLS patch を維持せずに済むことです。C `capdl-loader-app` の Isabelle による初期化のモデルレベルの証明は、この Rust initializer には適用されません。generator と initializer は証明の対象外です。kernel の構成と証明の範囲は変えません。QEMU の結果は実機の確認ではありません。

以下は 2026-11-11 時点の比較と旧案 B の決定の記録です。旧案の利点と推奨を、現在の採用決定とは区別して残します。

D1 で AArch32 の検証済み構成を選んだため、userland の基盤は AArch32 と `bcm2837` に対応する必要があります。採否は、driver の計画の前に「component-options」スキルで決めます。

| 基盤 | AArch32・rpi3 | 検証された部分 | 根拠（2026-11-11 取得） |
|---|---|---|---|
| Microkit 2.4.0 | 非対応。`build_sdk.py` の `KernelArch` は AARCH64・RISCV64・X86_64 だけで、board に rpi3 はない（rpi4b、rpi5b はある） | なし（初期化の検証は capDL と別） | https://github.com/seL4/microkit 、https://docs.sel4.systems/projects/microkit/platforms.html |
| sDDF（au-ts） | timer に `bcm2835` の driver がある。MMC は imx だけ、I2C は imx・meson・opentitan で、BCM の SPI・GPIO・SDHOST・SDHCI・USB の driver はない | なし | https://github.com/au-ts/sddf の `drivers/` |
| LionsOS 0.4.0 | Microkit と sDDF の上に作る研究開発中の OS。AArch64 前提 | なし | https://lionsos.org/ |
| CAmkES | 文書と tutorial を公開中。sel4test は AArch32 の rpi3 で build できる | なし（capDL の初期化を使う） | https://docs.sel4.systems/projects/camkes/ |
| capDL loader | AArch32 で使える | 初期化のモデルレベルの機能正当性（AArch32） | https://docs.sel4.systems/projects/sel4/verified-configurations.html |
| rust-sel4 | seL4 が対応する全構成を対象とする | なし | https://docs.sel4.systems/projects/rust/supported-configurations.html |

## 版と保守の状況（2026-11-11 に確かめた事実）

| 部品 | 最新の版 | seL4 17.0.0 との組み合わせ |
|---|---|---|
| CAmkES（`camkes-tool`） | `camkes-3.13.1`（2026-10-30） | `camkes-manifest` の `camkes-3.13.1` は kernel を `62e345c2`（17.0.0 と同じ commit）、`seL4_tools` を `6493e0c6`（`vendor/seL4_tools` と同じ）に固定している |
| capDL（`seL4/capdl`） | `0.6.1`（2026-10-30） | 同じ manifest が `23e3c5bb` に固定している |
| rust-sel4 | `v6.0.0`（2026-10-30） | 32-bit x86 を除く、kernel が対応する全構成を対象とする（文書の記載） |
| Microkit | `2.4.0`（2026-10-30） | AArch32 に対応しない（上表） |
| sDDF | `0.7.0`（2026-08-19） | AArch32 の BCM 用 driver は timer だけ |

## 初期化の証明の範囲

- C の `capdl-loader-app` は、algorithm が Isabelle/HOL で仕様化され、**model のレベルで**正しいと証明されています。**実装（C のコード）のレベルではありません**。証明は `seL4/l4v` の `sys-init/` にあります。
- 正しさの主張は「loader の終了後、system は capDL の仕様にある object と capability だけを持つ（loader の CSpace に残る、使われない capability を除く）」です。入力の仕様が well-formed の条件（`sys-init/WellFormed_SI.thy`）を満たす必要があります。
- 文書が capDL の初期化子の証明を挙げるのは `ARM`（AArch32）だけです。
- rust-sel4 の `sel4-capdl-initializer` は、`capdl-loader-app` と同じ目的の別実装です。この実装に対する証明は、README と文書に記載がありません（未確認として、証明なしと扱います）。

## 判断の材料

| 案 | 初期化の証明 | 記述の生成 | 部品の言語 | 利点 | 欠点 |
|---|---|---|---|---|---|
| A: CAmkES 3.13.1 | `capdl-loader-app`（model のレベル） | CAmkES の ADL から capDL を生成 | C | 17.0.0 と同じ commit で組み合わせが公開されている。connector（RPC、dataport、event）が揃う | Python・Haskell・Jinja を含む大きな toolchain。生成される glue code は証明されていない |
| B: capDL を直接使う、自作の小さな記述 | `capdl-loader-app`（model のレベル） | `python-capdl-tool` を使う自作の generator | C と Rust | 記述が小さく、capability の表と capDL を 1 対 1 で照合できる。Microkit に近い形にできる | generator と IPC の規約を自作する |
| C: rust-sel4 と `sel4-capdl-initializer` | なし | 自作 | Rust | Rust の型で IPC を書ける | 初期化の証明を失う |
| D: Microkit を AArch32 に移植 | なし（Microkit の monitor は証明されていない） | Microkit の SDF | C と Rust | sDDF の部品を使える | 上流に AArch32 の対応がなく、移植と追従の工数が大きい |

## 推奨と決定（推奨の理由は推測を含む）

- **B を推奨します。** 初期化の証明がある `capdl-loader-app` を root task とし、system の記述を capDL で静的に固定します。capability の分配は capDL の仕様から機械的に確かめられます（「部品 X が資源 Y に届くか」）。
- Rust の対応状況と採用の検討は [rust.md](rust.md) と [rust-adoption.md](rust-adoption.md) にあります。
- 部品は C を基本とし、証明や検査の道具（Frama-C、CBMC、Kani、Verus）との相性を形式検証の調査（`research/verification/`）で比べてから、Rust を使う範囲を決めます。
- A は、B の generator が大きくなりすぎた場合の代わりとして残します。CAmkES の connector の設計は参考にします。
- sDDF の設計（方向が決まった共有メモリの queue と通知、driver と virtualiser の分離）は、コードを使わずに考え方として取り入れます。
- smoke test（task 17）は、capDL を使う前に、最小の root task で起動と UART を確かめる段階から始めます。

**決定（2026-11-11、利用者の判断）:** 案 B を採ります。

## 未確認

- `capdl-loader-app` と capDL tool 0.6.1 を、seL4 17.0.0 の AArch32 `bcm2837` で build できるか。
- `sys-init` の証明が仮定する kernel の API と、17.0.0 の API の対応。
- Microkit を AArch32 に移植する工数。

# 調査・設計の記録（索引）

MSD/seL4 の内部文書です。公開サイトは `docs/` にあります。各文書では、現在の決定、一次資料、実測、推測、未確認を区別します。調査の基準は seL4 17.0.0（commit `62e345c240a15671484530b4e6e069ce266c28d7`）と、2026-11-11 に取得した公開ページです。本リポジトリでは、まだ実機と QEMU での試験をしていません。

## 現在の決定（2026-11-11、利用者の判断）

| # | 論点 | 決定 |
|---|---|---|
| D1 | kernel の構成 | AArch32 の検証済み構成 `ARM_bcm2837_verified` を製品の既定にする |
| D2 | 設計の柱「すぐ使える」 | 加えない |
| D3 | 内部文書の置き場 | `research/` |
| D4 | ライセンス | BSD-3-Clause（依存と合わせる必要がないため） |
| D5 | 準備段階の CI | seL4 kernel の検証済み構成の build を確かめる |
| D6 | 共通の開発環境 | C の build、QEMU、Rust。Haskell と Isabelle・l4v は userland の基盤を決めた後に判断 |
| D7 | m5stack-linux-dtoverlays | 最新の `main`（`4f7aeee9`）に固定し、以後は Dependabot で追う |
| D8 | PR の分け方 | 主題ごとに stacked PR |
| - | driver | すべてユーザー空間に自作する。driver ごとに深い調査と深い計画を立ててから実装する |

## 文書

| 文書 | 内容 |
|---|---|
| [sel4/verified-configuration.md](sel4/verified-configuration.md) | 検証済み構成、証明された性質、前提、対象外の部分 |
| [sel4/verified-config-deviations.md](sel4/verified-config-deviations.md) | 検証済み構成からの差分の一覧 |
| [sel4/verified-platforms.md](sel4/verified-platforms.md) | 形式検証済みのアーキテクチャと、platform ごとの SoC・CPU の一覧 |
| [sel4/boot-chain.md](sel4/boot-chain.md) | Raspberry Pi firmware から seL4 までの起動経路と A/B 更新の可能性 |
| [sel4/userland-frameworks.md](sel4/userland-frameworks.md) | userland の基盤（Microkit、CAmkES、capDL、rust-sel4、sDDF、LionsOS）の比較、版、初期化の証明の範囲、推奨 |
| [sel4/system-architecture.md](sel4/system-architecture.md) | 部品の分け方と、capability・IPC・IRQ・MMIO・DMA・fault の設計方針 |
| [hardware/inventory.md](hardware/inventory.md) | CardputerZero の device と接続 |
| [drivers/README.md](drivers/README.md) | driver ごとの状況 |
| [security/threat-model.md](security/threat-model.md) | 脅威と、seL4 で防げる範囲・防げない範囲 |
| [verification/layers.md](verification/layers.md) | 証明・host・QEMU・実機の確認の階層 |
| [verification/beyond-kernel.md](verification/beyond-kernel.md) | kernel 以外の形式検証の道具、層ごとの判断、計画、柱への追加 |
| [vendor/dependencies.md](vendor/dependencies.md) | 依存の固定版、ライセンス、採用の理由 |
| [experiments/README.md](experiments/README.md) | 実験記録の一覧 |

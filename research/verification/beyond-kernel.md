# kernel 以外の形式検証

[索引へ戻る](../README.md)

seL4 kernel の証明の外側（初期化、userland、driver、起動、更新、storage、暗号）を、どこまで形式検証できるかを調べました。結論は「全体の証明はできない。部品ごとに、証明・model 検査・静的解析・試験を組み合わせ、どの部品がどの方法で確かめられたかを表で公開する」です。

## 一次資料から確かめたこと（2026-11-11）

| 道具・成果 | 何を証明・検査するか | AArch32 で使えるか | 根拠 |
|---|---|---|---|
| seL4 の l4v（`seL4-17.0.0`） | kernel の機能正当性（`crefine`）、完全性と権限の閉じ込め（`access-control`）、機密性と非干渉（`infoflow`）、バイナリ正当性（`asmrefine`） | `L4V_ARCH=ARM` がすべての session を持つ | https://github.com/seL4/l4v の README |
| l4v の `sys-init` | capDL による初期化の algorithm（model のレベル） | `ARM` | 同上。`capdl-loader-app` の C 実装は対象外 |
| l4v の `camkes` | CAmkES の初期の形式化 | - | 同上。glue code の正しさの証明ではない |
| capDL の仕様 | capability の分配から「部品 X が資源 Y に届くか」を決める | 仕様の性質で、アーキテクチャに依らない | https://docs.sel4.systems/projects/capdl/ |
| Pancake（CakeML、BSD-3-Clause） | C に近い言語。compiler の各 pass に正しさの証明がある（`pancake/proofs/`、`pan_to_targetProofScript.sml`）。proof を生む decompiler で program を interaction tree にできる | CakeML の backend に `arm7` と `arm8` がある | https://github.com/CakeML/cakeml の `pancake/`、`compiler/backend/` |
| sDDF の Pancake 版 | serial の driver（`drivers/serial/*/uart.pnk`）と virtualiser（`serial/components/virt_*.pnk`） | BCM 用はない | https://github.com/au-ts/sddf |
| Frama-C（WP、Eva） | C の関数の契約（ACSL）の証明と、未定義動作の不在の解析 | host で解析する。対象のアーキテクチャの前提（整数の幅など）を設定する | https://frama-c.com/ |
| CBMC 6.11.0 | C の有界 model 検査（境界、overflow、assertion） | 同上 | https://github.com/diffblue/cbmc |
| Kani 0.68.0（Apache-2.0） | Rust の有界 model 検査 | 同上 | https://github.com/model-checking/kani |
| Verus（MIT） | Rust の関数の仕様を SMT で証明 | 同上 | https://github.com/verus-lang/verus |
| SPARK（GPL-3.0） | Ada の部分集合の証明 | GNAT の AArch32 の toolchain が要る | https://github.com/AdaCore/spark2014 |

## 層ごとの判断（推測を含む）

| 層 | 方法 | 証明できること | 証明できないこと・前提 |
|---|---|---|---|
| kernel | seL4 の証明をそのまま使う。検証済み構成からの差分を 0 に保つ（CI で検査） | 上表の性質 | 起動処理、cache・TLB の操作、hardware |
| system の初期化 | `capdl-loader-app` と capDL の仕様。仕様の well-formed を検査 | algorithm の正しさ（model）。仕様からの権限の到達可能性 | loader の C 実装、ELF の読み込み |
| capability の分配 | capDL の仕様に対する検査（自作の generator が出す表との照合） | 部品が持つ権限が設計の表と一致すること | 共有メモリの中身の正しさ |
| IPC の契約 | 契約を C の ACSL または Rust の仕様として書き、両端で検査する | 片側の実装が契約を守ること | 相手の部品の正しさ（契約を前提にする） |
| driver の論理（状態機械、queue、message の解析） | Pancake で書いて compiler の証明を使う、または C で Frama-C と CBMC、Rust で Kani と Verus | 仕様どおりに register へ読み書きすること、境界の超過や overflow がないこと | device の振る舞い（datasheet の model が正しい前提） |
| DMA を使う driver | 上と同じ。加えて buffer の所有の規約を契約にする | buffer の範囲を守ること | IOMMU がないため、device が規約を破る場合 |
| storage と A/B 更新 | 状態機械を model 検査し、電源断の各点で不変条件を確かめる。実装は上と同じ方法 | 「いつ電源が落ちても、ある 1 つの正しい版で起動できる」の model での成立 | SD card の書き込みの原子性（前提）、firmware の tryboot |
| 暗号 | 形式検証された実装（例: HACL*）の採用を検討する | 採用した実装が仕様どおりであること | 乱数の源、side channel、鍵の保管 |
| 起動（ROM、GPU firmware、elfloader） | 試験と review だけ | なし | 全体を前提とする |
| hardware | なし | なし | 全体を前提とする |

暗号の HACL* は候補として挙げただけで、AArch32 での build と license は未確認です。

## 計画（案）

1. capDL の仕様を設計の正本にし、capability の表との照合を CI に入れる（userland の基盤が決まってから）。
2. IPC の契約を、最初の driver（UART、GPIO）から書き、host の試験と CBMC か Kani で検査する。
3. Pancake を、小さな driver（UART）で試し、C で書いた同じ driver と、工数、性能、証明の範囲を比べる。結果を `research/experiments/` に残す。
4. A/B 更新の状態機械を model で書き、電源断の点を総当たりで確かめる。
5. 部品ごとに「証明」「model 検査」「静的解析」「試験」「review だけ」「前提」のどれで確かめたかを、README の表で公開する。

## 柱への追加

「検証できる」の柱に、次を加えます。「kernel の外でも、実用になる範囲で形式検証を使い、部品ごとに確かめた方法と前提を公開する」。全体を検証済みとは呼びません。

## 未確認

- Pancake の compiler の証明が、`arm7` の backend までつながるか（`pan_to_targetProofScript.sml` が target ごとに何を仮定するか）。
- Pancake を seL4 の AArch32 の userland と link する手順（sDDF の Pancake 版は Microkit 前提）。
- Frama-C の現在の版と、ACSL で seL4 の system call をどう model にするか。

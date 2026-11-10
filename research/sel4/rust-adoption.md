# Rust の採用の検討

[索引へ戻る](../README.md) ・ 対応状況は [rust.md](rust.md)

rust-sel4 を使って Rust で部品を書く場合の利点、危険、形式検証、toolchain、ライセンスを検討し、段階的な採用の案をまとめます。

## 現在の決定との関係

- userland の基盤は案 B（C の `capdl-loader-app` を root task にし、system の記述は capDL を自作の小さな generator で作る）に決まっています（[userland-frameworks.md](userland-frameworks.md)）。この文書は B を変えません。Rust は B の上で動く部品の言語として検討します。
- `sel4-capdl-initializer` に置き換えると、初期化の model のレベルの証明を失います。置き換えは、別の判断を利用者から得るまで行いません。
- DMA の方針（中央の DMA controller は DMA server だけが持つ。device 自身が bus master のものは、その driver を全メモリに書ける部品として扱う）は、言語によらず同じです（[dma-iommu.md](../drivers/dma-iommu.md)）。

## C と比べた利点と欠点

| 観点 | Rust（rust-sel4） | C（libsel4、sel4runtime） |
|---|---|---|
| メモリ安全 | safe Rust の範囲で、境界外の access、use-after-free、data race を型で防ぐ | 防がない。Frama-C、CBMC などで別に示す必要がある |
| capability の型 | `Cap<cap_type::Untyped>` のように型が付き、種類の取り違えを compile 時に見つける | `seL4_CPtr` は整数で、取り違えは実行時の error になる |
| message の解析 | parser を safe Rust で書ける | 境界の検査を手で書く |
| 大きさ（実測、QEMU の同じ処理） | text 23,796 byte | text 5,587 byte |
| toolchain | release ごとの nightly、`-Z build-std`、libclang（bindgen）が要る | 既存の GCC と CMake だけ |
| 証明・検査の道具 | Verus、Kani。どちらも研究段階を含む | Frama-C、CBMC。産業での実績がある |
| 証明済みの部品との組み合わせ | Rust の initializer には証明がない | `capdl-loader-app` は model のレベルの証明がある |
| 上流の安定性 | crates.io に未公開。nightly に追従して API が変わる | libsel4 の API は版ごとに CHANGES に書かれる |

大きさの差は、`sel4-root-task` の runtime（TLS、unwinding、allocator）を含む結果です。部品ごとの差は、同じ機能の C と Rust を作って測ります（推測で決めません）。

## unsafe の境界

Rust を使っても、次の処理は `unsafe` の中に残ります。部品ごとに、`unsafe` を置く module を一つに集め、その前提を英語の comment と仕様（Verus の `requires`、Kani の harness）で書きます。

| 処理 | 理由 | 守ること |
|---|---|---|
| MMIO の読み書き | 仮想 address への volatile な access は、型で正しさを示せない | `read_volatile`・`write_volatile`（または tock-registers）だけを使う。map は cacheable にしない（AArch32 では `PAGE_CACHEABLE` を付けない） |
| DMA の buffer と descriptor | device が物理 address を読み書きする。Rust の所有権は device に及ばない | buffer は DMA server が登録した範囲だけ。cache の clean・invalidate を転送の前後に行う。descriptor の `NEXTCONBK` の連鎖を検査する |
| 共有メモリ | 相手の部品が同時に書き換える | 相手が書く領域から読んだ値は、検査の前に信頼しない（読み取りを一度にし、写してから検査する） |
| IRQ | ack の順番と再入 | notification を待つ loop を一つに限る |
| BootInfo と ELF の領域 | kernel が渡す pointer | runtime の crate に任せ、部品の code では触らない |
| FFI と生の binding | `sel4-sys` は C の ABI に合わせた生の関数 | 部品からは `sel4` crate の型付き API だけを使う |

調べた時点で、`unsafe` という語を含む行は `sel4` が 45、`sel4-runtime-common` が 25、`sel4-initialize-tls` が 16、`sel4-root-task` が 5、`sel4-capdl-initializer` が 5 でした（`grep -w unsafe` の行数で、block の数ではありません）。これらは上流の code で、本リポジトリの TCB に入ります。

cache の操作（`seL4_ARM_Page_Clean_Data` など）が `sel4` crate で型付きに包まれているかは確かめていません。DMA server を Rust で書く前に確かめます。

## 形式検証と検査

| 道具 | 対象 | rust-sel4 との関係 | 限界 |
|---|---|---|---|
| Verus | Rust の関数の仕様を SMT で証明 | `crates/private/tests/root-task/verus` に root task の例がある。Nix の環境が `release/0.2026.11.02.8bf68ee` を固定 | 証明は Verus で書いた関数の中だけ。`unsafe`、MMIO、device の振る舞い、runtime は対象外 |
| Kani | Rust の有界 model 検査 | Nix の環境が `kani-0.67.0` を固定 | 有界の範囲だけ。harness の外の入力や、並行性の一部は扱わない |
| Ferrocene | 認証を受けた Rust の compiler | Nix の環境に `rolling-2026-03-05` がある | compiler の品質の保証で、program の正しさの証明ではない |
| Frama-C、CBMC（C の比較対象） | C の仕様の証明と model 検査 | C の部品に使う | ACSL を書く手間が大きい |

rust-sel4 の crate 自体（`sel4`、`sel4-root-task` など）は形式検証されていません。Rust の型による保証は、safe Rust の部分のメモリ安全に限られ、機能の正しさ、capability の分配、device の扱いを示すものではありません。証明の範囲は [beyond-kernel.md](../verification/beyond-kernel.md) の層の分け方に合わせて書きます。

## toolchain と CI

- **固定**: release `v6.0.0` の commit を `rev` で指定し（tag は付け替えられるため）、`Cargo.lock` をコミットして `--locked` で build します。nightly は release の `rust-toolchain.toml` と同じ版にします。違う nightly では build できないことを実測しました（[実験記録](../experiments/2026-11-11-rust-root-task-qemu.md)の失敗した試行）。
- **開発用 image**: 2026-11-11 に、`docker/msd-sel4-dev` へ rust-sel4 の nightly、`rust-src`、libclang を加え、使っていなかった安定版の Rust を外しました。CI の `kernel-verified` は、Rust の root task を build して QEMU で起動します（QEMU だけ）。
- **更新の追跡**: crates.io にないため、Dependabot の cargo では rust-sel4 の新しい release を追えません。`pins-check` の対象に rust-sel4 の release と nightly の版を加えるかを、採用を決めるときに検討します。更新の手順は「vendor-update」スキルに従います。
- **上流の CI**: rust-sel4 は Nix で worlds を組み、Kani と Verus も build します。本リポジトリでは Nix を使わず、CMake の build が作る header を `SEL4_INCLUDE_DIRS` で渡します。

## ライセンス

- rust-sel4 の crate は主に BSD-2-Clause です。`sel4` と `sel4-sync` は MIT です。
- 実験で使った 81 package の依存には、MIT、Apache-2.0、`Apache-2.0 WITH LLVM-exception`、ISC、Unlicense、Unicode-3.0、BSD-3-Clause が含まれます（`cargo metadata` の値）。多くは build 時だけ使う crate（bindgen など）で、binary に入るのは `sel4` 系の crate、`dlmalloc`、`unwinding`、`lock_api` などです。binary に入る crate の一覧は、採用するときに `cargo tree` で確かめます。
- `BSD-2-Clause AND GPL-2.0-only` の crate は使いません。使う必要が出たら、利用者の判断を得ます。
- 本リポジトリの Rust の code は BSD-3-Clause で、配布する binary に入る crate の著作権表示を残します。

## 選択肢と推奨

| 案 | Rust で書くもの | 得られること | 失うこと・危険 |
|---|---|---|---|
| R0 | なし（すべて C） | toolchain が小さい | parser と protocol の処理のメモリ安全を、別の道具で示す必要がある |
| R1 | 全メモリに届かない部品のうち、parser、protocol の処理、純粋なデータ変換 | 外部の入力を読む部分のメモリ安全。Verus・Kani を試しやすい | nightly の toolchain の維持 |
| R2 | R1 に加え、DMA を使わない driver（I2C、GPIO、UART、keyboard、センサー） | MMIO を `unsafe` の小さな module に閉じ込められる | MMIO の正しさは型で示せない |
| R3 | R2 に加え、DMA server | buffer と descriptor の検査を型と Verus で書ける | 全メモリに書ける部品の正しさを、上流の未検証の crate に頼る |
| R4 | device 自身が bus master の driver（USB、カメラ、VideoCore、mailbox） | 言語の利点は R2 と同じ | 全メモリに届くことは言語で変わらない |
| R5 | `sel4-capdl-initializer` で root task を置き換え | 仕様の挿入が build と分かれる | 初期化の証明を失う |
| R6 | Microkit を AArch32 に移植して `sel4-microkit` と sDDF を使う | 上流の部品を使える | 移植と追従の工数。Microkit の monitor は証明されていない |

**推奨（推測を含む）:** R1 から始め、R2、R3 の順に広げます。R4 は部品ごとの調査で決め、R5 と R6 は採りません。

1. capDL の generator と `capdl-loader-app` で、C の部品が二つ以上動くところまで進める。
2. Rust の部品を `capdl-loader-app` の下で一つ動かす。root task ではない thread の TLS と IPC buffer を初期化する方法を、ここで確かめる（rust.md の未確認のこと）。
3. 外部の入力を読む部品（たとえば keyboard の event の解析、設定の parser）を Rust で書き、Kani の harness を付ける。C で書いた場合と大きさを比べる。
4. DMA を使わない driver を一つ Rust で書き、C 版と MMIO の access の回数・大きさを比べる（driver ごとの調査は順番に行う）。
5. DMA server を書く前に、cache の操作の API、descriptor の検査の仕様、Verus で示す性質を決め、利用者の判断を得る。

## 判断を変える条件

- rust-sel4 の上流が、crate や initializer の形式検証を公開した場合。
- rust-sel4 の上流 CI に `bcm2837` の world が加わった場合、または AArch32 の test が外された場合。
- 実機で、Rust の部品の大きさや速度が要件に合わないと分かった場合。
- 安定版の Rust で build できるようになった場合（nightly の維持が不要になる）。
- Microkit が AArch32 に対応した場合。

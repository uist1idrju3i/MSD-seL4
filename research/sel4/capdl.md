<!-- SPDX-License-Identifier: BSD-3-Clause -->
# capDL と Rust initializer の採用

[索引へ戻る](../README.md) ・ [固定値と URL](../vendor/dependencies.md) ・ [互換性の試験](../experiments/2026-11-12-capdl-schema.md)

## 未確認と、この PR の範囲

実機での起動、全 object 種別の schema 互換性、generator の正当性は未確認です。PR 1 は依存と決定だけを追加します。PR 2 で TOML からの generator、PR 3 で起動の統合を行う予定です。ここでは製品の root task を切り替えず、既存の smoke test を残します。

## 決定と代替案（2026-11-12、利用者の判断）

| 部品・選択肢 | 対応、由来、ライセンス | 採否と理由・リスク |
|---|---|---|
| `sel4-capdl-initializer` | rust-sel4 v6.0.0 `c819c27b076130cba9821c4555f23773e4b0bffd`、BSD-2-Clause。AArch32 の最小 root-task target がある | 採用。`tpidru` を維持して QEMU raspi3b で部品を起動できた。形式証明はなく、Rust・archive・unsafe の境界を信頼する |
| C `capdl-loader-app` | seL4/capdl。AArch32 の初期化モデルの Isabelle 証明がある | 旧案 B。musl の TPIDRURO 前提が検証済み構成の `tpidru` と合わない。patch の維持を避けるため取りやめる。証明上の利点は失う |
| seL4/capdl の Haskell tool | 公式 upstream。`23e3c5b` と master `55d2ef24` を調査。BSD-2-Clause | 不採用。どちらも frame cap の `executable` を JSON に出さず、指定の add-spec が拒否する |
| coliasgroup/capdl の Haskell tool | seL4/capdl の fork、rust branch `26b8d39c17e99e5423763e9ed292a1d123c39f56`。rust-sel4 の `hacking/nix/scope/sources.nix` が指定。tool は BSD-2-Clause | 採用。frame の実行権限を含めて schema が合う。公式 upstream と別の進行を追う必要があり、fork の停止・schema 変更のリスクがある。revision と tarball hash を固定し、更新時に試験する |
| JSON を直接自作 | Haskell を省けるが、object の allocation 順序や cap の参照を自前で正しく作る必要がある | 製品の経路には採らない。spike の手書き JSON では allocation 順と non-MCS の fault endpoint の誤りがあった |
| 自作の root task | AArch32 に実装可能だが初期化全体が自作になる | 不採用。capDL の既存機能を使い、generator の範囲を小さくする |
| Microkit、CAmkES、sDDF、LionsOS、Pancake | 対応状況と役割は [基盤の比較](userland-frameworks.md)と [Rust の採用](rust-adoption.md)に記録 | その比較を引き継ぐ。Microkit/LionsOS は AArch32 に合わず、CAmkES は今の小さな generator より大きい。sDDF/Pancake は initializer の代替ではない |

### schema と toolchain

公式の `23e3c5b` で作った JSON を add-spec に渡すと、fixture の frame cap で次のエラーになりました。master `55d2ef24` の `PrintJSON.hs` も同じ内容です。

```text
Error: missing field `executable` at line 1 column 744
```

fork の既定は GHC 9.10.3 / `lts-24.32` です。当初の GHC 9.2.8 / `lts-20.25` では `bytestring`、`containers`、`mtl`、`text` などの bounds が合わず、Stack が build plan を拒否しました。2026-11-12 に利用者が fork 自身の toolchain を使う方針に変更しました。互換 patch、`allow-newer`、依存 bounds の緩和は使いません。

### 初回追加として確認した変更とライセンス

製品への既存導入はなく、更新前の Haskell tool はありません。spike の公式版と fork の差分、双方の `CHANGES.md`、GHC 9.10.3 の release notes、Stack 3.7.1 の changelog を一次資料として確認します。

| 分類 | 確認内容と扱い |
|---|---|
| 破壊的変更 | fork は新しい Haskell library の bounds と GHC 専用 warning flag を持つ。declared resolver をそのまま採用する。公式版の JSON に `executable` はないため交換不可 |
| セキュリティ | この追加は kernel source・config を変えない。特定の CVE を修正する更新ではなく、parser と build tool の依存は別途更新監視が必要 |
| 機能・option・既定値 | fork は cap の実行権限と `executable` の出力を持つ。frame cap は既定で実行可能なので、非コードの frame は `execute_never` を明示する。公式版の `X` 権限の表記と fork の `executable` / `execute_never` は交換不可。採用するのは JSON 経路だけ。C、XML、Isabelle 出力などは使わない |
| ライセンス | Haskell tool の BSD-2-Clause 通知を保つ。source repository 全体の GPL 部分である C loader は build しない。GHC/Stack は build stage 限定だが、binary に link される Haskell library・RTS の通知も保持する |

## build と runtime の option

表の「設定」は採用経路で使う値です。PR 1 で initializer 自体の build を製品へ追加するわけではありません。固定版の一次資料を対象にし、最新版への自動追従はしません。公式版との差は上記の schema と toolchain にあります。rust-sel4 は v6.0.0 のままで、更新による feature 差はありません。

### initializer の Cargo feature と build 条件

| option | 意味・既定 | 設定と理由 |
|---|---|---|
| `default` | `deflate` を有効にする | 既定を使う |
| `deflate` | frame-fill の圧縮を展開する | 有効。add-spec の圧縮と合わせる |
| `alloc` | 初期化で heap allocation を使う。既定は無効 | 無効。最小 root-task target で動作した構成を維持する |
| Rust target | CPU/ABI を選ぶ | `armv7a-sel4-roottask-minimal.json`、soft-float、strict alignment。既存 nightly `nightly-2026-08-21` と build-std を使う |
| kernel config | libsel4 の生成 header から取得 | `ARM_bcm2837_verified`、`tpidru`、`threadID_register`、non-MCS、単一 core、FPU context switch なし。変更しない |
| runtime input | CapDL custom program header の rkyv archive | 起動時の CLI や TOML parser はない。TOML は host 側で処理する |

### add-spec の CLI

一次資料: `crates/sel4-capdl-initializer/add-spec/src/main.rs`。short option は括弧内に示します。

| option | 意味・既定 | 設定と理由 |
|---|---|---|
| `--initializer-elf` (`-e`) | 必須、spec 未追加の ELF | strip 済みの bare initializer |
| `--spec-json` (`-f`) | 必須、InputSpec JSON | parse-capDL の出力 |
| `--fill-dir` (`-d`) | 必須、fill file の探索先 | component ELF を置いた build directory |
| `--out-file` (`-o`) | 必須、生成 ELF | bare ELF とは別名にする |
| `--object-names-level` (`-n`) | 必須、0=なし、1=TCB、2=全 object | 試験は 2。製品での名前の削減は後続で判断 |
| `--no-embed-frames` | 既定 false | 指定せず frame を埋め込む |
| `--no-deflate` | 既定 false | 指定せず圧縮する。initializer の feature と一致させる |
| `--initializer-verbosity` | 0..5、既定 3 (Info) | verified config は printing 無効。spike は 0、互換性試験は既定。printing は有効にしない |
| `--verbose` (`-v`) | 既定 false、host 側の引数を表示 | 通常は指定しない |
| `--help` (`-h`) | clap の自動生成 help | host の引数確認用 |

### parse-capDL の全 CLI

一次資料: fork の `capDL-tool/Main.hs` の `options`。選択する output 以外はすべて未指定が既定です。

| option | 意味・既定 | 設定と理由 |
|---|---|---|
| `--json` | FILE に JSON | 採用。rust-sel4 の InputSpec への経路 |
| `--object-sizes` | kernel object サイズの YAML。既定なし | 指定。allocation 順のため生成 header に合わせる。fixture の定数は試験専用 |
| `--isabelle` (`-i`) | Isabelle 出力 | 不採用。Rust initializer の証明にはならない |
| `--dot` (`-d`) | DOT 出力 | 通常は不使用。調査時に利用可能 |
| `--code` (`-c`) | C spec | 不使用。C loader を採らない |
| `--code-dynamic-alloc` | C spec の動的 allocation。既定 true | JSON 経路では指定しない |
| `--code-static-alloc` | C spec の静的 allocation | JSON 経路では指定しない |
| `--xml` (`-x`) | XML 出力 | 不使用 |
| `--text` (`-t`) | capDL text 出力 | 通常は不使用 |
| `--analysis` (`-a`) | cap leak / information flow の解析結果 | PR 1 では使わない。形式証明の代わりにしない |
| `--dump-ast` | AST 出力 | 通常は不使用 |
| 位置引数 | 入力 file 一つ、必須 | `.cdl` fixture または generator の出力 |
| `--help` | 固定版にはない | 追加しない。image test は実際に JSON を生成する |

capDL-tool.cabal に独自の Cabal flag はありません。`-O2 -Werror -Wall` と warning 除外は上流の指定を維持します。Stack は `--system-ghc --no-install-ghc` で pinned bindist だけを使い、SHA-256 を照合した snapshot を local resolver として渡します。`--jobs 2` は build のメモリ使用を抑えるためです。

Stack 3 系は GHC 8.4 より前を対象から外し、GHC 同梱の Cabal を使います。3.3.1 から GHC 9.10 を tested compiler として扱うため、spike の Stack 2.15.7 ではなく 3.7.1 を固定します。`script`・Hpack・Windows の改善はこの build では使いません。GHC 9.10.3 の compiler・RTS・library 修正を含む bindist をそのまま使い、LLVM/Wasm backend などの新しい設定は有効にしません。

## pipeline と packaging の制約

```text
TOML（PR 2）→ generator → .cdl
                           ↓ parse-capDL --object-sizes=... --json=...
component ELFs ──────────→ JSON + fill directory
                           ↓ sel4-capdl-initializer-add-spec
bare initializer → strip → spec 付き initializer → elfloader / boot image
```

**strip は必ず add-spec より前に行い、追加後の ELF には行いません。** spike では elfloader の CMake custom command が rootserver を strip し、section を持たない埋め込み spec/frame の LOAD segment を除去しました。10 個の program header が 8 個になり、spec header の file size が 0 になった結果、runtime が正しい archive を読めませんでした。rkyv の root は buffer の末尾にあり、空の buffer を unchecked access することは安全ではありません。

元の archive は x86_64 と qemu-arm 上の ARM32 の checked access で、どちらも `Some(0)` を返しました。両方で長さ 1072、root size 112、alignment 8、root offset 960 が一致しています。strip されていない ELF を梱包し、手書き JSON の allocation 順と fault endpoint を直した後に QEMU で部品の marker が出ました。この spike の回避策を製品へコピーするのではなく、PR 3 で「strip 後に add-spec」を packaging に組み込みます。

Haskell tool は host image の専用 stage で build します。最終 image には strip 済み binary と必要な library・通知だけを渡します。対象は既存 CI と同じ amd64 host です。Arm の kernel を作ることと、開発 image の host architecture は別です。arm64 host はこの bindist の対象外として早く失敗させます。

## TOML schema と独立 checker（PR 2）

`tools/capdl/generate.py` は一つの TOML から PD の ELF・stack・IPC buffer と明示的な型付き grant を読み、AArch32 の `.cdl` と capability 表を生成します。PT_LOAD ごとの file-backed frame fill を使い、BSS はゼロにします。標準ライブラリだけで動きます。

`tools/capdl/check.py` は生成器を呼ばずに parse-capDL の JSON の TCB→CSpace をたどり、宣言と slot・対象・型・rights・badge が完全一致するかを検査します。VSpace と device の物理アドレス、frame fill も照合します。未知の key、untyped/CNode/TCB grant、無許可の grant 権、kernel device との重なり、DMA marker の不足を拒否します。schema と ELF reader は共有するため、検査器同士の一致を形式証明とは扱いません。

[schema と checker の仕様](capdl-generator.md)に全 key・CLI・拒否条件を、[生成した表](serial-client-capabilities.md)に serial/client の権限を記録します。

## 二つの C component を起動する（PR 3）

`projects/capdl/build.sh` が verified configuration と既存の boot patch の写しで C component を build します。musl は使いません。sel4runtime の ARM CRT の `_start` から、この project の `__sel4_start_c` に入ります。CapDL は SP とゼロ初期化した RAM を渡しますが、System V の argc/auxv は渡さないため、通常の runtime の main 起動処理を呼びません。一 thread/PD に限定し、libsel4 の thread-local IPC pointer を userland の option `LibSel4UseThreadLocals=OFF` で global にし、TOML から生成した IPC address を設定します。kernel の TLS/IPC 設定は変えません。

同じ TOML から生成した slot/address の header を C が使います。object-size YAML は実際の libsel4 header を preprocess した値です。unit-test のサイズを流用しません。`.cdl` を生成・check し、固定 parser の JSON を add-spec に渡します。Rust source は rust-smoke の固定 Cargo dependency から取得し、その checkout の Cargo.lock で initializer と host add-spec を `--locked` build します。nightly も rust-smoke の toolchain file から読み、minimal AArch32 root-task target、default deflate、alloc なしを使います。

initializer は **add-spec 前に `strip --strip-debug`** します。full strip は add-spec が patch する symbol まで消すので使えません。埋め込んだ後は `tools/capdl/copy-rootserver.sh` で byte copy だけにし、elfloader が pack する rootserver と元の ELF を `cmp` します。kernel の pack も copy です。seL4_tools と vendor は変更しません。生成した image は既存の AArch32 entry stub で QEMU raspi3b に渡します。

```sh
docker/msd-sel4-dev tools/qemu-capdl.sh build/capdl-positive positive local-positive
docker/msd-sel4-dev tools/qemu-capdl.sh build/capdl-negative negative local-negative
```

引数は build directory、`positive|negative|silent`、run ID です。`QEMU_TIMEOUT` は正の整数秒で既定 10、`QEMU_CAPDL_SKIP_BUILD=1` は保存済み binary を hash 照合して再利用します。run ID は英数字・`_-` のみで、既存の run directory は上書きしません。silent は送信を止める対照で、runner が失敗することを期待します。将来の rebuild 前には古い binary と log を保存してください。

serial は badge 1・長さ 2・request の内容を確認して marker を出し、Reply します。client は reply を検査して二度目の Call で ACK を送り、serial の二つ目の marker によって往復も確認します。negative だけがその後に未 mapping の PL011 物理アドレスを read します。serial は badge 2・VMFault・長さ・data abort・アドレスと protocol の状態を確認して fault marker を出し、reply せず止めます。client には device の cap も mapping もありません。

runner は log 全体が正しい順の marker だけであることと、QEMU の終了値が期待した timeout の 124 であることを要求します。marker の後の error や異常終了も成功にはしません。CI は両 mode を一回ずつ実行します。[実験記録](../experiments/2026-11-12-capdl-qemu.md)には各五回と送信なしの対照を残します。これは polling UART を使う基盤の試験で、実機の clock/pin/IRQ 初期化を備えた driver ではありません。

## 証明の範囲

seL4 17.0.0 の `ARM_bcm2837_verified` を変更しません。kernel の証明の範囲と前提は [検証済み構成](verified-configuration.md)、既存の boot patch は [差分](verified-config-deviations.md)に従います。**C capdl-loader-app の初期化のモデルレベルの Isabelle 証明は、Rust initializer に適用されません。** generator、JSON translator、add-spec、rkyv archive、initializer、driver、アプリケーションの正当性を証明したとは主張しません。QEMU の成功は実機・firmware・peripheral の確認ではありません。

## 一次資料

- [rust-sel4 の capDL source pin](https://github.com/seL4/rust-sel4/blob/c819c27b076130cba9821c4555f23773e4b0bffd/hacking/nix/scope/sources.nix)
- [fork の CLI](https://github.com/coliasgroup/capdl/blob/26b8d39c17e99e5423763e9ed292a1d123c39f56/capDL-tool/Main.hs)、[JSON translator](https://github.com/coliasgroup/capdl/blob/26b8d39c17e99e5423763e9ed292a1d123c39f56/capDL-tool/CapDL/PrintJSON.hs)、[resolver](https://github.com/coliasgroup/capdl/blob/26b8d39c17e99e5423763e9ed292a1d123c39f56/capDL-tool/stack.yaml)
- [公式 capDL の履歴](https://github.com/seL4/capdl/blob/55d2ef24aeb6de08f6bfc27ed1942eec54164a62/CHANGES.md)、[GHC 9.10.3 release notes](https://downloads.haskell.org/~ghc/9.10.3/docs/users_guide/9.10.3-notes.html)、[Stack 3.7.1 changelog](https://github.com/commercialhaskell/stack/blob/v3.7.1/ChangeLog.md)
- [seL4 の証明対象構成](https://docs.sel4.systems/projects/sel4/verified-configurations.html)

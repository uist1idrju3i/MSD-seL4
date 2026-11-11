# CI の構成と、動かす条件の判断

[索引へ戻る](README.md)

2026-11-11 の調査と変更の記録です。workflow の正本は `.github/workflows/` です。

## workflow と動かす条件

| workflow | job | 動かす条件 | 理由 |
|---|---|---|---|
| agent-docs | `check` | すべての PR と push | 文書の検査（リンク、JIS X 0213、大きさ、スキル、固定値）。文書だけの PR でも要る |
| CodeQL | `Analyze (actions)`、`Analyze (python)` | すべての PR と push、週次 | `main` の ruleset の code scanning の rule が、PR の CodeQL の結果を待つ |
| Build | `changes`、`kernel-verified`、`publish-dev-image`、`build-result` | `changes` が `.github/workflows/build.yml`、`.gitmodules`、`vendor/**`、`docker/**`、`tools/**`、`projects/**`、`patches/**`、`tests/msd-sel4-dev/**` の変更を見つけたとき。週次 | kernel の build、C と Rust の QEMU smoke test、image の CVE 検査（Trivy）。週次で CVE の検査を続ける |
| Lint | `changes`、4 つの lint、`lint-result` | workflow、shell script、`docker/**`、`tools/**`、`tests/**` などの変更 | actionlint、zizmor、shellcheck、hadolint |
| Site | `changes`、`build`、`site-result` | `docs/**`、`site.yml`、`check-site.py`、`tests/check-site/**` の変更 | Jekyll の build と公開サイトの検査 |
| pins-check | `check` | 週次と手動 | 固定値の更新の確認 |

`changes` は `.github/scripts/changed-files.py` で、PR は `pulls/{n}/files`、push は `compare` の API から変更されたファイルを取ります。schedule、手動、新しい branch、API の上限に届いた場合は、常に動かします。

## 判断の経緯

1. 【実測】research だけの PR（#21）で、Build（約 2.5 分）、CodeQL の 2 job（約 1 分）、Lint の 4 job、Site が毎回動いていた。
2. #22 で workflow に `paths` を付けた。required status checks が空だったので、merge を止めないと判断した。
3. 【失敗】`main` の ruleset には、required status checks とは別に code scanning の rule（CodeQL、alert の閾値 errors、security alert は high 以上）があった。research だけの #23 で CodeQL が動かず、merge できなくなった。#22 では ruleset の rule を全部確かめていなかった。#24 で CodeQL を常に動かすよう戻した。
4. `paths` で workflow ごと動かさないと、required status checks に指定した check が「待ち」のままになる。#26 で `changes` と `*-result` の job に変え、skip は成功として扱うようにした。
5. 【失敗】#26 の試験の例の path（`docs/index.md`）が、文書のリンク検査で古い path と見なされ、agent-docs が失敗したまま merge された。#27 で直した。当時は required status checks が空で、失敗した PR を merge できた。
6. 利用者が required status checks に `check`、`build-result`、`lint-result`、`site-result`、`Analyze (actions)`、`Analyze (python)` を設定した。【実測】research だけの #30 で、7 つの job が skip、必須の 6 つが成功、`mergeable_state` は `clean` だった。

## 守ること

- workflow の動かす条件を変える前に、`gh api repos/<owner>/<repo>/rulesets/<id>` で ruleset の rule を全部（required status checks、code scanning など）確かめる。
- 必須の check の名前は変えない。新しい job を加えたら、その workflow の `*-result` の `needs` に入れる。
- 動かす条件の glob を変えたら、`tests/changed-files/run.sh` に例を加える。

## 開発用 image の中身

2026-11-11 に、使っていない道具を外しました（#28）。外す前に、各道具を使う script と build を調べ、外した image で kernel の build、C と Rust の smoke test、UID の試験を実行しました。

| 道具 | 判断 | 根拠 |
|---|---|---|
| 安定版の Rust 1.99.1 と target | 外した | どの build も使っていない。rust-sel4 は自分の nightly を使う |
| curl、xz-utils、明示の bash | 外した | 使う script がない。bash は base image にある |
| `file` | 残した | 外すと `tools/build-verified-kernel.sh` が失敗した |
| `g++-arm-linux-gnueabi` | 残した | 外すと `seL4_tools` の `base.cmake` の `enable_language(CXX)` で CMake が失敗した |
| rust-sel4 の nightly、`rust-src`、`llvm-tools-preview`、libclang | 加えた | Rust の root task の build |

image の大きさは、安定版を持っていた image（nightly 追加後）が 4,397,823,631 byte、#28 の image が 3,352,975,518 byte でした（手元の `docker image inspect`）。

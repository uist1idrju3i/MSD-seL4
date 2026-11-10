# AGENTS.md

Devin / Codex / Claude Code など、このリポジトリで作業するすべての AI エージェントと人間が守るルールです。

## 1. main ブランチ

- GitHub のルールセットにより、`main` への直接 push、force push、削除、PR なしのマージは拒否されます。
- `<agent>/<short>` ブランチで作業し、PR を作成します。
- ルールセットは承認 0 件でのマージを許可するため、エージェントは PR をマージしません。
- ルールセットやブランチ保護を変更しません。
- tag の作成と Release の公開は利用者が行います。エージェントは行いません。
- 作業前に `git branch --show-current` を確認し、`main` では作業しません。
- 誤って `main` にコミットした場合は push も reset もせず、新しいブランチに移して報告します。

## 2. 言語と書式

- ドキュメント、Issue、Pull Request のタイトルと本文、コミットメッセージは日本語で書きます。
- コード、識別子、ファイル名は英語のままにします。ソースコード中のコメントは英語で書きます。
- 日本語の文章を書いたら、推敲スキル「yomiyasu」で読みやすさを整えてください（§6）。
- 追跡しているテキストファイルの文字は JIS X 0213:2004 の範囲に収めます。範囲外の文字は upstream 由来のファイルと原文の引用にだけ認めます。手順は「jisx0213-text」スキルに従います。
- 文書は目的と読者で分け、一つのファイルが大きくなりすぎないようにします。UTF-8 で 20,000 バイトを超えたら分割を検討し、40,000 バイトを超えたら分割するか、理由付きの例外にします。手順は「document-structure」スキルに従います。
- `docs/` は GitHub Pages で公開するサイト専用です。内部文書（調査、設計、実験記録）は `research/` に置きます。

## 3. 外部リポジトリ（vendor/）

- `vendor/` の外部コードは shallow submodule として管理し、ファイルを直接編集しません。`.gitmodules` の `shallow = true` を維持します。
- submodule やほかの依存を追加・更新するときは「vendor-update」スキルに従います。
- 上流への Issue・PR・push・コメントは人間の承認を得てから行います。

## 4. ライセンス

- 本リポジトリのコードと文書は BSD-3-Clause です（[LICENSE](LICENSE)）。新しいソースファイルの先頭に `SPDX-License-Identifier: BSD-3-Clause` を書きます。
- seL4 kernel（GPL-2.0-only）は改変せず、別のバイナリとして組み合わせます。`libsel4`、Microkit、sDDF などの BSD-2-Clause のコードを取り込むときは、元の著作権表示とライセンスを残します。
- Linux kernel、m5stack-linux-dtoverlays など GPL のコードは、ハードウェアの仕様を読む資料として参照するだけにし、本リポジトリへ写しません。GPL のコードを移植する必要が出たら、作業の前に利用者の判断を得ます。

## 5. エージェントスキル

- リポジトリ固有のスキルは `.agents/skills/<name>/` に置きます。vendor 内のスキルはコピーせず、`.agents/skills/<name>` からのシンボリックリンクにします。
- Claude Code は `.claude/skills/` しか読まないため、`.claude/skills/<name>` → `../../.agents/skills/<name>` のリンクも必ず作ります。スキルを追加・改名・削除したら、リンクも同じ PR で直します。Windows で clone するときは、シンボリックリンクを有効にします（`git config core.symlinks true` と、開発者モードか管理者権限）。
- 個人用の設定はコミットしません（`CLAUDE.local.md`、`.claude/settings.local.json`、`AGENTS.override.md` は gitignore 済み）。

| スキル | 使う場面 |
|---|---|
| `yomiyasu` | 日本語文書の推敲（`vendor/yomiyasu` へのリンク） |
| `jisx0213-text` | 範囲外の文字の置き換え、引用と upstream ファイルの例外 |
| `document-structure` | 文書の分割、公開サイト `docs/` と内部文書 `research/` の区別、索引とリンクの照合 |
| `vendor-update` | 依存関係の全版の変更点（新機能の活用を含む）、採否、ライセンス、回帰の確認 |
| `component-options` | 部品の採用・置換の前の、代替品・build option・実行時設定の調査と網羅の照合 |
| `experiment-record` | 実験・測定・比較の計画、実行、再現できる記録 |
| `release-versioning` | 公開版、CHANGELOG の更新と検査 |
| `site-review` | 公開サイト `docs/` の見え方（テキストブラウザー、小さな画面、明暗）の確認 |
| `sel4-verified-config` | seL4 kernel の構成、検証済み構成からの差分、証明の範囲の確認 |
| `sel4-capability-design` | 保護ドメインの分割、capability・共有メモリ・割り込み・device の割り当てと検査 |
| `sel4-driver` | ユーザー空間の driver ごとの調査、計画、実装、検証 |

## 6. yomiyasu（日本語推敲スキル）

`vendor/yomiyasu` にある、AI が生成した日本語を読みやすく整えるスキルです。意味と条件を保ったまま、不自然な比喩、曖昧な主述関係、不要な装飾を直します。

- 呼び出し方: `/yomiyasu`、`$yomiyasu:yomiyasu`（Codex 系）、`yomiyasu:yomiyasu`（Claude Code）。依頼の文に「yomiyasu で」と書いても呼べます。
- 用途: 日本語のドキュメントや Issue・PR の説明文の推敲。
- 検査ツールは Python の標準ライブラリだけで動き、外部へ通信しません。
  - `python3 .agents/skills/yomiyasu/scripts/yomiyasu_lint.py <file>`: AI の文章に多い表現の候補を出します。
  - `python3 .agents/skills/yomiyasu/scripts/yomiyasu_check.py run --source <原文> --final <最終稿>`: 推敲の前後を比べ、数値・否定・主述が変わっていないかを確かめます。記録は git 最上位の `.yomiyasu/` に残ります（gitignore 済み）。
- 自動フックの `yomiyasu_hook.py` は各開発者の個人設定でだけ有効化し、リポジトリにはコミットしません。

## 7. 作業の進め方

- 自明でない作業は調査して深い計画を立ててから着手します。計画はリポジトリにコミットせず、チャットで共有します。
- 部品（kernel、userland の基盤、library、toolchain、CI tool）を採用・追加・置換する前に、代替品、build option、実行時の設定項目を一次資料で全部調べ、採否と理由を表にします。手順は「component-options」スキルに従います。
- 実験・測定・比較を行うときは「experiment-record」スキルに従い、条件、手順、生の値、結論、失敗した試行を `research/experiments/` に残します。結果を PR 本文だけに書きません。
- 調査では、現在の決定、当時の判断、一次資料、実測、推測、未確認を分けます。引用・生データ・失敗記録を、新しい検査に通すために書き換えません。
- 文書の根拠に、VM や個人環境のパスを書きません。リポジトリ内のファイル、CI の成果物、公開 URL を示します。
- 変更は小さく、主題ごとにまとめます。利用者に影響する変更は、同じ PR で [CHANGELOG.md](CHANGELOG.md) の Unreleased を更新します。
- 検証結果は、実行した commit、入力とバイナリ、変更した写しの範囲を示します。確認していないことを確認済みと書きません。
- 完了報告では、依頼と計画の各項目を変更・検証・未確認に照らし合わせます。CI の合否とログを確認し、未実施の試験を実施済みとは書きません。
- GitHub の stacked PR は、同一リポジトリ内で PR を積み重ね、先行 PR の変更を後続ブランチに含める運用です。各 PR の base は利用者が設定し、エージェントは指示なしに base を変更したり、PR を merge したりしません。

## 8. seL4 の規則

- 製品の kernel は、seL4 の検証済み構成 `ARM_bcm2837_verified`（AArch32、EL1、単一コア、FPU の context switch なし、MCS なし）を既定とします。CMake の設定をこの構成から変えるときは、理由、証明への影響、戻す条件を [検証済み構成からの差分](research/sel4/verified-config-deviations.md) に書き、利用者の判断を得てから入れます。手順は「sel4-verified-config」スキルに従います。
- `vendor/seL4` の kernel は改変しません。platform の設定（DTS の overlay、memory の範囲など）は、vendor を編集せずに渡す方法を使います。
- 証明の範囲を正確に書きます。kernel の証明は、kernel の起動処理、SMMU/IOMMU、debug・printing、ハードウェア、firmware、boot loader、ユーザー空間の driver とアプリケーションを含みません。「seL4 を使っているので安全」「検証済みのシステム」とは書きません。
- システムは保護ドメインに分け、各部品に必要な capability だけを静的に渡します。実行時に権限を増やす部品を作りません。部品の分割と capability の表は「sel4-capability-design」スキルに従います。
- device の driver はユーザー空間の独立した保護ドメインとして自作します。driver ごとに深い調査と深い計画を立て、利用者の確認を得てから実装します。手順は「sel4-driver」スキルに従います。
- DMA を使う device は IOMMU で制限できないため、その driver を「全メモリに書ける部品」として扱い、capability の表に明記します。
- 証明、QEMU、実機の確認を区別します。QEMU の起動成功を、LCD・キーボード・I2C・SPI・音声・カメラ・無線・USB・HDMI・GPU firmware の tryboot・実機の電源断の検証と扱いません。

## 9. リリースと版

- 公開版は SemVer 2.0.0 を使い、tag は `v<MAJOR>.<MINOR>.<PATCH>`（pre-release は `-rc.N`）にします。build metadata は付けません。
- `0.y.z` の互換性を壊す変更は MINOR を上げます。
- tag と Release は利用者だけが作成します。エージェントは CHANGELOG の PR だけを作ります。
- 詳細は「release-versioning」スキルを参照してください。

## 10. 確認コマンド

```sh
git submodule update --init --depth 1   # submodule の取得
docker/msd-sel4-dev build                # 共通の開発環境の image を作る
docker/msd-sel4-dev tools/build-verified-kernel.sh  # 検証済み構成の kernel を build し、構成を照合
python3 .github/scripts/check-skills.py  # 指示とスキルの一覧・名前・リンクを検査
python3 -m unittest discover -s tests/check-skills  # スキル検査のテスト
python3 .agents/skills/yomiyasu/scripts/yomiyasu_lint.py <file>  # 日本語文書の候補検査
python3 -m json.tool .devin/wiki.json >/dev/null  # DeepWiki 設定の JSON 検査
git diff --check                        # 空白エラーの検査
```

変更した対象の検査を実行します。コマンドが成功することと、意味・見え方・実機動作の確認は区別します。

## 11. 製品の規則

- 利用者が操作していない時や、progress を表示していない時には、永続 storage（microSD）へ書き込みません。log、cache、一時的なデータは RAM に置きます。例外は、理由と時機を付けて記録します。
- 2 秒以上かかり得る処理（format、更新、破損の検査など）では、進み具合と、中断してよいかどうかを画面に表示します。
- 製品の画面に出す利用者向けの文言は、英語と日本語を併記します。

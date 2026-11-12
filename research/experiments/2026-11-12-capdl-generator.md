<!-- SPDX-License-Identifier: BSD-3-Clause -->
# TOML generator と独立 checker の試験

[一覧へ戻る](README.md) / [仕様](../sel4/capdl-generator.md)

## 目的・基準・未確認

目的は、TOML の grant から capDL を生成し、parser の出力に余分な authority がないことを別の処理で検査できるかを確かめることです。実装前に定めた採否の基準は、通常・空入力の成功、全拒否条件の試験の成功、五回の出力一致、必須の四種類（追加・削除・rights・badge）の mutation の検出漏れ 0 件です。

構築可否の unit test は各一回、決定性は同じ入力で五回です。時間の比較や性能の測定はしません。QEMU、実機、二つの実 component の boot、情報流の証明は未実施です。入力 ELF は試験コードが作る ARM32 ET_EXEC の fixture で、製品の component ではありません。

## 条件

基準は PR 1 の commit `3ae098d9e3560ecea37e1501b51d5cb09ade197d`。PR 2 の作業 tree で、以下の入力・実装を使いました。host は Linux x86_64 / Python 3.12.16、開発 image は `inputs-036a7993dd036120` / Python 3.13.5 です。image は PR 1 のものを再利用し、Dockerfile・compiler・kernel・vendor を変更していません。

| 入力・実装 | SHA-256 |
|---|---|
| projects/capdl/system.toml | `0e2b26f6fafefeb8b45ca147561dc237d357ed36f6d36077f7081528ce2e8070` |
| tools/capdl/schema.py | `a2ada3a1da1c39028553db23d5d28be3a1bc78ca16f9a6f70f428cdbe4fe8698` |
| tools/capdl/elf.py | `dab8bad5bedb2a25a7d48cc6cf8b1c9eff86450631b861470487fe1012382c9b` |
| tools/capdl/generate.py | `4b81d68bfcc4e1f566eea2ef4b39f2dc8e5134188bad176b5b2178756159913a` |
| tools/capdl/check.py（最終） | `7b779c33552ca379e65a8c9786bbaa5d6288d2eac1105eec38244f8a7205f208` |
| tools/capdl/report.py | `64e151fbb3ea630c7ee6096c8acfe9e428918fe19aa9e5d2d16e3badc8395ba0` |
| tests/capdl/test_generator.py（最終、ELF の生成手順を含む） | `0ba4df9fb7b6d57057e083fe9eadbe611b9e23d6e0252a5ab952e55a107cd10d` |
| parse-capDL（coliasgroup/capdl 26b8d39、strip 済み） | `f70d18bb1c37bd4aaa5e0d9d2c5ea90c37cf1b5e3cacf7a47945cde68aba2cf1` |
| 生成した serial-client-capabilities.md | `5bd3ec627574bf9a2413f57e73dc8e3d2ac9aee1f716450f0c31633472eccc49` |

## コマンドと結果

```sh
tests/capdl/run.sh
docker/msd-sel4-dev env MSD_CAPDL_PARSER_TESTS=1 \
  python3 -m unittest discover -s tests/capdl -k Parser -v
```

```text
Ran 26 tests in 0.144s
OK (skipped=6)
capdl-check: table matches (no capDL checked)

Ran 6 tests in 0.468s
OK
```

最終版では host の 20 件が成功し、parser を必要とする 6 件は明示的に skip しました。container ではその 6 件が成功しています。fixture は一つの code PT_LOAD と、page の途中から始まり BSS を含む data PT_LOAD を持ちます。file offset 0x2004 の 8 bytes を virtual offset 4 に fill し、後の BSS page には file fill を作らないことを検査します。通常例のほか、空 CSpace、notification、二ページの共有 region、fault endpoint、DMA marker の構造も parser JSON と照合しました。共有 region は serial が read/write、client が read だけを持つ例です。

負の対照として、生成後の `.cdl` にだけ 8 種類の変更を加えました。TOML と表は変えず、parser 自体が読めることと checker が拒否することを両方 assert しています。必須の四種類に加え、他 PD の CSpace、TCB cap、device の物理アドレス、VSpace にだけ加えた余分な cap を拒否しました。検出漏れは 0 件です。

全行を確認した [CSV](2026-11-12-capdl-generator.csv) に集計を残します。各 host trial の決定性 test は五回の同一条件での byte 一致であり、任意の入力に対する決定性の証明ではありません。

### 失敗した試行と修正

初回 v1 は host 20 件と parser 4 件で成功しました。レビュー後の v2 では page-table level の照合を加え、leaf の `pt` を `pd` に変える負の対照も追加しました。この変更は checker より前に parser が拒否するため、「parser は成功する」という試験の assert が一件失敗しました。

```text
parse-capDL: Failed to check model
Ran 4 tests in 0.442s
FAILED (failures=1)
```

最終 v3 は、元の 8 種類の mutation に対する「parser 成功・checker 拒否」の assert を変えず、不正な page-table 型を parser が拒否する試験を別にしました。checker の level 検査自体には、正常な JSON の root/leaf level を変える二つの負の対照を追加しました。これらの追加二試験も成功しています。失敗した v2 のログは残し、成功例に混ぜません。

v1 の checker の SHA-256 は `00183456c78ad696ecacdf12ffe1ddff5cb709969deaf61928697836589cd6a2`、test source は `b614d5578681e1b673ab0419222eb03998a4f864c23961f6341d9d67154e7dee` でした。v2 の checker は最終版と同じで、test source は `1891224e70edeb9eb4b149098bef4740d94b830d36433519be7331a76b755234` です。

## ログ

ログは gitignored の `build/capdl-deps/` に置きます。上のコマンドから再生成できます。unit test の一時 ELF は `test_generator.py` の `image()` から作り、test 終了時に片付けます。

| file | SHA-256 |
|---|---|
| generator-host-tests.log | `e13227e0f633c8eac1c66ecf98766663a7b07a0bb5f14d6e466d5976d07aa22a` |
| generator-parser-tests.log | `16a5a0205de63f05c0b2c5b371d5284eb78fd9946d1e752224fc490c070724d6` |
| generator-host-v2-tests.log | `f794abc7db5a86b1dc270376c9aa8227b12b21e8991056d9e7b5a0679c6049ec` |
| generator-parser-v2-tests.log（失敗） | `e1e08c178622c7908c9c167d46a8af885a38158472c5ee4d986bf0b7220b4645` |
| generator-host-v3-tests.log | `e6202bedf6816ded9e8f839ad1e58ad052a966aa9ba9a465a5d2a80a3628b489` |
| generator-parser-v3-tests.log | `46bf162fdc1070d0ab843c6c39796edaed4df0b57f9e05ec3a3ab570e4c75773` |

## 結論

採否の基準を満たしました。生成した `.cdl` を pinned parse-capDL が JSON に変換し、checker が宣言と一致する CSpace・VSpace を確認できました。全 static object と内部 object の集合も照合します。ただし schema・ELF reader は二つの tool が共有しており、その共通部分の誤りや kernel の実際の所有権を独立に証明してはいません。PR 3 では実 component と kernel の生成値を使い、printing 無効の確認と boot を別に試験する必要があります。

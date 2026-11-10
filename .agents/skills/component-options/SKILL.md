---
name: component-options
description: 部品（seL4 の userland の基盤、library、toolchain、CI tool）の採用・追加・置換や、更新で新しい option が加わったときの調査に使う。
---

# component-options（部品の選定と option の調査）

部品を採用・追加・置換する前に、代替品、build option、実行時の設定項目を一次資料で全部調べ、採否と理由を表にします。部品の更新で新しい option、設定項目、既定値の変更が見つかったときも使います。

## 手順

1. 対象と制約を決めます。 部品の役割、固定版、製品の要件を記録します。seL4 の検証済み構成（AGENTS.md §8）と、永続 storage への書き込み・progress の規則（AGENTS.md §11）に照らします。
2. 代替品を調べます。 同じ役割の候補を新しいものも含めて挙げ、自作も比べます。seL4 の userland の基盤では、少なくとも Microkit、CAmkES、capDL loader と自作の root task、rust-sel4、Pancake、sDDF、LionsOS を比べます。各候補が AArch32 と `bcm2837` に対応するか、検証された部分があるか、保守状況、ライセンス、将来計画への適合を書きます。
3. build option を調べます。 一次資料の全 option（CMake の `option()`・`config_option()`・`config_string()`、Kconfig、`configure --help` など）を記録します。seL4 kernel では `vendor/seL4` の `config.cmake` 群が定義する全 option を対象にし、検証済み構成が固定する値と、自由に選べる値を分けます。`vendor/` を編集せずに値を渡せるかも書きます。
4. 実行時の設定を調べます。 設定ファイル、起動時の引数、DTS、`config.txt`（Raspberry Pi firmware）と、その既定値を確認します。build 時の option と実行時の設定を混同しません。
5. 版の差を記録します。 固定版と上流の最新版を確認し、option の追加・廃止、既定値の変更を分けて、版番号と一次資料の URL を記します。
6. 網羅を機械で照合します。 上流の定義から option の名前を機械的に抜き出し、表の option 列と比べて漏れを 0 にします。抜き出したものではないと判断した項目だけを、理由を付けて除きます。
7. 採否と測定を記録します。 表には option、意味、既定値、固定版で使えるか、最新版での変化、MSD/seL4 での扱い、理由を書きます。未確認と推測を区別し、数値の測定は「experiment-record」スキルに従います。
8. 置き場所を決めます。 比較と option の表は `research/` の主題のディレクトリに置き、`research/README.md` の索引からたどれるようにします。

## 更新時

「vendor-update」スキルで新しい option や既定値の変更を見つけたら、採否と理由を決め、同じ PR でこの表に反映します。

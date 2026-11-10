---
layout: page
title: 開発状況
permalink: /status/
---

開発の準備段階です。

| 項目 | 状況 |
|---|---|
| seL4 kernel | 17.0.0 に起動処理の不具合を直す patch を 1 つ当て、検証済み構成 `ARM_bcm2837_verified` で build できることと、QEMU raspi3b で最小の root task が起動することを CI で確かめています。実機での起動は未確認です |
| userland の基盤 | capDL の仕様と、初期化の algorithm が証明された `capdl-loader-app` を使うことに決めました。実装は未着手です |
| driver | すべて未着手です。driver ごとに調査と計画を立ててから作ります |
| 電源断と更新 | 未着手です |

driver ごとの状況は、リポジトリの `research/drivers/README.md` にあります。

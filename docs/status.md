---
layout: page
title: 開発状況
permalink: /status/
---

開発の準備段階です。

| 項目 | 状況 |
|---|---|
| seL4 kernel | 17.0.0 を検証済み構成 `ARM_bcm2837_verified` で build できることを CI で確かめています。QEMU と実機での起動は未確認です |
| userland の基盤 | 未決定です（capDL、CAmkES、rust-sel4 などを比較します） |
| driver | すべて未着手です。driver ごとに調査と計画を立ててから作ります |
| 電源断と更新 | 未着手です |

driver ごとの状況は、リポジトリの `research/drivers/README.md` にあります。

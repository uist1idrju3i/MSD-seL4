---
layout: page
title: 開発状況
permalink: /status/
---

開発の準備段階です。実機ではまだ起動しません（2026-11）。

| 項目 | 状況 |
|---|---|
| seL4 kernel | 17.0.0 に起動処理の不具合を直す patch を 1 つ当て、検証済み構成 `ARM_bcm2837_verified` で build できることを CI で確かめています |
| root task | C と Rust（rust-sel4 v6.0.0）の最小の root task が、QEMU raspi3b で起動して UART に出力することを CI で確かめています。QEMU だけの結果です |
| userland の基盤 | capDL の仕様と、初期化の algorithm が証明された `capdl-loader-app` を使うことに決めました。実装は未着手です |
| driver | LCD、キーボード、音声、センサー、RTC、電池、microSD、USB、無線、カメラ、HDMI、拡張端子などの調査が終わりました。実装は未着手です |
| DMA | 中央の DMA controller は DMA server だけが持ち、自分で bus master になる device（USB、カメラ、VideoCore）の driver はメモリ全体に届く部品として扱う方針に決めました |
| 電源断と更新 | 未着手です |
| 実機 | 確かめていません。資料だけでは決まらない項目の確認の計画があります |

driver ごとの状況は、リポジトリの `research/drivers/README.md` にあります。

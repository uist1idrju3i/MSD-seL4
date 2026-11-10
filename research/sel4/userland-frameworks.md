# userland の基盤の比較

[索引へ戻る](../README.md)

D1 で AArch32 の検証済み構成を選んだため、userland の基盤は AArch32 と `bcm2837` に対応する必要があります。採否は、driver の計画の前に「component-options」スキルで決めます。

| 基盤 | AArch32・rpi3 | 検証された部分 | 根拠（2026-11-11 取得） |
|---|---|---|---|
| Microkit 2.4.0 | 非対応。`build_sdk.py` の `KernelArch` は AARCH64・RISCV64・X86_64 だけで、board に rpi3 はない（rpi4b、rpi5b はある） | なし（初期化の検証は capDL と別） | https://github.com/seL4/microkit 、https://docs.sel4.systems/projects/microkit/platforms.html |
| sDDF（au-ts） | timer に `bcm2835` の driver がある。MMC は imx だけ、I2C は imx・meson・opentitan で、BCM の SPI・GPIO・SDHOST・SDHCI・USB の driver はない | なし | https://github.com/au-ts/sddf の `drivers/` |
| LionsOS 0.4.0 | Microkit と sDDF の上に作る研究開発中の OS。AArch64 前提 | なし | https://lionsos.org/ |
| CAmkES | 文書と tutorial を公開中。sel4test は AArch32 の rpi3 で build できる | なし（capDL の初期化を使う） | https://docs.sel4.systems/projects/camkes/ |
| capDL loader | AArch32 で使える | 初期化のモデルレベルの機能正当性（AArch32） | https://docs.sel4.systems/projects/sel4/verified-configurations.html |
| rust-sel4 | seL4 が対応する全構成を対象とする | なし | https://docs.sel4.systems/projects/rust/supported-configurations.html |

## 推測

- 「seL4 を活かし切る」には、capDL で静的なシステムを記述し、検証済みの初期化で起動する形が最も合います。その上の部品の作り方（CAmkES、自作の小さな枠組み、Microkit の AArch32 への移植、rust-sel4）は比較が必要です。
- sDDF の設計（方向が決まった共有メモリの queue と通知、driver と virtualiser の分離）は、AArch32 でも考え方として使えます。コードを使うかどうかは移植の工数を見て決めます。

## 未確認

- CAmkES と capDL tool の現在の保守状況と、seL4 17.0.0 との組み合わせ。
- Microkit を AArch32 に移植する工数。

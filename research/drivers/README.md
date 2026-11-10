# driver の状況

[索引へ戻る](../README.md)

driver はすべて seL4 のユーザー空間に自作します。driver ごとに「sel4-driver」スキルで調査し、計画を利用者が確認してから実装します。状態は「未着手」「調査済み」「実装済み（QEMU）」「実装済み（実機確認）」のどれかです。

DMA と PIO の選び方、IOMMU がないことの影響、QEMU で確かめられる範囲は [dma-iommu.md](dma-iommu.md) にまとめています。

| driver | 依存する driver | 状態 |
|---|---|---|
| UART（mini UART、PL011） | GPIO、clock | 未着手 |
| GPIO | - | 未着手 |
| mailbox（firmware との通信） | - | 未着手 |
| I2C（BSC） | GPIO | 未着手 |
| SPI | GPIO、DMA | 未着手 |
| DMA controller | - | 未着手 |
| microSD（SDHOST / SDHCI） | GPIO、DMA | 未着手 |
| LCD（ST7789V） | SPI、GPIO、M5IOE1 | 未着手 |
| キーボード（TCA8418） | I2C、GPIO | 未着手 |
| IO expander（M5IOE1） | I2C | 未着手 |
| 音声（ES8389、I2S、アンプ） | I2C、I2S、GPIO、DMA | 未着手 |
| IMU（BMI270、BMM150） | I2C | 未着手 |
| RTC（RX8130） | I2C | 未着手 |
| 電池（BQ27220） | I2C | 未着手 |
| 電源異常（GPIO6） | GPIO | 未着手 |
| IR | GPIO、PWM | 未着手 |
| USB（DWC2）と hub | DMA | 未着手 |
| USB Ethernet（SR9900A） | USB | 未着手 |
| Wi-Fi・Bluetooth | SDIO、UART | 未着手 |
| カメラ（CSI、IMX219） | I2C、mailbox | 未着手 |
| HDMI | mailbox | 未着手 |

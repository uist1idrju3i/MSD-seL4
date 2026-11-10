# CardputerZero の device

[索引へ戻る](../README.md)

出典は MSD/Linux の調査（[hardware-spec.md](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/docs/research/hardware/hardware-spec.md)、[hardware-components.csv](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/docs/research/hardware/hardware-components.csv)）と `vendor/m5stack-linux-dtoverlays` です。MSD/Linux でも多くの項目は実機で未確認です。driver を作る前に、driver ごとの調査で配線と手順を確かめ直します。

| 機能 | 部品 | 接続（MSD/Linux の調査による） |
|---|---|---|
| SoC | Raspberry Pi CM0（BCM2837、Cortex-A53 ×4、RAM 512 MB） | microSD 起動 |
| LCD | ST7789V | SPI |
| キーボード | TCA8418（46 キー） | I2C1 0x34、割り込み GPIO27 |
| 音声 | ES8389 codec、AW8737A アンプ | I2C 0x10、I2S（GPIO18〜21）、アンプ GPIO24 |
| IMU | BMI270 + BMM150 | I2C 0x68（BMM150 は BMI270 の aux） |
| RTC | RX8130 | I2C 0x32 |
| 電池 | BQ27220 燃料計、IP2315 充電器 | I2C 0x55 |
| IO expander | M5IOE1 | I2C 0x4f（backlight の PWM、reset など） |
| 電源異常 | - | GPIO6 |
| IR | XL-IRM-V838M3 受信、送信 LED | 受信 GPIO13、送信 GPIO12 |
| カメラ | IMX219 | CSI |
| Wi-Fi・Bluetooth | CM0 の無線 | SDIO と UART |
| USB | GL852G hub、SR9900A USB Ethernet | USB（DWC2） |
| HDMI | - | VC4 |
| 拡張 | Grove、HAT、GPIO、I2C、SPI、UART | - |

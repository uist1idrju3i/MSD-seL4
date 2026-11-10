# driver の状況

[索引へ戻る](../README.md)

driver はすべて seL4 のユーザー空間に自作します。driver ごとに「sel4-driver」スキルで調査し、計画を利用者が確認してから実装します。状態は「未着手」「調査済み」「実装済み（QEMU）」「実装済み（実機確認）」のどれかです。

DMA と PIO の選び方、IOMMU がないことの影響、QEMU で確かめられる範囲は [dma-iommu.md](dma-iommu.md) にまとめています。

| driver | 依存する driver | 調査 | 状態 |
|---|---|---|---|
| GPIO | - | [soc-blocks.md](soc-blocks.md) | 調査済み |
| UART（mini UART、PL011） | GPIO、clock | [soc-blocks.md](soc-blocks.md) | 調査済み |
| mailbox（firmware との通信） | - | [soc-blocks.md](soc-blocks.md) | 調査済み |
| I2C（BSC） | GPIO | [soc-blocks.md](soc-blocks.md) | 調査済み |
| SPI | GPIO、DMA | [soc-blocks.md](soc-blocks.md) | 調査済み |
| DMA controller（DMA server） | - | [soc-blocks.md](soc-blocks.md)、[dma-iommu.md](dma-iommu.md) | 調査済み |
| PWM と clock | mailbox | [soc-blocks.md](soc-blocks.md) | 調査済み |
| IO expander（M5IOE1） | I2C、GPIO | [m5ioe1.md](m5ioe1.md) | 調査済み |
| キーボード（TCA8418） | I2C、GPIO、M5IOE1 | [keyboard-tca8418.md](keyboard-tca8418.md) | 調査済み |
| LCD（ST7789V） | SPI、GPIO、M5IOE1、DMA | [lcd-st7789v.md](lcd-st7789v.md) | 調査済み |
| 電源異常（GPIO6）と電源の保持 | GPIO、M5IOE1 | [powerfail-gpio6.md](powerfail-gpio6.md) | 調査済み |
| RTC（RX8130） | I2C | [rtc-rx8130.md](rtc-rx8130.md) | 調査済み |
| 電池（BQ27220、IP2315） | I2C | [battery-bq27220.md](battery-bq27220.md) | 調査済み |
| microSD（SDHOST、EMMC） | GPIO、DMA | [storage-sd.md](storage-sd.md) | 調査済み |
| USB（DWC2）、hub、Ethernet（SR9900A） | M5IOE1、mailbox | [usb-dwc2.md](usb-dwc2.md) | 調査済み |
| 音声（ES8389、PCM・I2S、アンプ） | I2C、GPIO、M5IOE1、clock、DMA | [audio-es8389.md](audio-es8389.md) | 調査済み |
| IMU（BMI270、BMM150） | I2C | [imu-bmi270-bmm150.md](imu-bmi270-bmm150.md) | 調査済み |
| IR | GPIO、PWM、clock | [ir.md](ir.md) | 調査済み |
| HDMI | mailbox | [hdmi.md](hdmi.md) | 調査済み |
| Wi-Fi・Bluetooth（CYW43439） | SDIO（EMMC）、UART、GPIO | [wireless.md](wireless.md) | 調査済み |
| カメラ（Unicam、IMX219） | I2C、mailbox | [camera-imx219.md](camera-imx219.md) | 調査済み |
| 拡張端子（Grove、HAT） | GPIO、I2C、SPI、UART、M5IOE1 | [expansion.md](expansion.md) | 調査済み |

「調査済み」は、一次資料を読んで device、依存、権限、設計の案、試験の範囲を書いたという意味です。実機で確かめたことは 1 つもありません。各 driver の実装の前に、計画を利用者に送って確認を得ます。

## 調査で分かった、全体に関わること

- mailbox（`0x3F00B880`）は、kernel が使う割り込み controller（`0x3F00B200`）と同じ 4 KiB page にあり、この page は device untyped として userland に渡ります。mailbox の driver は割り込みの mask を変えられるので、TCB に近い部品として小さく作ります（[soc-blocks.md](soc-blocks.md)）。
- I2C の BSC0・BSC1・BSC2 は 1 つの割り込みを共有し、mini UART・SPI1・SPI2 は page と割り込みを共有します。それぞれ 1 つの部品にまとめます。
- 内部の 6 つの I2C の device は BSC1 の 1 本の bus にあります。I2C の部品は、client ごとに使える address を許可表で限ります。
- M5IOE1 は電源の保持、共有の reset（キーボードと USB hub）、LCD の reset と backlight、拡張端子の電源を 1 つで制御します。M5IOE1 の部品は、client ごとに使える pin と操作を許可表で限ります。register の仕様は M5Stack の GPL の driver にしかありません。
- QEMU の raspi3b で試せるのは、SoC 側の手順（GPIO、I2C、SPI の PIO、SDHOST の PIO、DWC2 の DMA mode、mailbox の一部）だけです。CardputerZero の device（TCA8418、ST7789V、M5IOE1、ES8389 など）は QEMU にありません。

## 作る順序の案（利用者の判断）

依存の少ないものと、ほかの driver の試験に要るものから作ります。

1. GPIO、PL011 UART（debug の出力）
2. I2C、M5IOE1
3. キーボード、LCD（PIO）、電源異常
4. RTC、電池
5. mailbox、DMA server
6. microSD と storage の部品
7. USB の host controller、hub、Ethernet
8. 音声、IMU、IR
9. HDMI（firmware の frame buffer）
10. Wi-Fi・Bluetooth、カメラ

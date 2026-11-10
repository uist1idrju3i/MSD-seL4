# 拡張端子（Grove、HAT、EXT）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md) / [M5IOE1](m5ioe1.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 端子 | 信号と切り替え | 電源 | 出典 |
|---|---|---|---|
| Grove（HY2.0-4P） | GPIO4 が LOW なら UART（GPIO14・15）、HIGH なら I2C1（GPIO2・3）。R184 100k で pull-down、既定は UART | M5IOE1 の PYG4 → U35。500 mA 未満 | 製品ページ、回路図 p.10 |
| HAT（2.54 mm、14 pin） | SPI0（GPIO10・11・7・9）、I2C1、UART（GPIO14・15）を level translator で接続。GPIO22。P0・P1 は PYG1 で GPIO26・23 と USB4 を切り替え | PYG13 → U23 EXT_5VOUT → U25 EXT_3V3。既定 off | 回路図 p.7、v5 overlay |

製品ページは、拡張の cap の hot-swap に対応しないことを明記し、抜き差しの前に本体の電源を切るよう求めています。

## 設計の検討

- 拡張の device は利用者が選ぶので、最初の版では bus（I2C、SPI、UART、GPIO）を client に貸す仕組みだけを作ります。拡張の device ごとの driver は、用途が決まってから作ります。
- 共有の bus: Grove を I2C にすると、内部の I2C1 の bus に外部の device がつながります。外部の device が bus を止める（SDA を LOW のままにする）と、キーボード、電池、M5IOE1 などの内部の device も止まります。既定は UART のままにし、I2C への切り替えは利用者の明示の設定にします。
- 拡張の client には、I2C の部品の許可表で、内部の device の address（0x10、0x32、0x34、0x4f、0x55、0x68）を使わせません。
- 電源: Grove と HAT の電源は既定で off にし、on にするときは hot-swap できないことを画面に表示します（[m5ioe1.md](m5ioe1.md)）。

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| GPIO の部品 | GPIO4（Grove の切り替え）、HAT の GPIO |
| I2C・SPI・UART の部品 | 拡張の client への貸し出し |
| M5IOE1 の部品 | PYG1、PYG4、PYG13 |

## 試験

| 範囲 | 確かめること |
|---|---|
| host | 許可表（内部の address を拒む） |
| QEMU | 各 bus の手順だけ |
| 実機 | 切り替え、電源、level translator、外部の device |

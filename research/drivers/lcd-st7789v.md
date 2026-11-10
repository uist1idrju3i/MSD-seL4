# LCD（ST7789V）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| panel | 1.9 inch、320×170、controller は ST7789V（製品ページは ST7789v3） | M5Stack の製品ページ、MSD/Linux の配線の監査 |
| 接続 | SPI0、MOSI GPIO10、CLK GPIO11、CS0 GPIO8、DC GPIO25、TE GPIO5 | 回路図 p.4・p.7、v5 overlay 444 行〜 |
| reset | M5IOE1 の PYG12 | 回路図 |
| backlight | AW9967（U9）を M5IOE1 の PWM（PYG10）で制御 | 回路図 p.4、v5 overlay 312 行 |
| 色と向き | RGB565、write-only | v5 overlay 448 行〜 |
| SPI の clock | v5 overlay の `spi-max-frequency` は 60 MHz。公式 OS の `config.txt` の fbtft は 40 MHz、fps 30、rotate 90 | v5 overlay 451 行、[config.txt](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/firmware/CardputerZero/config.txt) |

出典の M5Stack の source は GPL-2.0 で、仕様を読む資料にだけ使います。

## 初期化

M5Stack は panel の初期化の命令を [`cardputerzero,st7789v_lcd.bin`](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/st7789v-1.0/cardputerzero,st7789v_lcd.bin)（93 byte）に置いています。Linux の `panel-mipi-dbi` の形式（先頭が `MIPI DBI`、続いて「命令、引数の数、引数」の並び、命令 0 は待ち時間）です。中身を読むと、`SLPOUT`（0x11）、120 ms の待ち、`COLMOD`（0x3A、16 bit）、`MADCTL`（0x36、0xA0）、porch・gate・電源の設定、gamma（0xE0・0xE1）の順です。【一次。値の意味は ST7789V の datasheet で確かめる】

- この file の license は記載がありません。MSD/seL4 には写さず、datasheet から命令の列を自分で書きます。値が同じになるのは仕様の値だからで、写したことにはなりません。ただし、gamma の値は panel ごとの調整値なので、M5Stack に許可を確かめるか、datasheet の既定値から始めます。【利用者の判断】
- 320×170 の panel は、ST7789V の 240×320 の memory の一部を使います。表示の offset（column・row の開始位置）は panel ごとに違い、実機で確かめます。

## 依存と権限

| 依存 | 使う理由 | 部品 |
|---|---|---|
| SPI0 | 画素と命令の送信 | SPI の部品（CS0 の client） |
| GPIO | DC（GPIO25）、TE（GPIO5） | GPIO の部品 |
| M5IOE1 | reset（PYG12）、backlight の PWM（PYG10） | M5IOE1 の部品 |
| DMA server | 全画面の転送 | DMA server（[dma-iommu.md](dma-iommu.md) の決定で既定） |

LCD の driver は device のメモリを持ちません。SPI の部品へ「CS0 で、この共有 buffer の offset から長さ分を送る」と依頼し、DC は送る前に GPIO の部品に切り替えてもらいます。

## 設計の検討

- 画面の buffer: 320×170×2 = 108,800 byte。client（画面の合成の部品）と LCD の driver の間で共有メモリにし、更新した矩形を通知で知らせます。LCD の driver は、その矩形を `CASET`・`RASET`・`RAMWR` で送ります。
- 転送の速度: 40 MHz で全画面は約 22 ms、60 MHz で約 15 ms です（計算値。命令と DC の切り替えの時間を含まない）。30 fps に足りる見込みですが、PIO では転送の間 CPU を占めます。
- tearing: TE（GPIO5）の割り込みに合わせて送ると、表示の途中で画が切り替わるのを防げます。v5 overlay では TE をコメントアウトしています。まず TE なしで作り、必要なら加えます。
- 起動の画面: 電源を入れてから画面が出るまでの時間は、M5IOE1、I2C、SPI の部品の起動を待つので長くなります。起動の早い段階に出す画面は、LCD の driver が持つ固定の画像にします。
- 障害時: SPI の部品か M5IOE1 が応答しないときは、LCD の driver は表示をあきらめて client に error を返します。画面が出ないことは、AGENTS.md §11 の progress の表示ができないことを意味するので、時間のかかる処理（更新など）を始めない条件にします。

## 試験

| 範囲 | 確かめること |
|---|---|
| host | 矩形の範囲の検査、命令の列の生成 |
| QEMU | SPI0 の PIO の手順。QEMU の SPI は DMA mode を実装していない。ST7789V の応答はない |
| 実機 | 表示、色、向き、offset、backlight、転送速度と fps、TE |

## 決めること

1. 初期化の命令の列を datasheet から書き直すか、M5Stack の値を使う許可を確かめるか。推奨: datasheet の既定から始め、gamma だけ実機で合わせる。
2. 最初の版を PIO にするか、DMA server を先に作るか。推奨: DMA server は SPI・SDHOST・PCM で共通なので、LCD の driver は PIO で先に作り、DMA server ができたら切り替える。決定の既定（DMA）からの一時的な差分として記録する。

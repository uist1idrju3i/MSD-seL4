# 実機の確認の計画（CardputerZero）

[実験記録の一覧へ戻る](README.md) / [driver の状況](../drivers/README.md)

driver の調査で、資料だけでは決まらず実機での確認が要る項目をまとめました。実機での作業を 1 回でまとめて行えるよう、手順と合否の基準を先に決めておきます。これは計画で、まだ何も実施していません。実施したら、項目ごとに「experiment-record」スキルで記録を作り、この表の「記録」の列に足します。

## 準備

- 本体: CardputerZero Standard 1 台（可能なら Lite も 1 台）。基板の版（V0.6 か）を PYG2 の分圧か刻印で確かめ、記録に書きます。
- microSD: 公式 OS（M5Stack の pi-gen）と MSD/Linux の image。seL4 の image はまだ実機で起動できる段階にないため、多くの項目は Linux から確かめます。Linux で確かめた値は「Linux 上での実測」と書き、seL4 の driver の動作確認とは区別します。
- 測定器: 2 channel 以上の oscilloscope か logic analyzer（GPIO と電源の rail の時間を測る）、USB の電圧・電流 meter、I2C を読める logic analyzer。
- 安全: 拡張の cap は電源を切ってから抜き差しします（製品ページ）。電池を外す試験は、M5Stack が電池の取り外しを想定しているかを先に確かめます。

## 項目

| ID | 確かめること | 関係する文書 | 手順 | 合否の基準 | 記録 |
|---|---|---|---|---|---|
| HW-1 | 電源スイッチを切ってから CM0 の電源が落ちるまでの時間 | [電源異常](../drivers/powerfail-gpio6.md) | GPIO6、VSYS_CM0、CM0_3V3 を oscilloscope で同時に測り、スイッチを切る。10 回繰り返す | 10 回の最小値・最大値・中央値を記録できたら完了（合否ではなく値を得る項目） | - |
| HW-2 | PYG14 で電源を保持できるか、何秒保持できるか | [電源異常](../drivers/powerfail-gpio6.md)、[M5IOE1](../drivers/m5ioe1.md) | Linux から PYG14 を出力 HIGH にしてスイッチを切り、VSYS_CM0 が保たれる時間を測る。その後 PYG14 を LOW にして落ちるか確かめる | 保持の有無と時間を記録できたら完了 | - |
| HW-3 | 電池を外したときに GPIO6 が動くか | [電源異常](../drivers/powerfail-gpio6.md) | USB の給電なしで動かし、電池の接続を外す。GPIO6 と VSYS_CM0 を測る | GPIO6 が電源断より先に LOW になるか、記録できたら完了 | - |
| HW-4 | M5IOE1 の `REV`・`VERSION`・`HW_VERSION` の値と、`READY`（0xB0）を書かないときの動作 | [M5IOE1](../drivers/m5ioe1.md) | Linux の M5IOE1 の driver を外し、`i2cget` で読む。`READY` を書かずに 10 分待ち、電源や reset の変化を見る | 値を記録し、10 分の間に電源が切れないか、何が起きたかを記録できたら完了 | - |
| HW-5 | RTC が電源を切った間に時刻を保てるか | [RTC](../drivers/rtc-rx8130.md) | 時刻を合わせ、電源スイッチを切って 1 時間置く。電池あり、電池なし（USB も外す）の 2 条件 | 両条件で、時刻の差と電源断の flag（`VLF` など）を記録できたら完了 | - |
| HW-6 | BQ27220 の data memory の設計容量 | [電池](../drivers/battery-bq27220.md) | TI の TRM の手順で data memory を読む（書き込みはしない） | 設計容量の値を記録し、overlay の 1,750 mAh と比べたら完了 | - |
| HW-7 | SR9900A の USB の VID・PID | [USB](../drivers/usb-dwc2.md) | Linux で `lsusb -v` を実行する | VID・PID と、hub の port の対応を記録できたら完了 | - |
| HW-8 | USB_SW を駆動する信号と、USB の経路の既定 | [USB](../drivers/usb-dwc2.md) | 回路図で USB_SW の net を追い、Linux で切り替えて右の USB-C と hub の列挙を確かめる | 駆動元（SoC の GPIO か M5IOE1 か）と既定の経路を記録できたら完了 | - |
| HW-9 | 無線の chip の ID と firmware | [無線](../drivers/wireless.md) | CM0 の刻印を読み、Linux の `dmesg` と SDIO の ID、読み込まれた firmware の名前を記録する | chip の ID と firmware の file 名を記録できたら完了 | - |
| HW-10 | microSD と Wi-Fi の SDIO がどの controller（SDHOST、EMMC）につながるか | [microSD](../drivers/storage-sd.md)、[無線](../drivers/wireless.md) | Linux の DT（`/proc/device-tree`）と `dmesg` で、各 controller の接続先を確かめる | 対応を記録できたら完了 | - |
| HW-11 | EMMC が bus master として DMA を使うか | [dma-iommu.md](../drivers/dma-iommu.md) | Linux の `sdhci-iproc` の設定（ADMA・SDMA の有無）と、register の capability の値を読む | DMA の有無を記録できたら完了。分からなければ bus master として扱う決定を続ける | - |
| HW-12 | LCD の表示の offset、色、向き | [LCD](../drivers/lcd-st7789v.md) | 公式 OS の初期化の後、Linux から `CASET`・`RASET` を変えて既知の模様を描く | 画面の左上と右下が panel の端に合う offset を記録できたら完了 | - |
| HW-13 | キーボードの無効なキー（Z・X・C・F）の刻印と matrix | [キーボード](../drivers/keyboard-tca8418.md) | 刻印を写真で記録し、TCA8418 の event を `i2cget` で読む | 46 キーの行・列を記録できたら完了 | - |
| HW-14 | PCM の clock と MCLK の周波数 | [音声](../drivers/audio-es8389.md) | Linux で 48 kHz の再生中に、GPIO18（BCLK）、19（LRCK）、21 を測る | 周波数を記録できたら完了 | - |
| HW-15 | IR の割り込みの遅れ | [IR](../drivers/ir.md) | seL4 の GPIO の driver ができた後に行う。信号発生器の pulse と、driver が記録した時刻を比べる | 遅れの分布を記録できたら完了 | - |
| HW-16 | GPIO の boot 時の function・level と firmware の責務 | [GPIO](../drivers/gpio.md) | firmware の版、実際の config.txt、DT を保存。Linux 起動後と seL4 の GPIO 初期化前を別条件で記録し、GPIO0〜53 の GPFSEL/GPLEV と配線を照合。pull は読み戻せないので設定手順を記録。reset・電源 pin は変更しない | 各値を firmware の宣言、Linux の pinctrl、seL4 の設定と区別できること。GPIO16 を誤って camera 用に変更していないこと | - |
| HW-17 | GPIO6 の即時通知、edge/level、pull、IRQ storm | [GPIO](../drivers/gpio.md)、[電源異常](../drivers/powerfail-gpio6.md) | driver 完成後、安全な信号入力で pin ごとの GPEDS と IRQ group を照合。起動時 LOW、連続 edge、GPIO27 の LOW 保持、他 pin の storm 中の GPIO6 を測る。実際の電源断は HW-1/HW-2 の安全確認後 | pull が計画値と合い、許可外 pin を操作せず、level を解除後に再 arm できること。GPIO6 の遅延を最小・中央値・最大で記録し、事前に決めた猶予以内であること。GPEDS/通知の合流を欠落ゼロとは扱わない | - |
| HW-18 | PL011 の外部経路、BT、clock、baud | [PL011](../drivers/uart-pl011.md) | 無線の有無と BT の停止方針を確認してから14/15を設定。実際の config と UART clock query 又は静的値、divisor を保存。Grove/HAT を一つずつ loopback 接続し、logic analyzer で115200 8N1を測る | UART の pin、Grove mux、clock が計画と一致し、baud error の事前の許容値以内であること。BT や二つの外部 RX と競合しないこと | - |
| HW-19 | UART FIFO 閾値・短い RX・overrun・停止 | [PL011](../drivers/uart-pl011.md) | driver 完成後、1 byte、閾値未満、連続入力を送り RX/RT IRQ を観測。ring full、受信処理遅延、client/driver 停止、TX drain を試す。GPIO6 の経路も同時に観測 | 短い入力が届くこと。overflow/error が counter と gap に現れ、無言で成功しないこと。BUSY 待ちと client 待ちが期限で終わり、UART 障害で電源通知が止まらないこと | - |

HW-1〜HW-14 は Linux で行えます。HW-15 は seL4 の driver ができてからです。

HW-16 の Linux の値は firmware 引き継ぎ値とは別です。HW-17〜HW-19 の driver 試験は seL4 の実装後に行い、合否に必要な時間・baud error の上限を測定前に決めます。開発 image と同版の upstream QEMU 10.0.13 には GPIO の edge/pull/IRQ がなく、PL011 も IFLS の閾値、受信 timeout、baud 波形を再現しません。MSD/Linux の patch 付き QEMU の試験で代用しません。全項目は未実施です。

## 実施の順序

電源に関わる項目（HW-1〜HW-3）を先に行います。電源断の設計（storage の書き方）に影響するためです。その後、I2C で読むだけの項目（HW-4〜HW-6）、USB と無線（HW-7〜HW-11）、表示と入力（HW-12、HW-13）、音声（HW-14）の順にします。

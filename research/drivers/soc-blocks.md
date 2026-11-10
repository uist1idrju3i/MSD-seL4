# BCM2837 の共通の部品（GPIO、割り込み、mailbox、UART、I2C、SPI、DMA、PWM、clock）

[driver の状況へ戻る](README.md)

CardputerZero の各 device の driver が使う、SoC 側の部品の調査です。device ごとの調査はこの文書の部品を前提にします。2026-11-11 に調べました。実機では何も確かめていません。

## 出典

- 【一次】[BCM2835 ARM Peripherals](https://datasheets.raspberrypi.com/bcm2835/bcm2835-peripherals.pdf)。BCM2837 は同じ周辺の配置で、bus address の `0x7Exxxxxx` が ARM の物理 address の `0x3Fxxxxxx` に当たります。
- 【一次】seL4 17.0.0 の `vendor/seL4/tools/dts/rpi3.dts`（`ARM_bcm2837_verified` の build が使う device tree）。
- 【実測】`ARM_bcm2837_verified` の build が生成した `gen_headers/plat/machine/devices_gen.h`（kernel が使う device の frame と、userland から外す範囲）。
- 【一次】M5Stack の [v5 overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/CardputerZero/cardputerzero-v5-overlay.dts) と [config.txt](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/firmware/CardputerZero/config.txt)（GPL-2.0。仕様を読む資料にだけ使います）。
- 【一次】MSD/Linux の [部品と回路接続の監査](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/docs/research/hardware/hardware-wiring-audit.md)。

## 部品の address と割り込み

割り込みは `rpi3.dts` の `<bank 番号>` の形で書きます。bank 0 は ARM の basic、bank 1 は GPU の IRQ 0〜31、bank 2 は GPU の IRQ 32〜63 です。

| 部品 | ARM の物理 address（4 KiB page） | 割り込み | CardputerZero での用途 |
|---|---|---|---|
| system timer | `0x3F003000` | `<1 0>`〜`<1 3>` | timeout の基準。kernel は ARM local timer を使う |
| DMA controller（channel 0〜14） | `0x3F007000` | `<1 16>`〜`<1 28>`。channel 11〜14 は `<1 27>` を共有 | DMA server（[dma-iommu.md](dma-iommu.md)） |
| 割り込み controller と mailbox | `0x3F00B000`（controller は `+0x200`、mailbox は `+0x880`） | mailbox は `<0 1>` | kernel と mailbox の driver |
| 電源管理と watchdog | `0x3F100000` | なし | 再起動、power domain |
| clock manager（cprman） | `0x3F101000` | なし | PCM、PWM、GP clock |
| 乱数（RNG） | `0x3F104000` | `<2 29>` | 乱数の部品 |
| GPIO | `0x3F200000` | `<2 17>`〜`<2 20>` | 全 device の pin |
| PL011 UART | `0x3F201000` | `<2 25>` | Bluetooth（推測）または console |
| SDHOST | `0x3F202000` | `<2 24>` | microSD（[storage-sd.md](storage-sd.md)） |
| PCM・I2S | `0x3F203000` | `rpi3.dts` に記載なし | 音声（[audio-es8389.md](audio-es8389.md)） |
| SPI0 | `0x3F204000` | `<2 22>` | LCD、HAT の SPI |
| BSC0（I2C0） | `0x3F205000` | `<2 21>` | カメラの I2C（SDA0・SCL0） |
| PWM | `0x3F20C000` | なし | IR の送信の候補 |
| AUX（mini UART、SPI1、SPI2） | `0x3F215000` | `<1 29>` を 3 つで共有 | Grove・HAT の UART |
| EMMC（Arasan の SDHCI） | `0x3F300000` | `<2 30>` | Wi-Fi の SDIO（推測） |
| BSC1（I2C1） | `0x3F804000` | `<2 21>` | 内部の I2C の全 device |
| BSC2（I2C2） | `0x3F805000` | `<2 21>` | HDMI の DDC |
| USB（DWC2） | `0x3F980000` | `<1 9>` | USB hub と Ethernet |

## kernel と共有する page

`devices_gen.h` によると、`ARM_bcm2837_verified`（`KernelPrinting=OFF`）の kernel は次の frame を使います。

| frame | 内容 | userland から外すか |
|---|---|---|
| `0x3F215000` | mini UART（kernel の console） | `CONFIG_PRINTING` のときだけ kernel が使う。製品の構成では使わない |
| `0x3F00B000` | 割り込み controller | 外さない。DTS の `user: true` の扱いで、device untyped として userland に渡る |
| `0x40000000` | ARM local の割り込み controller | 外す（`kernel_device_reserved_regions`） |

ここから分かる大事な点です。

- mailbox（`0x3F00B880`）は、kernel の割り込み controller（`0x3F00B200`）と同じ 4 KiB page にあります。mailbox の driver に page を渡すと、その driver は割り込み controller の register も書けます。割り込みの mask を変えれば、ほかの部品の割り込みを止められます。【推測。register の効果は datasheet による】
- このため、mailbox の page は、kernel の割り込みを妨げてよい部品、つまり信頼の前提（TCB）に近い部品にだけ渡します。[dma-iommu.md](dma-iommu.md) で mailbox をすでに「全メモリに届く部品」としているので、扱いの重さは変わりません。ただし、mailbox の driver はできるだけ小さくします。
- 証明の model では、user の書き込みは割り込みの mask（`irq_masks`）を変えません。page を map した部品が割り込み controller を書くと、実機と model が食い違います。選択肢と推奨は [shared-intc-page.md](../sel4/shared-intc-page.md) にあります。

## 割り込みの共有

seL4 では 1 つの IRQ の capability を 1 つの部品が受け取ります。次の割り込みは複数の device で共有されているため、部品の分け方を制限します。

- BSC0、BSC1、BSC2 は同じ `<2 21>` です。I2C の driver を bus ごとに分ける場合でも、割り込みを受ける部品は 1 つです。案は、3 つの BSC を 1 つの I2C の部品にまとめるか、割り込みを使わない bus（HDMI の DDC）は timer で polling することです。
- mini UART、SPI1、SPI2 は同じ AUX の `<1 29>` で、register も同じ page です。この 3 つは 1 つの部品にまとめます。
- DMA の channel 11〜14 は `<1 27>` を共有します。DMA server がまとめて持つので問題になりません。
- GPIO の割り込みは bank ごとに 4 本（`<2 17>`〜`<2 20>`）です。CardputerZero で割り込みに使う pin（GPIO6、GPIO13、GPIO17、GPIO27）は、すべて bank 0（GPIO0〜27）にあり、同じ `<2 17>` に来ます。【推測。bank の割り当ては BCM2835 ARM Peripherals の GPIO の章による】GPIO の割り込みは GPIO の部品が受け、通知で各 driver に配ります。

## GPIO

- 54 本の pin の機能（`GPFSEL`）、出力（`GPSET`、`GPCLR`）、入力（`GPLEV`）、edge・level の検出（`GPEDS` など）、pull（BCM2837 は `GPPUD` と `GPPUDCLK` の手順）が 1 つの page にあります。
- page を分けられないので、GPIO の部品を 1 つ置き、各 driver には「この pin だけ」を操作する IPC の interface を渡します。pin と操作の許可表は、capDL の generator が作る静的な表にします。
- CardputerZero の割り当て（v5 overlay と回路図による）: LCD は GPIO8（CS0）・10・11・25（DC）・5（TE）、HAT の SPI は GPIO7（CS1）・9・22（GPIO の CS）、I2C1 は GPIO2・3、音声は GPIO18〜21・17（ヘッドホンの検出）・24（アンプ）、キーボードの割り込みは GPIO27、電源異常は GPIO6、IR は GPIO12（送信）・13（受信）、Grove の切り替えは GPIO4、UART は GPIO14・15、HAT の P0・P1 は GPIO26・23。
- 電源断に関わる pin（GPIO6）の割り込みが遅れないよう、GPIO の部品は優先度を高くします。

## mailbox（firmware との通信）

- VideoCore の firmware と property の message をやり取りします。clock の設定、電源の on・off、frame buffer の確保、温度などに使います。
- message の buffer は VideoCore が DMA で読み書きします。buffer の物理 address を渡すので、mailbox の driver は「全メモリに届く部品」です（[dma-iommu.md](dma-iommu.md) の決定）。
- 上で書いたとおり、page が割り込み controller と同じです。driver は property の種類を許可表で限り、ほかの部品は「clock を設定する」「電源を入れる」などの限られた操作だけを依頼できるようにします。
- QEMU の raspi3b は property の一部を実装しています。実際の firmware の応答は実機でしか確かめられません。

## UART

- PL011（`0x3F201000`）は単独の page です。CM0 の無線付きの型番では、Raspberry Pi の firmware の既定で PL011 が Bluetooth に、mini UART が GPIO14・15 に割り当てられます。【推測。`config.txt` の `dtoverlay` の組み合わせで変わり、v5 の config.txt では明示していない】
- mini UART は AUX の page と割り込みを SPI1・SPI2 と共有し、baud rate が VPU の clock に依存します。
- smoke test では PL011 を使っています（[QEMU の smoke test](../experiments/2026-11-11-qemu-smoke.md)）。

## I2C（BSC）

- 内部の device（M5IOE1 0x4f、TCA8418 0x34、ES8389 0x10、RX8130 0x32、BMI270 0x68、BQ27220 0x55）はすべて BSC1 にあります。v5 overlay の bus の速度は 100 kHz です。
- BSC の FIFO は 16 byte です。転送は割り込みか polling の PIO で、DMA は使いません（[dma-iommu.md](dma-iommu.md) の決定）。
- I2C の部品は bus を持ち、各 driver には「この address だけ」に読み書きできる interface を渡します。たとえば電池の driver はキーボードの address に書けません。
- 6 つの device の driver が 1 つの bus を共有するので、I2C の部品が止まると全部止まります。I2C の部品は小さくし、各 transaction に timeout を付けます。BCM2835 の BSC には clock stretching の不具合があると Linux のコメントや Raspberry Pi の forum で知られています。【推測。datasheet の errata では未確認】
- QEMU は BSC を実装していますが、接続先の device はありません。

## SPI0

- LCD（CS0）と HAT の SPI（CS1、GPIO22 の CS）で使います。v5 overlay は GPIO22 を gpio-forwarder 経由の 3 本目の CS にしています。
- FIFO は 64 byte で、DMA を使う場合は DMA server を通します。LCD の全画面は 108,800 byte です。
- LCD と HAT を別の部品にする場合、SPI0 の register は 1 つの page なので、SPI の部品を 1 つにして、CS ごとに client を分けます。

## DMA controller

- channel 0〜14 の register は同じ page に並び、channel 15 は `0x3FE05000` にあります。DMA server だけが持ちます（[dma-iommu.md](dma-iommu.md) の決定）。
- Raspberry Pi の firmware と VideoCore も一部の channel を使います。firmware が使う channel は、firmware が device tree の `brcm,dma-channel-mask` で知らせます。DMA server は mask にない channel を使いません。【推測。seL4 の起動の経路では Linux 用の DT を作り直さないので、mask の受け取り方を確かめる】

## PWM と clock

- PWM（`0x3F20C000`）の clock は clock manager（`0x3F101000`）の `CM_PWMCTL` で設定します。PCM の clock（`CM_PCMCTL`）も同じ page にあります。
- clock manager の page はほかの全 clock も含むので、1 つの clock の部品にまとめるか、mailbox の property で firmware に clock を設定させます。部品が少ないのは後者ですが、mailbox の driver に依存が集まります。
- CardputerZero の LCD の backlight は SoC の PWM ではなく M5IOE1 の PWM です（[m5ioe1.md](m5ioe1.md)）。

## 決めること（利用者の判断）

1. 割り込み controller と同じ page にある mailbox を、どの部品に渡すか。決定（2026-11-11）: mailbox の driver だけに渡し、割り込み controller を書かないことを driver の検証の対象にする（[shared-intc-page.md](../sel4/shared-intc-page.md) の案 A）。
2. clock を誰が設定するか。推奨: 起動の直後は firmware に任せ、変更が要る PCM の clock だけ mailbox の property で設定する。
3. I2C の BSC0・BSC1・BSC2 を 1 つの部品にまとめるか。推奨: 1 つにまとめる。割り込みが共有で、分けても隔離が強くならないため。

# BCM2837 GPIO の調査

[driver の状況](README.md) / [SoC の要約](soc-blocks.md) / [PL011](uart-pl011.md)

2026-11-12 の資料調査です。driver、TOML の拡張、IRQ の配布は未実装です。新しい QEMU 起動試験と実機試験は行っていません。「一次」は資料・source の記載、「提案」は未採用の設計、【推測】は推論を表します。

## 出典と適用範囲

- 【一次】[BCM2835 ARM Peripherals、2012-02-06](https://datasheets.raspberrypi.com/bcm2835/bcm2835-peripherals.pdf)、§6 pp.89-104、§7 pp.109-116。以下のページは印刷ページです。取得した PDF の SHA-256 は `5e446658d154c4447381ef62c1a3ce4102715e437fe488e2b93e798b60c4004e`。BCM2837 の配置は [seL4 の rpi3.dts](https://github.com/seL4/seL4/blob/62e345c240a15671484530b4e6e069ce266c28d7/tools/dts/rpi3.dts#L120-L127) と照合しました。
- 【一次】固定した M5 source `4f7aeee9fc103ebb03d22cac476bb191ecfb321e` の [v5 overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/CardputerZero/cardputerzero-v5-overlay.dts#L15-L33)、[電源 IRQ](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/CardputerZero/cardputerzero-v5-overlay.dts#L284-L296)、[config.txt](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/firmware/CardputerZero/config.txt#L6-L16)、[config_setup](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/CardputerZero/Makefile#L66-L104)。GPL の source は読解だけに使い、コードは写していません。
- 【一次資料との照合記録】MSD/Linux の [配線監査](https://github.com/uist1idrju3i/MSD-Linux/blob/530d91d6ffbc1624a7c05ffc845bd1d811f98a86/docs/research/hardware/hardware-wiring-audit.md#L61-L95)。根拠は [C154 V0.6.1 回路図](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf) pp.4-10 と [CM0 datasheet Release 3](https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf)。監査側の M5 pin は `37b42d9` で、当 repo の `4f7aeee` と同じ版とは扱いません。下表の GPIO4/6/17/24/27 は当 repo の v5 でも照合しました。物理導通は未確認です。

## register と初期化

GPIO は bus address `0x7E200000`、ARM 物理 address `0x3F200000` の 4 KiB page に収まります。全 54 pin を一つの GPIO PD が所有します。pin ごとに page を分割して隔離することはできません。

【一次】§6.1 pp.90-101 の全通常 register は次のとおりです。bank 0 は pin 0-31、bank 1 は pin 32-53 です。bank 1 の上位 10 bit、GPFSEL0-4 の上位2 bit、GPFSEL5 の上位20 bit と表にない予約領域は操作しません。`+0xB0` は Test register で、製品 driver には公開しません。

| register | offset | 動作・注意 |
|---|---|---|
| GPFSEL0-5 | 0x00,04,08,0C,10,14 | pin あたり 3 bit。input=0、output=1、ALT0=4、ALT1=5、ALT2=6、ALT3=7、ALT4=3、ALT5=2。10 pin を共有するので read-modify-write を直列化 |
| GPSET0/1 | 0x1C/20 | 書いた 1 bit の出力 latch を HIGH。read-modify-write は不要 |
| GPCLR0/1 | 0x28/2C | 書いた 1 bit を LOW。set と clear の競合は同じ pin の要求順序で決める |
| GPLEV0/1 | 0x34/38 | 入力・出力の現時点の level を読む。1=HIGH、書き込み禁止 |
| GPEDS0/1 | 0x40/44 | event の sticky bit。処理した bit にだけ 1 を書いて clear（W1C） |
| GPREN0/1 | 0x4C/50 | 同期 rising edge の検出を許可 |
| GPFEN0/1 | 0x58/5C | 同期 falling edge の検出を許可 |
| GPHEN0/1 | 0x64/68 | HIGH level の検出を許可 |
| GPLEN0/1 | 0x70/74 | LOW level の検出を許可。原因が残れば再び pending になる |
| GPAREN0/1 | 0x7C/80 | 非同期 rising edge。短い pulse も対象となり、noise に注意 |
| GPAFEN0/1 | 0x88/8C | 非同期 falling edge |
| GPPUD | 0x94 | 全 pin 共通の pull 制御。0=off、1=down、2=up、3=予約 |
| GPPUDCLK0/1 | 0x98/9C | 選択 pin に pull を取り込む clock。別 client の pull 更新も同時実行しない |

【一次】pull は §6.1 pp.100-101 の順に、GPPUD を設定、150 cycles 以上待つ、対象 pin mask を GPPUDCLK に書く、150 cycles 以上待つ、GPPUD を 0、GPPUDCLK を 0 とします。現在の pull は読めず、PD が設定の写しを持ちます。BCM2711 の別方式の pull register を使ってはいけません。

150 cycles の clock は datasheet に明記がありません。[Linux の説明と実装](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/pinctrl/bcm/pinctrl-bcm2835.c#L1076-L1101) は VPU 250 MHz を根拠に各 1 μs 待ちます。提案は timer による各 1 μs 以上の待ちで、CPU の NOP 150 回にはしません。timer の userland への配布と実際の clock 条件は未確定です。Linux は最後に clock だけを下げますが、自作版では資料の両方を解除する順序を採る案です。

【既知の資料の誤り】[eLinux errata](https://elinux.org/BCM2835_datasheet_errata) は community の二次資料であり、Broadcom の保証ではありません。p.90 の GPFSEL0 重複、p.96 の GPCLR1 の set/clear と GPLEV の HIGH=0、p.98 の GPFEN 見出し、p.101 の存在しない GPPUDCLK2 に注意します。上表は register map、固定 libplatsupport、Linux と照合した意味です。ALT の符号値と ALT の番号も別です。

### IRQ と event の扱い

【一次】rpi3.dts は `<2 17>`-`<2 20>` の 4 本を記載します。一方 datasheet pp.90,96 は「3 本」と記述しており、それだけでは group を確定できません。[Linux の handler](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/pinctrl/bcm/pinctrl-bcm2835.c#L461-L490) と [全 bank IRQ を飛ばす処理](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/pinctrl/bcm/pinctrl-bcm2835.c#L1432-L1446) を併用して区別します。

| DT IRQ | pin group | register bank |
|---|---|---|
| `<2 17>` | GPIO0-27 | bank 0 |
| `<2 18>` | GPIO28-45 | bank 0 の28-31と bank 1 の32-45 |
| `<2 19>` | GPIO46-53（BCM2837 の範囲） | bank 1 |
| `<2 20>` | 全 group の集約 | bank 0/1 |

初版の外部 pin はすべて最初の group なので、提案は GPIO PD に `<2 17>` の IRQHandler だけを静的に渡すことです。集約 IRQ を重ねて受けません。DT の `<bank bit>` は seL4 の IRQ 番号そのものではなく、生成 header と kernel の IRQ 番号への変換を実装前に照合します。

提案する起動手順は、検出許可を止める、許可 pin の残留 GPEDS を W1C、入出力・pull・初期 level を設定、IRQ notification を結び、対象の検出だけを許可、level と GPEDS を再確認してから待つ、です。GPIO6 は既に LOW なら edge がなくても通知します。出力では初期 latch を先に設定し、output に切り替える際の glitch を避けます。

IRQ 処理では GPEDS と許可 mask の積だけを処理し、GPIO6 を最初に通知します。観測した bit だけを W1C し、再読してから IRQHandler を Ack します。level IRQ は client が device の原因を解消するまで pin の検出を mask して再 arm を依頼させる案です。無制限に IRQ を回す処理にはしません。

同じ pin の edge が clear 前に重なると GPEDS は回数を保持しません。notification の badge も合流します。したがって「各 edge を欠落なく数える」API とはしません。software の event sequence、最新 level、overflow flag を返し、IR の pulse 計測を保証するには別途 sampling・時間精度の検討が要ります。GPFSEL と検出許可の read-modify-write、共通 GPPUD は一つの thread で直列化します。GPSET/GPCLR は別 pin の更新を壊しませんが、複数 write の同時性は保証しません。

## CardputerZero の pin 許可表の入力案

次は SoC 番号です。M5IOE1 の PYG 番号とは別です。owner は提案する論理的所有者で、MMIO を持つのは常に GPIO PD だけです。pull の「既定」は SoC reset 時の表6-31 pp.102-103、「外部」は配線監査、「v5」は Linux 用 pinctrl の指定です。seL4 起動時の実測ではありません。「未定」は実機・回路条件を確認して TOML で固定する項目です。

| GPIO | owner / 接続 | 方向・function 案 | pull の根拠 / 案 | event 案 |
|---|---|---|---|---|
| 0,1 | 予約、CM0 の ID_SDA/SCL | client 操作不可 | 既定 up、外部配線未確認 | なし |
| 2,3 | I2C1 | 双方向 ALT0 SDA/SCL | 外部 2.2k up、内部 off 案 | なし |
| 4 | 拡張 mux / Grove | output GPIO、LOW=UART | 外部 100k down、v5 off | なし |
| 5 | LCD TE | input GPIO | 既定 up、最終値未定 | rising 候補、未確認 |
| 6 | 電源異常 / SW_DET | input GPIO | 分圧、既定 up。内部値未定 | falling、起動時 LOW も通知 |
| 7 | SPI0 / HAT CS1 | output ALT0 CE1 又は GPIO CS | 既定 up、非選択 HIGH 案 | なし |
| 8 | SPI0 / LCD CS0 | output ALT0 CE0 又は GPIO CS | 既定 up、非選択 HIGH 案 | なし |
| 9 | SPI0 / HAT MISO | input ALT0 | 既定 down、内部値未定 | なし |
| 10,11 | SPI0 / MOSI, SCLK | output ALT0 | 既定 down、内部 off 案 | なし |
| 12 | IR TX | output GPIO、将来 PWM0 ALT0 | 既定 down、LOW 案 | なし |
| 13 | IR RX | input GPIO | config_setup は up | 両 edge 候補 |
| 14 | UART / 外部 TX | output ALT0 TXD0 は判断待ち | 既定 down、内部 off 案 | UART IRQ を使う |
| 15 | UART / 外部 RX | input ALT0 RXD0 は判断待ち | 既定 down、idle up 案 | UART IRQ を使う |
| 16 | M5IOE1 reset | output GPIO、非 assert HIGH 案 | 外部 R80 100k up | なし |
| 17 | 音声 / HP_DET | input GPIO | v5 up | 両 edge 候補 |
| 18,19 | PCM / BCLK, LRCK | output ALT0、clock producer | 既定 down、内部 off 案 | なし |
| 20 | PCM / DIN | input ALT0 | 既定 down、内部値未定 | なし |
| 21 | PCM / DOUT、MCLK 経路あり | output ALT0、競合は音声側で確認 | 既定 down、内部 off 案 | なし |
| 22 | SPI0 / HAT の追加 CS | output GPIO | 既定 down、非選択 HIGH 案 | なし |
| 23,26 | 拡張 / P1,P0 | input から開始、貸出時に限定設定 | 既定 down、内部値未定 | 明示許可時だけ |
| 24 | 音声 / amp enable | output GPIO | 既定 down、disable 開始案 | なし |
| 25 | LCD / DC | output GPIO | 既定 down、LOW 開始案 | なし |
| 27 | keyboard / TCA8418 IRQ | input GPIO | 外部 R124 100k up、v5 up | v5 は LOW level（edge ではない） |

全行は register bank 0、IRQ group `<2 17>` です。GPIO28-53 は client に貸しません。固定 [CM0 DTS](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts#L21-L75) は28 HPD、29 LED、30-33 BT UART、34-39 SDIO、40 camera、42 BT shutdown、43 clock などの内部用途を記載します。28-31 は register bank 0、32-53 は bank 1 です。41、44-53 の用途も未照合のまま予約します。

### firmware と Linux の設定を分ける

配布 config.txt は I2C/I2S/SPI と fbtft を指定しますが、`gpio=`、`enable_uart`、`init_uart_clock`、`disable-bt` はありません。末尾は `cardputerzero-overlay` で、v5 を直接指定する file ではありません。別の Makefile の config_setup が `enable_uart=1`、v5 overlay、GPIO13 の pull-up、GPIO12 の IR TX を追記します。この target が実機で実行済みとは確認していません。

v5 の GPIO4 output/pull off、17/27 input/pull up、24 amp enable、6 falling IRQ は Linux に向けた宣言です。DT node の存在だけで firmware が既に MMIO を設定したとは言えません。firmware の UART 初期化の影響は [PL011 調査](uart-pl011.md) に分けます。個別 pin の実際の引き継ぎ値は未確認で、seL4 起動直後の GPFSEL/GPLEV を HW-16 で記録します。pull は読み戻せないため config と設定手順を記録します。GPIO16 は camera 用という旧仮説を採らず、M5IOE1 reset として保護します。

## 権限・interface の提案（未実装）

| PD | 対象・権限 | 理由・DMA |
|---|---|---|
| GPIO | `0x3F200000` frame RW、IRQHandler `<2 17>`、IRQ notification receive | 一つの page の唯一の所有者。GPIO 自体に DMA なし |
| GPIO | badged request endpoint receive、client ごとの event notification signal | badge から静的 pin 許可表を引く。cap の追加配布なし |
| client | request endpoint write/grantreply、event notification receive、event 状態 page read | Call の reply と event 観測だけ。GPIO frame、他 client の通知先、IRQControl、untyped は渡さない |

`tools/capdl` は現在 IRQ object と pin policy を受け付けません。提案は一つの TOML に client badge、pin、許可 op、direction、pull、ALT、event、初期 level を追加し、GPIO PD 用の定数表と Markdown を生成するものです。重複 owner、予約 pin、無許可 ALT、入力への set、cap badge との不一致を拒否し、独立 checker と mutation 試験を加えます。現行 schema に既に実装されているとは主張しません。

ops は configure / set / clear / read / wait-for-edge とし、wait は購読を登録して直ちに応答、その後 notification で知らせます。client が送る pin mask は許可 mask の部分集合だけ、configure は固定した候補だけを認めます。通知後に状態 page の sequence/level を読み、arm と再確認で取りこぼす待ちを避けます。input LOW level の再 arm は別状態で管理します。不正 pin・op・長さ・sequence は MMIO に触る前に拒否し、記録は RAM の rate limit 付き counter に限ります。

GPIO PD は UART や通常 client より高優先度、powerfail の受信先はさらに高くする案です。verified kernel は non-MCS なので SC の budget はありません。1 dispatch の処理件数と購読者数を制限し、GPIO6 の経路では他 client の reply を待ちません。Linux の 500 ms debounce を電源断の猶予だと解釈せず、まず LOW を即通知し、誤検出の扱いを電源側で決めます。優先度の数値・許容遅延・timer の提供者は判断待ちです。

GPIO PD が死ぬと全 pin 操作・電源異常の通知が止まります。出力 latch が残るという想定だけで安全を保証しません。fault を監視する PD、各 client の timeout、起動時の安全な再設定を計画します。静的な権限を維持したままの再起動機構は未実装です。電源断に UART 出力や storage flush を必須とせず、[電源保持](powerfail-gpio6.md) と HW-1/HW-2 の実測を前提にします。

## 既存実装と QEMU の限界

[libplatsupport gpio.c](https://github.com/seL4/util_libs/blob/ef49a397b7044fc38b609a99a8c6265a97913b8e/libplatsupport/src/plat/bcm2837/gpio.c#L13-L58) は BSD-2-Clause。FSEL、set/clear/read の参考になりますが、この file に pull の待ちや IRQ 配布はありません。[Linux pinctrl](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/pinctrl/bcm/pinctrl-bcm2835.c) は GPL-2.0-or-later の仕様確認用で、移植しません。他 OS と UART の比較は [PL011](uart-pl011.md) にあります。

開発 image の version 出力は `QEMU emulator version 10.0.13 (Debian 1:10.0.13+ds-0+deb13u1)` でした。読んだのは同版の upstream source で、Debian patchset との全差分は未照合です。MSD/Linux の GPIO IRQ patch 付き QEMU 11 系と混同しません。

| 機能 | [bcm2835_gpio.c v10.0.13](https://github.com/qemu/qemu/blob/v10.0.13/hw/gpio/bcm2835_gpio.c#L147-L248) の実装 | 試験の範囲 |
|---|---|---|
| FSEL、GPSET/CLR、GPLEV | 状態と GPIO 出力を実装 | mask・RMW・基本 readback の QEMU 試験を計画できる。外部 pin は再現しない |
| GPEDS、全 edge/level 検出、pull | read は 0、write は無視 | event、W1C、pull の効き・待ち時間を QEMU 合格にできない |
| GPIO IRQ | model は pin 出力のみ。[raspi peripheral 配線](https://github.com/qemu/qemu/blob/v10.0.13/hw/arm/bcm2835_peripherals.c#L238-L246) に GPIO IRQ の接続なし | host の fake MMIO/IRQ 試験と実機が必要 |

host では全 pin 境界、権限拒否、FSEL の隣接 bit、W1C mask、pull の write 順序、購読直後の event、notification の合流、GPIO6 と IRQ storm の優先処理を試験する案です。実機は [HW-16/HW-17](../experiments/hardware-checklist.md) と電源試験を使います。これは試験計画であり、いずれも今回の実施結果ではありません。kernel の構成・証明の範囲は変更せず、GPIO PD・generator・firmware・基板は kernel の証明の対象外です。

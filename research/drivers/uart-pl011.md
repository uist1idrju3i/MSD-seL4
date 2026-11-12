# BCM2837 PL011 UART の調査

[driver の状況](README.md) / [SoC の要約](soc-blocks.md) / [GPIO](gpio.md)

2026-11-12 の資料調査です。提案する driver は未実装・未採用で、今回 QEMU の新しい起動試験も実機試験も行っていません。既存の [CapDL polling component](../sel4/capdl.md) の成功を IRQ driver や実機 UART の成功とは扱いません。

## 出典と接続

- 【一次】[BCM2835 ARM Peripherals、2012-02-06](https://datasheets.raspberrypi.com/bcm2835/bcm2835-peripherals.pdf)、§13 pp.175-194、GPIO の ALT は §6 pp.102-104。印刷ページで示します。PDF の hash と配線監査の版は [GPIO 調査](gpio.md) にあります。
- 【一次】固定 [rpi3.dts の PL011](https://github.com/seL4/seL4/blob/62e345c240a15671484530b4e6e069ce266c28d7/tools/dts/rpi3.dts#L374-L389)、[GPIO14/15 ALT0 と32/33 ALT3](https://github.com/seL4/seL4/blob/62e345c240a15671484530b4e6e069ce266c28d7/tools/dts/rpi3.dts#L299-L335)。bus `0x7E201000`、ARM 物理 `0x3F201000` の単独 page、IRQ `<2 25>`（GPU IRQ57）です。seL4 の IRQ 番号は実装前に生成 header と照合します。
- 【一次資料との照合記録】[MSD/Linux の配線監査](https://github.com/uist1idrju3i/MSD-Linux/blob/530d91d6ffbc1624a7c05ffc845bd1d811f98a86/docs/research/hardware/hardware-wiring-audit.md#L74-L95) は GPIO14/15 が U37 の level translator を介して HAT に、GPIO4 の mux を介して Grove に出ることを示します。回路図 pp.7,10。GPIO4 LOW=UART、HIGH=I2C1。HAT と Grove は独立 UART ではなく同じ二線です。同時接続による RX の競合は未確認で、同時使用を許可する案にはしません。

### CM0 の Bluetooth と実際の config

【一次】当 repo の固定 M5 [config.txt L6-16](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/firmware/CardputerZero/config.txt#L6-L16) と [L48-58](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/firmware/CardputerZero/config.txt#L48-L58) には `disable-bt`、`miniuart-bt`、`enable_uart`、`init_uart_clock` の指定がありません。最後は v5 でなく `cardputerzero-overlay` です。別の [Makefile L66-104](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/CardputerZero/Makefile#L66-L104) が config_setup で `enable_uart=1` と v5 overlay を加えますが、Bluetooth の再配置や UART clock の指定はしません。v5 overlay 自体にも UART の再配置はありません。

【一次】固定 [CM0 DTS の aliases](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts#L3-L18) は serial0=uart1（mini UART）、serial1=uart0（PL011）です。[同 file L114-135](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts#L114-L135) は uart0 を GPIO30-33 ALT3 の BT 用にします。seL4 の rpi3.dts も PL011 の32/33と Bluetooth node を記載します。

したがって「v5 が PL011 を外部 GPIO14/15 に出す」とは言えません。config_setup の enable_uart だけでも PL011 への切り替えにはなりません。実機の firmware、適用済み DT、pin mux は未確認です。無線付きかどうかも CM0 の型番で識別します。

提案の選択肢は次のとおりで、起動設定は今回変更しません。

| 案 | 利点 | 欠点・前提 | 推奨 |
|---|---|---|---|
| BT を無効化し、PL011 を14/15 ALT0 に明示配置 | debug 用の安定した clock、単独 page/IRQ | Bluetooth と両立しない。firmware と GPIO PD の所有権の合意が要る | 初版の外部 debug 用に推奨、利用者の判断待ち |
| BT は PL011、外部は mini UART | 既存 CM0 の配線方針を保つ | core clock 依存、AUX の page/IRQ を SPI1/2 と共有。別調査・driver が要る | BT 優先なら候補 |
| BT を mini UART に移す | 外部 PL011 と BT を併用できる可能性 | clock、flow control、firmware、BT stack まで検証が増える | 初版は非推奨 |

Linux 用 [disable-bt overlay](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/arch/arm/boot/dts/overlays/disable-bt-overlay.dts#L4-L57) は UART/BT の node と aliases を変更します。seL4 の自前 GPIO PD が14/15を ALT0 にする処理の代わりと決めつけません。BT UART の古い pin mux を残して同じ UART を二つの経路で駆動しないよう、内部30-33の扱いも決める必要があります。

## clock と register

【一次】firmware 文書の [init_uart_clock](https://github.com/raspberrypi/documentation/blob/21d772e7ee022e36a8f43c3ee75e20ca359fb832/documentation/asciidoc/computers/legacy_config_txt/boot.adoc#L46-L52) は UART0 の初期 clock の既定を48 MHz、初期 baud を115200としています。APB clock、CPU clock、mini UART の core VPU clock と混同しません。clock manager が UARTCLK を供給します。文書の既定値は、手元の実機で firmware が設定した値の実測ではありません。

提案は起動設定で `init_uart_clock=48000000` を明示し、UART PD に同じ値を静的に渡す方法です。mailbox を省けますが firmware 設定との一致を HW-18 で確認する必要があります。別案は [firmware property interface](https://github.com/raspberrypi/firmware/wiki/Mailbox-property-interface) の Get clock rate（tag `0x00030002`、UART clock ID=2）を問い合わせることです。これは最後の要求値で、実周波数の測定ではありません。Get clock rate measured（`0x00030047`）もありますが、対象 firmware の対応は未確認です。この場合 UART PD に mailbox MMIO を渡さず、mailbox PD の許可した clock-query interface だけを使います。mailbox は VideoCore DMA と kernel の割り込み controller 共有 page の信頼範囲に関わります。初版は静的 clock、動的変更は非対応を推奨します。

【一次】§13.4 pp.177-194。32-bit MMIO とし、予約 bit は保持又は仕様どおり0にします。

| register | offset | 意味・扱い |
|---|---|---|
| DR | 0x00 | 送信 data[7:0]、受信 data と FE/PE/BE/OE[11:8]。RXFE が0のときだけ read、TXFF が0のときだけ write |
| RSR/ECR | 0x04 | 受信 error の状態／書いて解除。DR の error を捨てる前に counter と status に反映 |
| FR | 0x18 | CTS、BUSY、RXFE、TXFF、RXFF、TXFE。FIFO empty と shift register の送信完了を区別 |
| ILPR | 0x20 | BCM では未使用。触らない |
| IBRD/FBRD | 0x24/28 | baud divisor の整数16 bit／小数6 bit |
| LCRH | 0x2C | word length、parity、stop、FIFO enable、break。divisor 設定後に書く |
| CR | 0x30 | UARTEN/TXE/RXE、CTS/RTS flow control。初版は8N1・二線、flow control off |
| IFLS | 0x34 | RX/TX FIFO IRQ 閾値。1/8,1/4,1/2,3/4,7/8 |
| IMSC | 0x38 | IRQ mask。RX/receive timeout/error を許可し、TX は未送信 data がある間だけ許可 |
| RIS | 0x3C | mask 前の IRQ 状態 |
| MIS | 0x40 | mask 後。handler はこれと FIFO の状態を確認 |
| ICR | 0x44 | 対象 bit に1を書いて IRQ を clear。MIS に値を書いても解除されない |
| DMACR | 0x48 | 初版は0。generic register の存在だけで BCM の DMA 対応を判断しない |

TX FIFO は16 byte、RX は16 entry×12 bit（data と error）です（p.175）。FEN=0 は1 entry。BCM2837 の rpi3.dts の PrimeCell ID は `0x241011`、[Linux](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/tty/serial/amba-pl011.c#L121-L138) の revision 判定でも16 entry 側です。実機の ID と波形は未確認です。

baud は `UARTCLK / (16 * baud)` の整数を IBRD、小数×64を丸めて FBRD にします。丸めで64なら整数へ繰り上げ、範囲・baud error を検査する案です。48 MHz /115200なら IBRD=26、FBRD=3。clock の値を誤ると QEMU では出ても実機では文字化けします。

### 初期化・IRQ・既知の誤り

【提案】GPIO PD に許可済みの mux を依頼して応答を得た後、IMSC=0、DMACR=0、UART を disable、FR.BUSY が下がるまで期限付きで待ち、FIFO を止めて残留状態を整理します。IBRD/FBRD、LCRH（8N1、FEN）、IFLS、ICR と ECR、CR を設定し、IRQ notification を結んで RX/TX を起動します。再設定時の未送信 data は drain 又は明示破棄を選び、無言で FIFO を消しません。BUSY 待ちで無期限に CPU を占有しません。

IRQ は RX が空になるまで読み、TX が満杯になるまで書きますが、1 dispatch の byte 数を制限します。RX 閾値未満の短い入力は RTIM も使って拾います（PL011 の受信 timeout は32 bit period）。TX queue が空なら TXIM を止めます。観測した IRQ の原因を処理し、ICR、MIS 再確認、seL4 IRQHandler Ack の順を計画します。RX interrupt を単に clear するだけでは FIFO の原因が残ります。

【既知の資料の誤り】[community errata](https://elinux.org/BCM2835_datasheet_errata#p177) は p.177 の IRQ 見出しの取り違えと base address の桁落ち、[p.192](https://elinux.org/BCM2835_datasheet_errata#p192) は ICR に MIS の説明を転記した誤りを挙げます。Broadcom 公認の errata としては扱いません。IRQ の意味は register map と固定実装を合わせて読みます。

p.175 はこの BCM2835 UART の DMA を非対応と記載します。BCM2837 の実装差を DMACR の説明だけから推定しません。debug/console の115200 baudなら PIO+IRQ を第一案にし、UART PD に DMA controller・descriptor・物理 memory の権限は渡しません。高 throughput が要るなら実測後に別判断します。Linux の全 vendor 向け workaround を無条件に BCM2837 の errata として導入することもしません。

## interface・権限・障害の提案

shared-memory の TX/RX ring と notification を使います。初版の RX 所有者は一つに固定し、複数 TX client の出力は byte quota と順序規則で分配する案です。pin mux と baud は固定し、任意 client には再設定を認めません。

| PD | capability | 理由・DMA |
|---|---|---|
| UART | `0x3F201000` frame RW、IRQHandler `<2 25>`、IRQ notification receive | 唯一の MMIO 所有者。PIO、DMA cap なし |
| UART | GPIO request endpoint write/grantreply、必要なら clock-query endpoint | pin14/15 の許可操作だけ。GPIO/clock/mailbox の frame を持たない |
| UART/client | client ごとの TX/RX data と head/tail の frame、相手への notification signal、自分の receive | 静的な双方向経路。通知は内容を信頼する根拠ではない |
| fault monitor | UART の fault endpoint receive | 停止を検出。client に TCB、IRQControl、untyped、他 client の ring を渡さない |

方向別に data/producer-index/consumer-index の page を分け、TX data は client write・UART read、RX は UART write・client read、各 index の writer は片側だけにします。cacheable な通常 RAM と device MMIO は属性を分けます。writer の release と reader の acquire に相当する順序を定義し、32-bit index の wrap、差分が capacity 以下か、長さ・範囲を検査します。consumer が信用できない場合も自分の shadow index と比較します。notification は wakeup だけで、ring の状態を再検査してから待つ手順にし、lost wakeup を host 試験します。

RX overrun は消えた byte を復元できません。OE/FE/PE/BE の counter と stream gap を client に知らせ、ECR を解除します。ring full 時は無期限に待たず、破棄方針と再通知を決めます。二線には相手を止める flow control がないため、損失なしを保証しません。受信した長さ・index が不正ならその client の要求だけを拒否し、MMIO の address と baud に反映しません。

UART PD の死亡時は GPIO PD・電源異常の経路を巻き込まない設計にします。client の待ちには timeout、monitor から offline 通知、IRQ mask と安全な再初期化を計画しますが、再起動機構は未実装です。GPIO PD の死亡時には UART の再 mux はできません。UART 停止や電源断で TX ring に残った data は失われ得ます。TXFE=1だけで送信完了とはせず、期限付きの drain は BUSY=0まで確認します。電源断の処理で log の完送を待ったり、永続 storage へ log を保存したりしません。

優先度は powerfail/GPIO より下、通常 client より上の案です。verified non-MCS には SC budget がないため、byte quota・client 数・ring capacity で処理量を制限します。capDL の IRQ/ring/pin policy の拡張と独立 checker は後続の実装範囲です。

### polling component の置き換え

現在の serial は固定文字列の PL011 polling と request/reply/fault 観測の試験用です。製品案は同じ MMIO を持つ別の UART PD とし、client は ring と通知だけを持ちます。既存の positive/negative 試験は隔離の回帰として残し、UART driver の RX/IRQ/FIFO/error 試験を別に追加します。試験用 serial と製品 UART を同時に MMIO 所有者にはしません。kernel は既存の verified configuration と printing off のままです。

## 既存実装・ライセンス

採用・移植の決定ではなく、読解した候補の比較です。GPL のコードを自作 driver へ写しません。

| 実装と固定版 | 読解で分かること | ライセンス・限界 |
|---|---|---|
| [libplatsupport BCM serial](https://github.com/seL4/util_libs/blob/ef49a397b7044fc38b609a99a8c6265a97913b8e/libplatsupport/src/mach/bcm/serial.c)、[PL011](https://github.com/seL4/util_libs/blob/ef49a397b7044fc38b609a99a8c6265a97913b8e/libplatsupport/src/mach/bcm/pl011_uart.c#L180-L238) | BCM の GPIO mux と初期化の参考。FIFO を止める SerialServer 向け判断がある | BSD-2-Clause。その設定を新しい ring driver にそのまま採らない |
| [sDDF ARM PL011](https://github.com/au-ts/sddf/blob/ae5086dff63f5a23785a26febe3d7fc8fe66c062/drivers/serial/arm/uart.c#L24-L150) | RX/TX queue、RTIM、TXIM の停止・再開 | BSD-2-Clause。baud 計算に float を使い、固定 reference clock を仮定。FPU off の verified build 向けには整数計算を設計する |
| [sDDF serial example](https://github.com/au-ts/sddf/blob/ae5086dff63f5a23785a26febe3d7fc8fe66c062/examples/serial/README.md)、[Microkit loader UART](https://github.com/seL4/microkit/blob/30e1406490d60f446db2a78fd131f3909a62699e/loader/src/uart.c) | Microkit 上の二つの client の例と、loader の debug UART は別物 | BSD-2-Clause。example は rpi4b/qemu virt 等で、BCM2837 verified の動作証拠ではない。loader の polling は製品 PD の代用でない |
| [U-Boot PL01x](https://github.com/u-boot/u-boot/blob/3cb2cbbc75aa7fe2391f662607d6b2f46c1292a7/drivers/serial/serial_pl01x.c) | baud、busy、register 順序の比較 | GPL-2.0-or-later、仕様読解だけ |
| [Linux amba-pl011](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/tty/serial/amba-pl011.c) | FIFO revision、vendor 差、error と flow control | GPL-2.0-or-later、仕様読解だけ |
| [Circle serial.cpp](https://github.com/rsta2/circle/blob/7a81e1b480fe7d19fc1fc695b89bff0a0848f44b/lib/serial.cpp) | Raspberry Pi の bare-metal 初期化・clock の比較 | GPL-3.0-or-later、仕様読解だけ |

## QEMU と実機の境界

開発 image の QEMU は10.0.13（Debian `1:10.0.13+ds-0+deb13u1`）。以下は同版 upstream source の読解です。Debian patchset の全差分は未照合で、今回これらの動作を試験したという意味ではありません。

| 対象 | source で確認した実装 | 試験の限界 |
|---|---|---|
| raspi3b の UART0 | [serial_hd(0) と IRQ の接続](https://github.com/qemu/qemu/blob/v10.0.13/hw/arm/bcm2835_peripherals.c#L284-L326) | pin mux を経由せず host chardev に直結。GPIO14/15 や BT の正しさは確認できない |
| RX FIFO、IMSC/MIS/ICR、IRQ | [pl011.c](https://github.com/qemu/qemu/blob/v10.0.13/hw/char/pl011.c#L120-L195)、[FIFO depth=16](https://github.com/qemu/qemu/blob/v10.0.13/include/hw/char/pl011.h#L28-L42) | RX・IRQ・ring の結合試験を計画できる |
| IFLS / RTIM | [read_trigger は1に固定](https://github.com/qemu/qemu/blob/v10.0.13/hw/char/pl011.c#L332-L346)。通常受信経路に RT interrupt を発生させる timer はない | 閾値と短い入力の timeout は実機で確認 |
| TX と baud | [TX は chardev へ直接 write](https://github.com/qemu/qemu/blob/v10.0.13/hw/char/pl011.c#L227-L245)、clock/divisor は状態・trace に反映 | 実機の TX FIFO/backpressure、baud 波形、BUSY の時間を再現する保証なし |
| enable/error/DMA | [RX は enable bit を実質無視](https://github.com/qemu/qemu/blob/v10.0.13/hw/char/pl011.c#L487-L528)、[DMA は未実装](https://github.com/qemu/qemu/blob/v10.0.13/hw/char/pl011.c#L475-L479) | 無効化漏れでも QEMU だけ通り得る。overrun・電気的 error・CTS/RTS は実機が必要 |

host 試験案は divisor の丸めと境界、ring の wrap/full/empty、不正 index、通知合流・待ちの競合、error の伝達、IRQ の Ack 順序です。QEMU は RX/TX と IRQ の基本結合、PD の停止、client に MMIO がないことを検査する案です。実機は [HW-18/HW-19](../experiments/hardware-checklist.md) で mux・BT・clock・FIFO・overrun を確かめます。UART PD、ring、generator、firmware、基板を kernel の形式検証の対象とは主張しません。

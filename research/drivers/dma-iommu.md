# IOMMU がないことの影響と、PIO・DMA の方針

[driver の状況へ戻る](README.md)

BCM2837 には IOMMU がありません（[資源の設計方針](../sel4/system-architecture.md)）。この文書では、DMA を使う部品が壊れたり乗っ取られたりしたときに何が起きるかを device ごとに評価し、PIO（CPU が FIFO を読み書きする方式）と DMA のどちらを選ぶかの基準を決めます。QEMU で確かめられる範囲と、実機でしか確かめられない範囲も分けます。

状態: 方針は決定です（利用者の判断、2026-11-11。「決定」の節）。性能の値は、測定していない推測です。

## 何が起きるか

seL4 の capability は、CPU からのメモリの access だけを制限します。device がメモリを読み書きする DMA は、MMU を通らないため制限できません。DMA を指示できる部品が壊れると、次のものを読み書きできます。

- kernel の image と kernel object（CNode、TCB、page table、untyped の中身）。seL4 の証明（機能正当性、完全性、機密性）は、ここが書き換えられないことを前提にしています。この前提が崩れると、どの保護ドメインの分離も保証されません。
- ほかの保護ドメインのメモリ（storage の buffer、暗号の鍵、更新の image、画面の frame buffer）。
- 読み出しだけでも、鍵や利用者のデータが漏れます。

壊れ方は 3 つに分けて考えます。

| 壊れ方 | 例 | DMA で起きること |
|---|---|---|
| 偶発的な bug | address の計算違い、buffer の解放後の転送 | 関係のないメモリを壊す。原因の特定が難しい |
| driver の乗っ取り | 外部から届く data（USB、Wi-Fi、Ethernet、microSD の内容）を処理する部分の脆弱性 | 攻撃者がメモリ全体を読み書きできる。system 全体の乗っ取りに等しい |
| device や firmware の誤動作・悪意 | VideoCore の firmware、USB device の異常な応答 | device が bus master なら、driver に関係なくメモリ全体に届く |

## device の種類

DMA の経路は 2 種類あり、評価が違います。

1. 中央の DMA controller（BCM2835 DMA）を使う device: SPI0、SDHOST、EMMC、PCM（I2S）、PL011、PWM など。device 自体はメモリを読み書きせず、DMA controller が DREQ の信号に合わせて転送します。DMA controller は、メモリ上の control block に書かれた任意の物理 address の間で転送します。このため、DMA controller の MMIO を持つ部品は、メモリ全体を読み書きできます。逆に、DMA controller の capability を渡さなければ、この種類の device の driver は CPU の access しかできず、seL4 の分離がそのまま効きます。
2. 自分で bus master になる device: USB の DWC2（内蔵の DMA）、カメラの受信部（unicam）、VideoCore（GPU、HVS、V3D、ISP）。これらは、device の register に address を書くだけでメモリを読み書きします。driver が PIO で動いていても、乗っ取られた driver は register に書いて DMA を始められます。MMIO の capability を持つこと自体が、メモリ全体への access に等しくなります。

mailbox（firmware との通信）も 2 に入ります。property の要求では buffer の bus address を渡し、VideoCore の firmware がそこを読み書きします。乗っ取られた mailbox の driver は、firmware に任意の address を書かせられます（推測。firmware が address を検査するかは未確認です）。

EMMC（Arasan の SDHCI）は、SDHCI の規格では SDMA と ADMA を持てます。Linux の `drivers/mmc/host/sdhci-iproc.c` は bcm2835 で SDMA と ADMA の capability を宣言しておらず、QEMU の `hw/arm/bcm2835_peripherals.c` も capability register を「no DMA」にしています。実機の EMMC が bus master として動くかは未確認なので、確かめるまでは 2 として扱います。

## device ごとの評価

性能の欄は、どれも推測です。driver の調査のときに、QEMU ではなく実機で測ります。

| device | DMA の経路 | 外部からの入力 | PIO の性能の見込み | 当初の案（PIO を既定） |
|---|---|---|---|---|
| I2C の各 device、GPIO、UART、IR、RTC、電池、IMU、キーボード | なし、または中央 | 少ない | 問題ない | PIO |
| 音声（PCM・I2S） | 中央 | なし | 48 kHz の stereo で、FIFO の半分ごとの割り込みが毎秒約 1,500 回 | PIO で始める |
| LCD（ST7789V、SPI） | 中央 | なし | 320×170 で 16 bit の全画面は 108,800 バイト。SPI の FIFO は 64 バイトなので、CPU が転送の間ずっと FIFO を埋めることになる | PIO で始め、frame rate を測る。足りなければ DMA server（下記）を使う |
| microSD（SDHOST） | 中央 | microSD の内容 | FIFO は 16 word。転送中は CPU を占めるが、製品の規則で書き込みは少ない | PIO |
| microSD・SDIO（EMMC） | 未確認（中央か bus master） | microSD の内容、Wi-Fi の frame | SDHOST と同じ程度 | PIO。bus master かどうかを先に確かめる |
| USB（DWC2）、hub、Ethernet（SR9900A） | bus master | USB device と network からの data | Slave mode は割り込みが非常に多い。Linux の bcm2835 は DMA を使う | 分離はどちらの mode でも同じ。性能で選ぶ |
| Wi-Fi・Bluetooth | EMMC または SDIO と UART | 無線からの data | 未調査 | 接続先の device に従う |
| カメラ（unicam、IMX219） | bus master | センサーの data | PIO の経路はない | DMA が前提 |
| HDMI、画面合成、GPU | VideoCore | なし | PIO の経路はない | VideoCore を信頼の前提に含める |
| mailbox | VideoCore が buffer を読み書き | なし | 該当しない | 信頼の前提に近い部品として最小にする |

## 影響を抑える方法

「device ごとの評価」の表と、この節の 1 と 2 は当初の案（PIO を既定）です。決めた方針は「決定」の節にあります。

### 1. DMA controller の capability を誰にも渡さない（当初の案の既定）

中央の DMA controller を使う device は、すべて PIO で動かします。DMA controller の MMIO の frame を root task から渡さなければ、DMA の経路そのものがなくなります。capDL の記述で、DMA controller の frame がどの保護ドメインにも map されていないことを機械的に検査できます。

### 2. DMA server（当初の案では性能が足りない device だけ）

PIO で性能が足りないと実機で分かった device（LCD が最初の候補）は、driver に DMA controller を渡さず、DMA server という小さな保護ドメインを置きます。

- DMA server だけが DMA controller の MMIO と、control block を置くメモリを持ちます。control block は client と共有しません。
- client は「自分の DMA buffer の offset と長さ」と「device の種類」だけを IPC で渡します。DMA server は、転送先と転送元が登録済みの buffer と、その device の FIFO の address に収まることを確かめてから control block を作ります。
- こうすると、メモリ全体に届く部品は DMA server だけになります。DMA server は小さく、外部からの data を処理しないので、Frama-C や CBMC での検証の候補になります（[kernel 以外の形式検証](../verification/beyond-kernel.md)）。
- 残る危険: DMA server の bug、DMA controller の hardware の不具合、control block の chain（`NEXTCONBK`）の検査漏れ、cache の clean・invalidate の誤り。

### 3. bus master の device

DWC2、unicam、VideoCore、mailbox（と、未確認の間の EMMC）は、software では分離できません。次のようにして影響を抑えます。

- driver を小さくし、外部からの data の解析（USB の descriptor、network の protocol）を別の保護ドメインに分けます。driver は register の操作と、決まった buffer の受け渡しだけをします。こうすると、乗っ取りの入口になる code が、メモリ全体に届く部品の外に出ます。
- これらの driver は「全メモリに書ける部品」として capability の表に書き、形式検証と試験の優先度を上げます。
- 使わない機能の device は起動しません。capability も渡しません。
- DWC2 は DMA mode と Slave mode で分離の強さが同じです。Slave mode は address の誤りによる偶発的な破壊を減らせますが、乗っ取りには効きません。mode は性能と CPU の負荷で選びます。

### 4. 使わない対策

- TrustZone で RAM を分ける方法: BCM2837 に TZASC のような memory の保護があるかは未確認です。あったとしても、firmware と boot の流れを作り直す必要があります。今は採用しません。
- VideoCore の firmware を信頼しない設計: firmware は起動を担い、メモリ全体に届くので、どの案でも信頼の前提に入ります。

## QEMU で確かめられる範囲

QEMU 10.0 の raspi3b を source（`hw/arm/bcm2835_peripherals.c` ほか）で確かめた結果です。

| device | QEMU の実装 | QEMU で確かめられること | QEMU では確かめられないこと |
|---|---|---|---|
| DMA controller | あり（`hw/dma/bcm2835_dma.c`） | DMA server の address の検査（範囲外の要求を拒むか） | 実機の転送速度、hardware の不具合 |
| SPI | あり。DMA mode は「not supported」と log を出す | PIO の driver の手順 | ST7789V の応答、DMA での転送、frame rate |
| I2C | あり | BSC の手順 | 各 device（TCA8418、BMI270 など）の応答 |
| SDHOST | あり。DMA の処理はない | PIO の driver の手順、block の読み書き | 実際の microSD の速度、電源断 |
| EMMC（SDHCI） | 汎用の SDHCI。capability は「no DMA」 | PIO の手順 | 実機の DMA の有無 |
| USB（DWC2） | DMA mode だけ。Slave mode は未実装（`hw/usb/hcd-dwc2.c` の TODO） | DMA mode の driver の手順 | Slave mode の試験、SR9900A、hub |
| PCM・I2S | 未実装（`create_unimp`） | なし | 音声のすべて |
| GPIO、mini UART、PL011 | あり | driver の手順 | 実機の配線 |
| mailbox、frame buffer | 一部あり | property の手順 | 実際の firmware の振る舞い |
| カメラ、HDMI、V3D | 未実装 | なし | すべて |

QEMU は cache を模擬しないため、DMA の前後の cache の clean・invalidate を忘れても QEMU では動きます。cache の扱いは、実機と review でしか確かめられません。

## 決定（2026-11-11）

利用者は、乗っ取られたときの影響が PIO でも変わらない device では DMA を既定にする、と判断しました。中央の DMA controller についても、DMA server が DMA controller を持てば、driver には DMA を渡さずに分離を保てます。この 2 点から、次の方針に決めました。

| device の種類 | 既定 | 全メモリに届く部品 | 理由 |
|---|---|---|---|
| 中央の DMA controller を使う device（SPI の LCD、SDHOST、PCM・I2S など） | DMA server を通した DMA | DMA server だけ | driver は DMA controller の capability を持たない。DMA server が転送元と転送先を登録済みの buffer と device の FIFO に限るので、driver が乗っ取られても DMA ではほかのメモリに届かない |
| 自分で bus master になる device（USB の DWC2、カメラの unicam、VideoCore、mailbox） | device 自身の DMA | その driver | MMIO の capability を持つだけでメモリ全体に届くため、PIO にしても乗っ取られたときの影響は変わらない。DWC2 は DMA mode を既定にする |
| DMA を使わない device（I2C、GPIO、UART、IR、RTC、電池、IMU、キーボード） | PIO | なし | 転送量が少ない |
| EMMC（Arasan の SDHCI） | bus master かどうかを確かめるまでは bus master として扱う | その driver | 実機の DMA の有無が未確認 |

- PIO は、DMA server ができるまでの間と、試験で DMA と比べるために残します。
- DMA server は、DMA controller の MMIO と、control block を置くメモリを持つ唯一の保護ドメインです。client と control block を共有しません。control block の chain（`NEXTCONBK`）も DMA server が作ります。capDL の記述で、DMA controller の frame が DMA server にだけ map されていることを機械的に検査します。
- DMA server は全メモリに届くため、信頼する部品（TCB）に入ります。形式検証（Frama-C、CBMC など）と試験の優先度を最も高くします。外部からの data は処理しません。
- 転送のたびに、client と DMA server の間で IPC が少なくとも 1 回増えます。この負荷を、LCD の frame rate と音声の遅延で測ります。
- bus master の device の driver は「全メモリに書ける部品」として capability の表に書きます。外部からの data の解析（USB の descriptor、network の protocol）は、別の保護ドメインに分けます。
- QEMU の使い方は変えません。driver の手順と DMA server の address の検査に使い、性能、cache、音声、USB の Slave mode、実際の device の応答は実機で確かめます。

### DMA controller を driver ごとに分けて渡せない理由

seL4 の frame は 4 KiB 単位です。BCM2837 の DMA controller の channel 0〜14 は 0x100 ずつの間隔で並び、1 つの 4 KiB page に収まります（`vendor/seL4/tools/dts/rpi3.dts` の `dma@7e007000` は `reg = < 0x7e007000 0xf00 >`）。このため、channel ごとに frame の capability を分けて driver に渡すことはできません。channel の割り当ても DMA server が持ちます。

### 当初の案（PIO を既定、2026-11-11 に変更）

1. 中央の DMA controller を使う device は PIO で作り、DMA controller の capability は誰にも渡さない。
2. PIO で性能が足りないと実機で分かったときは、driver に DMA を渡さず、DMA server を置く。
3. bus master の device の driver は「全メモリに書ける部品」として扱い、外部からの data の解析を別の保護ドメインに分ける。DWC2 の mode は性能で選ぶ。
4. QEMU は、driver の手順と DMA server の検査に使う。性能、cache、音声、USB の Slave mode、実際の device の応答は実機で確かめる。

この案では、DMA server を作るまでの手間は省けます。一方で、乗っ取られたときの影響が変わらない bus master の device にまで性能の損失を負わせます。中央の DMA を使う device も、DMA server があれば DMA を使って分離を保てます。このため変更しました。

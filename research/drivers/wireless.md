# Wi-Fi・Bluetooth（CYW43439）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| chip | CM0 の datasheet は無線の部品に CYW43439 を記載。無線付きの型番（CM0100000 など）だけにある | CM0 の datasheet Release 3、MSD/Linux の配線の監査 |
| Wi-Fi | SDIO（EMMC の controller の見込み） | MSD/Linux の [ハードウェア仕様](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/docs/research/hardware/hardware-spec.md)（Linux は `BRCMFMAC`） |
| Bluetooth | UART（PL011 の見込み） | 同上（Linux は `BT_HCIUART`） |
| 有効・無効 | WiFi_ON・BT_ON。LOW で無効にできるが、GND 側の R67・R68 は NC | 回路図 p.5 |

CardputerZero に載る CM0 の型番と、実際の chip の ID は確かめていません。【未確認。実機の刻印と SDIO の ID で確かめる】

## 何が大事か

- chip の中で firmware が動き、Wi-Fi の frame と Bluetooth の packet を処理します。この firmware は Infineon（Cypress）の binary で、中身を検査できません。
- Wi-Fi は外部から data が届く経路です。chip の firmware が乗っ取られる攻撃は、Broadcom の chip で過去に公開されています（Broadpwn など）。【一次。CVE-2017-9417】
- SDIO の host controller（EMMC）が bus master かどうかは確かめていません。bus master なら、Wi-Fi の driver は「全メモリに届く部品」になります（[dma-iommu.md](dma-iommu.md) の決定）。

## 設計の検討

- 部品の分け方: SDIO の host controller の driver、Wi-Fi の chip の driver（firmware の読み込みと、chip との制御・data の通信）、network の stack（WPA などの暗号と IP）を分けます。chip との通信は Broadcom の FullMAC の形式で、frame の解析は DMA の capability を持たない部品で行います。
- firmware と NVRAM・CLM の file: chip に毎回読み込む必要があります。Raspberry Pi の firmware の配布物にあり、Infineon の再配布の license の条件を確かめます。【未確認】
- 規模と順序: Wi-Fi は、SDIO、chip の driver、WPA、IP の stack を全部作る必要があり、最も大きい作業の 1 つです。製品の更新（network からの取得）に要るかどうかで優先度を決めます。Ethernet（USB の SR9900A）の方が先に作れる見込みです。
- 既定で off: 使わない間は WiFi_ON・BT_ON を LOW にします。どの pin で制御できるかは CM0 の DTS で確かめます。【未確認】

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| EMMC の page | SDIO の host controller の driver |
| PL011 の page | Bluetooth の HCI |
| GPIO の部品 | WiFi_ON・BT_ON |
| mailbox | 無線の電源や clock を firmware に依頼する場合 |

## 試験

| 範囲 | 確かめること |
|---|---|
| host | FullMAC の message の解析（fuzzing） |
| QEMU | 汎用の SDHCI の PIO の手順だけ。QEMU に CYW43439 はない |
| 実機 | chip の ID、firmware の読み込み、scan、接続、Bluetooth の HCI |

## 決めること

1. 無線を作るかどうかと、その時期。推奨: Ethernet を先にし、Wi-Fi は network の更新の設計が決まってから判断する。Bluetooth は用途が決まるまで作らない。

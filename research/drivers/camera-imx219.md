# カメラ（CSI-2、Unicam、IMX219）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。CardputerZero Standard だけにあり、Lite にはありません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| sensor | IMX219。I2C は SDA0・SCL0（BSC0 の見込み） | 回路図 p.5・p.10、MSD/Linux の配線の監査 |
| CSI | CM0 は 4 lane に対応し D0〜D3 を配線。Linux の固定の DTS と既定の IMX219 overlay は 2 lane | MSD/Linux の配線の監査 |
| 電源 | U36 の CAM_3V3。EN は VSYS_5V に 100k で pull-up | 回路図 p.10 |
| CAM_GPIO | CM0 の pin 44、内部の GPIO40 | MSD/Linux の配線の監査 |
| 受信部 | Unicam（CSI1）。seL4 の `rpi3.dts` には node がない | `rpi3.dts` |

Unicam の register の address と割り込みは、seL4 の DTS にないので Raspberry Pi の Linux の DTS（`bcm283x.dtsi`）で確かめます。【未確認】Unicam の register の仕様は Broadcom の公開資料にはなく、Linux の `bcm2835-unicam` driver（GPL-2.0）が事実上の資料です。

## 何が大事か

- Unicam は受け取った frame を直接メモリに書く bus master で、PIO の経路がありません。driver は「全メモリに届く部品」です（[dma-iommu.md](dma-iommu.md) の決定）。
- IMX219 の raw の data（Bayer）を表示に使うには、色の補間などの処理が要ります。Linux では VideoCore の ISP（`bcm2835-isp`）か libcamera の software で行います。

## 設計の検討

- 部品の分け方: Unicam の driver（frame の受信）と、IMX219 の設定（I2C）と、画像の処理を分けます。画像の処理は DMA の capability を持ちません。
- frame の buffer: Unicam に渡す buffer を、カメラ用の領域に限ります。bus master なので乗っ取りは防げませんが、偶発的な bug を防げます。
- 優先度: カメラは製品の基本の機能（表示、入力、storage、更新）に要らないので、後の段階にします。

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| I2C の部品（BSC0） | IMX219 の設定 |
| Unicam の page | Unicam の driver だけ |
| mailbox | カメラの電源と clock を firmware に依頼する場合 |

## 試験

| 範囲 | 確かめること |
|---|---|
| host | frame の header の検査、raw の変換 |
| QEMU | なし。QEMU の raspi3b に Unicam はない |
| 実機 | sensor の ID、2 lane の raw の受信、Lite での応答なし |

## 決めること

1. カメラを作る時期。推奨: 表示、入力、storage、更新、network の後にする。

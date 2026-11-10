# USB（DWC2）、hub（GL852G）、Ethernet（SR9900A）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| controller | Synopsys DWC2（`0x3F980000`、`<1 9>`）。OTG の controller が 1 つ | `rpi3.dts` |
| 経路の切り替え | U16 FSW7227。USB_SW が LOW なら CM0 の USB は右の USB-C、HIGH なら hub。Q4 が USB_OTG を駆動 | 回路図 p.6 |
| hub | GL852G（U15）。USB1 は SR9900A、USB2 は USB-A、USB3 は左の USB-C、USB4 は HAT | 回路図 p.6 |
| hub の reset | M5IOE1 の PYG3。キーボードの reset と共有 | 回路図 p.6・p.8 |
| Ethernet | SR9900A（U13）。USB の上の 10/100 の Ethernet | 回路図 p.6 |
| 給電 | USB-A と左の USB-C は合計 1 A（U33） | 回路図 p.10 |

USB_SW をどの信号が駆動するか（SoC の GPIO か、M5IOE1 か）を回路図で確かめていません。【未確認】

## 何が大事か

DWC2 は自分で bus master になる device です。PIO（Slave mode）で動かしても、register を持つだけで全メモリに届きます。このため、[dma-iommu.md](dma-iommu.md) の決定どおり、device 自身の DMA を既定にし、USB の driver を「全メモリに届く部品」として扱います。さらに、USB と Ethernet は外部から data が届く経路です。乗っ取られたときの影響が最も大きい部品の 1 つです。

## 設計の検討

- 部品の分け方: 全メモリに届く部分（DWC2 の host controller の driver）をできるだけ小さくします。descriptor の解析、hub の処理、class の driver（Ethernet、mass storage、HID）は、DMA の capability を持たない別の部品にします。host controller の driver は「この endpoint にこの buffer を送る・受ける」だけを提供します。
- buffer の範囲: host controller の driver に渡すメモリを、USB 用の領域に限ります。ただし DWC2 は物理 address を何でも指せるので、これは偶発的な bug を防ぐだけです。乗っ取られた場合は防げません。
- DWC2 の難しさ: DWC2 の host mode は split transaction、channel の割り当て、頻繁な割り込みなどが複雑です。Linux、U-Boot、Circle の driver が参考になります。Circle（GPL-3.0）と Linux（GPL-2.0）は写さず、仕様を読む資料にします。U-Boot の DWC2 の driver の license は確かめていません。【未確認】Synopsys の databook は公開されていません。
- SR9900A: Linux の `sr9700` driver が SR9900A に対応しているかは、USB の VID・PID を実機で確かめていないので分かっていません（MSD/Linux の配線の監査）。【未確認】
- 外部からの入力: USB の descriptor と Ethernet の frame は、攻撃者が用意できます。解析する部品は DMA の capability を持たず、Rust などで書く候補にします（[rust-adoption.md](../sel4/rust-adoption.md)）。
- 規模: USB の stack は、この project の中で最も大きい部品になる見込みです。最初は hub と SR9900A だけに対応し、USB-A と USB-C の汎用の device は後にします。

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| DWC2 の page | host controller の driver だけ |
| M5IOE1 の部品 | hub の reset（PYG3、M5IOE1 の部品が起動の手順で動かす） |
| mailbox | USB の電源（power domain）を firmware に依頼する場合 |

## 試験

| 範囲 | 確かめること |
|---|---|
| host | descriptor の解析（壊れた入力の fuzzing）、範囲の検査 |
| QEMU | DMA mode の host controller の手順。QEMU の DWC2 は Slave mode を実装していない。hub と SR9900A はない |
| 実機 | 列挙、hub、SR9900A の VID・PID と通信、給電、host と device の切り替え |

## 決めること

1. USB の対応の範囲と順序。推奨: hub と SR9900A を先にし、汎用の USB device は後にする。

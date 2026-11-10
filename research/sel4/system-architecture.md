# capability・IPC・IRQ・MMIO・DMA の設計方針

[索引へ戻る](../README.md)

userland の部品の分け方と、資源の持ち方の方針です。基盤は [userland-frameworks.md](userland-frameworks.md) の推奨（案 B: capDL と `capdl-loader-app`）を前提にします。driver ごとの具体は `research/drivers/` に書きます。

## 一次資料から確かめたこと（seL4 17.0.0）

- `src/plat/bcm2837/overlay-rpi3.dts` は、kernel が使う device を `serial1`、`interrupt-controller@7e00b200`（BCM2835 の割り込み制御器）、`local_intc@40000000`（BCM2836 の core ごとの制御器）、`timer`（Arm generic timer、19.2 MHz）としています。これ以外の device は userland に渡ります。
- 同じ overlay は、既定のメモリを 128 MiB（`reg = <0x00 0x08000000>`）としています。CardputerZero の 512 MiB を使うには、この値を変えるか、GPU firmware が渡す値と合わせる必要があります。
- 同じ overlay は先頭のページを予約しています。SMP を使わない構成（検証済み構成は single core）では、副 core は armstub の中で回り続けます。この領域を再利用すると、副 core が任意のコードを実行します。
- `Hardware/Rpi3.md` の front matter は `iommu: false` です。BCM2837 には、DMA の範囲を制限する仕組みがありません。

## 方針

### 部品の分け方

- 1 つの device（または bus）に 1 つの driver の部品を置き、その device の MMIO と IRQ の capability はその部品だけが持ちます。
- bus（I2C1、SPI0、I2S）の driver と、その上の device（TCA8418、BMI270 など）の driver は別の部品にします。device の driver は、bus の driver への IPC だけで device に触れます。
- 部品の間の権限は capDL の仕様で固定し、実行中に capability を増やす経路（`Untyped` の配布、`CNode` の書き込み権）を、必要な部品にだけ渡します。

### IPC

- 制御は endpoint の同期 IPC（`seL4_Call` と `seL4_Reply`）、大きなデータは共有メモリの queue と notification で渡します（sDDF の考え方）。
- 部品の間の各 IPC には、message の形、事前条件、事後条件、error を「IPC の契約」として書き、host の試験と検査の対象にします。
- 呼ばれる側は badge で呼び手を区別し、呼び手ごとに許す操作を決めます。

### IRQ

- `IRQHandler` の capability は、その device の driver の部品だけに渡します。kernel は IRQ を notification で届けます。
- GPIO の割り込み（TCA8418 の GPIO27、電源断の GPIO6 など）は GPIO bank の IRQ を共有するため、GPIO の driver が受けて、pin ごとの notification に分けて配ります。

### MMIO

- device の MMIO は、その driver の VSpace にだけ、uncached（device memory）で map します。
- 1 つのページに複数の device の register が入る場合（BCM2837 の周辺は 4 KiB のページに密に並ぶ）、同じページを持つ部品は同じ信頼の境界に入ります。ページの割り当ては driver ごとの計画で表にします。

### DMA と cache

- IOMMU がないため、DMA を使える driver（SD の SDHOST・EMMC、USB の DWC2、SPI・I2S の DMA、DMA controller）は、任意の物理メモリを読み書きできます。capability による分離は、DMA には効きません。
- 中央の DMA controller を使う device と、自分で bus master になる device では評価が違います。device ごとの評価と PIO・DMA の方針の案は [dma-iommu.md](../drivers/dma-iommu.md) にあります。
- このため、DMA を使う driver は信頼する部品（trusted computing base）に数え、[threat-model.md](../security/threat-model.md) と形式検証の範囲の説明に明記します。
- DMA の buffer は専用の `Untyped` から作り、物理 address を driver に渡します。Cortex-A53 と DMA の間の cache の一貫性は、cache の clean・invalidate を driver が行う前提にします。具体の手順は driver ごとに調べます（未確認）。

### fault

- 部品の fault は、その部品を管理する部品（supervisor）の endpoint に届けます。supervisor は部品を止めるか、作り直します。
- 状態を持つ部品（storage、更新）は、作り直したときに、永続の状態から戻せるように設計します。

## 未確認

- 512 MiB を使うときの DTS の変更が、検証済み構成からの差分になるか（[verified-config-deviations.md](verified-config-deviations.md) に記録するかの判断）。
- BCM2837 の周辺の register の配置で、1 ページを共有する device の組。
- DMA と cache の一貫性の扱い（VideoCore の bus address の別名を含む）。

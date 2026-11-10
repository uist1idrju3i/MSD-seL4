# HDMI

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。HDMI の connector と出力そのものは、MSD/Linux の [HDMI の調査](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/docs/research/hardware/hdmi-output.md) にまとまっています。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| connector | 回路図 p.10 の J5、19 pin の `HDMI-001`。形と実際の出力は未確認 | MSD/Linux の配線の監査 |
| 部品 | HDMI（`0x7E902000`、`0x7E808000`）、HVS、pixelvalve、DDC は BSC2 | `rpi3.dts` |
| Linux | `DRM_VC4`（KMS） | MSD/Linux の [ハードウェア仕様](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/docs/research/hardware/hardware-spec.md) |

## 選択肢

| 案 | 内容 | 利点 | 欠点 |
|---|---|---|---|
| A: firmware の frame buffer | mailbox の property で firmware に frame buffer を確保させ、そこへ書く | 小さい。HDMI の register に触れない | 解像度の変更、hotplug、音声に限りがある。VideoCore の firmware に頼る |
| B: HVS と HDMI を直接制御 | Linux の vc4 と同じく、display の pipeline を自分で設定 | 柔軟 | 公開の資料がほとんどなく、規模が大きい。HDCP や音声は難しい |
| C: 作らない | HDMI を使わない | 作業がない | 外部の画面に出せない |

どの案でも、画面の data は VideoCore（HVS）がメモリから読みます。VideoCore は「全メモリに届く部品」です（[dma-iommu.md](dma-iommu.md) の決定）。

## 設計の検討

- 推奨は A です。mailbox の driver に frame buffer の property だけを許可表で加え、画面の合成の部品が frame buffer を共有メモリとして受け取ります。
- frame buffer の物理 address は firmware が決めるので、mailbox の driver はその範囲が予約されたメモリの中にあることを検査します。
- hotplug（HDMI の抜き差し）の検出は、HDMI の register か GPIO を使います。案 A では起動時に接続されていた場合だけ出力します。

## 試験

| 範囲 | 確かめること |
|---|---|
| host | property の message の生成と検査 |
| QEMU | mailbox の frame buffer の property は QEMU が一部を実装（出力は QEMU の画面）。HDMI はない |
| 実機 | 出力、解像度、hotplug、connector の形 |

## 決めること

1. HDMI の案。推奨: A（firmware の frame buffer）。

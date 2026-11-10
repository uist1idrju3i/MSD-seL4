# microSD（SDHOST、EMMC）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| socket | U17。SD_3V3 は VSYS_3V3 から。card の検出（SW）は NC | 回路図 p.6 |
| CM0 側 | CM0Lite（eMMC なし）では外部の SDIO で microSD を使う。SD_VREF は R75 0 ohm で CM0_3V3 | CM0 の datasheet、回路図 p.5 |
| controller | SDHOST（`0x3F202000`、`<2 24>`）と EMMC（Arasan の SDHCI、`0x3F300000`、`<2 30>`）。どちらを microSD に使い、どちらを Wi-Fi の SDIO に使うかは、firmware と DT の設定で決まる | `rpi3.dts`、BCM2835 ARM Peripherals |

Raspberry Pi の Linux では、microSD に SDHOST を、Wi-Fi（SDIO）に EMMC を使うのが通常の構成です。【推測。CardputerZero の config.txt では明示していないので、CM0 の DTS と実機で確かめる】pin の割り当ては GPIO48〜53 と GPIO34〜39 の alternate function で切り替わります。

## 何が大事か

microSD はこのプロジェクトの唯一の永続 storage で、boot の file、更新の image、利用者の data を置きます。電源断で壊さないこと、失敗した更新から戻れることは、この driver と、その上の storage の部品の設計で決まります。

## 設計の検討

- 部品の分け方: SD の driver（card の初期化、block の読み書き）と、その上の storage の部品（partition、A/B、journal、書き込みの方針）を分けます。SD の driver は block の番号と長さだけを扱い、file system を解釈しません。
- 外部からの入力: card の内容（MBR、file system）は攻撃者が用意できます。解釈は storage の部品で行い、Rust などで書く候補にします（[rust-adoption.md](../sel4/rust-adoption.md)）。
- DMA: SDHOST は中央の DMA controller を使うので、DMA server を通します。EMMC は bus master かどうかを確かめるまでは bus master として扱います（[dma-iommu.md](dma-iommu.md) の決定）。最初の版は PIO で作ります。QEMU の SDHOST は DMA を実装していません。
- 書き込みの方針: AGENTS.md §11 により、利用者が操作していない時や progress を表示していない時は書き込みません。SD の driver は、storage の部品からの依頼だけを受け、ほかの部品に書き込みの interface を渡しません。
- 電源断: SD card の中の controller が書き込み中の電源断にどう振る舞うかは card ごとに違い、software では保証できません。書き込みの単位（erase block）をまたぐ更新を避け、更新は新しい場所に書いてから切り替えます。
- cache: block の data の buffer は、DMA の前後で cache を clean・invalidate します。QEMU は cache を模擬しないので、この誤りは実機でしか見つかりません。

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| SDHOST の page | SD の driver だけが持つ |
| GPIO の部品 | 起動後に pin の機能を変える場合だけ |
| DMA server | DMA の転送 |
| mailbox | SD の clock や電源を firmware に依頼する場合 |

## 試験

| 範囲 | 確かめること |
|---|---|
| host | 範囲の検査、命令の列 |
| QEMU | SDHOST の PIO の手順、block の読み書き（QEMU の raspi3b の SD） |
| 実機 | card の初期化、速度、電源断の反復（experiment-record で記録）、複数の銘柄の card |

## 決めること

1. microSD に SDHOST と EMMC のどちらを使うか。推奨: SDHOST。中央の DMA を使うので DMA server で範囲を限れる。EMMC は Wi-Fi の SDIO に残す。

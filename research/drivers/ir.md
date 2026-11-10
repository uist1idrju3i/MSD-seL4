# IR（赤外線の送受信）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| 受信 | XL-IRM-V838M3（U21）、GPIO13 | 回路図 p.7 |
| 送信 | GPIO12 から Q5 で LED を駆動 | 回路図 p.7 |
| Linux | 公式 OS の config に IR の overlay はない | MSD/Linux の [ハードウェア仕様](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/docs/research/hardware/hardware-spec.md) |

## 設計の検討

- 送信: 38 kHz 前後の搬送波を、data に合わせて on・off します。GPIO12 は PWM0 の alternate function（ALT0）にできるので、SoC の PWM で搬送波を作り、on・off の時間だけ software で決めます。【一次。BCM2835 ARM Peripherals の alternate function の表で GPIO12 が PWM0】受信の部品が搬送波の周波数を決めるので、protocol（NEC、RC5 など）ごとに変えられるようにします。
- 受信: 受信の module は復調した信号を出します。GPIO13 の両方の edge の割り込みで時刻を記録し、pulse の幅の列を client に渡します。protocol の解釈は client（または別の部品）で行い、外部からの入力を解析する部分を小さく分けます。
- 時刻の分解能: 割り込みの遅れが pulse の幅（NEC で約 560 us）に比べて小さいか確かめます。seL4 の割り込みは通知を経て userland に届くので、遅れは Linux より大きいかもしれません。【未確認。QEMU では測れないので、実機で測る】
- 権限: PWM の page（`0x3F20C000`）は IR の driver だけが持ちます。PWM の clock は clock manager にあるので、clock の部品か mailbox に設定を依頼します（[soc-blocks.md](soc-blocks.md)）。
- 外部からの入力: 受信した pulse は誰でも送れます。長さと件数の上限を決め、解析の部品で範囲を検査します。

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| GPIO の部品 | GPIO13 の edge の通知、GPIO12 の機能の設定 |
| PWM | 搬送波（`0x3F20C000` の page） |
| clock | PWM の clock |

## 試験

| 範囲 | 確かめること |
|---|---|
| host | pulse の列の解析（NEC など）、範囲の検査 |
| QEMU | GPIO の割り込みの経路だけ。QEMU の raspi3b に PWM の実装があるかは確かめていない |
| 実機 | 受信（市販の remote control）、送信（受信の module で受ける）、割り込みの遅れ |

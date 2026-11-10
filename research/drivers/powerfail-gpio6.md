# 電源異常（GPIO6）と電源の保持

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md) / [M5IOE1](m5ioe1.md)

2026-11-11 に調べました。実機では何も確かめていません。電源断で system を壊さないことは、このプロジェクトの目標の 1 つです。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| 検出 | 電源スイッチ（SW_EN）の分圧から GPIO6（SW_DET）と PYG5（PWR_DET） | 回路図 p.4 |
| 保持 | SW_EN と PYG14_PWR_EN を diode で合わせた VSYS_PW_EN が U7（CM0 側の昇圧）の EN | 回路図 p.4 |
| Linux の設定 | GPIO6 の falling edge、500 ms の debounce、LOW を有効とする | v5 overlay 288 行 |
| Linux の処理 | debounce の後に GPIO6 を読み直し、SysRq `u`（全 filesystem を読み取り専用にする）を呼ぶ。SysRq `s`（sync）はコメントアウト。最後に `disabled-gpios`（M5IOE1 の index 11）を出力 | [`powerfail_suo.c`](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/CardputerZero/powerfail_suo.c) 36〜115 行（GPL-2.0） |

MSD/Linux は、この処理に filesystem の sync と userland への通知を加える patch を持っています。それでも、通常の shutdown や実機の電源の保持時間は保証していません（MSD/Linux の [ハードウェア仕様](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/docs/research/hardware/hardware-spec.md)）。

## 分かっていないこと

- スイッチを切ってから、CM0 の電源が実際に落ちるまでの時間。PYG14 で電源を保持できるか、保持できるならどれだけの時間か。【未確認。実機の測定が要る】
- 電池が外れる、または電池が切れるときの電源断では、GPIO6 が動かない可能性があります。【推測】この場合は、何も知らせずに電源が落ちます。

## 設計の検討

- 電源断で壊さない設計の本体は、電源異常の通知ではなく storage の書き方（atomic な更新、A/B、journal）です。通知は「書き込みを始めない」「書きかけを終える」ための補助と考えます。電源異常の通知が来ないまま電源が落ちても壊れないことを、まず storage の設計で保証します。
- 電源異常の部品: GPIO の部品から GPIO6 の通知を受け、debounce の後に、storage の部品へ「新しい書き込みを止める」通知を送ります。M5IOE1 の部品へは、電源を保持する・切るの依頼を送ります。
- 優先度: GPIO の部品と電源異常の部品は、ほかの部品より優先度を高くします。seL4 の非 MCS の scheduler は固定優先度なので、優先度の表を capDL の generator で決めます。
- debounce: Linux の 500 ms は、スイッチの chattering を除くための値と見られます。電源を保持できない場合、500 ms 待つ間に電源が落ちるかもしれません。測定の後で決めます。

## 試験

| 範囲 | 確かめること |
|---|---|
| host | debounce と状態の遷移 |
| QEMU | GPIO の割り込みの経路だけ。電源断は再現できない |
| 実機 | スイッチを切ってから電源が落ちるまでの時間（oscilloscope か、GPIO の toggle を外部で記録）、PYG14 の保持、電池を外したときの動作、電源断の反復試験（experiment-record で記録） |

## 決めること

1. 電源異常の通知を、storage の安全性の前提にするか。推奨: 前提にしない。通知がなくても壊れない storage の設計にし、通知は補助にする。

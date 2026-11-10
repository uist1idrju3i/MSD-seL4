# 電池（BQ27220 燃料計、IP2315 充電器）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| 燃料計 | BQ27220YZFR（U4）。I2C1 から level translator U6 を通る BQ_I2C1 の 7-bit address 0x55。10 mohm の R15 と BAT_NTC | 回路図 p.3 |
| 設計値 | 3.7 V、1,750 mAh（v5 用の overlay） | [`bq27220_v5.dts`](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/bq27220-1.0/bq27220_v5.dts) 17〜18 行 |
| 充電器 | IP2315（U1）。USB 入力を優先する独立した充電の経路。I2C はない | 回路図 p.3、部品台帳 |
| 入力の選択 | TPS2116（U5）が右の USB-C と外部入力から VCHG_5V を選ぶ | 回路図 p.3 |

BQ27220 の Linux driver（`bq27xxx_battery*.c`）は GPL-2.0 で、写しません。TI の datasheet と Technical Reference Manual（TRM）の command（`Voltage`、`Current`、`RemainingCapacity`、`StateOfCharge` など）を一次資料にします。

## 設計の検討

- 燃料計の driver は、電圧、電流、残量、温度を読み、client に渡すだけにします。読み取りは standard command だけで、data memory（設計容量などの設定）への書き込みは既定で行いません。
- 設計容量: M5Stack の overlay の 1,750 mAh は Linux の driver に渡す値です。BQ27220 の data memory に入っている値と同じかは分かっていません。【未確認。実機で読む】data memory を書き換えると、燃料計の学習の状態が変わります。書き換えは利用者の明示の操作でだけ行い、AGENTS.md §11 の対象（時間がかかり得る処理）として progress を表示します。
- 充電器（IP2315）は software から制御も監視もできません。充電中かどうかは、燃料計の電流の符号から推定します。
- 残量が少ないとき: 残量の閾値で、利用者に知らせ、新しい書き込み（更新など）を始めないようにします。

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| I2C の部品 | address 0x55 だけの読み書き。data memory への書き込みは、許可表で別の操作として分ける |

## 試験

| 範囲 | 確かめること |
|---|---|
| host | 単位の変換、範囲の検査 |
| QEMU | I2C の手順だけ |
| 実機 | 各値、充電中と放電中の電流、data memory の設計容量、低残量の閾値 |

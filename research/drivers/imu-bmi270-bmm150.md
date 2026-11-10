# IMU（BMI270、BMM150）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。CardputerZero Standard だけにあり、Lite にはありません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| 加速度・角速度 | BMI270（U18）。I2C1 の 7-bit address 0x68（SDO を R96 10k で pull-down） | 回路図 p.7、[overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/imu-1.0/bmi270_bmm150_overlay.dts) 17 行 |
| 地磁気 | BMM150（U20）。BMI270 の AUX の I2C（ASDx・ASCx）の address 0x10 | 回路図 p.7、overlay 27 行 |
| 割り込み | INT1・INT2 は NC。polling で読む | 回路図 p.7 |

BMM150 は主の I2C1 の上にはありません。ES8389（I2C1 の 0x10）と address は同じですが、別の bus なので衝突しません（MSD/Linux の配線の監査）。

## 初期化

- BMI270 は、起動のたびに 8 KiB の設定 data を `INIT_DATA`（0x5E）へ書き込む必要があります。M5Stack は [`bmi270-init-data.fw`](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/imu-1.0/bmi270-init-data.fw)（8,192 byte）を使います（`bmi270_core.c` 92・118 行）。
- この data の元は Bosch の BMI270 Sensor API と見られます。Bosch の Sensor API は BSD-3-Clause で公開されています。【推測。M5Stack の file と Bosch の配布物が同じかは hash で照合していない】
- BMI270 の Linux driver は `(GPL-2.0-only OR BSD-2-Clause)` の dual license です。BSD-2-Clause を選べば、著作権表示を残して参照・利用できます（AGENTS.md §4）。BMM150 の driver（`bmc150_magn*.c`）は GPL-2.0-only なので、写しません。
- 100 kHz の I2C で 8 KiB を書くと、約 0.8 秒かかります（計算値）。起動の時間に入るので、IMU は必要になってから初期化します。

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| I2C の部品 | address 0x68 だけの読み書き。BMM150 には BMI270 の AUX の register を通して触れる |

## 設計の検討

- 設定 data は、ROM に置く固定の data として部品に入れます。永続 storage から読む場合は、hash を検査します。
- 割り込みがないので、client が要求した周期で読みます。周期の上限を決め、I2C の bus を占めすぎないようにします（キーボードの応答を遅らせないため）。
- Lite では device が応答しません。応答がなければ「device なし」として client に返し、起動を止めません。

## 試験

| 範囲 | 確かめること |
|---|---|
| host | 単位の変換、範囲の検査、AUX の手順 |
| QEMU | I2C の手順だけ。BMI270 は QEMU にない |
| 実機 | chip ID、設定 data の書き込みと `INTERNAL_STATUS`、測定値、BMM150 の AUX 経由の読み出し、Lite での応答なし |

## 決めること

1. 設定 data の出典を Bosch の配布物にするか。推奨: Bosch の BSD-3-Clause の配布物から取り、hash と版を記録する。

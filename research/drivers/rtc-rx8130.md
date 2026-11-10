# RTC（RX8130）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| 部品 | RX8130CE:B3（U19） | 回路図 p.7 |
| 接続 | I2C1 の 7-bit address 0x32 | 回路図 p.7、v5 overlay 81 行 |
| 割り込み・出力 | nIRQ、nRSTO、FOUT は NC | 回路図 p.7 |
| backup | BAT1 は NC の表記、R95 は 0 ohm | 回路図 p.7 |
| Linux | upstream の `rtc-ds1307`（`CONFIG_RTC_DRV_DS1307`）が `epson,rx8130` に対応 | MSD/Linux の [ハードウェア仕様](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/docs/research/hardware/hardware-spec.md) |

M5Stack の単独の [rx8130 overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/rx8130/rx8130-overlay.dts) は address を 0x68 としていますが、v5 overlay と回路図は 0x32 です。0x68 は BMI270 の address なので、単独の overlay は CardputerZero 用ではないと見られます。【推測】0x32 を使います。

## 分かっていないこと

- 電源を切った間に時刻を保てるか。BAT1 が NC の表記なので、backup 用の電池が載っていない可能性があります。この場合、電池（VBAT）から RTC へ給電が続くかどうかで、時刻の保持が決まります。【未確認。実機で電源を切って確かめる】
- RX8130 の電源断の検出（`VLF` などの flag）を読めば、時刻が信用できるかを判断できます。【一次。Epson の application manual で bit の名前を確かめる】

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| I2C の部品 | address 0x32 だけの読み書き |

## 設計の検討

- 時刻の部品は、起動時に RTC を読み、時刻が信用できないとき（電源断の flag が立っている、年が範囲外）は「時刻なし」として扱います。署名の検査など、時刻を使う処理は、時刻なしの場合の動作を決めておきます。
- 書き込み: RTC への書き込みは利用者の設定か、network の時刻の同期のときだけにします。RTC は microSD ではないので、AGENTS.md §11 の永続 storage の規則の対象外です。
- 割り込みがないので、alarm は使えません。

## 試験

| 範囲 | 確かめること |
|---|---|
| host | BCD の変換、範囲の検査、flag の判定 |
| QEMU | I2C の手順だけ |
| 実機 | 読み書き、電源を切った後の保持、電源断の flag |

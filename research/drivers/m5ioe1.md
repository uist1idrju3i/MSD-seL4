# IO expander（M5IOE1）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。M5IOE1 は M5Stack 独自の MCU で、公開の datasheet は見つかっていません。register の情報は M5Stack の Linux driver（[`m5ioe1.c`](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/m5ioe1-1.0/m5ioe1.c)、GPL-2.0-only）から読んだもので、仕様を読む資料にだけ使います。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| 部品 | M5IOE1（U14）。回路図の見出しは M5IOM1 | 回路図 p.6 |
| 接続 | I2C1、7-bit address 0x4f、16 本の GPIO と PWM | v5 overlay 45 行 |
| reset | SoC の GPIO16、R80 100k で pull-up | 回路図 p.6 |
| 電源 | VSYS_3V3 | 部品台帳 |

## 何を制御するか

物理の PYG 番号と、DT の GPIO の index（0 始まり）は別の番号です（MSD/Linux の配線の監査）。

| PYG | 用途 | DT での参照 |
|---|---|---|
| PYG1 | HAT の P0・P1 を GPIO26・23 と USB4 で切り替え | `ext_usb_gpio_fun`（index 0） |
| PYG2 | hardware の版の検出（分圧、ADC） | なし |
| PYG3 | キーボードと USB hub の共有 reset | `rest-gpios = <&m5ioe1 2 1>` |
| PYG4 | Grove の 5V 出力 | `grove_5v_out`（index 3） |
| PYG5 | 電源の検出 | なし |
| PYG6 | マイクの CTIA・OMTP の切り替え | なし |
| PYG8・9・11 | キーボードの LED | `capslock-led-gpio` など |
| PYG10 | LCD の backlight の PWM | `pwms = <&m5ioe1 3 ...>` |
| PYG12 | LCD の reset | なし |
| PYG13 | HAT の 5V・3.3V の出力 | `ext_5v_out`（index 12） |
| PYG14 | 電源の保持（VSYS_PW_EN） | powerfail の `disabled-gpios = <&m5ioe1 11 1>` が関係する可能性。【未確認】 |

## register（M5Stack の driver による）

`UID` 0x00〜0x01、`REV` 0x02、GPIO の向き・出力・入力・pull・割り込み 0x03〜0x14、ADC 0x15〜0x17、温度 0x18〜0x1A、PWM1〜4 0x1B〜0x22、`IIC_CFG` 0x23、`LED_CFG` 0x24、PWM の周波数 0x25〜0x26（既定 0x01F4 = 500）、`RESET` 0x29、LED の RAM 0x30〜0x6F、RTC の RAM 0x70〜0x8F、`READY` 0xB0、`OFF_TIME` 0xB2、`HW_VERSION` 0xB8、`VERSION` 0xBA。

M5Stack の driver は、起動時に GPIO16 で M5IOE1 を reset し、`REV` を読み、特定の版なら `READY` に書きます（`m5ioe1.c` 1232〜1302 行）。`READY` を書かないと MCU が何をするか（たとえば一定時間後に電源を切るか）は分かっていません。【未確認。M5Stack に問い合わせるか、実機で確かめる】

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| I2C の部品 | address 0x4f だけの読み書き |
| GPIO の部品 | GPIO16（reset） |

## 設計の検討

M5IOE1 は電源、reset、LCD、キーボード、USB hub、拡張端子の電源を 1 つで制御します。乗っ取られたり誤動作したりすると、電源を切る、USB hub を reset し続ける、HAT に 5V を出す、といったことができます。このため次のようにします。

- M5IOE1 の部品を 1 つ置き、各 client には「この PYG のこの操作だけ」を許す IPC の interface を渡します。許可表は capDL の generator が作る静的な表にします。例: LCD の driver は PYG10（PWM）と PYG12（reset）だけ、キーボードの driver は LED の 3 本だけ。
- PYG3（共有 reset）と PYG14（電源の保持）はどの client にも渡さず、M5IOE1 の部品が起動の手順の中でだけ動かします。
- 外部の電源（Grove の PYG4、HAT の PYG13）は既定で off にし、利用者の設定でだけ on にします。hot-swap はしない仕様（製品ページ）なので、on の間に取り外さないよう画面に表示します。
- 電源断: M5IOE1 が電源の保持にどこまで関わるかが分かっていないため、電源異常の処理（[powerfail-gpio6.md](powerfail-gpio6.md)）とあわせて実機で確かめます。

## 試験

| 範囲 | 確かめること |
|---|---|
| host | 許可表の検査（許されない PYG・操作を拒む） |
| QEMU | I2C の手順だけ。M5IOE1 は QEMU にない |
| 実機 | `REV`・`VERSION` の値、各 PYG の動作、PWM の周波数と duty、`READY` を書かないときの動作、reset の順序 |

## 決めること

1. register の仕様が GPL の driver にしかないことの扱い。推奨: M5Stack に仕様の公開を問い合わせる（外部への連絡なので利用者の承認が要る）。それまでは register の番号と意味だけを事実として使い、code は写さない。
2. 外部の電源（Grove、HAT）の既定。推奨: off。

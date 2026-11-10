# キーボード（TCA8418）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| 部品 | TCA8418RTWR（U27）。5 行×10 列の matrix に 46 キー | 回路図 p.8、MSD/Linux の配線の監査 |
| 接続 | I2C1、7-bit address 0x34 | v5 overlay 88 行 |
| 割り込み | GPIO27、active-low、R124 100k で pull-up。v5 overlay は level（low）の trigger | v5 overlay 88 行〜 |
| reset | M5IOE1 の PYG3。USB hub（GL852G）の reset と共有 | 回路図 p.6・p.8 |
| LED | CapsLock、Fn、table の切り替えの LED は M5IOE1 の pin | v5 overlay の `capslock-led-gpio` など |
| 配列 | v5 overlay の `linux,keymap` と `linux,keymap2`（Fn を押したときの配列） | v5 overlay |

TCA8418 の register（`CFG` 0x01、`INT_STAT` 0x02、`KEY_LCK_EC` 0x03、`KEY_EVENT_A`〜`J` 0x04〜0x0D、`KP_GPIO1`〜`3` 0x1D〜0x1F など）は TI の datasheet にあります。M5Stack の driver（`tca8418_keypad_m5stack.c`、GPL）は同じ定義を使っています。

## 動作

- 押す・離すの event は、TCA8418 の中の FIFO（10 個）に入り、割り込みが出ます。driver は `INT_STAT` を読み、`KEY_LCK_EC` の件数だけ `KEY_EVENT_A` を読み、最後に `INT_STAT` を書いて割り込みを消します。
- M5Stack の driver は、Sym・Fn・Shift の状態を状態機械（`tca8418_fsm.c`）で持ち、one-shot、hold、lock を作っています。これは device の仕様ではなく M5Stack の設計です。MSD/seL4 では、状態機械を host で試験できる純粋な関数として自作します。
- 配列のうち、v5 overlay では Z・X・C と F のキーを `KEY_RESERVED`（無効）にしています。理由は書かれていません。【未確認。実機の刻印と照合する】

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| I2C の部品 | address 0x34 だけの読み書き |
| GPIO の部品 | GPIO27 の割り込みを通知で受ける |
| M5IOE1 の部品 | reset（PYG3）と LED |

キーボードの driver は device のメモリも IRQ の capability も持ちません。

## 設計の検討

- 外部からの入力: キーの操作は利用者の入力で、悪意のある data は来ません。ただし I2C の値は壊れることがあるので、行・列の範囲を検査します。
- reset の共有: PYG3 を動かすと USB hub も reset されます。キーボードの driver には reset の権限を渡さず、M5IOE1 の部品が「起動時に 1 回だけ」reset します。reset の順序（キーボードと hub の初期化の前）は M5IOE1 の部品の設計に入れます。
- 割り込みが来ない場合: GPIO27 の割り込みが止まったときのために、低い頻度（例: 1 秒ごと）で `INT_STAT` を読む予備の polling を入れます。電力を使うので、実機で必要か確かめます。
- event の client: 押したキーは、input の部品へ queue（共有メモリ）と通知で渡します。queue があふれたら古い event を捨て、件数を数えます。
- 電源断: キーボードは状態を持たないので、電源断の影響はありません。

## 試験

| 範囲 | 確かめること |
|---|---|
| host | 状態機械（Sym・Fn・Shift、one-shot、lock）、配列の表、範囲の検査 |
| QEMU | I2C の手順と GPIO の通知だけ。TCA8418 は QEMU にない |
| 実機 | 46 キーと配列、割り込み、長押し、同時押し、LED、reset の順序 |

## 決めること

1. 無効にされているキー（Z・X・C・F）の扱い。推奨: 実機で刻印と matrix を確かめ、使えるなら有効にする。
2. Fn の配列（keymap2）を M5Stack と同じにするか。推奨: 同じにする。利用者が公式 OS と同じ操作で使えるため。

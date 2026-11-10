# 音声（ES8389、PCM・I2S、アンプ）

[driver の状況へ戻る](README.md) / [SoC の共通の部品](soc-blocks.md)

2026-11-11 に調べました。実機では何も確かめていません。

## device

| 項目 | 内容 | 出典 |
|---|---|---|
| codec | ES8389（U30）。I2C1 の 7-bit address 0x10。v5 overlay の compatible は `everest,es8390` | 回路図 p.9、v5 overlay 69 行 |
| I2S | GPIO18 BCLK、19 LRCK、20 DIN、21 DOUT。SoC の PCM が clock の master | v5 overlay 378 行〜（`bitclock-master`、`frame-master` が CPU 側） |
| MCLK | GPIO21 から 0 ohm の R160 を通る経路がある。overlay の fixed-clock は 12.288 MHz | 回路図 p.9、v5 overlay 298 行 |
| アンプ | AW8737A（U31）。GPIO24 から Q7 などを通る AW_SPK_EN | 回路図 p.9、v5 overlay 335 行 |
| ヘッドホンの検出 | GPIO17（HP_DET） | v5 overlay の `hp-det-gpios` |
| マイクの切り替え | U32 FSW7227 を M5IOE1 の PYG6 で切り替え（LOW CTIA、HIGH OMTP） | 回路図 p.9 |
| マイク | MEMS マイク（U29）、3.5 mm の TRRS | 回路図 p.9 |

ES8389 と ES8390 は Everest の別の型番です。物理の部品名は ES8389 で、compatible の名前に合わせて部品名を変えません。register の情報は M5Stack の [`es8389_m5stack.c`](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/4f7aeee9fc103ebb03d22cac476bb191ecfb321e/modules/es8389-1.0/es8389_m5stack.c)（GPL-2.0-only）にあります。公開の datasheet を確かめていません。【未確認。Everest の datasheet を入手する】

## 経路の切り替え

M5Stack の machine driver（`cardputerzero-audio.c`）は、ヘッドホンの有無で codec の入力（Line 1 と Line 2）を切り替え、ヘッドホンがあるときはスピーカーを mute します（v5 overlay の `hp-absent-controls`、`hp-present-controls`）。

## 依存と権限

| 依存 | 使う理由 |
|---|---|
| I2C の部品 | codec の設定（address 0x10 だけ） |
| PCM・I2S | 音声の data。PCM の register は単独の page（`0x3F203000`） |
| clock | PCM の clock（`CM_PCMCTL`）。clock manager の page は共有（[soc-blocks.md](soc-blocks.md)） |
| DMA server | 再生と録音の転送（[dma-iommu.md](dma-iommu.md) の決定で既定） |
| GPIO の部品 | GPIO24（アンプ）、GPIO17（検出の通知） |
| M5IOE1 の部品 | PYG6（マイクの切り替え） |

## 設計の検討

- 部品の分け方: 音声の driver（PCM と codec の設定、経路の切り替え）を 1 つにします。PCM の page は単独なので、PCM の capability はこの driver だけが持ちます。
- 転送: 48 kHz の stereo、16 bit で毎秒 192,000 byte です。DMA server に循環する buffer を登録し、半分ずつの割り込みで client に通知します。DMA server ができるまでは PCM の FIFO の割り込みで PIO にします。
- clock: 12.288 MHz（48 kHz×256）を作るには PCM の clock の分周が要ります。PLL の出力と分周の値は datasheet で計算し、clock manager か mailbox で設定します。【未確認。overlay の fixed-clock は値の宣言で、実際の波形は測っていない】
- スピーカーの保護: アンプの enable（GPIO24）を、data の準備ができてから on にし、止めるときは先に off にします。起動の直後の雑音を避けるためです。
- 電源断: 音声は状態を持たないので、電源断の影響はありません。

## 試験

| 範囲 | 確かめること |
|---|---|
| host | 経路の切り替えの状態、buffer の範囲の検査 |
| QEMU | なし。QEMU の raspi3b は PCM を実装していない（`create_unimp`） |
| 実機 | 再生、録音、ヘッドホンの検出と切り替え、CTIA・OMTP、アンプの on・off の雑音、clock の周波数 |

## 決めること

1. QEMU で試せないため、最初から実機で試すことになります。推奨: 音声は後の段階にし、I2C、GPIO、LCD、キーボードを先に作る。

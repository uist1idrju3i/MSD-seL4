---
name: sel4-driver
description: CardputerZero の device（LCD、キーボード、I2C、SPI、GPIO、音声、センサー、RTC、電池、IR、カメラ、Wi-Fi・Bluetooth、USB、Ethernet、HDMI、microSD など）の driver を seL4 のユーザー空間に作るときに使う。driver ごとに調査と計画を立て、利用者の確認を得てから実装する。
---

# sel4-driver（ユーザー空間の driver）

driver は seL4 のユーザー空間で、device ごとに独立した保護ドメインとして自作します。driver ごとに深い調査と深い計画を立て、利用者の確認を得てから実装します。

## 1. 調査

調査は `research/drivers/<device>.md` に、一次資料の出典（datasheet、Linux の driver と DTS の固定 commit と行番号、M5Stack の資料）を付けて書きます。

- device: 部品名、接続（bus、アドレス、pin、割り込み、reset、電源）、CardputerZero での配線。MSD/Linux の調査（`research/` の hardware の文書）と `vendor/m5stack-linux-dtoverlays` の DTS を照合します。
- 依存: その device が必要とする bus の driver（I2C、SPI、GPIO、DMA、clock、mailbox）と、それらの保護ドメイン。
- 初期化と動作: register の手順、timing、firmware の要否、Raspberry Pi firmware に頼る部分。
- 既存の実装: sDDF、Microkit、seL4 の libplatsupport、他の OS（Linux、U-Boot、Circle など）の driver。ライセンスを書き、GPL のコードは仕様を読む資料にだけ使い、写しません（AGENTS.md §4）。
- 権限: 必要な device のメモリ、IRQ、DMA の有無、共有メモリと通知。
- 検証: QEMU で確かめられる範囲（QEMU の `raspi3b` が対象の device を再現するか）と、実機でしか確かめられない範囲。

## 2. 計画

計画はチャットで利用者に送り、確認を得ます。計画には次を含めます。

- 保護ドメインと capability の表（「sel4-capability-design」スキル）
- client との interface（共有メモリの queue、通知、メッセージの形式）
- 障害時の動作（device が応答しない、割り込みが来ない、不正な入力）と、電源断の影響
- 試験の計画（host での単体試験、QEMU、実機の手順と合否の基準）
- 利用者に決めていただく点（選択肢、利点、欠点、推奨）

## 3. 実装

- コードとコメントは英語で書き、`SPDX-License-Identifier: BSD-3-Clause` を付けます。
- device のメモリと DMA の範囲を、渡された capability の範囲だけに限ります。client から受け取った値（長さ、index、アドレス）は全部検査します。
- busy-wait で CPU を使い続けず、割り込みと通知を使います。timeout を決めます。
- 永続 storage への書き込みと時間のかかる処理は、AGENTS.md §11 に従います。

## 4. 検証と報告

- host の単体試験、QEMU、実機の結果を分けて書きます。QEMU が再現しない device を、QEMU で確認済みと書きません。
- 実機の試験は「experiment-record」スキルで記録します。
- 対応表（README と `research/`）の状態を「未着手」「調査済み」「実装済み（QEMU）」「実装済み（実機確認）」のどれかで更新します。

## 提出前の確認

- [ ] 調査文書に一次資料の出典とライセンスがある
- [ ] 計画を利用者が確認した
- [ ] capability の表と実装が一致する
- [ ] GPL のコードを写していない
- [ ] 試験の範囲（host、QEMU、実機）を分けて書いた

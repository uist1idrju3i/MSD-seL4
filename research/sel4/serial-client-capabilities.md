<!-- SPDX-License-Identifier: BSD-3-Clause -->
# system の capability 表（自動生成）

`tools/capdl/generate.py` で生成します。手では編集しません。

| PD | slot（名前） | object | type | rights | badge | device / vaddr | DMA | 理由 |
|---|---|---|---|---|---|---|---|---|
| client | 1 (send) | o_serial_ep | endpoint | write | 1 | なし | なし | badge 1 で識別される送信。capability の転送は許さない |
| serial | 1 (uart) | o_uart | device | read, write | なし | 0x3f201000 / 0x40000000 | なし | PL011 の status 読み取りと送信 register 書き込み |
| serial | 2 (receive) | o_serial_ep | endpoint | read | 0 | なし | なし | client からの IPC の受信だけを許す |

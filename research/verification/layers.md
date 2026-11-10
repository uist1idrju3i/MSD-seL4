# 確認の階層

[索引へ戻る](../README.md)

| 階層 | 確かめられること | 確かめられないこと |
|---|---|---|
| 証明（seL4 の l4v） | 検証済み構成の kernel の性質（[verified-configuration.md](../sel4/verified-configuration.md)） | 起動処理、driver、アプリケーション、ハードウェア |
| 構成の検査（CI） | 検証済み構成で kernel を build できること、構成からの差分がないこと、capability の表と記述の一致 | 実行時の動作 |
| host の試験 | driver と部品の論理（device を模したもの） | 実際の device |
| QEMU（`raspi3b`） | kernel と部品の起動、UART、timer、QEMU が再現する device | LCD、キーボード、M5 の I2C device、音声、カメラ、無線、HDMI、GPU firmware の tryboot、電源断 |
| 実機（CardputerZero） | すべての device と電源断 | - |

QEMU の起動成功を、実機の device や電源断の確認と扱いません。

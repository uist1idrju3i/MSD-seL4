# 起動経路と A/B 更新

[索引へ戻る](../README.md)

## 一次資料から確かめたこと

[Rpi3 のページ](https://docs.sel4.systems/Hardware/Rpi3.html) によると、Raspberry Pi 3 は SD card の第 1 パーティション（FAT32）から、ROM → `bootcode.bin` → GPU firmware（`start.elf`）→ `config.txt` の `kernel=` で指定した image の順に起動します。既定の U-Boot は seL4 の elfloader の cache の設定と合わず、cache を無効にする U-Boot（commit `995eab8b` を戻したもの）が必要と書かれています。sel4test は `-DPLATFORM=bcm2837 -DAARCH32=1` で build します。

seL4 17.0.0 の `CHANGES.md` によると、AArch64 の kernel image は 2 MiB 境界に置かれ、rpi3・rpi4・rpi5 では RAM 先頭の最大 2 MiB が device untyped になります。

MSD/Linux は、GPU firmware の `autoboot.txt` と `tryboot` を使って A/B の boot パーティションを切り替え、試験起動に失敗したら前のスロットへ戻ります（[MSD/Linux の README](https://github.com/uist1idrju3i/MSD-Linux/blob/34ab582/README.md)）。

## 推測

- elfloader の image を `config.txt` の `kernel=` で直接起動できれば、U-Boot なしで MSD/Linux と同じ `autoboot.txt` + `tryboot` の A/B を使えます。U-Boot を使う場合は、U-Boot も信頼する部品に加わり、cache の問題への対処が必要です。
- 起動処理（GPU firmware、elfloader、kernel の起動）は証明の対象外です。更新の署名検証をどこで行うか（seL4 の上の更新部品が書き込む前に検証する、など）を決める必要があります。

## 未確認

- elfloader の直接起動、`tryboot` の動作、512 MB の RAM の扱い、`armstub` と secondary core の扱い。

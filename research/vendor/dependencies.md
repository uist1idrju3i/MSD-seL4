# 依存の固定版とライセンス

[索引へ戻る](../README.md)

| path | upstream | 固定先 | ライセンス | 採用の理由 |
|---|---|---|---|---|
| `vendor/seL4` | https://github.com/seL4/seL4 | tag `17.0.0`（commit `62e345c240a15671484530b4e6e069ce266c28d7`、2026-10-30） | kernel は主に GPL-2.0-only、`libsel4` は BSD-2-Clause | 製品の kernel。改変せずに build する |
| `vendor/seL4_tools` | https://github.com/seL4/seL4_tools | `master` の `6493e0c6fab360eb81a8115a49c9ca7bc280c48a`（`seL4/sel4test-manifest` の tag `17.0.0` が指す commit） | elfloader-tool と cmake-tool は主に GPL-2.0-only、一部 BSD-2-Clause・BSD-3-Clause | seL4 を起動する elfloader と、root task を含む image を作る CMake の helper。改変せずに build する。tag がないため、seL4 の release の manifest が指す commit に合わせる |
| `vendor/yomiyasu` | https://github.com/nanaism/yomiyasu | tag `v2.5.0`（commit `29d67ccb05e370b5958d72920a9cd1aa829dee80`） | MIT | 日本語文書の推敲スキル |
| `vendor/m5stack-linux-dtoverlays` | https://github.com/m5stack/m5stack-linux-dtoverlays | `main` の `4f7aeee9fc103ebb03d22cac476bb191ecfb321e`（2026-11-05） | GPL-2.0 WITH Linux-syscall-note（`COPYING`） | CardputerZero の配線と初期化の手順を読む資料。コードは写さない |

## 加えなかった起動部品

| 部品 | 判断 | 理由 |
|---|---|---|
| U-Boot | 今は加えない | rpi3 の公式手順は U-Boot から elfloader を起動するが、既定の U-Boot は elfloader の cache の扱いと合わない（[起動経路](../sel4/boot-chain.md)）。GPU firmware の `kernel=` で elfloader を直接起動できれば不要になり、信頼する部品も減る。直接起動の実験で失敗したときに、版と cache の対処を決めて加える |
| Raspberry Pi の GPU firmware（`bootcode.bin`、`start*.elf`、`fixup*.dat`） | submodule にしない | `raspberrypi/firmware` は履歴が数十 GB あり、shallow でも Linux kernel の image を含む。起動 image を作る段階で、release の tag と各ファイルの SHA-256 を固定して取得する。版は MSD/Linux の Buildroot が使う commit（`063bcab6`）を起点に比べる |
| Raspberry Pi の Linux kernel（`raspberrypi/linux`） | submodule にしない | 大きく、GPL。BCM2837 の周辺回路の driver を読む資料として、commit を固定した URL で参照する |
| seL4 の userland（`seL4_libs`、`sel4runtime`、`musllibc`、`util_libs`、capDL など） | userland の基盤を決めた後に加える | どれを使うかが基盤（[userland の基盤](../sel4/userland-frameworks.md)）で変わる。加えるときは、`sel4test-manifest` などの tag `17.0.0` が指す commit に合わせる |

## CardputerZero の公式の上流

m5stack の GitHub organization で CardputerZero に関わる repository は、次のとおりです（2026-11-11 に GitHub の検索で確認）。

| repository | 内容 | 扱い |
|---|---|---|
| `m5stack/m5stack-linux-dtoverlays` | CardputerZero の device tree overlay と Linux の driver | submodule。配線、I2C アドレス、割り込み、reset、電源の手順を確かめられる唯一の公式の一次資料のため残す |
| `m5stack/CardputerZeroRepository` | Debian の `.deb` を配る apt repository | 加えない。application の配布の仕組みで、ハードウェアの情報はない |
| `m5stack/CardputerZero-AppBuilder` | Linux の application の build の仕組み（MIT） | 加えない |
| `m5stack/M5Stack_Linux_Libs` | Linux 用の C/C++ の library（framebuffer、I2C、SPI、UART の wrapper、LVGL） | 加えない。Linux の device file を使う層で、レジスタの手順は含まない |

回路図と pin の対応は M5Stack の公式文書（docs.m5stack.com）で確かめます。文書は git repository ではないため、参照した日付と URL を driver の調査文書に記録します。

## seL4 17.0.0 で特に確認した変更（`vendor/seL4/CHANGES.md`）

- AArch64 の kernel image を 2 MiB 境界に置き、rpi3・rpi4・rpi5 では RAM 先頭の最大 2 MiB を device untyped にする変更。
- Arm の hypervisor 構成での debug register、PMU、各種 system register の扱いの強化（hypervisor を使わない本プロジェクトの既定の構成には直接は関係しない、推測）。
- AArch32 の FPU、CPACR、FPEXC などの context switch の修正、TEEHBR と Jazelle DBX へのアクセスの禁止。
- stale TLB・ASID の問題の修正。

全項目の採否は、seL4 を更新するときに「vendor-update」スキルで記録します。

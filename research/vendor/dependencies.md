# 依存の固定版とライセンス

[索引へ戻る](../README.md)

| path | upstream | 固定先 | ライセンス | 採用の理由 |
|---|---|---|---|---|
| `vendor/seL4` | https://github.com/seL4/seL4 | tag `17.0.0`（commit `62e345c240a15671484530b4e6e069ce266c28d7`、2026-10-30） | kernel は主に GPL-2.0-only、`libsel4` は BSD-2-Clause | 製品の kernel。改変せずに build する |
| `vendor/yomiyasu` | https://github.com/nanaism/yomiyasu | tag `v2.5.0`（commit `29d67ccb05e370b5958d72920a9cd1aa829dee80`） | MIT | 日本語文書の推敲スキル |
| `vendor/m5stack-linux-dtoverlays` | https://github.com/m5stack/m5stack-linux-dtoverlays | `main` の `4f7aeee9fc103ebb03d22cac476bb191ecfb321e`（2026-11-05） | GPL-2.0 WITH Linux-syscall-note（`COPYING`） | CardputerZero の配線と初期化の手順を読む資料。コードは写さない |

## seL4 17.0.0 で特に確認した変更（`vendor/seL4/CHANGES.md`）

- AArch64 の kernel image を 2 MiB 境界に置き、rpi3・rpi4・rpi5 では RAM 先頭の最大 2 MiB を device untyped にする変更。
- Arm の hypervisor 構成での debug register、PMU、各種 system register の扱いの強化（hypervisor を使わない本プロジェクトの既定の構成には直接は関係しない、推測）。
- AArch32 の FPU、CPACR、FPEXC などの context switch の修正、TEEHBR と Jazelle DBX へのアクセスの禁止。
- stale TLB・ASID の問題の修正。

全項目の採否は、seL4 を更新するときに「vendor-update」スキルで記録します。

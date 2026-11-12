# 依存の固定版とライセンス

[索引へ戻る](../README.md)

| path | upstream | 固定先 | ライセンス | 採用の理由 |
|---|---|---|---|---|
| `vendor/seL4` | https://github.com/seL4/seL4 | tag `17.0.0`（commit `62e345c240a15671484530b4e6e069ce266c28d7`、2026-10-30） | kernel は主に GPL-2.0-only、`libsel4` は BSD-2-Clause | 製品の kernel。`patches/seL4/` の patch を build 時の写しに当てる（[差分](../sel4/verified-config-deviations.md)） |
| `vendor/seL4_tools` | https://github.com/seL4/seL4_tools | `master` の `6493e0c6fab360eb81a8115a49c9ca7bc280c48a`（`seL4/sel4test-manifest` の tag `17.0.0` が指す commit） | elfloader-tool と cmake-tool は主に GPL-2.0-only、一部 BSD-2-Clause・BSD-3-Clause | seL4 を起動する elfloader と、root task を含む image を作る CMake の helper。改変せずに build する。tag がないため、seL4 の release の manifest が指す commit に合わせる |
| `vendor/sel4runtime` | https://github.com/seL4/sel4runtime | `master` の `86489cf6efab9f314964e79468c036e9035394c7`（`seL4/sel4test-manifest` の tag `17.0.0` が指す commit、2025-03-17） | 主に BSD-2-Clause。一部 MIT（`memcpy.c`、`memset.c`、`elf.h` など）、文書は CC-BY-SA-4.0 | root task の起動処理（C runtime、BootInfo の受け取り）。smoke test の root task が使う。改変せずに build する |
| `vendor/util_libs` | https://github.com/seL4/util_libs | `master` の `ef49a397b7044fc38b609a99a8c6265a97913b8e`（`seL4/sel4test-manifest` の tag `17.0.0` が指す commit、2026-10-27） | 使うのは `libcpio` だけで BSD-2-Clause。repository 全体には GPL などの部品もあるが build しない | elfloader が image の中の kernel と root task を CPIO から取り出すのに使う。改変せずに build する |
| `vendor/musllibc` | https://github.com/seL4/musllibc | `sel4` の `b0005f86fecbd6d0257b15363a5b013446914265`（`seL4/sel4test-manifest` の tag `17.0.0` が指す commit） | MIT | seL4_tools の `base.cmake` が `find_package(musllibc REQUIRED)` で要求するため置く。この版は AArch32 の `KernelArmTLSReg=tpidruro` だけに対応し、検証済み構成の `tpidru` と合わないので、root task には link しない（[実験記録](../experiments/2026-11-11-qemu-smoke.md)） |
| `vendor/yomiyasu` | https://github.com/nanaism/yomiyasu | tag `v2.5.0`（commit `29d67ccb05e370b5958d72920a9cd1aa829dee80`） | MIT | 日本語文書の推敲スキル |
| `vendor/m5stack-linux-dtoverlays` | https://github.com/m5stack/m5stack-linux-dtoverlays | `main` の `4f7aeee9fc103ebb03d22cac476bb191ecfb321e`（2026-11-05） | GPL-2.0 WITH Linux-syscall-note（`COPYING`） | CardputerZero の配線と初期化の手順を読む資料。コードは写さない |

## capDL の build 用配布物（2026-11-12）

root initializer は rust-sel4 `c819c27b076130cba9821c4555f23773e4b0bffd` の `sel4-capdl-initializer` に決めました。[判断と option](../sel4/capdl.md)を参照してください。以下は Dockerfile の ARG と対応します。取得した各ファイルは SHA-256 を照合してから使います。

| ARG | 固定値 | 役割・ライセンス |
|---|---|---|
| CAPDL_REV | `26b8d39c17e99e5423763e9ed292a1d123c39f56` | coliasgroup/capdl の rust branch。Haskell tool は BSD-2-Clause。repository 全体には GPL-2.0-only なども含むが C loader は build しない |
| CAPDL_SHA256 | `0d96b8fe4b0175d3739cf2f2314d717f915da6b4e6f220be9f763a3103356c86` | capDL source tarball |
| GHC_VERSION | `9.10.3` | build stage 専用。GHC は BSD-3-Clause を中心とする複数ライセンス |
| GHC_SHA256 | `1ac63f04eac0ad551d45cbde38f27e0e3f43ceefd98833fae1fa3f2dbd042367` | x86_64 Debian 12 bindist |
| STACK_VERSION | `3.7.1` | build stage 専用。BSD-3-Clause |
| STACK_SHA256 | `b6df9168d471d917d955ee80553562ca2b0b3b1aa61cd1256199406c2d8c4eb4` | Linux x86_64 binary tarball |
| STACK_SNAPSHOT | `lts-24.32` | capDL 自身の stack.yaml と同じ resolver |
| STACK_SNAPSHOT_SHA256 | `35f75b07f0b69b3c3e69fe8f034f3be26b3236826b569b7bfdfb9c8aaf651552` | snapshot YAML。依存 package の Hackage revision と hash はこの内容に従う |

固定 URL:

- https://codeload.github.com/coliasgroup/capdl/tar.gz/26b8d39c17e99e5423763e9ed292a1d123c39f56
- https://downloads.haskell.org/~ghc/9.10.3/ghc-9.10.3-x86_64-deb12-linux.tar.xz
- https://github.com/commercialhaskell/stack/releases/download/v3.7.1/stack-3.7.1-linux-x86_64.tar.gz
- https://raw.githubusercontent.com/commercialhaskell/stackage-snapshots/master/lts/24/32.yaml

GHC と Stack の SHA-256 は配布元の [GHC SHA256SUMS](https://downloads.haskell.org/~ghc/9.10.3/SHA256SUMS) と [Stack checksum](https://github.com/commercialhaskell/stack/releases/download/v3.7.1/stack-3.7.1-linux-x86_64.tar.gz.sha256)に照合します。tarball と snapshot は取得した内容の hash を固定します。既存と同じ Debian snapshot を使い、CA の初回導入だけは既存と同様に通常の apt mirror を使います。

submodule にはしません。必要なのは build stage の source だけで、Dockerfile に URL・revision・hash があれば image の入力 tag に反映されます。最終 image へは strip 済み `parse-capDL`、ライセンス通知、必要な runtime library を入れ、GHC・Stack・source tree は入れません。`check-pins.py consistency` は全 ARG と本表の一致を、`manifest` は rust-sel4 の指定 revision、capDL の resolver、snapshot hash と GHC の一致を調べます。週次の `upstream` は fork の rust branch・GHC・Stack・snapshot を監視します。版を単独では上げず、JSON schema の試験を繰り返します。

## 加えなかった起動部品

| 部品 | 判断 | 理由 |
|---|---|---|
| U-Boot | 今は加えない | rpi3 の公式手順は U-Boot から elfloader を起動するが、既定の U-Boot は elfloader の cache の扱いと合わない（[起動経路](../sel4/boot-chain.md)）。GPU firmware の `kernel=` で elfloader を直接起動できれば不要になり、信頼する部品も減る。直接起動の実験で失敗したときに、版と cache の対処を決めて加える |
| Raspberry Pi の GPU firmware（`bootcode.bin`、`start*.elf`、`fixup*.dat`） | submodule にしない | `raspberrypi/firmware` は履歴が数十 GB あり、shallow でも Linux kernel の image を含む。起動 image を作る段階で、release の tag と各ファイルの SHA-256 を固定して取得する。版は MSD/Linux の Buildroot が使う commit（`063bcab6`）を起点に比べる |
| Raspberry Pi の Linux kernel（`raspberrypi/linux`） | submodule にしない | 大きく、GPL。BCM2837 の周辺回路の driver を読む資料として、commit を固定した URL で参照する |
| seL4 の userland の残り（`seL4_libs`、`capdl-loader-app` など） | 今は加えない | 2026-11-12 に Rust initializer を選んだため、C loader と musl の TLS patch は不要。既存の C smoke test は引き続き `sel4runtime` だけを link する |

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

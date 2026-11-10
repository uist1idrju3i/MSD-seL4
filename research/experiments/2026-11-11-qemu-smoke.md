# QEMU raspi3b での最小 root task の起動（seL4 17.0.0、ARM_bcm2837_verified）

- 状態: 完了
- 日付: 2026-11-11
- 担当: Devin
- 関連: [userland の基盤](../sel4/userland-frameworks.md)、[検証済み構成からの差分](../sel4/verified-config-deviations.md)、[起動の流れ](../sel4/boot-chain.md)

## 目的と仮説

検証済み構成 `ARM_bcm2837_verified` の kernel と最小の root task（`projects/smoke/`）を QEMU の `raspi3b` で起動し、root task が device untyped から PL011 の frame を作って文字を出せるかを確かめます。仮説は「改変しない kernel のまま root task まで進む」でした。

## 採否の基準（結果を見る前に書く）

- 合格: PL011 の出力に `MSD-seL4 smoke: OK` が出て、`tools/qemu-smoke.sh` が終了コード 0 で終わる。
- 不合格: 制限時間内に上の行が出ない。
- 構築できるかを見る試験なので、各条件 1 回だけ実行しました。性能の結論には使いません。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `477017c66cba8bbc60f2cbe0e14e6a49535820c4`（main）に、作業中の `projects/smoke/`、`tools/qemu-smoke.sh`、submodule の追加を載せた作業ツリー |
| ホスト | 開発用 image（Debian GNU/Linux 13 trixie） |
| QEMU | 10.0.13（Debian 1:10.0.13+ds-0+deb13u1）、binary の SHA-256 `2e7fe3008a900980493a85e606036793fd162153edac0228477579988c53e1f5` |
| seL4 / GCC / CMake | seL4 17.0.0（`62e345c240a15671484530b4e6e069ce266c28d7`）、arm-linux-gnueabi-gcc 14.2.0、aarch64-linux-gnu-gcc 14.2.0（入口の stub だけ）、CMake 3.31.6、Ninja 1.12.1 |
| userland の部品 | seL4_tools `6493e0c6fab360eb81a8115a49c9ca7bc280c48a`、sel4runtime `86489cf6efab9f314964e79468c036e9035394c7`、util_libs `ef49a397b7044fc38b609a99a8c6265a97913b8e`（libcpio だけ）。musllibc `b0005f86fecbd6d0257b15363a5b013446914265` は submodule にあるが link しない |
| 出力先と状態 | `build/smoke-base` と `build/smoke-patched`。どちらも毎回削除してから cold で build |
| 変える条件 | kernel の source（改変なし / `boot.c` の 1 か所を変えた写し） |
| 変えない条件 | CMake の構成（`ARM_bcm2837_verified`）、root task、QEMU の引数、制限時間 15 秒 |
| 繰り返し | 各 1 回（構築と起動の可否を見る試験） |
| 入力とバイナリ | 下の「結果」の表 |
| 初回と失敗の扱い | 失敗した回も結果に残す |

改変した写しは、`vendor/seL4` を `git archive` で `build/seL4-exp` に展開し、`src/arch/arm/kernel/boot.c` の `disableFpu()` の呼び出しを次のように変えたものです。`vendor/seL4` は改変していません。

```c
    if (haveHWFPU) {
        setCPACR(CPACR_FPU_ENABLE);
        isb();
        disableFpu();
        setCPACR(CPACR_DEFAULT);
        isb();
    }
```

## 手順

```sh
docker/msd-sel4-dev bash -c 'QEMU_TIMEOUT=15 tools/qemu-smoke.sh build/smoke-base'
docker/msd-sel4-dev bash -c 'KERNEL_PATH=$PWD/build/seL4-exp QEMU_TIMEOUT=15 tools/qemu-smoke.sh build/smoke-patched'
```

`tools/qemu-smoke.sh` は、CMake cache の構成（`KernelPlatform=bcm2837`、`KernelSel4Arch=aarch32`、`KernelVerificationBuild=ON`、`KernelMaxNumNodes=1`、`KernelAArch32FPUEnableContextSwitch=OFF`、`KernelIsMCS=OFF`）を照合してから QEMU を起動します。

QEMU の `-kernel` に渡した ELF は AArch64 の EL3 で始まります。そこで、AArch32 へ切り替える小さな stub（`projects/smoke/qemu/aarch32-entry.S`）を `-kernel` に渡し、elfloader の image は `-device loader` で読み込みます。stub は core 0 だけを進め、`SCR_EL3.RW=0` にして AArch32 の HYP mode で elfloader に入ります。実機の firmware で `arm_64bit=0` にしたときと同じく HYP mode から入りますが、stub は実機では使いません。

## 計測器の検証

- 負の対照: 改変なしの kernel では PL011 の出力が 0 バイトで、`tools/qemu-smoke.sh` は終了コード 1 で終わりました。合否の判定に使う行は、root task が動かない回には出ません。
- 例外の追跡: `-d int,guest_errors,unimp` で、例外の種類と発生した例外 level を記録しました。

## 結果

| 条件 | image の SHA-256 | kernel.elf の SHA-256 | 結果 |
|---|---|---|---|
| 改変なし | `0519ab188f0f180f853993dad01b5c2611a5a3dc95aa3b7177cbd1612fad58e0` | `bf133e8fba31e9ee9569d91b2ecbef587afd65df5ad67af24e84f3af54baf663` | 不合格。kernel の起動処理で Undefined Instruction |
| `boot.c` の 1 か所を変えた写し | `3e74cb151eaa317ba4bae5873777b3a91ee6d88a70b27b7ff119c93b4c1cfb46` | `c29e1405ba5e953490e37e864af06602c3ee49adc7b6c80a1a27d666934365d8` | 合格 |

改変なしの image は、別の日時に cold で 2 回 build し、2 回とも同じ SHA-256 になりました。

改変なしの回の流れ（QEMU のログから）:

1. stub が AArch64 の EL3 から AArch32 の EL2（HYP）へ戻り、elfloader が始まる。
2. elfloader が mini UART に `Enabling MMU and jumping to entry point...` まで出し、SVC mode で kernel に入る。
3. kernel の `init_kernel` の `0xe000191c`（`vmrs r3, fpexc`）で、EL1 の Undefined Instruction（ESR の EC が 0x7、FP と SIMD の access の trap）が起きる。
4. kernel の例外処理の中で止まり、root task には進まない。

変えた写しの回の PL011 の出力:

```text
MSD-seL4 smoke: root task started
untyped caps: 0x00000040
empty slots: 0x00000f82
MSD-seL4 smoke: OK
```

原因は、seL4 17.0.0 に入った [33d77d4](https://github.com/seL4/seL4/commit/33d77d487cd8)（PR #1791）です。

- `CONFIG_HAVE_FPU` が無効のとき（検証済み構成では無効）、`fpsimd_HWCapTest()` は最後に CPACR を `CPACR_DEFAULT` に戻します。この値は cp10 と cp11 を禁止します。
- その直後の `init_kernel` は、FPU があれば `disableFpu()` を呼びます。`disableFpu()` は hypervisor support のない構成では `clearEnFPEXC()` で FPEXC を読み書きするので、ここで trap します。
- 13.0.0 の `fpsimd_HWCapTest()` は、CPACR で cp10 と cp11 を許可したまま戻っていました。

seL4 の master（2026-11-09 の `c98d70adf15e` 時点）でも、関係する `src/arch/arm/kernel/boot.c`、`src/arch/arm/32/machine/fpu.c`、`include/arch/arm/arch/32/mode/machine/fpu.h` は 17.0.0 から変わっていません。

root task が frame を作れたことから、次の 2 点も QEMU で確かめられました。

- device untyped を半分ずつ分け、PL011 を含む 4 KiB の untyped から frame を作る処理
- `seL4_ARM_PageCacheable` を付けずに map した frame への MMIO の読み書き。AArch32 の kernel は、この属性のない frame を strongly-ordered として map します（`makeUserPTE()`）

## 捨てた試行と経緯

- `-cpu cortex-a53,aarch64=off`: QEMU が「KVM なしでは aarch64 を無効にできない」として起動しませんでした。
- elfloader の image を直接 `-kernel` に渡した回: QEMU は AArch64 で始めるため、AArch32 の elfloader が動きませんでした。上の stub を作りました。
- stub の最初の版: QEMU が EL2 で始めると仮定していました。実際は EL3 で始まったので、何もせずに止まりました。EL3 から HYP へ戻す処理を加えました。
- stub の 2 番目の版: core を選んでいなかったため、4 つの core が同時に elfloader に入りました。core 0 だけを進めるように直しました。
- root task に musllibc を link した回: CMake が止まりました。この版の musllibc は `KernelArmTLSReg=tpidruro` だけに対応していて、検証済み構成は `tpidru` を使うためです。構成は変えず、musllibc を link しないようにし、`memset` だけを root task に置きました。
- CMake の構成の照合の最初の版: `KernelMaxNumNodes` が cache に `INTERNAL` 型で入るため、型まで一致させる照合が失敗しました。型を問わない照合に直しました。

## 結論

- 改変しない seL4 17.0.0 の `ARM_bcm2837_verified` は、QEMU の raspi3b で kernel の起動処理を終えられません。仮説は外れました。
- `boot.c` の 1 か所を変えた写しでは、root task が device の frame を map し、PL011 に出力できました。
- ここで変えたのは kernel の起動処理です。kernel の証明は起動処理を含まないので、証明済みの部分は変えていません。それでも検証済み構成の source からの差分になるので、製品に入れるかどうかは利用者が判断します。
- この結果は QEMU での結果で、実機の CardputerZero で起動することを示すものではありません。

## 未確認の点

- 実機の BCM2837 でも同じ箇所で止まるか。Arm のアーキテクチャの規定では、CPACR が cp10 を禁止しているときの EL1 からの FPEXC の access は UNDEFINED です。このため実機でも止まると推測していますが、実機では試していません。
- 実機の firmware（`arm_64bit=0`）から elfloader に入ったときの CPU の状態（NSACR、HCPTR、CNTFRQ など）と、QEMU の stub で作った状態の違い。
- PL011 は QEMU で試すために使いました。CardputerZero で PL011 が何に配線されているか（Bluetooth など）は、driver の調査で確かめます。
- 実機の電源断、microSD、firmware の tryboot は、この試験の対象外です。

## ログ

ログはリポジトリに入れていません。上の手順で再生成できます。例外の追跡は、`tools/qemu-smoke.sh` の QEMU の引数に `-d int,guest_errors,unimp -D <file>` を足して取りました。

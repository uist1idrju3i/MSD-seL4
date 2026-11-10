# 検証済み構成からの差分

製品の seL4 kernel の構成が、検証済み構成 `ARM_bcm2837_verified`（`vendor/seL4/configs/ARM_bcm2837_verified.cmake`）から外れる箇所の一覧です。手順は「sel4-verified-config」スキルに従います。

CMake の構成の差分はありません（seL4 17.0.0）。kernel の source には patch を 1 つ当てています（「kernel の source の patch」の節）。

| CMake の変数 | 検証済み構成の値 | 製品の値 | 理由 | 証明への影響 | 戻す条件 | 利用者の判断 |
|---|---|---|---|---|---|---|

## kernel の source の patch

patch は `patches/seL4/` に置き、`tools/prepare-sel4-source.sh` が build のたびに `vendor/seL4` の写しへ当てます。`vendor/seL4` は変えません。`tools/build-verified-kernel.sh` と `tools/qemu-smoke.sh` は、既定で patch を当てた写しを使います。`MSD_SEL4_PATCHES=none` を付けると、改変なしの `vendor/seL4` を使います。CMake の構成は、どちらも `ARM_bcm2837_verified` のままです。

上流の seL4 には Issue も PR も出しません。patch と調査結果をこのリポジトリに置き、上流が直したらその版を取り込んで patch を外します（利用者の判断、2026-11-11）。

| patch | 変える箇所 | 理由 | 証明への影響 | 戻す条件 | 利用者の判断 |
|---|---|---|---|---|---|
| `0001-arm-boot-allow-fpu-access-around-disableFpu.patch` | `src/arch/arm/kernel/boot.c` の `init_cpu()`（`BOOT_CODE`） | 改変なしの 17.0.0 は、`disableFpu()` の `vmrs fpexc` で Undefined Instruction になり、起動処理を終えられない | 起動処理は証明の対象外。ただし、l4v の証明とバイナリ正当性の検証は改変なしの source と、その build を対象にしている。patch を当てた source では、どちらも実行していない | 上流の seL4 で同じ箇所が直った版に上げ、改変なしで smoke test が通ったら patch を外す | 2026-11-11。patch をリポジトリに置く。上流へ Issue は出さない |

### 原因

- seL4 17.0.0 に含まれる上流の [33d77d4](https://github.com/seL4/seL4/commit/33d77d487cd8)（PR #1791）で、`fpsimd_HWCapTest()` は最後に CPACR を `CPACR_DEFAULT` に戻すようになりました。
- `CONFIG_HAVE_FPU` を無効にした構成では、`CPACR_DEFAULT` は `CPACR_TRCDIS` だけで、cp10 と cp11 を禁止します（`include/arch/arm/arch/32/mode/machine/fpu.h`）。検証済み構成もこの構成です。
- その直後に `init_cpu()` が呼ぶ `disableFpu()` は、FPEXC を `vmrs` で読みます。cp10 が禁止された状態で EL1 から FPEXC を読むと UNDEFINED になります。
- 経緯と QEMU のログは [QEMU raspi3b での最小 root task の起動](../experiments/2026-11-11-qemu-smoke.md) にあります。

### patch の中身

`disableFpu()` を呼ぶ前に CPACR を `CPACR_FPU_ENABLE` にし、呼んだ後で `CPACR_DEFAULT` に戻します。どちらの後にも `isb` を置きます。FPEXC.EN を 0 にして FPU を止める、もとの処理は変えません。起動処理を終えた後の CPACR の値は、改変なしの source の意図と同じです。

### 上流の修正を確かめる手順

- 週次の `pins-check` の Issue にある「seL4 の patch 0001」の行で、seL4 の master の該当箇所が patch を当てる前のままかを確かめます。箇所が変われば「更新あり」になります。
- seL4 を上げるときは、`tools/prepare-sel4-source.sh` を使います。patch がすでに `vendor/seL4` に入っていれば、このスクリプトは止まります。patch が当たらなくなったら、上流の変更を読み、`MSD_SEL4_PATCHES=none tools/qemu-smoke.sh` で改変なしの kernel が起動するかを確かめます。起動すれば patch を外します。

### 確かめたこと

- `patches/seL4/` の patch を当てた kernel と image の SHA-256 は、実験の記録の「`boot.c` の 1 か所を変えた写し」と同じでした（kernel `c29e1405…`、image `3e74cb15…`）。`MSD_SEL4_PATCHES=none` の build は「改変なし」と同じでした（kernel `bf133e8f…`、image `0519ab18…`）。
- CI の `kernel-verified` は、patch を当てた kernel を build し、QEMU raspi3b で smoke test を実行します。QEMU の結果は、実機の CardputerZero で起動することを示しません。

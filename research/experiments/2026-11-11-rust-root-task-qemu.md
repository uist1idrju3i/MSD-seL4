# QEMU raspi3b での Rust の root task の起動（rust-sel4 v6.0.0、ARM_bcm2837_verified）

- 状態: 完了
- 日付: 2026-11-11
- 担当: Devin
- 関連: [seL4 の Rust の対応状況](../sel4/rust.md)、[Rust の採用の検討](../sel4/rust-adoption.md)、[C の smoke test の記録](2026-11-11-qemu-smoke.md)

## 目的と仮説

rust-sel4 の文書は「32-bit x86 を除き、kernel が対応する全構成に対応する」と書いています。しかし rust-sel4 の CI の構成（`hacking/nix/scope/worlds.nix`）に `bcm2837` はありません。この実験では、本リポジトリの検証済み構成 `ARM_bcm2837_verified` の libsel4 の header に対して rust-sel4 の root task を build し、C の smoke test と同じ処理（device untyped を半分ずつ分けて PL011 の frame を作り、page table と frame を map して文字を出す）が QEMU の `raspi3b` で動くかを確かめます。

仮説は「AArch32 の TLS の register（`KernelArmTLSReg=tpidru`、Arm の名前では TPIDRURW）と IPC buffer の置き場（`KernelIPCBufferLocation=threadID_register`、TPIDRURO）が rust-sel4 の runtime の前提と合い、root task まで動く」でした。

## 採否の基準（結果を見る前に書く）

- 合格: PL011 の出力に `MSD-seL4 rust smoke: OK` が出て、`tools/qemu-smoke.sh` が終了コード 0 で終わる。
- 不合格: build が失敗する、または制限時間内に上の行が出ない。
- 構築と起動の可否を見る試験です。起動は同じ image で 5 回繰り返し、出力が毎回同じかを見ました。性能の結論には使いません。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `4becd2f2f6dc4d3976a5b9efd91753aaf5384031`（main）に、`projects/rust-smoke/` と `tools/qemu-smoke.sh` の変更を載せた作業ツリー |
| Rust を build したホスト | Ubuntu 22.04.5 LTS の開発 VM。開発用 image には nightly の Rust と libclang がないため、image の外で build した |
| Rust | `nightly-2026-08-21`（rustc 1.100.0-nightly 8925ea358）。rust-sel4 `v6.0.0` の `rust-toolchain.toml` の版。`rust-src` を使う `-Z build-std` |
| libclang | `libclang-14-dev` 1:14.0.0-1ubuntu1.1（`sel4-sys` の bindgen が使う） |
| rust-sel4 | `v6.0.0`（`c819c27b076130cba9821c4555f23773e4b0bffd`）。crate は `sel4` と `sel4-root-task`。依存は `projects/rust-smoke/Cargo.lock` の 81 package |
| target | rust-sel4 の `support/targets/armv7a-sel4-roottask.json`（`armv7a-none-eabi`、soft-float、`panic-strategy=abort`） |
| kernel、elfloader、QEMU | C の smoke test と同じ。seL4 17.0.0 に FPU の patch を当てた写し、`ARM_bcm2837_verified`、QEMU 10.0.13（SHA-256 `2e7fe3008a900980493a85e606036793fd162153edac0228477579988c53e1f5`）、開発用 image の中で実行 |
| 構成の確認 | `CMakeCache.txt` で `KernelArmTLSReg=tpidru`、`KernelIPCBufferLocation=threadID_register`、`KernelPrinting=OFF` を確認 |
| 変える条件 | root task（C の `projects/smoke/` / Rust の `projects/rust-smoke/`）、kernel の source（patch あり / なし） |
| 繰り返し | patch ありの Rust を 5 回、patch なしの Rust を 1 回、marker を変えない負の対照を 1 回 |

## 手順

```sh
docker/msd-sel4-dev tools/qemu-smoke.sh build/rs-base        # libsel4 の header を作る
projects/rust-smoke/build.sh build/rs-base                   # 開発用 image の外で実行
cp projects/rust-smoke/target/armv7a-sel4-roottask/release/rust-smoke.elf build/rust-smoke-repro.elf
docker/msd-sel4-dev env MSD_SMOKE_ROOTSERVER=build/rust-smoke-repro.elf \
    "MSD_SMOKE_MARKER=MSD-seL4 rust smoke: OK" tools/qemu-smoke.sh build/rs-run
docker/msd-sel4-dev env MSD_SMOKE_ROOTSERVER=build/rust-smoke-repro.elf \
    tools/qemu-smoke.sh build/rs-neg                         # 負の対照（既定の marker）
```

`MSD_SMOKE_ROOTSERVER` は、C の root task を build した後で ELF を差し替え、elfloader の image を作り直します。kernel と elfloader は C の smoke test と同じものです。patch なしの回は、開発用 image の中で `MSD_SEL4_PATCHES=none` を付けて同じ手順を実行しました。

## 結果

| 回 | kernel | root task | 結果 |
|---|---|---|---|
| rust-patched-1〜5 | patch あり（SHA-256 `c29e1405…34365d8`） | Rust | 5 回とも `MSD-seL4 rust smoke: OK`。PL011 の出力は 5 回とも同じ（SHA-256 の先頭 `5f9afbeb7b640748`） |
| rust-unpatched-1 | 改変なし（`bf133e8f…af54baf663`） | Rust | marker なし。C の smoke test と同じく kernel の起動処理で止まる |
| rust-negative-1 | patch あり | Rust、marker は既定の `MSD-seL4 smoke: OK` | 終了コード 1。Rust の出力は `MSD-seL4 rust smoke: OK` で、既定の marker と一致しない |
| rust-repro-1 | patch あり | Rust（`build.sh` で build し直した ELF、SHA-256 `1a6922a0dd9120e14a03903ad9beaf76f16b0728359f62398eab063f5e982f62`） | 合格。image の SHA-256 `9f6a027577623367aee1ecbc0bbe82d03c8eb519f0ca45613ead8438e819692a` |

PL011 の出力（rust-repro-1）:

```text
MSD-seL4 rust smoke: root task started
MSD-seL4 rust smoke: OK
```

### 大きさ（同じ処理の C と Rust の root task）

| root task | text | data | bss | ELF | strip 後 |
|---|---|---|---|---|---|
| C（`projects/smoke/`、sel4runtime） | 5,587 | 8 | 98,388 | 16,848 | 13,052 |
| Rust（`opt-level="s"`、heap 4 KiB） | 23,796 | 16 | 66,024 | 60,348 | 24,912 |

単位は byte です。Rust の text は C の約 4.3 倍です。差の内訳（`sel4-root-task` の TLS・unwinding・allocator、`core` の format など）は測っていません。

## 失敗した試行

1. tag `v6.0.0` の crate を `nightly-2026-10-28`（rust-sel4 の main の版）で build したところ、`sel4-runtime-common` で `core::intrinsics::abort` が見つからず失敗しました。rust-sel4 の各 release は、その時点の `rust-toolchain.toml` の nightly でだけ試されています。tag の版（`nightly-2026-08-21`）に合わせて解決しました。
2. 最初の build は、`sel4-sys` の bindgen が libclang を見つけられず失敗しました。開発用 image にも libclang はありません。
3. 最初の ELF（tag で依存を指定）と、rev で指定し直した ELF は SHA-256 が違います。依存の指定の文字列が binary に入るためと推測しますが、確かめていません。同じ指定で 2 回 build して一致するか（再現できる build か）も確かめていません。

## 結論

- `ARM_bcm2837_verified` の header に対して rust-sel4 v6.0.0 の root task を build でき、QEMU raspi3b で untyped の retype、page table と frame の map、MMIO の書き込みまで動きました。`sel4` crate の IPC buffer は thread local に置かれるので、TLS の初期化も動いていると判断します（推測。TLS の値を直接は読んでいません）。
- 気にしていた TLS の register は、検証済み構成が `KernelArmTLSReg=tpidru`（TPIDRURW）で、rust-sel4 が TPIDRURW を使うので一致します。IPC buffer の場所は TPIDRURO で、別の register です。
- QEMU の結果で、実機の結果ではありません。cache、MMIO の memory 属性、実機の firmware の違いは確かめていません。
- 改変なしの seL4 17.0.0 では、Rust の root task でも kernel の起動処理で止まります。FPU の patch が要るのは C と同じです。

## 生の値

[2026-11-11-rust-root-task-qemu.csv](2026-11-11-rust-root-task-qemu.csv)。大きなログはコミットしていません。上の手順で再生成できます。

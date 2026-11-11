# SMP とマルチカーネル

[索引へ戻る](../README.md)

2026-11-11 に調べました。seL4 17.0.0（`vendor/seL4`）の source と文書、および公開されている資料を読みました。実機と QEMU では何も試していません。kernel の build も試していません。

## 用語

- SMP（対称型多重処理）: 1 つの kernel image が全コアで動き、thread をコア間で移動させる形です。kernel の状態は全コアで共有します。
- マルチカーネル（seL4 の文書では static multi-kernel）: コアごとに別の seL4 instance が動き、互いのメモリは分割します。共有は user-level のメモリだけで行います。

## seL4 の SMP

### CAVEATS.md の SMP の節

- SMP 構成は seL4 Foundation がサポートしますが、形式検証はありません。
- SMP と MCS の組み合わせは experimental で、対応ボードは Armv8-a、RISC-V、Intel だけです。Armv7-a の対応ボードはありません（テスト済みの表記: hifive、tqma8xqp1gb、odroidc4、zynqmp、tx1、tx2、pc99-32、pc99-64）。
- SMP と domain scheduler の組み合わせはサポートされません。
- 公式 FAQ は、SMP kernel が big-lock 方式で、L2 cache を共有する密結合コア向けであり、多数のコアへの拡張は目的でなく、その場合は multikernel が適すると説明しています。

### 構成と実装

- `config.cmake` の `KernelMaxNumNodes`（既定 1）が 1 より大きいと `ENABLE_SMP_SUPPORT` が有効になります（`config.cmake` 200〜204 行）。ただしこの option は `KernelNumDomains EQUAL 1` のときだけ意味を持ちます（同 197 行）。
- `src/arch/arm/kernel/boot.c` は `populate_bi_frame(0, CONFIG_MAX_NUM_NODES, ...)` で bootinfo の node 数を設定し、`release_secondary_cpus` が `ksNumCPUs == CONFIG_MAX_NUM_NODES` になるまで副コアの解放を待ちます。
- `src/smp/ipi.c` は big kernel lock（CLH lock）と IPI（inter-processor interrupt）による remote call（TLB の invalidate、FPU owner の切り替えなど）を実装します。
- IPI の送信 `ipi_send_target` は、ARM では `src/arch/arm/machine/gic_v2.c` と `gic_v3.c` にだけ実装があります。x86 は APIC、RISC-V は SBI 経由です。
- `src/arch/arm/32/head.S` は SMP 構成で MPIDR からコア番号を読み、コアごとの kernel stack を選びます。

## seL4 のマルチカーネル

### CAVEATS.md の multi-kernel の節

- 「より高い保証への中間ステップとして static multi-kernel 構成がある。AArch64 向けの形式検証がロードマップにあり、初期の作業が始まっている」とあります。検証が完了していなくても、単純で逐次の証明に近いため、より堅牢と期待されるとしています。
- 各コアが別の seL4 instance を動かし、各 instance は機械のメモリの素集合にだけアクセスします。user-level のメモリは device-untyped memory として共有でき、kernel は管理しますが中身には触れません。
- 「適切な device tree overlay を各 instance に与えることで、kernel の変更なしに構成できる」とあります。IRQ controller のアクセス管理など、使いやすく安全にする作業は計画中です。

### コア間の割り込み（IPI）の API

- seL4 14.0.0（2025-11-25）で `ARMIRQIssueSGISignal` invocation と `SGISignal` capability が追加されました（`CHANGES.md`）。RFC-17（multikernel-ipi-api、実装済み）がこの設計で、送信は unicast から始めます。
- `src/arch/arm/object/interrupt.c` では、この invocation は `CONFIG_ENABLE_SMP_SUPPORT` が無い構成（＝各コアが単一ノードの kernel を動かすマルチカーネル構成）でだけ有効です。`NUM_SGIS` が 0 の platform では「not available on this platform」で拒否します。
- `NUM_SGIS=16` は GIC 共通の header（`include/arch/arm/arch/machine/gic_common.h`）にだけあります。bcm2837 の `include/drivers/irq/bcm2836-armctrl-ic.h` は `NUM_SGIS 0` なので、この API は bcm2837 では使えません。

### bootinfo の shared frame

- `libsel4/include/sel4/bootinfo_types.h` の `sharedFrames` は「shared-frame caps（seL4 node 間で共有）」の欄です。
- ARM と RISC-V の `src/arch/*/kernel/boot.c` は `S_REG_EMPTY` を設定し、コメントに「no shared-frame caps（ARM/RISC-V has no multikernel support）」とあります。x86 は `sharedFrames` を代入しませんが、`populate_bi_frame`（`src/kernel/boot.c`）が bootinfo frame を clear するため、結果は同じく空です。つまり 17.0.0 ではどのアーキテクチャでも `sharedFrames` は空で、instance 間で capability を受け渡す公式の経路は未実装です。なお bootinfo の `numNodes` は、x86 が `ksNumCPUs`（実行時の CPU 数）、ARM と RISC-V が `CONFIG_MAX_NUM_NODES`（構成時の値）を渡します。

### 関連する動き

- 公式 FAQ は「multicore は x64、ARMv7、ARMv8、RISC-V でサポート。multicore kernel の検証は static multikernel 構成について進行中」と述べています。
- 公式 roadmap は、Proofcraft による multikernel verification を挙げ、完了予定を Q3/28 としています。
- 2026-09-03 の seL4 Summit の資料（Single Kernel Multicore seL4, SKMS）は、1 つの kernel core と各 user core の stub kernel からなる非対称構成を x86 で試作した報告です。検証計画のたたき台を示し、community の feedback を求めています。seL4 本体の公式構成ではありません。
- 参考までに、mCertiKOS（Yale の CertiKOS フレームワーク、Coq 証明、x86）は検証済みの concurrent kernel の先行例ですが、seL4 ではありません。

## bcm2837（CardputerZero）での実現性

### SMP

- bcm2837 の割り込み controller は `bcm2836-armctrl-ic` で、GIC ではありません。`ipi_send_target` の実装がないため、`KernelMaxNumNodes` を 1 より大きくした build は link に失敗する見込みです（build は試していません）。
- 同じ header で `plat_sendSGI` は `UNREACHABLE` の stub、`plat_SGITargetValid` は常に false です。
- SMP は `KernelNumDomains=1` が前提で、検証済み構成の `KernelNumDomains=16`（domain scheduler を使用）と両立しません。
- 以上から、bcm2837 で seL4 の SMP を使うには kernel への patch（例: ARM local regs の mailbox を使う IPI の実装）が必要で、しかも未検証の構成になります。SMP は現実的な選択肢ではありません。

### マルチカーネル

- メモリ: 512 MiB を静的に分割します。`overlay-rpi3.dts` の `memory` の `reg` と reserved-memory（先頭の 4 KiB は armstub 用）を instance ごとの overlay で与える形が、CAVEATS の想定と合います。
- コア間シグナル: SGI が使えないため代替が必要です。候補は BCM2836 の core ごとの local regs（`0x40000000`）の mailbox 系 register（`coreMailboxesIrqCtrl`、`coreMailboxWriteset`、`coreMailboxRW`）です。この page は kernel が予約しており、userland からは触れません。他コアへ IRQ を出せるかは BCM2835/6/7 の peripheral 資料で要確認で、kernel 変更なしに user-level で実現できるかは未確認です。
- IRQ: 割り込み controller は `0x3F00B200`（ARM_CTRL、全コア共有）と `0x40000000`（core ごと）の 2 系統です。device の IRQ をどの instance に割り当てるかの管理は upstream も未整備です（CAVEATS の「planned」）。
- 起動: `vendor/seL4_tools/elfloader-tool` の `smp-spin-table.c` は `raspberrypi,bcm2835-firmware`（`tools/dts/rpi3.dts` にあり）に対応し、`CONFIG_MAX_NUM_NODES > 1` のとき各コアの `cpu-release-addr`（`0xd8`〜`0xf0`）に `secondary_startup` を書きます。ただし elfloader の SMP 経路は全コアで同じ 1 つの kernel image を起動する SMP 用で、コアごとに別の image を起動する機能はありません。マルチカーネルには loader の拡張か独自の loader が必要です。実機の起動経路（GPU firmware の `start.elf` が `config.txt` の `kernel=` の 1 image を読む）も単一 image 前提で、[boot-chain.md](boot-chain.md) の範囲で別途検討が要ります。
- 検証の範囲: 各 instance は検証済み構成（single node）をそのまま使えるため、kernel 自体の証明は各 instance にそのまま適用されます。ただしメモリ分割の正しさ、共有メモリの protocol、IRQ の分割、loader は証明の外です。upstream の multikernel 検証（AArch64、進行中）が完了しても、bcm2837 の AArch32 構成にそのまま適用される保証はありません。

## 選択肢と進め方

将来計画への記録は [../roadmap.md](../roadmap.md) にあります。

- SMP は bcm2837 では upstream の実装がなく、検証もありません。採用する理由がありません。
- マルチカーネルは seL4 が「より高い保証への中間ステップ」と位置づける方向で、検証済みの単一ノード kernel を各コアで使い続けられる点が製品の方針と合います。一方で、bcm2837 ではコア間シグナル、IRQ 分割、複数 image の起動が未整備で、kernel patch が必要になる可能性があります。
- 投資するなら、まず QEMU で 2 つの kernel instance を起動する実験（loader の検討を含む）から始め、kernel patch が必要になった時点で [検証済み構成からの差分](verified-config-deviations.md) の手続きに乗せます。

## 未確認

- `KernelMaxNumNodes > 1` の bcm2837 build が link に失敗すること（build 未実施）。
- `0x40000000` の mailbox register で他コアへ通知できるか（peripheral 資料未確認）。
- QEMU の `raspi3b` 機種で複数コアと複数 kernel image を試したか（未実施）。
- bcm2837 での PSCI/SMC の有無（armstub を使うため恐らく存在しないが未確認）。
- seL4 17.0.0 にマルチカーネル用の公式の example や tool があるか（未調査）。

## 出典

- `vendor/seL4`（commit `62e345c240a15671484530b4e6e069ce266c28d7`）: `CAVEATS.md`、`CHANGES.md`、`config.cmake`、`src/kernel/boot.c`、`src/arch/arm/kernel/boot.c`、`src/arch/riscv/kernel/boot.c`、`src/arch/x86/kernel/boot.c`、`src/arch/arm/object/interrupt.c`、`src/smp/ipi.c`、`src/arch/arm/machine/gic_v2.c`、`src/arch/arm/machine/gic_v3.c`、`include/drivers/irq/bcm2836-armctrl-ic.h`、`include/arch/arm/arch/machine/gic_common.h`、`src/arch/arm/32/head.S`、`src/plat/bcm2837/overlay-rpi3.dts`、`tools/dts/rpi3.dts`
- `vendor/seL4_tools`（commit `6493e0c6fab360eb81a8115a49c9ca7bc280c48a`）: `elfloader-tool/src/arch-arm/drivers/smp-spin-table.c`、`elfloader-tool/src/arch-arm/smp_boot.c`
- [RFC-17: seL4 multikernel IPI API](https://sel4.github.io/rfcs/implemented/0170-multikernel-ipi-api.html)（2026-11-11 取得）
- [seL4 FAQ](https://sel4.systems/About/FAQ.html)（2026-11-11 取得）
- [seL4 Development Roadmap](https://sel4.systems/roadmap.html)（2026-11-11 取得）
- [Single Kernel Multicore seL4 (SKMS)（seL4 Summit 2026 の資料）](https://sel4.systems/Summit/2026/slides/single-kernel.pdf)（2026-11-11 取得）
- [CertiKOS@yale: mCertiKOS](https://flint.cs.yale.edu/certikos/mcertikos.html)（2026-11-11 取得）

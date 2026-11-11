# 割り込み controller と mailbox が同じ page にあることと、kernel の証明の前提

[索引へ戻る](../README.md) / [SoC の共通の部品](../drivers/soc-blocks.md)

2026-11-11 に調べました。証明の model を読んだ結果で、実機と QEMU では何も試していません。

## 事実

- BCM2837 の割り込み controller（`0x3F00B200`）と mailbox（`0x3F00B880`）は、同じ 4 KiB の page（`0x3F00B000`）にあります。【一次。`vendor/seL4/tools/dts/rpi3.dts`】
- seL4 17.0.0 の `tools/hardware.yml` は、`brcm,bcm2836-armctrl-ic` の region に `user: true` を付けています。コメントは「pi 3 は同じ page の `0x3f00b400` に別の timer を出しているので、この region を userspace に渡す必要がある」です。【一次。`vendor/seL4/tools/hardware.yml` 52〜60 行】
- このため、`ARM_bcm2837_verified` の build が生成する `devices_gen.h` では、`0x3F00B000` は kernel が map する frame であると同時に、userland から外す範囲（`kernel_device_reserved_regions`）に入っていません。root task はこの page を device untyped として受け取ります。【実測。build の生成物】

## 証明の model がどう扱うか

l4v（[seL4/l4v](https://github.com/seL4/l4v) の commit `771ae43c17fc6ab8559cb9c43a731b898a636878`、2026-11-09）を読みました。

- ARM の `machine_state` は、`irq_masks`（どの IRQ が mask されているか）、`underlying_memory`、`device_state` などを持ちます。説明文は「kernel が観測できる部分は、割り込み controller（どの IRQ が mask されているか）と machine のメモリ」としています。【一次。`spec/design/m-skel/ARM/MachineTypes.thy` 54〜72 行】
- user が実行する 1 step は `do_user_op` で表します。user が変えられるのは、書き込み権のある user のメモリ（`user_memory_update`）と device のメモリ（`device_memory_update`、`device_state`）だけです。`irq_masks` は変わりません。【一次。`proof/invariant-abstract/ADT_AI.thy` 200〜220 行】
- `irq_masks` を変えるのは kernel の `maskInterrupt` だけです。【一次。`spec/machine/ARM/MachineOps.thy` 285〜295 行】

## 何を意味するか

user の component が割り込み controller の register（mask の set・clear）を書くと、実機の mask は変わります。しかし証明の model では、user の書き込みは `device_state` を変えるだけで、`irq_masks` は変わりません。このとき、実機と model が食い違います。【推論】

- 証明は「device のメモリへの user の書き込みが、kernel が観測する machine の状態（`irq_masks`）を変えない」ことを、hardware の前提として置いていることになります。この前提は、`0x3F00B000` の page を map した component が割り込み controller の register を書かない限り保たれます。【推論】
- 前提が崩れたときに起きうること: kernel が mask していると考える IRQ が来る、または来るはずの IRQ が来ない。前者は、kernel が想定していない割り込みの処理につながります。何が起きるかは証明の外です。【推論】
- mailbox の driver は、[DMA の決定](../drivers/dma-iommu.md) で、VideoCore が buffer を DMA で読み書きするため「全メモリに届く部品」としています。全メモリに書ける部品は、もともと kernel のメモリも書けるので、証明の前提を崩せます。page を共有することで、新しい種類の危険は増えません。ただし、mailbox の driver の誤りが kernel の割り込みに届く経路が 1 つ増えます。【推論】

## 選択肢

| 案 | 内容 | 利点 | 欠点 |
|---|---|---|---|
| A: mailbox の driver にだけ page を渡し、割り込み controller を書かないことを driver の検証の対象にする | capDL で page を 1 つの component にだけ置く。driver は `0x880` 以降の mailbox の register だけを使う | kernel を変えない。mailbox を使える | 前提が driver の正しさに依存する。driver を小さくし、形式検証か静的解析で「`0x200`〜`0x3FF` を書かない」を確かめる |
| B: page をどの component にも渡さない | root task（capDL loader）がこの device untyped を使わない | 前提が確実に保たれる | mailbox を使えない。firmware の clock、電源、frame buffer（HDMI）、温度が使えない |
| C: kernel の `hardware.yml` を patch して page を予約する | `user: true` を外す | B と同じく確実 | B と同じく mailbox を使えない。検証済み構成からの差分（kernel の build の入力）になる |

C は、mailbox を使えなくなる点で B と同じで、kernel の差分が増えるだけです。

## 決定（2026-11-11）

利用者の判断で A に決めました。

- 理由: mailbox がないと、clock、電源、HDMI の frame buffer を使えず、「全 hardware を使う」目標に届きません。mailbox の driver は、どの案でも VideoCore の DMA によって TCB に入ります。
- 条件:
  - capDL の generator が、`0x3F00B000` の page を mailbox の driver だけに置くことを検査する。
  - mailbox の driver は、mailbox の register の offset（`0x880`〜`0x8BF`）だけに access する。この性質を、driver の検証の目標（[kernel 以外の形式検証](../verification/beyond-kernel.md)）に加える。
  - [検証済み構成からの差分](verified-config-deviations.md) には、kernel の差分ではなく証明の前提として記録する。

B と C は、mailbox が使えなくなるため採りません。

## 確かめていないこと

- l4v の refinement の証明（C の実装と model の対応）が、この前提を明示の仮定として置いているかは、まだ調べていません。読んだのは抽象の model と invariant の定義だけです。
- `0x3F00B400` の timer（ARM の timer）を userland で使う必要があるかは、調べていません。

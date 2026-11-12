<!-- SPDX-License-Identifier: BSD-3-Clause -->
# TOML からの capDL 生成と権限検査

[採用判断へ戻る](capdl.md) / [索引へ戻る](../README.md)

## 範囲と未確認事項

PR 2 の host tool は、単一 thread の PD を静的に作る AArch32・non-MCS 用の generator です。Python 3.11 以降の標準ライブラリだけを使い、`tomllib` で一つの TOML を読みます。kernel・root initializer・実際の component の build と boot はこの tool の仕事ではありません。実機と新しい二つの PD の起動は未確認です。

[system.toml](../../projects/capdl/system.toml) は serial/client の宣言です。PR 3 で C component と [QEMU の起動経路](capdl.md#二つの-c-component-を起動するpr-3)を追加しました。[capability 表](serial-client-capabilities.md)はこの宣言から生成してコミットします。`.cdl` は ELF の segment に依存するため build 時の出力とし、コミットしません。

| 方式 | 採否 | 理由 |
|---|---|---|
| JSON を直接作る | 不採用 | object の allocation 順・schema の責任を自作部分に広げない |
| python-capdl と ELF library を使う | 不採用 | この PR は標準ライブラリだけとし、依存を増やさない |
| 制限付き ELF32 reader → `.cdl` → pinned parse-capDL | 採用 | frame fill を明示し、object 順・JSON 変換は既存 tool に任せる |

## serial/client の分割

| PD | 役割・扱うデータ | 優先度・予算 | 信頼・障害時の影響 |
|---|---|---|---|
| serial | badged endpoint から短い IPC を受け、長さを確認し、PL011 を polling する | 100。non-MCS のため予算設定はない | UART の所有者。誤動作で出力が壊れる。busy loop で低優先度の client を止めるおそれがある |
| client | 短いメッセージの送信。device の cap は持たない | 90。予算設定なし | serial への送信で停止・待機しうる。直接 UART や他 PD のメモリへ書けない |

初期化後の CSpace には宣言した grant だけを入れます。CNode・TCB・untyped・IRQ cap、自身の VSpace cap も配りません。stack・ELF・IPC buffer は VSpace に mapping し、TCB の内部 slot だけに CSpace・VSpace・IPC buffer の cap を置きます。権限を実行時に増やす allocator や capability 転送は、この system にありません。

PR 3 では同じ endpoint の badge 1 で Call、badge 2 で client の fault を届けます。client の二つの cap は write/grantreply、serial は read です。grant は配りません。allow_grant は schema の gate で、実際の rights は各 grant が決めます。reply cap は kernel が往復のために作る一時的な権限です。任意の cap を転送したり、object を増やしたりする権限はありません。

fault 用も write だけにはできません。non-MCS の [sendFaultIPC](https://github.com/seL4/seL4/blob/62e345c240a15671484530b4e6e069ce266c28d7/src/kernel/faulthandler.c#L83-L86) は send と grant/grantreply のいずれかを要求します。任意の cap を渡せる grant は避け、grantreply に限ります。kernel は client の CSpace から fault slot を lookup するため、その cap も client に置く必要があります。

serial は長さ・badge・protocol の順序を検査し、polling の反復にも上限を設けます。client の VM fault に reply せず、停止したまま残します。監視や再起動は実装せず、復帰には system 全体の再起動が必要です。serial が止まると client は Call 待ちで止まりえます。fault 用 badge は悪意ある client に対する kernel の認証ではありません。client 自身もその cap で送信できるため、この試験の結論は固定した C binary に限ります。

## schema version 1

全ての table で未知の key を拒否します。TOML の重複 key は `tomllib` が拒否し、object と PD の名前は system 全体で一意にします。名前は `[a-z][a-z0-9_]{0,47}`。実行時の任意 Python や式の評価、include、継承はありません。

### system と object

| key | 必須・既定 | 条件 |
|---|---|---|
| `version` | 必須 | 整数 `1` |
| `kernel_printing` | 必須 | boolean。kernel build の出力を自動検出する値ではなく、所有権の判断の宣言 |
| `objects` | 必須 | object の配列。空を許す。最大 128 件、展開後の object/frame は合計 4096 件まで |
| `pds` | 必須 | PD の配列。1..16 件 |
| object の `name`, `type`, `reason` | 必須 | type は下表。reason は空にせず、表の改行や区切り文字 `|` を含めない |
| `size` | frame/region/device で必須 | 4 KiB 単位、最大 16 MiB。frame は 4 KiB に限定 |
| `paddr` | device だけで必須 | 4 KiB aligned。32-bit address を越える range は拒否 |
| `dma_capable` | device で必須 | boolean。false を認めるのは、今回判断した PL011 一ページだけ |
| `dma` | DMA-capable device で必須 | `"all-memory"`。制限された DMA と偽る値は認めない |
| `allow_grant` | endpoint だけ、既定 false | true の object に限り `grant` / `grantreply` を許す |

| type | capDL への展開 | 設定 |
|---|---|---|
| `endpoint` | `ep` | badge と明示的な rights |
| `notification` | `notification` | badge、read/write のみ |
| `frame` | 一つの 4 KiB RAM frame | shared memory。ゼロ初期化 |
| `region` | 4 KiB RAM frame の列 | 同じ object を複数 PD に別々の rights で渡せる |
| `device` | 物理アドレス付き 4 KiB frame の列 | uncached、execute-never。DMA 宣言が必須 |

region/device の grant は `size / 4096` 個の連続 slot と mapping に展開します。object 名は `o_NAME`、複数 frame は `o_NAME_0` などです。展開後に別の object 名と衝突する場合も拒否します。IRQ は後続の設計まで未対応とし、未知の型として拒否します。

### PD と grant

| key | 必須・既定 | 条件 |
|---|---|---|
| PD の `name`, `reason` | 必須 | 役割を記録する |
| `elf` | 必須 | fill root からの相対 `.elf` path。ASCII の英数字、`_./-` のみ。絶対 path、空の要素、`.`・`..`、root 外への symlink は拒否 |
| `stack` | 必須 | `{ vaddr = ..., size = ... }`。ゼロ初期化・read/write・execute-never |
| `ipc_buffer` | 必須 | 一ページの仮想アドレス。ゼロ初期化・read/write・execute-never |
| `priority` | 必須 | 整数 0..255。max priority も同じ値 |
| `grants` | 必須 | 空を許す。PD ごとに最大 256 宣言 |
| `fault_endpoint` | 省略時は null endpoint（slot 0） | 同じ PD の endpoint grant の slot 名。write と grant/grantreply を要求し、object 側の allow_grant も必要 |
| grant の `name`, `slot`, `object`, `type`, `rights`, `reason` | 必須 | slot 名は PD 内で一意。slot は整数 1..4095。展開後の重複・overflow も拒否。type は object の型と一致させる |
| `rights` | 既定なし | `read`, `write`, `grant`, `grantreply` の重複しない非空配列。frame/notification には read/write だけを許す |
| `badge` | endpoint/notification で既定 0 | 整数 0..0xfffffff。frame には使わない |
| `vaddr` | frame/region/device の grant で必須 | mapping の先頭アドレス。endpoint/notification には使わない |

全 virtual mapping は一ページ以上かつ 2 GiB 未満の範囲に制限します。stack・IPC buffer・grants・ELF の page の重複を拒否します。各 PD は独立した page directory・page table・CNode を持ちます。CNode は使用 slot の最大値から必要な bits と guard を計算し、slot 0 は配りません。任意の CNode・TCB・untyped grant は、自分自身を対象にするものも含めて未対応です。

### device 所有と DMA

BCM2837 の kernel が使う interrupt-controller の page `0x3f00b000..0x3f00c000` と local-controller の page `0x40000000..0x40001000` に重なる device を拒否します。小さい frame だけでなく、広い region による部分的な重なりも拒否します。device 同士の重複も認めません。

この system は `kernel_printing = false` を宣言し、PL011 `0x3f201000` を serial に渡します。printing を true と宣言した場合は、PL011 と mini-UART `0x3f215000` の両 page を保守的に拒否します。現在の kernel の生成 header が printing 時に mapping する UART は mini-UART です。PL011 の拒否も所有権の方針として維持し、printing を有効にする変更を黙って許しません。

根拠は固定 seL4 の `src/plat/bcm2837/config.cmake` が選ぶ DTS と overlay、および検証済み構成の build が出す `gen_headers/plat/machine/devices_gen.h` です。hardware のアドレスという事実を policy に使い、vendor のコードはコピーしません。この tool は任意の DTS や別 platform の所有権を解析するものではありません。PR 3 の build は宣言どおり printing が無効かを確認する必要があります。

DMA のない device として判断したのは polling 用 PL011 一ページだけです。未判断の device は、DMA の有無を推測せず `dma_capable = true` と `dma = "all-memory"` を要求します。これは DMA を有効にする設定でも、メモリを隔離する保証でもありません。新しい driver の判断は別途必要です。中央 DMA controller の cap は DMA server だけに渡す運用とし、本 system には DMA controller・USB・カメラ・VideoCore の cap を追加していません。

## ELF と frame fill

`elf.py` は static ET_EXEC・EM_ARM・ELF32 little-endian・EABI5 の ARM-state entry に限定します。hard-float、PT_DYNAMIC/PT_INTERP、Thumb entry、壊れた header、file range の不足、filesz > memsz、重なる segment、書き込みと実行の両方を持つ page を拒否します。最大 128 program header、4096 load page/PD。FPU の命令を逆アセンブルして検査するものではないので、component も soft-float で build します。

PT_LOAD を virtual page ごとに分け、file がある部分だけを `{destination_offset length CDL_FrameFill_FileData "relative.elf" file_offset}` にします。file にない BSS と page の残りはゼロです。segment が page の途中から始まる場合、先頭 offset を保ちます。ELF の readable/writable/executable flags を mapping に使い、共有 frame と device は実行不可に固定します。section 名や section header は使いません。ELF を strip しても PT_LOAD が同じなら同じ `.cdl` が出ますが、add-spec 後の initializer の strip は別問題で、禁止のままです。

同じ TOML の意味と ELF の load layout に対して、名前・slot・virtual page の順を固定し、UTF-8/LF の出力を作ります。入力の PD/object/grant/rights の順序にも依存しません。コードの内容を `.cdl` にコピーする方式ではないため、内容だけが変わった ELF では `.cdl` が同じになる場合があります。add-spec 時の fill directory に渡す ELF を別途固定する必要があります。

## CLI と checker

```sh
python3 tools/capdl/generate.py projects/capdl/system.toml \
  --elf-dir build/capdl-components --cdl build/system.cdl \
  --table research/sel4/serial-client-capabilities.md
python3 tools/capdl/check.py projects/capdl/system.toml \
  --elf-dir build/capdl-components --cdl build/system.cdl \
  --object-sizes build/capdl-components/object-sizes.yaml \
  --table research/sel4/serial-client-capabilities.md
```

`object-sizes.yaml` は対応する kernel の生成値を使います。test の定数を製品へ流用しません。parse-capDL と add-spec には PR 1 の固定版を使い、`--fill-dir` は同じ ELF root にします。

| tool / option | 意味・既定 |
|---|---|
| generate / 位置引数 | 必須の TOML 一つ |
| `--cdl`, `--table` | 出力先。一つ以上が必要。table だけなら ELF を読まず宣言から作る |
| `--elf-dir` | ELF/fill root。省略時は TOML のある directory |
| check / 位置引数、`--table` | 必須の TOML とコミットした Markdown |
| check / `--cdl` | 指定時に parse-capDL を実行。未指定時は table だけの検査と明示して終了 |
| check / `--elf-dir` | ELF root。省略時は TOML のある directory |
| check / `--object-sizes` | `.cdl` の検査時に必須 |
| check / `--parser` | 既定 `parse-capDL`。実行 binary の指定 |
| 両 tool / `--help` (`-h`) | argparse の usage |

`check.py` は generator を import しません。schema の validation、ELF reader、表の renderer は共有しますが、宣言から期待する authority を作る処理と JSON の検査は emitter と別です。JSON の object index を実際の名前に解決し、各 TCB の CSpace をたどって slot の集合、型、対象、rights、badge、cache/execute 属性を完全一致で照合します。別 PD の CSpace への付け替えも拒否します。

さらに TCB の内部 slot、guard、初期 register・優先度、全 VSpace mapping と frame fill、device の物理アドレス、object の集合も確認します。余分な CNode/TCB、宣言外の mapped cap、IRQ/untyped authority を拒否し、生成表は期待する UTF-8 bytes と比較します。ただし共通 schema や ELF reader のバグまで独立に証明する checker ではありません。

host の `tests/capdl/run.sh` は validator、ELF の範囲、空・エラー入力、五回の同一出力と入力順序の変更、表の stale 検出を試験します。CI の agent-docs で実行します。Build workflow は開発 image 内で parser integration を実行し、通常・空・notification/共有/fault/DMA marker の構造、および cap の追加・削除・rights/badge 変更などの mutation を拒否することを確かめます。[試験記録](../experiments/2026-11-12-capdl-generator.md)を参照してください。

## 証明とは別の検査

kernel とその構成は変更しません。generator と checker の一致は、情報流や空間・時間の隔離の証明ではありません。parser、ELF reader、schema、checker、initializer、component、firmware の正当性は kernel の証明の範囲外です。QEMU・実機での動作確認は PR 3 以降で区別して記録します。

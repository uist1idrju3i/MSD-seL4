<!-- SPDX-License-Identifier: BSD-3-Clause -->
# 二つの C component を CapDL で起動する試験

状態: 完了（QEMU のみ）。基準は PR 2 の `f6c3f6c5260fb0f9a9f9e56d2b716fd10323feae`。日付は 2026-11-12。以下の採否基準は実行前に書き、結果を見て変えていません。

## 目的と事前の採否基準

固定した Rust initializer と TOML の spec で serial/client を起動します。正の条件は badge 1 の request と reply の確認、負の条件は同じ往復後に client の未 mapping の `0x3f201000` への read が VM fault として serial に届くことです。正負各五回で、必要な marker が全回にあり、不正な marker がないことを採用の基準とします。送信を止める対照では request marker が出ず、判定が失敗することも要求します。

kernel は verified configuration と既存 boot patch だけに固定します。CPU、printing、TLS、IPC buffer、MCS、FPU の設定を変えません。ELF、kernel、initializer、image、QEMU の hash と全回の終了状態・log を残します。出力先は build/capdl-positive と build/capdl-negative、各 run は別名にし、既存 log を上書きしません。component と image の build は条件ごとに一回で、反復では同じ binary を使います。

時間は性能の比較に使いません。marker の件数について中央値・最小・最大を集計します。失敗した試行は消さず別行に残します。QEMU は実機ではなく、generator・initializer・C component の正当性は kernel の証明の範囲外です。

## 条件と固定した入力

host は Ubuntu 22.04.5 LTS、Linux 6.8.0-1060-aws、x86_64。開発 image は PR 1 と同じ `inputs-036a7993dd036120`、local image ID は `sha256:e806396ef88cbd2a9f3654b2da961cbbda7c7088851429d5f5b4cde57fbfd619` です。実行した QEMU は 10.0.13（Debian 1:10.0.13+ds-0+deb13u1）、cross GCC は 14.2.0-19、CMake は 3.31.6、Ninja は 1.12.1。Rust は nightly-2026-08-21（rustc 1.100.0-nightly、8925ea358）、rust-sel4 は `c819c27b076130cba9821c4555f23773e4b0bffd` です。その checkout の Cargo.lock の SHA-256 は `8b4c4c6ab31a8aa8b325c9d1c9a843574b04a8946100e93b178b7105b2035f47`。

seL4 17.0.0 は `62e345c240a15671484530b4e6e069ce266c28d7`、seL4_tools は `6493e0c6fab360eb81a8115a49c9ca7bc280c48a`、sel4runtime は `86489cf6efab9f314964e79468c036e9035394c7`。vendor の変更はありません。kernel は `ARM_bcm2837_verified`、AArch32、EL1、単一 core、non-MCS、FPU context switch なし、printing なし、TLS=tpidru、IPC buffer=threadID_register に固定しました。既存の FPU boot patch だけを build 時の写しに適用しています。

| tool binary | SHA-256（image 内の実行 binary） |
|---|---|
| qemu-system-aarch64 | `2e7fe3008a900980493a85e606036793fd162153edac0228477579988c53e1f5` |
| arm-linux-gnueabi-gcc | `b2b8eaecb9b262b91b9f074404446e3dc1f8d752a549e7b9eed56eb2520a559c` |
| cmake | `9a2692f4d712265eb29c90c3366bfc40df400ea586b0477edabbcf3bae745dc1` |
| parse-capDL | `f70d18bb1c37bd4aaa5e0d9d2c5ea90c37cf1b5e3cacf7a47945cde68aba2cf1` |

component の code/linker script、TOML、generator/checker、entry/runner、patch の入力 hash と、実際の binary・log の hash は [SHA-256 一覧](2026-11-12-capdl-qemu.sha256)にあります。各 mode の binary は反復前に build し、反復中は作り直しません。positive の build tree は pilot の修正を経た warm、negative は新しい tree、Cargo は共通の warm cache です。cold/warm の build 時間を比較していません。`*-reconfigure` と ccache の測定は行っていません。

| binary | positive の SHA-256 | negative の SHA-256 |
|---|---|---|
| kernel.elf | `c29e1405ba5e953490e37e864af06602c3ee49adc7b6c80a1a27d666934365d8` | 同左 |
| serial.elf | `741a9a6988a1d0009768834f061874bf35d0a47ec9dff2d339f1adf7aa52dfc2` | 同左 |
| client.elf | `15ad31439bb838adde93bddaa60e20c1e5af60072de84642381f851921b59af9` | `4b8244102c456301dd2116e613c5ec9278b4a6cc7124e065f04b9b839453c430` |
| spec 付き initializer | `1200a95f59d15a2f3b20ec9303490eadffb6a4f96aa12dd03b6ef8c958e7cd8e` | `52c01120808661b6a7a06fd6dbe8ca7466f0edcf35940fe7a660e8105ed28512` |
| boot image | `ee474f5733ac56967fc118a0e1f5dad6222723fc0c7a3652a8669ffe1e261efe` | `0a70d8f28159e148598756aa09c6d11017638a719e8eebf12ecdfe52f6417d5f` |

kernel の hash は PR 1 の build と同じです。libsel4 の thread-local pointer を無効にする userland option は kernel を変更しません。component に musl、allocator、追加の cap を導入していません。

## 手順と計測器の検証

```sh
docker/msd-sel4-dev tools/qemu-capdl.sh build/capdl-positive positive pilot-4
docker/msd-sel4-dev tools/qemu-capdl.sh build/capdl-negative negative pilot-negative
docker/msd-sel4-dev python3 tools/capdl/repeat.py \
  --positive build/capdl-positive --negative build/capdl-negative \
  --csv research/experiments/2026-11-12-capdl-qemu.csv
docker/msd-sel4-dev tools/qemu-capdl.sh build/capdl-silent silent silent-control
```

最後の command は意図して終了値 1 になります。再実行時は新しい run ID と CSV の path を使います。runner は上書きせず、repeat は既存 run や既存 CSV があれば止まります。

A/A の positive 二回を含め、同じ binary の五回を確認しました。さらに silent では client を送信前に止め、PL011 log が 0 bytes、QEMU 終了値は同じ 124、runner は FAILED となりました。正常に UART だけが起動すれば marker が出る仕掛けではありません。host unit test でも空 log、fault の欠落、marker の重複・順序違い、後の error、異常終了値を拒否します。

## 結果

全十行・全列を読んだ [raw CSV](2026-11-12-capdl-qemu.csv) に、各 run の終了値、marker 件数、PL011 の全文（改行は escape）、hash を残しました。run ID の重複と欠測はありません。件数は有限の整数です。全回で QEMU=124、runner=0。124 は試験後も待機する image を timeout で止めた期待値で、crash を成功にしたものではありません。

| mode | 回数 | request 件数の最小/中央値/最大 | reply 確認 | fault 確認 |
|---|---|---|---|---|
| positive | 5 | 1/1/1 | 1/1/1 | 0/0/0 |
| negative | 5 | 1/1/1 | 1/1/1 | 1/1/1 |

実際の negative の log は次の三行だけでした。

```text
MSD-seL4 capdl: serial got badge 1 from client
MSD-seL4 capdl: client checked reply
MSD-seL4 capdl: client faulted at 0x3f201000
```

badge 1 と request cookie を確認した後だけ一行目が出ます。二行目は、client が実際に reply を検査して ACK を返した証拠です。三行目は serial が別 badge の VMFault、長さ、data abort、fault address、先行する protocol 状態を確認した結果です。client は fault cap でも送信できるので、これは悪意ある client の fault IPC を認証する試験ではありません。固定した client の C code はその cap に送信せず、ACK の reply 後に未 mapping のアドレスを read します。

採否基準を満たしました。情報流や任意の故障からの隔離の証明、性能差の結論には転用しません。

## 失敗した試行と過去の spike

[pilot と対照の CSV](2026-11-12-capdl-qemu-pilots.csv) は反復の成功集計と別にしました。失敗した三回は QEMU 起動前です。

1. pilot-1: `multiple definition of _start`。sel4runtime が CRT を既に link するため、C 側の入口を `_start` ではなく `__sel4_start_c` にしました。通常の argc/auxv 処理は呼びません。
2. pilot-2: initializer の path に `.elf` を付け忘れ、strip が `No such file` で止まりました。実際の target suffix に合わせました。
3. pilot-3: full strip が symbol table を消し、add-spec の `patch_symbol` が `Option::unwrap()` で panic。debug 情報だけを strip し、必要な symbol を残しました。失敗時の stripped ELF 自体は保存していません。ログと差分の説明を残しています。

pilot-4 と negative pilot で初めて image を起動し成功しました。kernel の既存 assembler 警告と elfloader の RWX segment 警告は残っています。run の QEMU log は timeout の終了通知だけで、crash の記録はありません。

以前の spike では、add-spec 後の seL4_tools の strip が埋め込んだ segment を消していました（[pipeline の注意](../sel4/capdl.md)）。今回は strip を copy に置き換え、pack 前に byte 一致を確認します。また、手書き JSON の RAM object の allocation 順序と non-MCS の `master_fault_ep=None` も spike の失敗でした。今回は固定 parser の [PrintJSON.hs](https://github.com/coliasgroup/capdl/blob/26b8d39c17e99e5423763e9ed292a1d123c39f56/capDL-tool/CapDL/PrintJSON.hs) の sort を使い、null fault endpoint は 0、client は明示 slot 2 にします。過去の失敗そのものは今回再現していません。

## 保存と未確認

大きな build log と各 run の `qemu.log`・`pl011.log`・`harness.log` は上記の build directory に保持し、削除していません。取得するには SHA-256 一覧の相対 path を使い、再生成には上記 command を使います。CI は両 mode を一回ずつ実行し、成功時の run log と binary hash を artifact に含めます。今回の CI 実行・artifact 公開はまだ未確認です。

最初の CSV writer は CRLF の row terminator を出し、git の空白検査が拒否しました。原本を `build/capdl-raw-results-crlf.csv`、実行時の collector を `build/capdl-repeat-crlf.py` に保存し、コミットする CSV の行末だけを LF に統一しました。全十行・全 field の値が不変であることを CSV reader で照合し、今後の writer も LF にしました。PL011 の bytes や件数・成否は変えていません。二つの原本と、引数の厳密な検査を足す前の copy wrapper（`build/capdl-copy-rootserver-before-guard.sh`）も含め、100 file の digest を保存しています。wrapper の正常な三引数での byte copy と、不正引数で出力を作らないことは host test で照合しました。既存 binary の bytes は変えていません。

実機、firmware による UART の初期化、pin/clock/IRQ、任意の不正 request、故障からの復帰、電源断は未試験です。timeout まで待つ test image であり、実機用 UART driver ではありません。kernel の既存 proof が generator、archive、Rust initializer、C component、boot patch、QEMU の正当性を示すとは主張しません。

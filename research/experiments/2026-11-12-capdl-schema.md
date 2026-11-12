<!-- SPDX-License-Identifier: BSD-3-Clause -->
# capDL の JSON と Rust initializer の互換性

[一覧へ戻る](README.md) ・ [採用と設定](../sel4/capdl.md)

- 日付: 2026-11-12
- 状態: 完了（host の schema・埋め込み試験）
- 基準 commit: `9944172965fe78f54c55d3a9590ed7c62e58f707`
- 担当: Devin

## 目的、基準、条件

TCB、CNode、endpoint、通常 frame、device frame、ELF の file fill を持つ `.cdl` を JSON に変換し、rust-sel4 `c819c27b076130cba9821c4555f23773e4b0bffd` の add-spec が受け入れる revision を選びます。採用の基準は、parser と add-spec の両方の正常終了、および device address・fill・実行権限を含む JSON の assertion 成功です。空の入力 model と文法エラーも調べます。

構築可否の試験なので各候補 1 回とし、時間の性能比較には使いません。host は Linux x86_64、開発 image は既存と同じ Debian trixie の digest・snapshot です。kernel の変更も実機での試験も行いません。build 出力は gitignored の `build/capdl-deps/` に置き、失敗した試験も記録します。Haskell の cold build と既存 spike の再利用 binary は区別します。

## 公式 upstream と toolchain の失敗

1. spike で build 済みの seL4/capdl `23e3c5bbc0fe9f97959e635c94728c99c1acf90e`（GHC 9.2.8 / lts-20.25）で、小さな `.cdl` を JSON に変換しました。add-spec は次のエラーで拒否しました。

   ```text
   Error: missing field `executable` at line 1 column 744
   ```

2. 公式 master `55d2ef24aeb6de08f6bfc27ed1942eec54164a62` の tarball も取得し、`PrintJSON.hs` が同じ内容であることを diff で確認しました。この master の binary を build・実行したわけではありません。

3. rust-sel4 の Nix source pin が指定する coliasgroup/capdl `26b8d39c17e99e5423763e9ed292a1d123c39f56` を GHC 9.2.8 / lts-20.25 で build しようとすると、Stack は plan の段階で拒否しました。

   ```text
   Error: [S-4804]
          Stack failed to construct a build plan.
   ```

   `bytestring >=0.12` に対して snapshot は 0.11.4.0、`containers >=0.7` に対して 0.6.5.1、`mtl >=2.3` に対して 2.2.2、`text >=2.1` に対して 1.2.5.0 でした。互換 patch や bounds の緩和は行いません。

4. 2026-11-12 に利用者が、fork 自身の resolver（GHC 9.10.3 / lts-24.32）を採ると判断しました。上流 source は改変せず、checksum 付き tarball で取得します。

初期 fixture には `fpu_disabled` の省略があり、TCBExtraInfo の pattern-match error になりました。明示した後に上記の schema error を確認しました。公式版の `RX` は fork と同じ文法ではありません。checked-in fixture は fork の `executable` を明示します。

## 再実行

```sh
docker/msd-sel4-dev build
tests/msd-sel4-dev/run.sh
```

試験入力は `tests/msd-sel4-dev/fixtures/compat.cdl`、固定の AArch32 object size は `sizes.yaml` です。試験 script が `component.S` を ARM ELF に link し、offset 0x1000 の `.text` を fill として参照します。これは schema と埋め込みの fixture であり、boot 可能な system の設計ではありません。

add-spec は開発 image に入れません。既存の Rust smoke build と同じ nightly で、固定 revision の rust-sel4 から次を build します。`SEL4_INCLUDE_DIRS` は生成済みの verified kernel の libsel4 header を指します。

```sh
cargo build --locked --release -p sel4-capdl-initializer-add-spec
cargo build --locked --release -p sel4-capdl-initializer \
  -Z build-std=core,alloc,compiler_builtins \
  -Z build-std-features=compiler-builtins-mem -Z json-target-spec \
  --target support/targets/armv7a-sel4-roottask-minimal.json
```

生成した bare initializer と add-spec を `/input` として mount し、fixture の試験を次のように実行できます。

```sh
docker run --rm -v "$PWD:/work:ro" -v "$ARTIFACT_DIR:/input:ro" \
  -e MSD_CAPDL_ADD_SPEC=/input/sel4-capdl-initializer-add-spec \
  -e MSD_CAPDL_INITIALIZER=/input/sel4-capdl-initializer.elf \
  msd-sel4-dev:local python3 /work/tests/msd-sel4-dev/check-capdl.py
```

`ARTIFACT_DIR` は上記の二つの binary を置いた directory です。optional な二つの変数を片方だけ渡すと試験は失敗します。fixture の ELF fill は実際に add-spec が読み込みます。埋め込み後の custom header の存在と非ゼロの size を検査します。

option 表の機械照合は、checksum を照合して展開した capDL と固定版 rust-sel4 の source directory を渡して実行します。

```sh
python3 tests/msd-sel4-dev/check-capdl-options.py "$CAPDL_SOURCE" "$RUST_SEL4_SOURCE"
```

## CI と残る確認

`.github/workflows/build.yml` は amd64 の Ubuntu runner で `docker/msd-sel4-dev build` を呼びます。Dockerfile に全 download pin があるため、既存の input hash と published image の再利用に反映されます。source tarball を使うため publish job の checkout に capDL submodule は不要です。既存の image 再利用は保ちますが、未公開の入力では Haskell を含む cold build が必要です。CI runner での所要時間と実際の公開・attestation は未確認です。30 分の job 制限は変えていません。

この試験では新しい root task の boot、実機、Isabelle 証明、全 schema の検証を実施しません。kernel の構成と既存の boot patch を変更しません。

## 結果と失敗した試行

生の結果は [CSV](2026-11-12-capdl-schema.csv) に記録します。採用した fork は上流 source を改変せず build できました。Haskell の compile step は cold 状態で 394.8 秒、79 action でした。これはこの host での 1 回の値であり、CI の時間の保証や toolchain 間の性能比較ではありません。

```text
ok - capDL JSON: TCB, CNode, endpoint, frames, device address, ELF fill, executable
ok - empty capDL spec
ok - invalid capDL spec rejected
ok - JSON accepted and embedded by sel4-capdl-initializer-add-spec
```

image test は UID 1000・1001・4242 で既存 tool と HOME の動作、parser が strip 済みであること、GHC と Stack が最終 image にないこと、通知の読み取りを確認しました。最終 image の tag は `inputs-036a7993dd036120` です。

同じ image で `docker/msd-sel4-dev tools/build-verified-kernel.sh` も実行しました。`kernel.elf` は 143,796 bytes、SHA-256 は `c29e1405ba5e953490e37e864af06602c3ee49adc7b6c80a1a27d666934365d8` で、spike の kernel と一致します。既存の boot patch 以外は加えていません。assembler の coprocessor access の非推奨警告と linker の RWX segment 警告は残っています。

| 対象 | 実測・SHA-256 |
|---|---|
| strip 済み parse-capDL | 20,997,824 bytes、`f70d18bb1c37bd4aaa5e0d9d2c5ea90c37cf1b5e3cacf7a47945cde68aba2cf1` |
| runtime library（ldd） | libm.so.6、libgmp.so.10、libc.so.6、ld-linux-x86-64.so.2 |
| add-spec（既存 spike の build を再利用） | `22da508d179e921b6fca34f05ee62f63e908ed42e36d3560fb78659ae4b67e31` |
| bare ARM initializer（同じ固定 revision、最小 target） | `ffb8b564fcf9052a375703dde81a73e29b147c082f8074f317c64a92de28bf73` |
| fixture compat.cdl | `d8f704221f3db7f31181d4cb675dbc5d89d3c76833b5b0ae6a1e8ec941dfea5f` |
| fixture component.S | `ad7b6885a1fabcc02b596534678e015af900fb685b06458da4737e166385fe8b` |
| fixture sizes.yaml | `89295ccefe6ec7e1a1e1b5d81395b4691b5d9ec12897b15caf73e2e31c10ea5f` |

試験 script の初版は endpoint の JSON が `null` になることを扱えず、`AttributeError` で止まりました。parser と add-spec の非互換ではありません。null を扱うよう直し、通常・空・エラー入力と add-spec を再試験しました。また、通知のコピー先が `/root` 由来の directory mode を保ったため、builder UID で読めないことが分かりました。コピー後に読み取り・directory の検索権限を付け、全通知の読み取りを UID ごとの試験に加えました。

Dockerfile lint は bindist の一時 directory への `cd` に DL3003 を出しました。同じ layer で configure・install・削除を行うため、その RUN だけに理由付きの抑制を置きました。共通の lint 設定は変えていません。DL3066 の非数値 USER に関する info は既存の `USER builder` に対するもので、failure threshold 未満です。

全 option の機械照合では漏れはありませんでした。

```text
ok - documented 11 parse-capDL options, 9 add-spec options, 3 initializer features; missing=0
```

## ログの再生成と識別

長いログはコミットせず、上記コマンドで再生成します。今回のログは gitignored の `build/capdl-deps/` に保存しました。

| file | SHA-256 |
|---|---|
| image-build.log（最初の cold build） | `2d89a64c4d9f48bf8fb5075486ba06092405ec8815ed9221cd085cdf6b3764f8` |
| add-spec-checked-test.log | `933681d0adab7b5f0e0ffaee99cb4975151fc8d758a78512266ba1d064b1fd42` |
| upstream-add-spec.log | `e049a6104cfa58129e2e5ce5384968d267cd1693d0da0dd5aa153f7f996d2066` |
| fork-ghc928.log | `79cfa563c13b519cf0f01ab64d6003524ccf86746690248df9c2487c6323a42a` |

各ログは終了状態と該当エラー・成功行を読み、hash を取得しました。初回 build 後の通知の追加・権限修正は compile step を再利用した warm build です。bit-for-bit の再現性を測った試験ではありません。

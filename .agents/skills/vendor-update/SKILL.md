---
name: vendor-update
description: MSD/seL4 の依存（vendor/ の shallow submodule、toolchain、開発用 image、CI tool、GitHub Actions）を追加・更新するときに使う。全版の変更点、採否、ライセンス、検証済み構成と回帰の結果を確認する。
---

# vendor-update（依存関係の追加と更新）

application、library、依存、toolchain を追加・更新するときは、間のすべての版の変更点とライセンスを確認し、更新前後の結果を比べます。Dependabot が作成した PR も同じ手順で確認してから、人間がマージします。

## 対象と変更履歴の参照先

| 依存 | 現在値の確認方法 | 変更履歴の参照先 | 特に確認すること |
|---|---|---|---|
| seL4 kernel（`vendor/seL4`） | `git submodule status vendor/seL4` と tag | `vendor/seL4/CHANGES.md` の全版、release notes、`git log <old>..<new> -- src/plat/bcm2837 src/arch/arm configs tools/dts` | Security-relevant Changes、BREAKING、Upgrade Notes、`configs/ARM_bcm2837_verified.cmake` と `configs/include/ARM_verified_include.cmake` の差、rpi3 の DTS・memory・alignment の変更、検証済み構成の一覧（docs.sel4.systems の Verified Configurations）。手順は「sel4-verified-config」スキル |
| m5stack-linux-dtoverlays | `git -C vendor/m5stack-linux-dtoverlays rev-parse HEAD` | `git log <old>..<new>`、README、CardputerZero の overlay と driver | 配線、I2C アドレス、割り込み、reset、電源の手順の変化。driver の調査文書（`research/drivers/`）に影響を反映する |
| yomiyasu | `git -C vendor/yomiyasu rev-parse HEAD` | nanaism/yomiyasu の release と変更履歴 | lint と check の挙動、スキルの手順の変化 |
| 開発用 image（`docker/`） | Dockerfile の `FROM` digest と apt・pip・Rust の固定版 | Debian の更新、各 tool の release | cross GCC、CMake、Ninja、QEMU、Rust の版と、seL4 の build 依存の対応 |
| GitHub Actions | workflow の `uses:` の commit SHA と `# vX.Y.Z` | 各 action の release と manifest。後続 major と Node.js runtime のサポートも確認 | 許可リスト（Actions permissions）との整合 |
| CI tool（actionlint、ShellCheck、zizmor、hadolint など） | workflow または requirements の版と SHA-256 | 各 release と公開 checksum | 検査の既定値の変化 |

新しい固定値を追加するときは、同じ PR で Dependabot か固定版の更新確認の監視対象に加えます。

## 手順

1. 作業ブランチで、更新前の基準を記録します（CI の結果、seL4 の verified build の成否と `kernel.elf` のサイズ、QEMU での起動、関係する検査）。
2. 更新する版の間にある変更履歴をすべて読みます。shallow clone に履歴がない場合は必要な範囲だけ fetch するか、upstream の compare・release ページで補います。`.gitmodules` の `shallow = true` は維持します。差分を読めない状態で「変更なし」としません。
3. 変更点を次の四つに分けて記録します。新機能、新しい option・設定項目、既定値の変更は採否と理由を決め、役立つものは同じ変更で採用します。見送る場合は理由と再確認の条件を残し、新しい option は「component-options」スキルの表に反映します。
   - 破壊的な変更と、こちらで必要な対応
   - セキュリティ修正と対象範囲（seL4 では、検証済み構成に影響するかどうか）
   - 新機能、新しい option・設定項目、既定値の変更と採否の理由
   - ライセンスまたはライセンス条件の変更
4. 更新します。submodule は `git -C vendor/<name> fetch --depth 1 origin <tag-or-commit>` の後に `git -C vendor/<name> checkout FETCH_HEAD` を使います。GitHub Actions は full commit SHA と `# vX.Y.Z` を併記します。
5. 更新後に回帰を確かめ、更新前の基準と比べます。seL4 の更新では、検証済み構成の build（`cmake -C vendor/seL4/configs/ARM_bcm2837_verified.cmake`）、`kernel_all_pp.c` の生成、QEMU での起動、capability の表と capDL の検査を含めます。
6. PR 本文に、依存ごとの旧版 → 新版、変更履歴のリンク、四分類の記録、採否と理由、回帰の比較結果を書きます。

## 止める条件

- 検証済み構成の設定が変わった、証明の対象から rpi3 が外れた、ライセンスの根拠が得られない場合は、利用者の判断を得るまで採用を確定しません。
- 上流への Issue・PR・コメントは、利用者の承認を得てから行います。
- 完了時は、変更履歴の四分類、更新前後の結果、CI とログを確認し、実機で確かめていない項目を分けて報告します。

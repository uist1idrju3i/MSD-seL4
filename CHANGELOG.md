# 変更履歴

この文書は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) の形で書き、版は [Semantic Versioning](https://semver.org/lang/ja/) に従います。

## [Unreleased]

### 追加

- CardputerZero の driver ごとの調査を `research/drivers/` に加えました。SoC の共通の部品（GPIO、mailbox、I2C、SPI、DMA など）と、LCD、キーボード、M5IOE1、電源異常、RTC、電池、microSD、USB、音声、IMU、IR、HDMI、無線、カメラ、拡張端子です。mailbox が kernel の割り込み controller と同じ page にあることなど、部品の分け方に関わる点と、作る順序の案を書きました。割り込み controller と mailbox が同じ page にあることが kernel の証明の前提に触れる点（`research/sel4/shared-intc-page.md`）と、実機の確認の計画（`research/experiments/hardware-checklist.md`）も加えました。実機では何も確かめていません。

- `vendor/` に seL4 17.0.0、yomiyasu v2.5.0、m5stack-linux-dtoverlays を shallow submodule で追加しました。
- AGENTS.md、エージェントスキル、DeepWiki の設定を追加しました。
- GitHub Pages の公開サイト（`docs/`）を追加しました。
- 調査・設計の記録（`research/`）を追加しました。
- 共通の開発環境（`docker/msd-sel4-dev`）と、検証済み構成の kernel を build する CI（`Build` workflow の `kernel-verified`）を追加しました。
- CI（`agent-docs`、`Lint`、Advanced 設定の `CodeQL`）と Dependabot の設定を追加しました。
- `vendor/seL4_tools`（elfloader と CMake の helper、seL4 17.0.0 の manifest が指す commit）を shallow submodule で追加しました。
- 固定版の週次確認（`pins-check` workflow と `.github/scripts/check-pins.py`）を追加しました。workflow と Dockerfile の固定値の重複、`vendor/seL4_tools` と seL4 の release manifest の一致を PR ごとに検査し、上流の新しい版を週次の Issue で知らせます。
- CI の `kernel-verified` が、入力の hash が同じ公開済みの開発用 image を、build の来歴を検証して使うようにしました（`docker/msd-sel4-dev available`・`pull`・`ensure`）。公開する image には provenance の attestation を付けます。UID 1000 以外での試験（`tests/msd-sel4-dev/run.sh`）を加えました。

- 公開サイトの検査（`Site` workflow、`.github/scripts/check-site.py`）を加えました。GitHub Pages と同じ builder で `docs/` を build し、生成された HTML の言語、見出し、参照先、script を確かめます。

- seL4 の調査を `research/sel4/` に加えました。形式検証済みのアーキテクチャと platform ごとの SoC・CPU の一覧、userland の基盤の版と推奨、capability・IPC・IRQ・MMIO・DMA の設計方針です。

- kernel 以外の形式検証の調査（`research/verification/beyond-kernel.md`）を加えました。README と公開サイトの設計の頁に、形式検証の範囲、検証していない部分、証明の前提を書き、README に Mermaid の図を加えました。「検証できる」の柱に、kernel の外での形式検証の方針を加えました。

- 最小の root task と QEMU raspi3b の smoke test（`projects/smoke/`、`tools/qemu-smoke.sh`）を加えました。検証済み構成の kernel で root task が起動し、PL011 に出力できるかを確かめます。改変していない seL4 17.0.0 では kernel の起動処理（`vmrs fpexc`）で止まることを、[実験記録](research/experiments/2026-11-11-qemu-smoke.md)に残しました。QEMU での結果で、実機の結果ではありません。

- seL4 の Rust（rust-sel4）の調査を `research/sel4/rust.md` と `research/sel4/rust-adoption.md` に加えました。`ARM_bcm2837_verified` とそれ以外の構成への対応状況、unsafe の境界、形式検証、toolchain、ライセンス、段階的な採用の案です。QEMU だけで動かす Rust の root task の実験（`projects/rust-smoke/`）を加え、`tools/qemu-smoke.sh` に root task の ELF を差し替える `MSD_SMOKE_ROOTSERVER` と、判定の文字列を変える `MSD_SMOKE_MARKER` を加えました。
- `vendor/` に `sel4runtime`、`musllibc`、`util_libs` を、seL4 17.0.0 の manifest が指す commit で shallow submodule として加えました。`check-pins.py manifest` の照合の対象にも加えました。
- IOMMU がないことの影響と、PIO・DMA の方針の案、QEMU で確かめられる範囲を `research/drivers/dma-iommu.md` に加えました。

### 変更

- 割り込み制御器と mailbox が同じ page にあることの扱いを、案 A（page は mailbox の driver だけに渡し、割り込み制御器の register を書かないことを driver の検証の対象にする）に決めました（`research/sel4/shared-intc-page.md`）。

- README を読者別の入口、今の状態、試し方の構成に書き直しました。公開サイト（`docs/`）の開発状況、開発環境、設計の柱と、DeepWiki の設定（`.devin/wiki.json`）を、driver の調査、DMA の方針、Rust の smoke test、割り込み制御器の page の前提に合わせて更新しました。

- 開発用 image に rust-sel4 v6.0.0 の nightly（`nightly-2026-08-21`、`rust-src`、`llvm-tools-preview`）と libclang を入れ、CI の `kernel-verified` で Rust の root task を build して QEMU raspi3b で起動するようにしました。使っていなかった安定版の Rust 1.99.1、curl、xz-utils は image から外しました。`pins-check` は安定版の Rust の代わりに rust-sel4 の release を追います。

- Build、Lint、Site の workflow は、`paths` の代わりに最初の `changes` job で変更されたファイルを判定し、入力が変わっていなければ残りの job を skip するようにしました。各 workflow の最後の `build-result`、`lint-result`、`site-result` は、skip のときも成功になるので、ruleset の required status checks に指定できます。判定は `.github/scripts/changed-files.py` で、試験は `tests/changed-files/run.sh` です。

- research、README、CHANGELOG など文書だけを変えた PR と push では、Build、Lint、Site の workflow を動かさないようにしました（`paths` で、結果に影響するファイルの変更に限定）。agent-docs は文書を検査するので、常に動きます。CodeQL は、`main` の ruleset の code scanning の rule が結果を待つので、すべての PR と push で動かします。Build は週に 1 回の定期実行を加え、開発用 image の CVE の検査と QEMU の smoke test を続けます。

- DMA の方針を決めました（`research/drivers/dma-iommu.md`）。中央の DMA controller を使う device（SPI、SDHOST、I2S など）は、DMA server を通した DMA を既定にし、driver には DMA controller の capability を渡しません。自分で bus master になる device（USB、カメラ、VideoCore、mailbox）は device 自身の DMA を既定にします。PIO は、DMA server ができるまでの間と比較のために残します。AGENTS.md と sel4-capability-design スキルも合わせました。
- seL4 17.0.0 の起動処理の不具合を直す patch（`patches/seL4/`）を加えました。FPU を使わない構成では、`vmrs fpexc` で Undefined Instruction になります。patch は `tools/prepare-sel4-source.sh` が build 時の写しに当て、`vendor/seL4` は変えません。`tools/build-verified-kernel.sh` と `tools/qemu-smoke.sh` は、既定で patch を当てた kernel を build します（`MSD_SEL4_PATCHES=none` で改変なし）。CI の `kernel-verified` は、QEMU raspi3b の smoke test も実行します。週次の `pins-check` は、seL4 の master で patch の箇所が変わったかを知らせます。
- PR の本文と完了報告で、確かめていないことを最初に書く運用を AGENTS.md に加え、PR template（`.github/pull_request_template.md`）を追加しました。

- `main` の `publish-dev-image` は、来歴を検証できる同じ入力の image が公開済みなら build と push を省きます。Trivy の DB を `actions/cache` に置きます。
- Trivy を 0.76.2 に、`debian:trixie-slim` の digest と Debian snapshot を 20261109T224401Z に上げました。

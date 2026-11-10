# 変更履歴

この文書は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) の形で書き、版は [Semantic Versioning](https://semver.org/lang/ja/) に従います。

## [Unreleased]

### 追加

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
- `vendor/` に `sel4runtime`、`musllibc`、`util_libs` を、seL4 17.0.0 の manifest が指す commit で shallow submodule として加えました。`check-pins.py manifest` の照合の対象にも加えました。
- IOMMU がないことの影響と、PIO・DMA の方針の案、QEMU で確かめられる範囲を `research/drivers/dma-iommu.md` に加えました。

### 変更

- `main` の `publish-dev-image` は、来歴を検証できる同じ入力の image が公開済みなら build と push を省きます。Trivy の DB を `actions/cache` に置きます。
- Trivy を 0.76.2 に、`debian:trixie-slim` の digest と Debian snapshot を 20261109T224401Z に上げました。

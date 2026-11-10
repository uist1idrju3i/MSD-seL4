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

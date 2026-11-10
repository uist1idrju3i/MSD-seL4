# 変更履歴

この文書は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) の形で書き、版は [Semantic Versioning](https://semver.org/lang/ja/) に従います。

## [Unreleased]

### 追加

- `vendor/` に seL4 17.0.0、yomiyasu v2.5.0、m5stack-linux-dtoverlays を shallow submodule で追加しました。
- AGENTS.md、エージェントスキル、DeepWiki の設定を追加しました。
- 調査・設計の記録（`research/`）を追加しました。
- 共通の開発環境（`docker/msd-sel4-dev`）と、検証済み構成の kernel を build する CI（`Build` workflow の `kernel-verified`）を追加しました。
- CI（`agent-docs`、`Lint`、Advanced 設定の `CodeQL`）と Dependabot の設定を追加しました。

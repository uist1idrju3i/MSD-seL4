# MSD/seL4

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/uist1idrju3i/MSD-seL4)

MSD/seL4 は、M5Stack CardputerZero（Raspberry Pi CM0 = BCM2837、Cortex-A53、RAM 512 MB、microSD 起動）の上で seL4 microkernel を動かし、CardputerZero の全機能を使える状態を目指す実験的なプロジェクトです。姉妹プロジェクトに Linux を使う [MSD/Linux](https://github.com/uist1idrju3i/MSD-Linux) があります。

## 設計の柱

| 柱 | 方針 |
|---|---|
| seL4 を活かし切る | 検証済み構成の kernel を使い、システムを保護ドメインに分け、各部品に必要な権限（capability）だけを静的に渡します。証明が扱う範囲と扱わない範囲を明記します |
| 電源断で壊れない | いつ電源が落ちても、次の起動で正しい状態に戻れるようにします |
| 更新に失敗しても戻れる | 試験起動で合格したときだけ更新を確定し、失敗したら前の版へ自動で戻ります |
| ハードウェアをすべて使える | LCD、キーボード、音声、センサー、RTC、電池、IR、カメラ、無線、USB、Ethernet、HDMI、拡張端子の driver を、seL4 のユーザー空間に作ります |
| 費用に見合うセキュリティ | 脅威と費用を比べて対策を選び、検証されていない部品（driver、firmware）を必要以上に信頼しない構成にします |
| 検証できる | 証明、QEMU、実機で確かめたことを分けて記録し、確かめていないことを確認済みと書きません |

## 開発状況

開発の準備段階です。OS の実装、ビルド、実機での確認はまだありません。

- seL4 kernel: 17.0.0 を使い、検証済み構成 `ARM_bcm2837_verified`（AArch32、単一コア）を既定にする方針です。
- driver: すべて未着手です。driver ごとに調査と計画を立ててから実装します。

## リポジトリの構成

| パス | 内容 |
|---|---|
| `AGENTS.md` | 作業の規則（エージェントと人間の共通） |
| `.agents/skills/` | 作業手順のスキル（`.claude/skills/` からリンク） |
| `research/` | 内部の調査、設計、実験の記録 |
| `docs/` | GitHub Pages で公開するサイト |
| `vendor/` | 外部リポジトリ（shallow submodule、編集しない） |

## 取得

```sh
git clone https://github.com/uist1idrju3i/MSD-seL4.git
cd MSD-seL4
git submodule update --init --depth 1
```

## ライセンス

[BSD-3-Clause](LICENSE)。`vendor/` の外部コードは、それぞれのライセンスに従います（seL4 kernel は GPL-2.0-only、`libsel4` は BSD-2-Clause など）。

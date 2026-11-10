---
name: release-versioning
description: MSD/seL4 の公開版、CHANGELOG、Release の準備と検査をするときに使う。tag と Release は利用者だけが作る。
---

# リリース版と CHANGELOG

## 規則

- 公開版は SemVer 2.0.0 です。tag は `^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-rc\.([1-9]\d*))?$` に従い、build metadata は付けません。
- `0.y.z` の互換性を壊す変更は MINOR を上げます。同じ SemVer を再発行せず、1 つの commit に複数の SemVer を付けません。
- tag と Release は利用者だけが作ります（tag の ruleset `release` が全 tag の作成を止めているため、公開の前に利用者が ruleset を判断します）。エージェントは CHANGELOG の PR だけを作ります。

## CHANGELOG の書き方

1. [CHANGELOG.md](../../../CHANGELOG.md) は Keep a Changelog の形で、日本語で書きます。利用者に影響する変更は、同じ PR で `## [Unreleased]` に足します。
2. 分類は「追加」「変更」「廃止予定」「削除」「修正」「セキュリティ」です。seL4 kernel の版、検証済み構成からの差分、capability の割り当ての変更は、利用者に影響する変更として書きます。
3. 公開の準備では、Unreleased を `## [x.y.z] - YYYY-MM-DD` に移す PR を作ります。版の決め方（互換性を壊すか、機能を足すか、修正だけか）を PR 本文に書きます。

## 提出前の確認

- [ ] CHANGELOG の Unreleased に、利用者に影響する変更をすべて書いた
- [ ] 版の増分の理由を書いた
- [ ] tag と Release を作っていない

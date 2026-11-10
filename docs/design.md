---
layout: page
title: 設計の柱
permalink: /design/
---

| 柱 | 方針 |
|---|---|
| seL4 を活かし切る | 検証済み構成の kernel を使い、システムを保護ドメインに分け、各部品に必要な権限（capability）だけを静的に渡します |
| 電源断で壊れない | いつ電源が落ちても、次の起動で正しい状態に戻れるようにします |
| 更新に失敗しても戻れる | 試験起動で合格したときだけ更新を確定し、失敗したら前の版へ自動で戻ります |
| ハードウェアをすべて使える | すべての device の driver を、seL4 のユーザー空間に作ります |
| 費用に見合うセキュリティ | 脅威と費用を比べて対策を選び、検証されていない部品を必要以上に信頼しない構成にします |
| 検証できる | 証明、QEMU、実機で確かめたことを分けて記録します |

## seL4 の証明が扱う範囲

MSD/seL4 は、seL4 の検証済み構成 `ARM_bcm2837_verified`（AArch32、単一コア）で kernel を build します。seL4 の [Verified Configurations](https://docs.sel4.systems/projects/sel4/verified-configurations.html) によると、この構成では kernel の機能正当性、完全性と可用性、機密性、バイナリ正当性、capDL による初期化のモデルレベルの機能正当性が証明されています。

証明は、kernel の起動処理、SMMU/IOMMU、debug と printing、ハードウェア、firmware、boot loader、ユーザー空間の driver とアプリケーションを扱いません。また、ハードウェアが正しく動くことを前提にします。MSD/seL4 を「全体が検証済みのシステム」とは呼びません。

## driver をユーザー空間に置く理由

seL4 の kernel には device の driver がありません。driver はユーザー空間の独立した保護ドメインとして動き、渡された device と共有メモリにだけ触れます。1 つの driver の不具合が、ほかの部品や kernel に広がりにくくなります。ただし BCM2837 には IOMMU がないため、DMA を使う driver はメモリ全体に書き込める部品として扱います。

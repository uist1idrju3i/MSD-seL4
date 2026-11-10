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
| 検証できる | 証明、QEMU、実機で確かめたことを分けて記録します。kernel の外でも、実用になる範囲で形式検証を使い、部品ごとに確かめた方法と前提を公開します |

## seL4 の証明が扱う範囲

MSD/seL4 は、seL4 の検証済み構成 `ARM_bcm2837_verified`（AArch32、単一コア）で kernel を build します。seL4 の [Verified Configurations](https://docs.sel4.systems/projects/sel4/verified-configurations.html) によると、この構成では kernel の機能正当性、完全性と可用性、機密性、バイナリ正当性、capDL による初期化のモデルレベルの機能正当性が証明されています。

MSD/seL4 は、seL4 17.0.0 の起動処理の不具合を直す patch を 1 つ当てて build します。証明とバイナリ正当性の検証は改変なしの source を対象にしており、patch を当てた source では実行していません。

証明は、kernel の起動処理、SMMU/IOMMU、debug と printing、ハードウェア、firmware、boot loader、ユーザー空間の driver とアプリケーションを扱いません。また、ハードウェアが正しく動くことを前提にします。MSD/seL4 を「全体が検証済みのシステム」とは呼びません。

## 形式検証していない部分と前提

MSD/seL4 が作る部品（system の初期化、IPC の契約、driver、storage、更新、暗号）は、まだ形式検証していません。部品ごとに、証明、model 検査、静的解析、試験のどれで確かめるかを選び、選んだ方法と結果を公開します。capDL による初期化の証明は algorithm の model のレベルで、C の実装は対象外です。

起動の部品（BCM2837 の ROM、GPU firmware、elfloader）と hardware は、形式検証の対象外です。証明は、次のことを前提にします。CPU、MMU、cache、TLB、割り込み制御器、device の register が仕様どおりに動き、改ざんされていないこと。DMA を使う device が、渡した buffer の外に書かないこと。暗号の基本部品と乱数の源が正しいこと。SD card と電源の回路が、書き込みと電源断を仕様どおりに扱うこと。

QEMU で動いても、CardputerZero の実機で動くことの確認にはなりません。kernel の証明は、ユーザー空間の driver の正しさを証明しません。

## driver をユーザー空間に置く理由

seL4 の kernel には device の driver がありません。driver はユーザー空間の独立した保護ドメインとして動き、渡された device と共有メモリにだけ触れます。1 つの driver の不具合が、ほかの部品や kernel に広がりにくくなります。ただし BCM2837 には IOMMU がないため、DMA を使う driver はメモリ全体に書き込める部品として扱います。

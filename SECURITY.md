# セキュリティ

## 報告の方法

脆弱性は公開の Issue に書かず、GitHub の [Private vulnerability reporting](https://github.com/uist1idrju3i/MSD-seL4/security/advisories/new) で報告してください。

## 対象

- 本リポジトリのコード、設定、CI、開発用 image
- `vendor/` の外部コード（seL4 など）の脆弱性は、まず各上流へ報告してください。本リポジトリでの影響と対応は、こちらで扱います。

## 証明の範囲について

MSD/seL4 は seL4 kernel を検証済み構成 `ARM_bcm2837_verified` で build します。kernel の証明は、kernel の起動処理、SMMU/IOMMU、debug・printing、ハードウェア、firmware、boot loader、ユーザー空間の driver とアプリケーションを対象にしていません。これらの部分の脆弱性も報告の対象です。

MSD/seL4 は実験的なプロジェクトで、まだ公開版はありません。

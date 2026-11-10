---
name: sel4-verified-config
description: seL4 kernel の CMake 構成を決める・変えるとき、seL4 を更新するとき、証明の範囲を文書に書くときに使う。検証済み構成 ARM_bcm2837_verified からの差分と、証明が何を保証し何を保証しないかを確かめる。
---

# sel4-verified-config（検証済み構成と証明の範囲）

## 既定の構成

- 製品の kernel は `vendor/seL4/configs/ARM_bcm2837_verified.cmake`（`configs/include/ARM_verified_include.cmake` を含む）です。AArch32、EL1、単一コア（`KernelMaxNumNodes=1`）、FPU の context switch なし、MCS なし、`KernelVerificationBuild=ON`、`KernelBinaryVerificationBuild=ON`、`-O2`、fastpath あり、printing なしです。
- 公式の [Verified Configurations](https://docs.sel4.systems/projects/sel4/verified-configurations.html) は、AArch32 の Raspberry Pi 3-b について、C レベルの機能正当性（fastpath を含む）、完全性と可用性、機密性、バイナリ正当性、capDL による初期化のモデルレベルの機能正当性を挙げています。
- どの検証済み構成も、SMMU/IOMMU、debug・profiling・printing、kernel の起動処理を対象にしていません。証明はハードウェアが正しいこと、cache と TLB の扱い、boot code と一部のアセンブリの正しさを前提にします（[What the Proofs Assume](https://sel4.systems/Verification/assumptions.html)）。

## 構成を変えるとき

1. 変えたい CMake の変数と値、理由、代替案を書きます。値の一覧は `vendor/seL4` の `config.cmake` 群から取り、「component-options」スキルで網羅を確かめます。
2. 証明への影響を一次資料で調べます。検証済み構成の値を変える、または検証済み構成にない機能（SMP、MCS、hypervisor、FPU の context switch、debug、benchmark）を有効にする変更は、証明の対象外になります。
3. [検証済み構成からの差分](../../../research/sel4/verified-config-deviations.md) に、変数、値、理由、証明への影響、戻す条件、利用者の判断の記録を一行で足します。利用者の判断を得る前に、製品の構成へ入れません。
4. 開発や試験のためだけの構成（printing を有効にした debug build など）は、製品の構成と名前を分け、製品の image に入らないことを確かめます。

## seL4 を更新するとき

- 「vendor-update」スキルの手順に加えて、`CHANGES.md` の Security-relevant Changes と BREAKING の項目のうち、AArch32、`bcm2837`、検証済み構成に関わるものを全部読みます。
- 新旧の `ARM_bcm2837_verified.cmake` と `ARM_verified_include.cmake`、`src/plat/bcm2837/`、`tools/dts/rpi3.dts` の差分を確かめます。
- Verified Configurations のページで、AArch32 の対象に Raspberry Pi 3-b が残っているかを確かめます。

## 書き方

- 「kernel は検証済み構成で build している」と「システムが検証済み」を区別します。証明が扱わない部分（起動処理、firmware、boot loader、driver、アプリケーション、ハードウェア）を、同じ文書で明記します。
- 証明の主張には、seL4 の版、構成のファイル、出典の URL を付けます。

## 提出前の確認

- [ ] 製品の構成が `ARM_bcm2837_verified` のままか、差分が一覧に記録され利用者が判断した
- [ ] 証明の範囲と前提を、出典付きで正確に書いた
- [ ] 開発用の構成が製品の image に入らない

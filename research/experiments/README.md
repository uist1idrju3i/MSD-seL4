# 実験記録の一覧

[索引へ戻る](../README.md)

実験は「experiment-record」スキルに従って記録し、この一覧に 1 行ずつ足します。

実機での確認の計画は [hardware-checklist.md](hardware-checklist.md) にあります。計画で、まだ実施していません。

| 日付 | 記録 | 結論 |
|---|---|---|
| 2026-11-12 | [TOML generator と独立 checker の試験](2026-11-12-capdl-generator.md) | 標準ライブラリだけで capDL を生成し、parser JSON の権限の一致と 8 種類の mutation の拒否を確認した。boot は未試験 |
| 2026-11-12 | [capDL の JSON と Rust initializer の互換性](2026-11-12-capdl-schema.md) | 公式版の JSON には `executable` がなく、fork の指定 revision と resolver を組み合わせる必要がある |
| 2026-11-11 | [QEMU raspi3b での最小 root task の起動](2026-11-11-qemu-smoke.md) | 改変しない seL4 17.0.0 は起動処理の FPEXC の access で止まる。`boot.c` の 1 か所を変えた写しでは root task が PL011 に出力できた（QEMU だけ） |
| 2026-11-11 | [QEMU raspi3b での Rust の root task の起動](2026-11-11-rust-root-task-qemu.md) | rust-sel4 v6.0.0 の root task が `ARM_bcm2837_verified`（FPU の patch あり）で動いた。TLS の register は一致した。text は同じ処理の C の約 4.3 倍（QEMU だけ） |

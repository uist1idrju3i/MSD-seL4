---
layout: home
title: MSD/seL4
---

MSD/seL4 は、M5Stack CardputerZero（Raspberry Pi CM0 = BCM2837、RAM 512 MB）の上で seL4 microkernel を動かし、CardputerZero の全機能を使える状態を目指す実験的なプロジェクトです。姉妹プロジェクトに、Linux を使う [MSD/Linux](https://github.com/uist1idrju3i/MSD-Linux) があります。

現在は開発の準備段階です。検証済み構成の kernel の build と、QEMU での最小の root task（C と Rust）の起動までを CI で確かめています。driver の調査は終わりましたが、実装と実機での確認はまだありません。

- [設計の柱](design.md): 6 つの柱と、seL4 の証明が扱う範囲
- [開発状況](status.md): kernel の構成と driver ごとの状況
- [開発環境](development.md): 共通の開発環境と、検証済み構成の kernel の build

ソースコードと調査の記録は [GitHub](https://github.com/uist1idrju3i/MSD-seL4) にあります。

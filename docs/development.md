---
layout: page
title: 開発環境
permalink: /development/
---

共通の開発環境は Docker の image です。cross GCC、CMake、Ninja、QEMU、Rust と、seL4 の build に必要な Python の package が入っています。

```sh
git clone https://github.com/uist1idrju3i/MSD-seL4.git
cd MSD-seL4
git submodule update --init --depth 1
docker/msd-sel4-dev build
docker/msd-sel4-dev tools/build-verified-kernel.sh
```

`tools/build-verified-kernel.sh` は seL4 kernel を検証済み構成で build し、生成された構成が検証済み構成と一致するかを照合します。kernel の source には、起動処理の不具合を直す patch（`patches/seL4/`）を build 時の写しに当てます。`MSD_SEL4_PATCHES=none` を付けると、改変なしの kernel を build します。`tools/qemu-smoke.sh` は最小の root task を QEMU raspi3b で起動します。QEMU での起動は、実機で起動することを示しません。

# 共通の開発環境

MSD/seL4 の build と試験に使う道具を、Debian trixie の container image にまとめています。apt は `snapshot.debian.org` の日付（`DEBIAN_SNAPSHOT`）に固定し、Python の追加 package は hash を固定しています。

| 道具 | 入手元 | 用途 |
|---|---|---|
| `arm-linux-gnueabi-gcc`、`aarch64-linux-gnu-gcc` | Debian | seL4 kernel と userland の cross build |
| CMake、Ninja | Debian | seL4 の build system |
| Python 3（jinja2、jsonschema、lxml、ply、PyYAML、typing_extensions）と pyfdt | Debian と PyPI | seL4 の build tool |
| device-tree-compiler、libxml2-utils | Debian | DTS と XML の処理 |
| QEMU（`qemu-system-arm`、`qemu-system-aarch64`） | Debian | `raspi3b` machine での起動確認 |
| Rust（rustup、`armv7a-none-eabi`、`aarch64-unknown-none`） | Debian の rustup と Rust の配布物 | userland の候補 |

Haskell（capDL tool）と Isabelle・l4v は、userland の基盤を決めた後に追加を判断します。

## 使い方

```sh
docker/msd-sel4-dev build                          # image を作る（msd-sel4-dev:local）
docker/msd-sel4-dev tools/build-verified-kernel.sh  # 検証済み構成の kernel を build する
docker/msd-sel4-dev bash                           # container の shell に入る
```

`main` に merge されると、CI が `ghcr.io/uist1idrju3i/msd-sel4-dev` に入力の hash の tag（`docker/msd-sel4-dev tag`）と `latest` を公開します。`MSD_SEL4_DEV_IMAGE` を設定すると、その image を使います。

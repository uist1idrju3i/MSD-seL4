# 共通の開発環境

MSD/seL4 の build と試験に使う道具を、Debian trixie の container image にまとめています。apt は `snapshot.debian.org` の日付（`DEBIAN_SNAPSHOT`）に固定し、Python の追加 package は hash を固定しています。

| 道具 | 入手元 | 用途 |
|---|---|---|
| `arm-linux-gnueabi-gcc`、`arm-linux-gnueabi-g++` | Debian | seL4 kernel と root task の cross build |
| `aarch64-linux-gnu-gcc` | Debian | QEMU の smoke test で AArch32 へ移る小さな入口（`projects/smoke/qemu/aarch32-entry.S`） |
| CMake、Ninja | Debian | seL4 の build system |
| Python 3（jinja2、jsonschema、lxml、ply、PyYAML、typing_extensions）と pyfdt | Debian と PyPI | seL4 の build tool |
| device-tree-compiler、libxml2-utils | Debian | DTS と XML の処理 |
| QEMU（`qemu-system-arm`、`qemu-system-aarch64`） | Debian | `raspi3b` machine での起動確認 |
| Rust（rustup、`nightly-2026-08-21`、`rust-src`、`llvm-tools-preview`）、libclang | Debian の rustup と Rust の配布物、Debian | rust-sel4 v6.0.0 の root task の build（`projects/rust-smoke`）。nightly は rust-sel4 の release が固定する版で、`check-pins` が `rust-toolchain.toml` と同じかを検査 |

使っていない道具は入れません。2026-11-11 に、使われていなかった安定版の Rust 1.99.1（`armv7a-none-eabi`、`aarch64-unknown-none`）、curl、xz-utils を外しました。`file`（`tools/build-verified-kernel.sh` が kernel.elf の形式を確かめる）と C++ の cross compiler（`seL4_tools` の `base.cmake` が CXX を有効にする）は、使っているので残しています。Haskell（capDL tool）と Isabelle・l4v は、使う段階で追加を判断します。

## 使い方

```sh
docker/msd-sel4-dev build                          # image を作る（msd-sel4-dev:local）
docker/msd-sel4-dev tools/build-verified-kernel.sh  # 検証済み構成の kernel を build する
docker/msd-sel4-dev bash                           # container の shell に入る
```

`main` に merge されると、CI が `ghcr.io/uist1idrju3i/msd-sel4-dev` に入力の hash の tag（`docker/msd-sel4-dev tag`）と `latest` を公開し、build の来歴（provenance）の attestation を付けます。`MSD_SEL4_DEV_IMAGE` を設定すると、その image を使います。

```sh
docker/msd-sel4-dev available   # 今の入力の image が公開済みなら true
docker/msd-sel4-dev pull        # 公開済みの image を取得し、attestation を検証して msd-sel4-dev:local にする
docker/msd-sel4-dev ensure      # pull が成功すればそれを使い、だめなら build する
tests/msd-sel4-dev/run.sh       # UID 1000・1001・4242 で道具と HOME が使えることを確かめる
```

`pull` は、認証済みの `gh` があれば `gh attestation verify --repo uist1idrju3i/MSD-seL4` で来歴を検証します。`MSD_SEL4_DEV_REQUIRE_ATTESTATION=1` のときは、検証できなければ失敗します。CI の `kernel-verified` は `ensure` を使います。Dockerfile などの入力を変えた PR では tag が変わるため、公開済みの image はなく、その PR で build した image を試験します。

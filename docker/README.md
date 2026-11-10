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

`main` に merge されると、CI が `ghcr.io/uist1idrju3i/msd-sel4-dev` に入力の hash の tag（`docker/msd-sel4-dev tag`）と `latest` を公開し、build の来歴（provenance）の attestation を付けます。`MSD_SEL4_DEV_IMAGE` を設定すると、その image を使います。

```sh
docker/msd-sel4-dev available   # 今の入力の image が公開済みなら true
docker/msd-sel4-dev pull        # 公開済みの image を取得し、attestation を検証して msd-sel4-dev:local にする
docker/msd-sel4-dev ensure      # pull が成功すればそれを使い、だめなら build する
tests/msd-sel4-dev/run.sh       # UID 1000・1001・4242 で道具と HOME が使えることを確かめる
```

`pull` は、認証済みの `gh` があれば `gh attestation verify --repo uist1idrju3i/MSD-seL4` で来歴を検証します。`MSD_SEL4_DEV_REQUIRE_ATTESTATION=1` のときは、検証できなければ失敗します。CI の `kernel-verified` は `ensure` を使います。Dockerfile などの入力を変えた PR では tag が変わるため、公開済みの image はなく、その PR で build した image を試験します。

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
MODE="${1:-serve}"
if [[ "$MODE" == deps ]]; then
  echo 'Fedora 44 (host ou toolbox): sudo dnf install -y gcc-c++ cmake ninja-build boost-devel sqlite-devel openssl-devel python3'
  exit 0
fi
if [[ "$MODE" == clean ]]; then
  echo 'Esta operação remove somente o diretório build/ (os dados em var/ são preservados).'
  rm -rf -- build
  exit 0
fi
if [[ "$MODE" != serve && "$MODE" != test && "$MODE" != build && "$MODE" != doctor ]]; then
  echo "Uso: ./run.sh [serve|test|build|doctor|deps|clean]" >&2
  exit 2
fi
for c in cmake c++ ninja; do command -v "$c" >/dev/null || { echo "Falta $c; execute ./run.sh deps" >&2; exit 1; }; done
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel "${TESSITURA_BUILD_JOBS:-2}"
case "$MODE" in
  build) echo 'Compilação concluída.';;
  doctor) ./build/tessitura-server --doctor --root "$PWD" --db "${TESSITURA_DB:-$PWD/var/tessitura.sqlite3}";;
  test) ctest --test-dir build --output-on-failure;;
  serve) exec ./build/tessitura-server --root "$PWD" --db "${TESSITURA_DB:-$PWD/var/tessitura.sqlite3}" --host "${TESSITURA_HOST:-127.0.0.1}" --port "${TESSITURA_PORT:-18871}";;
esac

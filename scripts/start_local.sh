#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
env_file="$repo/.env"
example="$repo/.env.example"

if [[ ! -f "$env_file" ]]; then
  cp "$example" "$env_file"
fi

get_env() {
  grep -E "^$1=" "$env_file" | sed -E "s/^$1=//" || true
}

set_env() {
  local key="$1"
  local value="$2"
  if grep -qE "^$key=" "$env_file"; then
    sed -i.bak -E "s|^$key=.*|$key=$value|" "$env_file"
  else
    echo "$key=$value" >> "$env_file"
  fi
}

mtx="$(get_env MTX_DIR_HOST)"
if [[ -z "$mtx" ]]; then
  read -rp "Enter local path to 10x MTX folder (e.g. /data/GSM7831813): " mtx
fi
cache="$(get_env VCACHE_DIR_HOST)"
if [[ -z "$cache" ]]; then
  cache="$repo/cache"
fi

set_env MTX_DIR_HOST "$mtx"
set_env VCACHE_DIR_HOST "$cache"

cd "$repo"
docker compose up --build

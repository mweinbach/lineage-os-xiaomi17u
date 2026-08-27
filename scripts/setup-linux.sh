#!/usr/bin/env bash
# Install the Ubuntu host packages; never touches a phone or Android source tree.
set -euo pipefail

packages=(
  git git-lfs gnupg flex bison build-essential zip curl zlib1g-dev
  libc6-dev-i386 libx11-dev lib32z1-dev libgl1-mesa-dev libxml2-utils
  xsltproc unzip fontconfig python3 python3-venv bc ccache lz4
  libssl-dev libelf-dev rsync
)

case "${1:---help}" in
  --print)
    printf '%s\n' 'sudo apt-get update'
    printf 'sudo apt-get install --no-install-recommends -y'
    printf ' %q' "${packages[@]}"
    printf '\n'
    exit 0
    ;;
  --install) ;;
  --help|-h)
    printf '%s\n' 'Usage: bash scripts/setup-linux.sh --print | --install' \
      'Targets Ubuntu 24.04 LTS on native x86-64 Linux.' \
      'The --print option is safe to run on the Mac control host.'
    exit 0
    ;;
  *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
esac

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  printf '%s\n' 'Use a native Linux x86-64 build host. No packages were installed.' >&2
  exit 2
fi
if [[ ! -r /etc/os-release ]]; then
  printf '%s\n' 'Cannot identify this Linux distribution.' >&2
  exit 2
fi
. /etc/os-release
if [[ "${ID:-}" != ubuntu || "${VERSION_ID:-}" != 24.04 ]]; then
  printf '%s\n' 'This package recipe targets Ubuntu 24.04 LTS; adapt it for other distributions.' >&2
  exit 2
fi

sudo apt-get update
sudo apt-get install --no-install-recommends -y "${packages[@]}"
printf '%s\n' 'Host packages installed. Run make refs, then make doctor on this host.'

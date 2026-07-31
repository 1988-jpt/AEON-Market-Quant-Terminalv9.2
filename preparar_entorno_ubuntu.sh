#!/usr/bin/env bash
set -euo pipefail
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-virtualenv \
  autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
  libtinfo6 cmake libffi-dev libssl-dev automake autopoint gettext curl
if [ ! -f "$HOME/.cargo/env" ]; then
  curl https://sh.rustup.rs -sSf | sh -s -- -y
fi
source "$HOME/.cargo/env"
python3 -m virtualenv "$HOME/venv_aeon"
source "$HOME/venv_aeon/bin/activate"
python -m pip install --upgrade pip setuptools wheel
pip install buildozer cython==0.29.34
printf '\nEntorno listo. Ejecute:\nsource ~/venv_aeon/bin/activate\nbuildozer android debug\n'

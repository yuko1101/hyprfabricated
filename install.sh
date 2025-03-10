#!/bin/bash
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Please, don't run as root."
  exit 1
fi

REPO_URL="https://github.com/Axenide/Ax-Shell"
INSTALL_DIR="$HOME/.config/Ax-Shell"
PACKAGES=(
  acpi
  brightnessctl
  cava
  fabric-cli-git
  gnome-bluetooth-3.0
  gpu-screen-recorder
  grimblast
  hypridle
  hyprlock
  hyprpicker
  hyprsunset
  imagemagick
  libnotify
  matugen-bin
  noto-fonts-emoji
  playerctl
  python-fabric-git
  python-ijson
  python-pillow
  python-psutil
  python-requests
  python-setproctitle
  python-toml
  python-watchdog
  swappy
  swww
  tesseract
  uwsm
  wl-clipboard
  wlinhibit
)

if command -v yay >/dev/null; then
  aur_helper="yay"
elif command -v paru >/dev/null; then
  aur_helper="paru"
else
  echo "Instalando yay-bin..."
  tmpdir=$(mktemp -d)
  git clone https://aur.archlinux.org/yay-bin.git "$tmpdir/yay-bin"
  (cd "$tmpdir/yay-bin" && makepkg -si --noconfirm)
  rm -rf "$tmpdir"
  aur_helper="yay"
fi

if [ -d "$INSTALL_DIR" ]; then
  git -C "$INSTALL_DIR" pull
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

yes | "$aur_helper" -Syy --devel --needed --noconfirm gray-git
"$aur_helper" -Syy --devel --needed --noconfirm "${PACKAGES[@]}"

killall ax-shell 2>/dev/null || true
uwsm app -- python "$INSTALL_DIR/main.py" > /dev/null 2>&1 & disown

echo "Instalación completa."

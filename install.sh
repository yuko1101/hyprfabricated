#!/bin/bash

set -e  # Exit immediately if a command fails
set -u  # Treat unset variables as errors
set -o pipefail  # Prevent errors in a pipeline from being masked

REPO_URL="https://github.com/tr1xem/hyprfabricated.git"
INSTALL_DIR="$HOME/.config/hyprfabricated"
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
    wlinhibit tesseract
    plasma-browser-integration
    cantarell-fonts

)

# Prevent running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "Please do not run this script as root."
    exit 1
fi

wasYayInstalled=1
wasParuInstalled=1

aur_helper="yay"

# Check if paru exists, otherwise use yay
if command -v paru &>/dev/null; then
    aur_helper="paru"
elif command -v yay &>/dev/null; then
    wasParuInstalled=0
else
    wasYayInstalled=0
    echo "Installing yay-bin..."
    tmpdir=$(mktemp -d)
    git clone --depth=1 https://aur.archlinux.org/yay-bin.git "$tmpdir/yay-bin"
    cd "$tmpdir/yay-bin"
    makepkg -si --noconfirm
    cd - > /dev/null
    rm -rf "$tmpdir"
fi

# Clone or update the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating hyprfabricated..."
    git -C "$INSTALL_DIR" pull
else
    echo "Cloning hyprfabricated..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

echo "Installing gray-git..."
yes | $aur_helper -Syy --needed --noconfirm gray-git || true

# Install required packages using the detected AUR helper (only if missing)
echo "Installing required packages..."
$aur_helper -Syy --needed --noconfirm "${PACKAGES[@]}" || true

# Update outdated packages from the list
echo "Updating outdated required packages..."
outdated=$($aur_helper -Qu | awk '{print $1}')
to_update=()
for pkg in "${PACKAGES[@]}"; do
    if echo "$outdated" | grep -q "^$pkg$"; then
        to_update+=("$pkg")
    fi
done

if [ ${#to_update[@]} -gt 0 ]; then
    $aur_helper -S --noconfirm "${to_update[@]}" || true
else
    echo "All required packages are up-to-date."
fi

python "$INSTALL_DIR/config/config.py"
echo "Starting hyprfabricated..."
killall hyprfabricated 2>/dev/null || true
uwsm app -- python "$INSTALL_DIR/main.py" > /dev/null 2>&1 & disown

if [ "$wasYayInstalled" -eq 0 ] && [ "$wasParuInstalled" -eq 0 ]; then
    sudo pacman -Rns yay
fi

echo "Doing Fallback Image..."
cp "$INSTALL_DIR/assets/wallpapers_example/example-1.jpg" ~/.current.wall
echo "If you see a transparent bar change the wallpaper from the notch"
echo "Backup your hypridle and hyprlock config before accepting in config"
echo "Installation complete."

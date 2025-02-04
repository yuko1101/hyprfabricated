#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error
set -o pipefail  # Prevent errors in a pipeline from being masked

REPO_URL="https://github.com/Axenide/Ax-Shell"
INSTALL_DIR="$HOME/.config/Ax-Shell"
PACKAGES=(
    fabric-cli-git
    gnome-bluetooth-3.0
    gray-git
    grimblast
    hypridle
    hyprlock
    hyprpicker
    imagemagick
    libnotify
    matugen-bin
    python-fabric-git
    python-pillow
    python-setproctitle
    python-toml
    swww
    ttf-tabler-icons
    uwsm
    vte3
)

# Ensure the script is run with sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Restarting with sudo..."
    exec sudo bash "$0"
fi

# Install yay-bin if not installed (as the normal user)
if ! command -v yay &>/dev/null; then
    echo "Installing yay-bin..."
    tmpdir=$(sudo -u "$SUDO_USER" mktemp -d)
    sudo -u "$SUDO_USER" git clone https://aur.archlinux.org/yay-bin.git "$tmpdir/yay-bin"
    cd "$tmpdir/yay-bin"
    sudo -u "$SUDO_USER" makepkg -si --noconfirm
    cd - > /dev/null
    rm -rf "$tmpdir"
fi

# Clone or update the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating Ax-Shell..."
    sudo -u "$SUDO_USER" git -C "$INSTALL_DIR" pull
else
    echo "Cloning Ax-Shell..."
    sudo -u "$SUDO_USER" git clone "$REPO_URL" "$INSTALL_DIR"
fi

# Install required packages using yay with --sudoloop
echo "Installing required packages..."
sudo -u "$SUDO_USER" yay -S --needed --noconfirm --sudoloop "${PACKAGES[@]}"

# Launch Ax-Shell
echo "Starting Ax-Shell..."
sudo -u "$SUDO_USER" uwsm app -- python "$INSTALL_DIR/main.py" & disown

echo "Installation complete."

# Install required packages with yay
echo "Installing required packages..."
yay -S --needed --noconfirm "${PACKAGES[@]}"

# Launch Ax-Shell
echo "Starting Ax-Shell..."
uwsm app -- python "$INSTALL_DIR/main.py" & disown

echo "Installation complete."

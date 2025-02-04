#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error
set -o pipefail  # Prevent errors in a pipeline from being masked

REPO_URL="https://github.com/Axenide/Ax-Shell"
INSTALL_DIR="$HOME/.config/Ax-Shell"
PACKAGES=(
    fabric-cli-git
    libnotify
    matugen-bin
    python-fabric-git
    python-setproctitle
    swww
    uwsm
    vte3
    ttf-tabler-icons
    grimblast
    wl-clipboard
    hypridle
    hyprpicker
    imagemagick
    python-pillow
    python-toml
)

# Clone or update the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating Ax-Shell..."
    git -C "$INSTALL_DIR" pull
else
    echo "Cloning Ax-Shell..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# Install required packages with yay
if ! command -v yay &>/dev/null; then
    echo "Error: 'yay' is not installed. Please install it first." >&2
    exit 1
fi

echo "Installing required packages..."
yay -S --needed --noconfirm "${PACKAGES[@]}"

# Launch Ax-Shell
echo "Starting Ax-Shell..."
uwsm app -- python "$INSTALL_DIR/main.py" & disown

echo "Installation complete."

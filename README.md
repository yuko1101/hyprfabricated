<h1 align="center">🍣 Ax-Shell</h1>
<p align="center">A hackable and powerful shell for Hyprland, powered by <a href="https://github.com/Fabric-Development/fabric/">Fabric</a>!</p>

<table>
  <tr>
    <td colspan="4"><img src="assets/screenshots/1.png"></td>
  </tr>
  <tr>
    <td colspan="1"><img src="assets/screenshots/2.png"></td>
    <td colspan="1"><img src="assets/screenshots/3.png"></td>
    <td colspan="1" align="center"><img src="assets/screenshots/4.png"></td>
    <td colspan="1" align="center"><img src="assets/screenshots/5.png"></td>
  </tr>
</table>

<p align="center">
  <a href="https://ko-fi.com/Axenide" target="_blank">
    <img src="assets/ko-fi.gif" alt="Apóyame en Ko-fi">
  </a>
</p>

## 📦 Installation

> [!CAUTION]
> PRE-RELEASE STATE. USABLE BUT INCOMPLETE.

> [!NOTE]
> You need a functioning Hyprland installation.

### Arch Linux
```bash
curl -fsSL https://raw.githubusercontent.com/Axenide/Ax-Shell/main/install.sh | bash
```

### Manual Installation
1. Install dependencies:
    - [Fabric](https://github.com/Fabric-Development/fabric)
    - [fabric-cli](https://github.com/Fabric-Development/fabric-cli)
    - [Gray](https://github.com/Fabric-Development/gray)
    - [Matugen](https://github.com/InioX/matugen)
    - `gnome-bluetooth-3.0`
    - `grimblast`
    - `hypridle`
    - `hyprlock`
    - `hyprpicker`
    - `imagemagick`
    - `libnotify`
    - `swww`
    - `uwsm`
    - `vte3`
    - Python dependencies:
        - pillow
        - toml
        - setproctitle
    - Fonts (automated on first run):
        - Zed Sans
        - Tabler Icons

2. Download and run Ax-Shell:
    ```bash
    git clone https://github.com/Axenide/Ax-Shell.git ~/.config/Ax-Shell
    uwsm -- app python ~/.config/Ax-Shell/main.py > /dev/null 2>&1 & disown
    ```

## 🚀 Roadmap
- [x] App Launcher
- [x] Power Menu
- [x] Wallpaper Selector
- [x] System Tray
- [x] Notifications
- [x] Terminal
- [x] Kanban Board
- [x] Calendar (Incomplete)
- [x] Color Picker
- [ ] Dashboard
- [ ] Network Manager
- [ ] Bluetooth Manager
- [ ] Power Manager
- [ ] Settings
- [ ] Screenshot Tool
- [ ] Screen Recorder
- [ ] Clipboard Manager
- [ ] Dock
- [ ] Workspaces Overview
- [ ] Multimodal AI Assistant

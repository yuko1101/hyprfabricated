<p align="center">
  <img src="assets/cover.png">
</p>

<p align="center"><sup>A ʜᴀᴄᴋᴀʙʟᴇ sʜᴇʟʟ ꜰᴏʀ Hʏᴘʀʟᴀɴᴅ, ᴘᴏᴡᴇʀᴇᴅ ʙʏ <a href="https://github.com/Fabric-Development/fabric/">Fᴀʙʀɪᴄ</a>.</sup></p>

## 📸 Screenshots
<table align="center">
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

<table align="center">
  <tr>
    <td align="center"><sup>✨ sᴜᴘᴘᴏʀᴛ ᴛʜᴇ ᴘʀᴏᴊᴇᴄᴛ ✨</sup></td>
  </tr>
  <tr>
    <td align="center">
      <a href='https://ko-fi.com/Axenide' target='_blank'>
        <img style='border:0px;height:128px;' 
             src='https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExc3N4NzlvZWs2Z2tsaGx4aHgwa3UzMWVpcmNwZTNraTM2NW84ZDlqbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/PaF9a1MpqDzovyqVKj/giphy.gif' 
             border='0' alt='Support me on Ko-fi!' />
      </a>
    </td>
  </tr>
</table>

## 📦 Installation

> [!CAUTION]
> PRE-RELEASE STATE. USABLE BUT INCOMPLETE.

> [!NOTE]
> You need a functioning Hyprland installation.

### Arch Linux

> [!TIP]
> This command also works for updating an existing installation!


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
- [x] Pins
- [x] Kanban Board
- [x] Calendar (Incomplete)
- [x] Color Picker
- [ ] Dashboard
- [ ] Network Manager
- [x] Bluetooth Manager
- [ ] Power Manager
- [x] Settings
- [ ] Screenshot Tool
- [ ] Screen Recorder
- [ ] Clipboard Manager
- [ ] Dock
- [x] Workspaces Overview
- [ ] Multimodal AI Assistant

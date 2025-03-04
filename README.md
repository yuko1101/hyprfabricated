<h1 align="center"><b>HYPRFABRICATED</b></h1>


<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/tr1xem/hyprfabricated?style=for-the-badge&logo=github&color=FFB686&logoColor=D9E0EE&labelColor=292324)](https://github.com/tr1xem/hyprfabricated/stargazers)
[![Hyprland](https://img.shields.io/badge/Made%20for-Hyprland-pink?style=for-the-badge&logo=linux&logoColor=D9E0EE&labelColor=292324&color=C6A0F6)](https://hyprland.org/)
[![Maintained](https://img.shields.io/badge/Maintained-Yes-blue?style=for-the-badge&logo=linux&logoColor=D9E0EE&labelColor=292324&color=3362E1)]()
[![Discord](https://dcbadge.limes.pink/api/server/https://discord.gg/vfSCyFZ6t2)](https://discord.gg/vfSCyFZ6t2)

</div>
<p align="center"><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Telegram-Animated-Emojis/main/Activity/Sparkles.webp" alt="Sparkles" width="25" height="25" /> <sup>A ʜᴀᴄᴋᴀʙʟᴇ sʜᴇʟʟ ꜰᴏʀ Hʏᴘʀʟᴀɴᴅ, ᴘᴏᴡᴇʀᴇᴅ ʙʏ <a href="https://github.com/Fabric-Development/fabric/">Fᴀʙʀɪᴄ</a>. </sup><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Telegram-Animated-Emojis/main/Activity/Sparkles.webp" alt="Sparkles" width="25" height="25" /></p>



<h2><sub><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Camera%20with%20Flash.png" alt="Camera with Flash" width="25" height="25" /></sub> Screenshots</h2>
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

<h2><sub><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Package.png" alt="Package" width="25" height="25" /></sub> Installation</h2>

> [!NOTE]
> - You need a functioning Hyprland installation. <br>
> - You need to install plasma-browser-integration for mpris and cava to work as it is intended

### Arch Linux

> [!TIP]
> - This command also works for updating an existing installation!!! <br>
> - If you see a transparent bar just change the wallpaper from notch > wallpaper as then it would gen color configs

```bash
curl -fsSL https://raw.githubusercontent.com/tr1xem/hyprfabricated/main/install.sh | bash
```

### Manual Installation
1. Install dependencies:
    - [Fabric](https://github.com/Fabric-Development/fabric)
    - [fabric-cli](https://github.com/Fabric-Development/fabric-cli)
    - [Gray](https://github.com/Fabric-Development/gray)
    - [Matugen](https://github.com/InioX/matugen)
    - `acpi`
    - `brightnessctl`
    - `gnome-bluetooth-3.0`
    - `gpu-screen-recorder`
    - `grimblast`
    - `hypridle`
    - `hyprlock`
    - `hyprpicker`
    - `hyprsunset`
    - `imagemagick`
    - `libnotify`
    - `playerctl`
    - `swappy`
    - `swww`
    - `tesseract`
    - `uwsm`
    - `vte3`
    - `cantarell-fonts-0.100`
    - `wlinhibit`
    - `gpu-screen-recorder`
    - `grimblast-git`
    - Python dependencies:
        - pillow
        - toml
        - setproctitle
        - watchdog
        - requests
    - Fonts (automated on first run):
        - Zed Sans
        - Tabler Icons

2. Download and run Ax-Shell:
    ```bash
    git clone https://github.com/tr1xem/hyprfabricated.git ~/.config/hyprfabricated
    uwsm -- app python ~/.config/hyprfabricated/main.py > /dev/null 2>&1 & disown
    ```

<h2><sub><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Rocket.png" alt="Rocket" width="25" height="25" /></sub> Roadmap</h2>

- [x] App Launcher
- [x] Power Menu
- [x] Wallpaper Selector
- [x] System Tray
- [x] Notifications
- [x] Terminal
- [x] Pins
- [x] Kanban Board
- [x] Calendar
- [x] Color Picker
- [x] Dashboard
- [x] Bluetooth Manager
- [x] Power Manager
- [x] Settings
- [x] Screenshot
- [x] Screen Recorder
- [x] OCR
- [x] Workspaces Overview
- [ ] Network Manager
- [ ] Clipboard Manager
- [ ] Emoji Manager
- [ ] Dock
- [ ] Multimodal AI Assistant
- [ ] Vertical Layout
- [ ] Multi-monitor support

# Credits

- <b>Huge Thanks to the original Project https://github.com/Axenide/Ax-Shell/ </b>
- [Amariokhz](https://github.com/mariokhz)

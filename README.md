<h1 align="center"><b>HYPRFABRICATED</b></h1>


<p align="center"><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Telegram-Animated-Emojis/main/Activity/Sparkles.webp" alt="Sparkles" width="25" height="25" /> <sup>A ʜᴀᴄᴋᴀʙʟᴇ sʜᴇʟʟ ꜰᴏʀ Hʏᴘʀʟᴀɴᴅ, ᴘᴏᴡᴇʀᴇᴅ ʙʏ <a href="https://github.com/Fabric-Development/fabric/">Fᴀʙʀɪᴄ</a>. </sup><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Telegram-Animated-Emojis/main/Activity/Sparkles.webp" alt="Sparkles" width="25" height="25" /></p>

<p align="center">
  <a href="https://github.com/Axenide/Ax-Shell/discussions"><sub><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/High%20Voltage.png" alt="High Voltage" width="16" height="16" /></sub> Feedback</a> ::
  <a href="https://github.com/Axenide/Ax-Shell/issues"><sub><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Symbols/Triangular%20Flag.png" alt="Triangular Flag" width="16" height="16" /></sub> Support</a> ::
  <a href="https://ko-fi.com/Axenide"><sub><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Smilies/Sparkling%20Heart.png" alt="Sparkling Heart" width="16" height="16" /></sub> Donate</a>
</p>


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

> [!CAUTION]
> PRE-RELEASE STATE. USABLE BUT INCOMPLETE.

> [!NOTE]
> You need a functioning Hyprland installation.
> You need to install plasma-browser-integration for mpris and cava to work as it is intended

### Arch Linux

> [!TIP]
> This command also works for updating an existing installation!


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
    - `auto-cpufreq`
    - `playerctl`
    - `gnome-bluetooth-3.0`
    - `grimblast`
    - `hypridle`
    - `hyprlock`
    - `hyprpicker`
    - `hyprsunset`
    - `imagemagick`
    - `libnotify`
    - `swww`
    - `uwsm`
    - `vte3`
    - `cantarell-fonts-0.100`
    - `wlinhibit`
    - Python dependencies:
        - pillow
        - toml
        - setproctitle
        - watchdog
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
- [x] Sys Info
- [x] Calendar (Incomplete)
- [x] Color Picker
- [ ] Dashboard
- [ ] Network Manager
- [x] Bluetooth Manager
- [x] Power Manager
- [x] Settings
- [ ] Screenshot Tool
- [ ] Screen Recorder
- [ ] Clipboard Manager
- [ ] Dock
- [x] Workspaces Overview
- [ ] Multimodal AI Assistant
- [ ] Vertical Layout

# Credits

- <b>Huge Thanks to the original Project https://github.com/Axenide/Ax-Shell/ </b>
- [Amariokhz](https://github.com/mariokhz)

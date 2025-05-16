import json
import os
import shutil
import subprocess
import time
import toml
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

from fabric.utils.helpers import exec_shell_command_async

from .data import APP_NAME, APP_NAME_CAP, CONFIG_DIR, HOME_DIR
from .settings_constants import DEFAULTS, SOURCE_STRING

# Global variable to store binding variables, managed by this module
bind_vars = {}

def deep_update(target: dict, update: dict) -> dict:
    """
    Recursively update a nested dictionary with values from another dictionary.
    """
    for key, value in update.items():
        if isinstance(value, dict):
            target[key] = deep_update(target.get(key, {}), value)
        else:
            target[key] = value
    return target

def ensure_matugen_config():
    """
    Ensure that the matugen configuration file exists and is updated
    with the expected settings.
    """
    expected_config = {
        'config': {
            'reload_apps': True,
            'wallpaper': {
                'command': 'swww',
                'arguments': [
                    'img', '-t', 'outer',
                    '--transition-duration', '1.5',
                    '--transition-step', '255',
                    '--transition-fps', '60',
                    '-f', 'Nearest'
                ],
                'set': True
            },
            'custom_colors': {
                'red': {'color': "#FF0000", 'blend': True},
                'green': {'color': "#00FF00", 'blend': True},
                'yellow': {'color': "#FFFF00", 'blend': True},
                'blue': {'color': "#0000FF", 'blend': True},
                'magenta': {'color': "#FF00FF", 'blend': True},
                'cyan': {'color': "#00FFFF", 'blend': True},
                'white': {'color': "#FFFFFF", 'blend': True}
            }
        },
        'templates': {
            'hyprland': {
                'input_path': f'~/.config/{APP_NAME_CAP}/config/matugen/templates/hyprland-colors.conf',
                'output_path': f'~/.config/{APP_NAME_CAP}/config/hypr/colors.conf'
            },
            f'{APP_NAME}': {
                'input_path': f'~/.config/{APP_NAME_CAP}/config/matugen/templates/{APP_NAME}.css',
                'output_path': f'~/.config/{APP_NAME_CAP}/styles/colors.css',
                'post_hook': f"fabric-cli exec {APP_NAME} 'app.set_css()' &"
            }
        }
    }

    config_path = os.path.expanduser('~/.config/matugen/config.toml')
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    existing_config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            existing_config = toml.load(f)
        shutil.copyfile(config_path, config_path + '.bak')

    merged_config = deep_update(existing_config, expected_config)
    with open(config_path, 'w') as f:
        toml.dump(merged_config, f)

    current_wall = os.path.expanduser("~/.current.wall")
    hypr_colors = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/colors.conf")
    css_colors = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/styles/colors.css")
    
    if not os.path.exists(current_wall) or not os.path.exists(hypr_colors) or not os.path.exists(css_colors):
        os.makedirs(os.path.dirname(hypr_colors), exist_ok=True)
        os.makedirs(os.path.dirname(css_colors), exist_ok=True)
        
        image_path = ""
        if not os.path.exists(current_wall):
            example_wallpaper_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/assets/wallpapers_example/example-1.jpg")
            if os.path.exists(example_wallpaper_path):
                try:
                    os.symlink(example_wallpaper_path, current_wall)
                    image_path = example_wallpaper_path
                except FileExistsError:
                    os.remove(current_wall)
                    os.symlink(example_wallpaper_path, current_wall)
                    image_path = example_wallpaper_path
        else:
            image_path = os.path.realpath(current_wall) if os.path.islink(current_wall) else current_wall
        
        if image_path: # Only run matugen if we have a valid image_path
            print(f"Generating color theme from wallpaper: {image_path}")
            try:
                matugen_cmd = f"matugen image '{image_path}'"
                exec_shell_command_async(matugen_cmd)
                print("Matugen color theme generation initiated.")
            except FileNotFoundError:
                print("Error: matugen command not found. Please install matugen.")
            except Exception as e:
                print(f"Error initiating matugen: {e}")
        else:
            print("Warning: No wallpaper found to generate matugen theme from.")


def load_bind_vars():
    """
    Load saved key binding variables from JSON, if available.
    Populates the global `bind_vars`.
    """
    global bind_vars
    # Start with a fresh copy of defaults
    bind_vars = DEFAULTS.copy()

    config_json = os.path.expanduser(f'~/.config/{APP_NAME_CAP}/config/config.json')
    if os.path.exists(config_json):
        try:
            with open(config_json, 'r') as f:
                saved_vars = json.load(f)
                # Update defaults with saved values, ensuring all keys exist
                for key in DEFAULTS:
                    if key in saved_vars:
                        bind_vars[key] = saved_vars[key]
                    # else: bind_vars[key] is already DEFAULTS[key]
                
                # Ensure nested dicts for metric visibility are properly handled
                for vis_key in ['metrics_visible', 'metrics_small_visible']:
                    if vis_key in DEFAULTS: # Check if the key exists in DEFAULTS
                        # Ensure the key exists in bind_vars and is a dict, or reset to default dict
                        if vis_key not in bind_vars or not isinstance(bind_vars[vis_key], dict):
                            bind_vars[vis_key] = DEFAULTS[vis_key].copy()
                        else:
                            # Ensure all sub-keys from DEFAULTS are present in bind_vars[vis_key]
                            for m_key in DEFAULTS[vis_key]:
                                if m_key not in bind_vars[vis_key]:
                                    bind_vars[vis_key][m_key] = DEFAULTS[vis_key][m_key]
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {config_json}. Using defaults.")
            bind_vars = DEFAULTS.copy() # Reset to defaults on error
        except Exception as e:
            print(f"Error loading config from {config_json}: {e}. Using defaults.")
            bind_vars = DEFAULTS.copy() # Reset to defaults on error
    # If config_json doesn't exist, bind_vars is already DEFAULTS.copy()


def generate_hyprconf() -> str:
    """
    Generate the Hypr configuration string using the current bind_vars.
    """
    home = os.path.expanduser('~') # HOME_DIR could also be used if it's always '~'
    # Uses the global bind_vars from this module
    return f"""exec-once = uwsm-app $(python {home}/.config/{APP_NAME_CAP}/main.py)
exec = pgrep -x "hypridle" > /dev/null || uwsm app -- hypridle
exec = uwsm app -- swww-daemon
exec-once =  wl-paste --type text --watch cliphist store
exec-once =  wl-paste --type image --watch cliphist store

$fabricSend = fabric-cli exec {APP_NAME}
$axMessage = notify-send "Axenide" "What are you doing?" -i "{home}/.config/{APP_NAME_CAP}/assets/ax.png" -a "Source Code" -A "Be patient. 🍙"

bind = {bind_vars['prefix_restart']}, {bind_vars['suffix_restart']}, exec, killall {APP_NAME}; uwsm-app $(python {home}/.config/{APP_NAME_CAP}/main.py) # Reload {APP_NAME_CAP} | Default: SUPER ALT + B
bind = {bind_vars['prefix_axmsg']}, {bind_vars['suffix_axmsg']}, exec, $axMessage # Message | Default: SUPER + A
bind = {bind_vars['prefix_dash']}, {bind_vars['suffix_dash']}, exec, $fabricSend 'notch.open_notch("dashboard")' # Dashboard | Default: SUPER + D
bind = {bind_vars['prefix_bluetooth']}, {bind_vars['suffix_bluetooth']}, exec, $fabricSend 'notch.open_notch("bluetooth")' # Bluetooth | Default: SUPER + B
bind = {bind_vars['prefix_pins']}, {bind_vars['suffix_pins']}, exec, $fabricSend 'notch.open_notch("pins")' # Pins | Default: SUPER + Q
bind = {bind_vars['prefix_kanban']}, {bind_vars['suffix_kanban']}, exec, $fabricSend 'notch.open_notch("kanban")' # Kanban | Default: SUPER + N
bind = {bind_vars['prefix_launcher']}, {bind_vars['suffix_launcher']}, exec, $fabricSend 'notch.open_notch("launcher")' # App Launcher | Default: SUPER + R
bind = {bind_vars['prefix_tmux']}, {bind_vars['suffix_tmux']}, exec, $fabricSend 'notch.open_notch("tmux")' # App Launcher | Default: SUPER + T
bind = {bind_vars['prefix_cliphist']}, {bind_vars['suffix_cliphist']}, exec, $fabricSend 'notch.open_notch("cliphist")' # App Launcher | Default: SUPER + V
bind = {bind_vars['prefix_toolbox']}, {bind_vars['suffix_toolbox']}, exec, $fabricSend 'notch.open_notch("tools")' # Toolbox | Default: SUPER + S
bind = {bind_vars['prefix_overview']}, {bind_vars['suffix_overview']}, exec, $fabricSend 'notch.open_notch("overview")' # Overview | Default: SUPER + TAB
bind = {bind_vars['prefix_wallpapers']}, {bind_vars['suffix_wallpapers']}, exec, $fabricSend 'notch.open_notch("wallpapers")' # Wallpapers | Default: SUPER + COMMA
bind = {bind_vars['prefix_emoji']}, {bind_vars['suffix_emoji']}, exec, $fabricSend 'notch.open_notch("emoji")' # Emoji | Default: SUPER + PERIOD
bind = {bind_vars['prefix_power']}, {bind_vars['suffix_power']}, exec, $fabricSend 'notch.open_notch("power")' # Power Menu | Default: SUPER + ESCAPE
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'bar.toggle_hidden()' # Toggle Bar | Default: SUPER CTRL + B
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'notch.toggle_hidden()' # Toggle Notch | Default: SUPER CTRL + B
bind = {bind_vars['prefix_css']}, {bind_vars['suffix_css']}, exec, $fabricSend 'app.set_css()' # Reload CSS | Default: SUPER SHIFT + B
bind = {bind_vars['prefix_restart_inspector']}, {bind_vars['suffix_restart_inspector']}, exec, killall {APP_NAME}; uwsm-app $(GTK_DEBUG=interactive python {home}/.config/{APP_NAME_CAP}/main.py) # Restart with inspector | Default: SUPER CTRL ALT + B

# Wallpapers directory: {bind_vars['wallpapers_dir']}

source = {home}/.config/{APP_NAME_CAP}/config/hypr/colors.conf

layerrule = noanim, fabric

exec = cp $wallpaper ~/.current.wall

general {{
    col.active_border = 0xff$primary
    col.inactive_border = 0xff$surface
    gaps_in = 2
    gaps_out = 4
    border_size = 2
    layout = dwindle
}}

cursor {{
  no_warps=true
}}

decoration {{
    blur {{
        enabled = yes
        size = 5
        passes = 3
        new_optimizations = yes
        contrast = 1
        brightness = 1
    }}
    rounding = 14
    shadow {{
      enabled = true
      range = 10
      render_power = 2
      color = rgba(0, 0, 0, 0.25)
    }}
}}

animations {{
    enabled = yes
    bezier = myBezier, 0.4, 0, 0.2, 1
    animation = windows, 1, 2.5, myBezier, popin 80%
    animation = border, 1, 2.5, myBezier
    animation = fade, 1, 2.5, myBezier
    animation = workspaces, 1, 2.5, myBezier, {'slidefadevert' if bind_vars.get('vertical', False) else 'slidefade'} 20%
}}
"""

def ensure_face_icon():
    """
    Ensure the face icon exists. If not, copy the default icon.
    """
    face_icon_path = os.path.expanduser("~/.face.icon")
    default_icon_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/assets/default.png")
    if not os.path.exists(face_icon_path) and os.path.exists(default_icon_path):
        try:
            shutil.copy(default_icon_path, face_icon_path)
        except Exception as e:
            print(f"Error copying default face icon: {e}")

def backup_and_replace(src: str, dest: str, config_name: str):
    """
    Backup the existing configuration file and replace it with a new one.
    """
    try:
        if os.path.exists(dest):
            backup_path = dest + ".bak"
            shutil.copy(dest, backup_path)
            print(f"{config_name} config backed up to {backup_path}")
        os.makedirs(os.path.dirname(dest), exist_ok=True) # Ensure dest directory exists
        shutil.copy(src, dest)
        print(f"{config_name} config replaced from {src}")
    except Exception as e:
        print(f"Error backing up/replacing {config_name} config: {e}")


def start_config():
    """
    Run final configuration steps: ensure necessary configs, write the hyprconf, and reload.
    """
    print(f"{time.time():.4f}: start_config: Ensuring matugen config...")
    ensure_matugen_config()
    print(f"{time.time():.4f}: start_config: Ensuring face icon...")
    ensure_face_icon()
    print(f"{time.time():.4f}: start_config: Generating hypr conf...")

    hypr_config_dir = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/")
    os.makedirs(hypr_config_dir, exist_ok=True)
    # Use APP_NAME_CAP for the conf file name to match SOURCE_STRING
    hypr_conf_path = os.path.join(hypr_config_dir, f"{APP_NAME_CAP}.conf")
    try:
        with open(hypr_conf_path, "w") as f:
            f.write(generate_hyprconf())
        print(f"Generated Hyprland config at {hypr_conf_path}")
    except Exception as e:
        print(f"Error writing Hyprland config: {e}")
    print(f"{time.time():.4f}: start_config: Finished generating hypr conf.")

    print(f"{time.time():.4f}: start_config: Initiating hyprctl reload...")
    try:
        exec_shell_command_async("hyprctl reload")
        print(f"{time.time():.4f}: start_config: Hyprland configuration reload initiated.")
    except FileNotFoundError:
         print("Error: hyprctl command not found. Cannot reload Hyprland.")
    except Exception as e:
         print(f"An error occurred initiating hyprctl reload: {e}")
    print(f"{time.time():.4f}: start_config: Finished initiating hyprctl reload.")

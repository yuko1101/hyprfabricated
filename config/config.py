import os
import json
import shutil
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

# Import Pillow for image processing
from PIL import Image
import toml  # Added for TOML handling

# Source string
source_string = """
# Ax-Shell
source = ~/.config/Ax-Shell/config/hypr/ax-shell.conf
"""

# Initialize default values
bind_vars = {
    'prefix_restart': "SUPER ALT",
    'suffix_restart': "B",
    'prefix_axmsg': "SUPER",
    'suffix_axmsg': "A",
    'prefix_dash': "SUPER",
    'suffix_dash': "D",
    'prefix_bluetooth': "SUPER",
    'suffix_bluetooth': "B",
    'prefix_walls': "SUPER",
    'suffix_walls': "COMMA",
    'prefix_launcher': "SUPER",
    'suffix_launcher': "R",
    'prefix_overview': "SUPER",
    'suffix_overview': "TAB",
    'prefix_power': "SUPER",
    'suffix_power': "ESCAPE",
    'prefix_toggle': "SUPER CTRL",
    'suffix_toggle': "B",
    'prefix_css': "SUPER SHIFT",
    'suffix_css': "B",
    'wallpapers_dir': os.path.expanduser("~/.config/Ax-Shell/assets/wallpapers_example")
}

def deep_update(target, update):
    """Recursively update a nested dictionary with values from another."""
    for key, value in update.items():
        if isinstance(value, dict):
            node = target.setdefault(key, {})
            deep_update(node, value)
        else:
            target[key] = value
    return target

def ensure_matugen_config():
    """Ensure the matugen config.toml has the required entries, creating or updating it if necessary."""
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
            }
        },
        'templates': {
            'hyprland': {
                'input_path': '~/.config/Ax-Shell/config/matugen/templates/hyprland-colors.conf',
                'output_path': '~/.config/Ax-Shell/config/hypr/colors.conf'
            },
            'ax-shell': {
                'input_path': '~/.config/Ax-Shell/config/matugen/templates/ax-shell.css',
                'output_path': '~/.config/Ax-Shell/styles/colors.css',
                'post_hook': 'fabric-cli exec ax-shell \'app.set_stylesheet_from_file(get_relative_path("main.css"))\' &'
            }
        }
    }

    config_path = os.path.expanduser('~/.config/matugen/config.toml')
    config_dir = os.path.dirname(config_path)
    os.makedirs(config_dir, exist_ok=True)

    existing_config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            existing_config = toml.load(f)

    # Create backup if existing config is present
    if os.path.exists(config_path):
        shutil.copyfile(config_path, config_path + '.bak')

    # Merge expected configuration into existing (deep update)
    merged_config = deep_update(existing_config, expected_config)

    # Write the merged configuration
    with open(config_path, 'w') as f:
        toml.dump(merged_config, f)

    os.system(f"matugen image {os.path.expanduser('~')}/.config/Ax-Shell/assets/wallpapers_example/example-1.jpg")

def ensure_fonts():
    font_path = os.path.expanduser('~/.fonts/zed-sans-1.2.0/')
    if not os.path.exists(font_path):
        shutil.copytree(os.path.expanduser('~/.config/Ax-Shell/assets/fonts/zed-sans-1.2.0/'), font_path)

def load_bind_vars():
    global bind_vars
    json_config_path = os.path.expanduser('~/.config/Ax-Shell/config/config.json')
    try:
        with open(json_config_path, 'r') as f:
            saved_bind_vars = json.load(f)
            bind_vars.update(saved_bind_vars)
    except FileNotFoundError:
        pass  # No saved config, use defaults

def generate_hyprconf():
    return f"""exec-once = uwsm app -- python ~/.config/Ax-Shell/main.py
exec = pgrep -x "hypridle" > /dev/null || uwsm app -- hypridle
exec = uwsm app -- swww-daemon

$fabricSend = fabric-cli exec ax-shell
$axMessage = notify-send "Axenide" "What are you doing?" -i "{os.path.expanduser('~')}/.config/Ax-Shell/assets/ax.png" -a "Source Code" -A "Be patient. 🍙"

bind = {bind_vars['prefix_restart']}, {bind_vars['suffix_restart']}, exec, killall ax-shell; uwsm app -- python ~/.config/Ax-Shell/main.py # Reload Ax-Shell | Default: SUPER ALT + B

bind = {bind_vars['prefix_axmsg']}, {bind_vars['suffix_axmsg']}, exec, $axMessage # Message | Default: SUPER + A
bind = {bind_vars['prefix_dash']}, {bind_vars['suffix_dash']}, exec, $fabricSend 'notch.open_notch("dashboard")' # Dashboard | Default: SUPER + D
bind = {bind_vars['prefix_bluetooth']}, {bind_vars['suffix_bluetooth']}, exec, $fabricSend 'notch.open_notch("bluetooth")' # Bluetooth | Default: SUPER + B
bind = {bind_vars['prefix_walls']}, {bind_vars['suffix_walls']}, exec, $fabricSend 'notch.open_notch("wallpapers")' # Wallpaper Selector | Default: SUPER + COMMA
bind = {bind_vars['prefix_launcher']}, {bind_vars['suffix_launcher']}, exec, $fabricSend 'notch.open_notch("launcher")' # App Launcher | Default: SUPER + R
bind = {bind_vars['prefix_overview']}, {bind_vars['suffix_overview']}, exec, $fabricSend 'notch.open_notch("overview")' # Overview | Default: SUPER + TAB
bind = {bind_vars['prefix_power']}, {bind_vars['suffix_power']}, exec, $fabricSend 'notch.open_notch("power")' # Power Menu | Default: SUPER + ESCAPE
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'bar.toggle_hidden()' # Toggle Bar | Default: SUPER CTRL + B
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'notch.toggle_hidden()' # Toggle Notch | Default: SUPER CTRL + B
bind = {bind_vars['prefix_css']}, {bind_vars['suffix_css']}, exec, $fabricSend 'app.set_stylesheet_from_file(get_relative_path("main.css"))' # Reload CSS | Default: SUPER SHIFT + B

# Wallpapers directory: {bind_vars['wallpapers_dir']}

source = {os.path.expanduser('~')}/.config/Ax-Shell/config/hypr/colors.conf

general {{
    col.active_border = 0xff$surface_bright
    col.inactive_border = 0xff$surface
    gaps_in = 2
    gaps_out = 4
    border_size = 1
    layout = dwindle
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
    rounding = 15

    shadow {{
      enabled = true
      range = 10
      render_power = 2
      color = rgba(0, 0, 0, 0.25)
    }}
}}

animations {{
    enabled = yes
    bezier = myBezier, .5, .25, 0, 1
    animation = windows, 1, 2.5, myBezier, popin 80%
    animation = border, 1, 2.5, myBezier
    animation = fade, 1, 2.5, myBezier
    animation = workspaces, 1, 2.5, myBezier, slidefade 20%
}}
"""

def ensure_face_icon():
    """
    If ~/.face.icon does not exist, copy the default image from
    ~/.config/Ax-Shell/assets/default.png to ~/.face.icon.
    """
    face_icon_path = os.path.expanduser("~/.face.icon")
    if not os.path.exists(face_icon_path):
        default_face_icon = os.path.expanduser("~/.config/Ax-Shell/assets/default.png")
        if os.path.exists(default_face_icon):
            shutil.copy(default_face_icon, face_icon_path)

class HyprConfGUI(Gtk.Window):
    def __init__(self, show_lock_checkbox, show_idle_checkbox):
        Gtk.Window.__init__(self, title="Configure Key Binds")
        self.set_border_width(20)
        self.set_default_size(500, 450)
        self.set_resizable(False)
        
        self.show_lock_checkbox = show_lock_checkbox
        self.show_idle_checkbox = show_idle_checkbox
        
        vbox = Gtk.VBox(spacing=10)
        self.add(vbox)
        
        # Create input fields for key bindings
        self.entries = []
        bindings = [
            ("Reload Ax-Shell", 'prefix_restart', 'suffix_restart'),
            ("Message", 'prefix_axmsg', 'suffix_axmsg'),
            ("Dashboard", 'prefix_dash', 'suffix_dash'),
            ("Bluetooth", 'prefix_bluetooth', 'suffix_bluetooth'),
            ("Wallpaper Selector", 'prefix_walls', 'suffix_walls'),
            ("App Launcher", 'prefix_launcher', 'suffix_launcher'),
            ("Overview", 'prefix_overview', 'suffix_overview'),
            ("Power Menu", 'prefix_power', 'suffix_power'),
            ("Toggle Bar and Notch", 'prefix_toggle', 'suffix_toggle'),
            ("Reload CSS", 'prefix_css', 'suffix_css'),
        ]
        
        for label_text, prefix_key, suffix_key in bindings:
            hbox = Gtk.HBox(spacing=10)
            lbl = Gtk.Label(label=label_text)
            hbox.pack_start(lbl, False, False, 0)
            
            prefix_entry = Gtk.Entry()
            prefix_entry.set_text(bind_vars[prefix_key])
            hbox.pack_start(prefix_entry, True, True, 0)
            
            hbox.pack_start(Gtk.Label(label=" + "), False, False, 0)
            
            suffix_entry = Gtk.Entry()
            suffix_entry.set_text(bind_vars[suffix_key])
            hbox.pack_start(suffix_entry, True, True, 0)
            
            vbox.pack_start(hbox, False, False, 0)
            self.entries.append((prefix_key, suffix_key, prefix_entry, suffix_entry))
        
        # Add option to select wallpaper directory
        hbox_wall = Gtk.HBox(spacing=10)
        lbl_wall = Gtk.Label(label="Wallpapers Directory")
        hbox_wall.pack_start(lbl_wall, False, False, 0)
        
        self.wall_dir_chooser = Gtk.FileChooserButton(title="Select a folder", action=Gtk.FileChooserAction.SELECT_FOLDER)
        self.wall_dir_chooser.set_filename(bind_vars['wallpapers_dir'])
        hbox_wall.pack_start(self.wall_dir_chooser, True, True, 0)
        vbox.pack_start(hbox_wall, False, False, 0)
        
        # Add a button to select a face icon image
        hbox_face = Gtk.HBox(spacing=10)
        lbl_face = Gtk.Label(label="Profile Icon")
        hbox_face.pack_start(lbl_face, False, False, 0)
        face_btn = Gtk.Button(label="Select Image")
        face_btn.connect("clicked", self.on_select_face_icon)
        hbox_face.pack_start(face_btn, True, True, 0)
        vbox.pack_start(hbox_face, False, False, 0)
        
        # Initialize variable to hold the selected face icon path
        self.selected_face_icon = None

        # --- New: Checkboxes for hyprlock and hypridle config replacement ---
        if self.show_lock_checkbox:
            hbox_lock = Gtk.HBox(spacing=10)
            self.lock_checkbox = Gtk.CheckButton(label="Replace Hyprlock config")
            self.lock_checkbox.set_active(False)
            hbox_lock.pack_start(self.lock_checkbox, False, False, 0)
            vbox.pack_start(hbox_lock, False, False, 0)
        # If the destination file did not exist, no checkbox is shown.
        
        if self.show_idle_checkbox:
            hbox_idle = Gtk.HBox(spacing=10)
            self.idle_checkbox = Gtk.CheckButton(label="Replace Hypridle config")
            self.idle_checkbox.set_active(False)
            hbox_idle.pack_start(self.idle_checkbox, False, False, 0)
            vbox.pack_start(hbox_idle, False, False, 0)
        
        # Buttons for Accept and Cancel
        btn_box = Gtk.HBox(spacing=10)
        accept_btn = Gtk.Button(label="Accept")
        accept_btn.connect("clicked", self.on_accept)
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", self.on_cancel)
        
        btn_box.pack_end(accept_btn, False, False, 0)
        btn_box.pack_end(cancel_btn, False, False, 0)
        vbox.pack_start(btn_box, False, False, 0)

    def on_select_face_icon(self, widget):
        """Open a file chooser to select an image and store its path for later processing."""
        dialog = Gtk.FileChooserDialog(
            title="Select Face Icon",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        
        # Set up a filter for image files
        filter_image = Gtk.FileFilter()
        filter_image.set_name("Image files")
        filter_image.add_mime_type("image/png")
        filter_image.add_mime_type("image/jpeg")
        filter_image.add_pattern("*.png")
        filter_image.add_pattern("*.jpg")
        filter_image.add_pattern("*.jpeg")
        dialog.add_filter(filter_image)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.selected_face_icon = dialog.get_filename()
            print(f"Face icon selected: {self.selected_face_icon}")
        dialog.destroy()

    def on_accept(self, widget):
        for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
            bind_vars[prefix_key] = prefix_entry.get_text()
            bind_vars[suffix_key] = suffix_entry.get_text()
        
        # Update the wallpaper directory path
        bind_vars['wallpapers_dir'] = self.wall_dir_chooser.get_filename()
        
        # Save current bind_vars to JSON
        json_config_path = os.path.expanduser('~/.config/Ax-Shell/config/config.json')
        os.makedirs(os.path.dirname(json_config_path), exist_ok=True)
        with open(json_config_path, 'w') as f:
            json.dump(bind_vars, f)
        
        # Process face icon if selected
        if self.selected_face_icon:
            try:
                img = Image.open(self.selected_face_icon)
                width, height = img.size
                # Determine the side length of the square crop (1:1 aspect ratio)
                side = min(width, height)
                left = (width - side) / 2
                top = (height - side) / 2
                right = left + side
                bottom = top + side
                cropped = img.crop((left, top, right, bottom))
                face_icon_path = os.path.expanduser("~/.face.icon")
                cropped.save(face_icon_path, format='PNG')
                print(f"Face icon saved to {face_icon_path}")
            except Exception as e:
                print("Error processing face icon image:", e)
        
        # Process hyprlock replacement if requested
        dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
        src_lock = os.path.expanduser("~/.config/Ax-Shell/config/hypr/hyprlock.conf")
        if hasattr(self, "lock_checkbox") and self.lock_checkbox.get_active():
            # Create backup
            backup_lock = dest_lock + ".bak"
            shutil.copy(dest_lock, backup_lock)
            print(f"Hyprlock config backed up to {backup_lock}")
            # Replace file
            shutil.copy(src_lock, dest_lock)
            print(f"Hyprlock config replaced from {src_lock}")
        
        # Process hypridle replacement if requested
        dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
        src_idle = os.path.expanduser("~/.config/Ax-Shell/config/hypr/hypridle.conf")
        if hasattr(self, "idle_checkbox") and self.idle_checkbox.get_active():
            # Create backup
            backup_idle = dest_idle + ".bak"
            shutil.copy(dest_idle, backup_idle)
            print(f"Hypridle config backed up to {backup_idle}")
            # Replace file
            shutil.copy(src_idle, dest_idle)
            print(f"Hypridle config replaced from {src_idle}")
        
        hypr_conf_path = os.path.expanduser("~/.config/hypr/hyprland.conf")
        with open(hypr_conf_path, "r") as f:
            contenido = f.read()

        if source_string not in contenido:
            with open(hypr_conf_path, "a") as f:
                f.write(source_string)
        
        start_config()
        self.destroy()

    def on_cancel(self, widget):
        self.destroy()

def start_config():
    ensure_matugen_config()
    ensure_face_icon()
    
    config_dir = os.path.expanduser('~/.config/Ax-Shell/config/hypr/')
    os.makedirs(config_dir, exist_ok=True)
    with open(f"{config_dir}/ax-shell.conf", "w") as f:
        f.write(generate_hyprconf())

    os.system("hyprctl reload")

def open_config():
    ensure_fonts()
    load_bind_vars()  # Load saved bind_vars before creating the GUI

    # --- Check hyprlock and hypridle config files ---
    dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
    src_lock = os.path.expanduser("~/.config/Ax-Shell/config/hypr/hyprlock.conf")
    os.makedirs(os.path.dirname(dest_lock), exist_ok=True)
    if not os.path.exists(dest_lock):
        shutil.copy(src_lock, dest_lock)
        show_lock_checkbox = False
    else:
        show_lock_checkbox = True

    dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
    src_idle = os.path.expanduser("~/.config/Ax-Shell/config/hypr/hypridle.conf")
    if not os.path.exists(dest_idle):
        shutil.copy(src_idle, dest_idle)
        show_idle_checkbox = False
    else:
        show_idle_checkbox = True

    win = HyprConfGUI(show_lock_checkbox, show_idle_checkbox)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    open_config()

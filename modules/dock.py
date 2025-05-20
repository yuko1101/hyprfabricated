import json
import logging

import cairo
from fabric.hyprland.widgets import get_hyprland_connection
from fabric.utils import (exec_shell_command, exec_shell_command_async,
                          get_relative_path, idle_add, remove_handler)
from fabric.utils.helpers import get_desktop_applications
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from fabric.widgets.image import Image
from fabric.widgets.revealer import Revealer  # Importar Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from gi.repository import Gdk, GLib, Gtk

import config.data as data
from modules.corners import MyCorner
from utils.icon_resolver import IconResolver
from utils.occlusion import check_occlusion

OCCLUSION = 36 + data.DOCK_ICON_SIZE

def read_config():
    """Read and return the full configuration from the JSON file, handling missing file."""
    config_path = get_relative_path("../config/dock.json")
    try:
        with open(config_path, "r") as file:
            config_data = json.load(file) # Renombrar variable para evitar conflicto con el módulo 'data'
            
        # Migration: Convert old format (simple string array) to new format (array of objects with full app data)
        if "pinned_apps" in config_data and config_data["pinned_apps"] and isinstance(config_data["pinned_apps"][0], str):
            all_apps = get_desktop_applications()
            app_map = {app.name: app for app in all_apps if app.name}
            
            old_pinned = config_data["pinned_apps"]
            config_data["pinned_apps"] = []
            
            for app_id in old_pinned:
                app = app_map.get(app_id)
                if app:
                    app_data_obj = { # Renombrar variable para evitar conflicto
                        "name": app.name,
                        "display_name": app.display_name,
                        "window_class": app.window_class,
                        "executable": app.executable,
                        "command_line": app.command_line
                    }
                    config_data["pinned_apps"].append(app_data_obj)
                else:
                    config_data["pinned_apps"].append({"name": app_id})
                
    except (FileNotFoundError, json.JSONDecodeError):
        config_data = {"pinned_apps": []}
    return config_data

def createSurfaceFromWidget(widget: Gtk.Widget) -> cairo.ImageSurface:
    alloc = widget.get_allocation()
    surface = cairo.ImageSurface(
        cairo.Format.ARGB32,
        alloc.width,
        alloc.height,
    )
    cr = cairo.Context(surface)
    cr.set_source_rgba(255, 255, 255, 0)
    cr.rectangle(0, 0, alloc.width, alloc.height)
    cr.fill()
    widget.draw(cr)
    return surface

class Dock(Window):
    _instances = []
    
    def __init__(self, **kwargs):
        super().__init__(
            name="dock-window",
            layer="top",
            anchor="bottom" if not data.VERTICAL else "right",
            margin="0px 0px 0px 0px",
            exclusivity="none",
            **kwargs,
        )
        Dock._instances.append(self)
        
        self.config = read_config()
        self.conn = get_hyprland_connection()
        self.icon = IconResolver()
        self.pinned = self.config.get("pinned_apps", [])
        self.config_path = get_relative_path("../config/dock.json")
        self.app_map = {}
        self._all_apps = get_desktop_applications()
        self.app_identifiers = self._build_app_identifiers_map()
        
        self.hide_id = None
        self._arranger_handler = None
        self._drag_in_progress = False
        self.always_occluded = data.DOCK_ALWAYS_OCCLUDED
        self.is_mouse_over_dock_area = False # Reemplaza a is_hovered
        self._prevent_occlusion = False # Para prevenir temporalmente la oclusión

        self.view = Box(name="viewport", orientation="h" if not data.VERTICAL else "v", spacing=4)
        self.wrapper = Box(name="dock", orientation="v", children=[self.view])

        match data.DOCK_THEME:
            case "Pills":
                self.wrapper.add_style_class("pills")
            case "Dense":
                self.wrapper.add_style_class("dense")
            case "Edge":
                self.wrapper.add_style_class("edge")
            case _:
                self.wrapper.add_style_class("pills")

        self.dock_eventbox = EventBox()
        self.dock_eventbox.add(self.wrapper)
        self.dock_eventbox.connect("enter-notify-event", self._on_dock_enter)
        self.dock_eventbox.connect("leave-notify-event", self._on_dock_leave)

        self.corner_left = Box()
        self.corner_right = Box()
        self.corner_top = Box()
        self.corner_bottom = Box()

        if not data.VERTICAL:
            self.corner_left = Box(
                name="dock-corner-left", orientation="v", h_align="start",
                children=[Box(v_expand=True, v_align="fill"), MyCorner("bottom-right")]
            )
            self.corner_right = Box(
                name="dock-corner-right", orientation="v", h_align="end",
                children=[Box(v_expand=True, v_align="fill"), MyCorner("bottom-left")]
            )
            self.dock_full = Box(
                name="dock-full", orientation="h", h_expand=True, h_align="fill",
                children=[self.corner_left, self.dock_eventbox, self.corner_right]
            )
        else:
            self.corner_top = Box(
                name="dock-corner-top", orientation="h", v_align="start",
                children=[Box(h_expand=True, h_align="fill"), MyCorner("bottom-right")]
            )
            self.corner_bottom = Box(
                name="dock-corner-bottom", orientation="h", v_align="end",
                children=[Box(h_expand=True, h_align="fill"), MyCorner("top-right")]
            )
            self.dock_full = Box(
                name="dock-full", orientation="v", v_expand=True, v_align="fill",
                children=[self.corner_top, self.dock_eventbox, self.corner_bottom]
            )

        # Crear el Revealer para el dock
        self.dock_revealer = Revealer(
            name="dock-revealer",
            transition_type="slide-up" if not data.VERTICAL else "slide-left",
            transition_duration=250,
            child_revealed=False, # Empezar oculto
            child=self.dock_full
        )

        self.hover_activator = EventBox()
        self.hover_activator.set_size_request(-1 if not data.VERTICAL else 1, 1 if not data.VERTICAL else -1)
        self.hover_activator.connect("enter-notify-event", self._on_hover_enter)
        self.hover_activator.connect("leave-notify-event", self._on_hover_leave)

        self.main_box = Box(
            orientation="v" if not data.VERTICAL else "h", 
            children=[self.hover_activator, self.dock_revealer],
            h_align="center" if not data.VERTICAL else "end",
        )
        self.add(self.main_box)

        self.view.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new("text/plain", Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.MOVE
        )
        self.view.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [Gtk.TargetEntry.new("text/plain", Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.MOVE
        )
        self.view.connect("drag-data-get", self.on_drag_data_get)
        self.view.connect("drag-data-received", self.on_drag_data_received)
        self.view.connect("drag-begin", self.on_drag_begin)
        self.view.connect("drag-end", self.on_drag_end)

        if self.conn.ready:
            self.update_dock()
            GLib.timeout_add(250, self.check_occlusion_state) # Iniciar chequeo periódico
        else:
            self.conn.connect("event::ready", self.update_dock)
            self.conn.connect("event::ready", lambda *args: GLib.timeout_add(250, self.check_occlusion_state))


        for ev in ("activewindow", "openwindow", "closewindow", "changefloatingmode"):
            self.conn.connect(f"event::{ev}", self.update_dock)
        self.conn.connect("event::workspace", self.check_hide) # check_hide reacciona a cambios de workspace
        
        if data.VERTICAL:
            self.wrapper.add_style_class("vertical")
        else:
            self.wrapper.remove_style_class("vertical")

        GLib.timeout_add_seconds(1, self.check_config_change)

        if data.DOCK_THEME in ["Edge", "Dense"]:
            for corner in [self.corner_left, self.corner_right, self.corner_top, self.corner_bottom]:
                corner.set_visible(False)
        
        if not data.DOCK_ENABLED:
            self.set_visible(False)
            
        if self.always_occluded:
            self.dock_full.add_style_class("occluded")
            
    def _build_app_identifiers_map(self):
        identifiers = {}
        for app in self._all_apps:
            if app.name: identifiers[app.name.lower()] = app
            if app.display_name: identifiers[app.display_name.lower()] = app
            if app.window_class: identifiers[app.window_class.lower()] = app
            if app.executable: identifiers[app.executable.split('/')[-1].lower()] = app
            if app.command_line: identifiers[app.command_line.split()[0].split('/')[-1].lower()] = app
        return identifiers

    def _normalize_window_class(self, class_name):
        if not class_name: return ""
        normalized = class_name.lower()
        suffixes = [".bin", ".exe", ".so", "-bin", "-gtk"]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        return normalized
        
    def _classes_match(self, class1, class2):
        if not class1 or not class2: return False
        norm1 = self._normalize_window_class(class1)
        norm2 = self._normalize_window_class(class2)
        return norm1 == norm2

    def on_drag_begin(self, widget, drag_context):
        self._drag_in_progress = True
        Gtk.drag_set_icon_surface(drag_context, createSurfaceFromWidget(widget))

    def _on_hover_enter(self, *args):
        self.is_mouse_over_dock_area = True
        if self.hide_id:
            GLib.source_remove(self.hide_id)
            self.hide_id = None
        self.dock_revealer.set_reveal_child(True)
        if not self.always_occluded: # Solo quitar si no es always_occluded
            self.dock_full.remove_style_class("occluded")

    def _on_hover_leave(self, *args):
        self.is_mouse_over_dock_area = False
        self.delay_hide()

    def _on_dock_enter(self, widget, event):
        self.is_mouse_over_dock_area = True
        if self.hide_id:
            GLib.source_remove(self.hide_id)
            self.hide_id = None
        self.dock_revealer.set_reveal_child(True)
        if not self.always_occluded: # Solo quitar si no es always_occluded
            self.dock_full.remove_style_class("occluded")
        return True

    def _on_dock_leave(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False

        self.is_mouse_over_dock_area = False
        self.delay_hide()
        
        if self.always_occluded: # Si always_occluded, el estilo vuelve al dejar el hover
            self.dock_full.add_style_class("occluded")
        # La lógica de oclusión principal está en check_occlusion_state
        return True

    def find_app(self, app_identifier):
        if not app_identifier: return None
        if isinstance(app_identifier, dict):
            for key in ["window_class", "executable", "command_line", "name", "display_name"]:
                if key in app_identifier and app_identifier[key]:
                    app = self.find_app_by_key(app_identifier[key])
                    if app: return app
            return None
        return self.find_app_by_key(app_identifier)
    
    def find_app_by_key(self, key_value):
        if not key_value: return None
        normalized_id = str(key_value).lower()
        if normalized_id in self.app_identifiers:
            return self.app_identifiers[normalized_id]
        for app in self._all_apps:
            if app.name and normalized_id in app.name.lower(): return app
            if app.display_name and normalized_id in app.display_name.lower(): return app
            if app.window_class and normalized_id in app.window_class.lower(): return app
            if app.executable and normalized_id in app.executable.lower(): return app
            if app.command_line and normalized_id in app.command_line.lower(): return app
        return None

    def update_app_map(self):
        self._all_apps = get_desktop_applications()
        self.app_map = {app.name: app for app in self._all_apps if app.name}
        self.app_identifiers = self._build_app_identifiers_map()

    def create_button(self, app_identifier, instances):
        desktop_app = self.find_app(app_identifier)
        icon_img = None
        display_name = None
        
        if desktop_app:
            icon_img = desktop_app.get_icon_pixbuf(size=data.DOCK_ICON_SIZE)
            display_name = desktop_app.display_name or desktop_app.name
        
        id_value = app_identifier["name"] if isinstance(app_identifier, dict) else app_identifier
        
        if not icon_img:
            icon_img = self.icon.get_icon_pixbuf(id_value, data.DOCK_ICON_SIZE)
        
        if not icon_img:
            icon_img = self.icon.get_icon_pixbuf("application-x-executable-symbolic", data.DOCK_ICON_SIZE)
            if not icon_img:
                icon_img = self.icon.get_icon_pixbuf("image-missing", data.DOCK_ICON_SIZE)
                
        items = [Image(pixbuf=icon_img)]
        tooltip = display_name or (id_value if isinstance(id_value, str) else "Unknown")
        if not display_name and instances and instances[0].get("title"):
            tooltip = instances[0]["title"]

        button = Button(
            child= Box(name="dock-icon", orientation="v", h_align="center", children=items),
            on_clicked=lambda *a: self.handle_app(app_identifier, instances, desktop_app),
            tooltip_text=tooltip, name="dock-app-button",
        )
        button.app_identifier = app_identifier
        button.desktop_app = desktop_app
        button.instances = instances
        if instances: button.add_style_class("instance")

        button.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new("text/plain", Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.MOVE
        )
        button.connect("drag-begin", self.on_drag_begin)
        button.connect("drag-end", self.on_drag_end)
        button.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [Gtk.TargetEntry.new("text/plain", Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.MOVE
        )
        button.connect("drag-data-get", self.on_drag_data_get)
        button.connect("drag-data-received", self.on_drag_data_received)
        button.connect("enter-notify-event", self._on_child_enter)
        return button

    def handle_app(self, app_identifier, instances, desktop_app=None):
        if not instances:
            if not desktop_app: desktop_app = self.find_app(app_identifier)
            if desktop_app:
                launch_success = desktop_app.launch()
                if not launch_success:
                    if desktop_app.command_line: exec_shell_command_async(f"nohup {desktop_app.command_line}")
                    elif desktop_app.executable: exec_shell_command_async(f"nohup {desktop_app.executable}")
            else:
                if isinstance(app_identifier, dict):
                    if "command_line" in app_identifier and app_identifier["command_line"]: exec_shell_command_async(f"nohup {app_identifier['command_line']}")
                    elif "executable" in app_identifier and app_identifier["executable"]: exec_shell_command_async(f"nohup {app_identifier['executable']}")
                    elif "name" in app_identifier and app_identifier["name"]: exec_shell_command_async(f"nohup {app_identifier['name']}")
                elif isinstance(app_identifier, str): exec_shell_command_async(f"nohup {app_identifier}")
        else:
            focused = self.get_focused()
            idx = next((i for i, inst in enumerate(instances) if inst["address"] == focused), -1)
            next_inst = instances[(idx + 1) % len(instances)]
            exec_shell_command(f"hyprctl dispatch focuswindow address:{next_inst['address']}")

    def _on_child_enter(self, widget, event):
        self.is_mouse_over_dock_area = True # Consider hover over child as hover over dock
        if self.hide_id:
            GLib.source_remove(self.hide_id)
            self.hide_id = None
        return False

    def delay_hide(self):
        if self.hide_id:
            GLib.source_remove(self.hide_id)
        self.hide_id = GLib.timeout_add(250, self.hide_dock_if_not_hovered) # Ajustado

    def hide_dock_if_not_hovered(self):
        self.hide_id = None 
        if not self.is_mouse_over_dock_area and not self._drag_in_progress and not self._prevent_occlusion:
            if self.always_occluded:
                self.dock_revealer.set_reveal_child(False)
            else:
                occlusion_region = ("bottom", OCCLUSION) if not data.VERTICAL else ("right", OCCLUSION)
                if check_occlusion(occlusion_region) or not self.view.get_children():
                    self.dock_revealer.set_reveal_child(False)
        return False

    def check_hide(self, *args):
        """Determina si el dock debe auto-ocultarse basado en el estado de las ventanas."""
        if self.is_mouse_over_dock_area or self._drag_in_progress or self._prevent_occlusion:
            return # El usuario está interactuando, no hacer nada

        clients = self.get_clients()
        current_ws = self.get_workspace()
        ws_clients = [w for w in clients if w["workspace"]["id"] == current_ws]

        if not self.always_occluded:
            if not ws_clients: # No hay ventanas en el workspace
                if not self.dock_revealer.get_reveal_child():
                    self.dock_revealer.set_reveal_child(True)
                self.dock_full.remove_style_class("occluded")
            elif any(not w.get("floating") and not w.get("fullscreen") for w in ws_clients): # Hay ventanas en mosaico
                self.check_occlusion_state() # Forzar reevaluación
            else: # Solo ventanas flotantes o pantalla completa
                if not self.dock_revealer.get_reveal_child():
                    self.dock_revealer.set_reveal_child(True)
                self.dock_full.remove_style_class("occluded")
        else: # Si always_occluded es true y no está en hover
            if self.dock_revealer.get_reveal_child():
                self.dock_revealer.set_reveal_child(False)
            self.dock_full.add_style_class("occluded")

    def update_dock(self, *args):
        self.update_app_map()
        arranger_handler = getattr(self, "_arranger_handler", None)
        if arranger_handler: remove_handler(arranger_handler)
        clients = self.get_clients()
        
        running_windows = {}
        for c in clients:
            window_id = None
            if class_name := c.get("initialClass", "").lower(): window_id = class_name
            elif class_name := c.get("class", "").lower(): window_id = class_name
            elif title := c.get("title", "").lower():
                possible_name = title.split(" - ")[0].strip()
                if possible_name and len(possible_name) > 1: window_id = possible_name
                else: window_id = title
            if not window_id: window_id = "unknown-app"
            logging.debug(f"Window detected: {window_id} (from {c.get('initialClass', '')}/{c.get('class', '')}/{c.get('title', '')})")
            running_windows.setdefault(window_id, []).append(c)
            normalized_id = self._normalize_window_class(window_id)
            if normalized_id != window_id:
                running_windows.setdefault(normalized_id, []).extend(running_windows[window_id])
        
        pinned_buttons = []
        used_window_classes = set()
        
        for app_data_item in self.pinned: # Renombrar variable
            app = self.find_app(app_data_item)
            instances = []
            matched_class = None
            possible_identifiers = []
            
            if isinstance(app_data_item, dict):
                for key in ["window_class", "executable", "command_line", "name", "display_name"]:
                    if key in app_data_item and app_data_item[key]: possible_identifiers.append(app_data_item[key].lower())
            elif isinstance(app_data_item, str): possible_identifiers.append(app_data_item.lower())
            
            if app:
                if app.window_class: possible_identifiers.append(app.window_class.lower())
                if app.executable: possible_identifiers.append(app.executable.split('/')[-1].lower())
                if app.command_line:
                    cmd_parts = app.command_line.split()
                    if cmd_parts: possible_identifiers.append(cmd_parts[0].split('/')[-1].lower())
                if app.name: possible_identifiers.append(app.name.lower())
                if app.display_name: possible_identifiers.append(app.display_name.lower())
            
            possible_identifiers = list(set(possible_identifiers))
            
            for identifier in possible_identifiers:
                if identifier in running_windows:
                    instances = running_windows[identifier]; matched_class = identifier; break
                normalized = self._normalize_window_class(identifier)
                if normalized in running_windows:
                    instances = running_windows[normalized]; matched_class = normalized; break
                for window_class in running_windows:
                    if len(identifier) >= 3 and identifier in window_class:
                        instances = running_windows[window_class]; matched_class = window_class
                        logging.debug(f"Substring match: {identifier} in {window_class}"); break
                if matched_class: break
            
            if matched_class:
                used_window_classes.add(matched_class)
                used_window_classes.add(self._normalize_window_class(matched_class))
                logging.debug(f"Matched pinned app {app_data_item} to running instances via {matched_class}")
            
            pinned_buttons.append(self.create_button(app_data_item, instances))
        
        open_buttons = []
        for class_name, instances in running_windows.items():
            if class_name not in used_window_classes:
                app = None
                app = self.app_identifiers.get(class_name)
                if not app:
                    norm_class = self._normalize_window_class(class_name)
                    app = self.app_identifiers.get(norm_class)
                if not app: app = self.find_app_by_key(class_name)
                if not app and instances and instances[0].get("title"):
                    title = instances[0].get("title", "")
                    potential_name = title.split(" - ")[0].strip()
                    if len(potential_name) > 2: app = self.find_app_by_key(potential_name)
                
                if app:
                    app_data_obj = { # Renombrar variable
                        "name": app.name, "display_name": app.display_name,
                        "window_class": app.window_class, "executable": app.executable,
                        "command_line": app.command_line
                    }
                    identifier = app_data_obj
                else: identifier = class_name
                open_buttons.append(self.create_button(identifier, instances))

        children = pinned_buttons
        if pinned_buttons and open_buttons:
            children += [Box(orientation="v" if not data.VERTICAL else "h", v_expand=False, h_expand=False, h_align="center", v_align="center", name="dock-separator")]
        children += open_buttons
        
        self.view.children = children
        idle_add(self._update_size)
        self._drag_in_progress = False
        self.check_occlusion_state() # Re-check occlusion after updating dock content

    def _update_size(self):
        width, _ = self.view.get_preferred_width()
        self.set_size_request(width, -1)
        return False

    def get_clients(self):
        try: return json.loads(self.conn.send_command("j/clients").reply.decode())
        except json.JSONDecodeError: return []

    def get_focused(self):
        try: return json.loads(self.conn.send_command("j/activewindow").reply.decode()).get("address", "")
        except json.JSONDecodeError: return ""

    def get_workspace(self):
        try: return json.loads(self.conn.send_command("j/activeworkspace").reply.decode()).get("id", 0)
        except json.JSONDecodeError: return 0

    def check_occlusion_state(self):
        """Comprobación periódica de oclusión. Gestiona el revealer y la clase 'occluded'."""
        if self.is_mouse_over_dock_area or self._drag_in_progress or self._prevent_occlusion:
            if not self.dock_revealer.get_reveal_child():
                self.dock_revealer.set_reveal_child(True)
            if not self.always_occluded: # Solo quitar si no es always_occluded y hay hover/interacción
                 self.dock_full.remove_style_class("occluded")
            return True

        if self.always_occluded:
            if self.dock_revealer.get_reveal_child():
                self.dock_revealer.set_reveal_child(False)
            self.dock_full.add_style_class("occluded")
            return True

        occlusion_region = ("bottom", OCCLUSION) if not data.VERTICAL else ("right", OCCLUSION)
        is_occluded_by_window = check_occlusion(occlusion_region)
        is_empty = not self.view.get_children()

        if is_occluded_by_window or is_empty:
            if self.dock_revealer.get_reveal_child():
                self.dock_revealer.set_reveal_child(False)
            self.dock_full.add_style_class("occluded")
        else:
            if not self.dock_revealer.get_reveal_child():
                self.dock_revealer.set_reveal_child(True)
            self.dock_full.remove_style_class("occluded")
        
        return True

    def _find_drag_target(self, widget):
        children = self.view.get_children()
        while widget is not None and widget not in children:
            widget = widget.get_parent() if hasattr(widget, "get_parent") else None
        return widget

    def on_drag_data_get(self, widget, drag_context, data_obj, info, time): # Renombrar data
        target = self._find_drag_target(widget.get_parent() if isinstance(widget, Box) else widget)
        if target is not None:
            index = self.view.get_children().index(target)
            data_obj.set_text(str(index), -1)

    def on_drag_data_received(self, widget, drag_context, x, y, data_obj, info, time): # Renombrar data
        target = self._find_drag_target(widget.get_parent() if isinstance(widget, Box) else widget)
        if target is None: return
        try: source_index = int(data_obj.get_text())
        except (TypeError, ValueError): return

        children = self.view.get_children()
        try: target_index = children.index(target)
        except ValueError: return

        if source_index != target_index:
            separator_index = -1
            for i, child_item in enumerate(children): # Renombrar child
                if child_item.get_name() == "dock-separator":
                    separator_index = i; break
            cross_section_drag = (separator_index != -1 and
                                 ((source_index < separator_index and target_index > separator_index) or
                                  (source_index > separator_index and target_index < separator_index)))
            
            child_item = children.pop(source_index) # Renombrar child
            children.insert(target_index, child_item)
            self.view.children = children
            self.update_pinned_apps(skip_update=not cross_section_drag)
            if cross_section_drag: GLib.idle_add(self.update_dock)

    def on_drag_end(self, widget, drag_context):
        if not self._drag_in_progress: return

        def process_drag_end():
            if self.get_mapped():
                display = Gdk.Display.get_default()
                _, x, y, _ = display.get_pointer()
                window = self.get_window()
                if window:
                    win_x, win_y, width, height = window.get_geometry()
                    if not (win_x <= x <= win_x + width and win_y <= y <= win_y + height):
                        app_id = widget.app_identifier
                        instances = widget.instances
                        app_index = -1
                        for i, pinned_app in enumerate(self.pinned):
                            if pinned_app == app_id: app_index = i; break
                            elif isinstance(pinned_app, dict) and isinstance(app_id, dict):
                                if pinned_app.get("name") == app_id.get("name"): app_index = i; break
                        if app_index >= 0:
                            self.pinned.pop(app_index)
                            self.config["pinned_apps"] = self.pinned
                            self.update_pinned_apps_file()
                            self.update_dock()
                        elif instances:
                            address = instances[0].get("address")
                            if address:
                                exec_shell_command(f"hyprctl dispatch closewindow address:{address}")
                                self.update_dock()
            self._drag_in_progress = False
            self.check_occlusion_state() # Re-check occlusion after drag ends

        GLib.idle_add(process_drag_end)

    def check_config_change(self):
        new_config = read_config()
        if new_config.get("pinned_apps", []) != self.config.get("pinned_apps", []):
            self.config = new_config
            self.pinned = self.config.get("pinned_apps", [])
            self.update_app_map()
            self.update_dock()
        return True

    def update_pinned_apps_file(self):
        config_path = get_relative_path("../config/dock.json")
        try:
            with open(config_path, "w") as file:
                json.dump(self.config, file, indent=4)
            return True
        except Exception as e:
            logging.error(f"Failed to write dock config: {e}")
            return False

    def update_pinned_apps(self, skip_update=False):
        pinned_children = []
        for child_item in self.view.get_children(): # Renombrar child
            if child_item.get_name() == "dock-separator": break
            if hasattr(child_item, "app_identifier"):
                if hasattr(child_item, "desktop_app") and child_item.desktop_app:
                    app = child_item.desktop_app
                    app_data_obj = { # Renombrar variable
                        "name": app.name, "display_name": app.display_name,
                        "window_class": app.window_class, "executable": app.executable,
                        "command_line": app.command_line
                    }
                    pinned_children.append(app_data_obj)
                else:
                    pinned_children.append(child_item.app_identifier)

        self.config["pinned_apps"] = pinned_children
        self.pinned = pinned_children
        file_updated = self.update_pinned_apps_file()
        if file_updated and not skip_update:
            self.update_dock()

    @staticmethod
    def notify_config_change():
        for dock in Dock._instances:
            GLib.idle_add(dock.check_config_change_immediate)
            
    def check_config_change_immediate(self):
        new_config = read_config()
        
        previous_always_occluded = self.always_occluded
        # Asumiendo que data.DOCK_ALWAYS_OCCLUDED se actualiza externamente si cambia en config.data
        self.always_occluded = data.DOCK_ALWAYS_OCCLUDED 
        
        if previous_always_occluded != self.always_occluded:
            # La lógica de visibilidad y estilo 'occluded' ahora se maneja principalmente
            # por check_occlusion_state() y los manejadores de hover.
            # Forzamos una reevaluación.
            self.check_occlusion_state() 
        
        if new_config.get("pinned_apps", []) != self.config.get("pinned_apps", []):
            self.config = new_config
            self.pinned = self.config.get("pinned_apps", [])
            self.update_app_map()
            self.update_dock() # Esto ya llama a check_occlusion_state al final
        return False

    @staticmethod
    def update_visibility(visible):
        for dock in Dock._instances:
            dock.set_visible(visible)
            if visible:
                # Si se hace visible, forzar una comprobación de oclusión para el estado inicial del revealer
                GLib.idle_add(dock.check_occlusion_state)
            else:
                # Si se oculta, asegurar que el revealer también esté oculto
                if dock.dock_revealer.get_reveal_child():
                    dock.dock_revealer.set_reveal_child(False)

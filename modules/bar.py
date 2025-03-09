import json
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.datetime import DateTime
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland.widgets import Workspaces, WorkspaceButton
from fabric.utils.helpers import get_relative_path, exec_shell_command_async
from gi.repository import Gdk
from modules.systemtray import SystemTray
import modules.icons as icons
import modules.data as data
from modules.controls import ControlSmall
from modules.weather import Weather
from modules.metrics import MetricsSmall
from modules.tools import Toolbox

class Bar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="bar",
            layer="top",
            anchor="left top right",
            margin="-8px -4px -8px -4px",
            exclusivity="auto",
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs.get("notch", None)
        config_path = get_relative_path("../config.json")
        with open(config_path) as config_file:
            config = json.load(config_file)

        self.workspaces = Workspaces(
            name="workspaces",
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h",
            spacing=10,
            buttons=[WorkspaceButton(id=i, label="") for i in range(1, 11)],
        )

        self.button_apps = Button(
            name="button-bar",
            on_clicked=lambda *_: self.search_apps(),
            child=Label(
                name="button-bar-label",
                markup=icons.apps
            )
        )
        self.button_apps.connect("enter_notify_event", self.on_button_enter)
        self.button_apps.connect("leave_notify_event", self.on_button_leave)

        left_children = []

        if config["Bar"]["buttonapps"]:
            left_children.append(self.button_apps)
        if config["Bar"]["workspaces"]:
            left_children.append(Box(name="workspaces-container", children=[self.workspaces]))

        start_children = []

        if config["Bar"]["Barleft"]["weather"]:
            self.weather = Weather()
            start_children.append(self.weather)

        if config["Bar"]["Barleft"]["overview"]:
            self.button_overview = Button(
                name="button-bar",
                on_clicked=lambda *_: self.overview(),
                child=Label(
                    name="button-bar-label",
                    markup=icons.windows
                )
            )
            self.button_overview.connect("enter_notify_event", self.on_button_enter)
            self.button_overview.connect("leave_notify_event", self.on_button_leave)
            start_children.append(self.button_overview)

        self.revealer_left = Revealer(
            name="bar-revealer",
            transition_type="slide-right",
            child_revealed=True,
            child=Box(
                name="bar-revealer-box",
                orientation="h",
                spacing=4,
                children=start_children,
            ),
        )

        self.boxed_revealer_left = Box(
            name="boxed-revealer",
            children=[
                self.revealer_left,
            ],
        )

        end_children = []

        if config["Bar"]["Barright"]["metrics"]:
            self.metrics = MetricsSmall()
            end_children.append(self.metrics)

        if config["Bar"]["Barright"]["controls"]:
            self.control = ControlSmall()
            end_children.append(self.control)

        self.revealer_right = Revealer(
            name="bar-revealer",
            transition_type="slide-left",
            child_revealed=True,
            child=Box(
                name="bar-revealer-box",
                orientation="h",
                spacing=4,
                children=end_children,
            ),
        )

        self.boxed_revealer_right = Box(
            name="boxed-revealer",
            children=[
                self.revealer_right,
            ],
        )

        end_children = [self.boxed_revealer_right]

        if config["Bar"]["systray"]:
            self.systray = SystemTray()
            end_children.append(self.systray)

        if config["Bar"]["buttontools"]:
            self.button_tools = Button(
                name="button-bar",
                tooltip_text="Opens Toolbox",
                on_clicked=lambda *_: self.tools_menu(),
                child=Label(
                    name="button-bar-label",
                    markup=icons.toolbox
                )
            )
            self.button_tools.connect("enter_notify_event", self.on_button_enter)
            self.button_tools.connect("leave_notify_event", self.on_button_leave)
            end_children.append(self.button_tools)

        if config["Bar"]["datetime"]:
            self.date_time = DateTime(name="date-time", formatters=["%I:%M %P"], h_align="center", v_align="center")
            end_children.append(self.date_time)

        if config["Bar"]["buttonpower"]:
            self.button_power = Button(
                name="button-bar",
                on_clicked=lambda *_: self.power_menu(),
                child=Label(
                    name="button-bar-label",
                    markup=icons.shutdown
                )
            )
            self.button_power.connect("enter_notify_event", self.on_button_enter)
            self.button_power.connect("leave_notify_event", self.on_button_leave)
            end_children.append(self.button_power)

        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation="h",
            h_align="fill",
            v_align="center",
            start_children=Box(
                name="start-container",
                spacing=4,
                orientation="h",
                children=left_children + [self.boxed_revealer_left],
            ),
            end_children=Box(
                name="end-container",
                spacing=4,
                orientation="h",
                children=end_children,
            ),
        )

        self.children = self.bar_inner

        self.hidden = False

        self.show_all()

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def on_button_clicked(self, *args):
        exec_shell_command_async("notify-send 'Botón presionado' '¡Funciona!'")

    def search_apps(self):
        self.notch.open_notch("launcher")

    def overview(self):
        self.notch.open_notch("overview")

    def power_menu(self):
        self.notch.open_notch("power")

    def tools_menu(self):
        self.notch.open_notch("tools")

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.bar_inner.add_style_class("hidden")
        else:
            self.bar_inner.remove_style_class("hidden")


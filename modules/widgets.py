import gi

gi.require_version('Gtk', '3.0')
from fabric.widgets.box import Box
from fabric.widgets.stack import Stack
from fabric.widgets.label import Label # <--- Añadida esta importación

from modules.bluetooth import BluetoothConnections
from modules.buttons import Buttons
from modules.calendar import Calendar
from modules.controls import ControlSliders
from modules.metrics import Metrics
from modules.player import Player


class Widgets(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="dash-widgets",
            h_align="fill",
            v_align="fill",
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs["notch"]

        self.buttons = Buttons(widgets=self)
        self.bluetooth = BluetoothConnections(widgets=self) # Esta es la página de Bluetooth

        self.box_1 = Box(
            name="box-1",
            h_expand=True,
            v_expand=True,
        )

        self.box_2 = Box(
            name="box-2",
            h_expand=True,
            v_expand=True,
        )

        self.box_3 = Box(
            name="box-3",
            v_expand=True,
        )

        self.controls = ControlSliders()

        self.player = Player()

        self.metrics = Metrics()

        self.notification_history = self.notch.notification_history # Esta es la página de historial de notificaciones

        # Crear la nueva página "Coming soon" para la red
        self.network_placeholder_page = Label( # <--- Añadidas estas líneas
            label="Network Details: Coming soon.",
            name="network-applet-placeholder-label",
            h_align="center",
            v_align="center",
            h_expand=True,
            v_expand=True,
        )

        self.applet_stack = Stack(
            h_expand=True,
            v_expand=True,
            transition_type="slide-left-right",
            children=[
                self.notification_history,
                self.bluetooth,
                self.network_placeholder_page, # <--- Añadida la nueva página aquí
            ]
        )

        self.applet_stack_box = Box(
            name="applet-stack",
            h_expand=True,
            v_expand=True,
            h_align="fill",
            children=[
                self.applet_stack,
            ]
        )

        self.container_1 = Box(
            name="container-1",
            h_expand=True,
            v_expand=True,
            orientation="h",
            spacing=8,
            children=[
                Box(
                    name="container-sub-1",
                    h_expand=True,
                    v_expand=True,
                    spacing=8,
                    children=[
                        Calendar(),
                        self.applet_stack_box,
                    ]
                ),
                self.metrics,
            ]
        )

        self.container_2 = Box(
            name="container-2",
            h_expand=True,
            v_expand=True,
            orientation="v",
            spacing=8,
            children=[
                self.buttons,
                self.controls,
                self.container_1,
            ]
        )

        self.container_3 = Box(
            name="container-3",
            h_expand=True,
            v_expand=True,
            orientation="h",
            spacing=8,
            children=[
                self.player,
                self.container_2,
            ]
        )

        self.add(self.container_3)

    def show_bt(self):
        self.applet_stack.set_visible_child(self.bluetooth)

    def show_notif(self):
        self.applet_stack.set_visible_child(self.notification_history)

    def show_network_applet(self): # <--- Añadido este nuevo método
        # Primero, asegúrate de que el dashboard esté visible y en la sección de widgets
        self.notch.open_notch("network_applet")
        # La lógica en open_notch("network_applet") se encargará de mostrar
        # self.network_placeholder_page dentro del applet_stack.

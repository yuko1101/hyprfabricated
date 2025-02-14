from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.overlay import Overlay
from fabric.widgets.stack import Stack
from fabric.utils.helpers import exec_shell_command_async
from widgets.circle_image import CircleImage
import modules.icons as icons
import modules.data as data

from gi.repository import Gtk, GLib


class PlayerBox(Box):
    def __init__(self):
        super().__init__(orientation="v", h_align="fill", spacing=0, h_expand=False, v_expand=True)

        self.cover = CircleImage(name="player-cover", image_file=f"{data.HOME_DIR}/.config/Ax-Shell/assets/ax.png", size=162, h_align="center", v_align="center")
        self.cover_placerholder = CircleImage(name="player-cover", size=198, h_align="center", v_align="center")
        self.title = Label(name="player-title")
        self.album = Label(name="player-album")
        self.artist = Label(name="player-artist")
        self.progressbar = CircularProgressBar(name="player-progress", size=198, h_align="center", v_align="center", angle=270, gap_size=180)

        self.overlay = Overlay(
            child=self.cover_placerholder,
            overlays=[self.progressbar, self.cover],
        )

        self.overlay_container = CenterBox(name="player-overlay", center_children=[self.overlay])

        self.title.set_text("Nostalgia (VIP Mix)")
        self.album.set_text("Origins EP")
        self.artist.set_text("Axenide")
        self.progressbar.set_value(0.5)

        self.prev = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.prev),
        )

        self.backward = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.rewind_backward_5),
        )

        self.play_pause = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.play),
        )

        self.forward = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.rewind_forward_5),
        )

        self.next = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.next),
        )

        self.btn_box = CenterBox(
            name="player-btn-box",
            orientation="h",
            center_children=[
                Box(
                    orientation="h",
                    spacing=8,
                    h_expand=True,
                    h_align="fill",
                    children=[
                        self.prev,
                        self.backward,
                        self.play_pause,
                        self.forward,
                        self.next,
                    ]
                )
            ]
        )

        self.time = Label(name="player-time", label="2:32 / 5:04")

        self.player_box = Box(
            name="player-box",
            orientation="v",
            spacing=4,
            children=[
                self.overlay_container,
                self.title,
                self.album,
                self.artist,
                self.btn_box,
                self.time,
            ]
        )

        # Agregamos el contenedor principal al PlayerBox para que se renderice
        self.add(self.player_box)


class Player(Box):
    def __init__(self):
        super().__init__(name="player", orientation="v", h_align="fill",
                         spacing=0, h_expand=False, v_expand=True)

        self.player_stack = Stack(
            name="player-stack",
            transition_type="slide-left-right",
            transition_duration=500,
        )

        self.switcher = Gtk.StackSwitcher(
            name="player-switcher",
            spacing=8,
        )

        # Widgets personalizados en lugar de los labels por defecto.
        self.custom_labels = [
            Label(name="player-label", markup=icons.firefox),
            Label(name="player-label", markup=icons.spotify),
            Label(name="player-label", markup=icons.chromium),
        ]

        self.switcher.set_stack(self.player_stack)

        # Agregamos las páginas al stack.
        self.player_stack.add_titled(PlayerBox(), "1", "Firefox")
        self.player_stack.add_titled(PlayerBox(), "2", "Spotify")
        self.player_stack.add_titled(PlayerBox(), "3", "Chromium")
        
        self.switcher.set_hexpand(True)
        self.switcher.set_vexpand(True)
        self.switcher.set_valign(Gtk.Align.END)
        self.switcher.set_homogeneous(True)

        self.add(self.player_stack)
        self.add(self.switcher)

        # Esperar al siguiente ciclo del loop para modificar los botones
        GLib.idle_add(self._replace_switcher_labels)

    def _replace_switcher_labels(self):
        """ Reemplaza los labels internos de los botones del StackSwitcher """
        # Los botones son hijos directos del StackSwitcher.
        buttons = self.switcher.get_children()

        for i, btn in enumerate(buttons):
            if isinstance(btn, Gtk.ToggleButton):  # StackSwitcher usa ToggleButtons
                default_label = None
                
                # Buscar el Gtk.Label dentro del botón
                for child in btn.get_children():
                    if isinstance(child, Gtk.Label):
                        default_label = child
                        break

                if default_label and i < len(self.custom_labels):
                    btn.remove(default_label)  # Eliminar el label original
                    btn.add(self.custom_labels[i])  # Agregar el custom
                    self.custom_labels[i].show_all()  # Asegurar que sea visible

        return False  # Detener la ejecución del idle_add

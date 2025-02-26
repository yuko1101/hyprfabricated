from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.overlay import Overlay
from fabric.widgets.eventbox import EventBox
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.scale import Scale
from fabric.audio.service import Audio
import modules.icons as icons

class VolumeSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-vol", **kwargs)
        self.audio = Audio()

        self.progress_bar = CircularProgressBar(
            name="button-volume", size=28, line_width=2,
            start_angle=135, end_angle=395,
        )
        self.vol_label = Label(name="vol-label", markup=icons.vol_high)

        self.vol_button = Button(
            on_clicked=self.toggle_mute,
            child=self.vol_label
        )
        self.event_box = EventBox(
            events="scroll",
            child=Overlay(
                child=self.progress_bar,
                overlays=self.vol_button
            ),
        )

        # Conectar cuando se actualice el speaker para volver a conectar la señal "changed"
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)

        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)

        # Actualizar el estado inicial
        self.on_speaker_changed()

    def on_new_speaker(self, *args):
        if self.audio.speaker:
            # Conectarse a la señal "changed" del stream para recibir cambios de volumen
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()

    def toggle_mute(self, event):
        current_stream = self.audio.speaker
        if current_stream:
            current_stream.muted = not current_stream.muted
            if current_stream.muted:
                self.vol_button.get_child().set_markup(icons.vol_off)
                self.progress_bar.add_style_class("muted")
                self.vol_label.add_style_class("muted")
            else:
                self.on_speaker_changed()
                self.progress_bar.remove_style_class("muted")
                self.vol_label.remove_style_class("muted")

    def on_scroll(self, _, event):
        match event.direction:
            case 0:
                self.audio.speaker.volume += 1
            case 1:
                self.audio.speaker.volume -= 1
        # La actualización del ícono se realizará en on_speaker_changed, al emitirse la señal "changed".
        return

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return

        # Actualiza el estado de mute
        if self.audio.speaker.muted:
            self.vol_button.get_child().set_markup(icons.vol_off)
            self.progress_bar.add_style_class("muted")
            self.vol_label.add_style_class("muted")
            return
        else:
            self.progress_bar.remove_style_class("muted")
            self.vol_label.remove_style_class("muted")

        # Actualizar la CircularProgressBar
        self.progress_bar.value = self.audio.speaker.volume / 100

        # Actualizar el ícono según el nivel de volumen
        if self.audio.speaker.volume >= 75:
            self.vol_button.get_child().set_markup(icons.vol_high)
        elif self.audio.speaker.volume >= 1:
            self.vol_button.get_child().set_markup(icons.vol_medium)
        else:
            self.vol_button.get_child().set_markup(icons.vol_mute)


class VolumeSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="volume-slider",
            orientation="h",
            h_expand=True,
            value=1,
            has_origin=True,
            **kwargs,
        )

        self.vol_icon = Label(name="vol-icon", markup=icons.vol_high)

        self.audio = Audio()
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)

        self.connect("value-changed", self.on_value_changed)

        # Actualizar el estado inicial
        self.on_speaker_changed()

    def on_new_speaker(self, *args):
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()

    def on_value_changed(self, _):
        self.audio.speaker.volume = self.value * 100

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return

        # Actualizar el valor del slider. (Aseguramos que el valor se encuentre entre 0 y 1)
        self.value = self.audio.speaker.volume / 100
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
from fabric.audio.service import Audio
from fabric.widgets.button import Button
from fabric.widgets.overlay import Overlay
from fabric.widgets.eventbox import EventBox
from fabric.widgets.circularprogressbar import CircularProgressBar
import modules.icons as icons

class MicSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            value=1,
            has_origin=True,
            **kwargs,
        )

        #self.mic_icon = Label(name="mic-icon", markup=icons.mic)

        self.audio = Audio()
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)

        self.connect("value-changed", self.on_value_changed)

        # Actualizar el estado inicial
        self.add_style_class("mic")
        self.on_microphone_changed()

    def on_new_microphone(self, *args):
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
            self.on_microphone_changed()

    def on_value_changed(self, _):
        if self.audio.microphone:
            self.audio.microphone.volume = self.value * 100

    def on_microphone_changed(self, *_):
        if not self.audio.microphone:
            return

        # Actualizar el valor del slider. (Aseguramos que el valor se encuentre entre 0 y 1)
        self.value = self.audio.microphone.volume / 100

class VolumeSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            value=1,
            has_origin=True,
            **kwargs,
        )

        #self.vol_icon = Label(name="vol-icon", markup=icons.vol_high)

        self.audio = Audio()
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)

        self.connect("value-changed", self.on_value_changed)

        # Actualizar el estado inicial
        self.add_style_class("vol")
        self.on_speaker_changed()

    def on_new_speaker(self, *args):
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()

    def on_value_changed(self, _):
        if self.audio.speaker:
            self.audio.speaker.volume = self.value * 100

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return

        # Actualizar el valor del slider. (Aseguramos que el valor se encuentre entre 0 y 1)
        self.value = self.audio.speaker.volume / 100


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


class MicSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-mic", **kwargs)
        self.audio = Audio()

        self.progress_bar = CircularProgressBar(
            name="button-mic", size=28, line_width=2,
            start_angle=135, end_angle=395,
        )
        self.mic_label = Label(name="mic-label", markup=icons.mic)

        self.mic_button = Button(
            on_clicked=self.toggle_mute,
            child=self.mic_label
        )
        self.event_box = EventBox(
            events="scroll",
            child=Overlay(
                child=self.progress_bar,
                overlays=self.mic_button
            ),
        )

        # Conectar cuando se actualice el microphone para volver a conectar la señal "changed"
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)

        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)

        # Actualizar el estado inicial
        self.on_microphone_changed()

    def on_new_microphone(self, *args):
        if self.audio.microphone:
            # Conectarse a la señal "changed" del stream para recibir cambios de volumen
            self.audio.microphone.connect("changed", self.on_microphone_changed)
            self.on_microphone_changed()

    def toggle_mute(self, event):
        current_stream = self.audio.microphone
        if current_stream:
            current_stream.muted = not current_stream.muted
            if current_stream.muted:
                self.mic_button.get_child().set_markup(icons.mic_mute)
                self.progress_bar.add_style_class("muted")
                self.mic_label.add_style_class("muted")
            else:
                self.on_microphone_changed()
                self.progress_bar.remove_style_class("muted")
                self.mic_label.remove_style_class("muted")

    def on_scroll(self, _, event):
        if not self.audio.microphone:
            return
        match event.direction:
            case 0:
                self.audio.microphone.volume += 1
            case 1:
                self.audio.microphone.volume -= 1
        # La actualización del ícono se realizará en on_microphone_changed, al emitirse la señal "changed".
        return

    def on_microphone_changed(self, *_):
        if not self.audio.microphone:
            return

        # Actualiza el estado de mute
        if self.audio.microphone.muted:
            self.mic_button.get_child().set_markup(icons.mic_off)
            self.progress_bar.add_style_class("muted")
            self.mic_label.add_style_class("muted")
            return
        else:
            self.progress_bar.remove_style_class("muted")
            self.mic_label.remove_style_class("muted")

        # Actualizar la CircularProgressBar
        self.progress_bar.value = self.audio.microphone.volume / 100

        # Actualizar el ícono según el nivel de volumen
        if self.audio.microphone.volume >= 1:
            self.mic_button.get_child().set_markup(icons.mic)
        else:
            self.mic_button.get_child().set_markup(icons.mic_mute)


class ControlSliders(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-sliders",
            orientation="h",
            spacing=4,
            children=[
                VolumeSlider(),
                MicSlider(),
            ],
            **kwargs,
        )

        self.show_all()


class ControlSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-small",
            orientation="h",
            spacing=4,
            children=[
                VolumeSmall(),
                MicSmall(),
            ],
            **kwargs,
        )

        self.show_all()
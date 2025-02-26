from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.overlay import Overlay
from fabric.widgets.eventbox import EventBox
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.audio.service import Audio
import modules.icons as icons

class VolumeSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-vol", **kwargs)
        self.audio = Audio()

        self.progress_bar = CircularProgressBar(
            name="button-volume", size=28, line_width=3,
            start_angle=270, end_angle=630,
        )
        self.ico = icons.vol_high
        self.vol_label = Label(name="vol-label", markup=icons.vol_high)

        self.vol_button = Button(
            on_clicked=self.toggle_mute,
            child=self.vol_label
        )
        self.event_box = EventBox(
            #            name="button-bar-vol",
            events="scroll",
            child=Overlay(
                child=self.progress_bar,
                overlays=self.vol_button
            ),
        )

        self.audio.connect("notify::speaker", self.on_speaker_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)

        # Check and update initial mute/volume state
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
                # Update display based on volume on unmute
                self.on_speaker_changed()
                self.progress_bar.remove_style_class("muted")
                self.vol_label.remove_style_class("muted")

    def on_scroll(self, _, event):
        match event.direction:
            case 0:
                self.audio.speaker.volume += 1
            case 1:
                self.audio.speaker.volume -= 1
        if self.audio.speaker.volume >= 75:
            self.vol_button.get_child().set_markup(icons.vol_high)
        elif self.audio.speaker.volume >= 1:
            self.vol_button.get_child().set_markup(icons.vol_medium)
        elif self.audio.speaker.volume < 1:
            self.vol_button.get_child().set_markup(icons.vol_mute)
        return

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return

        # Handle muted state first
        if self.audio.speaker.muted:
            self.vol_button.get_child().set_markup(icons.vol_off)
            self.progress_bar.add_style_class("muted")
            self.vol_label.add_style_class("muted")
            return
        else:
            self.progress_bar.remove_style_class("muted")
            self.vol_label.remove_style_class("muted")

        self.progress_bar.value = self.audio.speaker.volume / 100
        self.audio.speaker.bind(
            "volume", "value", self.progress_bar, lambda _, v: v / 100
        )
        if self.audio.speaker.volume >= 75:
            self.vol_button.get_child().set_markup(icons.vol_high)
        elif self.audio.speaker.volume >= 1:
            self.vol_button.get_child().set_markup(icons.vol_medium)
        elif self.audio.speaker.volume < 1:
            self.vol_button.get_child().set_markup(icons.vol_mute)
        return

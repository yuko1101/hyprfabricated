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
            name="button-volume", pie=False, size=28, line_width=2,
        )
        self.ico = icons.vol_high
        self.vollabel = Label(name="button-bar-label", markup=icons.vol_high)

        self.volbutton = Button(
                on_clicked=self.toggle_mute,
                child=self.vollabel
        )
        self.event_box = EventBox(
#            name="button-bar-vol",
            events="scroll",
            child=Overlay(
                child=self.progress_bar,
                overlays=self.volbutton
            ),
        )

        self.audio.connect("notify::speaker", self.on_speaker_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)

    #        self.button.connect("button", self.on_clicked)

    #thanks https://github.com/rubiin/HyDePanel/blob/master/widgets/volume.python.py

    def toggle_mute(self, event):
        current_stream = self.audio.speaker
        if current_stream:
            current_stream.muted = not current_stream.muted
            self.volbutton.get_child().set_markup(icons.vol_off) if current_stream.muted else self.on_speaker_changed()
    
    #def Mute():
    #self.audio.speaker += 2,

    def on_scroll(self, _, event):
        match event.direction:
            case 0:
                self.audio.speaker.volume += 2
            case 1:
                self.audio.speaker.volume -= 2
        if self.audio.speaker.volume > 60:
            self.volbutton.get_child().set_markup(icons.vol_high)
        elif self.audio.speaker.volume > 30:
            self.volbutton.get_child().set_markup(icons.vol_medium)
        elif self.audio.speaker.volume < 30:
            self.volbutton.get_child().set_markup(icons.vol_mute)


        return

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return
        self.progress_bar.value = self.audio.speaker.volume / 100
        self.audio.speaker.bind(
            "volume", "value", self.progress_bar, lambda _, v: v / 100
        )
        if self.audio.speaker.volume > 60:
            self.volbutton.get_child().set_markup(icons.vol_high)
        elif self.audio.speaker.volume > 30:
            self.volbutton.get_child().set_markup(icons.vol_medium)
        elif self.audio.speaker.volume < 30:
            self.volbutton.get_child().set_markup(icons.vol_mute)
        return

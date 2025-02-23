from fabric.widgets.overlay import Overlay
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from gi.repository import Gdk
from fabric.widgets.eventbox import EventBox
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.audio.service import Audio
import modules.icons as icons

class VolumeWidget(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-vol", **kwargs)
        self.audio = Audio()

        self.progress_bar = CircularProgressBar(
            name="button-volume", pie=False, size=30, line_width=3,
        )

        self.volume_label = Label(
            name="button-bar-label",
            markup=icons.vol_high,
        )

        self.event_box = EventBox(
#            name="button-bar-vol",
            events=["scroll", "smooth-scroll", "button-press"],
            child=Overlay(
                child=self.progress_bar,
                overlays=self.volume_label,
            ),
        )

        self.audio.connect("notify::speaker", self.on_speaker_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.event_box.connect("button-press-event", self.on_button_press)
        self.add(self.event_box)

    def on_scroll(self, _, event):
        
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if abs(event.delta_y) > 0:
                self.audio.speaker.volume += event.delta_y
            if abs(event.delta_x) > 0:
                self.audio.speaker.volume -= event.delta_x

            

        match event.direction:
            case 0:
                self.audio.speaker.volume += 2
            case 1:
                self.audio.speaker.volume -= 2
            

        self.update_label()
        return
    
    def on_button_press(self, *_):
        
        if self.audio.speaker.volume == 0:
            self.audio.speaker.volume = 50
        else:
            self.audio.speaker.volume = 0
        self.update_label()
        return


    def on_speaker_changed(self, *_):
        print("Nombre del icono de volumen: " + self.audio.speaker.icon_name)
        if not self.audio.speaker:
            return
        self.progress_bar.value = self.audio.speaker.volume / 100
        self.audio.speaker.bind(
            "volume", "value", self.progress_bar, lambda _, v: v / 100
        )
        self.update_label()
        return
    
    def update_label(self):
        if self.audio.speaker.icon_name != "audio-headset-bluetooth":
            if self.audio.speaker.muted:
                self.volume_label.markup = icons.vol_off
            if self.audio.speaker.volume > 65:
                self.volume_label.set_markup(icons.vol_high)
            elif self.audio.speaker.volume > 15:
                self.volume_label.set_markup(icons.vol_medium)
            elif self.audio.speaker.volume < 10:
                self.volume_label.set_markup(icons.vol_mute)
        else:
            if self.audio.speaker.volume == 0:
                self.volume_label.set_markup(icons.bluetooth_disconnected)
            else:
                self.volume_label.set_markup(icons.bluetooth_connected)
        return

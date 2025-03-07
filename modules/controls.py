import subprocess
import threading
import queue
import time
from gi.repository import GLib, Gdk, Gtk
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
from fabric.audio.service import Audio
from fabric.widgets.button import Button
from fabric.widgets.overlay import Overlay
from fabric.widgets.eventbox import EventBox
from fabric.widgets.circularprogressbar import CircularProgressBar
from services.brightness import Brightness
import modules.icons as icons
import math

def supports_backlight():
    try:
        output = subprocess.check_output(["brightnessctl", "-l"]).decode("utf-8").lower()
        return "backlight" in output
    except Exception:
        return False

BACKLIGHT_SUPPORTED = supports_backlight()

# Clase auxiliar para manejar cambios de brillo en un hilo
class BrightnessWorker:
    def __init__(self, brightness):
        self.brightness = brightness
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while True:
            value = self.queue.get()
            if value is None:  # Valor centinela para detener el hilo
                break
            try:
                self.brightness.screen_brightness = value  # Llamada que puede bloquear
            except Exception as e:
                print(f"Error setting brightness: {e}")
            self.queue.task_done()

    def set_brightness(self, value):
        self.queue.put(value)

    def stop(self):
        self.queue.put(None)
        self.thread.join()

# Resto de widgets (VolumeSlider, MicSlider, etc.) se mantienen igual...
class VolumeSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = Audio()
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
        self.connect("value-changed", self.on_value_changed)
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
        self.value = self.audio.speaker.volume / 100

class MicSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = Audio()
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
        self.connect("value-changed", self.on_value_changed)
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
        self.value = self.audio.microphone.volume / 100

# Versión mejorada del slider de brillo usando BrightnessWorker y debounce
class BrightnessSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        if not BACKLIGHT_SUPPORTED:
            return

        self.brightness = Brightness.get_initial()
        self.brightness.connect("screen", self.on_brightness_changed)
        self.connect("value-changed", self.on_value_changed)
        self.on_brightness_changed()
        self.add_style_class("brightness")

        self.timeout_id = None
        self.pending_value = None
        self.worker = BrightnessWorker(self.brightness)

    def on_value_changed(self, _):
        if self.brightness.max_screen != -1:
            new_brightness = int(self.value * self.brightness.max_screen)
            if self.timeout_id:
                try:
                    GLib.source_remove(self.timeout_id)
                except Exception:
                    pass
            self.pending_value = new_brightness
            self.timeout_id = GLib.timeout_add(100, self._queue_brightness_update)

    def _queue_brightness_update(self):
        if self.pending_value is not None:
            self.worker.set_brightness(self.pending_value)
            self.pending_value = None
        self.timeout_id = None
        return False

    def on_brightness_changed(self, *args):
        if self.brightness.max_screen != -1:
            self.value = self.brightness.screen_brightness / self.brightness.max_screen

    def destroy(self):
        self.worker.stop()
        super().destroy()

# Versión mejorada del widget pequeño de brillo
class BrightnessSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-brightness", **kwargs)
        if not BACKLIGHT_SUPPORTED:
            return

        self.brightness = Brightness.get_initial()
        self.progress_bar = CircularProgressBar(
            name="button-brightness", size=28, line_width=2,
            start_angle=150, end_angle=390,
        )
        self.brightness_label = Label(name="brightness-label", markup=icons.brightness_high)
        self.brightness_button = Button(child=self.brightness_label)
        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=Overlay(
                child=self.progress_bar,
                overlays=self.brightness_button
            ),
        )
        self.brightness.connect("screen", self.on_brightness_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)
        self.on_brightness_changed()
        self.add_events(
            Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK
        )

        self.worker = BrightnessWorker(self.brightness)
        # Variables para debouncing del scroll
        self.pending_delta = 0
        self.scroll_timeout_id = None

    def on_scroll(self, _, event):
        if self.brightness.max_screen == -1:
            return

        # Acumulamos la variación: delta_y negativo = subir brillo, positivo = bajar brillo.
        if event.delta_y < 0:
            self.pending_delta += 1
        elif event.delta_y > 0:
            self.pending_delta -= 1

        # Si no hay un timeout en curso, lo configuramos para aplicar el cambio en 100ms.
        if self.scroll_timeout_id is None:
            self.scroll_timeout_id = GLib.timeout_add(100, self._apply_scroll_delta)

    def _apply_scroll_delta(self):
        # Calculamos el nuevo valor a partir del brillo actual y la variación acumulada.
        new_val = self.brightness.screen_brightness + self.pending_delta
        self.worker.set_brightness(new_val)
        self.pending_delta = 0
        self.scroll_timeout_id = None
        return False

    def on_brightness_changed(self, *_):
        if self.brightness.max_screen == -1:
            return
        self.progress_bar.value = self.brightness.screen_brightness / self.brightness.max_screen
        brightness_percentage = (self.brightness.screen_brightness / self.brightness.max_screen) * 100
        if brightness_percentage > 74:
            self.brightness_label.set_markup(icons.brightness_high)
        elif brightness_percentage > 24:
            self.brightness_label.set_markup(icons.brightness_medium)
        else:
            self.brightness_label.set_markup(icons.brightness_low)
        self.set_tooltip_text(f"{round(brightness_percentage)}%")

    def destroy(self):
        self.worker.stop()
        super().destroy()

# Los demás widgets se mantienen igual...
class VolumeSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-vol", **kwargs)
        self.audio = Audio()
        self.progress_bar = CircularProgressBar(
            name="button-volume", size=28, line_width=2,
            start_angle=150, end_angle=390,
        )
        self.vol_label = Label(name="vol-label", markup=icons.vol_high)
        self.vol_button = Button(on_clicked=self.toggle_mute, child=self.vol_label)
        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=Overlay(child=self.progress_bar, overlays=self.vol_button),
        )
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)
        self.on_speaker_changed()
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)

    def on_new_speaker(self, *args):
        if self.audio.speaker:
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
        if not self.audio.speaker:
            return
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if abs(event.delta_y) > 0:
                self.audio.speaker.volume -= event.delta_y
            if abs(event.delta_x) > 0:
                self.audio.speaker.volume += event.delta_x

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return
        if self.audio.speaker.muted:
            self.vol_button.get_child().set_markup(icons.vol_off)
            self.progress_bar.add_style_class("muted")
            self.vol_label.add_style_class("muted")
            self.set_tooltip_text("0%")
            return
        else:
            self.progress_bar.remove_style_class("muted")
            self.vol_label.remove_style_class("muted")
        self.set_tooltip_text(f"{round(self.audio.speaker.volume)}%")
        self.progress_bar.value = self.audio.speaker.volume / 100
        if self.audio.speaker.volume > 74:
            self.vol_button.get_child().set_markup(icons.vol_high)
        elif self.audio.speaker.volume > 0:
            self.vol_button.get_child().set_markup(icons.vol_medium)
        else:
            self.vol_button.get_child().set_markup(icons.vol_mute)

class MicSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-mic", **kwargs)
        self.audio = Audio()
        self.progress_bar = CircularProgressBar(
            name="button-mic", size=28, line_width=2,
            start_angle=150, end_angle=390,
        )
        self.mic_label = Label(name="mic-label", markup=icons.mic)
        self.mic_button = Button(on_clicked=self.toggle_mute, child=self.mic_label)
        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=Overlay(child=self.progress_bar, overlays=self.mic_button),
        )
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.add(self.event_box)
        self.on_microphone_changed()

    def on_new_microphone(self, *args):
        if self.audio.microphone:
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
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if abs(event.delta_y) > 0:
                self.audio.microphone.volume -= event.delta_y
            if abs(event.delta_x) > 0:
                self.audio.microphone.volume += event.delta_x

    def on_microphone_changed(self, *_):
        if not self.audio.microphone:
            return
        if self.audio.microphone.muted:
            self.mic_button.get_child().set_markup(icons.mic_mute)
            self.progress_bar.add_style_class("muted")
            self.mic_label.add_style_class("muted")
            self.set_tooltip_text("0%")
            return
        else:
            self.progress_bar.remove_style_class("muted")
            self.mic_label.remove_style_class("muted")
        self.progress_bar.value = self.audio.microphone.volume / 100
        self.set_tooltip_text(f"{round(self.audio.microphone.volume)}%")
        if self.audio.microphone.volume >= 1:
            self.mic_button.get_child().set_markup(icons.mic)
        else:
            self.mic_button.get_child().set_markup(icons.mic_mute)

# Los contenedores incluyen el widget de brillo solo si es soportado.
class ControlSliders(Box):
    def __init__(self, **kwargs):
        children = []
        if BACKLIGHT_SUPPORTED:
            children.append(BrightnessSlider())
        children.extend([VolumeSlider(), MicSlider()])
        super().__init__(
            name="control-sliders",
            orientation="h",
            spacing=4,
            children=children,
            **kwargs,
        )
        self.show_all()

class ControlSmall(Box):
    def __init__(self, **kwargs):
        children = []
        if BACKLIGHT_SUPPORTED:
            children.append(BrightnessSmall())
        children.extend([VolumeSmall(), MicSmall()])
        super().__init__(
            name="control-small",
            orientation="h",
            spacing=4,
            children=children,
            **kwargs,
        )
        self.show_all()

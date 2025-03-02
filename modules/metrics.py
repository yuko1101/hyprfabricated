import psutil
import subprocess
import re
from gi.repository import GLib

from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.widgets.scale import Scale
from fabric.widgets.eventbox import EventBox
from fabric.widgets.button import Button
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import exec_shell_command_async

import modules.icons as icons

class MetricsProvider:
    """
    Class responsible for obtaining centralized CPU, memory, and disk usage metrics.
    It updates periodically so that all widgets querying it display the same values.
    """
    def __init__(self):
        self.cpu = 0.0
        self.mem = 0.0
        self.disk = 0.0
        # Updates every 1 second
        GLib.timeout_add_seconds(1, self._update)

    def _update(self):
        # Get non-blocking usage percentages (interval=0)
        # The first call may return 0, but subsequent calls will provide consistent values.
        self.cpu = psutil.cpu_percent(interval=0)
        self.mem = psutil.virtual_memory().percent
        self.disk = psutil.disk_usage("/").percent
        return True

    def get_metrics(self):
        return (self.cpu, self.mem, self.disk)

# Global instance to share data between both widgets.
shared_provider = MetricsProvider()

class Metrics(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="metrics",
            spacing=8,
            h_align="center",
            v_align="fill",
            visible=True,
            all_visible=True,
        )

        self.cpu_usage = Scale(
            name="cpu-usage",
            value=0.25,
            orientation='v',
            inverted=True,
            v_align='fill',
            v_expand=True,
        )

        self.cpu_label = Label(
            name="cpu-label",
            markup=icons.cpu,
        )

        self.cpu = Box(
            name="cpu-box",
            orientation='v',
            spacing=8,
            children=[
                self.cpu_usage,
                self.cpu_label,
            ]
        )

        self.ram_usage = Scale(
            name="ram-usage",
            value=0.5,
            orientation='v',
            inverted=True,
            v_align='fill',
            v_expand=True,
        )

        self.ram_label = Label(
            name="ram-label",
            markup=icons.memory,
        )

        self.ram = Box(
            name="ram-box",
            orientation='v',
            spacing=8,
            children=[
                self.ram_usage,
                self.ram_label,
            ]
        )

        self.disk_usage = Scale(
            name="disk-usage",
            value=0.75,
            orientation='v',
            inverted=True,
            v_align='fill',
            v_expand=True,
        )

        self.disk_label = Label(
            name="disk-label",
            markup=icons.disk,
        )

        self.disk = Box(
            name="disk-box",
            orientation='v',
            spacing=8,
            children=[
                self.disk_usage,
                self.disk_label,
            ]
        )

        self.scales = [
            self.disk,
            self.ram,
            self.cpu,
        ]

        self.cpu_usage.set_sensitive(False)
        self.ram_usage.set_sensitive(False)
        self.disk_usage.set_sensitive(False)

        for x in self.scales:
            self.add(x)

        # Update the widget every second
        GLib.timeout_add_seconds(1, self.update_status)

    def update_status(self):
        # Retrieve centralized data
        cpu, mem, disk = shared_provider.get_metrics()

        # Normalize to 0.0 - 1.0
        self.cpu_usage.value = cpu / 100.0
        self.ram_usage.value = mem / 100.0
        self.disk_usage.value = disk / 100.0

        return True  # Continue calling this function.

class MetricsSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="metrics-small",
            spacing=4,
            orientation="h",
            visible=True,
            all_visible=True,
        )

        # CPU
        self.cpu_icon = Label(name="metrics-icon", markup=icons.cpu)
        self.cpu_circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
        )
        self.cpu_overlay = Overlay(
            name="metrics-overlay",
            child=self.cpu_circle,
            overlays=[self.cpu_icon],
        )

        # RAM
        self.ram_icon = Label(name="metrics-icon", markup=icons.memory)
        self.ram_circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
        )
        self.ram_overlay = Overlay(
            name="metrics-overlay",
            child=self.ram_circle,
            overlays=[self.ram_icon],
        )

        # Disk
        self.disk_icon = Label(name="metrics-icon", markup=icons.disk)
        self.disk_circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
        )
        self.disk_overlay = Overlay(
            name="metrics-overlay",
            child=self.disk_circle,
            overlays=[self.disk_icon],
        )

        # Battery
        self.bat_icon = Label(name="metrics-icon", markup=icons.battery)
        self.bat_circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
        )
        self.bat_overlay = Overlay(
            name="metrics-overlay",
            child=self.bat_circle,
            overlays=[self.bat_icon],
        )

        # Battery level label and revealer
        self.bat_level = Label(name="metrics-level", label="100%")
        self.bat_revealer = Revealer(
            name="metrics-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.bat_level,
            child_revealed=False,
        )

        # Add all components
        self.add(self.cpu_overlay)
        self.add(self.ram_overlay)
        self.add(self.disk_overlay)
        self.add(self.bat_overlay)
        self.add(self.bat_revealer)

        # Initial state
        self.hide_timer = None
        self.hover_counter = 0

        # Configure event handlers to display battery details
        for widget in [self.cpu_overlay, self.ram_overlay, self.disk_overlay, self.bat_overlay]:
            event_box = EventBox(events=["enter-notify-event", "leave-notify-event"])
            event_box.connect("enter-notify-event", self.on_mouse_enter)
            event_box.connect("leave-notify-event", self.on_mouse_leave)
            event_box.add(widget)

        # Update indicators every second using centralized data.
        GLib.timeout_add_seconds(1, self.update_metrics)

        # Initialize battery update
        self.batt_fabricator = Fabricator(lambda *args, **kwargs: self.poll_battery(), interval=1000, stream=False, default_value=0)
        self.batt_fabricator.changed.connect(self.update_battery)

        GLib.idle_add(self.update_battery, None, self.poll_battery())

    def on_mouse_enter(self, widget, event):
        self.hover_counter += 1
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None
        self.bat_revealer.set_reveal_child(True)
        return False

    def on_mouse_leave(self, widget, event):
        if self.hover_counter > 0:
            self.hover_counter -= 1
        if self.hover_counter == 0:
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
            self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
        return False

    def hide_revealer(self):
        self.bat_revealer.set_reveal_child(False)
        self.hide_timer = None
        return False

    def update_metrics(self):
        # Use centralized data
        cpu, mem, disk = shared_provider.get_metrics()
        self.cpu_circle.set_value(cpu / 100.0)
        self.ram_circle.set_value(mem / 100.0)
        self.disk_circle.set_value(disk / 100.0)
        return True

    def poll_battery(self):
        try:
            output = subprocess.check_output(["acpi", "-b"]).decode("utf-8").strip()
            if "Battery" not in output:
                return (0, None)
            match_percent = re.search(r'(\d+)%', output)
            match_status = re.search(r'Battery \d+: (\w+)', output)
            if match_percent:
                percent = int(match_percent.group(1))
                status = match_status.group(1) if match_status else None
                return (percent / 100.0, status)
        except Exception:
            pass
        return (0, None)

    def update_battery(self, sender, battery_data):
        value, status = battery_data
        if value == 0:
            self.bat_overlay.set_visible(False)
            self.bat_revealer.set_visible(False)
        else:
            self.bat_overlay.set_visible(True)
            self.bat_revealer.set_visible(True)
            self.bat_circle.set_value(value)

        percentage = int(value * 100)
        self.bat_level.set_label(f"{percentage}%")

        if percentage <= 15:
            self.bat_icon.set_markup(icons.alert)
            self.bat_icon.add_style_class("alert")
            self.bat_circle.add_style_class("alert")
        else:
            self.bat_icon.remove_style_class("alert")
            self.bat_circle.remove_style_class("alert")
            if status == "Discharging":
                self.bat_icon.set_markup(icons.discharging)
            elif percentage == 100:
                self.bat_icon.set_markup(icons.battery)
            elif status == "Charging":
                self.bat_icon.set_markup(icons.charging)
            else:
                self.bat_icon.set_markup(icons.battery)

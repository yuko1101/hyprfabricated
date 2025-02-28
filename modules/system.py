import subprocess
import psutil
import re
from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox  # <-- use our EventBox
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import exec_shell_command_async

from gi.repository import GLib

import modules.icons as icons

class System(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="battery",
            orientation="h",
            spacing=3,
        )

        # Create three buttons for power modes.
        self.bat_save = Button(
            name="battery-save",
            child=Label(name="battery-save-label", markup=icons.power_saving),
            on_clicked=lambda *_: self.set_power_mode("powersave"),
        )
        self.bat_balanced = Button(
            name="battery-balanced",
            child=Label(name="battery-balanced-label", markup=icons.power_balanced),
            on_clicked=lambda *_: self.set_power_mode("balanced"),
        )
        self.bat_perf = Button(
            name="battery-performance",
            child=Label(name="battery-performance-label", markup=icons.power_performance),
            on_clicked=lambda *_: self.set_power_mode("performance"),
        )

        # Attach mouse enter/leave events to buttons as well
        for btn in [self.bat_save, self.bat_balanced, self.bat_perf]:
            btn.connect("enter-notify-event", self.on_mouse_enter)
            btn.connect("leave-notify-event", self.on_mouse_leave)

        # Group the mode buttons into a container.
        self.mode_switcher = Box(
            name="power-mode-switcher",
            orientation="h",
            spacing=4,
            children=[self.bat_save, self.bat_balanced, self.bat_perf],
        )
        self.cpu_icon = Label(name="memory-usage",markup=icons.cpu)

        self.cpu_circle = CircularProgressBar(
            name="cpu-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=180,
            end_angle=360,
        )

        self.cpu_overlay = Overlay(
            name="cpu-overlay",
            visible=False,
            child=self.cpu_circle,
            overlays=[self.cpu_icon],
        )

        self.cpu_level = Label(
            name="cpu-used",
            label="100%",
        )

        self.cpu_revealer = Revealer(
            name="cpu-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.cpu_level,
            child_revealed=False,
        )

        self.memory_icon = Label(name="memory-usage",markup=icons.memory)

        self.memory_circle = CircularProgressBar(
            name="memory-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=180,
            end_angle=360,
        )

        self.memory_overlay = Overlay(
            name="memory-overlay",
            visible=False,
            child=self.memory_circle,
            overlays=[self.memory_icon],
        )

        self.memory_level = Label(
            name="memory-used",
            label="100%",
        )

        self.memory_revealer = Revealer(
            name="memory-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.memory_level,
            child_revealed=False,
        )

        self.bat_icon = Label(name="battery-icon", markup=icons.battery)

        self.bat_circle = CircularProgressBar(
            name="battery-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
        )

        self.bat_overlay = Overlay(
            name="battery-overlay",
            visible=False,
            child=self.bat_circle,
            overlays=[self.bat_icon],
        )

        self.bat_level = Label(
            name="battery-level",
            label="100%",
        )

        self.bat_revealer = Revealer(
            name="battery-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.bat_level,
            child_revealed=False,
        )

        # Create an inner container to hold the battery elements.
        inner_container = Box(orientation="h", spacing=5)
        inner_container.add(self.bat_overlay)
        inner_container.add(self.bat_revealer)
        # inner_container.add(self.memory)
        inner_container.add(self.memory_overlay)
        inner_container.add(self.memory_revealer)
        inner_container.add(self.cpu_overlay)
        inner_container.add(self.cpu_revealer)
        # inner_container.add(self.mode_switcher)

        # Wrap the inner container in an EventBox.
        self.event_box = EventBox(
            events=["enter-notify-event", "leave-notify-event"],
            name="battery-eventbox",
        )
        self.event_box.connect("enter-notify-event", self.on_mouse_enter)
        self.event_box.connect("leave-notify-event", self.on_mouse_leave)
        self.event_box.add(inner_container)

        # Add the EventBox to the Battery widget.
        self.add(self.event_box)

        self.current_mode = None
        # Initialize hide_timer for delayed hiding.
        self.hide_timer = None
        # Initialize counter to track hover status across all related widgets.
        self.hover_counter = 0

        self.memory_fabricator = Fabricator(lambda *args, **kwargs: self.poll_ram_usage(), interval=1000, stream=False, default_value=0)
        self.memory_fabricator.changed.connect(self.update_memory)
        GLib.idle_add(self.update_memory, None, self.poll_ram_usage())

        self.cpu_fabricator = Fabricator(lambda *args, **kwargs: self.poll_cpu_usage(), interval=1000, stream=False, default_value=0)
        self.cpu_fabricator.changed.connect(self.update_cpu)
        GLib.idle_add(self.update_cpu, None, self.poll_cpu_usage())
        # Initialize Fabricator for battery polling every 5 seconds.
        # self.set_power_mode("balanced")
        self.batt_fabricator = Fabricator(lambda *args, **kwargs: self.poll_battery(), interval=5000, stream=False, default_value=0)
        self.batt_fabricator.changed.connect(self.update_battery)

        # Run update_battery immediately at startup.
        GLib.idle_add(self.update_battery, None, self.poll_battery())
        self.set_power_mode("balanced")

    def on_mouse_enter(self, widget, event):
        """Reveal battery level on hover."""
        self.hover_counter += 1
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None
        self.bat_revealer.set_reveal_child(True)
        self.memory_revealer.set_reveal_child(True)
        self.cpu_revealer.set_reveal_child(True)
        return False

    def on_mouse_leave(self, widget, event):
        """Schedule hiding the battery level after a 0.5s delay only if not hovering any element."""
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
        self.memory_revealer.set_reveal_child(False)
        self.cpu_revealer.set_reveal_child(False)
        return False


    def poll_cpu_usage(self):
        """
        Polls the current total CPU usage.
    def update_status(self):
        # Note: psutil.cpu_percent(interval=1) blocks. If blocking is not desired,
        # consider using interval=0 to get a non-blocking value.
        cpu = psutil.cpu_percent(interval=0)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent

        # Normalize percentage values to range 0.0 - 1.0
        self.cpu_usage.value = cpu / 100.0
        self.ram_usage.value = mem / 100.0
        self.disk_usage.value = disk / 100.0

        return True  # Continue calling this function.
        Returns a tuple: (CPU usage percentage as a float between 0 and 1, status placeholder).
        """
        try:
            # Instantaneous snapshot of total CPU usage
            usage_percent = psutil.cpu_percent(interval=0)

            # Return usage and a placeholder status (like 1 for 'active')
            return (usage_percent / 100.0, 1)

        except Exception:
            pass
        return (0.0, 0)

    # def poll_cpu_usage(self):
    #     """
    #     Polls the current CPU usage.
    #     Returns a tuple: (CPU usage percentage as a float between 0 and 1, number of logical cores).
    #     """
    #     try:
    #         # Get the current CPU usage percentage
    #         usage_percent = psutil.cpu_percent(interval=0.1)
    #         core_count = psutil.cpu_count(logical=True)
    #
    #         return (usage_percent / 100.0, core_count)
    #
    #     except Exception:
    #         pass
    #     return (0.0, 0)

    def poll_ram_usage(self):
        """
        polls the current ram usage.
        returns a tuple: (ram usage percentage as a float between 0 and 1, total ram in bytes)
        """
        try:
            # get virtual memory stats
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            total_ram = memory.total

            return (usage_percent / 100.0, total_ram)

        except exception:
            pass
        return (0, none)

    def poll_battery(self):
        """
        Polls the battery status by running the "acpi -b" command.
        If no battery information is found, returns (0, None).
        Otherwise, returns a tuple: (battery percentage as a float between 0 and 1, battery status string)
        """
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
    def update_memory(self, sender, memory_data):
        """
        Updates the battery widget...
        """
        value, status = memory_data
        if value == 0:
            self.memory_overlay.set_visible(False)
            self.memory_revealer.set_visible(False)
        else:
            self.memory_overlay.set_visible(True)
            self.memory_revealer.set_visible(True)
            self.memory_circle.set_value(value)

        percentage = int(value * 100)
        self.memory_level.set_label(f"{percentage}%")

    def update_cpu(self, sender, cpu_data):
        """
        Updates the battery widget...
        """
        value, status = cpu_data
        self.cpu_overlay.set_visible(True)
        self.cpu_revealer.set_visible(True)
        self.cpu_circle.set_value(value)

        percentage = int(value * 100)
        self.cpu_level.set_label(f"{percentage}%")

    def update_battery(self, sender, battery_data):
        """
        Updates the battery widget...
        """
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

        # Actualizar el icono de la batería basado en el nivel y el estado de carga.
        if percentage <= 15:
            self.bat_icon.set_markup(icons.alert)
            self.bat_icon.add_style_class("alert")
            self.bat_circle.add_style_class("alert")
        else:
            self.bat_icon.remove_style_class("alert")
            self.bat_circle.remove_style_class("alert")
            if status == "Discharging":  # Muestra discharging en cualquier nivel, incluso al 100%.
                self.bat_icon.set_markup(icons.discharging)
            elif percentage == 100:
                self.bat_icon.set_markup(icons.battery)
            elif status == "Charging":
                self.bat_icon.set_markup(icons.charging)
            else:
                self.bat_icon.set_markup(icons.battery)

    def set_power_mode(self, mode):
        pass
        # """
        # Switches power mode by running the corresponding auto-cpufreq command.
        # mode: one of 'powersave', 'balanced', or 'performance'
        # """
        # commands = {
        #     "powersave": "sudo auto-cpufreq --force powersave",
        #     "balanced": "sudo auto-cpufreq --force reset",
        #     "performance": "sudo auto-cpufreq --force performance",
        # }
        # if mode in commands:
        #     try:
        #         exec_shell_command_async(commands[mode])
        #         self.current_mode = mode
        #         self.update_button_styles()
        #     except Exception as err:
        #         # Optionally, handle errors or display a notification.
        #         print(f"Error setting power mode: {err}")

    def update_button_styles(self):
        """
        Optionally updates button styles to reflect the current mode.
        Adjust the styling method based on your toolkit's capabilities.
        """
        if self.current_mode == "powersave":
            self.bat_save.add_style_class("active")
            self.bat_balanced.remove_style_class("active")
            self.bat_perf.remove_style_class("active")
        elif self.current_mode == "balanced":
            self.bat_save.remove_style_class("active")
            self.bat_balanced.add_style_class("active")
            self.bat_perf.remove_style_class("active")
        elif self.current_mode == "performance":
            self.bat_save.remove_style_class("active")
            self.bat_balanced.remove_style_class("active")
            self.bat_perf.add_style_class("active")

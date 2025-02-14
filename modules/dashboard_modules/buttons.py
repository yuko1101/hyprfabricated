import subprocess
from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.utils.helpers import exec_shell_command_async
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
import modules.icons as icons


class NetworkButton(Box):
    def __init__(self):
        self.network_icon = Label(
            name="network-icon",
            markup=icons.wifi,
        )
        self.network_label = Label(
            name="network-label",
            label="Wi-Fi",
            justification="left",
        )
        self.network_label_box = Box(children=[self.network_label, Box(h_expand=True)])
        self.network_ssid = Label(
            name="network-ssid",
            label="ARGOS_5GHz",
            justification="left",
        )
        self.network_ssid_box = Box(children=[self.network_ssid, Box(h_expand=True)])
        self.network_text = Box(
            name="network-text",
            orientation="v",
            h_align="start",
            v_align="center",
            children=[self.network_label_box, self.network_ssid_box],
        )
        self.network_status_box = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[self.network_icon, self.network_text],
        )
        self.network_status_button = Button(
            name="network-status-button",
            h_expand=True,
            child=self.network_status_box,
        )
        self.network_menu_label = Label(
            name="network-menu-label",
            markup=icons.chevron_right,
        )
        self.network_menu_button = Button(
            name="network-menu-button",
            child=self.network_menu_label,
        )

        super().__init__(
            name="network-button",
            orientation="h",
            h_align="fill",
            v_align="center",
            h_expand=True,
            v_expand=True,
            spacing=0,
            children=[self.network_status_button, self.network_menu_button],
        )


class BluetoothButton(Box):
    def __init__(self, notch):
        super().__init__(
            name="bluetooth-button",
            orientation="h",
            h_align="fill",
            v_align="center",
            h_expand=True,
            v_expand=True,
        )
        self.notch = notch

        self.bluetooth_icon = Label(
            name="bluetooth-icon",
            markup=icons.bluetooth,
        )
        self.bluetooth_label = Label(
            name="bluetooth-label",
            label="Bluetooth",
            justification="left",
        )
        self.bluetooth_label_box = Box(children=[self.bluetooth_label, Box(h_expand=True)])
        self.bluetooth_status_text = Label(
            name="bluetooth-status",
            label="Disabled",
            justification="left",
        )
        self.bluetooth_status_box = Box(children=[self.bluetooth_status_text, Box(h_expand=True)])
        self.bluetooth_text = Box(
            orientation="v",
            h_align="start",
            v_align="center",
            children=[self.bluetooth_label_box, self.bluetooth_status_box],
        )
        self.bluetooth_status_container = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[self.bluetooth_icon, self.bluetooth_text],
        )
        self.bluetooth_status_button = Button(
            name="bluetooth-status-button",
            h_expand=True,
            child=self.bluetooth_status_container,
            on_clicked=lambda *_: self.notch.bluetooth.client.toggle_power(),
        )
        self.bluetooth_menu_label = Label(
            name="bluetooth-menu-label",
            markup=icons.chevron_right,
        )
        self.bluetooth_menu_button = Button(
            name="bluetooth-menu-button",
            on_clicked=lambda *_: self.notch.open_notch("bluetooth"),
            child=self.bluetooth_menu_label,
        )

        self.add(self.bluetooth_status_button)
        self.add(self.bluetooth_menu_button)


class NightModeButton(Button):
    def __init__(self):
        self.night_mode_icon = Label(
            name="night-mode-icon",
            markup=icons.night,
        )
        self.night_mode_label = Label(
            name="night-mode-label",
            label="Night Mode",
            justification="left",
        )
        self.night_mode_label_box = Box(children=[self.night_mode_label, Box(h_expand=True)])
        self.night_mode_status = Label(
            name="night-mode-status",
            label="Enabled",
            justification="left",
        )
        self.night_mode_status_box = Box(children=[self.night_mode_status, Box(h_expand=True)])
        self.night_mode_text = Box(
            name="night-mode-text",
            orientation="v",
            h_align="start",
            v_align="center",
            children=[self.night_mode_label_box, self.night_mode_status_box],
        )
        self.night_mode_box = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[self.night_mode_icon, self.night_mode_text],
        )

        super().__init__(
            name="night-mode-button",
            h_expand=True,
            child=self.night_mode_box,
            on_clicked=self.toggle_hyprsunset,
        )

        self.widgets = [self, self.night_mode_label, self.night_mode_status, self.night_mode_icon]
        self.check_hyprsunset()

    def toggle_hyprsunset(self, *args):
        """
        Toggle the 'hyprsunset' process:
          - If running, kill it and mark as 'Disabled'.
          - If not running, start it and mark as 'Enabled'.
        """
        try:
            # Check if hyprsunset is running
            subprocess.check_output(["pgrep", "hyprsunset"])
            # Process found – kill it
            exec_shell_command_async("pkill hyprsunset")
            self.night_mode_status.set_label("Disabled")
            for widget in self.widgets:
                widget.add_style_class("disabled")
        except subprocess.CalledProcessError:
            # Process not found – start it
            exec_shell_command_async("hyprsunset -t 3500")
            self.night_mode_status.set_label("Enabled")
            for widget in self.widgets:
                widget.remove_style_class("disabled")

    def check_hyprsunset(self, *args):
        """
        Update the button state based on whether hyprsunset is running.
        """
        try:
            subprocess.check_output(["pgrep", "hyprsunset"])
            self.night_mode_status.set_label("Enabled")
            for widget in self.widgets:
                widget.remove_style_class("disabled")
        except subprocess.CalledProcessError:
            self.night_mode_status.set_label("Disabled")
            for widget in self.widgets:
                widget.add_style_class("disabled")


class CaffeineButton(Button):
    def __init__(self):
        self.caffeine_icon = Label(
            name="caffeine-icon",
            markup=icons.coffee,
        )
        self.caffeine_label = Label(
            name="caffeine-label",
            label="Caffeine",
            justification="left",
        )
        self.caffeine_label_box = Box(children=[self.caffeine_label, Box(h_expand=True)])
        # Save the status label so we can update it when toggling
        self.caffeine_status = Label(
            name="caffeine-status",
            label="Enabled",
            justification="left",
        )
        self.caffeine_status_box = Box(children=[self.caffeine_status, Box(h_expand=True)])
        self.caffeine_text = Box(
            name="caffeine-text",
            orientation="v",
            h_align="start",
            v_align="center",
            children=[self.caffeine_label_box, self.caffeine_status_box],
        )
        self.caffeine_box = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[self.caffeine_icon, self.caffeine_text],
        )
        # Attach the toggle function to the button click
        super().__init__(
            name="caffeine-button",
            h_expand=True,
            child=self.caffeine_box,
            on_clicked=self.toggle_wlinhibit,
        )

        self.widgets = [self, self.caffeine_label, self.caffeine_status, self.caffeine_icon]

        self.check_wlinhibit()

    def toggle_wlinhibit(self, *args):
        """
        Toggle the 'wlinhibit' process:
          - If running, kill it and mark as 'Disabled' (add 'disabled' class).
          - If not running, start it and mark as 'Enabled' (remove 'disabled' class).
        """
        try:
            # Check if wlinhibit is running (pgrep exits with nonzero if not found)
            subprocess.check_output(["pgrep", "wlinhibit"])
            # Process found – kill it
            exec_shell_command_async("pkill wlinhibit")
            self.caffeine_status.set_label("Disabled")
            for i in self.widgets:
                i.add_style_class("disabled")

        except subprocess.CalledProcessError:
            # Process not found – start it
            exec_shell_command_async("wlinhibit")
            self.caffeine_status.set_label("Enabled")
            for i in self.widgets:
                i.remove_style_class("disabled")

    def check_wlinhibit(self, *args):
        try:
            # Process found – caffeine is active
            subprocess.check_output(["pgrep", "wlinhibit"])
            self.caffeine_status.set_label("Enabled")
            for i in self.widgets:
                i.remove_style_class("disabled")
        except subprocess.CalledProcessError:
            # Process not found – caffeine is inactive
            self.caffeine_status.set_label("Disabled")
            for i in self.widgets:
                i.add_style_class("disabled")


class Buttons(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="buttons",
            spacing=4,
            h_align="fill",
            v_align="fill",
            h_expand=True,
            v_expand=False,
            visible=True,
            all_visible=True,
        )
        self.notch = kwargs["notch"]

        # Instantiate each button
        self.network_button = NetworkButton()
        self.bluetooth_button = BluetoothButton(self.notch)
        self.night_mode_button = NightModeButton()
        self.caffeine_button = CaffeineButton()

        # Add buttons to the container
        self.add(self.network_button)
        self.add(self.bluetooth_button)
        self.add(self.night_mode_button)
        self.add(self.caffeine_button)

        self.show_all()

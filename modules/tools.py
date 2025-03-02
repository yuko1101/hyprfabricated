from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.utils.helpers import exec_shell_command_async
import modules.icons as icons

class Toolbox(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="toolbox",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            v_expand=True,
            h_expand=True,
            visible=True,
            **kwargs,
        )

        self.notch = kwargs["notch"]

        self.btn_screenshot = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.screenshot),
            on_clicked=self.lock,
        )

        self.btn_screenrecord = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.screenrecord),
            on_clicked=self.suspend,
        )

        self.btn_ocr = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.ocr),
            on_clicked=self.logout,
        )

        self.btn_close = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.close),
            # on_clicked=self.close_menu(),
        )

        # self.btn_shutdown = Button(
        #     name="toolbox-button",
        #     child=Label(name="button-label", markup=icons.shutdown),
        #     on_clicked=self.poweroff,
        # )

        self.buttons = [
            self.btn_screenshot,
            self.btn_screenrecord,
            self.btn_ocr,
            self.btn_close,
            # self.btn_shutdown,
        ]

        for button in self.buttons:
            self.add(button)

        self.show_all()

    def close_menu(self):
        self.notch.close_notch()

    # Métodos de acción
    def lock(self, *args):
        print("Locking screen...")
        exec_shell_command_async("loginctl lock-session")
        self.close_menu()

    def suspend(self, *args):
        print("Suspending system...")
        exec_shell_command_async("systemctl suspend")
        self.close_menu()

    def logout(self, *args):
        print("Logging out...")
        exec_shell_command_async("hyprctl dispatch exit")
        self.close_menu()

    def reboot(self, *args):
        print("Rebooting system...")
        exec_shell_command_async("systemctl reboot")
        self.close_menu()

    def poweroff(self, *args):
        print("Powering off...")
        exec_shell_command_async("systemctl poweroff")
        self.close_menu()

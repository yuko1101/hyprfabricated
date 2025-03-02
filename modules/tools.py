from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.utils.helpers import exec_shell_command_async
import modules.icons as icons
from fabric.utils.helpers import get_relative_path, exec_shell_command_async
SCREENSHOT_SCRIPT = get_relative_path("../scripts/screenshot.sh")
OCR_SCRIPT = get_relative_path("../scripts/ocr.sh")
SCREENRECORD_SCRIPT = get_relative_path("../scripts/screenrecord.sh")
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

        self.btn_ssregion = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.ssregion),
            on_clicked=self.ssregion,
        )
        self.btn_ssfull = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.ssfull),
            on_clicked=self.ssfull,
        )

        self.btn_screenrecord = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.screenrecord),
            on_clicked=self.screenrecord,
        )

        self.btn_ocr = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.ocr),
            on_clicked=self.ocr,
        )

        self.btn_close = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.close),
            # on_clicked=self.close,
        )


        self.buttons = [
            self.btn_ssregion,
            self.btn_ssfull,
            self.btn_screenrecord,
            self.btn_ocr,
            self.btn_close,
        ]

        for button in self.buttons:
            self.add(button)

        self.show_all()

    def close_menu(self):
        self.notch.close_notch()

    # Métodos de acción
    def ssfull(self, *args):
        exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} p")
        self.close_menu()

    def screenrecord(self, *args):
        exec_shell_command_async(f"bash {SCREENRECORD_SCRIPT}")
        self.close_menu()

    def ocr(self, *args):
        exec_shell_command_async(f"bash {OCR_SCRIPT} sf")
        self.close_menu()


    def ssregion(self, *args):
        exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} sf")
        self.close_menu()
    # def close():
    #     self.close_menu()

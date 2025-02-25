from fabric import Application
from fabric.widgets.box import Box
from fabric.widgets.datetime import DateTime
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import get_relative_path


class Deskwidgets(Window):

    def __init__(self, **kwargs):
        super().__init__(name="desktop", **kwargs)
        self.desktop_widget = Window(
            layer="bottom",
            anchor="bottom left",  # FYI: there's no anchor named "center" (anchor of "" is == to "center")
            exclusivity="none",
            child=Box(
                orientation="v",
                children=[
                    DateTime(formatters=["%I:%M"], name="clock"),
                    DateTime(formatters=["%A. %d %B"], interval=10000, name="date"),
                ],
            ),
            all_visible=True,
        )


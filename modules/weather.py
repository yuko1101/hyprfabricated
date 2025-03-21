import gi
import urllib.parse
import requests
from gi.repository import GLib

from fabric.widgets.label import Label
from fabric.widgets.button import Button

gi.require_version("Gtk", "3.0")
import modules.icons as icons
import config.data as data

class Weather(Button):
    def __init__(self, **kwargs) -> None:
        super().__init__(name="weather", orientation="h", spacing=8, **kwargs)
        self.label = Label(name="weather-label", markup=icons.loader)
        self.add(self.label)
        self.show_all()
        self.session = requests.Session()  # Reuse HTTP connection
        # Update every 10 minutes
        GLib.timeout_add_seconds(600, self.fetch_weather)
        self.fetch_weather()

    def fetch_weather(self):
        GLib.Thread.new("weather-fetch", self._fetch_weather_thread, None)
        return True

    def _fetch_weather_thread(self, user_data):
        # Let wttr.in determine location based on IP
        url = "https://wttr.in/?format=%c+%t" if not data.VERTICAL else "https://wttr.in/?format=%c"
        # Get detailed info for tooltip
        tooltip_url = "https://wttr.in/?format=%l:+%C,+%t+(%f),+Humidity:+%h,+Wind:+%w"
        
        try:
            response = self.session.get(url, timeout=5)
            if response.ok:
                weather_data = response.text.strip()
                if "Unknown" in weather_data:
                    GLib.idle_add(self.set_visible, False)
                else:
                    # Get tooltip data
                    tooltip_response = self.session.get(tooltip_url, timeout=5)
                    if tooltip_response.ok:
                        tooltip_text = tooltip_response.text.strip()
                        GLib.idle_add(self.set_tooltip_text, tooltip_text)
                    
                    GLib.idle_add(self.set_visible, True)
                    GLib.idle_add(self.label.set_label, weather_data.replace(" ", ""))
            else:
                GLib.idle_add(self.label.set_markup, f"{icons.cloud_off} Unavailable")
                GLib.idle_add(self.set_visible, False)
        except Exception as e:
            print(f"Error fetching weather: {e}")
            GLib.idle_add(self.label.set_markup, f"{icons.cloud_off} Error")
            GLib.idle_add(self.set_visible, False)

import gi
import requests

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

class Weather(Gtk.Box):
    def __init__(self, pixel_size: int = 20, **kwargs) -> None:
        super().__init__(name="weather", orientation=Gtk.Orientation.HORIZONTAL, spacing=8, **kwargs)
        self.pixel_size = pixel_size
        self.label = Gtk.Label(label="Fetching Weather...")
        self.pack_start(self.label, False, False, 0)
        self.set_visible(True)
        GLib.timeout_add_seconds(600, self.fetch_weather)
        self.fetch_weather()

    def get_location(self):
        try:
            response = requests.get("http://ip-api.com/json")
            if response.status_code == 200:
                data = response.json()
                return data.get("city", "")
        except Exception as e:
            print(f"Location fetch error: {e}")
        return ""

    def fetch_weather(self):
        location = self.get_location()
        url = f"https://wttr.in/{location}?format=%c+%t" if location else "https://wttr.in/?format=%c+%t"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                weather_data = response.text.strip()
                self.label.set_text(weather_data)
            else:
                self.label.set_text("Weather unavailable")
        except Exception as e:
            self.label.set_text("Weather error")
            print(f"Weather fetch error: {e}")
        return True


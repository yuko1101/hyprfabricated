import gi
import urllib.parse
import requests
from gi.repository import GLib
import modules.icons as icons
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from functools import partial

gi.require_version("Gtk", "3.0")


class Weather(Box):
    def __init__(self, **kwargs) -> None:
        super().__init__(name="weather", orientation="h", spacing=8, **kwargs)
        self.label = Label(name="weather-label", markup=icons.loader)
        self.add(self.label)
        self.show_all()
        self.session = requests.Session()  # Reuse HTTP connection
        self.api_url = "https://wttr.in/{}?format=%c+%t"

        # Update every 10 minutes
        GLib.timeout_add_seconds(600, self.fetch_weather)
        self.fetch_weather()

    def get_location(self):
        """Fetch user's city using IP geolocation."""
        try:
            response = self.session.get("https://ipinfo.io/json", timeout=5, stream=True)
            if response.ok:
                return response.json().get("city", "")
        except requests.RequestException:
            pass
        return ""

    def fetch_weather(self):
        """Fetch weather data asynchronously."""
        GLib.Thread.new("weather-fetch", self._fetch_weather_thread, None)
        return True

    def _fetch_weather_thread(self, data):
        """Worker thread to fetch and process weather data."""
        location = self.get_location()
        if not location:
            return self._update_ui(error=True)

        try:
            response = self.session.get(self.api_url.format(urllib.parse.quote(location)), timeout=5, stream=True)
            if response.ok:
                weather_data = response.text.strip()
                if "Unknown" in weather_data:
                    self._update_ui(visible=False)
                else:
                    self._update_ui(weather_data.replace(" ", ""), visible=True)
            else:
                self._update_ui(error=True)
        except requests.RequestException:
            self._update_ui(error=True)

    def _update_ui(self, text=None, visible=True, error=False):
        """Safely update UI elements from the worker thread."""
        if error:
            text = f"{icons.cloud_off} Unavailable"
            visible = False
        GLib.idle_add(self.label.set_markup if error else self.label.set_label, text)
        GLib.idle_add(self.set_visible, visible)


from fabric import Application
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.datetime import DateTime
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import get_relative_path
import os
from loguru import logger
import psutil
import time
from fabric import Application
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.datetime import DateTime
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import invoke_repeater, get_relative_path
import requests
import urllib.parse
import threading
import threading
import time
import datetime
def get_location():
    try:
        response = requests.get("https://ipinfo.io/json")
        response.encoding = 'utf-8'  # Ensure the response is decoded using UTF-8

        if response.status_code == 200:
            data = response.json()
            return data.get('city', '').replace(' ', '')
        else:
            print("Error getting location from ipinfo.")
    except Exception as e:
        print(f"Error getting location: {e}")
    return ""

def get_location_threaded(callback):
    def run():
        location = get_location()
        callback(location)

    threading.Thread(target=run, daemon=True).start()

def get_weather(callback):
    def fetch_weather(location):
        if location:
            encoded_location = urllib.parse.quote(location)
            url = f"https://wttr.in/{encoded_location}?format=%c+%t+%C+%f"
        else:
            callback(None)
            return

        try:
            response = requests.get(url)
            if response.status_code == 200:
                weather_data = response.text.strip().split()
                if len(weather_data) == 4:
                    emoji, temp, condition, feels_like = weather_data
                    temp = temp.replace('+', '').replace('C', '')
                    feels_like = feels_like.replace('+', '').replace('C', '')
                    update_time = datetime.datetime.now().strftime("%H:%M:%S")
                    callback([emoji, temp, condition, feels_like, location, update_time])
                else:
                    print("Unexpected weather data format.")
                    callback(None)
            else:
                print("Error getting weather from wttr.in.")
                callback(None)
        except Exception as e:
            print(f"Error getting weather: {e}")
            callback(None)

    get_location_threaded(fetch_weather)

def update_weather(widget):
    def fetch_and_update():
        while True:
            get_weather(lambda weather_info: update_widget(widget, weather_info))
            time.sleep(600)  # 10 minutes

    threading.Thread(target=fetch_and_update, daemon=True).start()

def update_widget(widget, weather_info):
    if weather_info:
        widget.weatherinfo = weather_info
        widget.update_labels()

class weather(Box):
    def __init__(self, **kwargs):
        super().__init__(
            layer="bottom",
            name="weather-widget",
            h_align="center",
            v_align="center",
            h_expand=True,
            visible=False,
            v_expand=True,
            **kwargs,
        )
        self.weatherinfo = None
        self.header = Box(
            name="header1",
            orientation="h",
            h_expand=True,
            children=[
                Box(
                    orientation="v",
                    children=[
                        Label(label="On Moon", h_align="start", name="headertxt1"),
                        Label(label="", h_align="start", name="headertxt3"),
                        Label(label="", h_align="start", name="headertxt2"),
                    ],
                ),
            ],
        )
        self.temp = Box(
            name="header2",
            orientation="h",
            children=[
                Box(
                    orientation="v",
                    children=[
                        Label(label="", name="temptxt"),
                        Label(label="Feels like ", name="temptxtbt")
                    ],
                ),
            ],
        )
        self.header_right = Box(
            name="header3",
            orientation="h",
            children=[
                Box(
                    orientation="v",
                    children=[
                        Label(label="", name="headertxt"),
                    ],
                ),
            ],
        )
        self.add(
            Box(
                name="window-inner",
                orientation="h",
                h_align="center",
                v_align="center",
                children=[self.header, self.temp, self.header_right],
            ),
        )
        self.show_all()
        self.set_visible(False)
        update_weather(self)

    def update_labels(self):
        if self.weatherinfo:
            self.set_visible(True)
            self.header.children[0].children[0].set_label(f"{self.weatherinfo[4]}")
            self.header.children[0].children[1].set_label(f"Updated {self.weatherinfo[5]}")
            self.header.children[0].children[2].set_label(f"{self.weatherinfo[2]}")
            self.temp.children[0].children[0].set_label(f"{self.weatherinfo[1]}")
            self.temp.children[0].children[1].set_label(f"Feels like {self.weatherinfo[3]}")
            self.header_right.children[0].children[0].set_label(f"{self.weatherinfo[0]}")

def fetch_quote():
    try:
        response = requests.get('https://zenquotes.io/api/random')
        response.raise_for_status()
        data = response.json()
        return data[0]['q']  # Return the quote text
    except requests.exceptions.RequestException as e:
        print(f'Error fetching quote: {e}')
        return "What's in your head,in your head?"


class qoute(Label):
    def __init__(self, **kwargs):
        super().__init__(
            name="quote",
            label=f"{fetch_quote()}",
            h_align="center",
            v_align="center",
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
        )

class Deskwidgets(Window):
    def __init__(self, **kwargs):
        super().__init__(name="desktop", **kwargs)
        desktop_widget = Window(
            layer="bottom",
            anchor="center",
            exclusivity="none",
            child=Box(
                orientation="v",
                v_expand=True,
                v_align="center",
                h_align="center",
                children=[
                    DateTime(formatters=["%A, %d %B"], interval=10000, name="date"),
                    DateTime(formatters=["%I:%M"], name="clock"),
                    qoute(),
                    weather(),
                ],
            ),
            all_visible=True,
        )


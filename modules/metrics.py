import subprocess
import json
import logging
# import threading # Removed threading
import time
import gi # Added gi
gi.require_version('GLib', '2.0') # Added GLib requirement
from gi.repository import GLib # Ensure GLib is imported
import os # Added os
import signal # Added signal

import psutil
# from gi.repository import GLib # Already imported above

from fabric.core.fabricator import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.utils.helpers import invoke_repeater
from fabric.widgets.scale import Scale

import modules.icons as icons
import config.data as data
from services.network import NetworkClient

# Setup logger
logger = logging.getLogger(__name__)
# Basic config if not handled elsewhere.
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Example basic config

class MetricsProvider:
    """
    Class responsible for obtaining centralized CPU, memory, disk usage, and battery metrics.
    It updates periodically so that all widgets querying it display the same values.
    """
    def __init__(self):
        self.gpu = []
        self.cpu = 0.0
        self.mem = 0.0
        self.disk = []

        self.bat_percent = 0.0
        self.bat_charging = None

        # GLib process management for GPU update
        self._gpu_process_pid = None
        self._gpu_stdout_fd = -1
        self._gpu_stderr_fd = -1
        self._gpu_timeout_id = None # To track the timeout source

        # Updates every 1 second (1000 milliseconds)
        GLib.timeout_add_seconds(1, self._update)

    def _update(self):
        # Get non-blocking usage percentages (interval=0)
        # The first call may return 0, but subsequent calls will provide consistent values.
        self.cpu = psutil.cpu_percent(interval=0)
        self.mem = psutil.virtual_memory().percent
        self.disk = [psutil.disk_usage(path).percent for path in data.BAR_METRICS_DISKS]

        # Spawn async GPU update only if one is not already running
        if self._gpu_process_pid is None:
            self._spawn_gpu_update()

        battery = psutil.sensors_battery()
        if battery is None:
            self.bat_percent = 0.0
            self.bat_charging = None
        else:
            self.bat_percent = battery.percent
            self.bat_charging = battery.power_plugged

        return True # Keep the GLib timeout running

    # Removed _start_gpu_update_async
    # Removed _run_nvtop_in_thread

    def _spawn_gpu_update(self):
        """Spawns the nvtop process asynchronously using GLib."""
        command = ["nvtop", "-s"]
        flags = (
            GLib.SpawnFlags.DO_NOT_REAP_CHILD |
            GLib.SpawnFlags.SEARCH_PATH |
            GLib.SpawnFlags.STDOUT_PIPE | # Corrected flag name
            GLib.SpawnFlags.STDERR_PIPE # Corrected flag name
        )

        try:
            # Spawn the process and get PID and pipe file descriptors
            (pid, stdin_fd, stdout_fd, stderr_fd) = GLib.spawn_async_with_pipes(
                working_directory=None,
                argv=command,
                envp=None,
                flags=flags,
                child_setup_func=None,
            )

            # Store PID and FDs
            self._gpu_process_pid = pid
            self._gpu_stdout_fd = stdout_fd
            self._gpu_stderr_fd = stderr_fd

            # Close stdin_fd as we don't need it
            os.close(stdin_fd)

            # Add a watch for when the child process exits
            # Pass stdout_fd and stderr_fd as user data to the watch function
            GLib.child_watch_add(pid, self._on_gpu_process_exit, (stdout_fd, stderr_fd))

            # Add a timeout source to kill the process if it takes too long
            self._gpu_timeout_id = GLib.timeout_add_seconds(10, self._on_gpu_timeout, pid) # 10 second timeout

        except GLib.Error as e:
            logger.error(f"Failed to spawn nvtop process: {e.message}")
            self._gpu_process_pid = None
            # Ensure FDs are closed even if spawn failed after opening pipes
            if self._gpu_stdout_fd != -1: os.close(self._gpu_stdout_fd)
            if self._gpu_stderr_fd != -1: os.close(self._gpu_stderr_fd)
            self._gpu_stdout_fd = -1
            self._gpu_stderr_fd = -1
            if self._gpu_timeout_id:
                 GLib.source_remove(self._gpu_timeout_id)
                 self._gpu_timeout_id = None
        except Exception as e:
            logger.error(f"Unexpected error spawning nvtop: {e}")
            self._gpu_process_pid = None
            if self._gpu_stdout_fd != -1: os.close(self._gpu_stdout_fd)
            if self._gpu_stderr_fd != -1: os.close(self._gpu_stderr_fd)
            self._gpu_stdout_fd = -1
            self._gpu_stderr_fd = -1
            if self._gpu_timeout_id:
                 GLib.source_remove(self._gpu_timeout_id)
                 self._gpu_timeout_id = None

    def _on_gpu_process_exit(self, pid, condition, data):
        """Callback executed on the main thread when the nvtop process exits."""
        stdout_fd, stderr_fd = data
        output = ""
        error_output = ""
        error_message = None

        # Remove the timeout source if it's still active
        if self._gpu_timeout_id:
            GLib.source_remove(self._gpu_timeout_id)
            self._gpu_timeout_id = None

        # Read output from pipes
        try:
            output = self._read_pipe(stdout_fd)
            error_output = self._read_pipe(stderr_fd)
        finally:
            # Always close the file descriptors
            if stdout_fd != -1: os.close(stdout_fd)
            if stderr_fd != -1: os.close(stderr_fd)
            self._gpu_stdout_fd = -1
            self._gpu_stderr_fd = -1

        # Check process exit condition and status
        if condition == GLib.ChildWatchFlags.EXITED:
            exit_status = GLib.ProcessTools.get_exit_status(condition)
            if exit_status != 0:
                error_message = f"nvtop command failed with exit code {exit_status}: {error_output.strip()}"
                logger.error(error_message)
        elif condition == GLib.ChildWatchFlags.SIGNALED:
             term_signal = GLib.ProcessTools.get_signal_number(condition)
             error_message = f"nvtop process terminated by signal {term_signal}"
             logger.error(error_message)
        else:
             error_message = f"nvtop process exited with unexpected condition: {condition}"
             logger.error(error_message)


        # Process the output or handle the error
        self._process_gpu_output(output if not error_message else None, error_message)

        # Reset PID to allow spawning a new process in the next update cycle
        self._gpu_process_pid = None

        # GLib.child_watch_add automatically reaps the child process, no need for GLib.spawn_close_pid

    def _on_gpu_timeout(self, pid):
        """Callback executed if the nvtop process times out."""
        logger.error("nvtop command timed out. Attempting to kill process.")
        try:
            # Send SIGTERM to the process
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            logger.error(f"Failed to kill timed-out nvtop process {pid}: {e}")

        # The child_watch will handle cleanup when the process exits after being signaled
        self._gpu_timeout_id = None
        return GLib.SOURCE_REMOVE # Remove the timeout source

    def _read_pipe(self, fd):
        """Reads all data from a file descriptor until EOF."""
        output = b""
        if fd == -1:
            return ""
        try:
            # Read in chunks until EOF
            while True:
                chunk = os.read(fd, 4096) # Read up to 4096 bytes at a time
                if not chunk:
                    break # EOF reached
                output += chunk
        except BlockingIOError:
            # This shouldn't happen with spawn_async_with_pipes after exit, but handle defensively
            logger.warning(f"BlockingIOError while reading pipe {fd}")
        except OSError as e:
            logger.error(f"Error reading pipe {fd}: {e}")
            return "" # Return empty string on read error

        return output.decode('utf-8', errors='replace') # Decode bytes to string


    def _process_gpu_output(self, output, error_message):
        """Callback executed on the main thread to process nvtop output."""
        try:
            if error_message:
                # An error occurred in the process or watch
                logger.error(f"GPU update failed: {error_message}")
                self.gpu = [] # Clear GPU data on error
            elif output:
                # Parse JSON output
                info = json.loads(output)
                # Update the shared GPU data
                # Ensure the data format matches what the widgets expect (list of ints)
                # Handle potential errors during parsing or data extraction
                try:
                    self.gpu = [int(v["gpu_util"][:-1]) for v in info]
                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Failed to parse nvtop data structure: {e}")
                    self.gpu = []
            else:
                 # No output and no specific error message (shouldn't happen with check=True in subprocess,
                 # but possible with GLib spawn if process exits without output)
                 logger.warning("nvtop returned no output.")
                 self.gpu = []

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse nvtop JSON output: {e}")
            self.gpu = []
        except Exception as e:
            logger.error(f"Error processing nvtop output: {e}")
            self.gpu = []

        # The process PID is reset in _on_gpu_process_exit, allowing the next spawn.
        # No need for _gpu_update_running flag here.


    def get_metrics(self):
        """Returns the current state of metrics. GPU might be slightly stale until async update finishes."""
        return (self.cpu, self.mem, self.disk, self.gpu)

    def get_battery(self):
        return (self.bat_percent, self.bat_charging)

    def get_gpu_info(self):
        """Synchronously gets GPU info for initial setup (e.g., counting GPUs).
           Includes a timeout to prevent indefinite blocking."""
        try:
            # This is blocking, used only during initialization of widgets
            # Use text=True for string output
            # Using subprocess.check_output here is acceptable for a blocking init call
            result = subprocess.check_output(["nvtop", "-s"], text=True, timeout=5) # Added timeout
            return json.loads(result)
        except FileNotFoundError:
            logger.warning("nvtop command not found. GPU metrics may not be available.")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"nvtop command failed: {e}")
            return []
        except subprocess.TimeoutExpired:
             logger.error("nvtop command timed out during initial sync call.")
             return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse nvtop JSON output: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting GPU info: {e}")
            return []

# Global instance to share data between both widgets.
shared_provider = MetricsProvider()

class SingularMetric:
    def __init__(self, id, name, icon):
        self.usage = Scale(
            name=f"{id}-usage",
            value=0.25,
            orientation='v',
            inverted=True,
            v_align='fill',
            v_expand=True,
        )

        self.label = Label(
            name=f"{id}-label",
            markup=icon,
        )

        self.box = Box(
            name=f"{id}-box",
            orientation='v',
            spacing=8,
            children=[
                self.usage,
                self.label,
            ]
        )

        self.box.set_tooltip_markup(f"{icon} {name}")

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

        # Only include enabled metrics
        visible = getattr(data, "METRICS_VISIBLE", {'cpu': True, 'ram': True, 'disk': True, 'gpu': True})
        disks = [SingularMetric("disk", f"DISK ({path})" if len(data.BAR_METRICS_DISKS) != 1 else "DISK", icons.disk)
                 for path in data.BAR_METRICS_DISKS] if visible.get('disk', True) else []
        # Use the synchronous get_gpu_info here for initial count
        gpu_info = shared_provider.get_gpu_info()
        gpus = [SingularMetric(f"gpu", f"GPU ({v['device_name']})" if len(gpu_info) != 1 else "GPU", icons.gpu)
                for v in gpu_info] if visible.get('gpu', True) else []

        self.cpu = SingularMetric("cpu", "CPU", icons.cpu) if visible.get('cpu', True) else None
        self.ram = SingularMetric("ram", "RAM", icons.memory) if visible.get('ram', True) else None
        self.disk = disks
        self.gpu = gpus

        self.scales = []
        if self.disk: self.scales.extend([v.box for v in self.disk])
        if self.ram: self.scales.append(self.ram.box)
        if self.cpu: self.scales.append(self.cpu.box)
        if self.gpu: self.scales.extend([v.box for v in self.gpu])

        if self.cpu: self.cpu.usage.set_sensitive(False)
        if self.ram: self.ram.usage.set_sensitive(False)
        for disk in self.disk:
            disk.usage.set_sensitive(False)
        for gpu in self.gpu:
            gpu.usage.set_sensitive(False)

        for x in self.scales:
            self.add(x)

        # Update status periodically
        GLib.timeout_add_seconds(1, self.update_status)

    def update_status(self):
        cpu, mem, disks, gpus = shared_provider.get_metrics()
        # idx = 0 # This variable is not used
        if self.cpu:
            self.cpu.usage.value = cpu / 100.0
        if self.ram:
            self.ram.usage.value = mem / 100.0
        for i, disk in enumerate(self.disk):
            # Ensure index is within bounds for disks list
            if i < len(disks):
                disk.usage.value = disks[i] / 100.0
        for i, gpu in enumerate(self.gpu):
             # Ensure index is within bounds for gpus list
            if i < len(gpus):
                gpu.usage.value = gpus[i] / 100.0
        return True

class SingularMetricSmall:
    def __init__(self, id, name, icon):
        self.name_markup = name
        self.icon_markup = icon

        self.icon = Label(name="metrics-icon", markup=icon)
        self.circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes=id,
            child=self.icon,
        )

        self.level = Label(name="metrics-level", style_classes=id, label="0%")
        self.revealer = Revealer(
            name=f"metrics-{id}-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.level,
            child_revealed=False,
        )

        self.box = Box(
            name=f"metrics-{id}-box",
            orientation="h",
            spacing=0,
            children=[self.circle, self.revealer],
        )

    def markup(self):
        return f"{self.icon_markup} {self.name_markup}" if not data.VERTICAL else f"{self.icon_markup} {self.name_markup}: {self.level.get_label()}"

class MetricsSmall(Button):
    def __init__(self, **kwargs):
        super().__init__(name="metrics-small", **kwargs)

        # Create the main box for metrics widgets
        main_box = Box(
            name="metrics-small",
            spacing=0,
            orientation="h" if not data.VERTICAL else "v",
            visible=True,
            all_visible=True,
        )

        visible = getattr(data, "METRICS_SMALL_VISIBLE", {'cpu': True, 'ram': True, 'disk': True, 'gpu': True})
        disks = [SingularMetricSmall("disk", f"DISK ({path})" if len(data.BAR_METRICS_DISKS) != 1 else "DISK", icons.disk)
                 for path in data.BAR_METRICS_DISKS] if visible.get('disk', True) else []
        # Use the synchronous get_gpu_info here for initial count
        gpu_info = shared_provider.get_gpu_info()
        gpus = [SingularMetricSmall(f"gpu", f"GPU ({v['device_name']})" if len(gpu_info) != 1 else "GPU", icons.gpu)
                for v in gpu_info] if visible.get('gpu', True) else []

        self.cpu = SingularMetricSmall("cpu", "CPU", icons.cpu) if visible.get('cpu', True) else None
        self.ram = SingularMetricSmall("ram", "RAM", icons.memory) if visible.get('ram', True) else None
        self.disk = disks
        self.gpu = gpus

        # Add only enabled metrics
        for disk in self.disk:
            main_box.add(disk.box)
            main_box.add(Box(name="metrics-sep"))
        if self.ram:
            main_box.add(self.ram.box)
            main_box.add(Box(name="metrics-sep"))
        if self.cpu:
            main_box.add(self.cpu.box)
        for gpu in self.gpu:
            main_box.add(Box(name="metrics-sep"))
            main_box.add(gpu.box)

        self.add(main_box)

        # Connect events directly to the button
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

        # Actualización de métricas cada segundo
        GLib.timeout_add_seconds(1, self.update_metrics)

        # Estado inicial de los revealers y variables para la gestión del hover
        self.hide_timer = None
        self.hover_counter = 0

    def _format_percentage(self, value: int) -> str:
        """Formato natural del porcentaje sin forzar ancho fijo."""
        return f"{value}%"

    def on_mouse_enter(self, widget, event):
        if not data.VERTICAL:
            self.hover_counter += 1
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
                self.hide_timer = None
            # Revelar niveles en hover para todas las métricas
            if self.cpu: self.cpu.revealer.set_reveal_child(True)
            if self.ram: self.ram.revealer.set_reveal_child(True)
            for disk in self.disk:
                disk.revealer.set_reveal_child(True)
            for gpu in self.gpu:
                gpu.revealer.set_reveal_child(True)
            return False

    def on_mouse_leave(self, widget, event):
        if not data.VERTICAL:
            if self.hover_counter > 0:
                self.hover_counter -= 1
            if self.hover_counter == 0:
                if self.hide_timer is not None:
                    GLib.source_remove(self.hide_timer)
                self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
            return False

    def hide_revealer(self):
        if not data.VERTICAL:
            if self.cpu: self.cpu.revealer.set_reveal_child(False)
            if self.ram: self.ram.revealer.set_reveal_child(False)
            for disk in self.disk:
                disk.revealer.set_reveal_child(False)
            for gpu in self.gpu:
                gpu.revealer.set_reveal_child(False)
            self.hide_timer = None
            return False

    def update_metrics(self):
        cpu, mem, disks, gpus = shared_provider.get_metrics()
        # idx = 0 # This variable is not used
        if self.cpu:
            self.cpu.circle.set_value(cpu / 100.0)
            self.cpu.level.set_label(self._format_percentage(int(cpu)))
        if self.ram:
            self.ram.circle.set_value(mem / 100.0)
            self.ram.level.set_label(self._format_percentage(int(mem)))
        for i, disk in enumerate(self.disk):
            # Ensure index is within bounds for disks list
            if i < len(disks):
                disk.circle.set_value(disks[i] / 100.0)
                disk.level.set_label(self._format_percentage(int(disks[i])))
        for i, gpu in enumerate(self.gpu):
            # Ensure index is within bounds for gpus list
            if i < len(gpus):
                gpu.circle.set_value(gpus[i] / 100.0)
                gpu.level.set_label(self._format_percentage(int(gpus[i])))

        # Tooltip: only show enabled metrics
        tooltip_metrics = []
        if self.disk: tooltip_metrics.extend(self.disk)
        if self.ram: tooltip_metrics.append(self.ram)
        if self.cpu: tooltip_metrics.append(self.cpu)
        if self.gpu: tooltip_metrics.extend(self.gpu)
        self.set_tooltip_markup((" - " if not data.VERTICAL else "\n").join([v.markup() for v in tooltip_metrics]))

        return True

class Battery(Button):
    def __init__(self, **kwargs):
        super().__init__(name="metrics-small", **kwargs)

        # Create the main box for metrics widgets
        main_box = Box(
            name="metrics-small",
            spacing=0,
            orientation="h",
            visible=True,
            all_visible=True,
        )

        # ------------------ Battery ------------------
        self.bat_icon = Label(name="metrics-icon", markup=icons.battery)
        self.bat_circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes="bat",
            child=self.bat_icon,
        )
        self.bat_level = Label(name="metrics-level", style_classes="bat", label="100%")
        self.bat_revealer = Revealer(
            name="metrics-bat-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.bat_level,
            child_revealed=False,
        )
        self.bat_box = Box(
            name="metrics-bat-box",
            orientation="h",
            spacing=0,
            children=[self.bat_circle, self.bat_revealer],
        )

        # Add the battery widget to the main container
        main_box.add(self.bat_box)

        # Set the main box as the button's child
        self.add(main_box)

        # Connect events directly to the button
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

        # Actualización de la batería cada segundo
        self.batt_fabricator = Fabricator(
            poll_from=lambda v: shared_provider.get_battery(),
            on_changed=lambda f, v: self.update_battery,
            interval=1000,
            stream=False,
            default_value=0
        )
        self.batt_fabricator.changed.connect(self.update_battery)
        GLib.idle_add(self.update_battery, None, shared_provider.get_battery())

        # Estado inicial de los revealers y variables para la gestión del hover
        self.hide_timer = None
        self.hover_counter = 0

    def _format_percentage(self, value: int) -> str:
        """Formato natural del porcentaje sin forzar ancho fijo."""
        return f"{value}%"

    def on_mouse_enter(self, widget, event):
        if not data.VERTICAL:
            self.hover_counter += 1
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
                self.hide_timer = None
            # Revelar niveles en hover para todas las métricas
            self.bat_revealer.set_reveal_child(True)
            return False

    def on_mouse_leave(self, widget, event):
        if not data.VERTICAL:
            if self.hover_counter > 0:
                self.hover_counter -= 1
            if self.hover_counter == 0:
                if self.hide_timer is not None:
                    GLib.source_remove(self.hide_timer)
                self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
            return False

    def hide_revealer(self):
        if not data.VERTICAL:
            self.bat_revealer.set_reveal_child(False)
            self.hide_timer = None
            return False

    def update_battery(self, sender, battery_data):
        value, charging = battery_data
        if value == 0:
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.bat_circle.set_value(value / 100)
        percentage = int(value)
        self.bat_level.set_label(self._format_percentage(percentage))

        # Apply alert styling if battery is low, regardless of charging status
        if percentage <= 15:
            self.bat_icon.add_style_class("alert")
            self.bat_circle.add_style_class("alert")
        else:
            self.bat_icon.remove_style_class("alert")
            self.bat_circle.remove_style_class("alert")

        # Choose the icon based on charging state first, then battery level
        if percentage == 100:
            self.bat_icon.set_markup(icons.battery)
            charging_status = f"{icons.bat_full} Fully Charged"
        elif charging == True:
            self.bat_icon.set_markup(icons.charging)
            charging_status = f"{icons.bat_charging} Charging"
        elif percentage <= 15 and charging == False:
            self.bat_icon.set_markup(icons.alert)
            charging_status = f"{icons.bat_low} Low Battery"
        elif charging == False:
            self.bat_icon.set_markup(icons.discharging)
            charging_status = f"{icons.bat_discharging} Discharging"
        else:
            self.bat_icon.set_markup(icons.battery)
            charging_status = "Battery"

        # Set a descriptive tooltip with battery percentage
        self.set_tooltip_markup(f"{charging_status}" if not data.VERTICAL else f"{charging_status}: {percentage}%")

class NetworkApplet(Button):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar", **kwargs)
        self.download_label = Label(name="download-label", markup="Download: 0 B/s")
        self.network_client = NetworkClient()
        self.upload_label = Label(name="upload-label", markup="Upload: 0 B/s")
        self.wifi_label = Label(name="network-icon-label", markup="WiFi: Unknown")

        self.is_mouse_over = False
        self.downloading = False  # Track if downloading threshold is reached
        self.uploading = False    # Track if uploading threshold is reached

        self.download_icon = Label(name="download-icon-label", markup=icons.download, v_align="center", h_align="center", h_expand=True, v_expand=True)
        self.upload_icon = Label(name="upload-icon-label", markup=icons.upload, v_align="center", h_align="center", h_expand=True, v_expand=True)

        self.download_box = Box(
            children=[self.download_icon, self.download_label],
        )

        self.upload_box = Box(
            children=[self.upload_label, self.upload_icon],
        )

        self.download_revealer = Revealer(child=self.download_box, transition_type = "slide-right" if not data.VERTICAL else "slide-down", child_revealed=False)
        self.upload_revealer = Revealer(child=self.upload_box, transition_type="slide-left" if not data.VERTICAL else "slide-up",child_revealed=False)


        self.children = Box(
            orientation="h" if not data.VERTICAL else "v",
            children=[self.upload_revealer, self.wifi_label, self.download_revealer],
        )

        if data.VERTICAL:
            self.download_label.set_visible(False)
            self.upload_label.set_visible(False)
            self.upload_icon.set_margin_top(4)
            self.download_icon.set_margin_bottom(4)

        self.last_counters = psutil.net_io_counters()
        self.last_time = time.time()
        invoke_repeater(1000, self.update_network)

        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

    def update_network(self):
        current_time = time.time()
        elapsed = current_time - self.last_time
        current_counters = psutil.net_io_counters()
        download_speed = (current_counters.bytes_recv - self.last_counters.bytes_recv) / elapsed
        upload_speed = (current_counters.bytes_sent - self.last_counters.bytes_sent) / elapsed
        download_str = self.format_speed(download_speed)
        upload_str = self.format_speed(upload_speed)
        self.download_label.set_markup(download_str)
        self.upload_label.set_markup(upload_str)

        # Store current network activity state
        self.downloading = (download_speed >= 10e6)
        self.uploading = (upload_speed >= 2e6)

        # Apply urgent styles based on network activity (if not being hovered)
        if not self.is_mouse_over:
            if self.downloading:
                self.download_urgent()
            elif self.uploading:
                self.upload_urgent()
            else:
                self.remove_urgent()

        # Revealer behavior with hover consideration only in horizontal mode
        show_download = self.downloading or (self.is_mouse_over and not data.VERTICAL)
        show_upload = self.uploading or (self.is_mouse_over and not data.VERTICAL)
        self.download_revealer.set_reveal_child(show_download)
        self.upload_revealer.set_reveal_child(show_upload)

        # Check for primary device type (ethernet or wifi)
        primary_device = None
        if self.network_client:
            primary_device = self.network_client.primary_device

        # Create tooltip content based on orientation
        tooltip_base = ""
        tooltip_vertical = ""

        # Handle Ethernet connection
        if primary_device == "wired" and self.network_client.ethernet_device:
            ethernet_state = self.network_client.ethernet_device.internet
            # Horizontal mode ethernet icons
            if ethernet_state == "activated":
                self.wifi_label.set_markup(icons.world)
            elif ethernet_state == "activating":
                self.wifi_label.set_markup(icons.world)
            else:
                self.wifi_label.set_markup(icons.world_off)

            tooltip_base = "Ethernet Connection"
            tooltip_vertical = f"SSID: Ethernet\nUpload: {upload_str}\nDownload: {download_str}"

        # Handle WiFi connection
        elif self.network_client and self.network_client.wifi_device:
            if self.network_client.wifi_device.ssid != "Disconnected":
                strength = self.network_client.wifi_device.strength

                # Only horizontal mode wifi icons based on signal strength
                if strength >= 75:
                    self.wifi_label.set_markup(icons.wifi_3)
                elif strength >= 50:
                    self.wifi_label.set_markup(icons.wifi_2)
                elif strength >= 25:
                    self.wifi_label.set_markup(icons.wifi_1)
                else:
                    self.wifi_label.set_markup(icons.wifi_0)

                tooltip_base = self.network_client.wifi_device.ssid
                tooltip_vertical = f"SSID: {self.network_client.wifi_device.ssid}\nUpload: {upload_str}\nDownload: {download_str}"
            else:
                self.wifi_label.set_markup(icons.world_off)
                tooltip_base = "Disconnected"
                tooltip_vertical = f"SSID: Disconnected\nUpload: {upload_str}\nDownload: {download_str}"
        else:
            self.wifi_label.set_markup(icons.world_off)
            tooltip_base = "Disconnected"
            tooltip_vertical = f"SSID: Disconnected\nUpload: {upload_str}\nDownload: {download_str}"

        # Set the appropriate tooltip based on orientation
        if data.VERTICAL:
            self.set_tooltip_text(tooltip_vertical)
        else:
            self.set_tooltip_text(tooltip_base)

        self.last_counters = current_counters
        self.last_time = current_time
        return True

    def format_speed(self, speed):
        if speed < 1024:
            return f"{speed:.0f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        else:
            return f"{speed / (1024 * 1024):.1f} MB/s"

    def on_mouse_enter(self, *_):
        self.is_mouse_over = True
        if not data.VERTICAL:
            # Just reveal the panels, don't remove urgency styling anymore
            self.download_revealer.set_reveal_child(True)
            self.upload_revealer.set_reveal_child(True)
        return

    def on_mouse_leave(self, *_):
        self.is_mouse_over = False
        if not data.VERTICAL:
            # When mouse leaves, only hide revealers if there's no active download/upload
            self.download_revealer.set_reveal_child(self.downloading)
            self.upload_revealer.set_reveal_child(self.uploading)

            # Restore urgency styling based on current network activity
            if self.downloading:
                self.download_urgent()
            elif self.uploading:
                self.upload_urgent()
            else:
                self.remove_urgent()
        return

    def upload_urgent(self):
        self.add_style_class("upload")
        self.wifi_label.add_style_class("urgent")
        self.upload_label.add_style_class("urgent")
        self.upload_icon.add_style_class("urgent")
        self.download_icon.add_style_class("urgent")
        self.download_label.add_style_class("urgent")
        self.upload_revealer.set_reveal_child(True)
        self.download_revealer.set_reveal_child(self.downloading)
        return

    def download_urgent(self):
        self.add_style_class("download")
        self.wifi_label.add_style_class("urgent")
        self.download_label.add_style_class("urgent")
        self.download_icon.add_style_class("urgent")
        self.upload_icon.add_style_class("urgent")
        self.upload_label.add_style_class("urgent")
        self.download_revealer.set_reveal_child(True)
        self.upload_revealer.set_reveal_child(self.uploading)
        return

    def remove_urgent(self):
        self.remove_style_class("download")
        self.remove_style_class("upload")
        self.wifi_label.remove_style_class("urgent")
        self.download_label.remove_style_class("urgent")
        self.upload_label.remove_style_class("urgent")
        self.download_icon.remove_style_class("urgent")
        self.upload_icon.remove_style_class("urgent")
        return

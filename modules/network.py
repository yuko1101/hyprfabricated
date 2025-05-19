import gi

gi.require_version('Gtk', '3.0')
gi.require_version('NM', '1.0') # Necesario para NM.utils_ssid_to_utf8 si se usa directamente
from fabric.utils import bulk_connect
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label  # Asegúrate que Label está importado
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import NM, GLib, Gtk

import modules.icons as icons  # Para el botón de atrás y potencialmente otros
from services.network import NetworkClient  # El servicio principal de red


class WifiAccessPointSlot(CenterBox):
    # ... (contenido sin cambios) ...
    def __init__(self, ap_data: dict, network_service: NetworkClient, wifi_service, **kwargs):
        super().__init__(name="wifi-ap-slot", **kwargs)
        self.ap_data = ap_data
        self.network_service = network_service
        self.wifi_service = wifi_service # Es network_service.wifi_device

        ssid = ap_data.get("ssid", "SSID Desconocido")
        icon_name = ap_data.get("icon-name", "network-wireless-signal-none-symbolic")

        self.is_active = False
        active_ap_details = ap_data.get("active-ap")
        if active_ap_details and hasattr(active_ap_details, 'get_bssid') and active_ap_details.get_bssid() == ap_data.get("bssid"):
            self.is_active = True
        
        self.ap_icon = Image(icon_name=icon_name, size=24) # Esto se mantiene como Image
        self.ap_label = Label(label=ssid)
        
        self.connect_button = Button(
            name="wifi-connect-button",
            label="Conectado" if self.is_active else "Conectar",
            sensitive=not self.is_active,
            on_clicked=self._on_connect_clicked,
        )

        self.set_start_children([
            Box(spacing=8, children=[
                self.ap_icon,
                self.ap_label,
            ])
        ])
        self.set_end_children([self.connect_button])

    def _on_connect_clicked(self, _):
        if not self.is_active and self.ap_data.get("bssid"):
            self.connect_button.set_label("Conectando...")
            self.connect_button.set_sensitive(False)
            self.network_service.connect_wifi_bssid(self.ap_data["bssid"])

class NetworkConnections(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="network-connections",
            orientation="vertical",
            spacing=8,
            **kwargs,
        )
        self.widgets = kwargs["widgets"]
        self.network_client = NetworkClient()

        self.status_label = Label(label="Inicializando Wi-Fi...", h_expand=True, h_align="center")

        self.back_button = Button(
            name="network-back-button",
            child=Label(name="network-back-label", markup=icons.chevron_left), # Esto ya usa Label
            on_clicked=lambda *_: self.widgets.show_notif()
        )
        
        # Cambiar de Image a Label para usar iconos de modules.icons
        self.wifi_toggle_button_icon = Label(markup=icons.wifi_3) # Usar un icono "on" por defecto si está disponible, o el más fuerte
        self.wifi_toggle_button = Button(
            name="wifi-toggle-button",
            child=self.wifi_toggle_button_icon,
            tooltip_text="Activar/Desactivar Wi-Fi",
            on_clicked=self._toggle_wifi
        )
        
        # Cambiar de Image a Label para usar iconos de modules.icons
        self.refresh_button_icon = Label(markup=icons.reload) # Usar el icono de recargar
        self.refresh_button = Button(
            name="network-refresh-button",
            child=self.refresh_button_icon,
            tooltip_text="Buscar redes Wi-Fi",
            on_clicked=self._refresh_access_points
        )

        header_box = CenterBox(
            name="network-header",
            start_children=[self.back_button],
            center_children=[Label(name="network-title", label="Redes Wi-Fi")],
            end_children=[Box(orientation="horizontal", spacing=4, children=[self.wifi_toggle_button, self.refresh_button])]
        )

        self.ap_list_box = Box(orientation="vertical", spacing=4)
        scrolled_window = ScrolledWindow(
            name="network-ap-scrolled-window",
            child=self.ap_list_box,
            v_expand=True,
            h_expand=True,
        )

        scrolled_window.set_propagate_natural_height(False)

        self.add(header_box)
        self.add(self.status_label)
        self.add(scrolled_window)

        self.network_client.connect("device-ready", self._on_device_ready)
        self.wifi_toggle_button.set_sensitive(False)
        self.refresh_button.set_sensitive(False)

    def _on_device_ready(self, _client):
        # ... (contenido sin cambios) ...
        if self.network_client.wifi_device:
            self.network_client.wifi_device.connect("changed", self._load_access_points)
            self.network_client.wifi_device.connect("notify::enabled", self._update_wifi_status_ui)
            self._update_wifi_status_ui() 
            if self.network_client.wifi_device.enabled:
                self._load_access_points() 
            else:
                self.status_label.set_label("Wi-Fi desactivado.")
                self.status_label.set_visible(True)
        else:
            self.status_label.set_label("Dispositivo Wi-Fi no disponible.")
            self.status_label.set_visible(True)
            self.wifi_toggle_button.set_sensitive(False)
            self.refresh_button.set_sensitive(False)


    def _update_wifi_status_ui(self, *args):
        if self.network_client.wifi_device:
            enabled = self.network_client.wifi_device.enabled
            self.wifi_toggle_button.set_sensitive(True)
            self.refresh_button.set_sensitive(enabled)
            
            if enabled:
                # Actualizar markup del Label
                self.wifi_toggle_button_icon.set_markup(icons.wifi_3) # Icono para Wi-Fi encendido (ej. señal completa)
            else:
                # Actualizar markup del Label
                self.wifi_toggle_button_icon.set_markup(icons.wifi_off) # Icono para Wi-Fi apagado
                self.status_label.set_label("Wi-Fi desactivado.")
                self.status_label.set_visible(True)
                self._clear_ap_list()
            
            if enabled and not self.ap_list_box.get_children():
                 GLib.idle_add(self._refresh_access_points)
        else:
            self.wifi_toggle_button.set_sensitive(False)
            self.refresh_button.set_sensitive(False)

    # ... (resto de los métodos _toggle_wifi, _refresh_access_points, _clear_ap_list, _load_access_points sin cambios) ...
    def _toggle_wifi(self, _):
        if self.network_client.wifi_device:
            self.network_client.wifi_device.toggle_wifi()

    def _refresh_access_points(self, _=None): 
        if self.network_client.wifi_device and self.network_client.wifi_device.enabled:
            self.status_label.set_label("Buscando redes Wi-Fi...")
            self.status_label.set_visible(True)
            self._clear_ap_list() 
            self.network_client.wifi_device.scan() 
        return False 

    def _clear_ap_list(self):
        for child in self.ap_list_box.get_children():
            child.destroy()

    def _load_access_points(self, *args):
        if not self.network_client.wifi_device or not self.network_client.wifi_device.enabled:
            self._clear_ap_list()
            self.status_label.set_label("Wi-Fi desactivado.")
            self.status_label.set_visible(True)
            return

        self._clear_ap_list()
        
        access_points = self.network_client.wifi_device.access_points
        
        if not access_points:
            self.status_label.set_label("No se encontraron redes Wi-Fi.")
            self.status_label.set_visible(True)
        else:
            self.status_label.set_visible(False) 
            sorted_aps = sorted(access_points, key=lambda x: x.get("strength", 0), reverse=True)
            for ap_data in sorted_aps:
                slot = WifiAccessPointSlot(ap_data, self.network_client, self.network_client.wifi_device)
                self.ap_list_box.add(slot)
        self.ap_list_box.show_all()

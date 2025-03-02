import os
from gi.repository import GdkPixbuf, GLib, Gtk
from loguru import logger
from widgets.rounded_image import CustomImage
from fabric.notifications.service import (
    Notification,
    NotificationAction,
    Notifications,
    NotificationCloseReason,
)
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
import modules.icons as icons
from datetime import datetime, timedelta

# Directorio de caché
CACHE_DIR = os.path.expanduser("~/.cache/ax-shell")

def cache_notification_pixbuf(notification):
    """Guarda el pixbuf de la notificación en el directorio de caché si existe."""
    if notification.image_pixbuf:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = os.path.join(CACHE_DIR, f"notification_{notification.id}.png")
        try:
            notification.image_pixbuf.savev(cache_file, "png", [], [])
            notification.cached_image_path = cache_file
        except Exception as e:
            logger.error(f"Error al cachear la imagen: {e}")

class ActionButton(Button):
    def __init__(self, action: NotificationAction, index: int, total: int, notification_box):
        super().__init__(
            name="action-button",
            h_expand=True,
            on_clicked=self.on_clicked,
            child=Label(name="button-label", label=action.label),
        )
        self.action = action
        self.notification_box = notification_box
        style_class = (
            "start-action" if index == 0
            else "end-action" if index == total - 1
            else "middle-action"
        )
        self.add_style_class(style_class)
        self.connect("enter-notify-event", lambda *_: notification_box.hover_button(self))
        self.connect("leave-notify-event", lambda *_: notification_box.unhover_button(self))

    def on_clicked(self, *_):
        self.action.invoke()
        self.action.parent.close("dismissed-by-user")

class NotificationBox(Box):
    def __init__(self, notification: Notification, timeout_ms=5000, **kwargs):
        super().__init__(
            name="notification-box",
            orientation="v",
            h_align="fill",
            h_expand=True,
            children=[
                self.create_content(notification),
                self.create_action_buttons(notification),
            ],
        )
        self.notification = notification
        self.timeout_ms = timeout_ms
        self._timeout_id = None
        self._container = None
        self.start_timeout()
        
        self.connect("enter-notify-event", self.on_hover_enter)
        self.connect("leave-notify-event", self.on_hover_leave)

        self._destroyed = False

    def set_container(self, container):
        self._container = container

    def get_container(self):
        return self._container

    def create_header(self, notification):
        app_icon = (
            Image(
                name="notification-icon",
                image_file=notification.app_icon[7:],
                size=24,
            ) if "file://" in notification.app_icon else
            Image(
                name="notification-icon",
                icon_name="dialog-information-symbolic" or notification.app_icon,
                icon_size=24,
            )
        )

        return CenterBox(
            name="notification-title",
            start_children=[
                Box(
                    spacing=4,
                    children=[
                        app_icon,
                        Label(
                            notification.app_name,
                            name="notification-app-name",
                            h_align="start"
                        )
                    ]
                )
            ],
            end_children=[self.create_close_button()]
        )

    def create_content(self, notification):
        # En la notificación activa se utiliza el pixbuf original
        pixbuf = (notification.image_pixbuf.scale_simple(
                        48, 48, GdkPixbuf.InterpType.BILINEAR
                    ) if notification.image_pixbuf else 
                    self.get_pixbuf(notification.app_icon, 48, 48))
        return Box(
            name="notification-content",
            spacing=8,
            children=[
                Box(
                    name="notification-image",
                    children=CustomImage(pixbuf=pixbuf),
                ),
                Box(
                    name="notification-text",
                    orientation="v",
                    v_align="center",
                    children=[
                        Box(
                            name="notification-summary-box",
                            orientation="h",
                            children=[
                                Label(
                                    name="notification-summary",
                                    markup=notification.summary,
                                    h_align="start",
                                    ellipsization="end",
                                ),
                                Label(
                                    name="notification-app-name",
                                    markup=" | " + notification.app_name,
                                    h_align="start",
                                    ellipsization="end",
                                ),
                            ],
                        ),
                        Label(
                            markup=notification.body,
                            h_align="start",
                            ellipsization="end",
                        ) if notification.body else Box(),
                    ],
                ),
                Box(h_expand=True),
                Box(
                    orientation="v",
                    children=[
                        self.create_close_button(),
                        Box(v_expand=True),
                    ],
                ),
            ],
        )

    def get_pixbuf(self, icon_path, width, height):
        if icon_path.startswith("file://"):
            icon_path = icon_path[7:]
        if not os.path.exists(icon_path):
            logger.warning(f"Icon path does not exist: {icon_path}")
            return None
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
            return pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
        except Exception as e:
            logger.error(f"Failed to load or scale icon: {e}")
            return None

    def create_action_buttons(self, notification):
        return Box(
            name="notification-action-buttons",
            spacing=4,
            h_expand=True,
            children=[
                ActionButton(action, i, len(notification.actions), self)
                for i, action in enumerate(notification.actions)
            ],
        )

    def create_close_button(self):
        close_button = Button(
            name="notif-close-button",
            child=Label(name="notif-close-label", markup=icons.cancel),
            on_clicked=lambda *_: self.notification.close("dismissed-by-user"),
        )
        close_button.connect("enter-notify-event", lambda *_: self.hover_button(close_button))
        close_button.connect("leave-notify-event", lambda *_: self.unhover_button(close_button))
        return close_button

    def on_hover_enter(self, *args):
        if self._container:
            self._container.pause_and_reset_all_timeouts()
            
    def on_hover_leave(self, *args):
        if self._container:
            self._container.resume_all_timeouts()

    def start_timeout(self):
        self.stop_timeout()
        self._timeout_id = GLib.timeout_add(self.timeout_ms, self.close_notification)

    def stop_timeout(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

    def close_notification(self):
        if not self._destroyed:
            self.notification.close("expired")
            self.stop_timeout()
        return False

    def destroy(self):
        self._destroyed = True
        self.stop_timeout()
        super().destroy()

    def hover_button(self, button):
        if self._container:
            self._container.pause_and_reset_all_timeouts()

    def unhover_button(self, button):
        if self._container:
            self._container.resume_all_timeouts()

class NotificationHistory(ScrolledWindow):
    def __init__(self, **kwargs):
        super().__init__(
            name="notification-history",
            orientation="v",
            min_content_size=(-1, -1),
            max_content_size=(-1, -1),
        )

        self.notch = kwargs["notch"]

        self.notifications_list = Box(
            name="notifications-list",
            orientation="v",
            spacing=4,
        )
        
        self.add(self.notifications_list)

    def update_last_separator(self):
        children = self.notifications_list.get_children()
        for child in children:
            separator = [c for c in child.get_children() if c.get_name() == "notification-separator"]
            if separator:
                separator[0].set_visible(child != children[-1])

    def get_cached_pixbuf(self, notification, width, height):
        # Si la notificación tiene imagen cacheada, se carga desde allí
        if hasattr(notification, "cached_image_path") and os.path.exists(notification.cached_image_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(notification.cached_image_path)
                return pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
            except Exception as e:
                logger.error(f"Error al cargar la imagen cacheada: {e}")
        # Fallback: cargar desde el icono original
        return self.get_pixbuf(notification.app_icon, width, height)

    def add_notification(self, notification_box):
        if len(self.notifications_list.get_children()) >= 50:
            oldest_notification = self.notifications_list.get_children()[0]
            self.notifications_list.remove(oldest_notification)

        def on_container_destroy(container):
            if hasattr(container, "_timestamp_timer_id") and container._timestamp_timer_id:
                GLib.source_remove(container._timestamp_timer_id)
            # Eliminar el archivo cacheado si existe
            if hasattr(container, "notification"):
                notif = container.notification
                if hasattr(notif, "cached_image_path") and os.path.exists(notif.cached_image_path):
                    try:
                        os.remove(notif.cached_image_path)
                    except Exception as e:
                        logger.error(f"Error al eliminar la imagen cacheada: {e}")
            container.destroy()
            GLib.idle_add(self.update_separators)

        container = Box(
            name="notification-container",
            orientation="v",
            h_align="fill",
            h_expand=True,
        )
        container.arrival_time = datetime.now()

        def compute_time_label(arrival_time):
            now = datetime.now()
            if arrival_time.date() != now.date():
                if arrival_time.date() == (now - timedelta(days=1)).date():
                    return " | Yesterday " + arrival_time.strftime("%H:%M")
                else:
                    return arrival_time.strftime("| %d/%m/%Y %H:%M")
            delta = now - arrival_time
            seconds = delta.total_seconds()
            if seconds < 60:
                return " | Now"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                return f" | {minutes} min" if minutes == 1 else f" | {minutes} mins"
            else:
                return arrival_time.strftime(" | %H:%M")

        time_label = Label(name="notification-timestamp", markup=compute_time_label(container.arrival_time))

        # Se usa la imagen cacheada para el historial
        content_box = Box(
            name="notification-content",
            spacing=8,
            children=[
                Box(
                    name="notification-image",
                    children=[
                        CustomImage(
                            pixbuf=self.get_cached_pixbuf(notification_box.notification, 48, 48)
                        )
                    ]
                ),
                Box(
                    name="notification-text",
                    orientation="v",
                    v_align="center",
                    h_expand=True,
                    children=[
                        Box(
                            name="notification-summary-box",
                            orientation="h",
                            children=[
                                Label(
                                    name="notification-summary",
                                    markup=notification_box.notification.summary,
                                    h_align="start",
                                    ellipsization="end",
                                ),
                                Label(
                                    name="notification-app-name",
                                    markup=f" | {notification_box.notification.app_name}",
                                    h_align="start",
                                    ellipsization="end",
                                ),
                                time_label,
                            ],
                        ),
                        Label(
                            name="notification-body",
                            markup=notification_box.notification.body,
                            h_align="start",
                            ellipsization="end",
                        ) if notification_box.notification.body else Box(),
                    ],
                ),
                Box(
                    orientation="v",
                    children=[
                        Button(
                            name="notif-close-button",
                            child=Label(name="notif-close-label", markup=icons.cancel),
                            on_clicked=lambda *_: on_container_destroy(container),
                        ),
                        Box(v_expand=True),
                    ],
                ),
            ],
        )

        def update_timestamp():
            time_label.set_markup(compute_time_label(container.arrival_time))
            return True

        container._timestamp_timer_id = GLib.timeout_add_seconds(10, update_timestamp)
        # Guardamos la notificación en el contenedor para poder acceder a ella luego
        container.notification = notification_box.notification
        hist_box = Box(
            name="notification-box-hist",
            orientation="v",
            h_align="fill",
            h_expand=True,
        )
        hist_box.add(content_box)
        content_box.get_children()[2].get_children()[0].connect(
            "clicked", 
            lambda *_: on_container_destroy(container)
        )
        container.add(hist_box)
        container.add(Box(name="notification-separator"))
        self.notifications_list.pack_start(container, False, False, 0)
        self.update_separators()
        self.show_all()

    def get_pixbuf(self, icon_path, width, height):
        if icon_path.startswith("file://"):
            icon_path = icon_path[7:]
        if not os.path.exists(icon_path):
            logger.warning(f"Icon path does not exist: {icon_path}")
            return None
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
            return pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
        except Exception as e:
            logger.error(f"Failed to load or scale icon: {e}")
            return None

    def update_separators(self):
        children = self.notifications_list.get_children()
        for child in children:
            for widget in child.get_children():
                if widget.get_name() == "notification-separator":
                    child.remove(widget)
        for i, child in enumerate(children):
            if i < len(children) - 1:
                separator = Box(name="notification-separator")
                child.add(separator)

class NotificationContainer(Box):
    def __init__(self, **kwargs):
        super().__init__(name="notification", orientation="v", spacing=4)
        self.notch = kwargs["notch"]
        self._server = Notifications()
        self._server.connect("notification-added", self.on_new_notification)
        self._pending_removal = False
        self._is_destroying = False

        self.history = NotificationHistory(notch=self.notch)
        
        self.stack = Gtk.Stack(
            name="notification-stack",
            transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
            transition_duration=200,
            visible=True,
        )
        
        self.stack_box = Box(
            name="notification-stack-box",
            h_align="center",
            h_expand=False,
            children=[self.stack]
        )
        
        self.navigation = Box(
            name="notification-navigation",
            spacing=4,
            h_align="center"
        )
        
        self.prev_button = Button(
            name="nav-button",
            child=Label(name="nav-button-label", markup=icons.chevron_left),
            on_clicked=self.show_previous,
        )
        
        self.close_all_button = Button(
            name="nav-button",
            child=Label(name="nav-button-label", markup=icons.cancel),
            on_clicked=self.close_all_notifications,
        )
        
        self.next_button = Button(
            name="nav-button", 
            child=Label(name="nav-button-label", markup=icons.chevron_right),
            on_clicked=self.show_next,
        )
        
        for button in [self.prev_button, self.close_all_button, self.next_button]:
            button.connect("enter-notify-event", lambda *_: self.pause_and_reset_all_timeouts())
            button.connect("leave-notify-event", lambda *_: self.resume_all_timeouts())
        
        self.navigation.add(self.prev_button)
        self.navigation.add(self.close_all_button)
        self.close_all_button.get_child().add_style_class("close")
        self.navigation.add(self.next_button)
        
        self.notification_box = Box(
            orientation="v",
            spacing=4,
            children=[self.stack_box, self.navigation]
        )
        
        self.notifications = []
        self.current_index = 0
        
        self.update_navigation_buttons()

        self._destroyed_notifications = set()

    def show_previous(self, *args):
        if self.current_index > 0:
            self.current_index -= 1
            self.stack.set_visible_child(self.notifications[self.current_index])
            self.update_navigation_buttons()

    def show_next(self, *args):
        if self.current_index < len(self.notifications) - 1:
            self.current_index += 1
            self.stack.set_visible_child(self.notifications[self.current_index])
            self.update_navigation_buttons()

    def update_navigation_buttons(self):
        self.prev_button.set_sensitive(self.current_index > 0)
        self.next_button.set_sensitive(self.current_index < len(self.notifications) - 1)
        self.navigation.set_visible(len(self.notifications) > 1)

    def on_new_notification(self, fabric_notif, id):
        notification = fabric_notif.get_notification_from_id(id)
        # Cachear la imagen (si existe) para evitar problemas al mover al historial
        if notification.image_pixbuf:
            cache_notification_pixbuf(notification)
        new_box = NotificationBox(notification)
        new_box.set_container(self)
        notification.connect("closed", self.on_notification_closed)
        
        # Limitar a 5 notificaciones activas
        while len(self.notifications) >= 5:
            oldest_notification = self.notifications[0]
            self.notch.notification_history.add_notification(oldest_notification)
            self.stack.remove(oldest_notification)
            self.notifications.pop(0)
            if self.current_index > 0:
                self.current_index -= 1
        
        self.stack.add_named(new_box, str(id))
        self.notifications.append(new_box)
        self.current_index = len(self.notifications) - 1
        self.stack.set_visible_child(new_box)
        
        for notification_box in self.notifications:
            notification_box.start_timeout()
        
        if len(self.notifications) == 1:
            if not self.notification_box.get_parent():
                self.notch.notification_revealer.add(self.notification_box)
            
        self.notch.notification_revealer.show_all()
        self.notch.notification_revealer.set_reveal_child(True)
        self.update_navigation_buttons()

    def on_notification_closed(self, notification, reason):
        if self._is_destroying:
            return
            
        if notification.id in self._destroyed_notifications:
            return
        
        self._destroyed_notifications.add(notification.id)
        
        try:
            logger.info(f"Notification {notification.id} closing with reason: {reason}")
            
            notif_to_remove = None
            for i, notif_box in enumerate(self.notifications):
                if notif_box.notification.id == notification.id:
                    notif_to_remove = (i, notif_box)
                    break
            
            if not notif_to_remove:
                return
            
            i, notif_box = notif_to_remove

            reason_str = str(reason)
            if (reason_str == "NotificationCloseReason.EXPIRED" or 
                reason_str == "NotificationCloseReason.CLOSED" or
                reason_str == "NotificationCloseReason.UNDEFINED"):
                logger.info(f"Adding notification {notification.id} to history")
                self.notch.notification_history.add_notification(notif_box)
            
            if len(self.notifications) == 1:
                self._is_destroying = True
                self.notch.notification_revealer.set_reveal_child(False)
                GLib.timeout_add(
                    self.notch.notification_revealer.get_transition_duration(),
                    self._destroy_container
                )
                return
            
            new_index = i
            if i == self.current_index:
                new_index = max(0, i - 1)
            elif i < self.current_index:
                new_index = self.current_index - 1
            
            next_notification = self.notifications[new_index if new_index < i else i]
            self.stack.set_visible_child(next_notification)
            
            if notif_box.get_parent() == self.stack:
                self.stack.remove(notif_box)
            self.notifications.remove(notif_box)
            
            self.current_index = new_index
            self.update_navigation_buttons()

        except Exception as e:
            logger.error(f"Error al cerrar notificación: {e}")
            
        logger.info(f"Notification {notification.id} closed with reason: {reason}")

    def _destroy_container(self):
        try:
            self.notifications.clear()
            self._destroyed_notifications.clear()
            for child in self.stack.get_children():
                self.stack.remove(child)
            self.current_index = 0
            self.navigation.set_visible(False)
            if self.notification_box.get_parent():
                self.notification_box.get_parent().remove(self.notification_box)
            
        except Exception as e:
            logger.error(f"Error al limpiar el contenedor: {e}")
        finally:
            self._is_destroying = False
            return False

    def pause_and_reset_all_timeouts(self):
        if self._is_destroying:
            return
        for notification in self.notifications[:]:
            try:
                if not notification._destroyed and notification.get_parent():
                    notification.stop_timeout()
            except Exception as e:
                logger.error(f"Error al pausar timeout: {e}")

    def resume_all_timeouts(self):
        if self._is_destroying:
            return
        for notification in self.notifications[:]:
            try:
                if not notification._destroyed and notification.get_parent():
                    notification.start_timeout()
            except Exception as e:
                logger.error(f"Error al reanudar timeout: {e}")

    def close_all_notifications(self, *args):
        notifications_to_close = self.notifications.copy()
        for notification_box in notifications_to_close:
            notification_box.notification.close("dismissed-by-user")

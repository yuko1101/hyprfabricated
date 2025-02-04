import gi
import json
import os
from pathlib import Path

from fabric.widgets.label import Label
import modules.icons as icons

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject

class InlineEditor(Gtk.Box):
    __gsignals__ = {
        'confirmed': (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'canceled': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, initial_text=""):
        super().__init__(spacing=4)
        self.entry = Gtk.Entry()
        self.entry.set_text(initial_text)
        self.entry.connect("activate", self.on_confirm)
        self.entry.connect("key-press-event", self.on_key_press)
        
        confirm_btn = Gtk.Button.new_from_icon_name("object-select-symbolic", Gtk.IconSize.BUTTON)
        confirm_btn.connect("clicked", self.on_confirm)
        confirm_btn.get_style_context().add_class("flat")
        
        cancel_btn = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        cancel_btn.connect("clicked", self.on_cancel)
        cancel_btn.get_style_context().add_class("flat")

        self.pack_start(self.entry, True, True, 0)
        self.pack_start(confirm_btn, False, False, 0)
        self.pack_start(cancel_btn, False, False, 0)
        self.show_all()

    def on_confirm(self, widget):
        text = self.entry.get_text().strip()
        if text:
            self.emit('confirmed', text)
        else:
            self.emit('canceled')

    def on_cancel(self, widget):
        self.emit('canceled')

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.emit('canceled')
            return True
        return False

class KanbanNote(Gtk.EventBox):
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, text):
        super().__init__()
        self.text = text
        self.setup_ui()
        self.setup_dnd()
        self.connect("button-press-event", self.on_double_click)

    def setup_ui(self):
        self.box = Gtk.Box(name="kanban-note", spacing=4)
        self.label = Gtk.Label(label=self.text)
        self.label.set_line_wrap(True)
        # Wrap long lines
        self.label.set_line_wrap_mode(Gtk.WrapMode.WORD)
        
        self.delete_btn = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        self.delete_btn.get_style_context().add_class("flat")
        self.delete_btn.connect("clicked", self.on_delete_clicked)
        
        self.box.pack_start(self.label, True, True, 0)
        self.box.pack_start(self.delete_btn, False, False, 0)
        self.add(self.box)
        self.show_all()

    def setup_dnd(self):
        self.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new('UTF8_STRING', Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.MOVE
        )
        
        self.connect("drag-data-get", self.on_drag_data_get)
        self.connect("drag-data-delete", self.on_drag_data_delete)

    def on_drag_data_get(self, widget, drag_context, data, info, time):
        data.set_text(self.label.get_text(), -1)

    def on_drag_data_delete(self, widget, drag_context):
        self.get_parent().destroy()

    def on_delete_clicked(self, button):
        self.get_parent().destroy()

    def on_double_click(self, widget, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            self.start_edit()
            return True

    def start_edit(self):
        row = self.get_parent()
        editor = InlineEditor(self.label.get_text())
        
        def on_confirmed(editor, text):
            self.label.set_text(text)
            row.remove(editor)
            row.add(self)
            row.show_all()
            self.emit('changed')  # Emit changed signal after edit

        def on_canceled(editor):
            row.remove(editor)
            row.add(self)
            row.show_all()

        editor.connect('confirmed', on_confirmed)
        editor.connect('canceled', on_canceled)
        
        row.remove(self)
        row.add(editor)
        editor.entry.grab_focus()
        row.show_all()

class KanbanColumn(Gtk.Frame):
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, title):
        super().__init__(name="kanban-column")
        self.title = title
        self.setup_ui()
        self.setup_dnd()
        self.set_hexpand(True)
        self.set_vexpand(True)

    def setup_ui(self):
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        header = Label(name="column-header", label=self.title)
        self.box.pack_start(header, False, False, 0)
        
        self.add_btn = Gtk.Button(name="add-btn", child=Label(name="add-note", markup=icons.add))
        self.add_btn.connect("clicked", self.on_add_clicked)
        
        scrolled = Gtk.ScrolledWindow(name="kanban-scroll")
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        scrolled.set_vexpand(True)
        
        self.box.pack_start(scrolled, True, True, 0)
        self.box.pack_start(self.add_btn, False, False, 0)
        self.add(self.box)
        self.show_all()

    def setup_dnd(self):
        self.listbox.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [Gtk.TargetEntry.new('UTF8_STRING', Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.MOVE
        )
        
        self.listbox.connect("drag-data-received", self.on_drag_data_received)
        self.listbox.connect("drag-motion", self.on_drag_motion)
        self.listbox.connect("drag-leave", self.on_drag_leave)

    def on_add_clicked(self, button):
        editor = InlineEditor()
        row = Gtk.ListBoxRow()
        row.add(editor)
        self.listbox.add(row)
        self.listbox.show_all()
        editor.entry.grab_focus()

        def on_confirmed(editor, text):
            note = KanbanNote(text)
            note.connect('changed', lambda x: self.emit('changed'))
            row.remove(editor)
            row.add(note)
            self.listbox.show_all()
            self.emit('changed')  # Emit on add

        def on_canceled(editor):
            row.destroy()

        editor.connect('confirmed', on_confirmed)
        editor.connect('canceled', on_canceled)

    def add_note(self, text, suppress_signal=False):
        note = KanbanNote(text)
        note.connect('changed', lambda x: self.emit('changed'))
        row = Gtk.ListBoxRow()
        row.add(note)
        row.connect('destroy', lambda x: self.emit('changed'))
        self.listbox.add(row)
        self.listbox.show_all()
        if not suppress_signal:
            self.emit('changed')

    def get_notes(self):
        return [
            row.get_children()[0].label.get_text()
            for row in self.listbox.get_children()
            if isinstance(row.get_children()[0], KanbanNote)
        ]

    def clear_notes(self, suppress_signal=False):
        for row in self.listbox.get_children():
            row.destroy()
        if not suppress_signal:
            self.emit('changed')

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        text = data.get_text()
        if text:
            row = self.listbox.get_row_at_y(y)
            new_note = KanbanNote(text)
            new_note.connect('changed', lambda x: self.emit('changed'))
            new_row = Gtk.ListBoxRow()
            new_row.add(new_note)
            new_row.connect('destroy', lambda x: self.emit('changed'))
            
            if row:
                self.listbox.insert(new_row, row.get_index())
            else:
                self.listbox.add(new_row)
            
            self.listbox.show_all()
            drag_context.finish(True, False, time)
            self.emit('changed')  # Emit on move

    def on_drag_motion(self, widget, drag_context, x, y, time):
        Gdk.drag_status(drag_context, Gdk.DragAction.MOVE, time)
        return True

    def on_drag_leave(self, widget, drag_context, time):
        widget.get_parent().get_parent().drag_unhighlight()

class Kanban(Gtk.Box):
    STATE_FILE = Path(os.path.expanduser("~/.kanban.json"))

    def __init__(self):
        super().__init__(name="kanban")
        
        self.grid = Gtk.Grid(column_spacing=4)
        self.grid.set_vexpand(True)
        self.add(self.grid)
        
        self.columns = [
            KanbanColumn("To Do"),
            KanbanColumn("In Progress"),
            KanbanColumn("Done")
        ]
        
        for i, column in enumerate(self.columns):
            self.grid.attach(column, i, 0, 1, 1)
            column.connect('changed', lambda x: self.save_state())
        
        self.load_state()
        self.show_all()

    def save_state(self):
        state = {
            "columns": [
                {"title": col.title, "notes": col.get_notes()}
                for col in self.columns
            ]
        }
        try:
            with open(self.STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")

    def load_state(self):
        try:
            with open(self.STATE_FILE, "r") as f:
                state = json.load(f)
                for col_data in state["columns"]:
                    for column in self.columns:
                        if column.title == col_data["title"]:
                            column.clear_notes(suppress_signal=True)
                            for note_text in col_data["notes"]:
                                column.add_note(note_text, suppress_signal=True)
                            break
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error loading state: {e}")

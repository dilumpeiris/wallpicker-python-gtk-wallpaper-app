import os
import sys
import gi
import subprocess
from threading import Thread

# pyright: reportAttributeAccessIssue=false
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk

gi.require_version("Gtk", "4.0")

ROOT_DIRECTORY = os.path.expanduser("~/Pictures/wallpapers")
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


class FStrcut:
    def __init__(self, root_path):
        if not os.path.exists(root_path):
            print(f"ERROR: Directory does not exist: {root_path}")
            return
        self.root_path = root_path

    def get_root_folders(self):
        root_list = [
            d
            for d in sorted(os.listdir(self.root_path))
            if os.path.isdir(os.path.join(self.root_path, d)) and not d.startswith(".")
        ]
        return root_list

    def get_folder_images(self, folder):
        if not os.path.exists(folder):
            return []
        images = [
            i
            for i in sorted(os.listdir(folder))
            if os.path.splitext(i)[1].lower() in SUPPORTED
        ]
        return images


class ImageRow(Gtk.Box):
    def __init__(self, filepath, filename, thumb_w, thumb_h):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.filepath = filepath

        self.set_hexpand(True)
        self.set_halign(Gtk.Align.CENTER)
        self.set_margin_top(14)
        self.set_margin_bottom(14)

        self.picture = Gtk.Picture()
        # self.picture.set_size_request(thumb_w, thumb_h)

        self.picture.set_can_shrink(False)
        self.picture.set_content_fit(Gtk.ContentFit.COVER)

        base_name = os.path.splitext(filename)[0]
        self.label = Gtk.Label(label=base_name)
        self.label.set_ellipsize(3)
        self.label.set_halign(Gtk.Align.START)

        self.append(self.picture)
        self.append(self.label)

        gesture = Gtk.GestureClick()
        gesture.connect("pressed", self.on_row_clicked)
        self.add_controller(gesture)

        Thread(
            target=self._load_thumb, args=(filepath, thumb_w, thumb_h), daemon=True
        ).start()

    def _load_thumb(self, filepath, thumb_w, thumb_h):
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filepath, thumb_w, thumb_h, False
            )

            texture = Gdk.Texture.new_for_pixbuf(pb)

            GLib.idle_add(self.picture.set_paintable, texture)

        except Exception as e:
            print(f"Error compiling thumbnail graphics for {filepath}: {e}")

    def on_row_clicked(self, gesture, n_press, x, y):
        try:
            print(f"Applying wallpaper via swww: {self.filepath}")
            subprocess.Popen(["swww", "img", self.filepath])
        except Exception as e:
            print(f"Failed to execute swww system call: {e}")


class MyScrollWindow(Gtk.ScrolledWindow):
    def __init__(self):
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.list_box.set_hexpand(True)

        self.set_child(self.list_box)

        self.selected_folder = ""
        self.current_width = 0

        self.running_for_the_first_time = True

    def load_images(self, folder_name):

        self.selected_folder = folder_name
        folder_structure = FStrcut(ROOT_DIRECTORY)

        # Remove every child and rebuild
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)

        folder_path = os.path.join(ROOT_DIRECTORY, folder_name)
        images = folder_structure.get_folder_images(folder_path)

        print(f"Loading {len(images)} wallpaper images from folder: '{folder_name}'")

        for filename in images:
            filepath = os.path.join(folder_path, filename)
            row = ImageRow(
                filepath, filename, self.current_width, self.current_width * 0.6
            )
            self.list_box.append(row)

    def do_size_allocate(self, width, height, baseline):
        Gtk.ScrolledWindow.do_size_allocate(self, width, height, baseline)

        print(f"Successfully allocated width: {width}")
        self.current_width = width

        if self.running_for_the_first_time:
            self.load_images(self.selected_folder)
            self.running_for_the_first_time = False


def on_activate(app):
    print("App activated successfully!")

    win = Gtk.ApplicationWindow(application=app)
    win.set_title("WallPicker")

    folder_structure = FStrcut(ROOT_DIRECTORY)
    root_folders = folder_structure.get_root_folders()

    if not root_folders:
        string_list = Gtk.StringList.new(["No folders Found"])
    else:
        string_list = Gtk.StringList.new(folder_structure.get_root_folders())

    dropdown = Gtk.DropDown.new(model=string_list)
    dropdown.set_hexpand(True)
    dropdown.set_size_request(-1, 40)

    scroll_window = MyScrollWindow()

    def on_dropdown_changed(dropdown, pspec):
        selected_item = dropdown.get_selected_item()

        if selected_item:
            folder = selected_item.get_string()
            if folder and folder != "No folders found!":
                scroll_window.load_images(folder)

    dropdown.connect("notify::selected", on_dropdown_changed)

    if root_folders:
        dropdown.set_selected(0)
        scroll_window.load_images(root_folders[0])

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.set_margin_top(20)
    box.set_margin_bottom(20)
    box.set_margin_start(20)
    box.set_margin_end(20)
    box.append(dropdown)
    box.append(scroll_window)

    win.set_child(box)
    win.present()


if __name__ == "__main__":
    app = Gtk.Application(application_id="org.myitems.wallpicker")
    app.connect("activate", on_activate)
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)

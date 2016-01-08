#!/usr/bin/env python3
#
# castawesome.py (ver 0.12)
# Copyright (C) 2012 Sami Lahtinen <lifelessplanetsoftware@gmail.com>
#
# Castawesome is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Castawesome is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Gdk, GLib
import os
import sys
import subprocess
import json
import re
import multiprocessing
import operator


# UI files, two for each window
# One is for local installation and one for system-wide installation
CONFIG_DIRECTORY = ".config/castawesome/"
SHARED_DIRECTORY = "/usr/local/share/castawesome/"
CONFIG_FILE = CONFIG_DIRECTORY + "config.txt"
IMAGE_CHAIN_CONNECTED = "gimp-vchain.png"
IMAGE_CHAIN_BROKEN = "gimp-vchain-broken.png"
IMAGE_LOGO = "CastA1.png"
STREAM_KEY = CONFIG_DIRECTORY + ".twitch_key"
UI_MAIN_LOCAL = "castawesome.ui"
UI_MAIN_SHARED = SHARED_DIRECTORY + "ui/castawesome.ui"
ABOUT_UI_FILE_LOCAL = "castawesome_about.ui"
ABOUT_UI_FILE_SHARED = SHARED_DIRECTORY + "/ui/castawesome_about.ui"

# A "hack" to get path to user's home folder
home = os.path.expanduser("~")


class GUI:
    streaming = False
    screen_input_resolution_ratio = None
    screen_output_resolution_ratio = None
    webcam_resolution_ratio = None
    webcam_button_lock = False
    application_process = None

    def __init__(self):
        self.builder = Gtk.Builder()
        self.settings = Settings(self.builder)
        self.stream_key = StreamKey()

        # Find the UI file
        try:
            self.builder.add_from_file(UI_MAIN_LOCAL)
        except:
            self.builder.add_from_file(UI_MAIN_SHARED)
        self.builder.connect_signals(self)

        window = self.builder.get_object('window_castawesome')

        compression_list = [
            ['ultrafast', 'Ultra Fast'],
            ['superfast', 'Super Fast'],
            ['veryfast', 'Very Fast'],
            ['faster', 'Faster'],
            ['fast', 'Fast'],
            ['medium', 'Medium'],
            ['slow', 'Slow'],
            ['slower', 'Slower'],
            ['veryslow', 'Very Slow'],
        ]
        for compression in compression_list:
            self.builder.get_object("liststore_compression")\
                .append(compression)

        services = [
            ['rtmp://live.twitch.tv/app/', 'Twitch.tv'],
            ['rtmp://a.rtmp.youtube.com/live2/', 'YouTube'],
            ['rtmp://live.hitbox.tv/push/', 'Hitbox.tv'],
            ['rtmp://live.us.picarto.tv/golive/', "Picarto.tv"],
            ['./', "Local File"],
            ["none", "Custom"]
        ]
        for service in services:
            self.builder.get_object("liststore_services").append(service)

        for obj in [
                "combobox_compression",
                "combobox_service"]:
            cell = Gtk.CellRendererText()
            self.builder.get_object(obj).pack_start(cell, True)
            self.builder.get_object(obj).add_attribute(cell, 'text', 1)

        self.initialize_values()

        window.show_all()

        self.counter_sec = 0
        self.counter_min = 0

        # Update timer every second
        GLib.timeout_add_seconds(1, self.update_timer)

    def initialize_values(self):
        # Initialize logo
        try:
            self.builder.add_from_file(ABOUT_UI_FILE_LOCAL)
            self.builder.get_object('image_logo').set_from_file(IMAGE_LOGO)
        except:
            self.builder.add_from_file(ABOUT_UI_FILE_SHARED)
            self.builder.get_object('image_logo')\
                .set_from_file(SHARED_DIRECTORY + "ui/" + IMAGE_LOGO)
        # Initialize the Screen tab.
        screen = Gdk.Screen.get_default()
        self.builder.get_object("adjustment_input_resolution_x")\
            .set_upper(screen.get_width())
        self.builder.get_object("adjustment_input_resolution_y")\
            .set_upper(screen.get_height())
        self.builder.get_object("adjustment_output_resolution_x")\
            .set_upper(screen.get_width())
        self.builder.get_object("adjustment_output_resolution_y")\
            .set_upper(screen.get_height())
        self.builder.get_object("adjustment_offset_x")\
            .set_upper(screen.get_width())
        self.builder.get_object("adjustment_offset_y")\
            .set_upper(screen.get_height())
        self.builder.get_object("adjustment_webcam_resolution_x")\
            .set_upper(screen.get_width())
        self.builder.get_object("adjustment_webcam_resolution_y")\
            .set_upper(screen.get_height())
        self.builder.get_object("spinbutton_input_resolution_x")\
            .set_text(self.settings.inres.split('x')[0])
        self.builder.get_object("spinbutton_input_resolution_y")\
            .set_text(self.settings.inres.split('x')[1])
        self.builder.get_object("spinbutton_output_resolution_x")\
            .set_text(self.settings.outres.split('x')[0])
        self.builder.get_object("spinbutton_output_resolution_y")\
            .set_text(self.settings.outres.split('x')[1])
        if self.settings.inres == self.settings.outres:
            self.builder.get_object("checkbutton_output_same_as_input")\
                .set_active(True)
            self.builder.get_object("spinbutton_output_resolution_x")\
                .set_sensitive(False)
            self.builder.get_object("spinbutton_output_resolution_y")\
                .set_sensitive(False)
        self.builder.get_object("spinbutton_offset_x")\
            .set_text(self.settings.x_offset)
        self.builder.get_object("spinbutton_offset_y")\
            .set_text(self.settings.y_offset)
        self.builder.get_object("spinbutton_frames_per_second")\
            .set_text(self.settings.fps)
        self.builder.get_object("switch_show_capture_region")\
            .set_active(self.settings.show_region)
        # Initialize the Stream tab.
        if self.settings.quality == "ultrafast":
            self.builder.get_object("combobox_compression").set_active(0)
        elif self.settings.quality == "superfast":
            self.builder.get_object("combobox_compression").set_active(1)
        elif self.settings.quality == "veryfast":
            self.builder.get_object("combobox_compression").set_active(2)
        elif self.settings.quality == "faster":
            self.builder.get_object("combobox_compression").set_active(3)
        elif self.settings.quality == "fast":
            self.builder.get_object("combobox_compression").set_active(4)
        elif self.settings.quality == "medium":
            self.builder.get_object("combobox_compression").set_active(5)
        elif self.settings.quality == "slow":
            self.builder.get_object("combobox_compression").set_active(6)
        elif self.settings.quality == "slower":
            self.builder.get_object("combobox_compression").set_active(7)
        elif self.settings.quality == "veryslow":
            self.builder.get_object("combobox_compression").set_active(8)
        if self.settings.service == 'rtmp://live.twitch.tv/app/':
            self.builder.get_object("combobox_service").set_active(0)
        elif self.settings.service == 'rtmp://a.rtmp.youtube.com/live2/':
            self.builder.get_object("combobox_service").set_active(1)
        elif self.settings.service == 'rtmp://live.hitbox.tv/push/':
            self.builder.get_object("combobox_service").set_active(2)
        elif self.settings.service == 'rtmp://live.us.picarto.tv/golive/':
            self.builder.get_object("combobox_service").set_active(3)
        elif self.settings.service == './':
            self.builder.get_object("combobox_service").set_active(4)
        else:
            self.builder.get_object("combobox_service").set_active(5)
        self.builder.get_object("entry_video_bitrate")\
            .set_text(self.settings.bitrate)
        advanced_options = get_advanced_options()
        for key in ["video_container", "video_codec", "audio_codec"]:
            lst = self.builder.get_object("liststore_" + key)
            val = getattr(self.settings, key)
            idx = 0
            for item in advanced_options[key]:
                name = item["name"]
                lst.append([name])
                if name == val:
                    self.builder.get_object("combobox_" + key).set_active(idx)
                idx += 1
            cell = Gtk.CellRendererText()
            self.builder.get_object("combobox_" + key).pack_start(cell, True)
            self.builder.get_object("combobox_" + key)\
                .add_attribute(cell, 'text', 0)
        self.builder.get_object("entry_audio_bitrate")\
            .set_text(self.settings.audio_bitrate)
        self.builder.get_object("spinbutton_threads")\
            .set_text(self.settings.threads)
        self.builder.get_object("entry_service")\
            .set_text(self.settings.service)
        self.builder.get_object("adjustment_threads")\
            .set_upper(multiprocessing.cpu_count())
        # Initialize the Application tab.
        self.builder.get_object("switch_run_application")\
            .set_active(self.settings.run_application)
        self.builder.get_object("entry_application")\
            .set_text(self.settings.application)
        # Initialize the Watermark tab.
        self.builder.get_object("switch_watermark")\
            .set_active(self.settings.watermark)
        if self.settings.watermark:
            self.builder.get_object("filechooserbutton_watermark_image")\
                .set_filename(self.settings.watermark_file)
            self.builder.get_object("image_watermark_image")\
                .set_from_file(self.settings.watermark_file)
            self.on_toggle_watermark_toggled(
                self.builder.get_object("switch_watermark")
            )
        # Initialize the Webcam tab.
        self.builder.get_object("switch_webcam")\
            .set_active(self.settings.webcam)
        self.builder.get_object("spinbutton_webcam_resolution_x")\
            .set_text(self.settings.webcam_resolution.split('x')[0])
        self.builder.get_object("spinbutton_webcam_resolution_y")\
            .set_text(self.settings.webcam_resolution.split('x')[1])

    def on_togglebutton_record_toggled(self, togglebutton):
        if togglebutton.get_active():
            togglebutton.set_sensitive(False)
            self.builder.get_object("togglebutton_stop").set_sensitive(True)
            self.builder.get_object("togglebutton_stop").set_active(False)
            self.on_toggle_streaming_toggled(togglebutton)

    def on_togglebutton_stop_toggled(self, togglebutton):
        if togglebutton.get_active():
            togglebutton.set_sensitive(False)
            self.builder.get_object("togglebutton_record").set_sensitive(True)
            self.builder.get_object("togglebutton_record").set_active(False)
            self.on_toggle_streaming_toggled(togglebutton)

    def on_toggle_input_resolution_link_toggled(self, togglebutton):
        if togglebutton.get_active():
            try:
                self.builder.add_from_file(ABOUT_UI_FILE_LOCAL)
                self.builder.get_object('image_input_resolution_link')\
                    .set_from_file(IMAGE_CHAIN_CONNECTED)
            except:
                self.builder.add_from_file(ABOUT_UI_FILE_SHARED)
                self.builder.get_object('image_input_resolution_link')\
                    .set_from_file(
                        SHARED_DIRECTORY + "ui/" + IMAGE_CHAIN_CONNECTED
                    )
            self.screen_input_resolution_ratio =\
                int(self.builder.get_object("spinbutton_input_resolution_x")
                    .get_text())\
                /\
                int(self.builder.get_object("spinbutton_input_resolution_y")
                    .get_text())
        else:
            try:
                self.builder.add_from_file(ABOUT_UI_FILE_LOCAL)
                self.builder.get_object('image_input_resolution_link')\
                    .set_from_file(IMAGE_CHAIN_BROKEN)
            except:
                self.builder.add_from_file(ABOUT_UI_FILE_SHARED)
                self.builder.get_object('image_input_resolution_link')\
                    .set_from_file(
                        SHARED_DIRECTORY + "ui/" + IMAGE_CHAIN_BROKEN
                    )
            self.screen_input_resolution_ratio = None

    def on_spinbutton_input_resolution_x_changed(self, spinbutton):
        input_resolution_link = self.builder\
            .get_object("toggle_input_resolution_link")
        input_resolution_y = self.builder\
            .get_object("spinbutton_input_resolution_y")
        if input_resolution_link.get_active():
            input_resolution_y.set_text(
                str(int(int(spinbutton.get_text())
                    / self.screen_input_resolution_ratio))
            )
        self.settings.inres = spinbutton.get_text() + 'x'\
            + input_resolution_y.get_text()

    def on_spinbutton_input_resolution_y_changed(self, spinbutton):
        input_resolution_link = self.builder\
            .get_object("toggle_input_resolution_link")
        input_resolution_x = self.builder\
            .get_object("spinbutton_input_resolution_x")
        if input_resolution_link.get_active():
            input_resolution_x.set_text(
                str(int(int(spinbutton.get_text())
                    * self.screen_input_resolution_ratio))
            )
        self.settings.inres = input_resolution_x.get_text() + 'x'\
            + spinbutton.get_text()

    def set_fullscreen(self, button):
        screen = Gdk.Screen.get_default()
        self.builder.get_object("spinbutton_input_resolution_x")\
            .set_text(str(screen.get_width()))
        self.builder.get_object("spinbutton_input_resolution_y")\
            .set_text(str(screen.get_height()))
        self.settings.inres = str(screen.get_width()) + 'x'\
            + str(screen.get_width())

    def on_toggle_output_resolution_link_toggled(self, togglebutton):
        if togglebutton.get_active():
            try:
                self.builder.add_from_file(ABOUT_UI_FILE_LOCAL)
                self.builder.get_object('image_output_resolution_link')\
                    .set_from_file(IMAGE_CHAIN_CONNECTED)
            except:
                self.builder.add_from_file(ABOUT_UI_FILE_SHARED)
                self.builder.get_object('image_output_resolution_link')\
                    .set_from_file(
                        SHARED_DIRECTORY + "ui/" + IMAGE_CHAIN_CONNECTED
                    )
            self.screen_output_resolution_ratio =\
                int(self.builder.get_object("spinbutton_output_resolution_x")
                    .get_text())\
                /\
                int(self.builder.get_object("spinbutton_output_resolution_y")
                    .get_text())
        else:
            try:
                self.builder.add_from_file(ABOUT_UI_FILE_LOCAL)
                self.builder.get_object('image_output_resolution_link')\
                    .set_from_file(IMAGE_CHAIN_BROKEN)
            except:
                self.builder.add_from_file(ABOUT_UI_FILE_SHARED)
                self.builder.get_object('image_output_resolution_link')\
                    .set_from_file(
                        SHARED_DIRECTORY + "ui/" + IMAGE_CHAIN_BROKEN
                    )
            self.screen_output_resolution_ratio = None

    def on_spinbutton_output_resolution_x_changed(self, spinbutton):
        output_resolution_link = self.builder\
            .get_object("toggle_output_resolution_link")
        output_resolution_y = self.builder\
            .get_object("spinbutton_output_resolution_y")
        if output_resolution_link.get_active():
            output_resolution_y.set_text(
                str(int(int(spinbutton.get_text())
                    / self.screen_output_resolution_ratio))
            )
        self.settings.outres = spinbutton.get_text() + 'x'\
            + output_resolution_y.get_text()

    def on_spinbutton_output_resolution_y_changed(self, spinbutton):
        output_resolution_link = self.builder\
            .get_object("toggle_output_resolution_link")
        output_resolution_x = self.builder\
            .get_object("spinbutton_output_resolution_x")
        if output_resolution_link.get_active():
            output_resolution_x.set_text(
                str(int(int(spinbutton.get_text())
                    * self.screen_output_resolution_ratio))
            )
        self.settings.outres = output_resolution_x.get_text() + 'x'\
            + spinbutton.get_text()

    def on_toggle_streaming_toggled(self, window):
        # Are we streaming, or not?
        if self.streaming:
            # Kill the subprocess and end the stream
            subprocess.call(
                "ps -ef | awk '$3 == \"" + str(self.process.pid)
                + "\" {print $2}' | xargs kill -9",
                shell=True
            )
            self.process.kill()
        else:
            self.stream()
        self.streaming = not self.streaming
        print ("Streaming: " + str(self.streaming))

    def on_output_same_as_input_toggled(self, checkbutton):
        if checkbutton.get_active():
            self.builder.get_object('spinbutton_output_resolution_x')\
                .set_sensitive(False)
            self.builder.get_object('spinbutton_output_resolution_x')\
                .set_text(
                    self.builder.get_object('spinbutton_input_resolution_x')
                        .get_text()
                )
            self.builder.get_object('spinbutton_output_resolution_y')\
                .set_sensitive(False)
            self.builder.get_object('spinbutton_output_resolution_y')\
                .set_text(
                    self.builder.get_object('spinbutton_input_resolution_y')
                        .get_text()
                )
        else:
            self.builder.get_object('spinbutton_output_resolution_x')\
                .set_sensitive(True)
            self.builder.get_object('spinbutton_output_resolution_y')\
                .set_sensitive(True)

    def on_offset_x_changed(self, spinbutton):
        self.settings.x_offset = spinbutton.get_text()

    def on_offset_y_changed(self, spinbutton):
        self.settings.y_offset = spinbutton.get_text()

    def on_offset_frames_per_second_changed(self, spinbutton):
        self.settings.fps = spinbutton.get_text()

    def on_toggle_show_capture_region_toggled(self, toggle):
        self.settings.show_region = toggle.get_active()

    def on_compression_changed(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active >= 0:
            self.settings.quality = model[active][0]

    def on_video_bitrate_changed(self, entry):
        self.settings.bitrate = entry.get_text()

    def on_video_container_changed(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active >= 0:
            self.settings.video_container = model[active][0]

    def on_video_codec_changed(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active >= 0:
            self.settings.video_codec = model[active][0]

    def on_audio_bitrate_changed(self, entry):
        self.settings.audio_bitrate = entry.get_text()

    def on_audio_codec_changed(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active >= 0:
            self.settings.audio_codec = model[active][0]

    def on_threads_value_changed(self, spinbutton):
        self.settings.threads = spinbutton.get_text()

    def on_service_changed(self, combobox):
        model = self.builder.get_object("combobox_service").get_model()
        active = self.builder.get_object("combobox_service").get_active()
        if active >= 0:
            self.settings.service = model[active][0]
            self.builder.get_object("entry_service")\
                .set_text(self.settings.service)
            if active == 5:
                self.builder.get_object("entry_service").set_sensitive(True)
                self.builder.get_object("entry_service").set_text("rtmp://")
            else:
                self.builder.get_object("entry_service").set_sensitive(False)

    def on_key_edit_toggled(self, entry):
        if entry.get_active():
            self.builder.get_object("entry_key").set_text(self.stream_key.key)
            self.builder.get_object("entry_key").set_sensitive(True)
        else:
            self.stream_key.key = self.builder.get_object("entry_key")\
                .get_text()
            self.builder.get_object("entry_key").set_text('')
            self.builder.get_object("entry_key").set_sensitive(False)

    def on_key_changed(self, entry):
        if entry.get_text() != '':
            self.stream_key.key = entry.get_text()

    def on_toggle_run_application_toggled(self, toggle):
        self.settings.run_application = toggle.get_active()
        self.builder.get_object("entry_application")\
            .set_sensitive(toggle.get_active())

    def on_application_changed(self, entry):
        self.settings.application = entry.get_text()

    def on_toggle_watermark_toggled(self, toggle):
        self.settings.watermark = toggle.get_active()
        self.builder.get_object("filechooserbutton_watermark_image")\
            .set_sensitive(toggle.get_active())
        self.builder.get_object("image_watermark_image")\
            .set_sensitive(toggle.get_active())
        if toggle.get_active():
            self.builder.get_object("image_watermark_image")\
                .set_opacity(1)
        else:
            self.builder.get_object("image_watermark_image")\
                .set_opacity(.25)

    def on_watermark_image_file_set(self, file_chooser):
        self.settings.watermark_file = file_chooser.get_filename()
        self.builder.get_object("image_watermark_image")\
            .set_from_file(self.settings.watermark_file)

    def on_toggle_webcam_toggled(self, toggle):
        self.settings.webcam = toggle.get_active()
        if toggle.get_active():
            self.initialize_webcam_position()
            self.builder.get_object("togglebutton_webcam_top_left")\
                .set_sensitive(True)
            self.builder.get_object("togglebutton_webcam_top_center")\
                .set_sensitive(True)
            self.builder.get_object("togglebutton_webcam_top_right")\
                .set_sensitive(True)
            self.builder.get_object("togglebutton_webcam_center_left")\
                .set_sensitive(True)
            self.builder.get_object("togglebutton_webcam_center_center")\
                .set_sensitive(True)
            self.builder.get_object("togglebutton_webcam_center_right")\
                .set_sensitive(True)
            self.builder.get_object("togglebutton_webcam_bottom_left")\
                .set_sensitive(True)
            self.builder.get_object("togglebutton_webcam_bottom_center")\
                .set_sensitive(True)
            self.builder.get_object("togglebutton_webcam_bottom_right")\
                .set_sensitive(True)
            self.builder.get_object("label_webcam_resolution")\
                .set_sensitive(True)
            self.builder.get_object("spinbutton_webcam_resolution_x")\
                .set_sensitive(True)
            self.builder.get_object("spinbutton_webcam_resolution_y")\
                .set_sensitive(True)
            self.builder.get_object("togglebutton_webcam_resolution_link")\
                .set_sensitive(True)
            self.builder.get_object("image_webcam_resolution_link")\
                .set_sensitive(True)
        else:
            self.builder.get_object("togglebutton_webcam_top_left")\
                .set_sensitive(False)
            self.builder.get_object("togglebutton_webcam_top_center")\
                .set_sensitive(False)
            self.builder.get_object("togglebutton_webcam_top_right")\
                .set_sensitive(False)
            self.builder.get_object("togglebutton_webcam_center_left")\
                .set_sensitive(False)
            self.builder.get_object("togglebutton_webcam_center_center")\
                .set_sensitive(False)
            self.builder.get_object("togglebutton_webcam_center_right")\
                .set_sensitive(False)
            self.builder.get_object("togglebutton_webcam_bottom_left")\
                .set_sensitive(False)
            self.builder.get_object("togglebutton_webcam_bottom_center")\
                .set_sensitive(False)
            self.builder.get_object("togglebutton_webcam_bottom_right")\
                .set_sensitive(False)
            self.builder.get_object("label_webcam_resolution")\
                .set_sensitive(False)
            self.builder.get_object("spinbutton_webcam_resolution_x")\
                .set_sensitive(False)
            self.builder.get_object("spinbutton_webcam_resolution_y")\
                .set_sensitive(False)
            self.builder.get_object("togglebutton_webcam_resolution_link")\
                .set_sensitive(False)
            self.builder.get_object("image_webcam_resolution_link")\
                .set_sensitive(False)

    def initialize_webcam_position(self):
        self.builder.get_object("togglebutton_webcam_top_left")\
            .set_active(False)
        self.builder.get_object("togglebutton_webcam_top_center")\
            .set_active(False)
        self.builder.get_object("togglebutton_webcam_top_right")\
            .set_active(False)
        self.builder.get_object("togglebutton_webcam_center_left")\
            .set_active(False)
        self.builder.get_object("togglebutton_webcam_center_center")\
            .set_active(False)
        self.builder.get_object("togglebutton_webcam_center_right")\
            .set_active(False)
        self.builder.get_object("togglebutton_webcam_bottom_left")\
            .set_active(False)
        self.builder.get_object("togglebutton_webcam_bottom_center")\
            .set_active(False)
        self.builder.get_object("togglebutton_webcam_bottom_right")\
            .set_active(False)
        if self.settings.webcam_placement == "0:0":
            self.builder.get_object("togglebutton_webcam_top_left")\
                .set_active(True)
        elif self.settings.webcam_placement == "main_w/2-w/2:0":
            self.builder.get_object("togglebutton_webcam_top_center")\
                .set_active(True)
        elif self.settings.webcam_placement == "main_w-w:0":
            self.builder.get_object("togglebutton_webcam_top_right")\
                .set_active(True)
        elif self.settings.webcam_placement == "0:main_h/2-h/2":
            self.builder.get_object("togglebutton_webcam_center_left")\
                .set_active(True)
        elif self.settings.webcam_placement == "main_w/2-w/2:main_h/2-h/2":
            self.builder.get_object("togglebutton_webcam_center_center")\
                .set_active(True)
        elif self.settings.webcam_placement == "main_w-w:main_h/2-h/2":
            self.builder.get_object("togglebutton_webcam_center_right")\
                .set_active(True)
        elif self.settings.webcam_placement == "0:main_h-h":
            self.builder.get_object("togglebutton_webcam_bottom_left")\
                .set_active(True)
        elif self.settings.webcam_placement == "main_w/2-w/2:main_h-h":
            self.builder.get_object("togglebutton_webcam_bottom_center")\
                .set_active(True)
        elif self.settings.webcam_placement == "main_w-w:main_h-h":
            self.builder.get_object("togglebutton_webcam_bottom_right")\
                .set_active(True)

    def on_webcam_position_changed(self, togglebutton):
        if togglebutton.get_active() and not self.webcam_button_lock:
            self.webcam_button_lock = True
            if togglebutton.get_property('name')\
                    == 'togglebutton_webcam_top_left':
                self.settings.webcam_placement = "0:0"
            elif togglebutton.get_property('name')\
                    == 'togglebutton_webcam_top_center':
                self.settings.webcam_placement = "main_w/2-w/2:0"
            elif togglebutton.get_property('name')\
                    == 'togglebutton_webcam_top_right':
                self.settings.webcam_placement = "main_w-w:0"
            elif togglebutton.get_property('name')\
                    == 'togglebutton_webcam_center_left':
                self.settings.webcam_placement = "0:main_h/2-h/2"
            elif togglebutton.get_property('name')\
                    == 'togglebutton_webcam_center_center':
                self.settings.webcam_placement = "main_w/2-w/2:main_h/2-h/2"
            elif togglebutton.get_property('name')\
                    == 'togglebutton_webcam_center_right':
                self.settings.webcam_placement = "main_w-w:main_h/2-h/2"
            elif togglebutton.get_property('name')\
                    == 'togglebutton_webcam_bottom_left':
                self.settings.webcam_placement = "0:main_h-h"
            elif togglebutton.get_property('name')\
                    == 'togglebutton_webcam_bottom_center':
                self.settings.webcam_placement = "main_w/2-w/2:main_h-h"
            elif togglebutton.get_property('name')\
                    == 'togglebutton_webcam_bottom_right':
                self.settings.webcam_placement = "main_w-w:main_h-h"
            self.initialize_webcam_position()
            self.webcam_button_lock = False

    def on_toggle_webcam_resolution_link_toggled(self, togglebutton):
        if togglebutton.get_active():
            try:
                self.builder.add_from_file(ABOUT_UI_FILE_LOCAL)
                self.builder.get_object('image_webcam_resolution_link')\
                    .set_from_file(IMAGE_CHAIN_CONNECTED)
            except:
                self.builder.add_from_file(ABOUT_UI_FILE_SHARED)
                self.builder.get_object('image_webcam_resolution_link')\
                    .set_from_file(
                        SHARED_DIRECTORY + "ui/" + IMAGE_CHAIN_CONNECTED
                    )
            self.webcam_resolution_ratio =\
                int(self.builder.get_object("spinbutton_webcam_resolution_x")
                    .get_text())\
                /\
                int(self.builder.get_object("spinbutton_webcam_resolution_y")
                    .get_text())
        else:
            try:
                self.builder.add_from_file(ABOUT_UI_FILE_LOCAL)
                self.builder.get_object('image_webcam_resolution_link')\
                    .set_from_file(IMAGE_CHAIN_BROKEN)
            except:
                self.builder.add_from_file(ABOUT_UI_FILE_SHARED)
                self.builder.get_object('image_webcam_resolution_link')\
                    .set_from_file(
                        SHARED_DIRECTORY + "ui/" + IMAGE_CHAIN_BROKEN
                    )
            self.webcam_resolution_ratio = None

    def on_spinbutton_webcam_resolution_x_changed(self, spinbutton):
        webcam_resolution_link = self.builder\
            .get_object("togglebutton_webcam_resolution_link")
        webcam_resolution_y = self.builder\
            .get_object("spinbutton_webcam_resolution_y")
        if webcam_resolution_link.get_active():
            webcam_resolution_y.set_text(
                str(int(int(spinbutton.get_text())
                    / self.webcam_resolution_ratio))
            )
        self.settings.webcam_resolution = spinbutton.get_text() + 'x'\
            + webcam_resolution_y.get_text()

    def on_spinbutton_webcam_resolution_y_changed(self, spinbutton):
        webcam_resolution_link = self.builder\
            .get_object("togglebutton_webcam_resolution_link")
        webcam_resolution_x = self.builder\
            .get_object("spinbutton_webcam_resolution_x")
        if webcam_resolution_link.get_active():
            webcam_resolution_x.set_text(
                str(int(int(spinbutton.get_text())
                    * self.webcam_resolution_ratio))
            )
        self.settings.webcam_resolution = webcam_resolution_x.get_text() + 'x'\
            + spinbutton.get_text()

    def on_save_settings_clicked(self, button):
        self.settings.save()
        self.stream_key.save()

    def on_about_clicked(self, button):
        About()

    def stream(self):
        # Decide whether to enable visible screen regions
        if self.settings.show_region:
            show_region = "1"
        else:
            show_region = "0"

        # Avconv is supplied with user's settings and executed
        parameters = {
            "inres": self.settings.inres,
            "outres": self.settings.outres,
            "x_offset": self.settings.x_offset,
            "y_offset": self.settings.y_offset,
            "fps": self.settings.fps,
            "quality": self.settings.quality,
            "bitrate": self.settings.bitrate,
            "threads": self.settings.threads,
            "show_region": show_region,
            "service": self.settings.service,
            "watermark": '-vf "movie=%(watermark_file)s [watermark]; '
            + '[in][watermark] overlay=0:0 [out]"'
            % {"watermark_file": self.settings.watermark_file},
            "watermark_file": self.settings.watermark_file,
            "web_placement": self.settings.webcam_placement,
            "web_resolution": self.settings.webcam_resolution,
            "audio_bitrate": self.settings.audio_bitrate,
            "video_container": self.settings.video_container,
            "video_codec": self.settings.video_codec,
            "audio_codec": self.settings.audio_codec
        }
        parameters["keyint"] = str(int(parameters["fps"]) * 2)
        # Decide which avconv/avconv command to use based on the settings
        filter_complex = ''
        if self.settings.webcam and self.settings.watermark:
            filter_complex = "-filter_complex 'setpts=PTS-STARTPTS[bg]; "\
                "setpts=PTS-STARTPTS[fg]; "\
                "[bg][fg]overlay=%(web_placement)s[bg2]; "\
                "[bg2]overlay=0:main_h-overlay_h-0,format=yuv420p[out]' "\
                "-map '[out]' "
        elif self.settings.webcam:
            filter_complex = "-filter_complex 'overlay=0:main_h-overlay_h-0' "
        elif self.settings.watermark:
            filter_complex = "-filter_complex "\
                "'overlay=%(web_placement)s,format=yuv420p[out]' -map '[out]' "
        command = \
            'avconv -f x11grab -show_region %(show_region)s -s %(inres)s '\
            + '-framerate " %(fps)s" -i :0.0+%(x_offset)s,%(y_offset)s '
        if self.settings.webcam:
            command = command + \
                '-f video4linux2 -video_size %(web_resolution)s '\
                '-framerate %(fps)s -i /dev/video0 '
        if self.settings.watermark:
            command = command + '-i %(watermark_file)s '
        command = str(
            command
            + '-f pulse -ac 1 -i default -vcodec %(video_codec)s '
            + filter_complex
            + '-s %(outres)s -preset %(quality)s -acodec %(audio_codec)s '
            + '-ar 44100 -threads %(threads)s -qscale 3 '
            + '-b:a %(audio_bitrate)s -b:v %(bitrate)s -minrate %(bitrate)s '
            + '-g %(keyint)s -pix_fmt yuv420p '
            + '-f %(video_container)s "%(service)s' + self.stream_key.key + '"'
        ) % parameters
        if self.settings.run_application:
            self.application_process = subprocess.Popen(
                self.settings.application,
                stdout=subprocess.PIPE,
                shell=True
            )
        print (command.replace(self.stream_key.key, '<_stream_key_>'))
        # Start a subprocess to handle avconv
        self.process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE
        )

    def update_timer(self):
        # Just minute/second counter, nothing fancy here
        if self.streaming:
            self.counter_sec += 1
            if self.counter_sec == 60:
                self.counter_min += 1
                self.counter_sec = 0

            label = self.builder.get_object("label_record_status")
            label.set_text(
                "Time: %02d:%02d" % (self.counter_min, self.counter_sec)
            )
            if self.settings.run_application\
                    and self.application_process is not None\
                    and self.application_process.poll() is not None:
                self.builder.get_object("togglebutton_stop").set_active(True)
        else:
            self.counter_min = 0
            self.counter_sec = 0

        return True

    def destroy(self, window):
        if self.streaming:
            # Kill the subprocess and end the stream
            self.process.kill()
        Gtk.main_quit()


def get_advanced_options():
    options = {"video_container": [], "video_codec": [], "audio_codec": []}

    # make avconv list containers (which it calls formats)
    for line in subprocess.check_output(["avconv", "-formats"]).splitlines():
        match = re.match(
            b"""
            \s*      # maybe leading whitespace
            (.{2})   # container properties
            \s+      # whitespace
            ([\w-]+) # container name, like `flv`
            \s+      # whitespace
            (\S+)    # container description""",
            line,
            re.X
        )
        if match:
            props, name, desc = match.group(1, 2, 3)
            if b'E' in props:  # only formats that we can actually encode
                options["video_container"]\
                    .append({
                        "name": name.decode('utf-8'),
                        "desc": desc.decode('utf-8')
                    })
    options["video_container"] = sorted(
        options["video_container"],
        key=operator.itemgetter("name")
    )

    # make avconv list decoders
    for line in subprocess.check_output(["avconv", "-decoders"]).splitlines():
        match = re.match(
            b"""
            \s*            # maybe leading whitespace
            ([.VASFXBD]+)  # decoder properties
            \s+            # whitespace
            ([\w-]+)       # decoder name, like `h264`
            \s+            # whitespace
            (.+)           # decoder description""",
            line,
            re.X
        )
        if match:
            props, name, desc = match.group(1, 2, 3)
            decoder = {
                "name": name.decode('utf-8'),
                "desc": desc.decode('utf-8')
            }
            if b'V' in props:  # video codec
                options["video_codec"].append(decoder)
            if b'A' in props:  # audio codec
                options["audio_codec"].append(decoder)
    options["video_codec"] = sorted(
        options["video_codec"],
        key=operator.itemgetter("name")
    )
    options["audio_codec"] = sorted(
        options["audio_codec"],
        key=operator.itemgetter("name")
    )

    return options


# Settings manager for user's settings
class Settings:
    inres = "1280x720"                # Input resolution
    outres = "1280x720"                # Output resolution
    x_offset = "0"                    # X offset
    y_offset = "0"                    # Y offset
    fps = "30"                        # Frames per Second
    quality = "medium"                # Quality (medium, fast, etc.)
    bitrate = "500k"                # Bitrate (+300k usually is fine)
    audio_bitrate = "128k"            # <TODO>
    threads = "1"                    # Amount of threads
    show_region = "0"                # Show or don't show capture region
    video_container = "flv"            # <TODO>
    video_codec = "h264"            # <TODO>
    audio_codec = "mp3"                # <TODO>
    run_application = False
    application = ""
    watermark = False                # Enable/Disable watermarking
    watermark_file = ""                # Filename of the watermark
    webcam = False                    # Enable/Disable webcam
    webcam_placement = "0:0"        # Placement of the webcam overlay
    webcam_resolution = "320x200"    # Resolution of the webcam
    service = "rtmp://live.twitch.tv/app/"    # The streaming service in use

    def __init__(self, builder):
        try:
            if not os.path.isdir(os.path.join(home, CONFIG_DIRECTORY)):
                os.mkdir(os.path.join(home, CONFIG_DIRECTORY))
                self.save()
            elif not os.path.isfile(os.path.join(home, CONFIG_FILE)):
                self.save()

            self.load_configuration_file()

        except:
            print ("An error occured: " + str(sys.exc_info()))
            print ("Couldn't load config file!")

    def load_configuration_file(self):
        with open(
            os.path.join(home, CONFIG_FILE),
            "r"
        ) as fob:
            lines = fob.read()

        # What if user has legacy config files?
        if "{" not in lines[0]:
            print ("Using legacy config loader...")
            self.load_legacy_config()
        else:
            lines = json.loads(lines)

            self.inres = lines["inres"]
            self.outres = lines["outres"]
            self.x_offset = lines["x_offset"]
            self.y_offset = lines["y_offset"]
            self.fps = lines["fps"]
            self.quality = lines["quality"]
            self.bitrate = lines["bitrate"]
            self.audio_bitrate = lines["audio_bitrate"]
            self.video_container = lines["video_container"]
            self.video_codec = lines["video_codec"]
            self.audio_codec = lines["audio_codec"]
            if lines["run_application"] == "False":
                self.run_application = False
            else:
                self.run_application = True
            self.application = lines["application"]
            self.threads = lines["threads"]
            if lines["show_region"] == "False":
                self.show_region = False
            else:
                self.show_region = True
            try:
                self.service = lines["service"]
            except:
                self.service = "none"
            if lines["use_watermark"] == "True":
                self.watermark = True
            else:
                self.watermark = False
            try:
                self.watermark_file = lines["watermark_file"]
            except:
                ""
            try:
                if lines["use_webcam"] == "True":
                    self.webcam = True
                else:
                    self.webcam = False
            except:
                self.webcam = False
            try:
                self.webcam_placement = lines["webcam_placement"]
                self.webcam_resolution = lines["webcam_resolution"]
            except:
                self.webcam_placement = "0:0"
                self.webcam_resolution = "320x200"

    def save(self):
        with open(
            os.path.join(home, CONFIG_FILE),
            "w"
        ) as fob:
            # We will use dictionary based formatting expressions
            d = {
                "inres": self.inres,
                "outres": self.outres,
                "x_offset": self.x_offset,
                "y_offset": self.y_offset,
                "fps": self.fps,
                "quality": self.quality,
                "bitrate": self.bitrate,
                "audio_bitrate": self.audio_bitrate,
                "threads": self.threads,
                "video_container": self.video_container,
                "video_codec": self.video_codec,
                "audio_codec": self.audio_codec,
                "run_application": str(self.run_application),
                "application": self.application,
                "show_region": str(self.show_region),
                "use_watermark": str(self.watermark),
                "watermark_file": self.watermark_file,
                "webcam": str(self.webcam),
                "web_placement": self.webcam_placement,
                "web_resolution": self.webcam_resolution,
                "service": self.service
            }

            fob.write("""{
    "inres": "%(inres)s",
    "outres": "%(outres)s",
    "x_offset": "%(x_offset)s",
    "y_offset": "%(y_offset)s",
    "fps": "%(fps)s",
    "quality": "%(quality)s",
    "bitrate": "%(bitrate)s",
    "audio_bitrate" : "%(audio_bitrate)s",
    "video_container" : "%(video_container)s",
    "video_codec" : "%(video_codec)s",
    "audio_codec" : "%(audio_codec)s",
    "threads": "%(threads)s",
    "run_application": "%(run_application)s",
    "application": "%(application)s",
    "show_region": "%(show_region)s",
    "use_watermark" : "%(use_watermark)s",
    "watermark_file" : "%(watermark_file)s",
    "use_webcam" : "%(webcam)s",
    "webcam_placement" : "%(web_placement)s",
    "webcam_resolution" : "%(web_resolution)s",
    "service": "%(service)s"\n}""" % d)

    # Function to make the program backwards compatible
    # with the old config files
    def load_legacy_config(self):
        try:
            with open(
                os.path.join(home, CONFIG_FILE),
                "r"
            ) as fob:
                lines = fob.readlines()

            self.inres = lines[0].strip()
            self.outres = lines[1].strip()
            self.x_offset = lines[2].strip()
            self.y_offset = lines[3].strip()
            self.fps = lines[4].strip()
            self.quality = lines[5].strip()
            self.bitrate = lines[6].strip()
            self.threads = lines[7].strip()
            self.show_region = lines[8].strip()
        except IOError:
            print ("Couldn't load config file!")


# Stream key warning dialog
class StreamKey():
    key = None

    def __init__(self):
        # If the file does not exist, create it and set secure permissions.
        if not os.path.isfile(os.path.join(home, STREAM_KEY)):
            self._create_config_file()

        with open(
            os.path.join(home, STREAM_KEY),
            "r"
        ) as fob:
            self.key = fob.read()

    def save(self):
        with open(
            os.path.join(home, STREAM_KEY),
            "w"
        ) as fob:
            fob.write(self.key)

    def _create_config_file(self):
        os.system("touch " + os.path.join(home, STREAM_KEY))
        os.chmod(os.path.join(home, STREAM_KEY), 0o600)


# About window
class About():
    def __init__(self):
        self.builder = Gtk.Builder()
        try:
            self.builder.add_from_file(ABOUT_UI_FILE_LOCAL)
            self.builder.get_object('image').set_from_file(IMAGE_LOGO)
        except:
            self.builder.add_from_file(ABOUT_UI_FILE_SHARED)
            self.builder.get_object('image')\
                .set_from_file(SHARED_DIRECTORY + "ui/" + IMAGE_LOGO)
        self.window = self.builder.get_object("about")
        self.window.show_all()


# Program main function
def main():
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print ("Castawesome is ok")
        sys.exit(0)
    GUI()
    Gtk.main()

    return 0

if __name__ == "__main__":
    sys.exit(main())

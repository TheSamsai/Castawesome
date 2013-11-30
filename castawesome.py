#!/usr/bin/python2
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

from gi.repository import Gtk, GdkPixbuf, Gdk, GLib
import gobject
import os, sys, signal
import time
import thread
import subprocess, shlex
import json


# UI files, two for each window
# One is for local installation and one for system-wide installation
UI_FILE1 = "castawesome.ui"
UI_FILE2 = "/usr/local/share/castawesome/ui/castawesome.ui"
SETUP_UI_FILE1 = "castawesome_settings.ui"
SETUP_UI_FILE2 = "/usr/local/share/castawesome/ui/castawesome_settings.ui"
STREAMKEY_UI_FILE1 = "castawesome_streamkey.ui"
STREAMKEY_UI_FILE2 = "/usr/local/share/castawesome/ui/castawesome_streamkey.ui"
ABOUT_UI_FILE1 = "castawesome_about.ui"
ABOUT_UI_FILE2 = "/usr/local/share/castawesome/ui/castawesome_about.ui"

# A "hack" to get path to user's home folder
home = os.path.expanduser("~")

class GUI:
	streaming = False
	
	def __init__(self):
		self.builder = Gtk.Builder()
		
		# Find the UI file
		try:
			self.builder.add_from_file(UI_FILE1)
			self.builder.get_object('image').set_from_file("CastA1.png")
			self.builder.get_object('window').set_icon_from_file("IconCA.png")
		except:
			self.builder.add_from_file(UI_FILE2)
			self.builder.get_object('image').set_from_file("/usr/local/share/castawesome/ui/CastA1.png")
			self.builder.get_object('window').set_icon_from_file("/usr/local/share/castawesome/ui/IconCA.png")
		self.builder.connect_signals(self)

		window = self.builder.get_object('window')

		self.settings = Settings()
		
		window.show_all()

		self.counter_sec = 0
		self.counter_min = 0
		
		# Update timer every second
		GLib.timeout_add_seconds(1, self.update_timer)

	def on_toggle_streaming_toggled(self, window):
		# Are we streaming, or not?
		if self.streaming:
			# Kill the subprocess and end the stream
			self.process.kill()
		else:
			self.stream()
		self.streaming = not self.streaming
		print "Streaming: " + str(self.streaming)

	def on_button_settings_clicked(self, window):
		self.settings = Settings()
	def on_button_about_clicked(self, window):
		self.about = About()
	def stream(self):
		# Twitch key needs to be read to stream video
		fob = open(os.path.join(home, ".config/castawesome/.twitch_key"), "r")
		twitch_key = fob.read().strip()
		fob.close()
		
		# Setting up audio channels for audio input
		# self.audiochannels = "-f alsa -ac 2 -i pulse"
		
		# Avconv is supplied with user's settings and executed
		parameters = {"inres" : self.settings.get_inres(), "outres" : self.settings.get_outres(), "x_offset" : self.settings.get_x_offset(),
		"y_offset" : self.settings.get_y_offset(), "fps" : self.settings.get_fps(), "quality" : self.settings.get_quality(),
		"bitrate" : self.settings.get_bitrate(), "threads" : self.settings.get_threads(), "show_region" : self.settings.get_show_region()
		}
		
		command = str('avconv -f x11grab -show_region %(show_region)s -s %(inres)s -r " %(fps)s" -i :0.0+%(x_offset)s,%(y_offset)s -f alsa -ac 2 -i pulse -vcodec libx264 -s %(outres)s -preset %(quality)s -acodec libmp3lame -ar 44100 -threads %(threads)s -qscale 3 -b %(bitrate)s -bufsize 512k -f flv "rtmp://live.justin.tv/app/' + twitch_key + '"') % parameters
		print command
		# Start a subprocess to handle avconv
		self.process = subprocess.Popen(shlex.split(command))
		
	def update_timer(self):
		# Just minute/second counter, nothing fancy here
		if self.streaming:
			self.counter_sec += 1
			if(self.counter_sec == 60):
				self.counter_min += 1
				self.counter_sec = 0

			label = self.builder.get_object("label_timer")
			label.set_text(str(self.counter_min) + ":" + str(self.counter_sec))
		else:
			self.counter_min = 0
			self.counter_sec = 0
		return True
		
	def destroy(window, self):
		Gtk.main_quit()

# Settings manager for user's settings
class Settings:
	inres = ""				# Input resolution
	outres = ""				# Output resolution
	x_offset = ""			# X offset
	y_offset = ""			# Y offset
	fps = ""				# Frames per Second
	quality = ""			# Quality (medium, fast, etc.)
	bitrate = ""			# Bitrate (+300k usually is fine)
	threads = ""			# Amount of threads

	def __init__(self):
		try:
			os.mkdir(os.path.join(home, ".config/castawesome"))
			# Configuration files are missing, create them and add default settings
			os.system("touch ~/.config/castawesome/.twitch_key")
			
			# Default settings for the user
			fob = open(os.path.join(home, ".config/castawesome/config.txt"), "w")
			fob.write("""{
	"inres": "1280x720",\n
	"outres": "1280x720",\n
	"x_offset": "0",\n
	"y_offset": "0",\n
	"fps": "25",\n
	"quality": "medium",\n
	"bitrate": "400k",\n
	"threads": "1",\n
	"show_region": "1"\n
}""")
			fob.close()
		except:
			print "Config files exist..."
		try:
			fob = open(os.path.join(home, ".config/castawesome/.twitch_key"), "r")
			key = fob.read()
			fob.close()
			
			if key == "":
				warning = StreamKey()
			
			fob = open(os.path.join(home, ".config/castawesome/config.txt"), "r")
			lines = fob.read()
			fob.close()
			# What if user has legacy config files?
			if not "{" in lines[0]:
				print "Using legacy config loader..."
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
				self.threads = lines["threads"]
				self.show_region = lines["show_region"]
		except:
			print "An error occured: " + str(sys.exc_info())
			print "Couldn't load config files!"
			
		self.builder = Gtk.Builder()
		try:
			self.builder.add_from_file(SETUP_UI_FILE1)
			print "Loaded " + SETUP_UI_FILE1
		except:
			self.builder.add_from_file(SETUP_UI_FILE2)
			print "Loaded " + SETUP_UI_FILE2
		self.builder.connect_signals(self)

		window = self.builder.get_object("settings")
		self.builder.get_object("entry_inres").set_text(self.inres)
		self.builder.get_object("entry_outres").set_text(self.outres)
		self.builder.get_object("entry_xoffset").set_text(self.x_offset)
		self.builder.get_object("entry_yoffset").set_text(self.y_offset)
		self.builder.get_object("entry_fps").set_text(self.fps)
		self.builder.get_object("entry_quality").set_text(self.quality)
		self.builder.get_object("entry_bitrate").set_text(self.bitrate)
		self.builder.get_object("entry_threads").set_text(self.threads)
		self.builder.get_object("entry_region").set_text(self.show_region)
		
		# Apply previous configs
		self.on_button_apply_clicked(0)
		
		window.show_all()

	def get_inres(self):
		return self.inres

	def get_outres(self):
		return self.outres
		
	def get_x_offset(self):
		return self.x_offset
		
	def get_y_offset(self):
		return self.y_offset

	def get_fps(self):
		return self.fps

	def get_quality(self):
		return self.quality

	def get_bitrate(self):
		return self.bitrate

	def get_threads(self):
		return self.threads

	def get_show_region(self):
		return self.show_region
		
	def on_button_apply_clicked(self, window):
		self.inres = self.builder.get_object("entry_inres").get_text()
		self.outres = self.builder.get_object("entry_outres").get_text()
		self.x_offset = self.builder.get_object("entry_xoffset").get_text()
		self.y_offset = self.builder.get_object("entry_yoffset").get_text()
		self.fps = self.builder.get_object("entry_fps").get_text()
		self.quality = self.builder.get_object("entry_quality").get_text()
		self.bitrate = self.builder.get_object("entry_bitrate").get_text()
		self.threads = self.builder.get_object("entry_threads").get_text()
		self.show_region = self.builder.get_object("entry_region").get_text()

		# Save configs in homefolder
		fob = open(os.path.join(home, ".config/castawesome/config.txt"), "w")
		# We will use dictionary based formatting expressions
		d = {"inres" : self.inres, "outres" : self.outres, "x_offset" : self.x_offset,
		"y_offset" : self.y_offset, "fps" : self.fps, "quality" : self.quality,
		"bitrate" : self.bitrate, "threads" : self.threads, "show_region" : self.show_region
		}
		
		fob.write("""{
	"inres": "%(inres)s",
	"outres": "%(outres)s",
	"x_offset": "%(x_offset)s",
	"y_offset": "%(y_offset)s",
	"fps": "%(fps)s",
	"quality": "%(quality)s",
	"bitrate": "%(bitrate)s",
	"threads": "%(threads)s",
	"show_region": "%(show_region)s"\n}""" % d)
		
		fob.close()
		
	def on_button_reset_streamkey_clicked(self, window):
		warning = StreamKey()
	
	# Function to make the program backwards compatible with the old config files
	def load_legacy_config(self):
		try:
			fob = open(os.path.join(home, ".config/castawesome/.twitch_key"), "r")
			key = fob.read()
			fob.close()
			
			if key == "":
				warning = StreamKey()
			
			fob = open(os.path.join(home, ".config/castawesome/config.txt"), "r")
			lines = fob.readlines()
			fob.close()
			
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
			print "Couldn't load config files!"

# Stream key warning dialog
class StreamKey():
	def __init__(self):
		self.builder = Gtk.Builder()
		try:
			self.builder.add_from_file(STREAMKEY_UI_FILE1)
			print "Loaded " + STREAMKEY_UI_FILE1
		except:
			self.builder.add_from_file(STREAMKEY_UI_FILE2)
			print "Loaded " + STREAMKEY_UI_FILE2
		self.window = self.builder.get_object("warning")
		self.builder.connect_signals(self)
		self.window.show_all()
	
	def on_button_ok_clicked(self, window):
		fob = open(os.path.join(home, ".config/castawesome/.twitch_key"), "w")
		fob.write(self.builder.get_object("entry_streamkey").get_text())
		fob.close()
		
		self.window.destroy()

# About window
class About():
	def __init__(self):
		self.builder = Gtk.Builder()
		try:
			self.builder.add_from_file(ABOUT_UI_FILE1)
		except:
			self.builder.add_from_file(ABOUT_UI_FILE2)
		window = self.builder.get_object("about")
		window.show_all()

# Program main function
def main():
	if len(sys.argv) > 1 and sys.argv[1] == "test":
		print "Castawesome is ok"
		sys.exit(0)
	app = GUI()
	Gtk.main()
	
	return 0
		
if __name__ == "__main__":
	sys.exit(main())

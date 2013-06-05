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

from gi.repository import Gtk, GdkPixbuf, Gdk
import gobject
import os, sys, signal
import time
import thread
import subprocess, shlex


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
		except:
			self.builder.add_from_file(UI_FILE2)
		self.builder.connect_signals(self)

		window = self.builder.get_object('window')

		self.settings = Settings()
		
		window.show_all()

		self.counter_sec = 0
		self.counter_min = 0
		
		# Update timer every second
		gobject.timeout_add_seconds(1, self.update_timer)

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
		fob = open(home + "/.config/castawesome/.twitch_key", "r")
		twitch_key = fob.read().rstrip()
		fob.close()
		
		# Setting up audio channels for audio input
		self.audiochannels = ""
		
		for x in range(int(self.settings.get_audio_channels())):
			self.audiochannels += " -f alsa -ac " + str(x + 1) + " -i pulse"
		print self.audiochannels
		
		# Avconv is supplied with user's settings and executed
		command = str('avconv -f x11grab' + ' -show_region ' + self.settings.get_show_region() + ' -s ' + self.settings.get_inres() + ' -r "' + self.settings.get_fps() + '" -i :0.0+' + self.settings.get_x_offset() + ',' + self.settings.get_y_offset() + '  ' + self.audiochannels + ' -vcodec libx264 -s ' + self.settings.get_outres() + ' -preset ' + self.settings.get_quality() + ' -acodec libmp3lame -ar 44100 -threads ' + self.settings.get_threads() + ' -qscale 3 -b ' + self.settings.get_bitrate() + ' -bufsize 512k -f flv "rtmp://live.justin.tv/app/' + twitch_key + '"')
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
	audio_channels = ""		# Number of Pulseaudio channels
	bitrate = ""			# Bitrate (+300k usually is fine)
	threads = ""			# Amount of threads

	def __init__(self):
		if not os.system("mkdir ~/.config/castawesome"):
			# Configuration files are missing, create them and add default settings
			os.system("touch ~/.config/castawesome/.twitch_key")
			
			# Default settings for the user
			fob = open(home + "/.config/castawesome/config.txt", "w")
			fob.write("1280x720\n")
			fob.write("1280x720\n")
			fob.write("0\n")
			fob.write("0\n")
			fob.write("25\n")
			fob.write("medium\n")
			fob.write("1")
			fob.write("400k\n")
			fob.write("1\n")
			fob.write("1")
			fob.close()
			
		else:
			print "Config files exist..."
		try:
			fob = open(home + "/.config/castawesome/.twitch_key", "r")
			key = fob.read()
			fob.close()
			
			if key == "":
				warning = StreamKey()
			
			fob = open(home + "/.config/castawesome/config.txt", "r")
			lines = fob.readlines()
			fob.close()
			
			self.inres = lines[0].lstrip().rstrip()
			self.outres = lines[1].lstrip().rstrip()
			self.x_offset = lines[2].lstrip().rstrip()
			self.y_offset = lines[3].lstrip().rstrip()
			self.fps = lines[4].lstrip().rstrip()
			self.quality = lines[5].lstrip().rstrip()
			self.audio_channels = lines[6].lstrip().rstrip()
			self.bitrate = lines[7].lstrip().rstrip()
			self.threads = lines[8].lstrip().rstrip()
			self.show_region = lines[9].lstrip().rstrip()
		except:
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
		self.builder.get_object("entry_audiochannels").set_text(self.audio_channels)
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
		
	def get_audio_channels(self):
		return self.audio_channels

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
		self.audio_channels = self.builder.get_object("entry_audiochannels").get_text()
		self.bitrate = self.builder.get_object("entry_bitrate").get_text()
		self.threads = self.builder.get_object("entry_threads").get_text()
		self.show_region = self.builder.get_object("entry_region").get_text()

		# Save configs in homefolder
		fob = open(home + "/.config/castawesome/config.txt", "w")

		fob.write(self.inres + "\n")
		fob.write(self.outres + "\n")
		fob.write(self.x_offset + "\n")
		fob.write(self.y_offset + "\n")
		fob.write(self.fps + "\n")
		fob.write(self.quality + "\n")
		fob.write(self.audio_channels + "\n")
		fob.write(self.bitrate + "\n")
		fob.write(self.threads + "\n")
		fob.write(self.show_region + "\n")
		
		fob.close()
		
	def on_button_reset_streamkey_clicked(self, window):
		warning = StreamKey()

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
		fob = open(home + "/.config/castawesome/.twitch_key", "w")
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

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
CUSTOM_UI_FILE1 = "castawesome_custom.ui"
CUSTOM_UI_FILE2 = "/usr/local/share/castawesome/ui/castawesome_custom.ui"
WEBCAM_UI_FILE1 = "castawesome_webcam.ui"
WEBCAM_UI_FILE2 = "/usr/local/share/castawesome/ui/castawesome_webcam.ui"

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
			subprocess.call("ps -ef | awk '$3 == \"" + str(self.process.pid) + "\" {print $2}' | xargs kill -9", shell=True)
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
		
		# Decide whether to enable visible screen regions
		if self.settings.get_show_region():
			show_region = "1"
		else:
			show_region = "0"
		
		# Avconv is supplied with user's settings and executed
		parameters = {"inres" : self.settings.get_inres(), "outres" : self.settings.get_outres(), "x_offset" : self.settings.get_x_offset(),
		"y_offset" : self.settings.get_y_offset(), "fps" : self.settings.get_fps(), "quality" : self.settings.get_quality(),
		"bitrate" : self.settings.get_bitrate(), "threads" : self.settings.get_threads(), "show_region" : show_region,
		"service" : self.settings.get_service(), "watermark" : '-vf "movie=%(watermark_file)s [watermark]; [in][watermark] overlay=0:0 [out]"' % {"watermark_file" : self.settings.get_watermark_file()},
		"watermark_file" : self.settings.get_watermark_file(), "web_placement" : self.settings.get_webcam_placement(), "web_resolution" : self.settings.get_webcam_resolution()
		}
		
		parameters["keyint"] = str(int(parameters["fps"]) * 2)
		print parameters["keyint"]
		
		print self.settings.get_webcam()
		
		if self.settings.get_watermark():
			# Look at this awesomeness! LOOK AT IT!
			command = str('avconv -f x11grab -show_region %(show_region)s -s %(inres)s -framerate " %(fps)s" -i :0.0+%(x_offset)s,%(y_offset)s -i %(watermark_file)s -f pulse -ac 1 -i default -vcodec libx264 -filter_complex '+ "'overlay=0:main_h-overlay_h-0'" + ' -s %(outres)s -preset %(quality)s -acodec libmp3lame -ar 44100 -threads %(threads)s -qscale 3 -b:a 128k -b:v %(bitrate)s -maxrate %(bitrate)s -minrate %(bitrate)s -g %(keyint)s -bufsize %(bitrate)s -pix_fmt yuv420p -f flv "%(service)s' + twitch_key + '"') % parameters
		elif self.settings.get_webcam():
			command = str('avconv -f x11grab -show_region %(show_region)s -s %(inres)s -framerate " %(fps)s" -i :0.0+%(x_offset)s,%(y_offset)s -f v4l2 -video_size %(web_resolution)s -framerate %(fps)s -i /dev/video0 -f pulse -ac 1 -i default -vcodec libx264 -filter_complex '+ "'overlay=%(web_placement)s,format=yuv420p[out]' -map '[out]'" + ' -s %(outres)s -preset %(quality)s -acodec libmp3lame -ar 44100 -threads %(threads)s -qscale 3 -b:a 128k -b:v %(bitrate)s -maxrate %(bitrate)s -minrate %(bitrate)s -g %(keyint)s -bufsize %(bitrate)s -pix_fmt yuv420p -f flv "%(service)s' + twitch_key + '"') % parameters
		else:
			command = str('avconv -f x11grab -show_region %(show_region)s -s %(inres)s -framerate " %(fps)s" -i :0.0+%(x_offset)s,%(y_offset)s -f pulse -ac 1 -i default -vcodec libx264 -s %(outres)s -preset %(quality)s -acodec libmp3lame -ar 44100 -threads %(threads)s -qscale 3 -b:a 128k -b:v %(bitrate)s -maxrate %(bitrate)s -minrate %(bitrate)s -g %(keyint)s -bufsize %(bitrate)s -pix_fmt yuv420p -f flv "%(service)s' + twitch_key + '"') % parameters
		print command
		# Start a subprocess to handle avconv
		self.process = subprocess.Popen(command, shell=True)
		#os.system(command + " &")
		
	def update_timer(self):
		# Just minute/second counter, nothing fancy here
		if self.streaming:
			self.counter_sec += 1
			if(self.counter_sec == 60):
				self.counter_min += 1
				self.counter_sec = 0

			label = self.builder.get_object("label_timer")
			label.set_text("Time: " + str(self.counter_min) + ":" + str(self.counter_sec))
		else:
			self.counter_min = 0
			self.counter_sec = 0
			
		return True
		
	def destroy(self, window):
		if self.streaming:
			# Kill the subprocess and end the stream
			self.process.kill()
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
	show_region = ""		# Show or don't show capture region
	watermark = ""			# Enable/Disable watermarking
	watermark_file = ""		# Filename of the watermark
	webcam = ""				# Enable/Disable webcam
	webcam_placement = ""	# Placement of the webcam overlay
	webcam_resolution = ""	# Resolution of the webcam
	service = ""			# The streaming service in use

	def __init__(self):
		try:
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
	"show_region": "1",\n
	"use_watermark" : "False",\n
	"use_webcam" : "False",\n
	"webcam_placement" : "0:0",\n
	"webcam_resolution" : "320x200",\n
	"service": "rtmp://live.twitch.tv/app/"\n
}""")
				fob.close()
			except:
				print "Config files exist..."
			
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
				print lines
				
				self.inres = lines["inres"]
				self.outres = lines["outres"]
				self.x_offset = lines["x_offset"]
				self.y_offset = lines["y_offset"]
				self.fps = lines["fps"]
				self.quality = lines["quality"]
				self.bitrate = lines["bitrate"]
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
		except:
			print "An error occured: " + str(sys.exc_info())
			print "Couldn't load config files!"
		try:	
			self.builder = Gtk.Builder()
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
		self.builder.get_object("entry_bitrate").set_text(self.bitrate)
		self.builder.get_object("entry_threads").set_text(self.threads)
		
		# Set the capture_region switch to the correct state
		self.builder.get_object("switch_capture_region").set_active(self.show_region)
		
		# If watermarking has been enabled, set the filenames and switches
		if self.watermark:
			self.builder.get_object("switch_watermark").set_active(self.watermark)
			self.builder.get_object("filechooserbutton_watermark").set_filename(self.watermark_file)
		
		# Set the webcam toggle status
		print "Webcam: " + str(self.webcam)
		self.builder.get_object("switch_enable_webcam").set_active(self.webcam)
		
		# Various "models" for service and preset lists
		services = [
			['rtmp://live.twitch.tv/app/', 'Twitch.tv'],
			['rtmp://a.rtmp.youtube.com/live2/', 'YouTube'],
			['rtmp://live.hitbox.tv/push/', 'Hitbox.tv'],
			['rtmp://live.us.picarto.tv/golive/', "Picarto.tv"],
			["none", "Custom"]
		]
		
		presets = [
			['ultrafast', 'ultrafast'],
			['superfast', 'superfast'],
			['veryfast', 'veryfast'],
			['faster', 'faster'],
			['fast', 'fast'],
			['medium', 'medium'],
			['slow', 'slow'],
			['slower', 'slower'],
			['veryslow', 'veryslow'],
		]
		
		# Append services and presets to the GTK's liststores
		for item in services:
			self.builder.get_object("list_services").append(item)
		for otheritem in presets:
			self.builder.get_object("list_presets").append(otheritem)
		
		# Stupid hack for GTK's weirdness
		cell = Gtk.CellRendererText()
		self.builder.get_object("combo_preset_selector").pack_start(cell, True)
		self.builder.get_object("combo_preset_selector").add_attribute(cell, 'text', 0)
		
		# Set the service selector based on the loaded configs
		if self.service == 'rtmp://live.twitch.tv/app/':
			self.builder.get_object("combo_service_selector").set_active(0)
		elif self.service == 'rtmp://a.rtmp.youtube.com/live2/':
			self.builder.get_object("combo_service_selector").set_active(1)
		elif self.service == 'rtmp://live.hitbox.tv/push/':
			self.builder.get_object("combo_service_selector").set_active(2)
		elif self.service == 'rtmp://live.us.picarto.tv/golive/':
			self.builder.get_object("combo_service_selector").set_active(3)
		else:
			self.builder.get_object("combo_service_selector").set_active(4)
		
		# Do the same to quality (compression) presets
		if self.quality == "ultrafast":
			self.builder.get_object("combo_preset_selector").set_active(0)
		elif self.quality == "superfast":
			self.builder.get_object("combo_preset_selector").set_active(1)
		elif self.quality == "veryfast":
			self.builder.get_object("combo_preset_selector").set_active(2)
		elif self.quality == "faster":
			self.builder.get_object("combo_preset_selector").set_active(3)
		elif self.quality == "fast":
			self.builder.get_object("combo_preset_selector").set_active(4)
		elif self.quality == "medium":
			self.builder.get_object("combo_preset_selector").set_active(5)
		elif self.quality == "slow":
			self.builder.get_object("combo_preset_selector").set_active(6)
		elif self.quality == "slower":
			self.builder.get_object("combo_preset_selector").set_active(7)
		elif self.quality == "veryslow":
			self.builder.get_object("combo_preset_selector").set_active(8)
		
		# Apply previous configs
		self.on_button_apply_clicked(0)
		
		window.show_all()
		
		# If watermarking is disabled, hide the watermarking options
		if self.watermark == False:
			self.builder.get_object("box_watermarking").hide()

# All the getters, one for each value
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
		
	def get_watermark(self):
		return self.watermark
		
	def get_watermark_file(self):
		return self.watermark_file
	
	def get_webcam(self):
		return self.webcam
	
	def get_webcam_placement(self):
		return self.webcam_placement
	
	def get_webcam_resolution(self):
		return self.webcam_resolution
	
	def get_service(self):
		return self.service
	
	def get_watermark(self):
		return self.watermark
	
	def on_combo_preset_selector_changed(self, widget):
		model = self.builder.get_object("combo_preset_selector").get_model()
		active = self.builder.get_object("combo_preset_selector").get_active()
		if active >= 0:
			self.quality = model[active][0]
	
	def on_combo_service_selector_changed(self, widget):
		model = self.builder.get_object("combo_service_selector").get_model()
		active = self.builder.get_object("combo_service_selector").get_active()
		if active >= 0:
			self.service = model[active][0]
		print self.service
	
	def on_filechooserbutton_watermark_file_set(self, widget):
		self.watermark_file = widget.get_filename()
	
	def on_toggle_capture_region_toggled(self, widget):
		self.show_region = widget.get_active()
		
		print self.show_region
		
	def on_toggle_webcam_toggled(self, widget):
		self.webcam = widget.get_active()
		
		if self.webcam:
			self.builder.get_object("box_webcam").show()
		else:
			self.builder.get_object("box_webcam").hide()
		
		print self.webcam
	
	def on_toggle_watermarking_toggled(self, widget):
		self.watermark = widget.get_active()
		
		if self.watermark:
			self.builder.get_object("box_watermarking").show()
		else:
			self.builder.get_object("box_watermarking").hide()
		print self.watermark
	
	def on_button_apply_clicked(self, window):
		self.inres = self.builder.get_object("entry_inres").get_text()
		self.outres = self.builder.get_object("entry_outres").get_text()
		self.x_offset = self.builder.get_object("entry_xoffset").get_text()
		self.y_offset = self.builder.get_object("entry_yoffset").get_text()
		self.fps = self.builder.get_object("entry_fps").get_text()
		self.bitrate = self.builder.get_object("entry_bitrate").get_text()
		self.threads = self.builder.get_object("entry_threads").get_text()

		# Save configs in homefolder
		fob = open(os.path.join(home, ".config/castawesome/config.txt"), "w")
		# We will use dictionary based formatting expressions
		d = {"inres" : self.inres, "outres" : self.outres, "x_offset" : self.x_offset,
		"y_offset" : self.y_offset, "fps" : self.fps, "quality" : self.quality,
		"bitrate" : self.bitrate, "threads" : self.threads,
		"show_region" : str(self.show_region), "use_watermark" : str(self.watermark), 
		"watermark_file" : self.watermark_file, "webcam" : str(self.webcam), 
		"web_placement" : self.webcam_placement, "web_resolution" : self.webcam_resolution,
		"service" : self.service
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
	"show_region": "%(show_region)s",
	"use_watermark" : "%(use_watermark)s",
	"watermark_file" : "%(watermark_file)s",
	"use_webcam" : "%(webcam)s",
	"webcam_placement" : "%(web_placement)s",
	"webcam_resolution" : "%(web_resolution)s",
	"service": "%(service)s"\n}""" % d)
		
		fob.close()
		
	def on_button_custom_service_clicked(self, window):
		custom = CustomService(self)
	
	def on_button_reset_streamkey_clicked(self, window):
		warning = StreamKey()
	
	def on_button_configure_webcam_clicked(self, window):
		self.webcamconfig = WebcamConfig(self)
	
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

# Custom Service Setup
class CustomService():
	def __init__(self, parent):
		self.parent = parent
		self.builder = Gtk.Builder()
		try:
			self.builder.add_from_file(CUSTOM_UI_FILE1)
			print "Loaded " + CUSTOM_UI_FILE1
		except:
			self.builder.add_from_file(CUSTOM_UI_FILE2)
			print "Loaded " + CUSTOM_UI_FILE2
		self.window = self.builder.get_object("custom_service")
		self.builder.connect_signals(self)
		self.window.show_all()
		
	def on_button_apply_custom_clicked(self, window):
		self.parent.service = self.builder.get_object("entry_rtmp_url").get_text()
		self.parent.builder.get_object("combo_service_selector").set_active(4)
		self.window.destroy()

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

# Webcam config
class WebcamConfig():
	placement = "0:0"
	res = ""
	
	def __init__(self, parent):
		self.parent = parent
		self.builder = Gtk.Builder()
		try:
			self.builder.add_from_file(WEBCAM_UI_FILE1)
		except:
			self.builder.add_from_file(WEBCAM_UI_FILE2)
		self.window = self.builder.get_object("webcam")
		self.builder.connect_signals(self)
		self.window.show_all()
		
		self.builder.get_object("entry_resolution").set_text(self.parent.webcam_resolution)
		
		if self.parent.webcam_placement == "0:0":
			self.builder.get_object("togglebutton_leftop").set_active(True)
		elif self.parent.webcam_placement == "0:main_h/2-h/2":
			self.builder.get_object("togglebutton_lefmid").set_active(True)
		elif self.parent.webcam_placement == "0:main_h-h":
			self.builder.get_object("togglebutton_lefbot").set_active(True)
		elif self.parent.webcam_placement == "main_w/2-w/2:0":
			self.builder.get_object("togglebutton_midtop").set_active(True)
		elif self.parent.webcam_placement == "main_w/2-w/2:main_h/2-h/2":
			self.builder.get_object("togglebutton_midmid").set_active(True)
		elif self.parent.webcam_placement == "main_w/2-w/2:main_h-h":
			self.builder.get_object("togglebutton_midbot").set_active(True)
		elif self.parent.webcam_placement == "main_w-w:0":
			self.builder.get_object("togglebutton_rigtop").set_active(True)
		elif self.parent.webcam_placement == "main_w-w:main_h/2-h/2":
			self.builder.get_object("togglebutton_rigmid").set_active(True)
		elif self.parent.webcam_placement == "main_w-w:main_h-h":
			self.builder.get_object("togglebutton_rigbot").set_active(True)
	
	def on_button_webcam_apply_clicked(self, widget):
		self.parent.webcam_placement = self.placement
		self.parent.webcam_resolution = self.builder.get_object("entry_resolution").get_text()
		
	# A bunch of toggleaction toggle event handlers
	def on_toggleaction_leftop_toggled(self, sender):
		if sender.get_active():
			self.placement = "0:0"
			self.builder.get_object("togglebutton_lefmid").set_active(False)
			self.builder.get_object("togglebutton_lefbot").set_active(False)
			self.builder.get_object("togglebutton_midtop").set_active(False)
			self.builder.get_object("togglebutton_midmid").set_active(False)
			self.builder.get_object("togglebutton_midbot").set_active(False)
			self.builder.get_object("togglebutton_rigtop").set_active(False)
			self.builder.get_object("togglebutton_rigmid").set_active(False)
			self.builder.get_object("togglebutton_rigbot").set_active(False)
	def on_toggleaction_lefmid_toggled(self, sender):
		if sender.get_active():
			self.placement = "0:main_h/2-h/2"
			self.builder.get_object("togglebutton_leftop").set_active(False)
			self.builder.get_object("togglebutton_lefbot").set_active(False)
			self.builder.get_object("togglebutton_midtop").set_active(False)
			self.builder.get_object("togglebutton_midmid").set_active(False)
			self.builder.get_object("togglebutton_midbot").set_active(False)
			self.builder.get_object("togglebutton_rigtop").set_active(False)
			self.builder.get_object("togglebutton_rigmid").set_active(False)
			self.builder.get_object("togglebutton_rigbot").set_active(False)
	def on_toggleaction_lefbot_toggled(self, sender):
		if sender.get_active():
			self.placement = "0:main_h-h"
			self.builder.get_object("togglebutton_leftop").set_active(False)
			self.builder.get_object("togglebutton_lefmid").set_active(False)
			self.builder.get_object("togglebutton_midtop").set_active(False)
			self.builder.get_object("togglebutton_midmid").set_active(False)
			self.builder.get_object("togglebutton_midbot").set_active(False)
			self.builder.get_object("togglebutton_rigtop").set_active(False)
			self.builder.get_object("togglebutton_rigmid").set_active(False)
			self.builder.get_object("togglebutton_rigbot").set_active(False)
		
	def on_toggleaction_midtop_toggled(self, sender):
		if sender.get_active():
			self.placement = "main_w/2-w/2:0"
			self.builder.get_object("togglebutton_leftop").set_active(False)
			self.builder.get_object("togglebutton_lefmid").set_active(False)
			self.builder.get_object("togglebutton_lefbot").set_active(False)
			self.builder.get_object("togglebutton_midmid").set_active(False)
			self.builder.get_object("togglebutton_midbot").set_active(False)
			self.builder.get_object("togglebutton_rigtop").set_active(False)
			self.builder.get_object("togglebutton_rigmid").set_active(False)
			self.builder.get_object("togglebutton_rigbot").set_active(False)
	def on_toggleaction_midmid_toggled(self, sender):
		if sender.get_active():
			self.placement = "main_w/2-w/2:main_h/2-h/2"
			self.builder.get_object("togglebutton_leftop").set_active(False)
			self.builder.get_object("togglebutton_lefmid").set_active(False)
			self.builder.get_object("togglebutton_leftop").set_active(False)
			self.builder.get_object("togglebutton_midtop").set_active(False)
			self.builder.get_object("togglebutton_midbot").set_active(False)
			self.builder.get_object("togglebutton_rigtop").set_active(False)
			self.builder.get_object("togglebutton_rigmid").set_active(False)
			self.builder.get_object("togglebutton_rigbot").set_active(False)
	def on_toggleaction_midbot_toggled(self, sender):
		if sender.get_active():
			self.placement = "main_w/2-w/2:main_h-h"
			self.builder.get_object("togglebutton_leftop").set_active(False)
			self.builder.get_object("togglebutton_lefmid").set_active(False)
			self.builder.get_object("togglebutton_lefbot").set_active(False)
			self.builder.get_object("togglebutton_midtop").set_active(False)
			self.builder.get_object("togglebutton_midmid").set_active(False)
			self.builder.get_object("togglebutton_rigtop").set_active(False)
			self.builder.get_object("togglebutton_rigmid").set_active(False)
			self.builder.get_object("togglebutton_rigbot").set_active(False)
		
	def on_toggleaction_rigtop_toggled(self, sender):
		if sender.get_active():
			self.placement = "main_w-w:0"
			self.builder.get_object("togglebutton_leftop").set_active(False)
			self.builder.get_object("togglebutton_lefmid").set_active(False)
			self.builder.get_object("togglebutton_lefbot").set_active(False)
			self.builder.get_object("togglebutton_midtop").set_active(False)
			self.builder.get_object("togglebutton_midmid").set_active(False)
			self.builder.get_object("togglebutton_midbot").set_active(False)
			self.builder.get_object("togglebutton_rigmid").set_active(False)
			self.builder.get_object("togglebutton_rigbot").set_active(False)
	def on_toggleaction_rigmid_toggled(self, sender):
		if sender.get_active():
			self.placement = "main_w-w:main_h/2-h/2"
			self.builder.get_object("togglebutton_leftop").set_active(False)
			self.builder.get_object("togglebutton_lefmid").set_active(False)
			self.builder.get_object("togglebutton_lefbot").set_active(False)
			self.builder.get_object("togglebutton_midtop").set_active(False)
			self.builder.get_object("togglebutton_midmid").set_active(False)
			self.builder.get_object("togglebutton_midbot").set_active(False)
			self.builder.get_object("togglebutton_rigtop").set_active(False)
			self.builder.get_object("togglebutton_rigbot").set_active(False)
	def on_toggleaction_rigbot_toggled(self, sender):
		if sender.get_active():
			self.placement = "main_w-w:main_h-h"
			self.builder.get_object("togglebutton_leftop").set_active(False)
			self.builder.get_object("togglebutton_lefmid").set_active(False)
			self.builder.get_object("togglebutton_lefbot").set_active(False)
			self.builder.get_object("togglebutton_midtop").set_active(False)
			self.builder.get_object("togglebutton_midmid").set_active(False)
			self.builder.get_object("togglebutton_midbot").set_active(False)
			self.builder.get_object("togglebutton_rigtop").set_active(False)
			self.builder.get_object("togglebutton_rigmid").set_active(False)

# About window
class About():
	def __init__(self):
		self.builder = Gtk.Builder()
		try:
			self.builder.add_from_file(ABOUT_UI_FILE1)
			self.builder.get_object('image').set_from_file("CastA1.png")
		except:
			self.builder.add_from_file(ABOUT_UI_FILE2)
			self.builder.get_object('image').set_from_file("/usr/local/share/castawesome/ui/CastA1.png")
		self.window = self.builder.get_object("about")
		self.window.show_all()

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

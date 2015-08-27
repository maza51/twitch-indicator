#!/usr/bin/python
# -*- coding: utf-8 -*-

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify
from gi.repository.GdkPixbuf import Pixbuf
import threading
import webbrowser
import subprocess
import traceback
import urllib
import shutil
import time
import re
import os
import sys
import json

sys.setrecursionlimit(1000000)

DIRICONS = os.path.dirname(__file__)+'/icons/'
DIRISETT = os.path.join(os.getenv("HOME"), ".config")
USERNAME = 'maza51'
MET = 1
NOTI = 1
PID = os.getpid()
ARR_STREAMERS = []
APPLET = None


def url_to_pixbuf(url):
    res = urllib.urlopen(url)
    input_stream = Gio.MemoryInputStream.new_from_data(res.read(), None)
    pixbuf = Pixbuf.new_from_stream(input_stream, None)
    return pixbuf


def update_streamers():
    global ARR_STREAMERS
    global APPLET

    twitch = Twitch()
    str_follows = twitch.get_follows_str()
    arr_streams = twitch.get_streams(str_follows)

    if cmp(ARR_STREAMERS, arr_streams):
        GLib.idle_add(APPLET.update_menu, arr_streams)
        if NOTI:
            if arr_streams and ARR_STREAMERS:
                for i in arr_streams:
                    new_stream = True
                    for k in ARR_STREAMERS:
                        if i['display_name'] == k['display_name']:
                            new_stream = False
                    if new_stream == True:
                        Notify.init("twitch-indicator")
                        notify = Notify.Notification.new(i['display_name'], i['status'], '')
                        notify.set_icon_from_pixbuf(i['logo'])
                        notify.set_timeout(3000)
                        notify.show()

    ARR_STREAMERS = arr_streams
    threading.Timer(30, update_streamers).start()


class Twitch:

    def __init__(self):
        self.url_follows = 'https://api.twitch.tv/kraken/users/{0}/follows/channels?limit=100&offset=0'
        self.url_channel = 'https://api.twitch.tv/kraken/streams?channel={0}&limit=100&offset=0'

    def get_follows_str(self):
        try:
            a = '0,'
            res = urllib.urlopen(self.url_follows.format(USERNAME)).read()
            try:
                json.loads(res)["error"]
                print 'Twitch Indicator: ' + json.loads(res)['message']
            except KeyError:
                for i in json.loads(res)["follows"]:
                    a = a + i['channel']['name']+','
            return a
        except Exception as err:
            print ("ERROR: {0}".format(traceback.format_exc()))
            return '0,'

    def get_streams(self, str_follows):
        try:
            a = []
            res = urllib.urlopen(self.url_channel.format(str_follows)).read()
            for i in json.loads(res)["streams"]:
                i = i['channel']
                try:
                    i['status']
                except KeyError:
                    i['status'] = 'Nope status'

                if i['logo']:
                    i['logo'] = url_to_pixbuf(i['logo'])
                else:
                    i['logo'] = Pixbuf.new_from_file(DIRICONS+'404_user.png')

                b = {
                    'display_name': i['display_name'],
                    'name': i['name'],
                    'logo': i['logo'],
                    'status': i['status']
                }
                a.append(b)
            return a
        except Exception as err:
            print ("ERROR: {0}".format(traceback.format_exc()))
            return []


class Show:

    def init(self, w, name):
        if MET == 1:
            threading.Thread(target=self.player, args=(name,)).start()
        else:
            self.browser(name)

    def player(self, name):
        p = subprocess.Popen('livestreamer twitch.tv/'+name+' best',
                             shell=True,
                             stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        for line in iter(p.stdout.readline, b''):
            if NOTI:
                result = re.finditer(r"Found matching plugin (.+)|error: (.+)",
                                     line,
                                     re.IGNORECASE | re.MULTILINE | re.DOTALL)
                for match in result:
                    pixbuf = Pixbuf.new_from_file(DIRICONS+'twitch-indicator.png')
                    Notify.init("twitch-indicator")
                    notify = Notify.Notification.new('Twitch Indicator', line, '')
                    notify.set_icon_from_pixbuf(pixbuf)
                    notify.set_timeout(2000)
                    notify.show()

    def browser(self, name):
        webbrowser.open('http://www.twitch.tv/'+name)


class Indicator:

    def __init__(self):
        self.icon = DIRICONS+'panel/twitch.svg'
        self.ind = appindicator.Indicator.new("twitch",
                                              self.icon,
                                              appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.ind.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.menu = Gtk.Menu()
        self.ind.set_menu(self.menu)

    def update_menu(self, arr_streams):
        for i in self.menu.get_children():
            self.menu.remove(i)

        if arr_streams:
            n = len(arr_streams)
            if n > 9:
                self.icon = DIRICONS+'panel/0.svg'
            else:
                self.icon = DIRICONS+'panel/'+str(n)+'.svg'

            for w in arr_streams:
                self.img = Gtk.Image()
                self.img.set_from_pixbuf(w['logo'])

                self.item = Gtk.ImageMenuItem(w['display_name'])
                self.item.set_image(self.img)
                self.item.set_always_show_image(True)
                self.item.connect("activate", Show().init, w['name'])
                self.menu.append(self.item)
        else:
            self.icon = DIRICONS+'panel/twitch.svg'

        self.ind.set_icon(self.icon)

        self.separator = Gtk.SeparatorMenuItem()
        self.menu.append(self.separator)

        self.item = Gtk.MenuItem("Preference")
        self.item.connect("activate", self.preference)
        self.menu.append(self.item)

        self.item = Gtk.MenuItem("Exit")
        self.item.connect("activate", self.quit)
        self.menu.append(self.item)

        self.menu.show_all()

    def preference(self, w):
        self.s = Settings()
        self.s.show_all()

    def quit(self, w):
        Gtk.main_quit()
        subprocess.Popen('kill ' + str(PID), shell=True)


class Settings(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Settings")
        self.set_size_request(200, 100)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(16)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(self.vbox)

        self.entry = Gtk.Entry()
        self.entry.set_text(USERNAME)
        self.entry.connect("changed", self.set_usr)
        self.entry.set_size_request(10, 10)
        self.vbox.pack_start(self.entry, True, True, 0)

        self.autostart = Gtk.CheckButton("Autostart Twitch indicator")
        self.autostart.connect("toggled", self.on_autostart)
        if os.path.exists(os.path.join(os.getenv("HOME"),
                          ".config/autostart/twitch-indicator.desktop")):
            self.autostart.set_active(True)
        self.vbox.pack_start(self.autostart, True, True, 0)

        self.noti = Gtk.CheckButton("Show Notification")
        self.noti.connect("toggled", self.on_notify)
        if NOTI == 1:
            self.noti.set_active(True)
        self.vbox.pack_start(self.noti, True, True, 0)

        self.button = Gtk.RadioButton.new_with_label_from_widget(None, "Open in browser")
        self.button.connect("toggled", self.on_ratio, 1)
        self.vbox.pack_start(self.button, False, False, 0)

        self.button = Gtk.RadioButton.new_from_widget(self.button)
        self.button.set_label("Open in livestreamer")
        self.button.connect("toggled", self.on_ratio, 2)
        if MET == 1:
            self.button.set_active(True)
        self.vbox.pack_start(self.button, False, False, 0)

        self.separator = Gtk.HSeparator()
        self.vbox.pack_start(self.separator, True, True, 10)

        self.label = Gtk.Label()
        self.label.set_markup("<big>Install Livestreamer</big>")
        self.vbox.pack_start(self.label, True, True, 1)

        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textbuffer = self.textview.get_buffer()
        self.textbuffer.set_text("sudo apt-get install python-pip\nsudo pip install livestreamer")
        self.vbox.pack_start(self.textview, True, True, 0)

    def save_sett(self):
        self.File = open(DIRISETT+"/twitch-indicator.cfg", 'w')
        self.File.write('{"n":"'+USERNAME+'","m":"'+str(MET)+'","t":"'+str(NOTI)+'"}')
        self.File.close()

    def on_notify(self, button):
        global NOTI
        if button.get_active():
            NOTI = 1
        else:
            NOTI = 0
        self.save_sett()

    def on_ratio(self, button, name):
        global MET
        if button.get_active():
            if name == 1:
                MET = 2
            else:
                MET = 1
        self.save_sett()

    def set_usr(self, button):
        global USERNAME
        USERNAME = self.entry.get_text()
        self.save_sett()

    def on_autostart(self, button):
        filestart = os.path.join(os.getenv("HOME"),
                                 ".config/autostart/twitch-indicator.desktop")
        pathstart = os.path.join(os.getenv("HOME"), ".config/autostart")
        if not os.path.exists(pathstart):
            os.mkdir(pathstart)
        if button.get_active():
            if not os.path.exists(filestart):
                shutil.copyfile("/usr/share/twitch-indicator/twitch-indicator.desktop",
                                filestart)
        else:
            if os.path.exists(filestart):
                os.remove(filestart)

if __name__ == '__main__':
    try:
        f = open(DIRISETT+"/twitch-indicator.cfg", 'r')
        txt = f.read()
        USERNAME = json.loads(txt)['n']
        MET = int(json.loads(txt)['m'])
        NOTI = int(json.loads(txt)['t'])
        f.close()
    except:
        f = open(DIRISETT+"/twitch-indicator.cfg", 'w')
        f.write('{"n":"maza51","m":"1","t":"1"}')
        f.close()

    APPLET = Indicator()
    APPLET.update_menu([])
    threading.Thread(target=update_streamers).start()
    Gtk.main()

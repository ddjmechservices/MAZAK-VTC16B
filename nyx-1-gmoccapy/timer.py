#!/usr/bin/env python
# -*- coding:UTF-8 -*-
"""
    This file will add some timer options to a additional panel to gmoccapy
    and demonstrats at the same time the possibilities you have introducing
    your own handler files and functions to that screen, showing the
    possibilities to modify the layout and behavior

    Copyright 2021 Norbert Schechner
    nieson@web.de

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""

import hal_glib                           # needed to make our own hal pins
import hal                                # needed to make our own hal pins
from gladevcp.persistence import IniFile  # we use this one to save the states of the widgets on shut down and restart
from gladevcp.persistence import widget_defaults
from gladevcp.persistence import select_widgets
import gtk
from gmoccapy import preferences
from gmoccapy import getiniinfo

from time import time
import gobject             # needed to add the timer for periodic


class TimerClass:

    def __init__(self, halcomp, builder, useropts):

        self.builder = builder
        self.halcomp = halcomp

        self.defaults = { IniFile.vars : { "machine_time"               : 0 ,
                                           "spindle_time"               : 0 ,
                                           "running_time"               : 0 ,
                                           "num_periodes_machine"       : 0 ,
                                           "num_periodes_spindle"       : 0 ,
                                         },
                                         
                        }

        get_ini_info = getiniinfo.GetIniInfo()
        prefs = preferences.preferences(get_ini_info.get_preference_file_path())
        theme_name = prefs.getpref("gtk_theme", "Follow System Theme", str)
        if theme_name == "Follow System Theme":
            theme_name = gtk.settings_get_default().get_property("gtk-theme-name")
        gtk.settings_get_default().set_string_property("gtk-theme-name", theme_name, "")

        self.ini_filename = __name__ + ".var"
        self.ini = IniFile(self.ini_filename, self.defaults, self.builder)
        self.ini.restore_state(self)

        # lets make our pins
        self.machine_on = hal_glib.GPin(halcomp.newpin("machine_on", hal.HAL_BIT, hal.HAL_IN))
        self.spindle_on = hal_glib.GPin(halcomp.newpin("spindle_on", hal.HAL_BIT, hal.HAL_IN))
        self.running = hal_glib.GPin(halcomp.newpin("running", hal.HAL_BIT, hal.HAL_IN))

        hal_glib.GPin(halcomp.newpin("periode_time_machine", hal.HAL_U32, hal.HAL_IN))
        hal_glib.GPin(halcomp.newpin("elapsed_periodes_machine", hal.HAL_U32, hal.HAL_OUT))
        self.halcomp["elapsed_periodes_machine"] = self.num_periodes_machine

        hal_glib.GPin(halcomp.newpin("alarm_machine", hal.HAL_BIT, hal.HAL_OUT))
        self.halcomp["alarm_machine"] = False
        self.reset_alarm_machine = hal_glib.GPin(halcomp.newpin("reset_alarm_machine", hal.HAL_BIT, hal.HAL_IN))
        self.reset_alarm_machine.connect("value_changed", self._reset_alarm)

        hal_glib.GPin(halcomp.newpin("periode_time_spindle", hal.HAL_U32, hal.HAL_IN))
        hal_glib.GPin(halcomp.newpin("elapsed_periodes_spindle", hal.HAL_U32, hal.HAL_OUT))
        self.halcomp["elapsed_periodes_spindle"] = self.num_periodes_spindle

        hal_glib.GPin(halcomp.newpin("alarm_spindle", hal.HAL_BIT, hal.HAL_OUT))
        self.halcomp["alarm_spindle"] = False
        self.reset_alarm_spindle = hal_glib.GPin(halcomp.newpin("reset_alarm_spindle", hal.HAL_BIT, hal.HAL_IN))
        self.reset_alarm_spindle.connect("value_changed", self._reset_alarm)

        # get all widgets and connect them
        self.lbl_machine_time = self.builder.get_object("lbl_machine_time")
        self.lbl_machine_time.connect("destroy", self._on_destroy)
        self.lbl_spindle_time = self.builder.get_object("lbl_spindle_time")
        self.lbl_running_time = self.builder.get_object("lbl_running_time")

        # we need to set the label values
        self.lbl_machine_time.set_text(self._get_label_text(self.machine_time))        
        self.lbl_spindle_time.set_text(self._get_label_text(self.spindle_time))        
        self.lbl_running_time.set_text(self._get_label_text(self.running_time))
        
        gobject.timeout_add(1000, self._periodic )  # time between calls to the function, in milliseconds

    def _reset_alarm(self, pin):
        print(pin.name)
        if not pin.get():
            return
        if pin.name == "reset_alarm_machine":
            self.num_periodes_machine += 1
            self.halcomp["elapsed_periodes_machine"] = self.num_periodes_machine
            self.halcomp["alarm_machine"] = False
        if pin.name == "reset_alarm_spindle":
            self.num_periodes_spindle += 1
            self.halcomp["elapsed_periodes_spindle"] = self.num_periodes_spindle
            self.halcomp["alarm_spindle"] = False


    def _periodic(self):
        if self.machine_on.get():
            self.machine_time += 1
            self.lbl_machine_time.set_text(self._get_label_text(self.machine_time))
            if self.machine_time > self.halcomp["periode_time_machine"] * 60 * (self.num_periodes_machine + 1): 
                if not self.halcomp["alarm_machine"]:
                    self.halcomp["alarm_machine"] = True
        if self.spindle_on.get():
            self.spindle_time += 1
            self.lbl_spindle_time.set_text(self._get_label_text(self.spindle_time))
            if self.spindle_time > self.halcomp["periode_time_spindle"] * 60 * (self.num_periodes_spindle + 1): 
                if not self.halcomp["alarm_spindle"]:
                    self.halcomp["alarm_spindle"] = True
        if self.running.get():
            self.running_time += 1
            self.lbl_running_time.set_text(self._get_label_text(self.running_time))
            
        return True


    def _get_label_text(self, seconds):
        hours = int(seconds / 3600)
        minutes = str(int(seconds / 60)).zfill(2)
        seconds = str(int(seconds % 60)).zfill(2)
        lbl_text = "{0:d}:{1}:{2}".format(hours, minutes, seconds)
        return lbl_text            

    def _on_destroy(self, obj, data = None):
        print("Destroy, save state")
        self.ini.save_state(self)


def get_handlers(halcomp, builder, useropts):
    return[TimerClass(halcomp, builder, useropts)]

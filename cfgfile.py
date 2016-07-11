# -*- coding: utf-8 -*-
#
# PyBorg: The python AI bot.
#
# Copyright (c) 2000, 2006 Tom Morton, Sebastien Dailly
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#        
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
import string


def _load_config(filename):
    """
    Load a config file returning dictionary of variables.
    """
    try:
        f = open(filename, "r")
    except IOError as e:
        return None

    stuff = {}
    line = 0

    while 1:
        line = line + 1
        s = f.readline()
        if s == "":
            break
        if s[0] == "#":
            continue

        # read if the string is above multiple lines
        while s.find("#") == -1:
            lecture = f.readline()
            if lecture == "":
                break

            # Convert old configuration system ( with \ at the end of line )
            if s[-2] == '\\':
                s = s[:-2]

            s = s[:s.rfind("\n")] + lecture
            line = line + 1

        s = s.split("=")
        try:
            stuff[string.strip(s[0])] = eval(string.strip(string.join(s[1:], "=")))
        except:
            print("Malformed line in %s line %d" % (filename, line))
            print("\t%s" % s)
            continue
    return stuff


def _save_config(filename, fields):
    """
    fields should be a dictionary. Keys as names of
    variables containing tuple (string comment, value).
    """
    f = open(filename, "w")

    # write the values with comments. this is a silly comment
    for key in list(fields.keys()):
        f.write("# " + fields[key][0] + " #\n")
        s = repr(fields[key][1])
        f.write(key + "\t= ")

        # Create a new line after each dic entry
        if s.find("],") != -1:
            cut_string = ""
            while s.find("],") != -1:
                position = s.find("],") + 3
                # cut_string = cut_string + s[:position] + "\\\n\t"
                cut_string = cut_string + s[:position] + "\n\t"
                s = s[position:]
            s = cut_string + s
            f.write(s + "\n")
            continue

        # If the line exceed a normal display ( 80 col ) cut it
        if len(s) > 80:
            cut_string = ""
            while len(s) > 80:
                position = s.rfind(",", 0, 80) + 1
                # cut_string = cut_string + s[:position] + "\\\n\t\t"
                cut_string = cut_string + s[:position] + "\n\t\t"
                s = s[position:]
            s = cut_string + s
        f.write(s + "\n")

    # f.write("# End of configuration #")
    f.close()


class cfgset:
    def load(self, filename, defaults):
        """
        Defaults should be key=variable name, value=
        tuple of (comment, default value)
        """
        self._defaults = defaults
        self._filename = filename

        for i in list(defaults.keys()):
            self.__dict__[i] = defaults[i][1]

        # try to laad saved ones
        vars = _load_config(filename)
        if vars == None:
            # none found. this is new
            self.save()
            return
        for i in list(vars.keys()):
            self.__dict__[i] = vars[i]

    def save(self):
        """
        Save borg settings
        """
        keys = {}
        for i in list(self.__dict__.keys()):
            # reserved
            if i == "_defaults" or i == "_filename":
                continue
            if i in self._defaults:
                comment = self._defaults[i][0]
            else:
                comment = ""
            keys[i] = (comment, self.__dict__[i])
        # save to config file
        _save_config(self._filename, keys)

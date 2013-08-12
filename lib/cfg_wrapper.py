#!/usr/bin/env python
# ConfigWrapper.py -- main file.
#    Copyright (C) 2013 Eugene Miller <theerm@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import ConfigParser

DEFAULTS = {
    "Netcasts": {
        "cue": False,
    },
    "password_salt": {
        "salt" : "",
    },
    "Misc": {
        "bedtime_mode": False
    },
    "postgres" : {
        "host": "127.0.0.1",
        "port": "5432",
        "username": "",
        "password": "",
        "database": "fmp"
    },
    "test": {
        "test_option": {"foo":"bar"}
    }
}

ALLOWED_TYPES = (str, int, bool, float, unicode)

class ConfigWrapper:
    def __init__(self, config_file=None, defaults=None):
        self.type_map = {}
        self.cfg = ConfigParser.ConfigParser()
        self.config_file = config_file
        if defaults is None:
            defaults = DEFAULTS
        self.defaults = defaults
        self.cfg.read(config_file)
        self.set_defaults()

    def set_defaults(self):
        
        for section, option_value in self.defaults.iteritems():
            for option, value in option_value.iteritems():
                self.add_to_typemap(section, option, value)
                if not self.cfg.has_option(section, option):
                    self.set(section, option, value)

    def read(self, config_file=None):
        if config_file is None:
            config_file = self.config_file
        self.cfg.read(config_file)

    def process_value(self, val, force=None):
        if force is None:
            return val
        if force == int:
            val = float(val)
        return force(val)

    def check_get_default(self, get_cmd, section, option, default=None, 
                          force=None):
        if default is None and section in self.defaults and option in self.defaults[section]:
            default = self.defaults[section][option]

        if default is None:
            val = get_cmd(section, option)
            return self.process_value(val, force)

        try:
            val = get_cmd(section, option) or default
        except ConfigParser.NoSectionError, e:
            self.add_section(section)
            self.set(section, option, default, force)
            val = get_cmd(section, option) or default
        except ConfigParser.NoOptionError:
            self.set(section, option, default, force)
            val = get_cmd(section, option) or default
        except ValueError:
            val = self.cfg.get(section, option) or default
        return self.process_value(val, force)

    def get(self, section, option, default=None, force=None, *args, **kwargs):
        try:
            return_type = None
            if force in ALLOWED_TYPES:
                return_type = force

            if return_type is None and section in self.type_map and \
               option in self.type_map[section]:
                if self.type_map[section][option] == bool:
                    return_type = bool
                if self.type_map[section][option] == float:
                    return_type = float
                if self.type_map[section][option] == int:
                    return_type = int

            if return_type is None:
                return_type = str

            if return_type in (str, unicode):
                return self.check_get_default(self.cfg.get, section, option,
                                              default, force)

            if return_type == int:
                return self.check_get_default(self.cfg.getint, section, option, 
                                              default, force)

            if return_type == bool:
                return self.check_get_default(self.cfg.getboolean, section, 
                                              option, default, force)

            if return_type == float:
                return self.check_get_default(self.cfg.getfloat, section, 
                                              option, default, force)
            

        except ConfigParser.NoSectionError, e:
            self.add_section(section)
            self.on_no_section(e, section, option, *args, **kwargs)
            if 'default' in kwargs:
                self.set(section, option, kwargs['default'])

    def on_no_section(self, e, section, option, *args, **kwargs):
        print "ConfigParser.NoSectionError:", e
        return self.add_section(section)

    def add_section(self, section):
        if not self.cfg.has_section(section):
            self.cfg.add_section(section)
            self.write()
        if section not in self.type_map:
            self.type_map[section] = {}

    def set(self, section, option, value, force=None, *args, **kwargs):
        self.add_to_typemap(section, option, value, force)
        self.cfg.set(section, option, "%s" % value)
        self.write()

    def add_to_typemap(self, section, option, value, force=None):
        self.add_section(section)
        if option not in self.type_map[section]:
            if force in ALLOWED_TYPES:
                self.type_map[section][option] = force
                return
            self.type_map[section][option] = type(value)

    def set_by_type(self, section, option, value, *args, **kwargs):
        try:
            if isinstance(value, (float, )):
                cfg.set(section, option, value)
            else:
                self.cfg.set(section, option, value)
        except ConfigParser.NoSectionError, e:
            if self.on_no_section(e, section, option, *args, **kwargs):
                self.cfg.set(section, option, value)

    def write(self):
        with open(self.config_file, 'wb') as cfg_fp:
            self.cfg.write(cfg_fp)

if __name__ == "__main__":
    cfg = ConfigWrapper("./test.conf", defaults=DEFAULTS)
    cfg.write()
    val = cfg.get('Netcasts', 'cue')
    print val, type(val)
    print "never made:", cfg.get("never", "made", default="foo", force=str).__repr__()
    print "my another test:", cfg.get("Tests", "bool", True, bool).__repr__()
    print "Unicode:", cfg.get("Tests", "unicode", 'My string', unicode).__repr__()
    print "Float:", cfg.get("Tests", "Float", 5.5, float).__repr__()
    print "Int:", cfg.get("Tests", "int", 5.5, int).__repr__()

import os

import bson


class ConfigurationError(Exception):
    pass


class Configuration(object):
    def __init__(self):
        super(Configuration, self).__init__()
        self.__configdir__ = os.path.join(
            os.environ.get("HOME"), ".config", "todo"
        )
        self.__configfile__ = os.path.join(self.__configdir__, "todo.conf")
        self.__config__ = None
        self._ensure()
        self._read()

    def _ensure(self):
        if not os.path.isdir(self.__configdir__):
            os.makedirs(self.__configdir__, mode=0o755)
        if not os.path.isfile(self.__configfile__):
            with open(self.__configfile__, "wb") as config:
                config.write(bson.dumps({}))

    def _read(self):
        with open(self.__configfile__, "rb") as config:
            self.__config__ = bson.loads(config.read())

    def _write(self):
        with open(self.__configfile__, "wb") as config:
            config.write(bson.dumps(self.__config__))

    def get(self):
        return self.__config__

    def set(self, config_dict):
        self.__config__ = config_dict
        self._write()

    def reset(self,):
        self.__config__ = {}
        self._write()

    def add_section(self, section):
        if section in self.__config__:
            raise ConfigurationError("Section \"{}\" already exists.".format(section))

        self.__config__.setdefault(section, {})
        self._write()

    def get_section(self, section):
        if section not in self.__config__:
            raise ConfigurationError("Section \"{}\" does not exist.".format(section))

        return self.__config__[section]

    def set_section(self, section, config):
        if section not in self.__config__:
            raise ConfigurationError("Invalid section: \"{}\"".format(section))
        self.__config__[section] = config
        self._write()

    def update_section(self, section, changes):
        if section not in self.__config__:
            raise ConfigurationError("Invalid section: \"{}\"".format(section))
        self.__config__[section].update(changes)
        self._write()

    def has_section(self, section):
        return section in self.__config__

    def reset_section(self, section):
        if section not in self.__config__:
            raise ConfigurationError("Invalid section: \"{}\"".format(section))
        self.__config__[section] = {}
        self._write()

    def delete_section(self, section):
        if section not in self.__config__:
            raise ConfigurationError("Invalid section: \"{}\"".format(section))
        del self.__config__[section]
        self._write()

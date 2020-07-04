# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import os
import platform
import subprocess
from typing import List
import xml.etree.ElementTree as ElementTree

class GWLocalGame(object):
    def __init__(self, game_dir, game_executable):
        self.__logger = logging.getLogger('gw2_local_game')
        self.__directory = game_dir
        self.__executable = game_executable
        self.__creationflags = 0x00000008 if platform.system() == 'Windows' else 0

    def get_app_size(self) -> int:
        total_size = 0
        try:
            for dirpath, _, filenames in os.walk(self.__directory):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except Exception:
            self.__logger.exception('get_app_size:')

        return total_size

    def exe_name(self) -> str:
        return os.path.basename(self.__executable)

    def run_game(self) -> None:
        subprocess.Popen([os.path.join(self.__directory, self.__executable)], creationflags=self.__creationflags, cwd=self.__directory)

    def uninstall_game(self) -> None:
        subprocess.Popen([os.path.join(self.__directory, self.__executable), '--uninstall'], creationflags=self.__creationflags, cwd=self.__directory)


def get_game_instances() -> List[GWLocalGame]:
    result = list()

    if platform.system() == 'Darwin':
        game_location = '/Applications/Guild Wars 2 64-bit.app'
        executable = 'Contents/MacOS/GuildWars2'
        if os.path.exists(os.path.join(game_location, executable)):
            result.append(GWLocalGame(game_location, executable))
        return result

    config_dir = os.path.expandvars('%APPDATA%\\Guild Wars 2\\')
    if not os.path.exists(config_dir):
        return result

    for _, _, files in os.walk(config_dir):
        for file_n in files:
            file_name = file_n.lower()
            if file_name.startswith('gfxsettings') and file_name.endswith('.exe.xml'):
                config = ElementTree.parse(os.path.join(config_dir,file_name)).getroot()

                game_dir = config.find('APPLICATION/INSTALLPATH').attrib['Value']
                game_executable = config.find('APPLICATION/EXECUTABLE').attrib['Value']

                if os.path.exists(os.path.join(game_dir,game_executable)):
                    result.append(GWLocalGame(game_dir.lower(),game_executable.lower()))

    return result

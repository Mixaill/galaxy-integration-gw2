import logging
import os
import subprocess
from typing import List
import xml.etree.ElementTree as ElementTree

class GWLocalGame(object):
    def __init__(self, game_dir, game_executable):
        self._dir = game_dir
        self._executable = game_executable

    def run_game(self):
        subprocess.Popen([os.path.join(self._dir,self._executable)], creationflags=0x00000008, cwd = self._dir)


def get_game_instances() -> List[GWLocalGame]:
    result = list()

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
                    result.append(GWLocalGame(game_dir,game_executable))

    return result

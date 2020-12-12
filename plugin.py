# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import asyncio
import logging
import json
import os
import platform
import sys
import time
from typing import Any, List, Optional
import webbrowser

#platform helper
def get_platform() -> str:
    system = platform.system()
    if system == 'Windows':
        return 'windows'

    if system == 'Darwin':
        return 'macos'

    logging.error('plugin/get_platform: unknown platform %s' % system)
    return 'unknown'

#expand sys.path
thirdparty =  os.path.join(os.path.dirname(os.path.realpath(__file__)),'3rdparty_%s/' % get_platform())
if thirdparty not in sys.path and os.path.exists(thirdparty):
    sys.path.insert(0, thirdparty)

#read manifest
menifest = None
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json")) as manifest:
    manifest = json.load(manifest)

#disable urllib3 logging
import urllib3
logging.getLogger("urllib3").propagate = False

#start sentry
try:
    import sentry_sdk
    sentry_sdk.init(
        "https://801708b080aa4699beb708e5ac909cc9@sentry.friends-of-friends-of-galaxy.org/3",
        release=("galaxy-integration-gw2@%s" % manifest['version']))
except Exception:
    logging.exception('plugin/bootstrap: failed to initialize sentry')

from galaxy.api.consts import OSCompatibility, Platform, LicenseType, LocalGameState
from galaxy.api.errors import BackendError, InvalidCredentials
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Achievement, Authentication, NextStep, Dlc, LicenseInfo, Game, GameTime, LocalGame
from galaxy.proc_tools import process_iter

import gw2.gw2_api
import gw2.gw2_authserver
import gw2.gw2_localgame

class GuildWars2Plugin(Plugin):
    """
    Guild Wars 2 Plugin for GOG Galaxy

    Implemented features:
      * ImportOwnedGames
      * ImportInstalledGames
      * LaunchGame
      * InstallGame
      * UninstallGame
      * ImportGameTime
      * ImportOSCompatibility
      * ImportAchievements
      * ImportLocalSize

    Missing features:
      * LaunchPlatformClient
      * ImportFriends
      * ImportUserPresence
      * ShutdownPlatformClient
      * ImportGameLibrarySettings
      * ImportSubscriptions
      * ImportSubscriptionGames
    """

    #constants
    GAME_ID = 'guild_wars_2'
    GAME_NAME = 'Guild Wars 2'
    SLEEP_CHECK_ACHIEVEMENTS = 1500
    SLEEP_CHECK_INSTANCES = 60
    SLEEP_CHECK_RUNNING = 5
    SLEEP_CHECK_RUNNING_ITER = 0.01


    def __init__(self, reader, writer, token):
        super().__init__(Platform(manifest['platform']), manifest['version'], reader, writer, token)

        self.__logger = logging.getLogger('plugin')

        self._gw2_api = gw2.gw2_api.GW2API()
        self._game_instances = None

        self.__task_check_for_achievements = None
        self.__task_check_for_instances = None
        self._task_check_for_running  = None

        self._last_state = LocalGameState.None_
        self.__imported_achievements = None

        self.__platform = get_platform()

    #
    # Authentication
    #

    async def authenticate(self, stored_credentials=None):
        #check stored credentials
        if stored_credentials:
            auth_result = await self._gw2_api.do_auth_apikey(stored_credentials['api_key'])
            if auth_result != gw2.gw2_api.GW2AuthorizationResult.FINISHED:
                self.__logger.warning('authenticate: stored credentials are invalid')
                raise InvalidCredentials()

            return Authentication(self._gw2_api.get_account_id(), self._gw2_api.get_account_name())

        #new auth
        self.__authserver = gw2.gw2_authserver.Gw2AuthServer(self._gw2_api)
        self.__logger.info('authenticate: no stored credentials')

        AUTH_PARAMS = {
            "window_title": "Login to Guild Wars 2",
            "window_width": 640,
            "window_height": 460,
            "start_uri": self.__authserver.get_uri(),
            "end_uri_regex": '.*finished'
        }
        if not await self.__authserver.start():
            self.__logger.error('authenticate: failed to start auth server', exc_info=True)
            raise BackendError()
        return NextStep("web_session", AUTH_PARAMS)


    async def pass_login_credentials(self, step, credentials, cookies):
        if self.__authserver is not None:
            await self.__authserver.shutdown()

        api_key = self._gw2_api.get_api_key()
        account_id = self._gw2_api.get_account_id()
        account_name = self._gw2_api.get_account_name()
        if (api_key is None) or (account_id is None) or (account_name is None):
            self.__logger.error('pass_login_credentials: invalid credentials')
            raise InvalidCredentials()

        self.store_credentials({'api_key': api_key})
        return Authentication(account_id, account_name)

    #
    # ImportOwnedGames
    #

    async def get_owned_games(self):
        free_to_play = False
        
        dlcs = list()
        for dlc in self._gw2_api.get_owned_games():
            if dlc == 'PlayForFree':
                free_to_play = True
                continue
            if dlc == 'GuildWars2':
                continue

            dlc_id = dlc
            dlc_name = dlc
            if dlc_id == 'HeartOfThorns':
                dlc_name = 'Heart of Thorns'
            elif dlc_id == 'PathOfFire':
                dlc_name = 'Path of Fire'

            dlcs.append(Dlc(dlc_id = dlc_id, dlc_title = dlc_name, license_info = LicenseInfo(license_type = LicenseType.SinglePurchase)))

        license_type = LicenseType.SinglePurchase
        if free_to_play:
            license_type = LicenseType.FreeToPlay

        return [ Game(game_id = self.GAME_ID, game_title = self.GAME_NAME, dlcs = dlcs, license_info = LicenseInfo(license_type = license_type)) ]

    #
    # ImportInstalledGames
    #

    async def get_local_games(self):
        self._game_instances = gw2.gw2_localgame.get_game_instances()
        if len(self._game_instances) == 0:
            self._last_state = LocalGameState.None_
            return []

        self._last_state = LocalGameState.Installed
        return [ LocalGame(game_id=self.GAME_ID, local_game_state = self._last_state) ]

    #
    # LaunchGame
    #

    async def launch_game(self, game_id):
        if game_id != self.GAME_ID:
            logging.warn('plugin/launch_game: unknown game_id %s' % game_id)
            return
        
        try:
            self._game_instances[0].run_game()
        except FileNotFoundError:
            logging.warning('plugin/launch_game: game executable is not found')
            self.update_local_game_status(LocalGame(game_id, LocalGameState.None_))

    #
    # InstallGame
    #

    async def install_game(self, game_id):
        if game_id != self.GAME_ID:
            logging.warn('plugin/install_game: unknown game_id %s' % game_id)
            return
        webbrowser.open('https://account.arena.net/welcome')

    #
    # UninstallGame
    #

    async def uninstall_game(self, game_id):
        if game_id != self.GAME_ID:
            logging.warn('plugin/uninstall_game: unknown game_id %s' % game_id)
            return
        try:
            self._game_instances[0].uninstall_game()
        except FileNotFoundError:
            logging.warning('plugin/uninstall_game: game executable is not found')
            self.update_local_game_status(LocalGame(game_id, LocalGameState.None_))

    #
    # ImportGameTime
    #

    async def get_game_time(self, game_id, context):
        if game_id != self.GAME_ID:
            logging.warn('plugin/get_game_time: unknown game_id %s' % game_id)
            return None

        time_played = int(self._gw2_api.get_account_age() / 60)
        last_played_time = self.persistent_cache.get('last_played')

        return GameTime(game_id = game_id, time_played = time_played, last_played_time = last_played_time)

    #
    # ImportOSCompatibility
    #

    async def get_os_compatibility(self, game_id: str, context: Any) -> Optional[OSCompatibility]:      
        if game_id != self.GAME_ID:
            logging.warn('plugin/get_game_time: unknown game_id %s' % game_id)
            return None

        return OSCompatibility.Windows | OSCompatibility.MacOS

    #
    # ImportAchievements
    #

    async def get_unlocked_achievements(self, game_id: str, context: Any) -> List[Achievement]:
        result = list()

        if game_id != self.GAME_ID:
            logging.warn('plugin/get_unlocked_achievements: unknown game_id %s' % game_id)
            return result

        if not self.__imported_achievements:
            self.__imported_achievements = list()

        self.__imported_achievements.clear()
        for key, value in (await self._gw2_api.get_account_achievements()).items():
            cache_key = 'achievement_%s' % key
            if cache_key not in self.persistent_cache:
                self.persistent_cache[cache_key] = int(time.time())

            result.append(Achievement(self.persistent_cache.get(cache_key), key, value))

        self.push_cache()
        return result

    #
    # ImportLocalSize
    #

    async def get_local_size(self, game_id: str, context: Any) -> Optional[int]:   
        if game_id != self.GAME_ID:
            logging.warn('plugin/get_local_size: unknown game_id %s' % game_id)
            return None

        if not self._game_instances:
            return None

        return await self._game_instances[0].get_app_size()

    #
    # Other
    #

    def tick(self):
        if not self._task_check_for_running or self._task_check_for_running.done():
            self._task_check_for_running = self.create_task(self.task_check_for_running_func(), "task_check_for_running_game")

        if not self.__task_check_for_instances or self.__task_check_for_instances.done():
            self.__task_check_for_instances = self.create_task(self.task_check_for_game_instances(), "task_check_for_instances")

        if not self.__task_check_for_achievements or self.__task_check_for_achievements.done():
            self.__task_check_for_achievements = self.create_task(self.task_check_for_achievements(), "task_check_for_achievements")

    async def shutdown(self) -> None:
        await self._gw2_api.shutdown()

    #
    # Internals
    #

    async def task_check_for_achievements(self):
        if self.__imported_achievements:
            for key, value in self._gw2_api.get_account_achievements().items():
                if key not in self.__imported_achievements:
                    self.__imported_achievements.append(key)
                    self.unlock_achievement(self.GAME_ID, Achievement(0, key, value))

        await asyncio.sleep(self.SLEEP_CHECK_ACHIEVEMENTS)


    async def task_check_for_game_instances(self):
        self._game_instances = gw2.gw2_localgame.get_game_instances()
        await asyncio.sleep(self.SLEEP_CHECK_INSTANCES)


    async def task_check_for_running_func(self):

        #skip status update if there is no instances
        if self._last_state == LocalGameState.None_ and not self._game_instances:
            await asyncio.sleep(self.SLEEP_CHECK_RUNNING)
            return

        #get exe names
        target_exes = list()
        for instance in self._game_instances:
            target_exes.append(instance.exe_name().lower())

        #check processes
        running = False
        if target_exes:    
            for proc_info in process_iter():
                if proc_info.binary_path is None:
                    continue
                if os.path.basename(proc_info.binary_path).lower() in target_exes:
                    running = True
                    break
                await asyncio.sleep(self.SLEEP_CHECK_RUNNING_ITER)

        #update state
        new_state = None
        if running:
            self.persistent_cache['last_played'] = int(time.time())
            self.push_cache()
            new_state = LocalGameState.Installed | LocalGameState.Running
        elif target_exes:
            new_state = LocalGameState.Installed
        else:
            new_state = LocalGameState.None_

        if self._last_state != new_state:
            self.update_local_game_status(LocalGame('guild_wars_2', new_state))
            self._last_state = new_state

        await asyncio.sleep(self.SLEEP_CHECK_RUNNING)


def main():
    create_and_run_plugin(GuildWars2Plugin, sys.argv)


if __name__ == "__main__":
    main()

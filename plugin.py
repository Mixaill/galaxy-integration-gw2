import asyncio
import logging
import os
import sys
from typing import List

#expand sys.path
thirdparty =  os.path.join(os.path.dirname(os.path.realpath(__file__)),'3rdparty\\')
if thirdparty not in sys.path:
    sys.path.insert(0, thirdparty)

from version import __version__

#Start sentry
import sentry_sdk
sentry_sdk.init(
    "https://fd007739e0054f6baceed3131fbfdbe5@sentry.openwg.net/3",
    release=("galaxy-integration-gw2@%s" % __version__))

from galaxy.api.errors import BackendError, InvalidCredentials
from galaxy.api.consts import Platform, LicenseType, LocalGameState
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Authentication, NextStep, Dlc, LicenseInfo, Game, GameTime, LocalGame

from gw2_api import GW2API
import gw2_localgame

class GuildWars2Plugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(Platform.GuildWars2, __version__, reader, writer, token)
        self._gw2_api = GW2API()
        self._game_instances = None

    async def authenticate(self, stored_credentials=None):
        if not stored_credentials:
            logging.info('No stored credentials')

            AUTH_PARAMS = {
                "window_title": "Login to Guild Wars 2",
                "window_width": 640,
                "window_height": 460,
                "start_uri": self._gw2_api.auth_server_uri(),
                "end_uri_regex": '.*finished'
            }

            if not self._gw2_api.auth_server_start():
                raise BackendError()

            return NextStep("web_session", AUTH_PARAMS)

        else:
            auth_passed = self._gw2_api.do_auth_apikey(stored_credentials['api_key'])
            if not auth_passed:
                logging.warning('plugin/authenticate: stored credentials are invalid')
                raise InvalidCredentials()
            
            return Authentication(self._gw2_api.get_account_id(), self._gw2_api.get_account_name())

    async def pass_login_credentials(self, step, credentials, cookies):
        self._gw2_api.auth_server_stop()

        api_key = self._gw2_api.get_api_key()
        if not api_key:
            logging.error('plugin/pass_login_credentials: api_key is None!')
            raise InvalidCredentials()

        self.store_credentials({'api_key': api_key})
        return Authentication(self._gw2_api.get_account_id(), self._gw2_api.get_account_name())

    async def get_local_games(self):
        self._game_instances = gw2_localgame.get_game_instances()
        if len(self._game_instances) == 0:
            return []

        return [ LocalGame(game_id='guild_wars_2', local_game_state = LocalGameState.Installed)]

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

        return [ Game(game_id = 'guild_wars_2', game_title = 'Guild Wars 2', dlcs = dlcs, license_info = LicenseInfo(license_type = license_type)) ]


    async def get_game_times(self):
        pass


    async def import_game_times(self, game_ids: List[str]) -> None:
        for game_id in game_ids:
            if game_id != 'guild_wars_2':
                continue

            self.game_time_import_success(GameTime(game_id = game_id, time_played = int(self._gw2_api.get_account_age() / 60), last_played_time = None))


    async def launch_game(self, game_id):
        if game_id != 'guild_wars_2':
            return
        
        self._game_instances[0].run_game()


    async def install_game(self, game_id):
        pass


    def tick(self):
        pass


def main():
    create_and_run_plugin(GuildWars2Plugin, sys.argv)


if __name__ == "__main__":
    main()

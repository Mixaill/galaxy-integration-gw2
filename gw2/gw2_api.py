# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import json
import os
import random
import string
import sys
import pprint
import threading
from urllib.parse import parse_qs
from typing import Dict, List

import common.mglx_http

from .gw2_constants import GW2AuthorizationResult

class GW2API(object):

    API_DOMAIN = 'https://api.guildwars2.com'

    API_URL_ACHIEVEMENTS = '/v2/achievements'
    API_URL_ACCOUNT = '/v2/account'
    API_URL_ACCOUNT_ACHIVEMENTS = '/v2/account/achievements'

    LOCALSERVER_HOST = '127.0.0.1'
    LOCALSERVER_PORT = 13338

    def __init__(self):
        self.__http = common.mglx_http.MglxHttp(user_agent='gog_gw2/0.4.2', verify_ssl=False)
        self.__logger = logging.getLogger('gw2_api')

        self._server_thread = None
        self._server_object = None

        self._api_key = None
        self._account_info = None

        self.__achievements_chunk_size = 50


    async def shutdown(self):
        await self.__http.shutdown()

    # 
    # Getters
    #

    def get_api_key(self) -> str:
        return self._api_key

    def get_account_id(self) -> str:
        if self._account_info is None:
            self.__logger.error('get_account_id: account info is None', exc_info=True)
            return None

        return self._account_info['id']

    def get_account_name(self) -> str:
        if self._account_info is None:
            self.__logger.error('get_account_name: account info is None', exc_info=True)
            return None

        return self._account_info['name']

    def get_owned_games(self) -> List[str]:
        if self._account_info is None:
            self.__logger.error('get_owned_games: account info is None', exc_info=True)
            return list()

        return self._account_info['access']

    def get_account_age(self) -> int:
        if self._account_info is None:
            self.__logger.error('get_owned_games: account info is None', exc_info=True)
            return None

        return self._account_info['age']

    async def get_account_achievements(self) -> Dict:
        result = dict()

        (status, achievements_account) = await self.__api_get_account_achievements(self._api_key)
        if status == 200:
            #select completed achievements
            ids_to_request = list()
            for achievement in achievements_account:
                if achievement['done'] == True:
                    ids_to_request.append(achievement['id'])
                    result[achievement['id']] = None

            #split requests in chunks
            def chunks(l, n):
                for i in range(0, len(l), n):
                    yield l[i:i + n]
            chunks = list(chunks(ids_to_request, self.__achievements_chunk_size))

            #request info for chunks
            for chunk in chunks:
                (status, achievements_info) = await self.__api_get_achievements_info(self._api_key, chunk)
                if status == 200 or status == 206:
                    for achievement in achievements_info:
                        result[achievement['id']] = achievement['name']
                else:
                    if (achievements_info is not None) and ('text' in achievements_info):
                        if achievements_info['text'] == 'all ids provided are invalid':
                            self.__logger.warning('get_account_achievements: all IDs are invalid')
                        else:
                            self.__logger.error('get_account_achievements: (%s, %s)' % (status, achievements_info['text']))
               
                    self.__logger.error('get_account_achievements: failed to get achievements info, code %s' % status)

        return result


    #
    # Authorization server
    #

    async def do_auth_apikey(self, api_key : str) -> GW2AuthorizationResult:
        self._api_key = None
        self._account_info = None

        if not api_key: 
            self.__logger.warn('do_auth_apikey: api_key is is None')
            return GW2AuthorizationResult.FAILED

        (status_code, account_info) = await self.__api_get_account_info(api_key)
 
        if status_code != 200:
            if 'text' in account_info:
                if account_info['text'] == 'Invalid access token':
                    return GW2AuthorizationResult.FAILED_INVALID_TOKEN

                if account_info['text'] == 'invalid key':
                    return GW2AuthorizationResult.FAILED_INVALID_KEY

                if account_info['text'] == 'no game account':
                    return GW2AuthorizationResult.FAILED_NO_ACCOUNT

                if account_info['text'] == 'ErrBadData':
                    return GW2AuthorizationResult.FAILED_BAD_DATA

                if account_info['text'] == 'ErrTimeout':
                    return GW2AuthorizationResult.FAILED_TIMEOUT

            self.__logger.error('do_auth_apikey: %s, %s' % (status_code, account_info))
            return GW2AuthorizationResult.FAILED

        if account_info is None:
            self.__logger.warn('do_auth_apikey: account info is None')
            return GW2AuthorizationResult.FAILED

        self._api_key = api_key
        self._account_info = account_info
        return GW2AuthorizationResult.FINISHED


    async def __api_get_response(self, api_key, url, parameters = None):
        result = None

        self.__http.update_headers({'Authorization': 'Bearer ' + api_key})

        resp = None
        try:
            resp = await self.__http.request_get(self.API_DOMAIN+url, params=parameters)
        except Exception:
            self.__logger.exception('__api_get_response: failed to perform GET request for url %s' % url)
            return (0, None)

        if resp.status == 400:
            self.__logger.warning('__api_get_response: TIMEOUT for url %s' % url)
        elif resp.status == 404:
            self.__logger.error('__api_get_response: NOT FOUND for url %s' % url)
        elif resp.status == 502:
            self.__logger.warning('__api_get_response: BAD GATEWAY for url %s' % url)

        try: 
            result = json.loads(resp.text)
        except Exception:
            logging.error('__api_get_response: failed to parse response %s for url %s' % (resp.text, url))


        return (resp.status, result)


    async def __api_get_account_info(self, api_key):
        return await self.__api_get_response(api_key, self.API_URL_ACCOUNT)


    async def __api_get_account_achievements(self, api_key):
        return await self.__api_get_response(api_key, self.API_URL_ACCOUNT_ACHIVEMENTS)


    async def __api_get_achievements_info(self, api_key, ids : List[int]):
        return await self.__api_get_response(api_key, self.API_URL_ACHIEVEMENTS, 'ids=' + ','.join(str(i) for i in ids))

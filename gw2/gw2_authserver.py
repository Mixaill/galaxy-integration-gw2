# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import os.path

import aiohttp

import common.mglx_webserver

from .gw2_constants import GW2AuthorizationResult

class Gw2AuthServer(common.mglx_webserver.MglxWebserver):

    def __init__(self, gw2api = None):
        super(Gw2AuthServer, self).__init__()

        self.__gw2api = gw2api

        self.add_route('GET', '/', self.handle_login_get)
        self.add_route('GET', '/login', self.handle_login_get)
        self.add_route('GET', '/login_baddata', self.handle_login_baddata_get)
        self.add_route('GET', '/login_failed', self.handle_login_baddata_get)
        self.add_route('GET', '/login_noaccount', self.handle_login_noaccount_get)
        self.add_route('GET', '/finished', self.handle_finished_get)

        self.add_route('POST', '/', self.handle_login_post)
        self.add_route('POST', '/login', self.handle_login_post)
    #
    # Handlers
    #

    async def handle_login_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/login.html'))

    async def handle_login_baddata_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/login_baddata.html'))

    async def handle_login_failed_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/login_failed.html'))

    async def handle_login_noaccount_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/login_noaccount.html'))

    async def handle_finished_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/login_noaccount.html'))

    async def handle_login_post(self, request):
        data = await request.post()

        #check for apikey field
        if 'apikey' not in data:
            raise aiohttp.web.HTTPFound('/login_baddata')

        #process authentication
        auth_result = None
        try:
            auth_result = await self.__gw2api.do_auth_apikey(data['apikey'])
        except Exception:
            self._logger.exception("exception on doing auth:")
            raise aiohttp.web.HTTPFound('/login_baddata')

        if auth_result == GW2AuthorizationResult.FINISHED:
            raise aiohttp.web.HTTPFound('/finished')
        elif auth_result == GW2AuthorizationResult.FAILED_NO_ACCOUNT:
            raise aiohttp.web.HTTPFound('/login_noaccount')
        elif auth_result == GW2AuthorizationResult.FAILED_BAD_DATA:
            raise aiohttp.web.HTTPFound('/login_baddata')
        else:
            raise aiohttp.web.HTTPFound('/login_failed')

        raise aiohttp.web.HTTPFound('/login_failed')

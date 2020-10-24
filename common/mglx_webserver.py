# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import asyncio
import os
import logging

import aiohttp
import aiohttp.web

class MglxWebserver():
    LOCALSERVER_DEFAULT_HOST = '127.0.0.1'
    LOCALSERVER_DEFAULT_PORT = 13337

    #
    # Init
    #

    def __init__(self, host = LOCALSERVER_DEFAULT_HOST, port = LOCALSERVER_DEFAULT_PORT):
        self._logger = logging.getLogger('mglx_webserver')

        self.__host = host
        self.__port = port

        self.__app = aiohttp.web.Application()

        self.__runner = None
        self.__site = None
        self.__task = None

    #
    # Routes
    #

    def add_route(self, request_type, url, handler):
        if request_type == 'GET':
            return self.__app.add_routes([aiohttp.web.get(url, handler)])
        elif request_type == 'POST':
            return self.__app.add_routes([aiohttp.web.post(url, handler)])
        else:
            self._logger('add_route: unknown request_type "%s"' % request_type)
            return None

    #
    # Info
    #

    def get_uri(self) -> str:
        return 'http://%s:%s/' % (self.__host, self.__port)

    #
    # Start/Stop
    #

    async def start(self) -> bool:

        if self.__task is not None:
            self._logger.warning('auth_server_start: auth server object is already exists')
            return False

        self.__task = asyncio.create_task(self.__worker(self.__host, self.__port))
        return True


    async def shutdown(self):    
        if self.__runner is not None:
            await self.__runner.cleanup()


    async def __worker(self, host, port):
        self.__runner = aiohttp.web.AppRunner(self.__app)
        await self.__runner.setup()
    
        self.__site = aiohttp.web.TCPSite(self.__runner, host, port)
        await self.__site.start()    

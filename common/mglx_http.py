# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import collections
import logging
import ssl
from typing import Any, Dict

import aiohttp
import certifi

class MglxHttp:
    HTTP_DEFAULT_USER_AGENT = 'mglx_http/1.0.0'
    
    def __init__(self, user_agent = HTTP_DEFAULT_USER_AGENT, verify_ssl = True):
        self.__user_agent = user_agent
        self.__logger = logging.getLogger('mglx_http')

        if verify_ssl:
            self.__sslcontext = ssl.create_default_context(cafile=certifi.where())
            self.__connector = aiohttp.TCPConnector(ssl_context=self.__sslcontext)
        else:
            self.__connector = aiohttp.TCPConnector(verify_ssl=False)

        self.__session_headers = {'User-Agent': self.__user_agent}
        self.__session = aiohttp.ClientSession(connector=self.__connector, headers = self.__session_headers)


    async def shutdown(self):
        await self.__session.close()

    def update_headers(self, headers: Dict):
        '''
        update HTTP headers
        '''
        self.__session_headers.update(headers)


    async def request(self, method: str, url: str, *, params: Any = None, data: Any = None, json: Any = None):
        response_status = None
        response_text = None

        if 'Referer' in self.__session_headers:
            self.__session_headers.pop('Referer')
    
        while True:
            try:
                async with self.__session.request(method, url, headers = self.__session_headers, params = params, data = data, json = json) as response:
                    response_text = await response.text()
                    response_status = response.status
                    if response_status == 202 and 'Location' in response.headers:
                        url = response.headers['Location']
                        self.__session_headers.update({'Referer': str(response.url)})
                        method = 'GET'
                    else:
                        break
            except TimeoutError:
                response_status = 408 #408 Request Timeout
                break

        return collections.namedtuple('MglxHttpResponse', ['status', 'text'])(response_status, response_text)

    async def request_get(self, url: str, params: Any = None) -> Any:
        return await self.request('GET', url, params = params)

    async def request_post(self, url: str, *, params: Any = None, data: Any = None, json: Any = None) -> Any:
        return await self.request('POST', url, params = params, data = data, json = json)

DEBUG = False

from http.server import HTTPServer, BaseHTTPRequestHandler
from enum import Enum
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

import requests

class GW2AuthorizationResult(Enum):
    FAILED = 0
    FAILED_INVALID_TOKEN = 1
    FAILED_INVALID_KEY = 2
    FAILED_NO_ACCOUNT = 3
    FAILED_BAD_DATA = 4
    FINISHED = 5

class GW2AuthorizationServer(BaseHTTPRequestHandler):
    backend = None

    def do_HEAD(self):
        return

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:       
            post_data = parse_qs(post_data)
        except:
            pass

        if self.path == '/login':
            self.do_POST_login(post_data)
        else:
            self.send_response(302)
            self.send_header('Location','/404')
            self.end_headers()

    def do_POST_login(self, data):

        data_valid = True
        if b'apikey' not in data:
            data_valid = False

        auth_result = False

        if data_valid:
            try:
                auth_result = self.backend.do_auth_apikey(data[b'apikey'][0].decode("utf-8"))
            except Exception:
                logging.exception("error on doing auth:")
 
        self.send_response(302)
        self.send_header('Content-type', "text/html")
        if auth_result == GW2AuthorizationResult.FINISHED:
            self.send_header('Location','/finished')
        elif auth_result == GW2AuthorizationResult.FAILED_NO_ACCOUNT:
            self.send_header('Location', '/login_noaccount')
        else:
            self.send_header('Location','/login_failed')

        self.end_headers()


    def do_GET(self):
        status = 200
        content_type = "text/html"
        response_content = ""

        try:
            filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\%s.html' % self.path)
            if os.path.isfile(filepath):
                response_content = open(filepath).read()
            else:
                filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\404.html')
                if os.path.isfile(filepath):
                    response_content = open(filepath).read()
                else:
                    response_content = 'ERROR: FILE NOT FOUND'

            self.send_response(status)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(bytes(response_content, "UTF-8"))
        except Exception:
            logging.exception('GW2AuthorizationServer/do_GET: error on %s' % self.path)


class GW2API(object):

    API_DOMAIN = 'https://api.guildwars2.com'
    API_URL_ACCOUNT = '/v2/account'

    LOCALSERVER_HOST = '127.0.0.1'
    LOCALSERVER_PORT = 13338

    def __init__(self):

        self._server_thread = None
        self._server_object = None

        self._api_key = None
        self._account_info = None

    # 
    # Getters
    #

    def get_api_key(self) -> str:
        return self._api_key

    def get_account_id(self) -> str:
        return self._account_info['id']

    def get_account_name(self) -> str:
        return self._account_info['name']

    def get_owned_games(self) -> List[str]:
        return self._account_info['access']

    def get_account_age(self) -> int:
        return self._account_info['age']

    #
    # Authorization server
    #

    def auth_server_uri(self) -> str:
        return 'http://%s:%s/login' % (self.LOCALSERVER_HOST, self.LOCALSERVER_PORT)

    def auth_server_start(self) -> bool:

        if self._server_thread is not None:
            logging.warning('GW2Authorization/auth_server_start: Auth server thread is already running')
            return False

        if self._server_object is not None:
            logging.warning('GW2Authorization/auth_server_start: Auth server object is exists')
            return False

        GW2AuthorizationServer.backend = self
        self._server_object = HTTPServer((self.LOCALSERVER_HOST, self.LOCALSERVER_PORT), GW2AuthorizationServer)
        self._server_thread = threading.Thread(target = self._server_object.serve_forever)
        self._server_thread.daemon = True
        self._server_thread.start()
        return True

    def auth_server_stop(self) -> bool:
        if self._server_object is not None:
            self._server_object.shutdown()
            self._server_object = None
        else:
            logging.warning('GW2Authorization/auth_server_stop: Auth server object is not exits')
            return False

        if self._server_thread is not None:
            self._server_thread.join()
            self._server_thread = None
        else:
            logging.warning('GW2Authorization/auth_server_stop: Auth server thread is not running')
            return False

    def do_auth_apikey(self, api_key : str) -> GW2AuthorizationResult:
        (status_code, account_info) = self.__api_get_account_info(api_key)

        if account_info is None:
            return GW2AuthorizationResult.FAILED

        if status_code != 200:
            if 'text' not in account_info:
                return GW2AuthorizationResult.FAILED

            if account_info['text'] == 'Invalid access token':
                return GW2AuthorizationResult.FAILED_INVALID_TOKEN

            if account_info['text'] == 'invalid key':
                return GW2AuthorizationResult.FAILED_INVALID_KEY

            if account_info['text'] == 'no game account':
                return GW2AuthorizationResult.FAILED_NO_ACCOUNT

            if account_info['text'] == 'ErrBadData':
                return GW2AuthorizationResult.FAILED_BAD_DATA

            logging.error('do_auth_apikey: %s, %s' % (status_code, account_info))
            return GW2AuthorizationResult.FAILED

        self._api_key = api_key
        self._account_info = account_info
        return GW2AuthorizationResult.FINISHED


    def __api_get_account_info(self, api_key):
        result = None

        resp = requests.get(self.API_DOMAIN+self.API_URL_ACCOUNT, params={'access_token': api_key})
        
        try: 
            result = json.loads(resp.text)
        except Exception:
            if resp.status_code != 502:
                logging.error('gw2api/__api_get_account_info: failed to parse response %s' % resp.text)


        return (resp.status_code, result)

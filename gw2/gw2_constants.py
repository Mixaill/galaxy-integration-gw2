# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

from enum import Enum

class GW2AuthorizationResult(Enum):
    FAILED = 0
    FAILED_INVALID_TOKEN = 1
    FAILED_INVALID_KEY = 2
    FAILED_NO_ACCOUNT = 3
    FAILED_BAD_DATA = 4
    FINISHED = 5
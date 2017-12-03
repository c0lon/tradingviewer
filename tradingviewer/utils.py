import json
import logging
from pprint import pprint

import aiohttp
from bs4 import BeautifulSoup


HTML_PARSER = 'html.parser'


async def get_soup(url):
    async with aiohttp.get(url) as response:
        if response.status != 200:
            return

        return BeautifulSoup(await response.text(), HTML_PARSER)


class GetLoggerMixin:
    ''' Adds a `_get_logger()` classmethod that returns the correctly
    named logger. The child class must have a `__loggername__` class variable.
    '''

    @classmethod
    def _logger(cls, name=''):
        logger_name = cls.__loggername__
        if name:
            logger_name += f'.{name}'

        return logging.getLogger(logger_name)


def pp(o):
    try:
        print(json.dumps(o, indent=2, sort_keys=True))
    except:
        pprint(o)

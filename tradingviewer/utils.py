import json
import logging
from pprint import pprint

import aiohttp
import requests


ACCOUNT_URL_FMT = 'https://www.tradingview.com/u/{account_name}'


async def get_account_info(account_name):
    account_url = ACCOUNT_URL_FMT.format(account_name=account_name)
    async with aiohttp.get(account_url) as response:
        if response.status != 200:
            return
        soup = BeautifulSoup(await response.text(), 'html.parser')

    account_info = {
        'name' : account_name,
        'url' : account_url
    }

    account_image = soup.find('img', class_='tv-profile__avatar-img')
    if account_image:
        account_info['image_url'] = account_image['src']

    return account_info


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

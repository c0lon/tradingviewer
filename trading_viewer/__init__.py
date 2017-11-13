import asyncio
from collections import defaultdict
from datetime import datetime
import json
import logging
import os

import aiohttp
from bs4 import BeautifulSoup
import discord
from discord.ext import commands


TRADINGVIEW_BASE_URL = 'https://www.tradingview.com'
ACCOUNT_URL_FMT = TRADINGVIEW_BASE_URL + '/u/{account_name}'
ACCOUNT_ICON_URL_FMT = 'https://s3.tradingview.com/userpics/{account_id}.png'
POST_IMAGE_URL_FMT = 'https://s3.tradingview.com/{first_letter}/{image_id}_big.png'



"""
read accounts from list
check each account
    get the html of each account page and check for new posts
    if new post:
        get all data from html
        save post id
        upload to discord
save account data
"""


class TradingViewer:
    def __init__(self, **config):
        self.account_file = config['account_file']
        if not os.path.isfile(self.account_file):
            raise OSError('Invalid account file: {}'.format(self.account_file))
        self.load_account_data()

        self.bot = commands.Bot(command_prefix=config['bot']['command_prefix'])
        self.interval = config['bot']['interval']
        self.channel_id = config['bot']['channel_id']

    def get_channel(self):
        return self.bot.get_channel(self.channel_id)
    channel = property(get_channel)

    def load_account_data(self):
        with open(self.account_file) as f:
            self.accounts = json.load(f)

    def save_account_data(self):
        with open(self.account_file, 'w+') as f:
            json.dump(self.accounts, f, indent=2, sort_keys=True)

    async def list_accounts(self):
        self.load_account_data()
        if self.accounts:
            accounts = '\n'.join(['* {}'.format(a) for a in self.accounts])
            message = 'Watching the following TradingView accounts:\n{}'.format(accounts)
        else:
            message = 'Not watching any TradingView accounts.'

        await self.bot.send_message(self.channel, message)

    async def add_account(self, account_name):
        logger = logging.getLogger('add_account')
        logger.debug(account_name)

        if account_name in self.accounts:
            message = 'Already watching account: {}'.format(account_name)
            logger.warning(message)
            await self.bot.send_message(self.channel, message)
            return

        account_url = ACCOUNT_URL_FMT.format(account_name=account_name)
        async with aiohttp.ClientSession() as session:
            async with aiohttp.get(account_url) as response:
                if response.status != 200:
                    message = 'Invalid TradingView account: {}'.format(account_name)
                    logger.warning(message)
                    await self.bot.send_message(self.channel, message)
                    return

        message = 'TradingView account added: {}\n{}'.format(account_name, account_url)
        logger.info(message)
        await self.bot.send_message(self.channel, message)

        account = {
            'url' : account_url,
            'handled' : []
        }
        self.accounts[account_name] = account
        await self.check_account(account_name)
        self.save_account_data()

        return True

    async def remove_account(self, account_name):
        logger = logging.getLogger('remove_account')
        logger.debug(account_name)

        if account_name not in self.accounts:
            message = 'Not watching TradingView account: {}'.format(account_name)
            logger.warning(message)
            await self.bot.send_message(self.channel, message)
            return

        message = 'Stopped following TradingView account: {}'.format(account_name)
        logger.info(message)
        await self.bot.send_message(self.channel, message)

        del self.accounts[account_name]
        self.save_account_data()

        return True

    async def watch_accounts(self):
        while True:
            self.load_account_data()
            for account_name in self.accounts:
                await self.check_account(account_name)

            self.save_account_data()
            await asyncio.sleep(self.interval)

    async def check_account(self, account_name):
        logger = logging.getLogger('check_account')
        logger.debug(account_name)

        account = self.accounts.get(account_name)
        if not account:
            logger.warning('not watching account: {}'.format(account_name))
            return
            
        async with aiohttp.ClientSession() as session:
            async with session.get(account['url']) as response:
                account_soup = BeautifulSoup(await response.text(), 'html.parser')

        latest_post_div = account_soup.find('div', class_='js-cb-item')
        if not latest_post_div:
            logger.debug('No posts for account: {}'.format(account_name))
            return

        latest_post_data = json.loads(latest_post_div['data-widget-data'])
        account_id = latest_post_data['user']['id']

        post_id = latest_post_data['id']
        if post_id in account['handled']:
            logger.debug('already handled: {}'.format(post_id))
            return

        post_url = '{}/{}'.format(TRADINGVIEW_BASE_URL,
                latest_post_data['published_chart_url'])
        post_image_id = latest_post_data['image_url']
        post_image_url = POST_IMAGE_URL_FMT.format(
            first_letter=post_image_id[0].lower(), image_id=post_image_id)

        post_description_elmt = latest_post_div.find('p',
            class_='tv-widget-idea__description-text')
        post_description = post_description_elmt.text.strip()

        post_timestamp = latest_post_div.find('span', class_='tv-widget-idea__time')
        post_datetime = datetime.fromtimestamp(float(post_timestamp['data-timestamp']))

        post = {
            'account' : {
                'name' : account_name,
                'url' : account['url'],
                'icon_url' : ACCOUNT_ICON_URL_FMT.format(account_id=account_id)
            },
            'market' : latest_post_data['name'],
            'url' : post_url,
            'image_url' : post_image_url,
            'description' : post_description,
            'timestamp' : post_datetime
        }
        logger.debug(post)

        if await self.upload_post(post):
            account['handled'].append(post_id)
            self.save_account_data()

    async def upload_post(self, post):
        msg = 'uploading post: {} {} ({})'.format(
            post['account']['name'], post['market'], post['url'])
        logging.getLogger('upload_post').info(msg, extra={'post' : post})

        embed = discord.Embed(title=post['market'], url=post['url'],
                timestamp=post['timestamp'], description=post['description'])
        embed.set_author(name=post['account']['name'],
            url=post['account']['url'], icon_url=post['account']['icon_url'])
        embed.set_image(url=post['image_url'])

        await self.bot.send_message(self.channel, embed=embed)
        return True

    @classmethod
    def watch(cls, **config):
        logger = logging.getLogger('TradingViewer.watch')
        logger.debug('start')

        viewer = cls(**config)

        @viewer.bot.event
        async def on_ready():
            viewer.bot.loop.create_task(viewer.watch_accounts())

        @viewer.bot.command()
        async def list():
            await viewer.list_accounts()

        @viewer.bot.command(pass_context=True)
        async def add(ctx, account_name : str):
            if ctx.message.channel != viewer.channel:
                return

            await viewer.add_account(account_name)

        @viewer.bot.command(pass_context=True)
        async def remove(ctx, account_name : str):
            if ctx.message.channel != viewer.channel:
                return

            await viewer.remove_account(account_name)

        viewer.bot.run(config['bot']['token'])

import asyncio

import discord
from discord.ext import commands

from .models.meta import (
    TradingViewerDBSession,
    transaction,
    )
from .models.tradingview_models import TradingViewAccount
from .utils import GetLoggerMixin


class TradingViewer(GetLoggerMixin):
    __loggername__ = f'{__name__}.TradingViewer'

    NAME = 'TradingViewer'

    def __init__(self, **config):
        self.bot = commands.Bot(command_prefix=config['command_prefix'])
        self.bot_token = config['token']
        self.channel_id = config['channel_id']
        self.interval = config['interval']

    def get_channel(self):
        return self.bot.get_channel(self.channel_id)
    channel = property(get_channel)

    async def add_account(self, account_name):
        with transaction(TradingViewerDBSession) as session:
            account = TradingViewAccount.get_by_name(session, account_name)
            added = False

            if account:
                embed = discord.Embed(title=f'Already watching {account_name}.', url=account.url)
                embed.set_image(url=account.image_url)
            else:
                account = await TradingViewAccount.add(session, account_name)
                if not account:
                    embed = discord.Embed(title=f'"{account_name}" is not a valid TradingView account.')
                else:
                    embed = discord.Embed(title=f'Added account {account_name}.', url=account.url)
                    embed.set_image(url=account.image_url)
                    added = True

            await self.bot.send_message(self.channel, embed=embed)

            if added:
                latest_posts = await account.get_new_posts(session, count=1)
                if latest_posts:
                    await self.upload_post(latest_posts[0])

    async def remove_account(self, account_name):
        with transaction(TradingViewerDBSession) as session:
            account = TradingViewAccount.get_by_name(session, account_name)
            if not account:
                embed = discord.Embed(title=f'Not watching "{account_name}".')
            else:
                embed = discord.Embed(title=f'Removed account {account_name}.', url=account.url)
                embed.set_image(url=account.image_url)
                TradingViewAccount.delete(session, account)

        await self.bot.send_message(self.channel, embed=embed)

    async def list_accounts(self):
        with transaction(TradingViewerDBSession) as session:
            accounts = TradingViewAccount.get_all(session)
            if not accounts:
                embed = discord.Embed(title='Not following any TradingView accounts.')
            else:
                embed = discord.Embed(title='Watching the following TradingView accounts:')
                for account in TradingViewAccount.get_all(session):
                    embed.add_field(name=account.name, value=account.url)

        await self.bot.send_message(self.channel, embed=embed)

    async def upload_post(self, post):
        embed = discord.Embed(title=post.title, url=post.url,
                timestamp=post.timestamp, description=post.description)
        embed.set_author(name=post.account.name, url=post.account.url,
                icon_url=post.account.image_url)
        embed.set_image(url=post.image_url)

        await self.bot.send_message(self.channel, embed=embed)

    async def _watch_for_new_posts(self):
        while True:
            with transaction(TradingviewerDBSession) as session:
                for new_post in TradingViewAccount.get_all_new_posts(session):
                    await self.upload_post(new_post)

            await asyncio.sleep(self.interval)

    def run(self):
        self.bot.run(self.bot_token)

    @classmethod
    def watch_for_new_posts(cls, **config):
        viewer = cls(**config)
        logger = cls._logger('watch_accounts')

        @viewer.bot.event
        async def on_ready():
            logger.debug('start')

        @viewer.bot.command()
        async def add(account_name : str):
            await viewer.add_account(account_name)

        @viewer.bot.command()
        async def remove(account_name : str):
            await viewer.remove_account(account_name)

        @viewer.bot.command()
        async def list():
            await viewer.list_accounts()

        viewer.bot.loop.create_task(viewer._watch_for_new_posts())
        viewer.run()

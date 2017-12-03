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
            account = session.query(TradingViewAccount) \
                    .filter(TradingViewAccount.name == account_name) \
                    .first()
            if account:
                embed = discord.Embed(title=f'Already watching account.', url=account.url)
                embed.add_field(name='Account Name', value=account.name)
                embed.set_image(url=account.image_url)
            else:
                account = await TradingViewAccount.add(session, account_name)
                if not account:
                    embed = discord.Embed(title=f'Account "{account_name}" does not exist.')
                else:
                    embed = discord.Embed(title=f'Added account {account_name}.', url=account.url,
                        image=account.image_url)

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

        viewer.bot.loop.create_task(viewer._watch_for_new_posts())
        viewer.run()

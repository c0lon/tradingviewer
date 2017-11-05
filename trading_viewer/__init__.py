import asyncio
from datetime import datetime
import json
import logging
import os

import aiohttp
from bs4 import BeautifulSoup
import discord


TRADINGVIEW_BASE_URL = 'https://www.tradingview.com'
ACCOUNT_URL_FMT = 'https://www.tradingview.com/ideas-widget/?count=1&header=true&idea_url=&interval=all&offset=0&publish_source=&sort=recent&stream=all&symbol=&time=all&username={account_name}'


async def check_account(account_name, handled):
    account_url = ACCOUNT_URL_FMT.format(account_name=account_name)
    async with aiohttp.ClientSession() as session:
        async with session.get(account_url) as response:
            account_json = await response.json()

    html = account_json['html']
    soup = BeautifulSoup(html, 'html.parser')

    ta_image = soup.find('img', class_='chart-image')
    if not ta_image:
        logging.error('no image found')
        return

    ta_image_url = ta_image['data-image_big']
    ta_market = ta_image['alt']
    if ta_image_url in handled:
        logging.debug('already handled: {}'.format(ta_image_url))
        return

    timestamp_div = soup.find('div', class_='time-info time-upd')
    if not timestamp_div:
        logging.error('no timestamp found')
        return

    timestamp = float(timestamp_div['data-timestamp'])
    ta_timestamp = datetime.utcfromtimestamp(timestamp) \
            .strftime('%Y-%m-%d %I:%M:%S')

    account_link = soup.find('a', class_='avatar userlink')
    if not account_link:
        logging.error('no account link found')
        return

    account_url = '{}/{}'.format(TRADINGVIEW_BASE_URL, account_link['href'])
    account_icon_url = account_link.find('img')['src']

    handled.append(ta_image_url)
    return {
        'account' : {
            'name' : account_name,
            'url' : account_url,
            'icon_url' : account_icon_url
        },
        'market' : ta_market,
        'url' : ta_image_url,
        'timestamp' : ta_timestamp
    }


async def upload_latest_post(client, channel, post):
    logging.info('uploading post', extra={'post' : post})

    embed = discord.Embed()
    embed.set_author(name=post['account']['name'],
            url=post['account']['url'], icon_url=post['account']['icon_url'])
    embed.add_field(name='Market', value=post['market'], inline=True)
    embed.add_field(name='Timestamp', value=post['timestamp'])
    embed.set_image(url=post['url'])

    await client.send_message(channel, embed=embed)


async def watch_accounts(client, **config):
    accounts_file = config['accounts']
    channel = client.get_channel(config['channel_id'])

    while True:
        with open(accounts_file) as f:
            account_data = json.load(f)

        for account_name in account_data['accounts']:
            handled = account_data['handled'].get(account_name, [])
            latest_post = await check_account(account_name, handled)
            if latest_post:
                account_data['handled'][account_name] = handled
                await upload_latest_post(client, channel, latest_post)

        with open(accounts_file, 'w+') as f:
            json.dump(account_data, f, sort_keys=True, indent=2)

        await asyncio.sleep(config['interval'])

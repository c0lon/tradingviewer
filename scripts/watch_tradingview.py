from argparse import ArgumentParser
import json
import logging.config
import os

import discord
import yaml

from trading_viewer import (
    add_account,
    watch_accounts,
    )


DEFAULT_ACCOUNTS = {
    'accounts' : [],
    'handled' : {}
}


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument('config_uri', type=str,
            help='the config file to use.')
    args = arg_parser.parse_args()

    assert os.path.isfile(args.config_uri), 'Config file does not exist.'
    with open(args.config_uri) as f:
        config = yaml.safe_load(f)

    account_file = config['accounts']
    if not os.path.isfile(account_file):
        with open(account_file, 'w+') as f:
            json.dump(DEFAULT_ACCOUNTS, f, sort_keys=True, indent=2)

    logging.config.dictConfig(config['logging'])

    client = discord.Client()
    add_account_prefix = config['bot']['command']['add_account']

    @client.event
    async def on_ready():
        client.loop.create_task(watch_accounts(client, **config))

    @client.event
    async def on_message(message):
        if message.content.startswith(add_account_prefix):
            account = message.content.replace(add_account_prefix, '').strip()
            account_url = await add_account(account)
            if not account_url:
                response = '{} "{}" is not a valid TradingView account.'.format(
                    message.author.mention, account)
            else:
                response = 'Watching "{}".\n{}'.format(account, account_url)
            await client.send_message(message.channel, response)

    client.run(config['bot']['token'])


if __name__ == '__main__':
    main()

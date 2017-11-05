from argparse import ArgumentParser
import json
import logging.config
import os

import discord
import yaml

from trading_viewer import watch_accounts


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

    @client.event
    async def on_ready():
        client.loop.create_task(watch_accounts(client, **config))

    client.run(config['bot']['token'])


if __name__ == '__main__':
    main()

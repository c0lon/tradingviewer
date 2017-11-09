from argparse import ArgumentParser
import json
import logging.config
import os

import discord
from discord.ext import commands
import yaml

from trading_viewer import TradingViewer


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
    logging.config.dictConfig(config['logging'])

    TradingViewer.watch(**config)


if __name__ == '__main__':
    main()

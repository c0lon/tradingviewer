import asyncio
import json

from tradingviewer import (
    configure_app,
    get_default_arg_parser,
    )
from tradingviewer.models import TradingViewAccount
from tradingviewer.models.meta import (
    TradingViewerDBSession, 
    transaction,
    )


def main():
    arg_parser = get_default_arg_parser()
    arg_parser.add_argument('accounts', type=str,
            help='A list of TradingView accounts to follow.')
    arg_parser.add_argument('-c', '--post-count', type=int, default=1,
            help='Fetch COUNT of the authors most recent posts.')
    settings, config = configure_app(arg_parser=arg_parser)

    with open(config['args']['accounts']) as f:
        accounts = json.load(f)
    post_count = config['args']['post_count']

    async def add_accounts():
        with transaction(TradingViewerDBSession) as session:
            for account_name in accounts:
                if TradingViewAccount.get_by_name(session, account_name):
                    continue

                account = await TradingViewAccount.add(session, account_name)
                if account and post_count:
                    await account.get_new_posts(session, count=post_count)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(add_accounts())


if __name__ == '__main__':
    main()

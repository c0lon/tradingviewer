import hupper

from tradingviewer import (
    configure_app,
    get_default_arg_parser,
    TradingViewer,
    )


def main():
    arg_parser = get_default_arg_parser()
    arg_parser.add_argument('--reload', action='store_true',
        help='reload the application on a code change.')
    settings, config = configure_app(arg_parser=arg_parser)

    if config['args'].get('reload'):
        reloader = hupper.start_reloader(f'{__name__}.main')
        reloader.watch_files([config['args']['config_uri']])

    TradingViewer.watch_for_new_posts(**settings)


if __name__ == '__main__':
    main()

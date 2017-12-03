from tradingviewer import configure_app
from tradingviewer.models.meta import TradingViewerBase


def main():
    configure_app()

    TradingViewerBase.metadata.drop_all()
    TradingViewerBase.metadata.create_all()

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    )
from sqlalchemy.orm import relationship

from .meta import TradingViewerBase
from ..utils import (
    GetLoggerMixin,
    get_account_info,
    )


class TradingViewAccount(TradingViewerBase, GetLoggerMixin):
    __tablename__ = 'accounts'
    __loggername__ = f'{__name__}.TradingViewAccount'

    id = Column(Integer, primary_key=True)
    name = Column(Text)
    url = Column(Text)
    image_url = Column(Text)
    date_added = Column(DateTime, default=datetime.now)

    posts = relationship('TradingViewPost', back_populates='account')

    @classmethod
    async def add(cls, session, name):
        logger = cls._logger('add')
        logger.info(name)

        account_info = await get_account_info(name)
        if not account_info:
            logger.warning(f'account does not exist: {name}')
            return

        account = cls(**account_info)
        session.add(account)

        return account

    def get_new_posts(self, session):
        logger = cls._logger('get_new_posts')
        logger.debug(self.name)

    @classmethod
    def get_all_new_posts(self, session):
        for account in session.query(cls).all():
            yield from account.get_new_posts(session)


class TradingViewPost(TradingViewerBase, GetLoggerMixin):
    __tablename__ = 'posts'
    __loggername__ = f'{__name__}.TradingViewPost'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    url = Column(Text)
    chat_image_url = Column(Text)
    timestamp = Column(DateTime)
    date_added = Column(DateTime, default=datetime.now)

    account = relationship('TradingViewAccount', foreign_keys=[account_id])

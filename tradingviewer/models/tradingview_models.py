from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup
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
    get_soup,
    )


TRADINGVIEW_URL_BASE = 'https://www.tradingview.com'
ACCOUNT_URL_FMT = TRADINGVIEW_URL_BASE + '/u/{account_name}'


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
    def get_by_name(cls, session, account_name):
        return session.query(cls) \
                .filter(cls.name == account_name) \
                .first()

    @classmethod
    def get_all(cls, session):
        return session.query(cls).all()

    @classmethod
    async def add(cls, session, name):
        logger = cls._logger('add')
        logger.info(name)

        url = ACCOUNT_URL_FMT.format(account_name=name)
        soup = await get_soup(url)
        if not soup:
            logger.warning(f'account does not exist: {name}')
            return

        image = soup.find('img', class_='tv-profile__avatar-img')
        image_url = image['src']

        account = cls(
            name=name,
            url=url,
            image_url=image_url
        )
        session.add(account)

        return account

    async def get_new_posts(self, session, count=5):
        logger = self._logger('get_new_posts')
        logger.debug(self.name)

        soup = await get_soup(self.url)
        if not soup:
            return

        new_posts = []
        for post_div in soup('div', class_='tv-widget-idea')[:count]:
            post_title_link_tag = post_div.find('a', class_='tv-widget-idea__title')
            post_url = TRADINGVIEW_URL_BASE + post_title_link_tag['href']
            if TradingViewPost.get_by_url(session, post_url):
                break

            post_title = post_title_link_tag.text.strip()
            post_text = post_div.find('p', class_='tv-widget-idea__description-text').text.strip()

            post_image_tag = post_div.find('img', class_='tv-widget-idea__cover')
            post_image_url = post_image_tag['src']

            post_timestamp_div = post_div.find('span', class_='tv-widget-idea__time')
            post_timestamp_seconds = float(post_timestamp_div['data-timestamp'])
            post_timestamp = datetime.fromtimestamp(post_timestamp_seconds)

            post = TradingViewPost(
                title=post_title,
                description=post_text,
                url=post_url,
                image_url=post_image_url,
                timestamp=post_timestamp
            )
            self.posts.append(post)
            new_posts.append(post)

        return new_posts

    @classmethod
    async def get_all_new_posts(self, session):
        for account in cls.get_all(session):
            for post in account.get_new_posts(session):
                yield post

    @classmethod
    def delete(cls, session, account):
        for post in account.posts:
            session.delete(post)
        session.delete(account)


class TradingViewPost(TradingViewerBase, GetLoggerMixin):
    __tablename__ = 'posts'
    __loggername__ = f'{__name__}.TradingViewPost'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    title = Column(Text)
    description = Column(Text)
    url = Column(Text)
    image_url = Column(Text)
    timestamp = Column(DateTime)
    date_added = Column(DateTime, default=datetime.now)

    account = relationship('TradingViewAccount', foreign_keys=[account_id])

    @classmethod
    def get_by_url(cls, session, url):
        return session.query(cls).filter(cls.url == url).first()

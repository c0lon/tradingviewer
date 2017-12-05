from datetime import datetime
import re

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
IDEAS_API_URL = TRADINGVIEW_URL_BASE + '/ideas-widget/'


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
        async with aiohttp.get(url) as response:
            if response.status != 200:
                logger.warning(f'account does not exist: {name}')
                return

            soup = get_soup(await response.text())

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

        params = {
            'username' : self.name,
            'count' : count,
            'interval' : 'all',
            'sort' : 'recent',
            'stream' : 'all',
            'time' : 'all'
        }
        async with aiohttp.get(IDEAS_API_URL, params=params) as response:
            if response.status != 200:
                return []
            latest_post_data = await response.json()

        new_posts = []
        latest_post_soup = get_soup(latest_post_data.get('html', ''))
        latest_post_divs = latest_post_soup('div', id=re.compile(r'chart-(\d+)')) or []
        for post_div in latest_post_divs[:count]:
            post = TradingViewPost.add_from_div(session, post_div)
            if not post:
                break

            self.posts.append(post)
            new_posts.append(post)

        return new_posts

    @classmethod
    async def get_all_new_posts(cls, session):
        all_new_posts = []
        for account in cls.get_all(session):
            all_new_posts.extend(await account.get_new_posts(session))

        return all_new_posts

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

    @classmethod
    def add_from_div(cls, session, post_div):
        logger = cls._logger('add_from_div')
        
        post_url_link = post_div.find('a', class_='chart-page-popup')
        post_url = TRADINGVIEW_URL_BASE + post_url_link['data-chart']
        if cls.get_by_url(session, post_url):
            logger.debug(f'seen post: {post_url}')
            return

        logger.info(post_url)

        post_title_div = post_div.find('div', class_='chart-title')
        post_title = post_title_div.text.strip()
        post_text = post_div.find('div', class_='desc').text.strip()

        post_image_element = post_url_link.find('img')
        post_image_url = post_image_element['data-image_big']

        timestamp_div = post_div.find('div', class_='time-info')
        post_timestamp = datetime.fromtimestamp(float(timestamp_div['data-timestamp']))

        post = cls(
            title=post_title,
            description=post_text,
            url=post_url,
            image_url=post_image_url,
            timestamp=post_timestamp
        )
        session.add(post)

        return post

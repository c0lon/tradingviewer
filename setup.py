import os
from setuptools import (
    find_packages,
    setup,
    )


install_requires = [
    'aiohttp<1.1.0,>=1.0.0',
    'bs4==0.0.1',
    'discord==0.0.2',
    'pyyaml==3.12'
]

entry_points = {
    'console_scripts' : [
        'watch-tv = scripts.watch_tradingview:main'
    ]
}


here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'VERSION')) as f:
    VERSION = f.read().strip()

setup(name='tradingviewer',
      description='Upload TA from TradingView to Discord',
      long_description=README,
      version=VERSION,
      author='Collin Barth',
      author_email='cpbarth92@gmail.com',
      install_requires=install_requires,
      packages=find_packages(),
      entry_points=entry_points,
      )

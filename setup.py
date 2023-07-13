#!/usr/bin/env python3

from setuptools import setup


setup(
    name='fuo_qqmusic',
    version='0.5.0',
    description='feeluown qqmusic plugin',
    author='Cosven',
    author_email='yinshaowen241@gmail.com',
    packages=[
        'fuo_qqmusic',
    ],
    package_data={
        '': ['assets/*.svg',]
    },
    url='https://github.com/feeluown/feeluown-qqmusic',
    keywords=['feeluown', 'plugin', 'qqmusic'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
    ],
    install_requires=[
        'feeluown<3.9',
        'requests',
        'marshmallow>=3.0'
    ],
    entry_points={
        'fuo.plugins_v1': [
            'qqmusic = fuo_qqmusic',
        ]
    },
)

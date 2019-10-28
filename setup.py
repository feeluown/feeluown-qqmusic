#!/usr/bin/env python3

from setuptools import setup


setup(
    name='fuo_qqmusic',
    version='0.1.5',
    description='feeluown qqmusic plugin',
    author='Cosven',
    author_email='yinshaowen241@gmail.com',
    packages=[
        'fuo_qqmusic',
    ],
    package_data={
        '': []
        },
    url='https://github.com/feeluown/feeluown-qqmusic',
    keywords=['feeluown', 'plugin', 'qqmusic'],
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        ),
    install_requires=[
        'feeluown>=3.1',
        'requests',
        'marshmallow>=2.13.5,<3.0'
    ],
    entry_points={
        'fuo.plugins_v1': [
            'qqmusic = fuo_qqmusic',
        ]
    },
)

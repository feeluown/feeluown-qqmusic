import json
import os
from unittest.mock import patch

import pytest

from fuo_qqmusic import provider
from fuo_qqmusic.api import API


def _read_json_fixture(path):
    path = os.path.join('data/fixtures', path)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


@pytest.fixture
def album_3913679():
    return _read_json_fixture('album_3913679.json')


def test_provider_album_get(album_3913679):
    patch.object(API, 'album_detail', return_value=album_3913679)
    album = provider.album_get('3913679')
    assert album.identifier == '3913679'

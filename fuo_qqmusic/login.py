import json
import os

from feeluown.consts import DATA_DIR

USER_INFO_FILE = DATA_DIR + '/qqmusic_user_info.json'


def read_cookies():
    if os.path.exists(USER_INFO_FILE):
        # if the file is broken, just raise error
        with open(USER_INFO_FILE) as f:
            return json.load(f).get('cookies', None)


def write_cookies(user, cookies):
    js = {
        'identifier': user.identifier,
        'name': user.name,
        'cookies': cookies
    }
    with open(USER_INFO_FILE, 'w') as f:
        json.dump(js, f, indent=2)


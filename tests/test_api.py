from fuo_qqmusic.api import API
import pytest


def parse_cookie_to_dict(cookie_str):
    # 初始化结果字典
    result = {}

    # 按分号分割字符串，得到每个键值对
    pairs = cookie_str.split(";")

    for pair in pairs:
        # 去除两端空格
        pair = pair.strip()

        # 按等号分割键和值
        if "=" in pair:
            key, value = pair.split("=", 1)
            key = key.strip()
            value = value.strip()

            # 如果值为空字符串，则设置为 None
            if value == "":
                value = None

            # 存入字典
            result[key] = value

    return result


cookie_str = "Your cookie string here"


@pytest.mark.skip(reason="need valid cookies")
def test_api():
    api = API()
    api.set_cookies(parse_cookie_to_dict(cookie_str))
    # You can also use the following code to load cookies
    # from fuo_qqmusic.provider import provider
    # provider.auto_login()
    # api = provider.api
    items = [
        {
            "ID": "238159921",
            "Name": "无人区-Vacuum Track#ADD8E6- - 米缐p.",
            "IdType": 0,
        }
    ]
    print(api.add_to_dislike_list(items, type_=API.DislikeListType.song))
    print(api.get_dislike_list(type_=API.DislikeListType.song))
    print(api.remove_from_dislike_list(items, type_=API.DislikeListType.song))


if __name__ == "__main__":
    test_api()

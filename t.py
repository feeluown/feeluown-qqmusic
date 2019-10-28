from fuo_qqmusic import provider


songid = 97773
songmid = '0039MnYb0qxYhV'

print(provider.api.get_song_detail(songid))

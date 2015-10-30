
AUDIO_EXT_WITH_TAGS = [
    '.flac',
    '.m4a',
    '.mp3',
    '.ogg',
    '.wma',
]

AUDIO_EXT_WITHOUT_TAGS = [
    '.wav'
]

AUDIO_EXT = AUDIO_EXT_WITHOUT_TAGS + AUDIO_EXT_WITH_TAGS

VIDEO_EXT = [
    '.avi',
    '.div',
    '.divx',
    '.flv',
    '.m4v'
    '.mov',
    '.mp4',
    '.mpeg',
    '.mpg',
    '.theora',
    '.vorb',
    '.vorbis',
    '.wmv',
]

VALID_EXT = AUDIO_EXT + VIDEO_EXT

# This is for the player
SUPPORTED_EXTENSIONS = [''] + VALID_EXT


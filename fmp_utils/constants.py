
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

import os
import sys

USER_HOME = os.path.realpath(os.path.expanduser("~/"))
CONFIG_DIR = os.path.join(USER_HOME, '.fmp')

if "--test-first-run" in sys.argv:
    CONFIG_DIR = os.path.join(USER_HOME, '.fmp-test')

CONFIG_FILE = os.path.join(CONFIG_DIR, "config")

CACHE_DIR = os.path.join(CONFIG_DIR, "cache")

os.makedirs(CONFIG_DIR, 0o775, True)
os.makedirs(CACHE_DIR, 0o775, True)


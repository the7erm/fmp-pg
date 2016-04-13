

from .constants import AUDIO_EXT, AUDIO_EXT_WITH_TAGS, VIDEO_EXT, VALID_EXT
import os
import re
import mutagen

audio_ext = AUDIO_EXT
audio_with_tags = AUDIO_EXT_WITH_TAGS
video_ext = VIDEO_EXT

def is_video(ext=None):
    return ext.lower() in video_ext


def is_audio(ext=None):
    return ext.lower() in audio_ext


def has_tags(ext=None):
    return ext.lower() in audio_with_tags


class MediaTags(object):
    def __init__(self, filename=None):
        self.filename = filename
        self.dirname = os.path.dirname(filename)
        self.basename = os.path.basename(filename)
        self.tags_easy = None
        self.tags_hard = None
        self.base, self.ext = os.path.splitext(self.basename)
        self.has_tags = has_tags(self.ext)
        self.is_audio = is_audio(self.ext)
        self.is_video = is_video(self.ext)
        self.tags_combined = {
            'artist': [],
            'title': [],
            'genre': [],
            'album': [],
            'year': [],
            'track': [],
            'keywords': [],
            'images': []
        }
        self.exists = os.path.exists(self.filename)
        self.add_keyword(self.basename)
        self.set_tags()

    def combine_tags(self, tags):
        if not tags:
            return
        artist_keys = ('artist', 'author', 'wm/albumartist', 'albumartist',
                       'tpe1', 'tpe2', 'tpe3')
        title_keys = ('title', 'tit2')
        album_keys = ('album', 'wm/albumtitle', 'albumtitle', 'talb')
        year_keys = ('year', 'wm/year', 'date', 'tdrc', 'tdat', 'tory', 'tdor',
                     'tyer')
        genre_keys = ('genre', 'wm/genre', 'wm/providerstyle', 'providerstyle',
                      'tcon')
        track_keys = ('wm/tracknumber', 'track', 'trck')

        image_keys = ('apic', 'apic:')

        for k in tags:
            # print ("k:",k,":",end="")
            try:
                # print(tags[k])
                self.add_to_combined(k, tags[k])
            except KeyError as e:
                print ("KeyError:", e)
                continue
            k_lower = k.lower()
            if k_lower in artist_keys:
                self.add_to_combined('artist', tags[k])
            if k_lower in title_keys:
                self.add_to_combined('title', tags[k])
            if k_lower in album_keys:
                self.add_to_combined('album', tags[k])
            if k_lower in year_keys:
                self.add_to_combined('year', tags[k])
            if k_lower in genre_keys:
                self.add_to_combined('genre', tags[k])
            if k_lower in track_keys:
                self.add_to_combined('track', tags[k])
            if k_lower in image_keys:
                self.add_to_combined('images', tags[k])

    def add_to_combined(self, tag, value):
        if tag not in self.tags_combined:
            self.tags_combined[tag] = []

        if not isinstance(value, (list, dict, tuple)):
            try:
                if value not in self.tags_combined[tag]:
                    self.tags_combined[tag].append(value)
                    if tag in ('artist', 'title', 'album', 'year', 'genre',
                               'track'):
                        self.add_keyword(value)
            except:
                pass
            return

        if isinstance(value, (list, tuple)):
            for v in value:
                self.add_to_combined(tag, v)

        if isinstance(value, dict):
            for k, v in value.items():
                self.add_to_combined(tag, v)


    def set_tags(self, *args, **kwargs):
        if not self.exists or not self.has_tags or self.tags_easy is not None \
           or self.tags_hard is not None:
            return

        self.tags_easy = self.get_tags(True)
        self.tags_hard = self.get_tags(False)


    def get_tags(self, easy=True):
        if not self.exists or not self.has_tags:
            return None

        tags = None
        try:
            tags = mutagen.File(self.filename, easy=easy)
            self.combine_tags(tags)
        except mutagen.mp3.HeaderNotFoundError:
            pass
        except mutagen.mp4.MP4StreamInfoError:
            pass
        except KeyError:
            pass

        return tags

    def add_keyword(self, value):
        value = str(value)
        value = value.replace("_", " ")
        value = value.lower()
        value = value.strip()
        if not value:
            return
        words = value.split(" ")
        for word in words:
            if not word:
                continue
            if word not in self.tags_combined['keywords']:
                self.tags_combined['keywords'].append(word)

            _word = re.sub("[^A-z0-9]+", "", word)
            if _word and _word != word and \
               _word not in self.tags_combined['keywords']:
                # print ("sub _word:", word)
                self.tags_combined['keywords'].append(_word)

            _word = re.split("[^A-z0-9]+", word)
            for w in _word:
                # print ("split _word:", w)
                if w and w not in self.tags_combined['keywords']:
                    self.tags_combined['keywords'].append(w)


import os
import sys
if "../" not in sys.path:
    sys.path.append("../")

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

import feedparser
import re
from fmp_utils.constants import CACHE_DIR
from fmp_utils.db_session import  create_all, Session
from fmp_utils.jobs import jobs
from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import not_, and_, text
from pprint import pprint
from time import mktime, time
from .user import User

class Rss(Base):
    __tablename__ = "rss"
    id = Column(Integer, primary_key=True)
    author = Column(String)
    expires = Column(Integer) # When the feed can be parsed again.
    generator = Column(String)
    image = Column(String)
    itunes_block = Column(Integer)
    itunes_explicit = Column(Boolean)
    language = Column(String)
    link = Column(String)
    publisher = Column(String)
    rights = Column(String)
    subtitle = Column(String)
    summary = Column(String)
    sy_updatefrequency = Column(Integer)
    sy_updateperiod = Column(String)
    title = Column(String)
    updated = Column(Integer)
    url = Column(String, unique=True)
    entries = relationship("Entry", backref="rss")
    timestamp = Column(BigInteger, onupdate=time)

    def update(self):
        feed = feedparser.parse(self.url)
        if feed.bozo:
            # Expire in 30 minutes
            self.expires = time() + (30 * 60)
            return
        self.author = feed.feed.author
        self.generator = feed.feed.generator
        self.image = feed.feed.image.href
        self.itunes_block = feed.feed.itunes_block
        self.itunes_explicit = feed.feed.itunes_explicit
        self.language = feed.feed.language
        self.link = feed.feed.link
        self.publisher = feed.feed.publisher
        self.rights = feed.feed.rights
        self.subtitle = feed.feed.subtitle
        self.summary = feed.feed.summary
        self.sy_updatefrequency = feed.feed.sy_updatefrequency
        self.sy_updateperiod = feed.feed.sy_updateperiod
        self.title = feed.feed.title
        self.updated = mktime(feed.feed.updated_parsed)


        session.add(self)
        session.commit()

        for item in feed.entries:
            found_entry = None
            for entry in self.entries:
                if entry.link_id == item.id:
                    found_entry = entry
                    break

            if not found_entry:
                entry = Entry()
                self.entries.append(entry)
            else:
                entry = found_entry

            entry.sync(item)

        session.add(self)
        session.commit()

class Entry(Base):
    __tablename__ = "entries"
    id = Column(Integer, primary_key=True)
    author = Column(String)
    comments = Column(String)
    guidislink = Column(Boolean)
    link = Column(String)
    link_id = Column(String)
    published = Column(Integer)
    slash_comments = Column(Integer)
    subtitle = Column(String)
    summary = Column(String)
    title = Column(String)
    wfw_commentrss = Column(String)

    rss_id = Column(Integer, ForeignKey('rss.id'))
    contents = relationship("Content", backref="entry")
    enclosures = relationship("Enclosure", backref="entry")
    timestamp = Column(BigInteger, onupdate=time)

    def sync(self, item):
        self.author = item.author
        self.comments = item.comments
        self.guidislink = item.guidislink
        self.link = item.link
        self.link_id = item.id
        self.published = mktime(item.published_parsed)
        self.slash_comments = item.slash_comments
        # self.subtitle = item.subtitle
        self.summary = item.summary
        self.title = item.title
        self.wfw_commentrss = item.wfw_commentrss

        for content_item in item.content:
            found_content = None
            for content in self.contents:
                if content.value == content_item.value:
                    found_content = content
                    break

            if not found_content:
                content = Content()
                self.contents.append(content)
            else:
                content = found_content

            content.sync(content_item)

        for enclosure_item in item.enclosures:
            found = None
            for enclosure in self.enclosures:
                if enclosure.href == enclosure_item.href:
                    found = enclosure
                    break

            if not found:
                enclosure = Enclosure()
                self.enclosures.append(enclosure)
            else:
                enclosure = found

            enclosure.sync(enclosure_item)

        session.add(self)
        session.commit()


class Content(Base):
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True)
    base = Column(String)
    typ = Column(String)
    value = Column(String)

    entry_id = Column(Integer, ForeignKey('entries.id'))
    timestamp = Column(BigInteger, onupdate=time)

    def sync(self, item):
        self.base = item.base
        self.typ = item.type
        self.value = item.value
        session.add(self)
        session.commit()


class Enclosure(Base):
    __tablename__ = "enclosures"
    id = Column(Integer, primary_key=True)
    href = Column(String)
    typ = Column(String)
    length = Column(Integer)

    entry_id = Column(Integer, ForeignKey('entries.id'))
    timestamp = Column(BigInteger, onupdate=time)

    def sync(self, item):
        self.href = item.href
        self.typ = item.type
        self.length = item.length
        session.add(self)
        session.commit()

    @property
    def cache_filename(self):
        return os.path.join(CACHE_DIR,
                            re.sub("\W+", "-",
                                   os.path.basename(href)))

    @property
    def filename(self):
        cache_filename = self.cache_filename
        if os.path.exist(cache_filename):
            return cache_filename
        return self.href

if __name__ == "__main__":
    create_all(Base)
    url = "http://music.the-erm.com/feed/"
    rss = (
            session.query(Rss)\
                   .filter(Rss.url==url)
                   .first()
          )

    if not rss:
        rss = Rss()

    rss.url = "http://music.the-erm.com/feed/"
    rss.update()
    session.add(rss)
    session.commit()

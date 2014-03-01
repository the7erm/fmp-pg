fmp-pg
======

Family Media Player

This is my hello-world project.  When I learn something new I apply it to this
concept.

If you'd like to contribute I'd appreciate it.  I really don't recommend anyone
use this unless you want to help develop it, and bring the concept to a useable 
state for joe average user.

Features:
* Multiple listeners
* Web interface `http://localhost:5050`
* Resumes song position
* Tray icon for rating and pressing next.
* Enable/disable genres (so you're not listening to Christmas songs all year long.)
* A fingerprint system that detects duplicate files so you don't have multiple
  entries for duplicate files.
* Rate a file 0 never hear it again. 
  * Ratings range from 0 to 6.
  * 0 = never play again
  * 1-5 = standard star system 1 hate 5 love
  * 6 = Unrated (so new songs get a higher priority)
* Let a file play through the skip score goes up
* Press skip the skip score goes down.
* Where you skip the percent played is recorded, and figured into the final
  true score.
* Extensive history.
* Netcasts/podcasts
* A file can have multiple artists. 
  * Artist parsing. 
    * `Foo vs/and/&/ft bar` will be tagged `Foo vs/and/&/ft Bar`, `Foo` and `Bar`
    * EG: `Big & Rich` = `Big & Rich`, `Big`, `Rich`
* A file can have multiple genres. 
* Sequentially play specific genres/artists (Like an audiobook, tv series)
* PosgreSQL for the db.
* Plays anything gstreamer will play.
* Bedtime mode that won't apply a skip score, or percent played if a file is 
  played through.

The true score's formula is something like this:
true_score = ((rating * 10 * 2) + (skip_score * 10) + percent_played + (average percent played for the last 5 times) ) / 4

What it lacks:
* A way to easily add netcasts
* mpris interface
* id3 tag editing (but buttons are available in file info dialogs to use kid3 or picard)
* Scrobbling
* Gpodder sync
* Downloading album images
* Plugin system.
* A playlist.  (It's a jukebox doesn't need a playlist.)
* A way to cue entire albums with one click.

# Setup

## Creating the database

[You'll need to set up PostgreSQL](https://wiki.postgresql.org/wiki/Detailed_installation_guides)

`pgsql <db-name> < ` [sql/create.sql](https://github.com/the7erm/fmp-pg/blob/master/sql/create.sql)


## Config file

You'll need to create your own config file in `~/.fmp/config` . 
Netcasts/Podcasts are downloaded to `~/.fmp/cache/`

```
[password_salt]
salt = 

[Misc]
bedtime_mode = false

[postgres]
username = <db-user>
host = 127.0.0.1
password = <db-password>
port = 5432
database = <db-name>

[Netcasts]
cue = true
```

# Scan
`./scan.py <folder-to-scan>`
Once your files are scanned

# Run
`./fmp-pg.py`

# Set up your media keys
```
/path/to/fmp-pg.py --pause # start's the player
/path/to/fmp-pg.py --next # play next song
/path/to/fmp-pg.py --prev # play previous songs
/path/to/pykill fmp.pg.py # kill it use it for stop/shutdown.
```

# Your very own web interface
`http://localhost:5050/` -- warning this is not secure, don't put it on the open internet







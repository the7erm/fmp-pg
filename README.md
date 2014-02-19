fmp-pg
======

Family Media Player

This is my hello-world project.  When I learn something new I apply it to this
concept.

If you'd like to contribute I'd appreciate it.

Features:
* Multiple listeners
* Web interface
* Tray icon for rating and pressing next.
* Enable/disable genres (so you're not listening to Christmas songs all year long.)
* A fingerprint system that detects duplicate files so you don't have multiple
  entries for duplicate files.
* Rate a file 0 never hear it again. Ratings range from 0 to 6.
  0 = never play again
  1-5 = standard star system 1 hate 5 love
  6 = Unrated (so new songs get a higher priority)
* Let a file play through the skip score goes up
* Press skip the skip score goes down.
* Where you skip the percent played is recorded, and figured into the final
  true score.
* Extensive history.
* Netcasts.
* A file can have multiple artists. 
  * Artist parsing. 
    * `Foo vs/and/&/ft bar` will be tagged `Foo vs/and/&/ft Bar`, `Foo` and `Bar`
    * EG: `Big & Rich` = `Big & Rich`, `Big`, `Rich`
* A file can have multiple genres. 
* Sequentially play specific genres/artists (Like an audiobook, tv series)
* PosgreSQL for the db.
* Plays anything gstreamer will play.

The true score's formula is something like this:
true_score = ((rating * 10 * 2) + (skip_score * 10) + percent_played + (average percent played for the last 5 times) ) / 4

What it lacks:
* A way to easily add netcasts
* mpris interface
* id3 tag editing (but buttons are available in file info dialogs to use kid3 or picard)
* Scrobbling
* Gpodder sycn
* Downloading album images
* Plugin system.

# Creating the database
=======================
`[sql/create.sql](https://github.com/the7erm/fmp-pg/blob/master/sql/create.sql)`

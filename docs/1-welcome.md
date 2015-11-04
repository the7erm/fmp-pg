# Welcome to FMP

**F**amily **M**edia **P**layer is not your normal media player.  It's main focus is to pick music for groups of people (although it's been tested extensively in single user mode.)  It could almost be considered a **P**arty **M**edia **P**layer, but I digress.

**DO NOT RUN THIS ON THE OPEN INTERNET.  IT'S FOR LAN/LOCAL USE ONLY**

In other words don't open up port 5050 on your router.  I've made 0 attempt at making this thing secure.  There's nothing stopping a random person from messing up all your ratings.

If you feel frisky and want to set up an ssh tunnel and run something like soundwire server on your phone that could be fun.


## Features
- Web interface
- Control the media player from any browser on the lan.
- Multiple users can listen at 1 time
- `Skip score` the more you click skip the less you hear it.
  - `Thumbs up` raises the `skip score`
  - `Thumbs down` lowers the `skip score`
- `Rating` 1-5 star rating of a song.
  - rate a song 0 and it'll never be played if that user is listening again.  Even if other users have a max `True Score` of 125.
- `True score`
  - Calculated based on values of the `Rating` and `Skip Score`
    - For anyone who cares here's the formula.
      `( (rating * 2 * 10) + (skip_score * 10) ) / 2`
    - The higher the `True score` the more a file gets picked for a user
      - If the `true score` gets a negative value, then it's not picked for
        that user.
- `Vote to skip`
  - If over half the listeners click `vote to skip` the file is skipped.
  - If under half the listeners click `vote to skip` the file is not skipped,
    but the listener's `skip_score` goes down.
- Duplicate reduction
  - Every file gets a fingerprint.  If the fingerprints match it is
    considered a duplicate.  That way you're not hearing the same file over
    and over because it exists in multiple places on your hard drive.  The
    reason this is done is so you can have a `sync` folder for your phone
    and still have that folder as part of the catalog.  Plus if you move a
    file it'll find it.  The fingerprint is a `sha512` hash of 64k of the
    front, middle and end of a file.
- Genre selection
  - Turn on/off genres that are chosen. (So you're not listening to Christmas
    music in July.)

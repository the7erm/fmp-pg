starterServices
.factory('FmpPlayer', function($ionicPlatform, FmpPreload, FmpPlaylist,
                               $rootScope, FmpUtils){
  var playerState = localStorage.playerState || Media.MEDIA_PAUSED,
      collection = {
        "duration": -1,
        "media": null,
        "position": -1,
        "remaining": -1,
        "releasing": false,
        "state": 0, /* Media object's state. */
        "playerState": playerState, /* The Media object's state is not the
                                       actual state of the player. */
        "initializing": true
      },
      methods = {
        collection: collection
      };

  FmpPlaylist.collection.state = playerState;
  FmpPlaylist.collection.player = methods;

  methods.onComplete = function() {
    // TODO incScore
    console.log("***************** ON COMPLETE");
    if (collection.releasing) {
      console.log("releasing, so not setting index");
      return;
    }
    console.log("FmpPlayer.onComplete:", arguments);
    FmpPlaylist.incScore();
    FmpPlaylist.setIndex("+1");
  };

  methods.onError = function() {
    console.log("FmpPlayer.onError:", arguments);
    console.log("FmpPlaylist.collection:", FmpPlaylist.collection);
  }

  methods.clearPosition = function () {
    collection.position = -1;
    collection.duration = -1;
    collection.remaining = -1;
  }

  methods.onStatusChange = function(state) {
    console.log("FmpPlayer.onStatusChange:", state);
    if (state < Media.MEDIA_RUNNING) {
      methods.clearPosition();
    }
    collection.state = state;
  };

  methods.pause = function() {
    console.log("FmpPlayer.PAUSE");
    if (collection.media == null) {
      console.log("collection.media is null");
      FmpPlaylist.setIndex(FmpPlaylist.collection.idx);
      if (collection.media == null) {
        methods.setMedia();
      }
      if (collection.media == null) {
        return;
      }
    }
    /*
      Media.MEDIA_NONE = 0;
      Media.MEDIA_STARTING = 1;
      Media.MEDIA_RUNNING = 2;
      Media.MEDIA_PAUSED = 3;
      Media.MEDIA_STOPPED = 4;
    */
    if (collection.state != Media.MEDIA_RUNNING) {
      console.log(".play();");
      collection.media.play();
      collection.playerState = Media.MEDIA_RUNNING;
    } else {
      console.log(".pause();");
      collection.media.pause();
      collection.playerState = Media.MEDIA_PAUSED;
    }
    FmpPlaylist.collection.state = collection.playerState;
    FmpPlaylist.markAction();
    methods.save();
  }

  methods.save = function () {
    localStorage.playerState = collection.playerState;
    if (collection.position > 0 && collection.duration > 0 &&
        !collection.initializing) {
      localStorage.position = collection.position;
    }
  }

  methods.timeStatus = function () {
      if (!collection.media || !Media || collection.state < Media.MEDIA_RUNNING) {
        methods.clearPosition();
        return;
      }
      // get media position
      collection.media.getCurrentPosition(
          // success callback
          function (position) {
              if (position > -1) {
                  if (collection.position == position && collection.duration > 0 &&
                      collection.remaining > -1) {
                    return;
                  }
                  collection.position = position;
                  if (collection.duration <= 0 || collection.remaining <= -1) {
                    collection.duration = collection.media.getDuration();
                  }
                  collection.remaining = collection.duration - collection.position;
                  $rootScope.$broadcast("time-status");
                  FmpPlaylist.markAsPlayed(collection.position,
                                           collection.remaining,
                                           collection.duration);
                  if (collection.initializing && collection.position > 0 &&
                      collection.duration > 0 && localStorage.position) {
                        collection.media.seekTo(localStorage.position * 1000);
                        collection.initializing = false;
                  }
                  methods.save();
              } else {
                methods.clearPosition();
              }
          },
          // error callback
          function (e) {
              console.log("Error getting pos=" + e);
          }
      );
  };

  methods.setMedia = function(){
      console.log("FmpPlayer.methods.setMedia:");
      if (collection.releasing) {
        console.log("!setMedia - releasing");
        return;
      }
      if (!FmpPlaylist.collection.playing) {
        console.log("!FmpPlaylist.collection.playing");
        return;
      }
      collection.releasing = true;
      if (collection.media != null) {
        collection.media.stop();
        collection.media.release();
      }
      FmpUtils.addLocalData(FmpPlaylist.collection.playing);
      var src = FmpPlaylist.collection.playing.fullFilename;
      if (typeof src == 'undefined') {
        console.log("SRC IS UNDEFINED fullFilename?:",
                    FmpPlaylist.collection.playing);


        src = FmpPlaylist.collection.playing.fullFilename;
        if (typeof src == 'undefined') {
          console.log("reconstruction failed")
          return;
        }
      }
      collection.media = new Media(src,
                                   methods.onComplete,
                                   methods.onError,
                                   methods.onStatusChange);
      collection.media.play();
      if (collection.playerState != Media.MEDIA_RUNNING) {
          collection.media.pause();
      }
      if (collection.initializing && localStorage.position) {
            collection.media.seekTo(localStorage.position * 1000);
            collection.initializing = false;
      }
      setTimeout(function(){
        collection.releasing = false;
      }, 1000);
      $rootScope.$broadcast("media-set");
  };

  methods.resume = function() {
    console.log("RESUME");
    methods.setMedia();
    methods.collection.media.pause();
    var duration = methods.collection.media.getDuration(),
        percent_played = parseFloat(FmpPlaylist.collection.playing.percent_played);
    console.log("duration:", duration, "percent_played:", percent_played);
    var tmp = function() {
        var duration = methods.collection.media.getDuration();
        console.log("duration:", duration);
        if (duration == -1) {
          setTimeout(tmp, 500);
          return;
        }
        var decimal = percent_played * 0.01;
        localStorage.position = decimal * duration;
        methods.collection.media.seekTo(localStorage.position * 1000);
        console.log("RESUME SEEK:", localStorage.position);
        methods.save();
    };
    if (percent_played) {
      setTimeout(tmp, 500);
    }
  }

  $rootScope.$on("index-changed", methods.setMedia);
  return methods;

})
fmpApp.factory('FmpPlaylist', function($rootScope, FmpUtils, FmpListeners,
                                       FmpSync, FmpPreload){
  var logger = new Logger("FmpPlaylist", false);
  var collection = {
        files: [],
        lastSave: 0,
        lastAction: 0,
        "sync": {},
        FmpSync: FmpSync,
        lastSyncTime: 0,
        organizeLock:false,
        saveLock: false,
        loaded: false
      },
      methods = {
        collection: collection
      };

    methods.load = function() {
      logger.log("load()");
      collection.files = [];
      if (typeof localStorage["playlist"] == "undefined" ||
          !localStorage["playlist"]) {
        collection.loaded = true;
        return;
      }
      var files = JSON.parse(localStorage["playlist"]),
          foundPlaying = false;
      for (var i=0;i<files.length;i++) {
        var key = files[i];
        if (typeof localStorage[key] == "undefined") {
          // the file doesn't exist.
          continue;
        }
        var file = new FmpFile(key);
        collection.files.push(file);
        if (file.playing == true) {
          file.play();
          foundPlaying = true;
        }
      }
      if (!foundPlaying && typeof collection.files[0] != "undefined") {
        collection.files[0].playing = true;
      }
      logger.log("loaded");
      collection.loaded = true;
    };

    methods.save = function() {
      if (collection.saveLock) {
        return;
      }
      collection.saveLock = true;
      var files = [];
      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i];
        file.save();
        files.push("file-"+file.file_id);
      }
      localStorage.playlist = JSON.stringify(files);
      collection.saveLock = false;
    };

    methods.incTrack = function(by, incScore, user_ids) {
      if (typeof by == 'undefined') {
        by = 1;
      }
      if (typeof incScore == 'undefined') {
        incScore = 0;
      }
      if (typeof user_ids == 'undefined') {
        user_ids = [];
      }
      if (!collection.files || collection.files.length == 0) {
        return;
      }
      var playingIdx = -1,
          prevIdx = -1,
          files = [],
          listener_user_ids = FmpListeners.collection.listener_user_ids,
          primary_user_id = FmpListeners.collection.primary_user_id,
          user_ids = [];

      // We're creating a new array because we don't want
      // to push the primary_user_id onto listener_user_ids
      $.each(FmpListeners.collection.listener_user_ids, function(i, user_id){
          user_ids.push(user_id);
      });
      if (user_ids.indexOf(primary_user_id) == -1) {
          user_ids.push(primary_user_id);
      }

      var atLeastOneWithoutError = false;

      // Build a list of files that are showing.
      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i];
        if (typeof file.cued == "undefined" || !file.cued || file.playing) {
          if (!file.err) {
            atLeastOneWithoutError = true;
          }
          files.push(file);
          continue;
        }
        if (user_ids.indexOf(file.cued.user_id) != -1) {
          if (!file.err) {
            atLeastOneWithoutError = true;
          }
          files.push(file);
        }
      }

      if (files.length == 0) {
        return;
      }

      if (!atLeastOneWithoutError) {
        return;
      }

      for (var i=0;i<files.length;i++) {
        // Get the playing index, then increment & decrement the score
        // accordingly.
        var file = files[i];
        if (file.playing) {
          playingIdx = i;
          prevIdx = i;
          if (incScore == -1) {
            file.spec.skipped = true;
            file.deinc_score(user_ids);
            file.save();
          }
          if (incScore == 1) {
            file.spec.skipped = false;
            file.inc_score(user_ids);
            file.save();
          }
          break;
        }
      }
      playingIdx = playingIdx + by;
      if (playingIdx < 0) {
        // The playing index is < 0 set it to the length of files.
        playingIdx = files.length - 1;
      }
      if (playingIdx >= files.length) {
        // the playing index is >= the files.length so we
        // loop back to the beginning.
        playingIdx = 0;
      }

      if (prevIdx != playingIdx && prevIdx != -1 &&
          typeof files[prevIdx] != 'undefined') {
            // The previous index exists, so set the playing to false
            var file = files[prevIdx];
            file.playing = false;
      }

      for (var i=0;i<files.length;i++) {
        if (i == playingIdx) {
          files[i].playing = true;
          files[i].play();
          break;
        }
      }
    }

    methods.next = function() {
      logger.log("PLAYLIST NEXT");
      methods.incTrack(1, -1, []);
    };

    methods.prev = function() {
      logger.log("PLAYLIST PREV");
      methods.incTrack(-1, 0, []);
    };

    methods.organize = function() {
      if (collection.organizeLock) {
        return;
      }
      collection.organizeLock = true;
      var files = [],
          newOrder = [],
          playedFiles = [],
          unplayedFiles = [],
          playingFile = null,
          groupedByUsers = {};

      for (var i=0;i<FmpPreload.collection.files.length;i++) {
          var file = FmpPreload.collection.files[i];
          logger.log("file:", file);
          files.push(file);
      }
      for (var i=0;i<collection.files.length;i++) {
          var file = collection.files[i];
          files.push(file);
      }
      FmpPreload.collection.files = [];
      for (var i=0;i<files.length;i++) {
        var file = files[i];
        if (!file) {
          logger.log("FILE IS NULL!");
          continue;
        }
        if (!file.spec) {
          logger.log("!file.spec", file);
          continue;
        }
        if (file.spec.cued) {
          var user_id = file.spec.cued.user_id;
        }


        if (typeof groupedByUsers[user_id] == "undefined"){
          groupedByUsers[user_id] = [];
        }
        if (!user_id || FmpListeners.collection.listener_user_ids.indexOf(user_id) != -1) {
            groupedByUsers[user_id].push(file);
        } else {
            FmpPreload.collection.files.push(file);
            logger.log("fallback push:", file.id);
        }
      }
      var hasFiles = true;
      while(hasFiles) {
        hasFiles = false;
        for(var user_id in groupedByUsers) {
          var files = groupedByUsers[user_id];
          if (files.length == 0) {
            continue;
          }
          hasFiles = true;
          var file = files.shift();
          if (file.played || file.spec.played) {
            if (file.playing || file.spec.playing) {
              playingFile = file;
            } else {
              playedFiles.push(file);
              logger.log("PLAYED:", file.id);
            }
          } else {
            unplayedFiles.push(file);
          }
        }
      }
      logger.log("playedFiles:", playedFiles);
      logger.log("playingFile:", playingFile);
      logger.log("unplayedFiles:", unplayedFiles);
      for (var i=0;i<playedFiles.length;i++) {
        newOrder.push(playedFiles[i]);
      }
      if (playingFile) {
        newOrder.push(playingFile);
      }
      for (var i=0;i<unplayedFiles.length;i++) {
        newOrder.push(unplayedFiles[i]);
      }
      collection.files = newOrder;
      collection.organizeLock = false;
    };

    methods.deleteFile = function(file, deleteCb) {
        console.log("deleteFile");
        if (typeof deleteCb == "undefined") {
          deleteCb = methods.deleteCb;
        }
        var idx = FmpUtils.indexOfFile(collection.files, file);
        console.log("idx:", idx);
        if (idx != -1) {
            var _file = collection.files[idx];
            collection.files.splice(idx,1);
            console.log("_file.delete");
            _file.delete(deleteCb);
        }
    }

    methods.deleteCb = function(file) {
      logger.log("deleteCb:", file);
      FmpSync.syncFile(file);
    }

    methods.rate = function(ufi) {
        logger.log("rate:", ufi);
        for (var i=0;i<collection.files.length;i++) {
            var file = collection.files[i];
            if (file.file_id == ufi.file_id) {
                file.rate(ufi.user_id, ufi.rating, true);
                break;
            }
        }
    };

    methods.score = function (ufi) {
        logger.log("score:", ufi);
        for (var i=0;i<collection.files.length;i++) {
            var file = collection.files[i];
            if (file.file_id == ufi.file_id) {
              file.skipScore(ufi.user_id, ufi.skip_score, true);
              break;
            }
        }
    };

    methods.remove = function(file) {
      logger.log("remove:", file);
    };

    window.player.completeCb = function(file) {
      logger.log("PLAYLIST COMPLETED CB:", file.basename);
      methods.incTrack(1, 1, []);
    };
    window.player.errorCb = function(file) {
      console.error("PLAYLIST ERROR CB:", file.basename);
      methods.incTrack(1, 0, []);
    };

    window.player.timeStatusCb = function(file) {
      // logger.log("window.player.timeStatusCb");
      // logger.log("file.duration:", file.duration, "file.position:", file.position);
      if (file.duration <= 0 || file.position <= 0) {
        // logger.log("return;");
        return;
      }
      var percent_played = (file.position / file.duration) * 100;
      file.spec.duration = file.duration;
      file.spec.position = file.position;
      file.mark_as_played(FmpListeners.collection.listener_user_ids, percent_played);
      file.spec.percent_played = percent_played;
      // logger.log("percent_played:", file.percent_played);
      collection.playingFile = file;
      $rootScope.$broadcast("time-status", file);
    }
    window.player.next = methods.next;
    window.player.prev = methods.prev;
    methods.load();
    return methods;
});
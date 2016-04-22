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

    methods.incTrack = function(by) {
      if (typeof by == 'undefined') {
        by = 1;
      }
      if (!collection.files || collection.files.length == 0) {
        return;
      }
      var playingIdx = -1,
          prevIdx = -1,
          files = [];

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
        if (FmpListeners.collection.listener_user_ids.indexOf(file.cued.user_id) != -1) {
          files.push(file);
        }
      }

      if (files.length == 0) {
        console.log("error files.length == 0");
        return;
      }

      if (!atLeastOneWithoutError) {
        console.log("error !atLeastOneWithoutError");
        return;
      }

      for (var i=0;i<files.length;i++) {
        // Get the playing index, then increment & decrement the score
        // accordingly.
        var file = files[i];
        if (file.playing) {
          playingIdx = i;
          prevIdx = i;
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

      if (FmpListeners.collection.listener_user_ids.length == 1) {
        var voted_to_skip = [];
        for (var i=0;i<window.player.file.spec.user_file_info.length;i++) {
            var ufi = window.player.file.spec.user_file_info[i];
            if (listener_user_ids.indexOf(ufi.user_id) != -1) {
                ufi.voted_to_skip = true;
                voted_to_skip.push(ufi.user_id);
                // This person didn't listen to the song.
                continue;
            }
            ufi.voted_to_skip = false;
        };
        window.player.file.voted_to_skip = voted_to_skip;
      }
      window.player.file.set_skipped_by_listeners(FmpListeners.collection.listener_user_ids);
      methods.incTrack(1);
    };

    methods.prev = function() {
      logger.log("PLAYLIST PREV");
      methods.incTrack(-1);
    };

    methods.getRandomInt = function (min, max) {
      return Math.floor(Math.random() * (max - min)) + min;
    }

    methods.organize_random = function(el, played_first) {
      if (collection.organizeLock) {
        return;
      }
      collection.organizeLock = true;
      if (typeof played_first == "undefined") {
        played_first = false;
      }
      var files = [],
          groupedByUsers = [],
          preload = [],
          alreadyLoaded = []
          walkList = function(idx, file){
            if (alreadyLoaded.indexOf(file.id) != -1) {
              return;
            }
            alreadyLoaded.push(file.id);
            var user_id = 0;
            if ("cued" in file && file.cued) {
              user_id = file.cued.user_id;
            }
            if (!(user_id in groupedByUsers)) {
              groupedByUsers[user_id] = [];
            }
            if (!user_id || FmpListeners.collection.listener_user_ids.indexOf(user_id) != -1) {
                groupedByUsers[user_id].push(file);
            } else {
                // preload.push(file);
                // logger.log("fallback push:", file.id);
                groupedByUsers[user_id].push(file);
            }
          };

      $.each(collection.files, walkList);
      $.each(FmpPreload.collection.files, walkList);

      FmpPreload.collection.files = preload;
      FmpPreload.save();

      var fileFound = true;
      while (fileFound) {
        fileFound = false;
        $.each(groupedByUsers, function(user_id, user_files) {
          console.log("user_id:", user_id)
          if (!user_files || user_files.length == 0) {
            return;
          }

          fileFound = true;
          var file = false;

          if (!played_first) {
            var idx = methods.getRandomInt(0, user_files.length-1),
                file = user_files.splice(idx, 1);
            file = file[0];
          } else {
            file = user_files.pop();
          }

          if (!file) {
            return;
          }

          console.log("file:", file.id);
          files.push(file);
        });
      }
      console.log("files:", files);
      collection.files = files;
      collection.organizeLock = false;
    };

    methods.organize = function(el) {
      methods.organize_random(el, true);
    };

    methods.deleteFile = function(file, deleteCb) {
        console.log("deleteFile");
        if (typeof file.spec != "undefined" &&
            typeof file.spec.keep != "undefined" &&
            file.spec.keep) {
            return;
        }

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
      FmpSync.syncFile(file.spec);
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
      window.player.file.completed(FmpListeners.collection.listener_user_ids);
      methods.incTrack(1);
    };
    window.player.errorCb = function(file) {
      console.error("PLAYLIST ERROR CB:", file.basename);
      methods.incTrack(1);
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
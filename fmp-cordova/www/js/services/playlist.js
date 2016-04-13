fmpApp.factory('FmpPlaylist', function($rootScope, FmpUtils, FmpListeners,
                                       FmpSync, FmpPreload){
  var collection = {
        files: [],
        lastSave: 0,
        lastAction: 0,
        "sync": {},
        FmpSync: FmpSync,
        lastSyncTime: 0,
        organizeLock:false,
        saveLock: false
      },
      methods = {
        collection: collection
      };

    methods.load = function() {
      collection.files = [];
      if (typeof localStorage["playlist"] == "undefined" ||
          !localStorage["playlist"]) {
        return;
      }
      var files = JSON.parse(localStorage["playlist"]);
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
          // file.pause();
        }
      }
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
          prevIdx = -1;
      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i];
        if (file.playing) {
          playingIdx = i;
          prevIdx = i;
          if (incScore == -1) {
            file.spec.skipped = true;
            file.deinc_score(FmpListeners.collection.listener_user_ids);
            file.save();
          }
          if (incScore == 1) {
            file.spec.skipped = false;
            file.inc_score(FmpListeners.collection.listener_user_ids);
            file.save();
          }
          break;
        }
      }
      playingIdx = playingIdx + by;
      if (playingIdx < 0) {
        playingIdx = collection.files.length - 1;
      }
      if (playingIdx > collection.files.length) {
        playingIdx = 0;
      }

      if (prevIdx != playingIdx && prevIdx != -1 &&
          typeof collection.files[prevIdx] != 'undefined') {
            var file = collection.files[prevIdx];
            file.playing = false;
            file.save();
      }

      for (var i=0;i<collection.files.length;i++) {
        if (i == playingIdx) {
          var file = collection.files[i];
          file.play();
          break;
        }
      }
    }

    methods.next = function() {
      console.log("PLAYLIST NEXT");
      methods.incTrack(1, -1, []);
    };

    methods.prev = function() {
      console.log("PLAYLIST PREV");
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
          console.log("file:", file);
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
          console.log("FILE IS NULL!");
          continue;
        }
        if (!file.spec) {
          console.log("!file.spec", file);
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
            console.log("fallback push:", file.id);
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
              console.log("PLAYED:", file.id);
            }
          } else {
            unplayedFiles.push(file);
          }
        }
      }
      console.log("playedFiles:", playedFiles);
      console.log("playingFile:", playingFile);
      console.log("unplayedFiles:", unplayedFiles);
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

    methods.rate = function(ufi) {
        console.log("rate:", ufi);
        for (var i=0;i<collection.files.length;i++) {
            var file = collection.files[i];
            if (file.file_id == ufi.file_id) {
                file.rate(ufi.user_id, ufi.rating, true);
                break;
            }
        }
    };

    methods.score = function (ufi) {
        console.log("score:", ufi);
        for (var i=0;i<collection.files.length;i++) {
            var file = collection.files[i];
            if (file.file_id == ufi.file_id) {
              file.skipScore(ufi.user_id, ufi.skip_score, true);
              break;
            }
        }
    };

    methods.remove = function(file) {
      console.log("remove:", file);
    };

    window.player.completeCb = function(file) {
      console.log("PLAYLIST COMPLETED CB:", file.basename);
      methods.incTrack(1, 1, []);
    };
    window.player.errorCb = function(file) {
      console.error("PLAYLIST ERROR CB:", file.basename);
      methods.incTrack(1, 0, []);
    };

    window.player.timeStatusCb = function(file) {
      // console.log("window.player.timeStatusCb");
      // console.log("file.duration:", file.duration, "file.position:", file.position);
      if (file.duration <= 0 || file.position <= 0) {
        // console.log("return;");
        return;
      }
      var percent_played = (file.position / file.duration) * 100;
      file.spec.duration = file.duration;
      file.spec.position = file.position;
      file.mark_as_played(FmpListeners.collection.listener_user_ids, percent_played);
      file.spec.percent_played = percent_played;
      // console.log("percent_played:", file.percent_played);
      collection.playingFile = file;
      $rootScope.$broadcast("time-status", file);
    }
    window.player.next = methods.next;
    window.player.prev = methods.prev;
    methods.load();
    return methods;
});
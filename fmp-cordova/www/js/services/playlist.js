fmpApp.factory('FmpPlaylist', function($rootScope, FmpUtils, FmpListeners,
                                       FmpSync){
  var collection = {
        files: [],
        lastSave: 0,
        lastAction: 0,
        "sync": {},
        FmpSync: FmpSync,
        lastSyncTime: 0
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
      var files = [];
      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i];
        file.save();
        files.push("file-"+file.file_id);
      }
      localStorage.playlist = JSON.stringify(files);
    };

    methods.incTrack = function(by, skipped, user_ids) {
      if (!collection.files || collection.files.length == 0) {
        return;
      }
      var playingIdx = -1;
      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i];
        if (file.playing) {
          playingIdx = i;
          if (skipped) {
            file.spec.skipped = true;
            file.deinc_score(FmpListeners.collection.listener_user_ids);
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
      methods.incTrack(1, true, []);
    };

    methods.prev = function() {
      console.log("PLAYLIST PREV");
      methods.incTrack(-1, false);
    };

    methods.organize = function() {
      var newOrder = [],
          playedFiles = [],
          unplayedFiles = [],
          playingFile = null,
          groupedByUsers = {};

      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i],
            user_id = file.spec.cued.user_id;
        if (typeof groupedByUsers[user_id] == "undefined"){
          groupedByUsers[user_id] = [];
        }
        groupedByUsers[user_id].push(file);
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
          if (file.played) {
            if (file.playing) {
              playingFile = file;
            } else {
              playedFiles.push(file);
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
      methods.incTrack(1, false);
    };
    window.player.errorCb = function(file) {
      console.error("PLAYLIST ERROR CB:", file.basename);
      methods.incTrack(1, false);
    };

    window.player.timeStatusCb = function(file) {
      if (file.duration <= 0 || file.position <= 0) {
        return;
      }
      var percent_played = (file.position / file.duration) * 100;
      file.mark_as_played(FmpListeners.collection.listener_user_ids, percent_played);
    }
    window.player.next = methods.next;
    window.player.prev = methods.prev;
    methods.load();
    return methods;
});
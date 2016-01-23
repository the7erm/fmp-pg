fmpApp
.factory('FmpPlaylist', function($rootScope, FmpPreload,
                                 FmpUtils, $http, FmpConfig, FmpLocalStorage,
                                 FmpSocket, FmpSync, FmpListeners){
  var collection = {
        files: [],
        idx: 0,
        playing: {},
        lastSave: 0,
        lastAction: 0,
        "sync": {}
      },
      methods = {
        collection: collection
      };

    methods.markAction = function() {
      collection.lastAction = FmpUtils.now().timestamp_UTC;
      localStorage.lastAction = collection.lastAction;
      FmpSocket.send({
        "action": "test",
        "payload": {
          "satellite": "user_action",
          "time": Math.floor(Date.now() / 1000)
        }
      });
    }

    methods.reset = function() {
      collection.files = [];
      collection.playing = {};
      collection.idx = 0;
    };

    methods.load = function() {
      console.log("LOAD");
      if (localStorage.lastAction) {
        collection.lastAction = parseFloat(localStorage.lastAction);
      }

      try {
        collection.sync = JSON.parse(localStorage.sync) || {};
      } catch (e) {
        console.error("load collection.sync err:", e);
        console.error("data:", localStorage.sync);
      }

      try {
        collection.files = JSON.parse(localStorage.playlistFiles) || [];
      } catch (e) {
        console.error("load collection.files err:", e);
        console.error("data:", localStorage.playlistFiles);
      }

      try {
        collection.idx = parseInt(localStorage.playlistIdx) || 0;
        if (collection.idx >= collection.files.length) {
          collection.idx = 0;
        }

      } catch (e) {
        console.log("load collection.idx err:", e);
      }
      try {
        collection.playing = collection.files[collection.idx];
      } catch (e) {
        console.log("load collection.playing err:", e);
      }
      console.log("LOADED:", collection);
      methods.unique();
      methods.removeAlreadyPlayedPreload();
    };

    methods.removeAlreadyPlayedPreload = function() {
      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i];
        FmpPreload.removeFile(file);
      }
    };

    methods.unique = function() {
      if (collection.files.length == 0) {
        return;
      }
      var current = collection.files[collection.idx],
          currentId = current.id,
          alreadyAdded = [],
          newList = [],
          idx = -1;
      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i];
        if (alreadyAdded.indexOf(file.id) == -1) {
          newList.push(file);
          alreadyAdded.push(file.id);
          if (file.id == currentId) {
            idx = newList.length - 1;
          }
        }
      }
      var changed = idx != collection.idx;
      collection.idx = idx;
      collection.files = newList;
      collection.playing = newList[idx];
      methods.setIndex(idx);
      if (changed) {
        $rootScope.$broadcast("index-changed");
      }
    }

    console.log("FmpPlaylist.collection:", collection);
    methods.save = function() {
      localStorage.playlistFiles = JSON.stringify(collection.files);
      localStorage.playlistIdx = collection.idx;
      localStorage.playlistPlaying = JSON.stringify(collection.playing);
      localStorage.sync = JSON.stringify(collection.sync);
      var now = new Date();
      collection.lastSave = now.valueOf();
    };

    methods.getUnplayedFile = function() {
      if (FmpPreload.collection.files.length == 0) {
        return null;
      }
      var file = FmpPreload.collection.files.shift(),
          found = false,
          ignore = ['flv', 'wma', 'wmv'];

      if (ignore.indexOf(file.ext) != -1) {
        return methods.getUnplayedFile();
      }
      for(var i=0;i<collection.files.length;i++) {
        if (collection.files.id == file.id) {
          found = true;
          break;
        }
      }
      // The file was not found in the playlist so we use it.
      if (!found) {
        return file;
      }
      // The file was found in the playlist so we try to get another one.
      if (FmpPreload.collection.files.length > 0) {
        return methods.getUnplayedFile();
      }
      return null;
    }

    methods.setIndex = function(idx) {
      if (idx == undefined) {
        console.log("setIndex idx is undefined");
        return;
      }
      if (idx == "+1" || idx == "+") {
        idx = parseInt(collection.idx) + 1;
      }
      if (idx == "-1" || idx == "-") {
        idx = parseInt(collection.idx) - 1;
      }
      if (idx < 0) {
        idx = collection.files.length - 1;
      }
      idx = parseInt(idx);
      console.log("setIndex:", idx);
      if (idx >= collection.files.length) {
        var file = methods.getUnplayedFile();
        if (file != null) {
          collection.files.push(file);
        } else {
          idx = 0;
        }
      }
      console.log("FmpPlaylist.setIndex:", idx);
      if (idx == collection.idx) {
        console.log("idx == collection.idx");
        if (collection.playing && collection.files && collection.files[idx] &&
            collection.playing.id == collection.files[idx].id) {
          console.log("return FmpPlaylist.setIndex collection.playing.id == collection.files[idx].id",
                      collection.playing.id);
          console.log("collection.files.length:", collection.files.length);
          console.log("collection.files:", collection.files);
          methods.initMusicControls();
          $rootScope.$broadcast("index-changed");
          return;
        }
      }
      collection.idx = idx;
      console.log("FmpPlaylist.setIndex collection.idx:", collection.idx);
      collection.playing = collection.files[idx];
      methods.initMusicControls();
      methods.save();
      $rootScope.$broadcast("index-changed");
    }

    methods.onButtonEvents = function(action) {
      console.log("onButtonEvents:", action);
      switch(action) {
        case 'music-controls-next':
            // Do something
            methods.next();
            break;
        case 'music-controls-previous':
            // Do something
            methods.prev();
            break;
        case 'music-controls-pause':
            // Do something
            collection.player.pause();
            break;
        case 'music-controls-play':
            // Do something
            collection.player.pause();
            break;
        case 'music-controls-destroy':
            // Do something
            break;

        // Headset events (Android only)
        case 'music-controls-media-button' :
            // Do something
            collection.player.pause();
            break;
        case 'music-controls-headset-unplugged':
            // Do something
            break;
        case 'music-controls-headset-plugged':
            // Do something
            break;
        default:
            break;
      }
    };

    methods.initMusicControls = function() {
      console.log("**** INIT MUSIC CONTROLS");
      var title = "",
          artist = "",
          artist_title = "";

      if (typeof collection.playing == 'undefined') {
        return;
      }
      console.log("playlist.collection.playing:", collection.playing);
      if (collection.playing.artists  && collection.playing.artists.length > 0) {
        artist = collection.playing.artists[0].name;
      }

      if (collection.playing.titles && collection.playing.titles.length > 0) {
        title = collection.playing.titles[0].name;
      }

      artist_title = artist;
      if (artist_title && title) {
        artist_title += " - "+ title;
      }
      if (!artist && title) {
        artist_title = title;
      }
      if (!artist_title &&
          collection.playing.locations &&
          collection.playing.locations.length > 0) {
        var basename = collection.playing.locations[0].basename;
        if (basename.indexOf("-") != -1) {
          var parts = basename.split("-",2);
          artist = parts[0];
          title = parts[1];
        }
        artist_title = basename;
      }

      var spec = {
          track       : title,        // optional, default : ''
          artist      : artist,                       // optional, default : ''
          // cover       : 'albums/absolution.jpg',      // optional, default : nothing
          isPlaying   : true,                         // optional, default : true
          dismissable : true,                         // optional, default : false

          // hide previous/next/close buttons:
          hasPrev   : true,      // show previous button, optional, default: true
          hasNext   : true,      // show next button, optional, default: true
          hasClose  : true,       // show close button, optional, default: false

          // Android only, optional
          // text displayed in the status bar when the notification (and the ticker) are updated
          ticker    : artist_title
      };
      console.log("MusicControls spec:", spec);

      var mc = MusicControls.create(spec, function(res){
          // on success
          console.log("**** SUCCESS");
          console.log("initMusicControls success:", res);
          MusicControls.subscribe(methods.onButtonEvents);
          MusicControls.listen();
          console.log("SUBSCRIBED & LISTENING");
      }, function(err){
          // on error
          console.log("**** FAILURE");
          console.log("initMusicControls ERROR:", err);
      });
      console.log("MC Object:", mc);
      // Register callback

    };

    methods.updateSkipScore = function(value) {
      var now = FmpUtils.now();
      for (var i=0;i<collection.playing.user_file_info.length;i++) {
        var ufi = collection.playing.user_file_info[i];
        ufi.skip_score = parseInt(ufi.skip_score) + value;
        FmpUtils.calculateTrueScore(ufi);
        FmpUtils.updateHistory(ufi, {"skip_score": ufi.skip_score});
      }
    }

    methods.incScore = function() {
      methods.updateSkipScore(1);
    }

    methods.deIncScore = function() {
      methods.updateSkipScore(-1);
    };

    methods.next = function() {
      methods.deIncScore();
      methods.setIndex("+1");
      methods.markAction();
    };

    methods.prev = function() {
      methods.setIndex("-1");
      methods.markAction();
    };

    methods.markAsPlayed = function(position, remaining, duration) {
      // FmpPlaylist.markAsPlayed(position, remaining, duration)
      var percent_played = (position / duration) * 100;
      console.log("percent_played:", percent_played);
      for (var i=0;i<collection.playing.user_file_info.length;i++) {
          var ufi = collection.playing.user_file_info[i];
          FmpUtils.updateHistory(ufi, {"percent_played": percent_played});
      }
      // markAsPlayed = function(file_id, user_ids, percent_played)
      FmpSync.markAsPlayed(collection.playing.id,
                           FmpListeners.collection.listener_user_ids,
                           percent_played);
      var now = new Date();
      if (collection.lastSave < now.valueOf() - 5000) {
        console.log("++++++++++SAVE");
        methods.save();
      }
    };

    methods.playFile = function (file) {
      var idx = FmpUtils.indexOfFile(collection.files, file);
      if (idx != -1) {
        console.log("playFile:", "IDX:",idx, "file:", file);
        if (collection.idx == idx) {
          return;
        }
        methods.setIndex(idx);
        return;
      }
      console.log("playFile from preload:", file);
      FmpPreload.removeFile(file);
      collection.files.push(file);
      idx = FmpUtils.indexOfFile(collection.files, file);
      if (idx != -1) {
        console.log("ADDED playFile:", "IDX:",idx, "file:", file);
        methods.setIndex(idx);
        return;
      }
      console.log("ERROR didn't find in PRELOAD or PLAYLIST file:", file);
    };

    $rootScope.$on("synced", function(){
      var groupedByUsers = {};
      for (var i=0;i<FmpPreload.collection.files.length;i++){
        var file = FmpPreload.collection.files[i],
            user_id = "";
        if (file.cued && file.cued.user_id) {
          user_id = file.cued.user_id;
        }
        if (typeof groupedByUsers[user_id] == 'undefined') {
          groupedByUsers[user_id] = [];
        }
        groupedByUsers[user_id].push(file);
      }

      var stillHasFiles = true,
          pushedFiles = false;

      while(stillHasFiles) {
        stillHasFiles = false;
        for (var user_id in groupedByUsers) {
          var files = groupedByUsers[user_id];
          if (files.length == 0) {
            continue;
          }
          stillHasFiles = true;
          var file = files.shift(),
              idx = FmpUtils.indexOfFile(collection.files, file);
          if (idx != -1) {
            continue;
          }
          pushedFiles = true;
          collection.files.push(file);
        }
      }
      if (pushedFiles) {
        $rootScope.$broadcast("playlist-changed");
      }
    });


    return methods;
});
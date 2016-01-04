starterServices
.factory('FmpPlaylist', function($ionicPlatform, $rootScope, FmpPreload,
                                 FmpUtils, $http, FmpConfig){
  var collection = {
        files: [],
        idx: 0,
        playing: {},
        lastSave: 0,
        lastAction: 0
      },
      methods = {
        collection: collection
      };

    methods.markAction = function() {
      collection.lastAction = FmpUtils.now().timestamp_UTC;
      localStorage.lastAction = collection.lastAction;
    }

    methods.load = function() {
      console.log("LOAD");
      if (localStorage.lastAction) {
        collection.lastAction = parseFloat(localStorage.lastAction);
      }

      try {
        collection.files = JSON.parse(localStorage.playlistFiles) || [];
      } catch (e) {
        console.log("load collection.files err:", e);
        console.log("data:", localStorage.playlistFiles);
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
    methods.save = function(){
      localStorage.playlistFiles = JSON.stringify(collection.files);
      localStorage.playlistIdx = collection.idx;
      localStorage.playlistPlaying = JSON.stringify(collection.playing);
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
          $rootScope.$broadcast("index-changed");
          return;
        }
      }
      collection.idx = idx;
      console.log("FmpPlaylist.setIndex collection.idx:", collection.idx);
      collection.playing = collection.files[idx];
      methods.save();
      methods.initMusicControls();
      $rootScope.$broadcast("index-changed");
    }

    methods.initMusicControls = function() {
      if (collection.musicControls) {
        collection.musicControls.destroy();
      }
      collection.musicControls = MusicControls.create({
          track       : collection.playing['titles'][0].name,        // optional, default : ''
          artist      : collection.playing['artists'][0].name,                       // optional, default : ''
          // cover       : 'albums/absolution.jpg',      // optional, default : nothing
          isPlaying   : true,                         // optional, default : true
          dismissable : true,                         // optional, default : false

          // hide previous/next/close buttons:
          hasPrev   : true,      // show previous button, optional, default: true
          hasNext   : true,      // show next button, optional, default: true
          hasClose  : true,       // show close button, optional, default: false

          // Android only, optional
          // text displayed in the status bar when the notification (and the ticker) are updated
          ticker    : collection.playing['titles'][0].name+" "+collection.playing['artists'][0].name
      }, function(){
          // on success
      }, function(){
          // on error
      });
      // Register callback
      collection.musicControls.subscribe(methods.onButtonEvents);
      collection.musicControls.listen();
    };

    methods.onButtonEvents = function() {
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
      var percent = (position / duration) * 100;
      console.log("percent:", percent);
      for (var i=0;i<collection.playing.user_file_info.length;i++) {
          var ufi = collection.playing.user_file_info[i];
          FmpUtils.updateHistory(ufi, {"percent_played": percent});
      }
      var now = new Date();
      if (collection.lastSave < now.valueOf() - 5000) {
        console.log("++++++++++SAVE");
        methods.save();
      }
    };

    $ionicPlatform.ready(function(){

    });

    return methods;
});
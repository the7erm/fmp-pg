starterServices
.factory('FmpConductor', function($http,
                                  $ionicPlatform,
                                  $rootScope,
                                  FmpCache,
                                  FmpConfig,
                                  FmpDownloader,
                                  FmpIpScanner,
                                  FmpPlayer,
                                  FmpPlaylist,
                                  FmpPreload,
                                  FmpUtils){
  // The conductor is sort of a 'main' service of sorts.
  // It's intended to keep all the services synced, and execute
  // code in the proper order.

  var collection = {
          "FmpCache": FmpCache,
          "FmpConfig": FmpConfig,
          "FmpDownloader": FmpDownloader,
          "FmpIpScanner": FmpIpScanner,
          "FmpPlayer": FmpPlayer,
          "FmpPlaylist": FmpPlaylist,
          "FmpPreload": FmpPreload,
          "FmpUtils": FmpUtils
      },
      methods = {
          collection: collection
      };

  methods.updateSyncHistory = function(processed_history) {
    if (!processed_history) {
      console.log("no processed_history");
      return;
    }
    /*
      This section will loop through the processed data from the server,
      and update FmpPlaylist.collection.files with the data from the server.
    */
    for(var i=0;i<processed_history.length;i++) {
      var file = processed_history[i];
      if (typeof file.id == 'undefined'){
        console.log("undefined file.id");
        if (typeof file[0] != 'undefined' &&
            typeof file[0].id != 'undefined') {
          file = file[0];
        } else {
          continue;
        }
      }
      var idx = FmpUtils.indexOfFile(FmpPlaylist.collection.files, file);
      console.log("checking:", file);
      if (idx != -1) {
        console.log("updating file.id:", file.id, "idx:", idx);
        FmpUtils.addLocalData(file);
        FmpPlaylist.collection.files[idx] = file;
        if (file.id == FmpPlaylist.collection.playing.id) {
          FmpPlaylist.collection.playing = FmpPlaylist.collection.files[idx];
          $rootScope.$broadcast("playing-data-changed");
        }
      }
    }
  }

  methods.processFiles = function(files, collection) {
    collection.files = [];
    for(var i=0;i<files.length;i++){
      var file = files[i];
      FmpUtils.addLocalData(file);
      if (!FmpUtils.validFile(file.locations[0].basename)) {
        continue;
      }
      FmpDownloader.checkExisting(file);
      collection.files.push(file);
      console.log("file:", file);
    }
  };

  methods.syncAll = function(data) {
    console.log("syncAll:", data);
    console.log("playlist");
    methods.processFiles(data.history, FmpPlaylist.collection);
    console.log("preload");
    methods.processFiles(data.preload, FmpPreload.collection);
    FmpPlaylist.collection.idx = FmpPlaylist.collection.files.length - 1;
    FmpPlaylist.collection.playing = FmpPlaylist.collection.files[FmpPlaylist.collection.idx];
    var percent_played = parseFloat(FmpPlaylist.collection.playing['percent_played']);
    FmpPlayer.setMedia();
    FmpPlayer.collection.media.pause();
    var duration = FmpPlayer.collection.media.getDuration();
    console.log("duration:", duration, "percent_played:", percent_played);
    var tmp = function() {
        var duration = FmpPlayer.collection.media.getDuration();
        console.log("duration:", duration);
        if (duration == -1) {
          setTimeout(tmp, 500);
          return;
        }
        var decimal = percent_played * 0.01;
        localStorage.position = decimal * duration;
        FmpPlayer.collection.media.seekTo(localStorage.position * 1000);
        FmpPlayer.save();
    };
    if (percent_played) {
      setTimeout(tmp, 500);
    }
  }

  methods.sync = function() {
    /*
      Connect to the server send the current playlist & state.
    */
    if (!FmpConfig.url) {
      return;
    }
    console.log("SYNC:", FmpPlaylist.collection);
    $http({
      method: 'POST',
      url: FmpConfig.url+"sync",
      data: FmpPlaylist.collection,
      headers: {
          'Content-Type': "application/json"
      },
    }).then(function(response) {
      console.log("SYNC response.data:", response.data);
      // TODO Loop through response.data and update the playlist/preload
      if (FmpPlaylist.collection.state == Media.MEDIA_RUNNING) {
        // The player is playing so don't change the file that's playing
        // or the playlist
        methods.updateSyncHistory(response.data.processed_history);
      } else {
        // The player isn't playing so we'll change the playing song
        // and also change the playlist
        methods.syncAll(response.data);
      }
      FmpPlayer.save();
      FmpPlaylist.save();

    }, function errorCallback(response) {
      // called asynchronously if an error occurs
      // or server returns response with an error status.
    });
  };

  setInterval(methods.sync, 60000); // sync once a minutes

  $rootScope.$on("server-found", function(){
    // This trigger happens whenever FmpIpScanner finds an address.
    FmpConfig.url = FmpIpScanner.collection.url;
    // Get the preload
    FmpPreload.fetch();
    // Sync the playlist to the server.
    // FmpPlaylist.sync();
  });

  $ionicPlatform.ready(function() {
    // fetchPreload
    // cordova.file isn't available until ionicPlatform.ready()
    FmpConfig.cacheDir = cordova.file.externalCacheDirectory;
    FmpIpScanner.startScan();

    // fetchPreload
    //collection.cacheDir = cordova.file.externalCacheDirectory;
    FmpPlaylist.load();
    if (typeof FmpPlaylist.collection.idx != 'undefined' &&
        typeof FmpPlaylist.collection.files[FmpPlaylist.collection.idx] != 'undefined') {
      FmpPlaylist.setIndex(FmpPlaylist.collection.idx);
      collection.firstRun = false;
    } else {
      collection.firstRun = true;
    }
    console.log("collection.reloadPlaylistOnFetch:",
                collection.reloadPlaylistOnFetch);
    if (collection.firstRun) {
      // This section of code will be used on first run
      $rootScope.$on("preload-fetched-first-run", function(){
        if (!collection.firstRun) {
          return;
        }
        collection.firstRun = false;
        FmpPlaylist.load();
        FmpPlaylist.setIndex(FmpPlaylist.collection.idx);
        // Disable listening for "preload-fetched"
        $rootScope.$$listeners["preload-fetched-first-run"] = [];
      });
    }

    collection.mediaTimer = setInterval(FmpPlayer.timeStatus, 1000);
  });

  return methods;
});
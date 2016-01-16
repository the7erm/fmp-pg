starterServices
.factory('FmpConductor', function($http,
                                  $ionicPlatform,
                                  $rootScope,
                                  FmpCache,
                                  FmpConfig,
                                  FmpConstants,
                                  FmpDownloader,
                                  FmpIpScanner,
                                  FmpListeners,
                                  FmpPlayer,
                                  FmpPlaylist,
                                  FmpPreload,
                                  FmpSync,
                                  FmpUtils){
  // The conductor is sort of a 'main' service of sorts.
  // It's intended to keep all the services synced, and execute
  // code in the proper order.

  var collection = {
          "FmpCache": FmpCache,
          "FmpConfig": FmpConfig,
          "FmpConstants": FmpConstants,
          "FmpDownloader": FmpDownloader,
          "FmpIpScanner": FmpIpScanner,
          "FmpListeners": FmpListeners,
          "FmpPlayer": FmpPlayer,
          "FmpPlaylist": FmpPlaylist,
          "FmpPreload": FmpPreload,
          "FmpSync": FmpSync,
          "FmpUtils": FmpUtils,
          "syncLock": false,
          "syncTime": 0
      },
      methods = {
          collection: collection
      };

  FmpSync.collection.FmpPreload = FmpPreload;
  FmpSync.collection.FmpPlaylist = FmpPlaylist;
  FmpSync.collection.FmpListeners = FmpListeners;

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
      var idx = FmpUtils.indexOfFile(FmpPreload.collection.files, file);
      console.log("checking:", file);
      if (idx != -1) {
        console.log("updating file.id:", file.id, "idx:", idx);
        FmpUtils.addLocalData(file);
        FmpPreload.collection.files[idx] = file;
      }
    }
  }

  methods.addFilesToPlaylist = function(files) {
    for (var i=0;i<files.length;i++) {
      var file = files[i],
          idx = FmpUtils.indexOfFile(FmpPlaylist.collection.files, file);
      if (idx == -1) {
        // wasn't found so we add it.
        FmpPlaylist.collection.files.push(file);
      }
      FmpDownloader.checkExisting(file);
    }
  };

  methods.updateSyncData = function(data){
    var playlist = FmpUtils.sanitize(data.history),
        preload = FmpUtils.sanitize(data.preload);

    for (var i=0;i<playlist.length;i++) {
      var file = playlist[i],
          idx = FmpUtils.indexOfFile(FmpPlaylist.collection.files, file);
      if (idx == -1) {
        // wasn't found so we add it.
        FmpPlaylist.collection.files.push(file);
        FmpDownloader.checkExisting(file);
      }
    }

    for (var i=0;i<preload.length;i++) {
      var file = preload[i],
          idx = FmpUtils.indexOfFile(FmpPreload.collection.files, file);
      idx = FmpUtils.indexOfFile(FmpPreload.collection.files, file);
      if (idx == -1) {
        // wasn't found so we add it.
        FmpPreload.collection.files.push(file);
        FmpDownloader.checkExisting(file);
      }
    }

  };

  methods.sync = function() {
    /*
      Connect to the server send the current playlist & state.
    */
    if (!FmpConfig.url || collection.syncLock) {
      return;
    }
    FmpSync.sync();
    FmpSync.syncCollections();
    return;
    var data = {
      "playlist": FmpPlaylist.collection,
      "preload": FmpPreload.collection,
      "listeners": FmpListeners.collection
    };
    console.log("SYNC:", data);
    $http({
      method: 'POST',
      url: FmpConfig.url+"sync",
      data: data,
      headers: {
          'Content-Type': "application/json"
      }
    }).then(function(response) {
      console.log("SYNC response.data:", response.data);
      if (response.data.sync_priority == "mothership") {
        FmpPlaylist.reset();
        FmpPreload.reset();
      }
      if (response.data.sync_priority == "satellite") {
        FmpPreload.reset();
      }
      methods.updateSyncData(response.data);
      if (response.data.sync_priority == "mothership") {
        FmpPlaylist.collection.idx = FmpPlaylist.collection.files.length - 1;
        FmpPlaylist.collection.playing = FmpPlaylist.collection.files[FmpPlaylist.collection.idx];
        FmpPlayer.resume();
        $rootScope.$broadcast("index-changed");
      }
      FmpPlayer.save();
      FmpPlaylist.save();
      FmpPreload.save();
      $rootScope.$broadcast("preload-changed");
      FmpCache.clean(FmpPlaylist.collection.files,
                     FmpPreload.collection.files);
      collection.syncLock = false;
      collection.syncTime = new Date();
      console.log("SYNC TIME:", collection.syncTime);
      $rootScope.$broadcast("synced");
    }, function errorCallback(response) {
      collection.syncLock = false;
      // called asynchronously if an error occurs
      // or server returns response with an error status.
      console.log("SYNC ERROR:", response);
      FmpConfig.url = "";
      FmpIpScanner.startScan();
    });
  };

  // setInterval(methods.sync, 60000); // sync once a minutes

  $rootScope.$on("server-found", function(){
    // This trigger happens whenever FmpIpScanner finds an address.
    FmpConfig.url = FmpIpScanner.collection.url;
    // Fetch the listeners
    FmpListeners.fetch();
    // Sync the playlist to the server.
  });

  $rootScope.$on("listeners-loaded", function(){
    // Get the preload
    // FmpPreload.fetch();
    methods.sync();
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

  methods.updateCollection = function(ufi, collection) {
    for (var i=0;i<collection.files.length;i++) {
      var file = collection.files[i];
      if (file.id == ufi.file_id) {
        for (var i2=0;i2<file.user_file_info.length;i2++) {
          var ufi2 = file.user_file_info[i2];
          if (ufi2.id == ufi.id) {
            file.user_file_info[i2] = ufi;
          }
        }
      }
    }
  };

  methods.setRating = function(ufi) {
      console.log("setRating:", ufi);
      FmpSync.set_attr(ufi.file_id, ufi.user_id, 'rating', ufi.rating);
      methods.processUfi(ufi);
  };

  methods.processUfi = function(ufi){
    if (typeof ufi.satellite_history == 'undefined') {
      ufi.satellite_history = {};
    }

    if (typeof ufi.satellite_history == 'undefined') {
      ufi.satellite_history = {};
    }

    FmpUtils.calculateTrueScore(ufi);

    FmpUtils.updateHistory(ufi, {
      "rating": ufi.rating,
      "skip_score": ufi.skip_score,
      "true_score": ufi.true_score
    });

    methods.updateCollection(ufi, FmpPlaylist.collection);
    methods.updateCollection(ufi, FmpPreload.collection);
  }

  FmpSync.processUfi = methods.processUfi;
  methods.stars = FmpConstants.stars;

  return methods;
});
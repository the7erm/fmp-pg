angular.module('starter.services', [])
.factory('FmpConfig', function($ionicPlatform, $rootScope){
  /*
      Media.MEDIA_NONE = 0;
      Media.MEDIA_STARTING = 1;
      Media.MEDIA_RUNNING = 2;
      Media.MEDIA_PAUSED = 3;
      Media.MEDIA_STOPPED = 4;
  */
  var collection = {
    'url': '',
    'cacheDir': null
  };

  return collection;
})
.factory("FmpConstants", function(){
  return {
    "NONE": Media.MEDIA_NONE,
    "STARTING": Media.MEDIA_STARTING,
    "PLAYING": Media.MEDIA_RUNNING,
    "PAUSED": Media.MEDIA_PAUSED,
    "STOPPED": Media.MEDIA_STOPPED
  }
})
.factory("FmpIpScanner", function($http, $rootScope){

  var collection = {
        "knownHosts": [],
        "scanHosts": [],
        "url": ""
      },
      methods = {
        collection: collection
      };

  methods.getKnownHosts = function() {
    var knownHosts = [];
    if (localStorage.knownHosts) {
      knownHosts = JSON.parse(localStorage.knownHosts);
    }
    collection.knownHosts = knownHosts;
    console.log("collection.knownHosts:", collection.knownHosts);
  }

  methods.generateHosts = function() {
    collection.scanHosts = [];
    methods.getKnownHosts();
    for (var i=0;i<collection.knownHosts.length;i++) {
      var host = collection.knownHosts[i];
      if (collection.scanHosts.indexOf(host) == -1) {
        collection.scanHosts.push(host);
        console.log("adding known host:", host);
      }
    }
    for(var i=1;i<255;i++) {
      var host = 'http://192.168.1.'+i+':5050/';
      if (collection.scanHosts.indexOf(host) == -1) {
        collection.scanHosts.push(host);
      }
    }
  }

  methods.scan = function(thread, FmpConfig) {
    if (collection.found || collection.scanHosts.length == 0) {
      return;
    }
    var host = collection.scanHosts.shift();
    console.log("scan thread:", thread, host);
    $http({
        method: 'GET',
        url: host+"fmp_version",
        timeout: 100
    }).then(function(response) {
      if (response.data.fmp) {
        collection.found = true;
        collection.url = host;
        scanEnd = new Date();
        if (collection.knownHosts.indexOf(host) == -1) {
          collection.knownHosts.push(host);
          localStorage.knownHosts = JSON.stringify(collection.knownHosts);
        }
        console.log("found fmp server at host:", host);
        console.log("Running time:", scanEnd.valueOf() -
                                     collection.scanStart.valueOf());
        $rootScope.$broadcast("server-found");
      }
    }, function errorCallback(response) {
      methods.scan(thread, FmpConfig);
    });
  };

  methods.startScan = function(FmpConfig) {
    methods.generateHosts();
    collection.scanStart = new Date();
    for (var i=1;i<5;i++) {
      methods.scan(i, FmpConfig);
    }
  }

  return methods;
})
.factory('FmpUtils', function(FmpConfig){
  var methods = {};
  methods.listDir = function (path, successCb, errorCb){
    if (typeof successCb == 'undefined') {
      successCb = function(entries) {
        console.log("FmpUtils.methods.listDir successCb:", entries);
      };
    }
    if (typeof errorCb == 'undefined') {
      errorCb = function(err) {
          console.log("FmpUtils.methods.listDir errorCb:", err);
      };
    }
    /* listDir stolen from
       https://github.com/driftyco/ng-cordova/issues/697#issuecomment-136957324 */
    window.resolveLocalFileSystemURL(path,
      function (fileSystem) {
        var reader = fileSystem.createReader();
        reader.readEntries(successCb, errorCb);
      },
      errorCb);
  };

  methods.isEmpty = function(arg) {
      return typeof arg == 'undefined' || !arg || arg == null || arg.length == 0;
  }

  methods.getExt = function(basename) {
    var parts = basename.split(".");
    if( parts.length <= 1 ) {
        return "";
    }
    return parts.pop().toLowerCase();
  }

  methods.pad = function(value) {
    if(value < 10) {
      return "0"+value;
    }
    return value;
  }

  methods.formatTime = function(seconds){
    var secs = Math.floor(seconds);
    var hr = Math.floor(secs / (60 * 60));
    secs = secs - (hr * 60 * 60);
    var mins = Math.floor(secs / 60);
    secs = secs - (mins * 60);
    var ret = "";
    if (hr > 0) {
      ret += hr;
    }
    if (hr > 0) {
      mins = methods.pad(mins);
    }
    ret += mins+":";
    secs = methods.pad(secs);
    ret += secs;
    return ret;
  };

  methods.now = function(now) {
    if (typeof now == 'undefined') {
      now = new Date();
    }
    var today = now.getUTCFullYear()+"/"+
              methods.pad(now.getUTCMonth()+1)+"/"+
              methods.pad(now.getUTCDate());
    return {
      "timestamp": now,
      "today": today,
      "timestamp_UTC": (now.valueOf() / 1000)
    };
  }

  methods.updateHistory = function(ufi, obj) {
    if (typeof ufi == 'undefined') {
      return;
    }
    if (typeof ufi.satellite_history == 'undefined') {
      ufi.satellite_history = {};
    }
    var now = methods.now();
    if (typeof ufi.satellite_history[now.today] == 'undefined') {
      ufi.satellite_history[now.today] = {};
    }
    ufi.satellite_history[now.today]["timestamp"] = now.timestamp.toISOString();
    ufi.satellite_history[now.today]["timestamp_UTC"] = now.timestamp_UTC;
    for (var k in obj) {
      console.log("K:",k, "v:", obj[k]);
      ufi.satellite_history[now.today][k] = obj[k];
    }
  }

  methods.calculateTrueScore = function(ufi) {
    var true_score = (
        (parseInt(ufi.rating) * 2 * 10) +
        (parseInt(ufi.skip_score) * 10)
    ) / 2;
    if (true_score >= -15 && true_score <= 125) {
      ufi.true_score = true_score;
    }
  }

  methods.indexOfFile = function(files, file) {
    for(var i=0;i<files.length;i++) {
        var fileToCompare = files[i];
      if (fileToCompare.id == file.id) {
        return i;
      }
    }
    return -1;
  }

  methods.addLocalData = function(fileFromServer) {
    fileFromServer.ext = methods.getExt(fileFromServer.locations[0].basename);
    var url = FmpConfig.url+"download?file_id="+fileFromServer.id,
        filename = fileFromServer.id+"."+fileFromServer.ext,
        tmpFile = filename + ".tmp",
        dst = FmpConfig.cacheDir+tmpFile;
    fileFromServer['dl-url'] = url;
    fileFromServer['filename'] = filename;
    fileFromServer['tmpFile'] = tmpFile;
    fileFromServer['fullFilename'] = FmpConfig.cacheDir+filename;
    fileFromServer['dl-tmp'] = dst;
  }

  methods.validFile = function(file) {
    var ignore = ['flv', 'wma', 'wmv'];

    if (ignore.indexOf(file.ext) != -1) {
      return false;
    }
    return true;
  }

  return methods;
})
.factory('FmpConductor', function($ionicPlatform,
                                  FmpCache,
                                  FmpConfig,
                                  FmpPlayer,
                                  FmpPlaylist,
                                  FmpPreload,
                                  FmpUtils,
                                  FmpIpScanner,
                                  FmpDownloader,
                                  $rootScope,
                                  $http){
  // The conductor is sort of a 'main' service of sorts.
  // It's intended to keep all the services synced, and execute
  // code in the proper order.

  var collection = {
          "FmpCache": FmpCache,
          "FmpConfig": FmpConfig,
          "FmpPlayer": FmpPlayer,
          "FmpPlaylist": FmpPlaylist,
          "FmpPreload": FmpPreload,
          "FmpUtils": FmpUtils,
          "FmpDownloader": FmpDownloader,
          "FmpIpScanner": FmpIpScanner
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
})
.factory('FmpPreload', function($ionicPlatform, FmpConfig, $http, FmpUtils,
                                $cordovaFile, FmpDownloader, $rootScope){

  var collection = {
        fetchLock: false,
        files: [],
      },
      methods = {
        collection: collection
      };

  if (typeof localStorage.preloadFiles != 'undefined') {
    // localStorage.collection.files = localStorage.preloadFiles;
  }

  methods.fetch = function(options) {
    console.log("fetchPreload");
    if (collection.fetchLock) {
      console.log("preload locked");
      return;
    }
    collection.fetchLock = true;
    if (typeof options == 'undefined') {
      options = {
        "offset": 0,
        "limit": 10
      };
    }

    if (typeof options.offset == 'undefined') {
      options.offset = 0;
    }

    if (typeof options.limit == 'undefined') {
      options.limit = 10;
    }

    var uids = collection.uids || [];
    uids = uids.join(",");
    $http({
      method: 'GET',
      url: FmpConfig.url+"search",
      params: {
        "user_ids": uids,
        "oc": true, // return only cued files.
        "q": "", // query.
        "s": options.offset,  // start at 0
        "l": options.limit
      }
    }).then(function(response) {
      console.log("FETCHED");
      methods.process(options, response);
      collection.fetchLock = false;
      $rootScope.$broadcast("preload-fetched-first-run");
      $rootScope.$broadcast("preload-fetched");
    }, function errorCallback(response) {
      // called asynchronously if an error occurs
      // or server returns response with an error status.
      collection.fetchLock = false;
    });
  };

  methods.fileInPreload = function(file) {
    if (FmpUtils.isEmpty(collection.files)) {
      return false;
    }
    var idx = FmpUtils.indexOfFile(collection.files, file);
    if (idx == -1) {
      return false;
    }
    return true;
  }

  methods.removeFile = function(file) {
    var idx = FmpUtils.indexOfFile(collection.files, file);
    if (idx == -1) {
      return;
    }
    collection.files.splice(idx, 1);
  };

  methods.getExt = function(file) {
    var ext = "";
    for(var i=0;i<file.locations.length;i++) {
        ext = FmpUtils.getExt(file.locations[i].basename);
        file.locations[i].ext = ext;
    }
    return ext;
  }

  methods.processFile = function(options, fileFromServer) {
    fileFromServer.ext = methods.getExt(fileFromServer);
    if (!FmpUtils.validFile(fileFromServer)) {
      return;
    }
    FmpUtils.addLocalData(fileFromServer);
    if (!methods.fileInPreload(fileFromServer)) {
      console.log("FmpPreload.process collection.files.push:", fileFromServer);
      collection.files.push(fileFromServer);
    } else {
      console.log("!FmpPreload.process collection.files.push:", fileFromServer);
    }
    var _options = null;
    if (typeof options.download != 'undefined' &&
        typeof options.download[i] != 'undefined') {
      _options = options.download[i];
    }
    FmpDownloader.checkExisting(fileFromServer);
  }

  methods.process = function(options, response) {
    console.log("FmpPreload options:", options, "response:", response);
    for(var i=0;i<response.data.results.length;i++) {
      var fileFromServer = response.data.results[i];
      methods.processFile(options, fileFromServer);
    }
  }
  return methods;
})
.factory('FmpDownloader', function($ionicPlatform, $cordovaFileTransfer,
                                   $cordovaFile, FmpConfig, $timeout,
                                   $rootScope, FmpUtils){
  var collection = {
        queue: [],
        runLock: false,
        downloading: {
          "progress":0,
          "locations": [{"basename":""}]
        }
      },
      methods = {
        collection: collection
      };
  methods.append = function(file) {
      console.log("FmpDownloader.append:", file);
      var found = false;
      for (var i=0;i<collection.queue.length;i++) {
        if (collection.queue.id == file.id) {
          found = true;
          break;
        }
      }
      if (!found) {
        collection.queue.push(file);
      }
      methods.run();
  };
  methods.run = function() {
    if (collection.runLock) {
      console.log("!FmpDownloader.run()");
      return;
    }
    console.log("FmpDownloader.run()");
    collection.runLock = true;
    methods.download();
  };

  methods.download = function() {
    if (collection.queue.length == 0) {
      collection.runLock = false;
      return;
    }
    var file = collection.queue.pop(),
        url = file["dl-url"],
        filename = file["filename"],
        tmpFile = file["tmpFile"],
        dst = file["dl-tmp"];
    console.log("FmpDownloader.download:", url, "=>", dst);

    collection.downloading = file;
    console.log("collection.downloading:", collection.downloading);

    $cordovaFileTransfer.download(url, dst)
                        .then(function(result) {
                          // Success!
                          console.log("methods.download success:", result);
                          methods.download();
                          $cordovaFile.moveFile(FmpConfig.cacheDir, tmpFile,
                                                FmpConfig.cacheDir, filename)
                                      .then(function (success) {
                                        console.log("moved:", tmpFile, "=>", filename,
                                                    "success:", success);
                                      }, function (error) {
                                        // error
                                        console.log("!moved:", tmpFile, "=>", filename,
                                                    "error:", error);
                                      });
                        }, function(err) {
                          // Error
                          console.log("methods.download error:", err);
                          console.log("error:", err);
                          methods.download();
                        }, function (progress) {
                            $timeout(function(){
                              var downloadProgress = Math.floor((progress.loaded / progress.total) * 100);
                              if (methods.collection.downloading.progress != downloadProgress) {
                                methods.collection.downloading.progress = downloadProgress;
                                console.log(url+" methods.download progress timeout:", collection.downloading.progress);
                                methods.progress = downloadProgress;
                              }
                              $rootScope.$broadcast("download-progress");
                            });
                        });
  }

  methods.checkExisting = function(file) {
    FmpUtils.addLocalData(file);
    $cordovaFile.checkFile(FmpConfig.cacheDir,
                           file.id+"."+file.ext)
                .then(function (success) {
                  // success
                  console.log("FmpDownloader.checkExisting success:", success, file);
                  // methods.download(fileFromServer, _options);
                  //console.log("TESTING APPENDING");
                  // FmpDownloader.append(file);
                }, function (error) {
                  // error
                  console.log("FmpDownloader $cordovaFile.checkFile error:", error, file);
                  if (error.code == 1) {
                    // NOT_FOUND_ERR
                    // methods.download(fileFromServer, _options);

                    methods.append(file);
                  }
                });
  }


  return methods;
})
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
      $rootScope.$broadcast("index-changed");
    }

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
})
.factory('FmpCache', function($ionicPlatform, FmpConfig){

  var collection = {},
      methods = {
        collection: collection
      };

  return methods;
})
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
  };

  $rootScope.$on("index-changed", methods.setMedia);
  return methods;

})
.factory('OldPlayer', function($http, $cordovaFileTransfer, $cordovaFile,
                               $ionicPlatform, $timeout){
  /****************************  ****/
  var collection = {
          url: 'http://192.168.1.117:5050',
          playlist: [],
          preload: [],
          preloadDict: {},
          idx:0,
          media: null,
          time_status: "",
          restored: false,
          initPreloadLocked: false,
          resumePosition: 0,
          remaining: -1000,
          uids: [],
          cacheDir: null,
          cacheDirEntries: [],
          preloadLock: false
      },
      methods = {
          collection: collection
      };



  methods.processCacheDir = function(entries) {
    console.log("methods.processCacheDir entries:", entries);
    collection.cacheDirEntries = entries;
    /*
      TODO:
        - loop through preload
        - loop through playlist
    */
  };

  methods.onError = function() {
      console.log("onError:", arguments);
  };

  methods.onComplete = function() {
    console.log("onComplete:", arguments);
  };

  methods.onStatusChange = function(playerStatus) {
    console.log("onStatusChange:", playerStatus);
  };



  methods.setIndex = function(idx) {
    console.log("methods.setIndex()");
    var src = null;
    if (typeof idx == 'undefined') {
        if (methods.isEmpty(collection.playlist)) {
          console.log("playlist is empty");
          return false;
        }
    }
    if (typeof collection.playlist[idx] == 'undefined') {
        console.log("collection.playlist["+idx+"] is undefined");
        return false;
    }
    src = collection.playlist[idx].filename;
    collection.media = new Media(src,
                                 methods.onComplete,
                                 methods.onError,
                                 methods.onStatusChange);

  }

  methods.play = function() {
    console.log("methods.play()", arguments);
    if (collection.media == null) {
      methods.setIndex();
      if (collection.media == null) {
          console.log("unable to set playlist index");
          methods.fetchPreload({
            "download": [{
                "success": methods.play
            }]
          });
          return;
      }
    }
    collection.media.play();
  };

  $ionicPlatform.ready(function() {
    // fetchPreload
    methods.play();
    methods.fetchPreload();

    // clean cache.
    collection.cacheDir = cordova.file.externalCacheDirectory;
    methods.listDir(collection.cacheDir, methods.processCacheDir);
  });

  return methods;
})
.factory('Chats', function() {
  // Might use a resource here that returns a JSON array

  // Some fake testing data
  var chats = [];

  return {
    all: function() {
      return chats;
    },
    remove: function(chat) {
      chats.splice(chats.indexOf(chat), 1);
    },
    get: function(chatId) {
      for (var i = 0; i < chats.length; i++) {
        if (chats[i].id === parseInt(chatId)) {
          return chats[i];
        }
      }
      return null;
    }
  };
});

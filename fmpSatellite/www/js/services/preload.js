starterServices
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
});
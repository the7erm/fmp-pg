fmpApp
.factory('FmpPreload', function(FmpConfig, $http, FmpUtils, FmpDownloader, $rootScope){

  var collection = {
        fetchLock: false,
        files: [],
      },
      methods = {
        collection: collection
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
    $rootScope.$broadcast("preload-changed");
  };

  methods.reset = function () {
    collection.files = [];
  }

  methods.load = function() {
    collection.files = [];
    if (typeof localStorage["preload"] == "undefined" ||
        !localStorage["preload"]) {
      return;
    }
    var files = JSON.parse(localStorage["preload"]);
    for (var i=0;i<files.length;i++) {
      var key = files[i];
      if (typeof localStorage[key] == "undefined") {
        // the file doesn't exist.
        continue;
      }
      var file = new FmpFile(key);
      collection.files.push(file);
    }
  };

  methods.save = function() {
    var files = [];
    for (var i=0;i<collection.files.length;i++) {
      var file = collection.files[i];
      file.save();
      files.push("file-"+file.file_id);
    }
    localStorage.preload = JSON.stringify(files);
  };

  if (typeof localStorage.preload != 'undefined') {
    methods.load();
  }


  return methods;
});
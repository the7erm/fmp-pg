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
    collection.files = JSON.parse(localStorage.preloadFiles);
  }

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

  methods.save = function() {
    localStorage.preloadFiles = JSON.stringify(collection.files);
  };

  return methods;
});
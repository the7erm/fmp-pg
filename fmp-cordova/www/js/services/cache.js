fmpApp
.factory('FmpCache', function(FmpConfig, FmpUtils){

  var collection = {},
      methods = {
        collection: collection
      };

  methods.process = function(fileEntries) {
    console.log("PROCESS CACHE FILES:", fileEntries);
    var filesToRemove = [];
    for (var i=0;i<fileEntries.length;i++) {
        var fileEntry = fileEntries[i],
            idx = collection.filenames.indexOf(fileEntry.nativeURL);
        if (idx == -1) {
            console.log("DELETE:", fileEntry.nativeURL);
            fileEntry.remove();
        }
    }
  };

  methods.error = function() {
    print("CACHE CHECK ERROR:", arguments);
  };

  methods.clean = function(playlist, preload) {
    console.log("CLEAN");
    if (!FmpConfig.cacheDir) {
        return;
    }
    var files = playlist.concat(preload);
    collection.filenames = [];
    for (var i=0;i<files.length;i++) {
        var file = files[i];
        if (file.fullFilename) {
            collection.filenames.push(file.fullFilename);
        }
    }
    FmpUtils.listDir(FmpConfig.cacheDir, methods.process, methods.error);

  }

  return methods;
});
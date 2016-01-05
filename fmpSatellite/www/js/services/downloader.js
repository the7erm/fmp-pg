starterServices
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
                                console.log(url+" methods.download progress:", collection.downloading.progress);
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
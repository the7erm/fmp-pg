fmpApp
.factory('FmpUtils', function(FmpConfig){
  var methods = {},
      logger = new Logger("FmpUtils", true);
  methods.listDir = function (path, successCb, errorCb){
    if (typeof successCb == 'undefined') {
      successCb = function(entries) {
        logger.log("FmpUtils.methods.listDir successCb:", entries);
      };
    }
    if (typeof errorCb == 'undefined') {
      errorCb = function(err) {
          logger.log("FmpUtils.methods.listDir errorCb:", err);
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

  methods.today = function() {
      var today = new Date(),
          year = today.getUTCFullYear(),
          month = methods.pad(today.getUTCMonth() + 1),
          day = methods.pad(today.getUTCDate());
      return year+"-"+month+"-"+day;
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
      logger.log("K:",k, "v:", obj[k]);
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
        filename = fileFromServer.id+".mp3",
        tmpFile = filename + ".tmp",
        dst = FmpConfig.cacheDir+tmpFile;
    fileFromServer['dl-url'] = url;
    fileFromServer['filename'] = filename;
    fileFromServer['tmpFile'] = tmpFile;
    fileFromServer['fullFilename'] = FmpConfig.cacheDir+filename;
    fileFromServer['dl-tmp'] = dst;
  }

  methods.validFile = function(file) {
    return true;
    // TODO: Make this unique to the device.
    var ignore = ['flv', 'wma', 'wmv'];

    if (ignore.indexOf(file.ext) != -1) {
      return false;
    }
    return true;
  }

  methods.sanitize = function(list) {
    /* Prepare a list of files, skip any that don't have a valid extension. */
    var newList = [];
    for (var i=0;i<list.length;i++) {
      var file = list[i];
      methods.addLocalData(file);
      if (!methods.validFile(file)) {
        logger.log("invalid extension:", file);
        continue;
      }
      newList.push(file);
    }
    return newList;
  };

  logger.log("Initialized");
  return methods;
});
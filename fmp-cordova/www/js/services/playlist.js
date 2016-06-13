fmpApp.factory('FmpPlaylist', function($rootScope, FmpUtils, FmpListeners,
                                       FmpSync, FmpPreload){
  var logger = new Logger("FmpPlaylist", false);
  var collection = {
        files: [],
        lastSave: 0,
        lastAction: 0,
        "sync": {},
        FmpSync: FmpSync,
        lastSyncTime: 0,
        organizeLock:false,
        saveLock: false,
        loaded: false
      },
      methods = {
        collection: collection
      };

    methods.load = function() {
      logger.log("load()");
      collection.files = [];
      if (typeof localStorage["playlist"] == "undefined" ||
          !localStorage["playlist"]) {
        collection.loaded = true;
        return;
      }
      var files = JSON.parse(localStorage["playlist"]),
          foundPlaying = false;
      for (var i=0;i<files.length;i++) {
        var key = files[i];
        if (typeof localStorage[key] == "undefined") {
          // the file doesn't exist.
          continue;
        }
        var file = new FmpFile(key);
        collection.files.push(file);
        if (file.playing == true) {
          file.play();
          foundPlaying = true;
        }
      }
      if (!foundPlaying && typeof collection.files[0] != "undefined") {
        collection.files[0].playing = true;
      }
      logger.log("loaded");
      collection.loaded = true;
    };

    methods.save = function() {
      if (collection.saveLock) {
        return;
      }
      collection.saveLock = true;
      var files = [];
      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i];
        file.save();
        files.push("file-"+file.file_id);
      }
      localStorage.playlist = JSON.stringify(files);
      collection.saveLock = false;
    };

    methods.incTrack = function(by) {
      if (typeof by == 'undefined') {
        by = 1;
      }
      if (!collection.files || collection.files.length == 0) {
        return;
      }
      var playingIdx = -1,
          prevIdx = -1,
          files = [];

      var atLeastOneWithoutError = false;

      // Build a list of files that are showing.
      for (var i=0;i<collection.files.length;i++) {
        var file = collection.files[i];
        if (typeof file.cued == "undefined" || !file.cued || file.playing) {
          if (!file.err) {
            atLeastOneWithoutError = true;
          }
          files.push(file);
          continue;
        }
        if (FmpListeners.collection.listener_user_ids.indexOf(file.cued.user_id) != -1) {
          files.push(file);
        }
      }

      if (files.length == 0) {
        console.log("error files.length == 0");
        return;
      }

      if (!atLeastOneWithoutError) {
        console.log("error !atLeastOneWithoutError");
        return;
      }

      for (var i=0;i<files.length;i++) {
        // Get the playing index, then increment & decrement the score
        // accordingly.
        var file = files[i];
        if (file.playing) {
          playingIdx = i;
          prevIdx = i;
          break;
        }
      }
      playingIdx = playingIdx + by;
      if (playingIdx < 0) {
        // The playing index is < 0 set it to the length of files.
        playingIdx = files.length - 1;
      }
      if (playingIdx >= files.length) {
        // the playing index is >= the files.length so we
        // loop back to the beginning.
        playingIdx = 0;
      }

      if (prevIdx != playingIdx && prevIdx != -1 &&
          typeof files[prevIdx] != 'undefined') {
            // The previous index exists, so set the playing to false
            var file = files[prevIdx];
            file.playing = false;
      }

      for (var i=0;i<files.length;i++) {
        if (i == playingIdx) {
          files[i].playing = true;
          files[i].play();
          break;
        }
      }
    }

    methods.next = function() {
      logger.log("PLAYLIST NEXT");

      if (FmpListeners.collection.listener_user_ids.length == 1) {
        var voted_to_skip = [];
        for (var i=0;i<window.player.file.spec.user_file_info.length;i++) {
            var ufi = window.player.file.spec.user_file_info[i];
            if (listener_user_ids.indexOf(ufi.user_id) != -1) {
                ufi.voted_to_skip = true;
                voted_to_skip.push(ufi.user_id);
                // This person didn't listen to the song.
                continue;
            }
            ufi.voted_to_skip = false;
        };
        window.player.file.voted_to_skip = voted_to_skip;
      }
      window.player.file.set_skipped_by_listeners(FmpListeners.collection.listener_user_ids);
      methods.incTrack(1);
    };

    methods.prev = function() {
      logger.log("PLAYLIST PREV");
      methods.incTrack(-1);
    };

    methods.getRandomInt = function (min, max) {
      return Math.floor(Math.random() * (max - min)) + min;
    }

    var getKeyValue = function(obj, key, defaultValue) {
      if (key.indexOf(".") != -1) {
          var parts = key.split("."),
              _key = parts.shift(),
              child_key = parts.join(".");
          if (typeof obj[_key] == "undefined") {
            return defaultValue;
          }
          return getKeyValue(obj[_key], child_key, defaultValue);
      }
      if (typeof obj[key] == "undefined") {
        return defaultValue;
      }
      return obj[key];
    };


    var collapsGroup = function(groupedList, groupSortDirection,
                                valueSortDirection, groupStyle) {
      var files = [],
          foundFile = true;

      $.each(groupedList, function(key, values) {
        // console.log("valueSortDirection: ", valueSortDirection, "values before sort:", values);
        if (valueSortDirection == 0) {
          // stolen from http://stackoverflow.com/a/18650169/2444609
          // This is a simple random and I love it.
          values.sort(function() {
            return .5 - Math.random();
          });
        } else {
          values.sort();
        }
        if (valueSortDirection == -1) {
          values.reverse();
        }
        // console.log("valueSortDirection: ", valueSortDirection, "values after sort:", values);
      });

      var keys = Object.keys(groupedList);
      // console.log("groupSortDirection: ", groupSortDirection, "keys before sort:", keys);
      if (groupSortDirection == 0) {
        // stolen from http://stackoverflow.com/a/18650169/2444609
        // This is a simple random and I love it.
        keys.sort(function() {
          return .5 - Math.random();
        });
      } else {
        keys.sort();
      }
      if (groupSortDirection == -1) {
        keys.reverse();
      }

      // console.log("groupSortDirection: ", groupSortDirection, "keys after sort:", keys);
      // console.log("groupedList:",groupedList);


      if (groupStyle == "stagger") {
        var foundFile = true;
        while(foundFile) {
          foundFile = false;
          $.each(keys, function(i, key){
            var values = groupedList[key];
            if (!values || values.length == 0) {
              return;
            }
            var file = values.shift();
            if (!file){
              return;
            }
            foundFile = true;
            files.push(file);
          });
        }
      } else {
        $.each(keys, function(i, key){
          var values = groupedList[key];
          if (!values || values.length == 0) {
            return;
          }
          while (values && values.length > 0) {
            var file = values.shift();
            if (!file){
              continue;
            }
            files.push(file);
          }
        });
      }


      return files;
    };

    var groupByKey = function(file_list, groupKeyRule, defaultValue,
                              returnGrouped) {
      var groupedList = {},
          alreadyAdded = [],
          trackBy = "",
          groupSortDirection = 1,
          valueSortDirection = 1,
          groupStyle = 0;

      if (typeof returnGrouped == "undefined") {
          returnGrouped = false;
      }

      if (groupKeyRule.indexOf(",") != -1) {
        var groups = groupKeyRule.split(","),
            groupRule = groups.shift(),
            groupedList = groupByKey(file_list, groupRule, defaultValue, true),
            remaingRules = groups.join(","),
            files_list = [],
            foundFile = true;
        // console.log("groupRule:", groupRule, "groupedList:", groupedList);
        $.each(groupedList['list'], function(key, values) {
          groupedList['list'][key] = groupByKey(values, remaingRules, defaultValue, false);
        });

        return collapsGroup(groupedList['list'],
                            groupedList['groupSortDirection'],
                            groupedList['valueSortDirection'],
                            groupedList['groupStyle']);
      }

      // Group by key has the format of:
      // <key to group by>|<key to track by>|<groupSortDirection>
      // groupSortDirection: 1 ascending, -1 descending, 0 random
      // valueSortDirection: 1 ascending, -1 descending, 0 random
      var cmds = groupKeyRule.split("|"),
          groupKey = "";

      if (cmds.length >= 1) {
        groupKey = cmds[0];
      }
      if (cmds.length >= 2) {
        trackBy = cmds[1];
      }
      if (cmds.length >= 3) {
        groupSortDirection =  parseInt(cmds[2]);
      }
      if (cmds.length >= 4) {
        valueSortDirection = parseInt(cmds[3]);
      }
      if (cmds.length >= 5) {
        groupStyle = cmds[4];
      }

      if ([0, 1, -1].indexOf(valueSortDirection) == -1) {
          valueSortDirection = 1;
      }

      if ([0, 1, -1].indexOf(groupSortDirection) == -1) {
          groupSortDirection = 1;
      }

      if (typeof defaultValue == "undefined") {
        defualt = "undefined";
      }
      $.each(file_list, function(i, file){
          var keyValue = getKeyValue(file, groupKey, defaultValue);
          if (typeof groupedList[keyValue] == "undefined") {
            groupedList[keyValue] = [];
          }
          if (trackBy) {
            var trackValue = getKeyValue(file, trackBy, "-failed-");
            if (alreadyAdded.indexOf(trackValue) != -1) {
              return;
            }
            alreadyAdded.push(trackValue);
          }
          groupedList[keyValue].push(file);
      });
      if (returnGrouped) {
          return {
            "list": groupedList,
            "valueSortDirection": valueSortDirection,
            "groupSortDirection": groupSortDirection,
            "groupStyle": groupStyle
          };
      }
      return collapsGroup(groupedList, groupSortDirection, valueSortDirection,
                          groupStyle);
    };

    methods.organize_random = function(sortRule) {
      if (collection.organizeLock) {
        return;
      }
      collection.organizeLock = true;
      if (typeof sortRule == "undefined" || !sortRule) {
        // Randomly sort by user id and stagger.
        sortRule = [
          "playing|id|-1|1", // playing first,
          "spec.cued.user_id|id|0|0|stagger"
        ];
      }
      if (sortRule instanceof Array) {
        sortRule = sortRule.join(",");
      }
      var files = collection.files.concat(FmpPreload.collection.files);
      collection.files = groupByKey(files, sortRule);
      var lowest = collection.files.length,
          highest = 0;
      for (var i=0;i<collection.files.length;i++) {
          var file = collection.files[i];
          if (file.showing) {
            if (i < lowest) {
              lowest = i;
            }
            if (i > highest) {
              highest = i;
            }
          }
      }
      for (var i=0;i<collection.files.length;i++) {
          if (i >= lowest && i <= highest) {
            collection.files[i].showing = true;
          }
      }
      collection.organizeLock = false;
    };

    methods.organize = function() {
      // Put played files first, then playing last out those, and stagger by user_id
      var rules = [
          "spec.played|id|-1|1",
          "playing|id|1|1",
          "spec.cued.user_id|id|1|1|stagger"
      ];
      methods.organize_random(rules);
    };

    methods.organize_by_plid = function() {
      // Put played first then files that were cued from search,
      // after that
      var rules = [
        "spec.played|id|-1|1", // played files first,
        "playing|id|1|1", // playing last,
        "spec.cued.user_id|id|1|1|stagger", // stagger by the user
        "spec.cued.from_search|id|-1|1", // cued from search next with `true`
                                         // values first
        "spec.cued.id"  // Last but not least order by the preload.id
      ];
      methods.organize_random(rules);
    };

    methods.deleteFile = function(file, deleteCb) {
        console.log("deleteFile");
        if (typeof file.spec != "undefined" &&
            typeof file.spec.keep != "undefined" &&
            file.spec.keep) {
            return;
        }

        if (typeof deleteCb == "undefined") {
          deleteCb = methods.deleteCb;
        }
        var idx = FmpUtils.indexOfFile(collection.files, file);
        console.log("idx:", idx);
        if (idx != -1) {
            var _file = collection.files[idx];
            collection.files.splice(idx,1);
            console.log("_file.delete");
            _file.delete(deleteCb);
        }
    }

    methods.deleteCb = function(file) {
      logger.log("deleteCb:", file);
      FmpSync.syncFile(file.spec);
    }

    methods.rate = function(ufi) {
        logger.log("rate:", ufi);
        for (var i=0;i<collection.files.length;i++) {
            var file = collection.files[i];
            if (file.file_id == ufi.file_id) {
                file.rate(ufi.user_id, ufi.rating, true);
                break;
            }
        }
    };

    methods.score = function (ufi) {
        logger.log("score:", ufi);
        for (var i=0;i<collection.files.length;i++) {
            var file = collection.files[i];
            if (file.file_id == ufi.file_id) {
              file.skipScore(ufi.user_id, ufi.skip_score, true);
              break;
            }
        }
    };

    methods.remove = function(file) {
      logger.log("remove:", file);
    };

    window.player.completeCb = function(file) {
      logger.log("PLAYLIST COMPLETED CB:", file.basename);
      window.player.file.completed(FmpListeners.collection.listener_user_ids);
      methods.incTrack(1);
    };
    window.player.errorCb = function(file) {
      console.error("PLAYLIST ERROR CB:", file.basename);
      methods.incTrack(1);
    };

    window.player.timeStatusCb = function(file) {
      // logger.log("window.player.timeStatusCb");
      // logger.log("file.duration:", file.duration, "file.position:", file.position);
      if (file.duration <= 0 || file.position <= 0) {
        // logger.log("return;");
        return;
      }
      var percent_played = (file.position / file.duration) * 100;
      file.spec.duration = file.duration;
      file.spec.position = file.position;
      file.mark_as_played(FmpListeners.collection.listener_user_ids, percent_played);
      file.spec.percent_played = percent_played;
      // logger.log("percent_played:", file.percent_played);
      collection.playingFile = file;
      $rootScope.$broadcast("time-status", file);
    }
    window.player.next = methods.next;
    window.player.prev = methods.prev;
    methods.load();
    return methods;
});
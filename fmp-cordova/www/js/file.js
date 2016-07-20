
window.objHandler = {
    dirty: false,
    ignore: [],
    get: function(target, name) {
        if (name != "dirty" && name != "ignore") {
            return name in target ? target[name] : undefined;
        }
        if (name == "ignore") {
            return this.ignore;
        }
        if (name == "dirty") {
            // console.log("get dirty:", target);
            if (this.dirty) {
                return true;
            }
            if (typeof target == "object") {
                if (target.dirty) {
                    return true;
                }
                for (k in target) {
                  if (typeof target[k] == "object" && target[k].dirty) {
                      return true;
                  }
                }
            }
            return this.dirty;
        }
        return undefined;
    },
    set: function(target, name, value) {
        if (name == "dirty") {
            this.dirty = value;
            if (typeof target == "object") {
                for (k in target) {
                    if (typeof target[k] == "object") {
                        target[k].dirty = value;
                    }
                }
            }
            return;
        }
        if (name == "ignore") {
            this.ignore = value;
            return;
        }
        if (angular.equals(target[name], value)) {
            return;
        }
        if (this.ignore.indexOf(name) == -1) {
            this.dirty = true;
        }
        var _type = typeof value;
        if (_type == "object") {
            // console.log("making proxy:", value);
            value = new Proxy(value, window.objHandler);
            value.dirty = true;
        }
        target[name] = value;
    }
};

window.transactionId = function() {
    return Math.random().toString(36).replace(/[^a-z0-9]+/g, '')+"-"+(Date.now() / 1000);
}

window.Logger = function(name, debug) {
    if (typeof debug == "undefined") {
        debug = false;
    }

    var thisLogger = this;
    thisLogger.name = name;
    thisLogger.debug = debug;

    thisLogger.log = function() {
        if (!thisLogger.debug) {
          return;
        }
        var args = [
          thisLogger.name+" -"
        ];
        for (var i=0;i<arguments.length;i++) {
          args.push(arguments[i]);
        }
        (function() {
          "use strict";
          console.log.apply(console, args);
        }());
    };

    thisLogger.error = function() {
        var args = [
          thisLogger.name+" -"
        ];
        for (var i=0;i<arguments.length;i++) {
          args.push(arguments[i]);
        }
        (function() {
          "use strict";
          console.error.apply(console, args);
        }());
    };
    thisLogger.log("initialized",name,"logger");
};

var listDir = function (path, successCb, errorCb){
    if (typeof successCb == 'undefined') {
      successCb = function(entries) {
        console.log("listDir successCb:", entries);
      };
    }
    if (typeof errorCb == 'undefined') {
      errorCb = function(err) {
          console.log("listDir errorCb:", err);
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

var proxyWriters = {};

var ProxyWriter = function(name) {
    var thisWriter = this;
    thisWriter.name = name;
    thisWriter.logger = new Logger("ProxyWriter - "+name, true);
    // angular.equals(purple, drank)

    thisWriter.write = function(value) {
        /*insert or replace into Book (ID, Name, TypeID, Level, Seen) values (
   (select ID from Book where Name = "SearchName"),
   "SearchName",
    5,
    6,
    (select Seen from Book where Name = "SearchName"));*/
        db.transaction('')
    };

}

var proxyWriter = function (name, value) {
    var writer = null;
    if (typeof proxyWriters[name] == "undefined") {
        proxyWriters[name] = new ProxyWriter(name);
    }
    writer = proxyWriters[name];
    writer.write(value);
}

var proxyReader = function(name, value) {

};

var proxyLogger = new Logger("proxyLogger", true);
/*
var localStorageProxy = new Proxy({}, {
    get: function(target, name) {
        if (!(name in target)) {
            return undefined;
        }
        return target[name];
    },
    set: function(target, name, value) {
        target[name] = value;
        proxyWriter(name, value);
    }
});
*/

var initalizeLocalStorageProxy = function(entries) {
    var patt = new RegExp("$.storage");
    for (var i=0;i<entries.length;i++) {
        var entry = entries[i];
        proxyLogger.log("entry:", entry);
        if (!patt.test(entry.name)) {
            proxyLogger.log("!process");
            continue;
        }

    }
};

var FmpFile = function (spec) {
    var thisFile = this;
    thisFile.dirty = false;
    thisFile.artist_cache = null;
    thisFile.title_cache = null;
    thisFile.downloading = false;
    thisFile.progress = 0;
    thisFile.dirname = cordova.file.externalDataDirectory;
    thisFile.exists = null;
    thisFile.$rootScope = null;
    thisFile.$timeout = null;
    thisFile.removeIfPlayed = false;

    var logger = new Logger("FmpFile", false);

    thisFile.load = function(key) {
        if (typeof localStorage[key] == "undefined" || !localStorage[key]) {
            thisFile.spec = {};
            return;
        }
        thisFile.spec = JSON.parse(localStorage[key]);
        if (typeof thisFile.spec.image != 'undefined') {
            // var img = thisFile.spec.image;
            delete thisFile.spec.image;
            thisFile.dirty = true;
            thisFile.save();
        }
        if (typeof thisFile.spec.image != 'undefined') {
            // var img = thisFile.spec.image;
            delete thisFile.spec.image;
            thisFile.dirty = true;
            thisFile.save();
        }
        if (typeof thisFile.spec.voted_to_skip == "undefined") {
            thisFile.spec.voted_to_skip = [];
        }

    };
    thisFile.save = function() {
        if (!thisFile.file_id) {
            return;
        }
        var key = "file-"+thisFile.file_id;
        if (typeof localStorage[key] != "undefined" &&
            !thisFile.dirty) {
            logger.log("!saved !dirty:", thisFile.basename);
            return;
        }
        if (typeof thisFile.spec.image != 'undefined') {
            // var img = thisFile.spec.image;
            delete thisFile.spec.image;
        }
        if (typeof thisFile.image != 'undefined') {
            // var img = thisFile.spec.image;
            delete thisFile.image;
        }
        if (typeof thisFile.spec.voted_to_skip == "undefined") {
            thisFile.spec.voted_to_skip = [];
        }
        $.each(thisFile.spec.user_file_info, function(idx, ufi){
            if (thisFile.spec.voted_to_skip.indexOf(ufi.user_id) != -1) {
                ufi.voted_to_skip = true;
            } else {
                ufi.voted_to_skip = false;
            }
        });
        // thisFile.spec["needsSync"] = true;
        // logger.log("saved dirty:", thisFile.basename);
        thisFile.spec.saved = thisFile.timestamp;
        localStorage[key] = JSON.stringify(thisFile.spec);
        thisFile.dirty = false;
    };

    thisFile.delete = function(deleteCb) {
        logger.debug = true;
        if (thisFile.spec.keep) {
            return;
        }
        logger.log("***** REMOVE FILE *****");
        window.resolveLocalFileSystemURL(
                thisFile.filename,
                function(fileEntry) {
                    fileEntry.remove(function(file){
                        logger.log("File removed!");
                        thisFile.spec.deleted = true;
                        thisFile.save();
                        localStorage["deleted-"+thisFile.id] = localStorage["file-"+thisFile.id];
                        delete localStorage["file-"+thisFile.id];
                        if (typeof deleteCb != "undefined") {
                            deleteCb(thisFile);
                        }
                    },function(error){
                        logger.log("error deleting the file " + error.code);

                    },function(){
                        logger.log("file does not exist");
                    });
                }, function(error){
                    logger.log("Couldn't resolve:", thisFile.filename,
                                "error:", error);
                }
        );
    };

    if (typeof spec == "string") {
        thisFile.spec = {};
        if (spec.indexOf("file-") == 0) {
            thisFile.load(spec);
        }
    } else {
        thisFile.spec = spec;
        if (typeof thisFile.spec.voted_to_skip == "undefined") {
            thisFile.spec.voted_to_skip = [];
        }
    }

    if (typeof thisFile.spec.image != "undefined") {
        delete thisFile.spec.image;
    }

    if (typeof thisFile.image != "undefined") {
        delete thisFile.image;
    }

    if(typeof thisFile.spec.played == 'undefined') {
        thisFile.spec.played = false;
    }
    if(typeof thisFile.spec.playing == 'undefined') {
        thisFile.spec.playing = false;
    }
    if(typeof thisFile.spec.playingState == 'undefined') {
        thisFile.spec.playingState = "";
    }
    if(typeof thisFile.spec.duration == 'undefined') {
        thisFile.spec.duration = -1;
    }
    if(typeof thisFile.spec.position == 'undefined') {
        thisFile.spec.position = -1;
    }
    if(typeof thisFile.spec.remaining == 'undefined') {
        thisFile.spec.remaining = -1;
    }
    thisFile.dlCompleteCallback = function() {};
    thisFile.dlFailCallback = function() {};

    thisFile.play = function() {
        window.player.play(thisFile);
    };
    thisFile.pause = function() {
        window.player.pause();
    };
    thisFile.get_YYYY_MM_DD = function() {
        var now = new Date(),
            YYYY = now.getUTCFullYear(),
            MM = now.getUTCMonth()+1,
            DD = now.getUTCDate();
        if (MM < 10) {
            MM = "0"+MM;
        }
        if (DD < 10) {
            DD = "0"+DD;
        }
        var YYYY_MM_DD = YYYY+"-"+MM+"-"+DD;
        return YYYY_MM_DD;
    };
    thisFile.get_id = function() {
        return thisFile.get_file_id();
    };
    thisFile.get_artist_or_title = function(specKey, side) {
        // -1 = left
        // 1 = right
        if (thisFile.spec[specKey] && thisFile.spec[specKey].length > 0) {
            var values = [],
                lowers = [];
            for (var i=0;i<thisFile.spec[specKey].length;i++) {
                var value = thisFile.spec[specKey][i],
                    lower = value.name.toLowerCase();
                if (value.name && lowers.indexOf(lower) == -1) {
                    values.push(value.name);
                    lowers.push(lower);
                }
            }
            if (values.length >= 1) {
                return values.join(" ,");
            }
        }
        var basename = thisFile.basename,
            idx = basename.indexOf("-"),
            value = "";
        if (idx != -1) {
            if (side == -1) {
                value = basename.substr(0, idx).trim();
            }
            if (side == 1) {
                value = basename.substr(idx+1).trim();
            }
            if (value) {
                return value;
            }
        }
        return basename;
    };
    thisFile.get_artist = function() {
        return thisFile.get_artist_or_title('artists', -1);
    };
    thisFile.get_title = function() {
        return thisFile.get_artist_or_title('titles', 1);
    };
    thisFile.get_artist_title = function() {
        var artist = thisFile.artist;
            title = thisFile.title;
        if (artist && title && artist == title) {
            return artist;
        }
        return artist+" - "+title;
    };
    thisFile.get_timestamp = function() {
        return Date.now() / 1000;
    };
    thisFile.get_basename = function() {
        if (typeof thisFile.spec.locations == 'undefined' || !thisFile.spec.locations) {
            return "";
        }
        for (var i=0;i<thisFile.spec.locations.length;i++) {
            var loc = thisFile.spec.locations[i];
            return loc.basename;
        }
        return "";
    };
    thisFile.get_ext = function() {
        var parts = thisFile.basename.split(".");
        if (!parts || parts.length == 0) {
            return "";
        }
        return parts[parts.length-1].toLowerCase();
    };
    thisFile.get_file_id = function() {
        if (thisFile.spec.id) {
            return parseInt(thisFile.spec.id);
        }
        return -1;
    };
    thisFile.get_filename = function() {
        var ext = thisFile.ext;
        if (!ext) {
            return thisFile.dirname+"unknown."+thisFile.ext;
        }
        return thisFile.dirname+thisFile.file_id+"."+thisFile.ext;
    };

    /*
        thisFile.playing = false;
        thisFile.played = false;
    */
    thisFile.toBool = function(value) {
        if (typeof value == "string") {
            value = value.toLowerCase();
        }
        if (typeof value == "undefined" || !value || value == "0" ||
            value == "off" || value == "false" || value == "n" ||
            value == "no" || value == "unchecked") {
            return false;
        }
        return true;
    };
    thisFile.set_spec_value = function(name, value, save) {
        if (thisFile.spec[name] == value) {
            return;
        }
        thisFile.spec["needsSync"] = true;
        thisFile.dirty = true;
        thisFile.spec.timestamp = thisFile.timestamp;
        thisFile.spec[name] = value;
        if (typeof save == "undefined") {
            // by default we always save.
            save = true;
        }
        if (save) {
            thisFile.save();
        }
    };

    thisFile.get_keep = function() {
        return thisFile.spec.keep;
    };
    thisFile.set_keep = function(value) {
        thisFile.set_spec_value("keep", thisFile.toBool(value));
    };
    thisFile.get_playing = function() {
        return thisFile.spec.playing;
    };
    thisFile.set_playing = function(value) {
        thisFile.set_spec_value("playing", thisFile.toBool(value));
    };
    thisFile.get_played = function() {
        return thisFile.spec.played;
    };
    thisFile.set_played = function(value) {
        thisFile.set_spec_value("played", thisFile.toBool(value));
    };
    thisFile.get_duration = function() {
        return thisFile.spec.duration;
    };
    thisFile.set_duration = function(value) {
        thisFile.set_spec_value("duration", value);
    };
    thisFile.get_position = function() {
        return thisFile.spec.position;
    };
    thisFile.set_position = function(value) {
        thisFile.set_spec_value("position", value);
    };
    thisFile.get_remaining = function() {
        return thisFile.spec.remaining;
    };
    thisFile.set_remaining = function(value) {
        thisFile.set_spec_value("remaining", value);
    };
    thisFile.get_playingState = function() {
        return thisFile.spec.playingState;
    };

    thisFile.set_playingState = function(value) {
        thisFile.set_spec_value("playingState", value);
    };

    thisFile.get_voted_to_skip = function() {
        return thisFile.spec.voted_to_skip;
    }

    thisFile.set_voted_to_skip = function(value) {
        thisFile.set_spec_value("voted_to_skip", value);
        $.each(thisFile.spec.user_file_info, function(idx, ufi){
            if (value.indexOf(ufi.user_id) != -1) {
                ufi.voted_to_skip = true;
            } else {
                ufi.voted_to_skip = false;
            }
        });
    }

    thisFile.setUserValue = function(name, user_id, value, forceSave) {
        user_id = parseInt(user_id);
        forceSave = thisFile.toBool(forceSave);
        if (name == 'rating' || name == 'skip_score') {
            value = parseInt(value);
            if (name == 'rating' && (value < 0 || value > 5)) {
                return;
            }
            if (name == 'skip_score' && (value < -15 || value > 15)) {
                return;
            }
        }
        if (name == 'voted_to_skip') {
            value = thisFile.toBool(value);
        }
        var dirty = false;
        for (var i=0;i<thisFile.spec.user_file_info.length;i++) {
            var ufi = thisFile.spec.user_file_info[i];
            if (ufi.user_id == user_id && ufi.file_id == thisFile.file_id &&
                ufi[name] != value) {
                ufi[name] = value;
                ufi.timestamp = thisFile.get_timestamp();
                thisFile.dirty = true;
                dirty = true;
                thisFile.calculateTrueScore(ufi);
                break;
            }
        }
        if (dirty || forceSave) {
            thisFile.dirty = true;
            thisFile.spec.needsSync = true;
            thisFile.save();
        }
    };
    thisFile.rate = function(user_id, rating, forceSave) {
        var file_id = parseInt(thisFile.spec.id),
            timestamp = thisFile.get_timestamp();

        user_id = parseInt(user_id);
        rating = parseInt(rating);
        if (rating < 0 || rating > 5) {
            return;
        }
        thisFile.setUserValue('rating', user_id, rating, forceSave);
    };
    thisFile.skipScore = function(user_id, score, forceSave) {
        var file_id = parseInt(thisFile.spec.id),
            timestamp = thisFile.get_timestamp();

        user_id = parseInt(user_id);
        score = parseInt(score);
        if (score < -15 || score > 15) {
            return;
        }
        thisFile.setUserValue('score', user_id, score, forceSave);
    };
    thisFile.calculateTrueScore = function(ufi) {
        var true_score = (
            (parseInt(ufi.rating) * 2 * 10) +
            (parseInt(ufi.skip_score) * 10)
        ) / 2;
        if (true_score > 125) {
            true_score = 125;
        }
        if (true_score < -25) {
            true_score = -25;
        }
        ufi.true_score = true_score;
    };

    thisFile.multiSetSkipScore = function(user_ids, by, voted_to_skip) {
        console.log("multiSetSkipScore:", user_ids, by, voted_to_skip);
        var file_id = parseInt(thisFile.spec.id),
            timestamp = thisFile.get_timestamp();
        for (var i=0;i<thisFile.spec.user_file_info.length;i++) {
            var ufi = thisFile.spec.user_file_info[i];
            if(user_ids.indexOf(ufi.user_id) != -1 && ufi.file_id == file_id) {
                if (typeof voted_to_skip != "undefined") {
                    ufi.voted_to_skip = voted_to_skip;
                }
                ufi.skip_score = parseInt(ufi.skip_score) + parseInt(by);
                ufi.timestamp = timestamp;
                thisFile.calculateTrueScore(ufi);
                thisFile.dirty = true;
            }
        }
    };
    thisFile.vote_to_skip = function(user_id, voted_to_skip) {
        var file_id = parseInt(thisFile.spec.id),
            timestamp = thisFile.get_timestamp();

        user_id = parseInt(user_id);
        if (typeof voted_to_skip == "string" &&
            ["0", "off", "false", "f"].indexOf(voted_to_skip.toLowerCase()) != -1) {
            voted_to_skip = false;
        }
        if (voted_to_skip) {
            voted_to_skip = true;
        } else {
            voted_to_skip = false;
        }
        if (typeof thisFile.spec.voted_to_skip == "undefined") {
            thisFile.spec.voted_to_skip = [];
        }
        console.log("vote_to_skip() user_id:", user_id, "voted_to_skip:", voted_to_skip);
        for (var i=0;i<thisFile.spec.user_file_info.length;i++) {
            var ufi = thisFile.spec.user_file_info[i];
            if (ufi.user_id != user_id) {
                continue;
            }
            ufi.voted_to_skip = voted_to_skip;
            ufi.timestamp = timestamp;
            thisFile.dirty = true;

            var idx = thisFile.spec.voted_to_skip.indexOf(ufi.user_id);
            if (ufi.voted_to_skip && idx == -1) {
                thisFile.spec.voted_to_skip.push(ufi.user_id);
            }

            if (!ufi.voted_to_skip && idx != -1) {
                thisFile.spec.voted_to_skip.splice(idx, 1);
            }
            break;
        }
        thisFile.save();
    };
    thisFile.inc_score = function(user_ids) {
        thisFile.multiSetSkipScore(user_ids, 1, false);
    };
    thisFile.deinc_score = function(user_ids) {
        thisFile.multiSetSkipScore(user_ids, -1, true);
    };
    thisFile.mark_as_played = function (listener_user_ids, percent_played, now) {
        /*
        logger.log("Mark as played NAME:",
                    "listener_user_ids:", listener_user_ids,
                    "percent_played:", percent_played,
                    "now:", now); */
        percent_played = parseFloat(percent_played);
        if (percent_played == parseFloat(thisFile.spec.percent_played)) {
            // logger.log("mlp return;");
            return;
        }
        if (typeof now == 'undefined') {
            now = thisFile.get_timestamp();
        }
        thisFile.spec["time_played"] = now;
        thisFile.spec["timestamp"] = now;
        thisFile.spec["now"] = now;
        thisFile.spec["percent_played"] = percent_played;
        thisFile.spec["needsSync"] = true;
        thisFile.spec['listener_user_ids'] = listener_user_ids;
        thisFile.spec["played"] = true;
        /*
            'user_ids': [],
                'file_id': <file_id>,
                'now': new Date().now(),
                'timestamp': new Date().now(),
                "action": "mark_as_played"
        */
        for (var i=0;i<thisFile.spec.user_file_info.length;i++) {
            var ufi = thisFile.spec.user_file_info[i];
            if (listener_user_ids.indexOf(ufi.user_id) != -1) {
                ufi.timestamp = now;
                ufi.time_played = now;
                ufi.percent_played = percent_played;
            }
        }
        thisFile.dirty = true;
        // logger.log("/mark_as_played");
    };
    thisFile.set_skipped_by_listeners = function(listener_user_ids) {
        console.log("thisFile.skipped_by_listeners called");
        var voted_to_skip_user_ids = [],
            didnt_vote_to_skip_user_ids = [];
        for (var i=0;i<thisFile.spec.user_file_info.length;i++) {
            var ufi = thisFile.spec.user_file_info[i];
            if (listener_user_ids.indexOf(ufi.user_id) == -1) {
                ufi.voted_to_skip = false;
                // This person didn't listen to the song.
                continue;
            }
            if (ufi.voted_to_skip) {
                voted_to_skip_user_ids.push(ufi.user_id);
            } else {
                didnt_vote_to_skip_user_ids.push(ufi.user_id);
            }
        };
        thisFile.multiSetSkipScore(voted_to_skip_user_ids, -1, true);
        thisFile.multiSetSkipScore(didnt_vote_to_skip_user_ids, 0, false);
    };
    thisFile.completed = function(listener_user_ids) {
        var voted_to_skip_user_ids = [],
            didnt_vote_to_skip_user_ids = [];
        for (var i=0;i<thisFile.spec.user_file_info.length;i++) {
            var ufi = thisFile.spec.user_file_info[i];
            if (listener_user_ids.indexOf(ufi.user_id) == -1) {
                // This person didn't listen to the song.
                continue;
            }
            if (ufi.voted_to_skip) {
                voted_to_skip_user_ids.push(ufi.user_id);
            } else {
                didnt_vote_to_skip_user_ids.push(ufi.user_id);
            }
        };

        thisFile.multiSetSkipScore(voted_to_skip_user_ids, -2, true);
        thisFile.multiSetSkipScore(didnt_vote_to_skip_user_ids, 1, false);
    };

    thisFile.error_playing = function() {
        // TODO
    };

    thisFile.download = function() {
        thisFile.downloading = 1;
        thisFile.progress = 0;
        thisFile.progressLock = false;
        // TODO Still need to make a downloading class/object that will
        // check.
        logger.log("DOWNLOAD:", thisFile.filename);
        logger.log("fmpHost:",window.fmpHost);
        if (!window.fmpHost) {
            return;
        }
        // download(self, file_id, convert=False, extract_audio=False)
        var fileTransfer = new FileTransfer(),
            source = encodeURI(window.fmpHost+"download?file_id="+thisFile.file_id),
            target = thisFile.filename+".tmp";

        fileTransfer.download(
            source,
            target,
            function(fileEntry) {
                logger.log("download complete: " + fileEntry.toURL());
                logger.log("fileEntry:", fileEntry);
                var newFileName = thisFile.file_id+"."+thisFile.ext;
                thisFile.progress = 100;
                // move the file to a new directory and rename it
                window.resolveLocalFileSystemURL(
                    thisFile.dirname,
                    function(dirEntry) {
                        // move the file to a new directory and rename it
                        fileEntry.moveTo(
                            dirEntry,
                            newFileName,
                            function(entry){
                                logger.log("New Path: ", entry);
                                thisFile.exists = true;
                                thisFile.progress = 100;
                                thisFile.dlCompleteCallback();
                            }, function(error){
                                logger.log("DIDN'T MOVE:",error.code);
                                thisFile.dlFailCallback();
                            }
                        );
                    }, function(error){
                        logger.log("Couldn't resolve:", thisFile.dirname,
                                    "error:", error);
                        thisFile.dlFailCallback();
                    }
            );

            },
            function(error) {
                logger.log("download error source " + error.source);
                logger.log("download error target " + error.target);
                logger.log("download error code" + error.code);
                thisFile.dlFailCallback();
            },
            false /*
            no options for the time being.
            ,
            {
                headers: {
                    "Authorization": "Basic dGVzdHVzZXJuYW1lOnRlc3RwYXNzd29yZA=="
                }
            } */
        );
        fileTransfer.onprogress = function(progressEvent) {
            // logger.log("onprogress:", progressEvent);
            if (progressEvent.lengthComputable) {
                // loadingStatus.setPercentage(progressEvent.loaded / progressEvent.total);
                var progress = Math.floor((progressEvent.loaded / progressEvent.total) * 100);
                if (!thisFile.progressLock) {
                    thisFile.progressLock = true;
                    if (progress != thisFile.progress && progress > thisFile.progress) {
                        thisFile.progress = progress;
                        logger.log("progress:", thisFile.progress, thisFile.basename);
                        try {
                            thisFile.$timeout(function(){
                                thisFile.progressLock = false;
                            });
                        } catch (e) {
                            logger.log("caught:", e);
                            thisFile.progressLock = false;
                        }
                    } else {
                        thisFile.progressLock = false;
                    }
                }
            } else {
                logger.log("incerment");
            }
        };
    };

    thisFile.check_existing = function() {
        logger.log("filename:", thisFile.filename);
        window.resolveLocalFileSystemURL(thisFile.filename,
            function(){
                thisFile.exists = true
            },
            function(){
                thisFile.exists = false;
                thisFile.download_if_not_exists();
            }
        );
    };
    thisFile.queue = function() {
        window.downloader.append(thisFile);
    };
    thisFile.download_if_not_exists = function() {
        if (thisFile.exists == null) {
            //Check for the file.
            window.resolveLocalFileSystemURL(thisFile.filename, function(){
                // thisFile.exists = true;
                thisFile.exists = true;
            }, thisFile.queue);
        } else if (!thisFile.exists) {
            thisFile.queue();
        }
    };
    thisFile.update = function(dataFromServer) {
        // TODO
        this.dirty = false;
    };
    var getterKeys = ["id", "file_id", "basename", "ext", "filename",  "artist",
                      "title", "timestamp", "YYYY_MM_DD", "artist_title"];
    for (var i=0;i<getterKeys.length;i++) {
        var key = getterKeys[i];
        Object.defineProperty(thisFile, key, {
          get: thisFile['get_'+key],
          set: function() { }
        });
        // logger.log("test getter", key, ":", thisFile[key]);
    };

    var getterSetterKeys = ["playing", "playing", "playingState", "duration",
                            "remaining", "position", "keep"];
    for (var i=0;i<getterSetterKeys.length;i++) {
        var key = getterSetterKeys[i];
        Object.defineProperty(thisFile, key, {
          get: thisFile['get_'+key],
          set: thisFile['set_'+key]
        });
        // logger.log("test getter", key, ":", thisFile[key]);
    };

    for (var k in thisFile.spec) {
        // This is a messed up hack.
        // It basically creates setters & getters based on thisFile.spec
        // logger.log("k:",k);
        var functionName = "get_"+k,
            ds = {};
        if (typeof thisFile[functionName] == "undefined" && typeof thisFile[k] == "undefined") {
            var funct = "thisFile['"+functionName+"'] = function () { return thisFile.spec['"+k+"']; }";
            var x = function(str){
              eval(str);
            }.call(thisFile, funct);
            ds["get"] = thisFile[functionName];
        }
        functionName = "set_"+k;
        if (typeof thisFile[functionName] == "undefined" && typeof thisFile[k] == "undefined") {
            var funct = "thisFile['"+functionName+"'] = function (value) { thisFile.spec['"+k+"'] = value;  thisFile.needsSync = true; thisFile.spec.needsSync = true; }";
            var x = function(str){
              eval(str);
            }.call(thisFile, funct);
            ds["set"] = thisFile[functionName];
        }
        if (typeof ds.set == "undefined" && typeof ds.get == "undefined") {
            continue;
        }
        Object.defineProperty(thisFile, k, ds);
        // logger.log("test getter", k, ":", thisFile[k]);
    }
    thisFile.check_existing();

};

var Downloader = function(){
    var thisDownloader = this;

    thisDownloader.queue = [];
    thisDownloader.downloading = null;
    var logger = new Logger("Downloader", false);

    thisDownloader.append = function(file) {
        if (thisDownloader.downloading && thisDownloader.downloading.id == file.id) {
            return;
        }
        var found = false;
        for (var i=0;i<thisDownloader.queue.length;i++) {
            var dlFile = thisDownloader.queue[i];
            if (dlFile.id == file.id) {
                found = true;
                break;
            }
        }
        if (!found) {
            logger.log("thisDownloader append:", file.basename);
            file.dlCompleteCallback = thisDownloader.onComplete;
            file.dlFailCallback = thisDownloader.onFail;
            thisDownloader.queue.push(file);
        }
        if (!thisDownloader.downloading || thisDownloader.downloading.progress == 100 ||
            thisDownloader.downloading.exists) {
            thisDownloader.downloading = null;
        }
        thisDownloader.run();
    };
    thisDownloader.onComplete = function() {
        thisDownloader.downloading = null;
        thisDownloader.run();
    };
    thisDownloader.onFail = function() {
        thisDownloader.downloading = null;
        thisDownloader.run();
    };
    thisDownloader.run = function() {
        if (thisDownloader.downloading || thisDownloader.queue.length == 0) {
            return;
        }
        var file = thisDownloader.queue.shift();
        logger.log("thisDownloader file:", file.basename);
        thisDownloader.downloading = file;
        setTimeout(thisDownloader.downloading.download, 1000);
    };
};

var Player = function() {
    var thisPlayer = this;
    thisPlayer.resume = true;
    thisPlayer.resuming = true;
    thisPlayer.media = null;
    thisPlayer.file = null;
    thisPlayer.realState = "STOPPED";
    thisPlayer.lastPosition = 0;
    thisPlayer.dragging = false;
    thisPlayer.mediaState = null;

    var logger = new Logger("Player", false);

    thisPlayer.completeCb = function(file) {
        logger.log("completeCb*********************");
    };

    thisPlayer.errorCb = function(file) {
        logger.log("errorCb*********************");
    };

    thisPlayer.timeStatusCb = function(file) {
        logger.log("timeStatusCb*********************");
    };

    thisPlayer.waitForRelease = function() {
        logger.log("waitForRelease");
        if (thisPlayer.state == "RELEASING") {
            setTimeout(thisPlayer.waitForRelease, 500);
            return;
        }
        logger.log("-waitForRelease");
        thisPlayer.state = "PLAYING";
        if (thisPlayer.resume) {
            thisPlayer.resume = false;
            if (typeof localStorage['player-position'] != "undefined") {
                thisPlayer.media.play();
                thisPlayer.media.seekTo(localStorage['player-position'] * 1000);
                logger.log("RESUME-waitForRelease");
                if (localStorage['player-state'] != "playing") {
                    thisPlayer.media.pause();
                } else {
                    thisPlayer.media.play();
                }
            }
            thisPlayer.resuming = false;
        } else {
            thisPlayer.media.play();
        }

        localStorage['player-playing-id'] = thisPlayer.file.id;
    };
    thisPlayer.prepare = function(file) {
        if (typeof file.spec.user_file_info != "undefined") {
            $.each(file.spec.user_file_info, function(idx, ufi){
                ufi.voted_to_skip = false;
            });
            file.spec.voted_to_skip = [];
            file.dirty = true;
            file.save();
        }
        if (thisPlayer.media) {
            logger.log("SETTING RELEASING 2");
            thisPlayer.state = "RELEASING";
            thisPlayer.media.stop();
            thisPlayer.media.release();
            /*
                Media.stop();
                - state changed fired
                - completed called
            */

        };
        if (thisPlayer.file) {
            thisPlayer.file.playing = false;
        }

        thisPlayer.file = file;
        thisPlayer.file.playing = true;
        thisPlayer.file.played = true;
        thisPlayer.file.skipped = false;
        thisPlayer.file.err = "";

        thisPlayer.media = new Media(thisPlayer.file.filename,
            function(){
                // mediaSuccess
                if (thisPlayer.state == "RELEASING") {
                    logger.log("COMPLETED CALLLED BUT RELEASING");
                    thisPlayer.state = "RELEASED";
                    return;
                } else {
                    thisPlayer.state = "STOPPED";
                    logger.log("completed");
                    thisPlayer.completeCb(thisPlayer.file);
                }
            },
            function(err){
                // mediaError
                console.error("failed:", err);
                if (err.code != 0) {
                    if (err.code == 1) {
                        thisPlayer.file.err = "MEDIA_ERR_ABORTED";
                    }
                    if (err.code == 2) {
                        thisPlayer.file.err = "MEDIA_ERR_NETWORK";
                    }
                    if (err.code == 3) {
                        thisPlayer.file.err = "MEDIA_ERR_DECODE";
                    }
                    if (err.code == 4) {
                        thisPlayer.file.err = "MEDIA_ERR_NONE_SUPPORTED";
                    }
                    thisPlayer.errorCb(thisPlayer.file);
                }
                thisPlayer.state = "STOPPED";
            },
            function(state){
                logger.log("state changed:", state);
                thisPlayer.mediaState = state;
                if (thisPlayer.state == "RELEASING") {
                    logger.log("STATE CHANGED BUT RELEASING");
                    return;
                }
                if (state == Media.MEDIA_RUNNING) {
                    thisPlayer.state = "PLAYING";
                    return;
                }
                if (state == Media.MEDIA_PAUSED) {
                    thisPlayer.state = "PAUSED";
                    return;
                }
                thisPlayer.state = "STOPPED";
            }
        );


        thisPlayer.waitForRelease();
    };

    thisPlayer.setMusicControls = function() {
        MusicControls.destroy(function(){}, function(){});
        var isPlaying = false;
        if (thisPlayer.realState == "PLAYING") {
            isPlaying = true;
        }

        MusicControls.create({
            track       : thisPlayer.file.get_title(),        // optional, default : ''
            artist      : thisPlayer.file.get_artist(),       // optional, default : ''
            cover       : 'img/logo.png',      // optional, default : nothing
            // cover can be a local path (use fullpath 'file:///storage/emulated/...', or only 'my_image.jpg' if my_image.jpg is in the www folder of your app)
            //           or a remote url ('http://...', 'https://...', 'ftp://...')
            isPlaying   : isPlaying,  // optional, default : true
            dismissable : false,                         // optional, default : false

            // hide previous/next/close buttons:
            hasPrev   : true,      // show previous button, optional, default: true
            hasNext   : true,      // show next button, optional, default: true
            hasClose  : false,       // show close button, optional, default: false

            // Android only, optional
            // text displayed in the status bar when the notification (and the ticker) are updated
            ticker    : 'Now playing '+thisPlayer.file.get_artist_title()
        }, function(){

        }, function() {

        });

        function events(action) {
            switch(action) {
                case 'music-controls-next':
                    // Do something
                    thisPlayer.next();
                    thisPlayer.setMusicControls();
                    break;
                case 'music-controls-previous':
                    // Do something
                    thisPlayer.prev();
                    thisPlayer.setMusicControls();
                    break;
                case 'music-controls-pause':
                    // Do something
                    thisPlayer.pause();
                    break;
                case 'music-controls-play':
                    // Do something
                    thisPlayer.pause();
                    break;
                case 'music-controls-destroy':
                    // Do something
                    break;

                // Headset events (Android only)
                case 'music-controls-media-button' :
                    // Do something
                    thisPlayer.pause();
                    break;
                case 'music-controls-headset-unplugged':
                    // Do something
                    break;
                case 'music-controls-headset-plugged':
                    // Do something
                    break;
                default:
                    break;
            }
        }

        // Register callback
        MusicControls.subscribe(events);

        // Start listening for events
        // The plugin will run the events function each time an event is fired
        MusicControls.listen();
    }

    thisPlayer.play = function(file) {
        if (typeof file == 'undefined' || !file ||
            (thisPlayer.file && thisPlayer.file.id == file.id)) {
            thisPlayer.pause();
            thisPlayer.setMusicControls();
            return;
        }
        thisPlayer.prepare(file);
        thisPlayer.setMusicControls();
    };
    thisPlayer.pause = function() {
        logger.log("PAUSE");

        if (!thisPlayer.media) {
            return;
        }

        if (thisPlayer.state != "PLAYING") {
            thisPlayer.media.play();
            thisPlayer.state = "PLAYING";
        } else {
            thisPlayer.media.pause();
            thisPlayer.state = "PAUSED";
        }
        thisPlayer.setMusicControls();
    };
    thisPlayer.get_state = function() {
        return thisPlayer.realState;
    };
    thisPlayer.set_state = function(value) {
        logger.log("set_state:", value);
        thisPlayer.realState = value;
        if (typeof thisPlayer.file != "undefined") {
            thisPlayer.file.playingState = value;
            thisPlayer.file.played = true;
            thisPlayer.file.save();
        }
    };

    thisPlayer.timeStatus = function() {
        if (!thisPlayer.media) {
            return;
        }
        if (!thisPlayer.file.spec.duration || thisPlayer.file.spec.duration < 0) {
            var duration = thisPlayer.media.getDuration();
            if (duration > 0) {
                logger.log("duration:", duration);
                thisPlayer.file.set_spec_value("duration", parseFloat(duration), false);
                thisPlayer.file.duration = parseFloat(duration);
            }
        }
        thisPlayer.media.getCurrentPosition(
            // success callback
            function (position) {
                if (thisPlayer.dragging) {
                    logger.log("thisPlayer.dragging return;");
                    return;
                }
                position = parseFloat(position);
                if (position <= -1 || position == thisPlayer.lastPosition) {
                    logger.log("position <= -1 || position == thisPlayer.lastPosition");
                    if(!thisPlayer.resume && !thisPlayer.resuming &&
                       thisPlayer.mediaState == Media.MEDIA_PAUSED) {
                        localStorage['player-state'] = "paused";
                    }
                    if (position != -1) {
                        thisPlayer.timeStatusCb(thisPlayer.file);
                    }
                    return;
                }
                if (!thisPlayer.resume) {
                    localStorage['player-position'] = position;
                }
                if(!thisPlayer.resume && !thisPlayer.resuming) {
                    if (thisPlayer.mediaState == Media.MEDIA_RUNNING) {
                        localStorage['player-state'] = "playing";
                    }
                    if (thisPlayer.mediaState == Media.MEDIA_PAUSED) {
                        localStorage['player-state'] = "paused";
                    }
                }
                thisPlayer.lastPosition = position;
                // logger.log("position:", position);
                var remaining = (thisPlayer.file.duration - position);
                thisPlayer.file.position = position;
                thisPlayer.file.remaining = remaining;

                thisPlayer.file.set_spec_value("remaining", remaining, false);
                thisPlayer.file.set_spec_value("position", position, false);
                thisPlayer.file.spec.needsSync = true;

                thisPlayer.timeStatusCb(thisPlayer.file);
                if (thisPlayer.file.dirty) {
                    thisPlayer.file.save();
                }
            },
            // error callback
            function (e) {
                thisPlayer.file.err = "Error getting pos=" + e;
            }
        );
    };
    thisPlayer.seekTo = function(ms) {
        logger.log("SEEK TO:", ms);
        // thisPlayer.media.seekTo(mil);
    };
    thisPlayer.onDragStart = function() {
        thisPlayer.dragging = true;
        logger.log("DRAG START:", arguments);
    };
    thisPlayer.onDragEnd = function() {
        thisPlayer.dragging = false;
        logger.log("DRAG END:", arguments);
        thisPlayer.media.seekTo(thisPlayer.file.position*1000);
    };
    thisPlayer.onDragChange = function() {
        logger.log("DRAG onDragChange:", arguments);
        // thisPlayer.media.seekTo(thisPlayer.file.position*1000);
    };
    setInterval(thisPlayer.timeStatus,1000);
    Object.defineProperty(thisPlayer, "state", {
      get: thisPlayer.get_state,
      set: thisPlayer.set_state
    });
}

window.downloader = new Downloader();
window.player = new Player();

window.onunload = function() {
    MusicControls.destroy(function(){}, function(){});
}
window.onbeforeunload = function() {
    MusicControls.destroy(function(){}, function(){});
}

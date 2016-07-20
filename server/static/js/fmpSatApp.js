var fmpApp = angular.module('fmpApp', ['mgcrea.ngStrap',
                                       'angularUtils.directives.dirPagination',
                                       'angular-growl']);

fmpApp.config(function(paginationTemplateProvider) {
    paginationTemplateProvider.setPath('/static/js/bower_components/angularUtils-pagination/dirPagination.tpl.html');
});

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



fmpApp.factory("FmpIpScanner", function($http, $rootScope){
  var logger = new Logger("FmpIpScanner", false);
  logger.log("Connection:", navigator.connection);
  var collection = {
        "knownHosts": [],
        "scanHosts": [],
        "url": "/",
        "socketUrl": "",
        "scanLock": false
      },
      methods = {
        collection: collection
      };

  methods.startScan = function() {
    $rootScope.$broadcast("server-found");
  }
  logger.log("FmpIpScanner: Initialized");
  return methods;
});

fmpApp.factory("ListenersService", function($http, $rootScope, FmpIpScanner){
    var listener_user_ids = [];
    try {
        listener_user_ids = JSON.parse(localStorage["listener_user_ids"]);
    } catch(e) {
        //console.log("ListenersService error:", e);
    }
    var collection = {
            users: [],
            listener_user_ids: listener_user_ids
        },
        methods = {
            collection:collection
        };
    methods.onServerFound = function() {
        $http({
          method: 'GET',
          url: FmpIpScanner.collection.url+"listeners"
        }).then(function(response) {
            collection.users = response.data;
            for (var i=0;i<collection.users.length;i++) {
                var user = collection.users[i];
                if (collection.listener_user_ids.indexOf(user['id']) == -1 ){
                    user.listening = false;
                } else {
                    user.listening = true;
                }
            }
        });
    }
    methods.setListening = function(user_id, listening) {

        var idx = collection.listener_user_ids.indexOf(user_id);
        if (listening && idx == -1) {
            collection.listener_user_ids.push(user_id);
        }
        if (!listening && idx != -1) {
            collection.listener_user_ids.splice(idx, 1);
        }
        collection.listener_user_ids.sort();
        for (var i=0;i<collection.users.length;i++) {
            var user = collection.users[i];
            if (user.id == user_id) {
                user.listening = listening;
            }
        }
        localStorage['listener_user_ids'] = JSON.stringify(collection.listener_user_ids);
        console.log("setListening:", localStorage['listener_user_ids']);
        $rootScope.$broadcast("listeners-changed");
    }
    $rootScope.$on("server-found", methods.onServerFound);

    return methods
});

fmpApp.factory("Utils", function(){
    var methods = {
        inList: function(list, item) {
            if (!list || !item) {
                return false;
            }
            return methods.idInList(list, item.id);
        },
        idInList: function(list, id){
            if (!list || !id) {
                return false;
            }
            var result = false;
            for (var i=0;i<list.length;i++) {
                if (id == list[i].id) {
                    result = true;
                    break;
                }
            }
            return result;
        },
        getIdIndex: function(list, id, last) {
            var idx = -1;
            if (!list || !id || list.length == 0) {
                return idx;
            }
            if (typeof last == "undefined") {
                last = true;
            }
            for(var i=0;i<list.length;i++) {
                if (list[i].id == id) {
                    idx = i;
                    if (!last) {
                        break;
                    }
                }
            }
            return idx;
        },
        isVideo: function(basename) {
            var rx = /\.(mp4|webm|ogv|3gpp|mkv)$/i;
            return rx.test(basename);
        }
    };
    return methods;
});

fmpApp.factory("Preload", function($http, $rootScope, ListenersService,
                                   FmpIpScanner, Utils, $timeout){
    var collection = {
            "preload": [],
            "minimum": 5,
            "promise": false
        },
        methods = {
            "collection": collection
        };

    methods.getNewPreload = function() {
        if (collection.promise) {
            $timeout.cancel(collection.promise);
        }
        collection.promise = $timeout(methods.clearPreload, 1000, true);
    };
    methods.clearPreload = function() {
        collection.preload = [];
        methods.getPreload();
    };
    methods.getPreload = function() {
        if (collection.locked) {
            return;
        }
        collection.locked = true;
        collection.promise = false;
        var files = [],
            history = methods.PlaylistService.collection.history,
            preload = collection.preload;
        if (preload && preload.length > 0) {
            $.each(preload, function(idx, item){
                if (Utils.inList(history, item)) {
                    collection.preload.splice(idx, 1);
                }
            });
        }
        var numberOfListeners = ListenersService.collection.listener_user_ids.length;
        if(!numberOfListeners) {
            numberOfListeners = 1;
        }
        if (collection.preload && collection.preload.length > collection.minimum) {
            console.log("collection.preload.length > "+collection.minimum);
            collection.locked = false;
            return;
        }
        var prefetchNum = numberOfListeners * 3,
            secondaryPrefetchNum = prefetchNum;

        if (prefetchNum < collection.minimum) {
            prefetchNum = collection.minimum * 2;
            secondaryPrefetchNum = prefetchNum;
        }

        var postData = {
            user_ids: ListenersService.collection.listener_user_ids,
            primary_user_id: ListenersService.collection.listener_user_ids[0],
            secondary_user_ids: ListenersService.collection.listener_user_ids,
            prefetchNum: prefetchNum,
            secondaryPrefetchNum: secondaryPrefetchNum,
            include_admins: false,
            files: collection.preload
        };
        $http({
          "method": 'POST',
          "url": FmpIpScanner.collection.url+"preloadSync",
          "headers": {
            "Content-type": "application/json"
          },
          "data": postData
        }).then(function(response) {
            var preload = response.data.preload;
            for (var i=0;i<preload.length;i++) {
                var item = preload[i],
                    found = false;
                if (methods.PlaylistService) {
                    found = Utils.inList(
                        methods.PlaylistService.collection.history, item);
                }
                if (!found) {
                    found = Utils.inList(collection.preload.history, item);
                }
                if (found) {
                    continue;
                }
                collection.preload.push(item);
            }
            // collection.preload = collection.preload.concat(response.data.preload);
            console.log("collection.preload:", collection.preload);
            collection.locked = false;
        }, function(){
            collection.locked = false;
        });
    };
    $rootScope.$on("server-found", methods.getPreload);
    $rootScope.$on("listeners-changed", methods.getNewPreload);
    return methods;
});

fmpApp.factory("PlaylistService", function($http, $rootScope, ListenersService,
                                           FmpIpScanner, Utils,
                                           Preload){
    var collection = {
            "history": []
        },
        methods = {
            "collection": collection
        };
    Preload.PlaylistService = methods;
    methods.getHistory = function() {
        if (collection.history && collection.history.length > 0) {
            return;
        }
        var postData = {
            user_ids: ListenersService.collection.listener_user_ids,
            limit: 1
        };
        $http({
          "method": 'POST',
          "url": FmpIpScanner.collection.url+"user_history",
          "headers": {
            "Content-type": "application/json"
          },
          "data": postData
        }).then(function(response) {
            var history = response.data;
            $.each(history, function(k, item){
                if (!Utils.inList(collection.history, item)) {
                    collection.history.unshift(item);
                }
            });
            console.log("collection.history:", collection.history);
            $rootScope.$broadcast("playlist-loaded");
        });
    };

    methods.moveToHistory = function(id) {
        var idInList = Utils.idInList(collection.history, id);
        for(var i=0;i<Preload.collection.preload.length;i++) {
            var item = Preload.collection.preload[i];
            if (item.id == id) {
                if (!idInList) {
                    collection.history.push(item);
                }
                Preload.collection.preload.splice(i, 1);
                Preload.getPreload();
            }
        }
    }

    methods.markAsPlayed = function(id, percent_played, force_sync){
        if (typeof force_sync == "undefined") {
            force_sync = false;
        }
        // console.log("markAsPlayed", id, percent_played);
        if (isNaN(percent_played)) {
            return;
        }
        var int_percent_played = parseInt(percent_played);
        if (collection.playingId == id &&
            collection.int_percent_played == int_percent_played &&
            !force_sync) {
            return;
        }

        collection.playingId = id;
        collection.int_percent_played = int_percent_played;

        var params = {
            "user_ids": ListenersService.collection.listener_user_ids.join(","),
            "percent_played": percent_played,
            "file_id": id,
            "set_playing": true,
            "force_sync": force_sync
        };
        $http({
          "method": 'GET',
          "url": FmpIpScanner.collection.url+"mark_as_played",
          "params": params
        }).then(function(response) {
            // console.log("response.data:", response);
        });
    };

    $rootScope.$on("server-found", methods.getHistory);
    $rootScope.$on("listeners-changed", methods.getHistory);
    return methods;
});


fmpApp.factory("PlayerService", function(PlaylistService,
                                         FmpIpScanner,
                                         $rootScope,
                                         $interval,
                                         Preload,
                                         $http,
                                         Utils,
                                         SearchService,
                                         growl){
    var collection = {
            "audio": document.createElement("audio"),
            "video": document.createElement("video"),
            "initialized": false,
            "playingId": null
        },
        methods = {
            "collection": collection
        };

    collection.media = collection.audio;

    methods.onended = function(){
        console.log("onended");
        var idx = methods.getPlayingIndex();
        if (idx == -1) {
            methods.setIndex(0);
            return;
        }
        var file = PlaylistService.collection.history[idx];
        for (var i=0;i<file.user_file_info.length;i++) {
            var ufi = file.user_file_info[i];
            console.log("inc score", ufi)
            methods.thumb(file, ufi.user.id, +1);
        }
        methods.setIndex(idx+1);
    };
    Preload.PlayerService = methods;
    collection.audio.setAttribute("preload", "auto");
    collection.video.setAttribute("preload", "auto");
    collection.audio.controls = true;
    collection.video.controls = true;
    collection.video.id = "video-player-element";
    collection.audio.style="width:100%";

    collection.audio.onerror = function() {
         alert("Error! Something went wrong");
    };
    collection.video.onerror = function() {
        try {
            var idx = methods.getPlayingIndex(),
                basename = PlaylistService.collection.history[idx].locations[0].basename;
                basename = basename.replace("<", "&lt;");
                basename = basename.replace(">", "&gt;");
                growl.error("Error! PLAYING VIDEO falling back to audio for:" +
                            "<code>" + basename + "</code>",
                            {ttl: -1});
        } catch (e) {
            alert("Error! PLAYING VIDEO falling back to audio");
        }
        methods.hideVideo();
        collection.media = collection.audio;
        collection.media.play();
    };
    collection.audio.onended = methods.onended;
    collection.video.onended = methods.onended;

    document.getElementById("audio-player").appendChild(collection.audio);
    document.getElementById("video-player").appendChild(collection.video);
    $("#video-player").resizable({
        handles: 'w, s, sw, n, nw, e, ne, se',
        aspectRatio: 16 / 9
    });

    methods.clearSrc = function() {
        collection.audio.src = "";
        collection.video.src = "";
    };

    window.onunload = function() {
        var keys = ['abort', 'canplay', 'canplaythrough', 'durationchange',
                    'emptied', 'ended', 'error', 'loadeddata',
                    'loadedmetadata', 'loadstart', 'pause',
                    'play', 'playing', 'progress', 'ratechange', 'seeked',
                    'seeking', 'stalled', 'suspend', 'timeupdate',
                    'volumechange', 'waiting'],
            noop = function(){},
            loopEls = function(els) {
                if (!els) {
                    return;
                }
                for (var i=0;i<els.length;i++) {
                    var el = els[i];
                    for (var j=0;j<keys.length;j++) {
                        var k = keys[j];
                        el["on"+k] = noop;
                    }
                    els[i].src = "";
                }
            };

        loopEls(document.getElementsByTagName("audio"));
        loopEls(document.getElementsByTagName("video"));
    };

    methods.initPlayer = function() {
        if (collection.initialized) {
            return;
        }
        collection.initialized = true;
        var playingId = localStorage['playingId'],
            currentTime = localStorage['currentTime'],
            paused = localStorage['paused'],
            history = PlaylistService.collection.history,
            idx = 0;
        if (playingId && !isNaN(playingId) &&
            Utils.idInList(history, playingId)) {
                var idx = Utils.getIdIndex(history, playingId);
                if (idx == -1) {
                    idx = 0;
                }
        }
        methods.setPlayingData(history[idx].id);
        methods.play();
        if (collection.playingId == playingId && !isNaN(currentTime)) {
            collection.media.currentTime = currentTime;
        }
        if (paused && paused != "0") {
            methods.pause();
        }
    };

    methods.showVideo = function() {
        $("#video-player").show();
        $("#audio-player").hide();
    };
    methods.hideAudio = methods.showVideo;

    methods.showAudio = function() {
        $("#video-player").hide();
        $("#audio-player").show();
    }
    methods.hideVideo = methods.showAudio;

    methods.setVideoSrc = function(id) {
        methods.showVideo();
        collection.video.src = (
            FmpIpScanner.collection.url+"stream?file_id="+id);
        collection.media = collection.video;
    }
    methods.setPlayingData = function(id) {
        if (!id) {
            return;
        }
        collection.audio.src = (
            FmpIpScanner.collection.url+"download?file_id="+id+"&convert_to=.mp3");
        var idx = Utils.getIdIndex(PlaylistService.collection.history, id);
        collection.media = collection.audio;
        if (idx != -1) {
            var item = PlaylistService.collection.history[idx];
            if (Utils.isVideo(item.locations[0].basename)) {
                methods.setVideoSrc(id);
            } else {
                methods.hideVideo();
            }
        } else {
            methods.showAudio();
        }
        collection.playingId = id;
    }

    methods.play = function() {
        if (!collection.playingId) {
            Preload.getPreload();
            methods.playId(Preload.collection.preload[0].id);
        } else {
            collection.media.play();
        }
    };
    methods.playId = function(id) {
        PlaylistService.moveToHistory(id);
        methods.setPlayingData(id);
        collection.media.play();
    };
    methods.playItem = function(item) {
        if (!Utils.inList(PlaylistService.collection.history, item)) {
            console.log("ADDED TO PLAYLIST");
            PlaylistService.collection.history.push(item);
        }
        methods.playId(item.id);
    };
    methods.pause = function() {
        methods.updateTime(0, true);
        collection.media.pause();
    };

    methods.getIdIndex = function(id) {
        return Utils.getIdIndex(PlaylistService.collection.history, id);
    };

    methods.getPlayingIndex = function() {
        return methods.getIdIndex(collection.playingId);
    };

    methods.next = function() {
        var idx = methods.getPlayingIndex();
        if (idx == -1) {
            methods.setIndex(0);
            return;
        }
        var file = PlaylistService.collection.history[idx];
        for (var i=0;i<file.user_file_info.length;i++) {
            var ufi = file.user_file_info[i];
            console.log("de inc score", ufi)
            methods.thumb(file, ufi.user.id, -1);
        }
        methods.setIndex(idx+1);
    };
    methods.getFileFromPreload = function() {
        if (!Preload.collection.preload ||
            Preload.collection.preload.length < 10) {
            Preload.getPreload();
            if (!Preload.collection.preload ||
                Preload.collection.preload.length == 0) {
                return null;
            }
        }
        return Preload.collection.preload[0];
    };
    methods.setIndex = function(idx) {
        // The idx is >= the playlist or it's -1
        var file = null,
            history = PlaylistService.collection.history;

        if (idx <= -1 && history && history.length > 0) {
            idx = history.length - 1;
        }
        if (!file && idx >= history.length) {
            file = methods.getFileFromPreload();
            if (!file && history && history.length > 0) {
                file = history[0];
            }
        } else {
            file = history[idx];
        }
        if (!file) {
            return;
        }
        collection.media.pause();
        methods.playId(file.id);
    }
    methods.prev = function() {
        var idx = methods.getPlayingIndex();
        methods.setIndex(idx-1);
    };
    methods.updateTime = function(cnt, force_sync) {
        // console.log("updateTime:", cnt, force_sync);
        if (typeof force_sync == "undefined") {
            force_sync = false;
        }
        if (!collection.media.src) {
            return;
        }
        collection.currentTime = collection.media.currentTime;
        collection.paused = collection.media.paused;
        if (!collection.paused) {
            var percent_played = (
                collection.currentTime / collection.media.duration) * 100;
            localStorage['playingId'] = collection.playingId;
            localStorage['percent_played'] = percent_played;
            localStorage['currentTime'] = collection.currentTime;
            localStorage['paused'] = 0;
            PlaylistService.markAsPlayed(collection.playingId, percent_played,
                                         force_sync);
        } else {
            localStorage['paused'] = 1;
        }
    };
    methods.updateLists = function(item) {
        var idx = Utils.getIdIndex(PlaylistService.collection.history, item.id);
        if (idx != -1) {
            PlaylistService.collection.history[idx].user_file_info = item.user_file_info;
        }
        idx = Utils.getIdIndex(Preload.collection.preload, item.id);
        if (idx != -1) {
            Preload.collection.preload[idx].user_file_info = item.user_file_info;
        }
        SearchService.updateLists(item);
    }
    methods.updateUserFileInfo = function(fileId, item, ufi, userId,
                                          ufiKey, route) {
        var params = {
            "user_id": userId,
            "file_id": fileId
        };
        params[ufiKey] = ufi[ufiKey];
        $http({
          "method": 'GET',
          "url": FmpIpScanner.collection.url+route,
          "params": params
        }).then(function(response) {
            console.log("response.data:", response.data);
            if (response.data) {
                ufi['true_score'] = response.data.true_score;
                methods.updateLists(item);
            }
        });
    };
    methods.rate = function(item, userId, rating) {
        var fileId = item.id;
        console.log("rate:", fileId, userId, rating);
        for (var j=0;j<item.user_file_info.length;j++){
            var ufi = item.user_file_info[j];
            if (ufi['user'].id == userId) {
                ufi['rating'] = rating;
                var x = methods.updateUserFileInfo.bind(
                    {}, fileId, item, ufi, userId, "rating", "rate");
                x();
            }
        }
    };
    methods.thumb = function(item, userId, direction) {
        var fileId = item.id;
        console.log("thumb:", fileId, userId, direction);
        for (var j=0;j<item.user_file_info.length;j++){
            var ufi = item.user_file_info[j];
            if (ufi['user'].id == userId) {
                ufi['skip_score'] = parseInt(ufi['skip_score']) + parseInt(direction);
                var x = methods.updateUserFileInfo.bind(
                    {}, fileId, item, ufi, userId, "skip_score", "set_score");
                x();
            }
        }
    }
    $interval(methods.updateTime, 1000);
    $rootScope.$on("playlist-loaded", methods.initPlayer);
    return methods;
});
fmpApp.factory("SearchService", function(ListenersService, $http,
                                         FmpIpScanner,
                                         $timeout,
                                         Utils){
    var collection = {
            results: {},
            searchTerm: "",
            expireTimes: {},
            start:0,
            limit:3,
            totals: {},
            promise: false,
            mostResentQuery: "",
            currentPage: 1,
            currentTotal: 0,
            locks: {}
        },
        methods = {
            collection: collection
        };

    methods.query = function() {
        var start = collection.start,
            limit = collection.limit;
        if (typeof collection.totals[collection.searchTerm] == "undefined") {
            start = 0;
            limit = collection.limit;
            collection.start = 0;
        } else if (start > collection.totals[collection.searchTerm]) {
            start = collection.totals[collection.searchTerm] - limit;
        }
        if (start < 0) {
            start = 0;
            collection.start = 0;
        }
        var uri = (
            "/search/?q="+encodeURIComponent(collection.searchTerm)+
            "&s="+start+
            "&l="+limit+
            "&user_ids="+ListenersService.collection.listener_user_ids.join(","));
        collection.mostResentQuery = uri;
        return uri;
    }

    methods.isLocked = function(query) {
        if(typeof collection.locks[query] == 'undefined') {
            return false;
        }
        // console.log("locked:", query, collection.locks[query]);
        return collection.locks[query];
    };

    methods.lock = function(query) {
        collection.locks[query] = true;
        // console.log("lock:", query);
    };

    methods.unlock = function(query) {
        collection.locks[query] = false;
        // console.log("unlock:", query);
        delete collection.locks[query];
    }

    methods.setCurrentPage = function() {
        collection.currentPage = (collection.start / collection.limit) + 1;
    }

    methods.search = function() {
        if (methods.isLocked("search")) {
            methods.timeoutSearch();
            return;
        }
        methods.lock("search");
        var query = methods.query();
        if (collection.promise) {
            $timeout.cancel(collection.promise);
        }
        collection.promise = false;
        collection.searchQuery = query;
        if (typeof collection.results[query] == "undefined") {
            collection.results[query] = [];
        }
        if (typeof collection.expireTimes[query] != "undefined" &&
            collection.expireTimes[query] > Date.now()) {
            console.log("cached:", query);
            methods.unlock("search");
            methods.prefetch();
            return;
        }
        if (methods.isLocked(query)) {
            methods.unlock("search");
            methods.prefetch();
            return;
        }
        methods.lock(query);
        $http({
          "method": 'GET',
          "url": query
        }).then(function(response) {
            collection.results[query] = response.data.results;
            collection.totals[collection.searchTerm] = response.data.total;
            // expire in a few minutes
            collection.expireTimes[query] = Date.now() + (1000 * 60 * 5);
            methods.setCurrentPage();
            methods.unlock(query);
            methods.unlock("search");
            methods.prefetch();
        }, function(){
            methods.unlock("search");
            methods.unlock(query);
        });
    };
    methods.pageChanged = function(newPageNumber) {
        collection.currentPage = parseInt(newPageNumber);
        collection.start = (collection.limit * (newPageNumber - 1));
        methods.search();
    };
    methods.doPrefetch = function(thisStart, multiplier) {
        console.log("prefetch collection.start:", collection.start,
                    "thisStart:", thisStart, "multiplier:", multiplier);
        var collectionStart = collection.start;
            collection.start = thisStart;
            var query = methods.query();
            collection.start = collectionStart;
            if (typeof collection.expireTimes[query] != "undefined" &&
                collection.expireTimes[query] > Date.now()) {
                methods.unlock("prefetch");
                methods.prefetch(multiplier+1);
                return;
            }
            if (methods.isLocked(query)) {
                methods.unlock("prefetch");
                methods.prefetch(multiplier+1);
                return;
            }
            methods.lock(query);
            console.log("prefetch:", query);
            $http({
              "method": 'GET',
              "url": query
            }).then(function(response) {
                methods.unlock("prefetch");
                collection.results[query] = response.data.results;
                collection.totals[collection.searchTerm] = response.data.total;

                // expire in a few minutes
                collection.expireTimes[query] = Date.now() + (1000 * 60 * 5);
                methods.unlock(query);
                methods.prefetch(multiplier+1);
            }, function(){
                methods.unlock("prefetch");
                methods.unlock(query);
            });
    };
    methods.prefetch = function(multiplier) {
        var maxPages = 10;
        if (isNaN(multiplier)) {
            multiplier = 1;
        }
        if (multiplier < 0) {
            return;
        }
        if (methods.isLocked("prefetch")) {
            return;
        }
        var numberOfPages = 7,
            halfWay = Math.floor(numberOfPages * 0.5),
            start = collection.start || 0,
            limit = collection.limit,
            _multi = multiplier - halfWay,
            subtract = _multi * limit,
            thisStart = start + subtract,
            total = collection.totals[collection.searchTerm],
            halfWayThroughFirstGroup = (limit * halfWay),
            lastGroupStartPage = (total - (limit * (numberOfPages)));

        console.log("871 thisStart:", thisStart,
                    "start:", start,
                    "collection.start:", collection.start,
                    "multiplier:", multiplier,
                    "subtract:", subtract);

        if (lastGroupStartPage < 0) {
            lastGroupStartPage = total;
        }

        console.log("total:", total, "lastGroupStartPage:", lastGroupStartPage);

        methods.lock("prefetch");
        if (multiplier > numberOfPages) {
            // doPrefetch = function(thisStart, multiplier);
            if (multiplier >= maxPages) {
                methods.unlock("prefetch");
                return;
            }
            thisStart = start - (maxPages * limit);
            if (thisStart > 0) {
                methods.doPrefetch(thisStart, -99);
            }
            thisStart = start + (maxPages * limit);
            if (thisStart <= total) {
                methods.doPrefetch(thisStart, -99);
            }
            methods.unlock("prefetch");
            return;
        }

        if (start >= lastGroupStartPage) {
            // The start is in the last group of pages, or it's halfway
            // through the first group.
            subtract = multiplier * limit;
            thisStart = start - subtract;
            console.log("LAST GROUP");
        }
        if (start <= halfWayThroughFirstGroup) {
            var numToAdd = multiplier * limit;
            thisStart = start + numToAdd;
            console.log("FIRST GROUP");
        }

        if (thisStart < 0) {
            methods.unlock("prefetch");
            methods.prefetch(multiplier+1);
            return;
        }

        if (thisStart <= total) {
            methods.doPrefetch(thisStart, multiplier);
        } else {
            console.log("thisStart > total", thisStart, ">", total);
            methods.unlock("prefetch");
        }
    }
    methods.updateLists = function(item) {
        var now = Date.now();
        $.each(collection.results, function(query, results){
            collection.expireTimes[query] = now;
        });
        if (!collection.mostResentQuery) {
            return;
        }
        var results = collection.results[collection.mostResentQuery]
        var idx = Utils.getIdIndex(results, item.id);
        if (idx != -1) {
            results[idx].user_file_info = item.user_file_info;
        }
    }
    methods.timeoutSearch = function(event) {
        if (collection.promise) {
            $timeout.cancel(collection.promise);
        }
        if (event && event.keyCode == 33 &&
            collection.start - collection.limit > 0) {
            // page up
            collection.start = collection.start - collection.limit;
            methods.setCurrentPage();
        }
        if (event && event.keyCode == 34 && collection.start + collection.limit < collection.totals[collection.searchTerm]) {
            // page down
            collection.start = collection.start + collection.limit;
            methods.setCurrentPage();
        }
        collection.promise = $timeout(methods.search, 500, true);
    }
    return methods;
});

fmpApp.controller("PlayerController", function($scope,
                                               ListenersService,
                                               FmpIpScanner,
                                               PlaylistService,
                                               PlayerService,
                                               Preload,
                                               $http,
                                               $modal,
                                               SearchService,
                                               Utils){

    $scope.works = "WORKS";
    $scope.ListenersService = ListenersService;
    $scope.FmpIpScanner = FmpIpScanner;
    $scope.Preload = Preload;
    $scope.pause = PlayerService.pause;
    $scope.play = PlayerService.play;
    $scope.next = PlayerService.next;
    $scope.prev = PlayerService.prev;
    $scope.PlayerService = PlayerService;
    $scope.PlaylistService = PlaylistService;
    $scope.rate = PlayerService.rate;
    $scope.thumb = PlayerService.thumb;
    $scope.searchTerm = SearchService.collection.searchTerm;
    $scope.SearchService = SearchService;
    $scope.search = SearchService.search;
    $scope.Utils = Utils;
    $scope.addToPlaylist = function(item){
        if (Utils.inList(PlaylistService.collection.history, item)) {
            return;
        }
        if (Utils.inList(Preload.collection.preload, item)) {
            PlaylistService.moveToHistory(item.id);
            return;
        }
        PlaylistService.collection.history.push(item);
        /*
        _id = kwargs.get('id')
        user_id = kwargs.get('uid')
        if not user_id:
            user_id = kwargs.get("user_id")
        cued = to_bool(kwargs.get('cued'))
        */
        $http({
          "method": 'GET',
          "url": "/cue",
          "params": {
            "id": item.id,
            "uid": ListenersService.collection.listener_user_ids[0],
            "cued": 1
          }
        });
    };
    $scope.removeFromPlaylist = function(item) {
        if (!Utils.inList(PlaylistService.collection.history, item) &&
            !Utils.inList(Preload.collection.preload, item)) {
            return;
        }
        var idx = Utils.getIdIndex(PlaylistService.collection.history, item.id);
        if (idx != -1) {
            PlaylistService.collection.history.splice(idx, 1);
        }
        var idx = Utils.getIdIndex(Preload.collection.preload, item.id);
        if (idx != -1) {
            Preload.collection.preload.splice(idx, 1);
        }
        $http({
          "method": 'GET',
          "url": "/cue",
          "params": {
            "id": item.id,
            "uid": ListenersService.collection.listener_user_ids[0],
            "cued": 0
          }
        }, function(){
            // console.log("MADE IT")
            // console.log(PlaylistService.getFileFromPreload());
        });
    };

    FmpIpScanner.startScan();
    var d = new Date();
    var myOtherModal = $modal({
        scope: $scope,
        template: '/static/partials/search.tpl.html?_='+Date.now()+".tpl.html",
        show: false,
        title:"Search",
        backdrop: false,
        onShow: function() {
            var $searchModalInput = $("#searchModalInput"),
                _this = $searchModalInput[0];
            $searchModalInput.focus();
            _this.selectionStart = _this.selectionEnd = _this.value.length;
        }
    });

    var aboutModal = $modal({
        scope: $scope,
        template: '/static/partials/about.tpl.html?_='+Date.now()+".tpl.html",
        show: false,
        title:"About",
        backdrop: false
    });

    // Show when some event occurs (use $promise property to ensure the template has been loaded)
    $scope.showModal = function() {
        myOtherModal.$promise.then(myOtherModal.show);
        SearchService.search();
    };
    $scope.showAboutModal = function() {
        aboutModal.$promise.then(aboutModal.show);
    }
    $scope.doSearch = function(searchTerm) {
        SearchService.collection.searchTerm = searchTerm;
        $scope.showModal();
        SearchService.timeoutSearch();
    };

});
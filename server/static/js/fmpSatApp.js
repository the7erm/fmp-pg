var fmpApp = angular.module('fmpApp', ['mgcrea.ngStrap']);
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
        console.error("ListenersService error:", e);
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
        }
    };
    return methods;
});

fmpApp.factory("Preload", function($http, $rootScope, ListenersService,
                                   FmpIpScanner, Utils){
    var collection = {
            "preload": []
        },
        methods = {
            "collection": collection
        };
    methods.getPreload = function() {
        var files = [],
            history = methods.PlaylistService.collection.history,
            preload = collection.preload;
        if (preload && preload.length > 0) {
            $.each(preload, function(idx, item){
                if (Utils.inList(history, item)) {
                    collection.preload.splice(idx, 1);
                }
            });
            if (collection.preload && collection.preload.length > 10) {
                return;
            }
        }
        if(history && history.length > 0) {
            files = files.concat(history);
        }
        if (preload && preload.length > 0) {
            files = files.concat(preload);
        }
        var postData = {
            user_ids: ListenersService.collection.listener_user_ids,
            primary_user_id: ListenersService.collection.listener_user_ids[0],
            secondary_user_ids: ListenersService.collection.listener_user_ids,
            prefetchNum: 10,
            secondaryPrefetchNum: 10,
            include_admins: false,
            files: files
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
                    found = Utils.inList(
                        methods.PlaylistService.collection.history, item);
                }
                if (found) {
                    continue;
                }
                collection.preload.push(item);
            }
            // collection.preload = collection.preload.concat(response.data.preload);
            console.log("collection.preload:", collection.preload);
        });
    };
    $rootScope.$on("server-found", methods.getPreload);
    $rootScope.$on("listeners-changed", methods.getPreload);
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
        for(var i=0;i<Preload.collection.preload.length;i++) {
            var item = Preload.collection.preload[i];
            if (item.id == id) {
                collection.history.push(item);
                Preload.collection.preload.splice(i, 1);
                Preload.getPreload();
            }
        }
    }

    methods.markAsPlayed = function(id, percent_played){
        // console.log("markAsPlayed", id, percent_played);
        if (isNaN(percent_played)) {
            return;
        }
        var int_percent_played = parseInt(percent_played);
        if (collection.playingId == id && collection.int_percent_played == int_percent_played) {
            return;
        }

        collection.playingId = id;
        collection.int_percent_played = int_percent_played;

        var params = {
            "user_ids": ListenersService.collection.listener_user_ids.join(","),
            "percent_played": percent_played,
            "file_id": id
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
                                         Utils){
    var collection = {
            "sound": document.createElement("audio"),
            "initialized": false,
            "playingId": null
        },
        methods = {
            "collection": collection
        };
    Preload.PlayerService = methods;
    collection.sound.setAttribute("preload", "auto");
    collection.sound.controls = true;
    collection.sound.style="width:100%";
    collection.sound.onerror = function() {
         alert("Error! Something went wrong");
    };
    collection.sound.onended = function(){
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
            methods.thumb(file.id, ufi.user.id, +1);
        }
        methods.setIndex(idx+1);
    }
    document.getElementById("player").appendChild(collection.sound);
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
            collection.sound.currentTime = currentTime;
        }
        if (paused && paused != "0") {
            methods.pause();
        }
    };

    methods.setPlayingData = function(id) {
        if (!id) {
            return;
        }
        collection.sound.src = (
            FmpIpScanner.collection.url+"download?file_id="+id);
        collection.playingId = id;
    }

    methods.play = function() {
        if (!collection.playingId) {
            Preload.getPreload();
            methods.playId(Preload.collection.preload[0].id);
        } else {
            collection.sound.play();
        }
    };
    methods.playId = function(id) {
        methods.setPlayingData(id);
        PlaylistService.moveToHistory(id);
        collection.sound.play();
    };
    methods.pause = function() {
        collection.sound.pause();
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
            methods.thumb(file.id, ufi.user.id, -1);
        }
        methods.setIndex(idx+1);
    };
    methods.getFileFromPreload = function() {
        if (!Preload.collection.preload ||
            Preload.collection.preload.length == 0) {
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
        methods.playId(file.id);
    }
    methods.prev = function() {
        var idx = methods.getPlayingIndex();
        methods.setIndex(idx-1);
    };
    methods.updateTime = function() {
        collection.currentTime = collection.sound.currentTime;
        collection.paused = collection.sound.paused;
        if (!collection.paused) {
            var percent_played = (
                collection.currentTime / collection.sound.duration) * 100;
            localStorage['playingId'] = collection.playingId;
            localStorage['percent_played'] = percent_played;
            localStorage['currentTime'] = collection.currentTime;
            localStorage['paused'] = 0;
            PlaylistService.markAsPlayed(collection.playingId, percent_played);
        } else {
            localStorage['paused'] = 1;
        }
    };
    methods.rate = function(fileId, userId, rating) {
        console.log("rate:", fileId, userId, rating);
        for(var i=0;i<PlaylistService.collection.history.length;i++) {
            var item = PlaylistService.collection.history[i];
            if (item.id == fileId) {
                for (var j=0;j<item.user_file_info.length;j++){
                    var ufi = item.user_file_info[j];
                    if (ufi['user'].id == userId) {
                        ufi['rating'] = rating;
                        var params = {
                            "user_id": userId,
                            "file_id": fileId,
                            "rating": rating
                        }
                        $http({
                          "method": 'GET',
                          "url": FmpIpScanner.collection.url+"rate",
                          "params": params
                        }).then(function(response) {
                            console.log("response.data:", response.data);
                            if (response.data) {
                                ufi['true_score'] = response.data.true_score;
                            }
                        });
                    }
                }
            }
        }
    };
    methods.thumb = function(fileId, userId, direction) {
        console.log("thumb:", fileId, userId, direction);
        for(var i=0;i<PlaylistService.collection.history.length;i++) {
            var item = PlaylistService.collection.history[i];
            if (item.id == fileId) {
                for (var j=0;j<item.user_file_info.length;j++){
                    var ufi = item.user_file_info[j];
                    if (ufi['user'].id == userId) {
                        ufi['skip_score'] = parseInt(ufi['skip_score']) + parseInt(direction);
                        var params = {
                            "user_id": userId,
                            "file_id": fileId,
                            "skip_score": ufi['skip_score']
                        }
                        $http({
                          "method": 'GET',
                          "url": FmpIpScanner.collection.url+"set_score",
                          "params": params
                        }).then(function(response) {
                            console.log("response.data:", response.data);
                            if (response.data) {
                                ufi['true_score'] = response.data.true_score;
                            }
                        });
                    }
                }
            }
        }
    }
    $interval(methods.updateTime, 1000);
    $rootScope.$on("playlist-loaded", methods.initPlayer);
    return methods;
});
fmpApp.factory("SearchService", function(ListenersService, $http,
                                         FmpIpScanner,
                                         $timeout){
    var collection = {
            results: {},
            searchTerm: "",
            expireTimes: {},
            start:0,
            limit:5,
            totals: {},
            promise: false
        },
        methods = {
            collection: collection
        };

    methods.query = function() {
        var start = collection.start,
            limit = collection.limit;
        if (typeof collection.totals[collection.searchTerm] == "undefined") {
            start = 0;
            limit = 5;
            collection.start = 0;
            collection.limit = 5;
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
        return uri;
    }

    methods.search = function() {
        var query = methods.query();
        collection.promise = false;
        collection.searchQuery = query;
        if (typeof collection.results[query] == "undefined") {
            collection.results[query] = [];
        }
        if (typeof collection.expireTimes[query] != "undefined" &&
            collection.expireTimes[query] < Date.now()) {
            return;
        }
        $http({
          "method": 'GET',
          "url": query
        }).then(function(response) {
            collection.results[query] = response.data.results;
            collection.totals[collection.searchTerm] = response.data.total;
            // expire in a few minutes
            collection.expireTimes[query] = Date.now() + (1000 * 60 * 5);
        });
    };
    methods.timeoutSearch = function() {
        if (collection.promise) {
            $timeout.cancel(collection.promise);
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
        });
    };

    FmpIpScanner.startScan();
    var d = new Date();
    var myOtherModal = $modal({
        scope: $scope,
        template: '/static/partials/search.tpl.html?_='+Date.now()+".tpl.html",
        show: false,
        title:"Search",
        backdrop: false
    });
    // Show when some event occurs (use $promise property to ensure the template has been loaded)
    $scope.showModal = function() {
        SearchService.search();
        myOtherModal.$promise.then(myOtherModal.show);
    };

});
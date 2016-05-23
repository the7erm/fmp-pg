fmpApp.controller("MainController", function($scope, $location, FmpListeners,
                                             FmpIpScanner, FmpSocket, FmpSync,
                                             FmpPlaylist, FmpPlayer, FmpPreload,
                                             $timeout, FmpRemote){
    var logger = new Logger("MainController", false);

    /*
    $scope.swipeLeft = function() {
        console.log("swipeLeft main");
        window.location = "#/playlist";
    };
    $scope.swipeRight = function() {
        console.log("swipeRight main")

        window.location = "#/player";
    }; */

    FmpSync.collection.FmpPlaylist = FmpPlaylist;
    // FmpSync.collection.FmpPlayer = FmpPlayer;
    FmpSync.collection.FmpListeners = FmpListeners;
    FmpSync.collection.FmpSocket = FmpSocket;
    FmpSync.collection.FmpIpScanner = FmpIpScanner;
    // FmpSync.collection.FmpPreload = FmpPreload;
    FmpListeners.collection.FmpSync = FmpSync;

    $scope.newSync = FmpSync.newSync;
    $scope.quickSync = FmpSync.quickSync;
    $scope.FmpSyncCollection = FmpSync.collection;
    $scope.connection = navigator.connection;
    $scope.path = $location.path();

    $scope.organize = FmpPlaylist.organize;
    $scope.organize_random = FmpPlaylist.organize_random;

    console.log("main.js 2");
    $scope.openSearch = function() {
        var user_ids = FmpListeners.collection.listener_user_ids.join(","),
            url = FmpIpScanner.collection.url+'#/search?s=0&q='+
                                               '&user_ids='+user_ids,
            res = confirm("You are now leaving the fmp app & accessing fmp "+
                          "directly.  Any song that is 'cued' will be "+
                          "automatically downloaded when you click the "+
                          "sync icon.");
        if (res) {
            cordova.InAppBrowser.open(url, "_system");
        }
    }

    $scope.scrollToPlaying = function() {
        console.log("scrollToPlaying()");
        if (!window.player || !window.player.file || !window.player.file.id) {
            if (!window.player) {
                console.log("missing window.player");
            } else if (!window.player.file) {
                console.log("missing window.player.file");
            } else if (!window.player.file.id) {
                console.log("missing window.player.file.id");
            } else {
                console.log("Not sure why I was caught");
            }
            $timeout($scope.scrollToPlaying, 1000);
            return;
        }
        $el = $("#file-"+window.player.file.id);
        if (!$el || $el.length == 0) {
            console.log("missing $el");
            $timeout($scope.scrollToPlaying, 1000);
            return;
        }
        console.log("el:",$el);
        $("html, body").animate({
            scrollTop: $el.offset().top-100
        }, "slow");
    }

    FmpIpScanner.startScan();
    logger.log("initialized");
});


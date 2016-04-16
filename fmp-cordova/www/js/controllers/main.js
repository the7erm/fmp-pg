fmpApp.controller("MainController", function($scope, $location, FmpListeners,
                                             FmpIpScanner, FmpSocket, FmpSync,
                                             FmpPlaylist, FmpPreload){
    /*
    $scope.swipeLeft = function() {
        console.log("swipeLeft main");
        window.location = "#/player";
    };
    $scope.swipeRight = function() {
        console.log("swipeRight main")
        window.location = "#/playlist";
    };
    */
    console.log("main.js 1");
    FmpSync.collection.FmpPlaylist = FmpPlaylist;
    FmpSync.collection.FmpListeners = FmpListeners;
    FmpSync.collection.FmpSocket = FmpSocket;
    FmpSync.collection.FmpIpScanner = FmpIpScanner;
    FmpSync.collection.FmpPreload = FmpPreload;
    FmpListeners.collection.FmpSync = FmpSync;

    $scope.newSync = FmpSync.newSync;
    $scope.FmpSyncCollection = FmpSync.collection;
    $scope.connection = navigator.connection;
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

    FmpIpScanner.startScan();
    console.log("mainJS ok");
});
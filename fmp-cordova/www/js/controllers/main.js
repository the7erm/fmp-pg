fmpApp.controller("MainController", function($scope, $location, FmpListeners,
                                             FmpIpScanner, FmpSocket, FmpSync,
                                             FmpPlaylist, FmpPlayer,
                                             FmpPreload){
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

    FmpSync.collection.FmpPlaylist = FmpPlaylist;
    FmpSync.collection.FmpPlayer = FmpPlayer;
    FmpSync.collection.FmpPreload = FmpPreload;
    FmpSync.collection.FmpListeners = FmpListeners;
    FmpSync.collection.FmpSocket = FmpSocket;

    $scope.newSync = FmpSync.newSync;
    $scope.FmpSyncCollection = FmpSync.collection;
    $scope.connection = navigator.connection;

    FmpIpScanner.startScan();
});
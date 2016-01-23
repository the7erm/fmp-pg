fmpApp.controller('PlaylistCtrl', function ($scope, FmpPlaylist, FmpSync,
                                            FmpPreload, FmpListeners) {
    $scope.FmpPlaylistCollection = FmpPlaylist.collection;
    $scope.FmpPreloadCollection = FmpPreload.collection;
    $scope.syncCollections = FmpSync.syncCollections;
    $scope.listenersCollection = FmpListeners.collection;
    $scope.next = FmpPlaylist.next;
    $scope.prev = FmpPlaylist.prev;
    $scope.player = window.player;
    $scope.organize = FmpPlaylist.organize;
    $scope.rate = FmpPlaylist.rate;
    $scope.score = FmpPlaylist.score;
});
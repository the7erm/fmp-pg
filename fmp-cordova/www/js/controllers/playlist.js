fmpApp.controller('PlaylistCtrl', function ($scope, FmpPlaylist, FmpSync,
                                            FmpListeners, FmpUtils, $rootScope,
                                            $timeout) {
    var logger = new Logger("PlaylistCtrl", false);

    $scope.FmpSyncCollection = FmpSync.collection;
    $scope.syncCollections = FmpSync.newSync;
    $scope.listenersCollection = FmpListeners.collection;
    $scope.next = FmpPlaylist.next;
    $scope.prev = FmpPlaylist.prev;
    $scope.player = window.player;
    $scope.organize = FmpPlaylist.organize;
    $scope.rate = FmpPlaylist.rate;
    $scope.score = FmpPlaylist.score;

    $scope.onStart = window.player.onDragStart;

    $scope.onChange = window.player.onDragChange;
    $scope.onEnd = window.player.onDragEnd;
    $scope.translate = FmpUtils.formatTime;

    $scope.trash = function(file) {
        console.log("trash:", file);
        var file_id = file.id,
            res = confirm("Remove "+file.get_artist_title());
        if (!res) {
            return;
        }
        console.log("deleting ... ");
        FmpPlaylist.deleteFile(file.spec);
    };

    $scope.syncFile = function(file) {
        console.log("$scole.syncFile:",file);
        file.spec.removeIfPlayed = false;
        console.log("/removeIfPlayed");
        FmpSync.syncFile(file.spec);
    }
    $timeout(function(){
        $scope.rendering = true;
        $scope.FmpPlaylistCollection = FmpPlaylist.collection;
        $scope.rendering = false;
    }, 500);
    logger.log("initialized");
});
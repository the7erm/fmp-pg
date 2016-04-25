
fmpApp.controller('PlaylistCtrl', function ($scope, FmpPlaylist, FmpSync,
                                            FmpListeners, FmpUtils, $rootScope,
                                            $timeout, $location) {
    var logger = new Logger("PlaylistCtrl", true);

    $scope.FmpSyncCollection = FmpSync.collection;
    $scope.syncCollections = FmpSync.newSync;
    $scope.listenersCollection = FmpListeners.collection;
    $scope.next = FmpPlaylist.next;
    $scope.prev = FmpPlaylist.prev;
    $scope.player = window.player;
    $scope.organize = FmpPlaylist.organize;
    $scope.organize_random = FmpPlaylist.organize_random;
    $scope.rate = FmpPlaylist.rate;
    $scope.score = FmpPlaylist.score;
    $scope.path = $location.path();

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
        file.spec.keep = false;
        console.log("deleting ... ");
        FmpPlaylist.deleteFile(file);
    };

    $scope.quickSync = function() {
        FmpSync.quickSync();
    };

    $scope.syncFile = function(file) {
        console.log("$scole.syncFile:",file);
        file.spec.removeIfPlayed = false;
        console.log("/removeIfPlayed");
        FmpSync.syncFile(file.spec);
    }
    if (window.location.hash == "#/player") {
         $timeout(function(){
            if (!$scope.FmpPlaylistCollection) {
                $scope.FmpPlaylistCollection = FmpPlaylist.collection;
            }
        }, 1000);
    } else {
        $timeout(function(){
            if (!$scope.FmpPlaylistCollection) {
                $scope.FmpPlaylistCollection = FmpPlaylist.collection;
            }
            $scope.scrollToPlaying();
        }, 1000);
    }

    logger.log("initialized");
});
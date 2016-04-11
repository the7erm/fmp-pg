fmpApp.controller('PlaylistCtrl', function ($scope, FmpPlaylist, FmpSync,
                                            FmpPreload, FmpListeners,
                                            FmpUtils, $rootScope) {
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
        console.log("trash file_id:", file_id);
        var deleteIndexes = [];
        for(var i=0;i<FmpPlaylist.collection.files.length;i++) {
            var file = FmpPlaylist.collection.files[i];
            if (file.id == file_id) {
                deleteIndexes.push(i);
            }
        }
        deleteIndexes.reverse();
        for(var i=0;i<deleteIndexes.length;i++) {
            var idx = deleteIndexes[i],
                file = FmpPlaylist.collection.files[idx];
            if (FmpSync.collection.deleted.indexOf(file_id) == -1) {
                FmpSync.collection.deleted.push(file_id);
            }
            FmpPlaylist.collection.files.splice(idx,1);
            file.delete();
        }
        FmpSync.save();
    };

});
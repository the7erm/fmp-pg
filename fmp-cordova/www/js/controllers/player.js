fmpApp.controller('PlayerController', function ($scope, FmpSync,
                                                FmpPlayer, $rootScope,
                                                FmpListeners) {
    console.log("PlayerController");
    $scope.FmpPlayerCollection = FmpPlayer.collection;
    $scope.syncCollections = FmpSync.newSync;
    $scope.syncFile = FmpSync.syncFile;
    $scope.FmpSyncCollection = FmpSync.collection;
    $scope.player = window.player;
    $scope.item = window.player.file;

    $rootScope.$on("time-status", function(scope, file){
        // console.log("$rootScope.$on time-status");
        if (!$scope.$$phase) {
            $scope.$apply();
        }
    });

    $scope.FmpListenersCollection = FmpListeners.collection;
    $scope.downloader = window.downloader;
    $scope.toggleVoteToSkip = function(user){
        console.log("toggleVoteToSkip:", user);
        for (var i=0;i<window.player.file.user_file_info.length;i++) {
            var ufi = window.player.file.user_file_info[i];
            if (ufi.user_id == user.id) {
                console.log("found ufi:", ufi);
                if (typeof ufi.voted_to_skip == "undefined") {
                    ufi.voted_to_skip = false;
                }
                console.log("voted_to_skip was:", ufi.voted_to_skip);
                var voted_to_skip = !ufi.voted_to_skip;
                console.log("voted_to_skip:", voted_to_skip);
                ufi.voted_to_skip = voted_to_skip;
                window.player.file.vote_to_skip(ufi.user_id, voted_to_skip);
            }
        }
    };
    $scope.confirmVoteToSkip = function() {
        window.player.next();
    };
    console.log("/PlayerController");
});

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
    var playingIndex = -1,
        files = FmpPlaylist.collection.files;



    for (var i=0;i<files.length;i++) {
        var file = files[i];
        if (file.playing) {
            playingIndex = i;
            break;
        }
    }

    $scope.showing = {
        "lowest": 0,
        "highest": 0
    };

    if (playingIndex != -1) {
        files[playingIndex].showing = true;
    } else {
        $scope.showing = {
            "lowest": playingIndex,
            "highest": playingIndex
        };
    }

    $scope.moreInView = function(direction) {
        $scope.more(direction);
        var tmp = function() {
            $scope.more(direction);
        };
    }

    for (var i=0;i<files.length;i++) {
        if (i >= (playingIndex-1) && i <= (playingIndex+1)) {
            files[i].showing = true;
            if ($scope.showing.lowest > i) {
                $scope.showing.lowest = i;
            }
            if ($scope.showing.highest < i) {
                $scope.showing.highest = i;
            }
        } else {
            files[i].showing = false;
        }
    }

    $scope.more = function(direction) {
        var files = FmpPlaylist.collection.files;
        if (!files) {
            console.log("no files");
            return;
        }
        if (direction < 0) {
            $scope.showing.lowest = $scope.showing.lowest + direction;
            if ($scope.showing.lowest < 0 && files[0].showing) {
                return;
            }
        }
        if (direction > 0) {
            $scope.showing.highest = $scope.showing.highest + direction;
            if ($scope.showing.highest >= files.length && files[files.length-1].showing) {
                return;
            }
        }
        console.log("more:", direction, $scope.showing);
        for (var i=0;i<files.length;i++) {
            var file = files[i];
            if (file.showing) {
                continue;
            }
            if (i >= $scope.showing.lowest && i <= $scope.showing.highest) {
                file.showing = true;
                if (file.spec.cued &&
                    FmpListeners.collection.listener_user_ids.indexOf(file.spec.cued.user_id) == -1) {
                        if (direction > 0 &&
                            $scope.showing.highest < files.length) {
                                $scope.showing.highest = $scope.showing.highest + 1;
                        }
                        if (direction < 0 &&
                            $scope.showing.lowest > 0) {
                                $scope.showing.lowest = $scope.showing.lowest - 1;
                        }
                }
                if (!$scope.$$phase) {
                    $scope.$apply();
                }
            }
        }
        if (!$scope.$$phase) {
            $scope.$apply();
        }
    }

    $scope.checkInview = function(idx) {
        idx = parseInt(idx);
        var files_length = FmpPlaylist.collection.files.length;
        if ($scope.showing.highest >= files_length) {
            return;
        }
        // console.log("checkInview idx:", idx, ":", files_length);
        // console.log("scope.showing:", $scope.showing)
        if ((idx-(files_length * 0.5)) < $scope.showing.lowest && $scope.showing.lowest > 0) {
            // console.log("checkInview adding more -");
            $scope.more(-3);
        }
        if ((idx+(files_length * 0.5)) > $scope.showing.highest &&
            $scope.showing.highest < files_length) {
                // console.log("checkInview adding more +");
                $scope.more(+3);
        }
    }
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
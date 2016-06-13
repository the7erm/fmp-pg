
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
    $scope.organize_by_plid = FmpPlaylist.organize_by_plid;
    $scope.organize_random = FmpPlaylist.organize_random;
    $scope.rate = FmpPlaylist.rate;
    $scope.score = FmpPlaylist.score;
    $scope.path = $location.path();
    $scope.moreLock = true;

    $scope.onStart = window.player.onDragStart;

    $scope.onChange = window.player.onDragChange;
    $scope.onEnd = window.player.onDragEnd;
    $scope.translate = FmpUtils.formatTime;
    $scope.hasUnratedFiles = false;
    var playingIndex = -1,
        files = FmpPlaylist.collection.files;

    var checkForUnrated = function(file) {
        var foundUnrated = false;
        for (var i=0;i<file.spec.user_file_info.length;i++) {
            var ufi = file.spec.user_file_info[i];
            if (FmpListeners.collection.listener_user_ids.indexOf(ufi.user_id) == -1) {
                continue;
            }
            if (ufi.rating == 6) {
                $scope.hasUnratedFiles = true;
                console.log("ufi.rating:", ufi.rating);
                foundUnrated = true;
                break;
            }
        }
        return foundUnrated;
    };

    var hasUnratedWrapper = function(file) {
        if ($scope.hasUnratedFiles) {
            return true;
        }
        if (checkForUnrated(file)) {
            return true;
        }
        return false;
    }

    for (var i=0;i<files.length;i++) {
        var file = files[i];
        hasUnratedWrapper(file);
        if (file.playing) {
            playingIndex = i;
            break;
        }
    }

    $scope.showing = {
        "lowest": files.length,
        "highest": 0
    };

    if (playingIndex != -1) {
        files[playingIndex].showing = true;
        $scope.showing = {
            "lowest": playingIndex,
            "highest": playingIndex
        };
    } else {

    }

    $scope.moreInView = function(direction) {
        // $scope.more(direction);
    }

    for (var i=0;i<files.length;i++) {
        try {
            var file = files[i];
        } catch (e) {
            continue;
        }
        file.viewed = true;
        hasUnratedWrapper(file);
        if (i >= (playingIndex-1) && i <= (playingIndex+1)) {
            file.showing = true;
            if ($scope.showing.lowest > i) {
                $scope.showing.lowest = i;
            }
            if ($scope.showing.highest < i) {
                $scope.showing.highest = i;
            }
        } else {
            file.showing = false;
        }
    }

    console.log("$scope.showing after initiali setup:", $scope.showing);

    var showFile = function(i, files, direction) {
        try {
            var file = files[i];
        } catch(e) {
            return;
        }
        if (file.showing) {
            return;
        }
        hasUnratedWrapper(file);
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

    $scope.more = function(direction, scrollToIdx) {
        if ($scope.moreLock) {
            console.log("More lock");
            return;
        }
        $scope.moreLock = true;
        var files = FmpPlaylist.collection.files;
        if (!files) {
            console.log("no files");
            $scope.moreLock = false;
            return;
        }
        if (typeof $scope == "undefined") {
            console.log("no $scope");
            $scope.moreLock = false;
            return;
        }

        if (typeof $scope.showing == "undefined") {
            $scope.showing = {
                "lowest": 0,
                "highest": 0
            };
        }
        if (direction < 0) {
            $scope.showing.lowest = $scope.showing.lowest + direction;
            try {
                if ($scope.showing.lowest < 0 && files[0].showing) {
                    $scope.moreLock = false;
                    return;
                }
            } catch (e) {
                $scope.moreLock = false;
                return;
            }
        }
        if (direction > 0) {
            $scope.showing.highest = $scope.showing.highest + direction;
            try {
                if ($scope.showing.highest >= files.length && files[files.length-1].showing) {
                    $scope.moreLock = false;
                    return;
                }
            } catch (e) {
                $scope.moreLock = false;
                return;
            }
        }
        console.log("more direction", direction, "showing:", $scope.showing);
        var hasUnratedFiles = false;
        if (direction > 0) {
            for (var i=0;i<files.length;i++) {
                showFile(i, files, direction);
                var file = files[i];
                hasUnratedFiles = hasUnratedWrapper(file);
            }
        }
        if (direction < 0) {
            for (var i=files.length-1;i>0;i--) {
                showFile(i, files, direction);
                var file = files[i];
                hasUnratedFiles = hasUnratedWrapper(file);
            }
        }
        $scope.hasUnratedFiles = hasUnratedFiles;

        if (!$scope.$$phase) {
            $scope.$apply();
        }
        if (typeof scrollToIdx != 'undefined') {
            // $scope.scrollToElement("#file-"+files[scrollToIdx].id);
        }
        $scope.moreLock = false;
    }



    $scope.scrollToUnrated = function() {
        if (!FmpPlaylist.collection.files) {
            console.log("no files");
            return;
        }
        var files = FmpPlaylist.collection.files,
            foundAtIndex = -1;
        for (var i=0;i<files.length;i++) {
            var file = files[i],
                found = checkForUnrated(file);
            if (found) {
                foundAtIndex = i;
                file.showing = true;
                if (!$scope.$$phase) {
                    $scope.$apply();
                }
                break;
            }
        }
        if (foundAtIndex == -1) {
            return;
        }
        var changedShowingIndexs = false;
        if (foundAtIndex > $scope.showing.highest) {
            $scope.showing.highest = foundAtIndex;
            changedShowingIndexs = true;
        }
        if (foundAtIndex < $scope.showing.lowest) {
            changedShowingIndexs = true;
            $scope.showing.lowest = foundAtIndex;
        }
        if (!changedShowingIndexs) {
            var file = files[foundAtIndex];
            $scope.scrollToElement("#file-"+file.id, 1000);
            return;
        }
        for (var i=0;i<files.length;i++) {
            showFile(i, files, 0);
        }
        if (!$scope.$$phase) {
            $scope.$apply();
        }
        $scope.scrollToElement("#file-"+file.id, 1000);
    }

    $scope.checkInview = function(idx) {
        idx = parseInt(idx);
        var files = FmpPlaylist.collection.files,
            files_length = files.length;
        if (!FmpPlaylist.collection.files) {
            return;
        }

        var file = files[idx];
        hasUnratedWrapper(file);
        if (file.viewed) {
            return;
        }
        file.viewed = true;

        // console.log("checkInview idx:", idx, ":", files_length);
        // console.log("scope.showing:", $scope.showing)
        if ($scope.showing && $scope.showing.lowest > 0 &&
            $scope.showing.lowest > (idx-3)) {
            // console.log("checkInview adding more -");
            $scope.more(-3, idx);
        }
        if ($scope.showing.highest && $scope.showing.highest < files_length) {
                // console.log("checkInview adding more +");
                $scope.more(+3, idx);
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
            for (var i=0;i<files.length;i++) {
                files[i].viewed = false;
            }
        }, 1000);
    } else {
        $scope.moreLock = false;
        $timeout(function(){
            if (!$scope.FmpPlaylistCollection) {
                $scope.FmpPlaylistCollection = FmpPlaylist.collection;
            }
            $scope.scrollToPlaying();
            $timeout(function(){
                var files = FmpPlaylist.collection.files;
                for (var i=0;i<files.length;i++) {
                    files[i].viewed = false;
                }
            }, 2000)
        }, 1000);
    }

    logger.log("initialized");
});
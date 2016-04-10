fmpApp
.factory('FmpSync', function($rootScope, $http, FmpLocalStorage, FmpUtils,
                             FmpIpScanner, FmpSocket, $timeout){
    var collection = {
            payload: {},
            transactionIds: [],
            transactions: [],
            storeFields: {
                "objects": [
                    "payload"
                ]
            },
            deleted: [],
            lastSyncTime: 0,
            FmpPlaylist: null, // Assigned by FmpConductor
            FmpPreload: null,   // Assigned by FmpConductor,
            played_files: []
        },
        methods = {
            collection:collection
        };

    collection.transactionLock = false;
    FmpLocalStorage.load(collection);


    methods.save = function() {
        methods.cleanPayload();
        FmpLocalStorage.save(collection);
    };

    methods.onSyncProcessed = function(){
        console.log("onSyncProcessed:", FmpSocket.collection.processed);
        while (FmpSocket.collection.processed.length > 0) {
            var processGroup = FmpSocket.collection.processed.shift();
            console.log("processGroup:", processGroup);
            for (var i=0;i<processGroup.processed.length;i++) {
                var item = processGroup.processed[i];
                console.log("item:", item);
                methods.removeSyncedPayload(item.spec);
                if (typeof item.file != 'undefined' && item.file) {
                    if (typeof item.file.user_file_info != 'undefined') {
                        for(var i=0;i<item.file.user_file_info.length;i++) {
                            var ufi = item.file.user_file_info[i];
                            methods.processUfi(ufi);
                        }
                    }
                }
            }
        }
        methods.save();
    };

    $rootScope.$on("sync-processed", methods.onSyncProcessed);

    methods.today = function () {
        var today = FmpUtils.today();
        if (typeof collection.payload[today] == 'undefined') {
            collection.payload[today] = {};
        }
        return today;
    };

    methods.syncCollections = function() {
        console.log("sync-collections()");
        console.log("1");
        if (!FmpSocket.collection.connected) {
            return;
        }
        collection.deleted = [];
        var transaction_id = Math.random().toString(36).replace(/[^a-z0-9]+/g, '');
        collection.transactionIds.push(transaction_id);
        console.log("2");
        var payload = {
            "transaction_id": transaction_id,
            "playlist_ids": [],
            "preload_ids": [],
            "primary_user_id": collection.FmpListeners.collection.primary_user_id,
            "listener_user_ids": collection.FmpListeners.collection.listener_user_ids,
            "secondary_user_ids": collection.FmpListeners.collection.secondary_user_ids,
            "prefetchNum": collection.FmpListeners.collection.prefetchNum,
            "secondaryPrefetchNum": collection.FmpListeners.collection.secondaryPrefetchNum,
            "needs_synced_files": []
        };
        console.log("3");
        collection.played_files = [];
        if (collection.FmpPreload.collection.files) {
            for(var i=0;i<collection.FmpPreload.collection.files.length;i++) {
                var file = collection.FmpPreload.collection.files[i];
                if (file.played || file.spec.played) {
                    collection.played_files.push(file.id);
                }
                payload.preload_ids.push(file.id);
                if (file.needsSync || file.spec.needsSync) {
                    payload.needs_synced_files.push(file.spec);
                }
            }
        }
        console.log("4");
        if (collection.FmpPreload.collection.files) {
            for(var i=0;i<collection.FmpPlaylist.collection.files.length;i++) {
                var file = collection.FmpPlaylist.collection.files[i];
                payload.playlist_ids.push(file.id);
                if ((file.played || file.spec.played ) &&
                    collection.played_files.indexOf(file.id) == -1) {
                    collection.played_files.push(file.id);
                }
                if (file.needsSync) {
                    payload.needs_synced_files.push(file.spec);
                }
            }
        }
        FmpSocket.send({"action": "sync-collections",
                        "payload": payload});
        console.log("5");
    };

    methods.processFileData = function(fileList) {
        fileList = FmpUtils.sanitize(fileList);
        while(fileList.length>0) {
            var fileData = fileList.shift();
            if (collection.deleted.indexOf(fileData.id) != -1 ||
                collection.deleted.indexOf(parseInt(fileData.id)) != -1) {
                continue;
            }
            if (collection.played_files.indexOf(fileData.id) != -1) {
                fileData.played = true;
            }
            var idx = FmpUtils.indexOfFile(collection.FmpPlaylist.collection.files,
                                           fileData);
            if (idx != -1) {
                var plfile = collection.FmpPlaylist.collection.files[idx];
                if (collection.played_files.indexOf(plfile.id) != -1) {
                    plfile.played = true;
                }
                if (plfile.spec.needsSyncedProcessed) {
                    plfile.spec.needsSync = false;
                }
                if (!angular.equals(plfile.spec.user_file_info,
                                    fileData.user_file_info)) {
                    plfile.spec.user_file_info = fileData.user_file_info;
                    plfile.dirty = true;
                }
                // array.splice(index, 1);
                if (plfile.played && !plfile.playing) {
                    console.log("******** DELETING ***",plfile);
                    collection.FmpPlaylist.collection.files.splice(idx,1);
                    collection.deleted.push(plfile.id);
                    plfile.delete();
                }
                continue;
            }

            console.log("processFileData");
            var file = new FmpFile(fileData);
            if (collection.played_files.indexOf(file.id) != -1) {
                file.played = true;
            }
            file.$rootScope = $rootScope;
            file.$timeout = $timeout;
            // Put it in a timeout so the file will download in the right order.
            $timeout(file.download_if_not_exists);
            console.log("FmpFile:", file);
            collection.FmpPlaylist.collection.files.push(file);
        }
        collection.FmpPlaylist.save();
    };

    methods.onPlaylistData = function () {
        methods.processFileData(FmpSocket.collection.playlistData);
    };

    methods.onPreloadData = function() {
        methods.processFileData(FmpSocket.collection.preloadData);
    };

    $rootScope.$on("playlist-data", methods.onPlaylistData);
    $rootScope.$on("preload-data", methods.onPreloadData);
    $rootScope.$on("socket-open", methods.sync);

    return methods;
});
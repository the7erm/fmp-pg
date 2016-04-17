fmpApp.factory('FmpSync', function($rootScope, $http, FmpLocalStorage, FmpUtils,
                                   FmpIpScanner, FmpSocket, $timeout){

    var logger = new Logger("FmpSync", true);
    var collection = {
            payload: {},
            transactionIds: [],
            transactions: [],
            storeFields: {
                "objects": [
                    "payload",
                    "deleted"
                ]
            },
            deleted: [],
            lastSyncTime: 0,
            FmpPlaylist: null, // Assigned by FmpConductor
            FmpPreload: null,   // Assigned by FmpConductor,
            played_files: [],
            syncQue: [],
            syncLock: false,
            syncFileLock: false,
            syncPreloadLock: false,
            removeFilesLock: false
        },
        methods = {
            collection:collection
        };
    /*
        main.js will populate
        FmpSync.collection.FmpPlaylist = FmpPlaylist;
        FmpSync.collection.FmpPlayer = FmpPlayer;
        FmpSync.collection.FmpPreload = FmpPreload;
        FmpSync.collection.FmpListeners = FmpListeners;
        FmpSync.collection.FmpSocket = FmpSocket;
        FmpSync.collection.FmpIpScanner = FmpIpScanner;
    */

    collection.transactionLock = false;
    FmpLocalStorage.load(collection);

    methods.save = function() {
        if (collection.deleted.length > 100) {
            var start = collection.deleted.length - 100;
            if (start > 0) {
                collection.deleted = collection.deleted.splice(start);
            }
        }
        // methods.cleanPayload();
        FmpLocalStorage.save(collection);
        logger.log("localStorage.deleted",localStorage.deleted);
    };

    methods.onSyncProcessed = function(){
        logger.log("onSyncProcessed:", FmpSocket.collection.processed);
        while (FmpSocket.collection.processed.length > 0) {
            var processGroup = FmpSocket.collection.processed.shift();
            logger.log("processGroup:", processGroup);
            for (var i=0;i<processGroup.processed.length;i++) {
                var item = processGroup.processed[i];
                logger.log("item:", item);
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
        console.log("syncCollections DEPRECATED");
        return;
        logger.log("1");
        if (!FmpSocket.collection.connected) {
            logger.log("FmpIpScanner.collection.socketUrl:",
                        FmpIpScanner.collection.socketUrl);
            if (!FmpIpScanner.collection.socketUrl) {
                FmpIpScanner.startScan();
            } else {
                FmpSocket.connect();
            }
            return;
        }
        var transaction_id = Math.random().toString(36).replace(/[^a-z0-9]+/g, '');
        collection.transactionIds.push(transaction_id);
        logger.log("2");
        var payload = {
            "transaction_id": transaction_id,
            "playlist_ids": [],
            "preload_ids": [],
            "primary_user_id": collection.FmpListeners.collection.primary_user_id,
            "listener_user_ids": collection.FmpListeners.collection.listener_user_ids,
            "secondary_user_ids": collection.FmpListeners.collection.secondary_user_ids,
            "prefetchNum": collection.FmpListeners.collection.prefetchNum,
            "secondaryPrefetchNum": collection.FmpListeners.collection.secondaryPrefetchNum,
            "needs_synced_files": [],
            "deleted": collection.deleted
        };
        logger.log("3");
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
        logger.log("4");
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
        logger.log("5");
    };

    methods.processFileData = function(fileList) {
        fileList = FmpUtils.sanitize(fileList);
        collection.syncing = true;
        while(fileList.length>0) {
            var fileData = fileList.shift();
            logger.log("fileData:",fileData.id);
            if (collection.deleted.indexOf(fileData.id) != -1 ||
                collection.deleted.indexOf(parseInt(fileData.id)) != -1) {
                logger.log("Not adding, in deleted files:", fileData.id);
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
                    logger.log("******** DELETING ***",plfile);
                    collection.FmpPlaylist.collection.files.splice(idx,1);
                    if (collection.deleted.indexOf(plfile.id) == -1) {
                        collection.deleted.push(plfile.id);
                    }
                    plfile.delete();
                } else {
                    $timeout(collection.FmpPlaylist.collection.files.download_if_not_exists);
                }
                continue;
            }

            logger.log("processFileData");
            var file = new FmpFile(fileData);
            if (collection.played_files.indexOf(file.id) != -1) {
                file.played = true;
            }
            file.$rootScope = $rootScope;
            file.$timeout = $timeout;
            // Put it in a timeout so the file will download in the right order.
            $timeout(file.download_if_not_exists);
            logger.log("FmpFile:", file);
            collection.FmpPlaylist.collection.files.push(file);
        }
        collection.FmpPlaylist.save();
        methods.save();
        collection.syncing = false;
    };

    methods.onPlaylistData = function () {
        methods.processFileData(FmpSocket.collection.playlistData);
    };

    methods.onPreloadData = function() {
        methods.processFileData(FmpSocket.collection.preloadData);
    };

    $rootScope.$on("playlist-data", methods.onPlaylistData);
    $rootScope.$on("preload-data", methods.onPreloadData);


    /* new code */

    methods.getPlaylistFiles = function() {
        var playlistFiles = [];
        if (collection.FmpPlaylist.collection.files) {
            for(var i=0;i<collection.FmpPlaylist.collection.files.length;i++) {
                playlistFiles.push(collection.FmpPlaylist.collection.files[i].spec);
            }
        }
        return playlistFiles;
    }

    methods.removeFiles = function() {
        // logger.log("DISABLED removeFiles()", collection.filesToRemove.length);
        // collection.filesToRemove = [];

        if (!collection.FmpPlaylist.collection.loaded) {
            setTimeout(methods.removeFiles, 1000);
            return;
        }
        if (collection.removeFilesLock) {
            return;
        }
        collection.removeFilesLock = true;
        collection.removingFiles = false;

        if (typeof localStorage.removeTimestamp != "undefined") {
            try {
                removeTimestamp = parseFloat(localStorage.removeTimestamp);
            } catch (e) {
                removeTimestamp = 0;
            }
        }

        if (collection.filesToRemove.length > 0) {
            while (collection.filesToRemove.length > 0) {
                var removeId = collection.filesToRemove.pop();
                for(var idx=collection.FmpPlaylist.collection.files.length - 1;
                    idx > -1;
                    idx--) {
                        var plfile = collection.FmpPlaylist.collection.files[idx];
                        if (plfile.spec.id == removeId && !plfile.spec.playing) {
                            collection.FmpPlaylist.deleteFile(plfile);
                        }
                }
            }
        }

        var removeTimestamp = 0,
            file_ids = [],
            startTimestamp = Date.now() / 1000;

        for (var i=0;i<collection.FmpPlaylist.collection.files.length;i++) {
            var file = collection.FmpPlaylist.collection.files[i];
            if (!file.playing) {
                file_ids.push(file.id);
            }
        }

        if (file_ids.length == 0) {
            collection.removeFilesLock = false;
            return;
        }

        var post_data = {
            "primary_user_id": collection.FmpListeners.collection.primary_user_id,
            "listener_user_ids": collection.FmpListeners.collection.listener_user_ids,
            "secondary_user_ids": collection.FmpListeners.collection.secondary_user_ids,
            "removeTimestamp": removeTimestamp,
            "deviceTimestamp": Date.now() / 1000,
            "file_ids": file_ids
        };
        $http({
          method: 'POST',
          url: FmpIpScanner.collection.url+"playedSince",
          data: JSON.stringify(post_data),
          headers: {
            'Content-Type': "application/json"
          }
        }).then(function successCallback(response) {
            if (response.data.STATUS != "OK") {
                logger.log("removeFiles response.data ERROR:", response.data);
                collection.syncPreloadLock = false;
                return;
            }
            logger.log("removeFiles response.data.result:", response.data.result);
            while (response.data.result.length > 0) {
                var ufi = response.data.result.shift();
                for(var i=0;i<collection.FmpPlaylist.collection.files.length;i++) {
                    var file = collection.FmpPlaylist.collection.files[i];
                    if (file.id == ufi.file_id) {
                        var deleteCb = function(file){
                            // We're removing it from storage so it won't
                            // be synced later.
                            if(typeof localStorage["deleted-"+file.id] != "undefined") {
                                delete localStorage["deleted-"+file.id];
                            }
                            logger.log("deleted played file:", file.id);
                        }
                        if (typeof file.cued == "undfined" || !file.cued) {
                            collection.FmpPlaylist.deleteFile(file, deleteCb);
                        } else if (file.cued.user_id == ufi.user_id) {
                            collection.FmpPlaylist.deleteFile(file, deleteCb);
                        }
                    }
                }
            }
            localStorage.removeTimestamp = startTimestamp;
            collection.removeFilesLock = false;
        }, function(){
            collection.removeFilesLock = false;
        });
    }

    methods.syncPreload = function() {
        if (collection.syncPreloadLock) {
            logger.log("!syncPreload syncPreloadLock:",collection.syncPreloadLock);
            return;
        }
        if (navigator.connection.type != Connection.WIFI) {
            return;
        }
        logger.log("syncPreload");

        collection.syncPreloadLock = true;
        /*
        "playlist_ids": [],
            "preload_ids": [],
            "primary_user_id": collection.FmpListeners.collection.primary_user_id,
            "listener_user_ids": collection.FmpListeners.collection.listener_user_ids,
            "secondary_user_ids": collection.FmpListeners.collection.secondary_user_ids,
            "prefetchNum": collection.FmpListeners.collection.prefetchNum,
            "secondaryPrefetchNum": collection.FmpListeners.collection.secondaryPrefetchNum,
            "needs_synced_files": [],
            "deleted": collection.deleted
        */
        var files = methods.getPlaylistFiles(),
            post_data = {
                'files': files,
                "primary_user_id": collection.FmpListeners.collection.primary_user_id,
                "listener_user_ids": collection.FmpListeners.collection.listener_user_ids,
                "secondary_user_ids": collection.FmpListeners.collection.secondary_user_ids,
                "prefetchNum": collection.FmpListeners.collection.prefetchNum,
                "secondaryPrefetchNum": collection.FmpListeners.collection.secondaryPrefetchNum
            },
            grouped_by_user = {};

        logger.log("POST_DATA:", post_data);

        for (var i=0;i<files.length;i++) {
            var file = files[i],
                user_id = 0;
            if (typeof file.cued != "undefined" && file.cued) {
                user_id = file.cued.user_id;
            }
            if (typeof grouped_by_user[user_id] == "undefined") {
                grouped_by_user[user_id] = [];
            }
            grouped_by_user[user_id].push(file.id);
        }
        var needFiles = false,
            tripped = false;
        if (angular.equals(grouped_by_user, {})) {
            needFiles = true;
        } else {
            for(var user_id in grouped_by_user) {
                var groupLength = grouped_by_user[user_id].length;
                logger.log("user_id:", user_id, "groupLength:", groupLength);
                if (user_id == 0) {
                    continue;
                }
                if (collection.FmpListeners.collection.secondary_user_ids.indexOf(user_id) != -1 &&
                    groupLength <= 10) {
                    logger.log("need files");
                    needFiles = true;
                    tripped = true;
                    break;
                }
                if (collection.FmpListeners.collection.primary_user_id == user_id &&
                    groupLength <= 50) {
                    logger.log("need files");
                    needFiles = true;
                    tripped = true;
                    break;
                }
            }
        }

        if (!tripped) {
            needFiles = true;
        }

        if (!needFiles) {
            logger.log("Plenty of files for all users. Not needed");
            collection.syncPreloadLock = false;
            return;
        }

        $http({
          method: 'POST',
          url: FmpIpScanner.collection.url+"preloadSync",
          data: JSON.stringify(post_data),
          headers: {
            'Content-Type': "application/json"
          }
        }).then(function successCallback(response) {
            // this callback will be called asynchronously
            // when the response is available'
            logger.log("preload response.data:", response.data);

            if (response.data.STATUS != "OK") {
                logger.log("preload response.data ERROR:", response.data);
                collection.syncPreloadLock = false;
                return;
            }
            var preload = response.data.preload,
                listener_user_ids = collection.FmpListeners.collection.listener_user_ids,
                secondary_user_ids = collection.FmpListeners.collection.secondary_user_ids,
                primary_user_id = collection.FmpListeners.collection.primary_user_id,
                grouped_by_user = {};
            for(var i=0;i<preload.length;i++) {
                var fileData = preload[i];
                var idx = FmpUtils.indexOfFile(collection.FmpPlaylist.collection.files,
                                               fileData);
                delete fileData.image;
                logger.log("preload fileData:", fileData);
                logger.log("primary_user_id:", primary_user_id);
                logger.log("listener_user_ids:", listener_user_ids);
                logger.log("secondary_user_ids:", secondary_user_ids);
                if (fileData.cued) {
                    if (idx != -1 &&
                        !angular.equals(collection.FmpPlaylist.collection.files[idx].spec.cued,
                                        fileData.cued)) {
                        collection.FmpPlaylist.collection.files[idx].spec.cued = fileData.cued;
                        collection.FmpPlaylist.collection.files[idx].save();
                    }
                    var user_id = fileData.cued.user_id;
                    if(typeof grouped_by_user[user_id] == "undefined") {
                        grouped_by_user[user_id] = [];
                    }
                    if (grouped_by_user[user_id].length >= 50) {
                        logger.log("The user has plenty of files ... skipping");
                        continue;
                    }
                    if (grouped_by_user[user_id].indexOf(fileData.id) != -1) {
                        continue;
                    }
                    grouped_by_user[user_id].push(fileData.id);
                    logger.log("grouped_by_user[user_id].length", grouped_by_user[user_id].length);

                    if (listener_user_ids.indexOf(fileData.cued.user_id) == -1 &&
                        secondary_user_ids.indexOf(fileData.cued.user_id) == -1 &&
                        primary_user_id != fileData.cued.user_id) {
                        logger.log("user_id:", user_id, "is not a listener.");
                        if (idx != -1 && !collection.FmpPlaylist.collection.files[idx].playing) {
                            logger.log("Removing file for non listener:",
                                       collection.FmpPlaylist.collection.files[idx]);
                            collection.FmpPlaylist.collection.deleteFile(
                                collection.FmpPlaylist.collection.files[idx]);
                        }
                        continue;
                    }
                }
                if (idx == -1) {
                    var file = new FmpFile(fileData);
                    file.$rootScope = $rootScope;
                    file.$timeout = $timeout;
                    // Put it in a timeout so the file will download in the right order.
                    $timeout(file.download_if_not_exists);
                    logger.log("AddFile:", file);
                    collection.FmpPlaylist.collection.files.push(file);
                    continue;
                }
            }
            collection.syncPreloadLock = false;
        }, function errorCallback(response) {
            // called asynchronously if an error occurs
            // or server returns response with an error status.
            logger.log("preload response.data:", response.data);
            collection.syncPreloadLock = false;
        });
    };

    methods.removeDuplicates = function() {
        var present = [],
            removeIndexes = [];

        for(var i=0;i<collection.FmpPlaylist.collection.files.length;i++) {
            var file = collection.FmpPlaylist.collection.files[i];
            if (present.indexOf(file.id)) {
                removeIndexes.push(file.id);
            } else {
                present.push(file.id);
            }
        }

        removeIndexes.reverse();
        logger.log("REMOVING INDEXES:", removeIndexes);
        for(var i=0;i<removeIndexes.length;i++) {
            var idx = removeIndexes[i];
            collection.FmpPlaylist.collection.files.splice(idx,1);
        }
    };


    methods.syncNext = function() {
        if (collection.syncQue.length == 0) {
            methods.save();
            methods.removeFiles();
            collection.FmpPlaylist.save();
            // logger.log("disabled: methods.syncPreload()");
            methods.syncPreload();
            return;
        }
        var file = collection.syncQue.shift();

        methods.syncFile(file);
    };

    methods.syncFile = function(fileData) {
        if (navigator.connection.type != Connection.WIFI) {
            collection.syncQue = [];
            collection.syncFileLock = false;
            return;
        }
        if (collection.syncFileLock) {
            logger.log("que:", fileData.id);
            collection.syncQue.push(fileData);
            return;
        }
        collection.syncFileLock = true;
        logger.log("collection.FmpListeners.collection:", collection.FmpListeners.collection);
        fileData.user_ids = [];

        if (collection.FmpListeners.collection.listener_user_ids) {
            for(var i=0;i<collection.FmpListeners.collection.listener_user_ids.length;i++) {
                var user_id = collection.FmpListeners.collection.listener_user_ids[i];
                if(fileData.user_ids.indexOf(user_id) == -1) {
                    fileData.user_ids.push(user_id);
                }
            }
        }
        if (collection.FmpListeners.collection.secondary_user_ids) {
            for(var i=0;i<collection.FmpListeners.collection.secondary_user_ids.length;i++) {
                var user_id = collection.FmpListeners.collection.secondary_user_ids[i];
                if(fileData.user_ids.indexOf(user_id) == -1) {
                    fileData.user_ids.push(user_id);
                }
            }
        }

        if (fileData.user_ids.indexOf(collection.FmpListeners.collection.primary_user_id) == -1) {
            fileData.user_ids.push(collection.FmpListeners.collection.primary_user_id);
        }

        // delete file['image'];
        logger.log("syncFile:", fileData);
        if (typeof localStorage["deleted-"+fileData.id] != "undefined") {
            fileData.deleted = true;
        }
        if (typeof fileData.deleted == "undefined") {
            fileData.deleted = false;
        }
        fileData.deviceTimestamp = Date.now() / 1000;
        $http({
          method: 'POST',
          url: FmpIpScanner.collection.url+"fileSync",
          data: JSON.stringify(fileData),
          headers: {
            'Content-Type': "application/json"
          }
        }).then(function successCallback(response) {
            // this callback will be called asynchronously
            // when the response is available
            logger.log("response:", response);
            if (response.data.STATUS == "OK") {
                var result = response.data.result;
                if (typeof localStorage["deleted-"+result.id] != "undefined" ||
                    fileData.deleted) {
                        if (typeof localStorage["deleted-"+result.id] != "undefined") {
                            delete localStorage["deleted-"+result.id];
                        }
                        if (typeof localStorage["file-"+result.id] != "undefined") {
                            delete localStorage["file-"+result.id];
                        }
                        for(var i=0;i<collection.FmpPlaylist.collection.files.length;i++) {
                            var file = collection.FmpPlaylist.collection.files[i];
                            if (file.id != result.id || file.id != fileData.id) {
                                continue;
                            }
                            collection.FmpPlaylist.collection.files.splice(i, 1);
                        }
                        collection.syncFileLock = false;
                        methods.syncNext();
                        return;
                }
                for(var i=0;i<collection.FmpPlaylist.collection.files.length;i++) {
                    var file = collection.FmpPlaylist.collection.files[i];
                    if (file.id != result.id || file.id != fileData.id) {
                        continue;
                    }
                    file.spec.needsSync = false;
                    if (!result.cued && file.spec['played'] &&
                        fileData.removeIfPlayed) {
                            logger.log("will remove:", result.id);
                            collection.filesToRemove.push(result.id);
                    }
                    if (typeof file.image != "undefined") {
                        delete file.image;
                    }
                    if (typeof file.spec.image != "undefined") {
                        delete file.image.spec;
                        file.save();
                    }

                    for (var k in result) {
                        if (k == "image" || k == "reason" || k == 'cued' ||
                            angular.equals(result[k], file.spec[k])) {
                                continue;
                        }
                        if (k == "timestamp") {
                            // Add 1 second because file.spec[k]
                            // is going to be a float.
                            if ((result[k] + 1) < file.spec[k]) {
                                continue;
                            }
                        }
                        logger.log("NA set:",k,"=",result[k]);
                        logger.log("was:",file.spec[k]);
                        file.spec[k] = result[k];
                    } // for (var k in result) {
                    file.save();
                }
            }
            collection.syncFileLock = false;
            methods.syncNext();
        }, function errorCallback(response) {
            // called asynchronously if an error occurs
            // or server returns response with an error status.
            logger.log("response:", response);
            collection.syncFileLock = false;
            fileData.syncing = false;
            methods.syncNext();
        });
    };

    methods.newSync = function(removeIfPlayed) {
        console.log("CALLED newSync");
        if (collection.syncLock) {
            logger.log("syncLock");
            return;
        }
        if (navigator.connection.type != Connection.WIFI) {
            return;
        }

        logger.log("FmpIpScanner.collection.url:", FmpIpScanner.collection.url);
        if (!FmpIpScanner.collection.url) {
            FmpIpScanner.scan();
            return;
        }
        if (!collection.FmpPlaylist.collection.loaded) {
            setTimeout(function(){
                methods.newSync(removeIfPlayed);
            }, 1000);
            return;
        }
        collection.syncLock = true;
        methods.removeDuplicates();
        collection.filesToRemove = [];
        var deletedRx = new RegExp("^deleted\-[\d]+");
        $.each(localStorage, function(key, value){
            if (deletedRx.test(key)) {
                try {
                    var obj = JSON.parse(value);
                    methods.syncFile(obj);
                } catch(e) {
                    console.error(e);
                }
            }
        });
        var files = methods.getPlaylistFiles();
        if (files.length == 0) {
            collection.syncLock = false;
            methods.syncPreload();
            return;
        }
        collection.syncTotal = parseInt(files.length);
        if (typeof removeIfPlayed == "undefined") {
            removeIfPlayed = false;
        }
        $.each(files, function(idx, file){
            file.removeIfPlayed = removeIfPlayed;
            methods.syncFile(file);
        });

        collection.syncLock = false;
    };

    methods.onSocketOpen = function() {
        methods.newSync(false);
    }

    $rootScope.$on("socket-open", methods.onSocketOpen);
    logger.log("initialized");
    return methods;
});
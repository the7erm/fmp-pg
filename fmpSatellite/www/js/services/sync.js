starterServices
.factory('FmpSync', function($rootScope, $http,
                             FmpLocalStorage, FmpUtils, FmpIpScanner,
                             FmpSocket){
    var collection = {
            payload: {},
            transactionIds: [],
            storeFields: {
                "objects": [
                    "payload"
                ]
            },
            FmpPlaylist: null, // Assigned by FmpConductor
            FmpPreload: null   // Assigned by FmpConductor
        },
        methods = {
            collection:collection
        };

    FmpLocalStorage.load(collection);

    methods.cleanPayloadItems = function (payload, depth) {
        console.log("depth:", depth, "payload before:", payload, 'typeof:', typeof payload);
        if (depth == 0) {
            return;
        }
        if (angular.isArray(payload)) {
            for (var i=0;i<payload.length;i++) {
                if (!payload[i] ||
                    angular.equals(payload[i], {}) ||
                    angular.equals(payload[i], [])) {
                    console.log("removing i:", i, "depth:", depth);
                    payload.splice(i,1);
                    i--;
                    continue;
                }
                methods.cleanPayloadItems(payload[i], depth-1);
                if (!payload[i] ||
                    angular.equals(payload[i], {}) ||
                    angular.equals(payload[i], [])) {
                    console.log("removing i:", i, "depth:", depth);
                    payload.splice(i,1);
                    i--;
                }
            }
            return;
        }
        if (typeof payload == 'object') {
            for (var k in payload) {
                console.log("k:",k);
                if (!payload[k] ||
                    angular.equals(payload[k], {}) ||
                    angular.equals(payload[k], [])) {
                    console.log("removing k:", k, "depth:", depth);
                    if (angular.isArray(payload)) {
                        console.log("IS ARRAY");
                        payload.splice(k,1);
                        continue;
                    }
                    delete payload[k];
                    continue;
                }
                methods.cleanPayloadItems(payload[k], depth-1);
                if (!payload[k] ||
                    angular.equals(payload[k], {}) ||
                    angular.equals(payload[k], [])) {
                    console.log("removing k:", k, "depth:", depth);
                    if (angular.isArray(payload)) {
                        console.log("IS ARRAY");
                        payload.splice(k,1);
                        continue;
                    }
                    delete payload[k];
                }
            }
        }

        console.log("payload after:", payload);
    }

    methods.cleanPayload = function() {
        // [day][file_id][elementType][action]
        methods.cleanPayloadItems(collection.payload, 5);
    };

    methods.save = function() {
        methods.cleanPayload();
        FmpLocalStorage.save(collection);
    };

    methods.sync = function () {
        if (!FmpSocket.collection.connected) {
            // We're not connected to the socket so save it.
            methods.save();
            return;
        }
        methods.cleanPayload();
        if (!collection.payload || angular.equals(collection.payload, {})) {
            console.log("!collection.payload");
            return;
        }
        console.log("collection.payload:", collection.payload);
        FmpSocket.send({"action": "sync",
                        "payload": collection.payload});
    }

    methods.removeAction = function (day, file_id, elementType, action, payload) {
        var items = collection.payload[day][file_id][elementType][action];
        console.log("items:", items);
        console.log("payload:", payload);
        if (elementType == 'object') {
            if (angular.equals(items, payload)) {
                console.log("REMOVE PROCESSED ITEM:", items);
                delete collection.payload[day][file_id][elementType][action];
            }
            return;
        }
        if (elementType == 'list') {
            for(var i=0;i<collection.payload[day][file_id][elementType][action].length;i++) {
                var item = collection.payload[day][file_id][elementType][action][i];
                if (angular.equals(item, payload)) {
                    console.log("REMOVE PROCESSED ITEM:", item);
                    delete collection.payload[day][file_id][elementType][action][i];
                }
            }
        }
    };

    methods.removeElementType = function (day, file_id, elementType, payload) {
        for (var action in collection.payload[day][file_id][elementType]) {
            console.log("action:", action);
            methods.removeAction(day, file_id, elementType, action, payload);
        }
    };

    methods.removeFileIdPayload = function(day, file_id, payload) {
        for (var elementType in collection.payload[day][file_id]) {
            console.log("elementType:", elementType);
            methods.removeElementType(day, file_id, elementType, payload);
        }
    };

    methods.removeDayPayload = function(day, payload) {
        // [today][file_id][elementType][action]
        for (var file_id in collection.payload[day]) {
            console.log("file_id:", file_id);
            if (payload.file_id != file_id) {
                console.log("file_id != payload.file_id");
                continue;
            }
            methods.removeFileIdPayload(day, file_id, payload);
        }
    };

    methods.removeSyncedPayload = function(payload) {
        for (var day in collection.payload) {
            console.log("day:", day);
            methods.removeDayPayload(day, payload);
        }
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

    methods.getSyncItem = function(file_id, elementType, action, defaultObject) {
        var today = methods.today();
        if (typeof collection.payload[today][file_id] == 'undefined') {
            collection.payload[today][file_id] = {};
        }
        if (typeof collection.payload[today][file_id][elementType] == 'undefined') {
            collection.payload[today][file_id][elementType] = {};
        }
        if (typeof collection.payload[today][file_id][elementType][action] == 'undefined') {
            collection.payload[today][file_id][elementType][action] = defaultObject;
        }
        return collection.payload[today][file_id][elementType][action]
    };

    methods.markAsPlayed = function(file_id, user_ids, percent_played) {
        var obj = methods.getSyncItem(file_id, 'object', 'mark_as_played', {});
        /*
        {
            "user_ids": [1,2,3,4],
            "percent_played": kwargs.get("percent_played", 0),
            "now": int(kwargs.get("now", time())),
            "file_id": file_id,
            "time": Date.now()
        }
        */
        obj['file_id'] = file_id;
        obj['user_ids'] = user_ids;
        obj['percent_played'] = percent_played;
        obj['time'] = Math.floor(Date.now() / 1000);
        obj['now'] = obj['time'];
        methods.sync();
    };

    methods.set_attr = function (file_id, user_id, attr, value) {
        /*
        {
            "attr": "rating/skip_score",
            "user_id": user_id,
            "value": 0 // 0-5 for rating and -15 to 16 for skip_score
            "file_id": file_id,
            "time": Date.now()
        }

        {
            "user_id": user_id,
            "file_id": file_id,
            "value": True/False,
            "time": Date.now()
        }

        */
        try {
            value = parseInt(value);
        } catch(e) {
            console.error("Error parsing value",e);
            return;
        }

        if (attr == 'rating' && (value < 0 || value > 5)) {
            console.error("Rating out of range:", value);
            return;
        }

        if (attr == 'skip_score' && (value < -16 || value > 16)) {
            console.error("Skip score out of range:", value);
            return;
        }

        if (attr == 'vote_to_skip') {
            if (typeof attr == "string") {
                value = value.toLowerCase();
                if (value == 'off' || value == 'false' || value == '0' || !value ||
                    value == 'null') {
                    value = false;
                }
            }
            if (value) {
                value = true;
            } else {
                value = false;
            }
        }

        var list = methods.getSyncItem(file_id, 'list', attr, []);
        list.push({
            "attr": attr,
            "file_id": file_id,
            "user_id": user_id,
            "value": value,
            "time": Math.floor(Date.now() / 1000)
        });
        methods.sync();
    };

    methods.syncCollections = function() {
        if (!FmpSocket.collection.connected) {
            return;
        }
        var transaction_id = Math.random().toString(36).replace(/[^a-z0-9]+/g, '');
        collection.transactionIds.push(transaction_id);
        var payload = {
            "transaction_id": transaction_id,
            "playlist_ids": [],
            "preload_ids": [],
            "primary_user_id": collection.FmpListeners.collection.primary_user_id,
            "listener_user_ids": collection.FmpListeners.collection.listener_user_ids,
            "secondary_user_ids": collection.FmpListeners.collection.secondary_user_ids,
            "prefetchNum": collection.FmpListeners.collection.prefetchNum,
            "secondaryPrefetchNum": collection.FmpListeners.collection.secondaryPrefetchNum
        };
        for(var i=0;i<collection.FmpPreload.collection.files.length;i++) {
            var file = collection.FmpPreload.collection.files[i];
            payload.preload_ids.push(file.id);
        }
        for(var i=0;i<collection.FmpPlaylist.collection.files.length;i++) {
            var file = collection.FmpPlaylist.collection.files[i];
            payload.playlist_ids.push(file.id);
        }
        FmpSocket.send({"action": "sync-collections",
                        "payload": payload});
    };

    methods.processFileData = function(fileList) {
        fileList = FmpUtils.sanitize(fileList);
        for(var i=0;i<fileList.length;i++) {
            var file = fileList[i];
            FmpUtils.addLocalData(file);
            var idx = FmpUtils.indexOfFile(FmpPlaylist.collection.files);
            if (idx == -1) {
                FmpPreload.collection.files.push(file);
            } else {
                FmpPlaylist[idx].user_file_info = file.user_file_info;
            }
        }
    };

    methods.onPlaylistData = function () {
        methods.processFileData(FmpSocket.collection.playlistData);
    };

    methods.onPreloadData = function() {
        methods.processFileData(FmpSocket.collection.preloadData);
    };

    $rootScope.$on("playlist-data", methods.onPlaylistData);
    $rootScope.$on("preload-data", methods.onPreloadData);

    return methods;
});
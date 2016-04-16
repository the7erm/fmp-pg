fmpApp
.factory('FmpListeners', function($http, $rootScope, FmpConfig,
                                  FmpLocalStorage, FmpSocket){

    var logger = new Logger("FmpListeners", true);

    var collection = {
            fetchLock: false,
            listener_user_ids: [],
            users: [],
            primary_user_id: 0, // user_id
            secondary_user_ids: [],
            prefetchNum: 50,
            secondaryPrefetchNum: 10,
            prefetchSize: -1,
            secondaryPrefetchSize: -1,
            prefetchSizeLimit: 0,
            loaded: false,
            storeFields: {
                "ints": [
                    'primary_user_id',
                    'prefetchNum',
                    'prefetchSize',
                    'secondaryPrefetchNum',
                    'secondaryPrefetchSize',
                ],
                "objects" : [
                    "users",
                    "listener_user_ids",
                    "secondary_user_ids"
                ],
                "strings": [],
                "floats": []
            },
            "ip_addresses": []
        },
        methods = {
            "collection": collection
        };

    methods.load = function() {
        logger.log("LOAD LISTENERS <<<<<<<<<<<<<<<<<<<");
        FmpLocalStorage.load(collection);
        collection.loaded = true;
        logger.log(">>>> LISTENERS LOADED", collection);
    }

    methods.load();

    methods.removeId = function(list, item) {
        var idx = list.indexOf(item);
        if (idx == -1) {
            return;
        }
        list.splice(idx, 1);
    }

    methods.fetch = function() {
        logger.log("FETCHING LISTENERS");
        if (collection.fetchLock) {
            // return;
        }
        collection.fetchLock = true;

        $http({
            method: 'GET',
            url: FmpConfig.url+"ip_addresses"
        }).then(function(response) {
            collection.ip_addresses = response.ip_addresses;
        });

        $http({
            method: 'GET',
            url: FmpConfig.url+"listeners"
        }).then(function(response) {
            logger.log("FETCHED:", response);
            collection.users = response.data;
            if (collection.listener_user_ids.length == 0) {
                var listener_user_ids = [];
                for (var i=0;i<collection.users.length;i++) {
                    var user = collection.users[i];
                    user.listening = false;
                }
                collection.listener_user_ids = listener_user_ids;
            }
            for (var i=0;i<collection.users.length;i++) {
                var user = collection.users[i];
                if (collection.secondary_user_ids.indexOf(user.id) != -1) {
                    user.secondary = true;
                } else {
                    user.secondary = false;
                }
            }
            $rootScope.$broadcast("listeners-loaded");
            collection.fetchLock = false;
            methods.save();
        }, function errorCallback(response) {
            // called asynchronously if an error occurs
            // or server returns response with an error status.
            collection.fetchLock = false;
            logger.log("ERROR FETCHING LISTENERS:", response);
        });
    };

    methods.setPrimaryUserId = function() {
        logger.log("-----------> setPrimaryUser:", collection.primary_user_id);
        localStorage.primary_user_id = collection.primary_user_id;
    };

    methods.setPrimary = function(user_id) {
        console.log("setPrimary:", user_id);
        for (var i=0;i<collection.users.length;i++) {
            var user = collection.users[i];
            if (user.id == user_id) {
                user.primary = true;
                user.secondary = false;
                user.listening = true; // The primary user ALWAYS is listening
                collection.primary_user_id = user.id;
                var idx = collection.secondary_user_ids.indexOf(user.id);
                if (idx != -1) {
                    collection.secondary_user_ids.splice(idx, 1);
                }
                if (collection.listener_user_ids.indexOf(user_id) == -1) {
                    collection.listener_user_ids.push(user_id);
                }
            } else {
                var wasPrimary = false;
                if (user.primary) {
                    // I did this check because I wanted to make sure
                    // the value wasn't linked to user.primary.
                    wasPrimary = true;
                }
                user.primary = false;
                if (wasPrimary) {
                    user.secondary = true;
                    if (collection.secondary_user_ids.indexOf(user_id) == -1) {
                        collection.secondary_user_ids.push(user_id);
                    }
                    if (collection.listener_user_ids.indexOf(user_id) == -1) {
                        collection.listener_user_ids.push(user_id);
                        user.listening = true;
                    }
                }
            }
        }
        methods.save();
    }

    methods.toggle = function(type, user_id) {
        console.log("type:", type, "user_id:", user_id, "forceValue:", forceValue);
        if (["listening", "secondary"].indexOf(type) == -1) {
            return;
        }
        for (var i=0;i<collection.users.length;i++) {
            var user = collection.users[i];
            if (user.id != user_id) {
                continue;
            }
            var obj = collection.listener_user_ids;
            if (type == "secondary") {
                obj = collection.secondary_user_ids;
            }
            user[type] = !user[type];
            var idx = obj.indexOf(user_id);
            if (user[type] && idx == -1) {
                obj.push(idx);
            } else if (!user[type] && idx != -1) {
                obj.splice(idx, 1);
            }
            if (type == "secondary" && !user["secondary"] &&
                user.listening) {
                // The user is not a secondary user yet is still listening.
                methods.toggle("listening", user_id);
                return;
            }
            methods.save();
            break;
        }
    }

    methods.save = function() {
        collection.listener_user_ids = [];
        collection.secondary_user_ids = [];
        var primaryMarked = false;
        for (var i=0;i<collection.users.length;i++) {
            var user = collection.users[i];
            if (!user.secondary && !user.primary) {
                // The user is not a primary or a secondary so they
                // can never be marked listening.
                user.listening = false;
            }
            if (user.primary) {
                if (!primaryMarked) {
                    primaryMarked = true;
                    collection.primary_user_id = user.id;
                    // Primary users are always listening, and they
                    // are never a secondary user.
                    user.listening = true;
                    user.secondary = false;
                } else {
                    // Only allow 1 user to be a primary user
                    // Mark them as the secondary user, and
                    // set them as listening.
                    user.secondary = true;
                    user.listening = true;
                }
            }
            if (user.listening) {
                collection.listener_user_ids.push(user.id);
            }
            if (user.secondary) {
                collection.secondary_user_ids.push(user.id);
            }
        }
        logger.log("SAVE collection:", collection);
        FmpLocalStorage.save(collection);
        logger.log("localStorage:", localStorage);
    };
    methods.updateSecondaryUserIds = function(scope, user_id) {
        logger.log("updateSecondaryUserIds:", scope, user_id);
        if (scope.user.secondary) {
            logger.log("ADD");
            if (typeof collection.secondary_user_ids == "string") {
                collection.secondary_user_ids = collection.secondary_user_ids.split(",");
            }
            if (collection.secondary_user_ids.indexOf(user_id) == -1) {
                collection.secondary_user_ids.push(user_id);
            }
        } else {
            logger.log("remove");
            methods.removeId(collection.secondary_user_ids, user_id);
        }
        collection.secondary_user_ids.sort();
        methods.save();
        logger.log("collection.secondary_user_ids:", collection.secondary_user_ids);
    };

    methods.syncUsers = function() {
        FmpSocket.send({"action": "sync-users"});
    };

    methods.onUserData = function() {
        if (!collection.users) {
            collection.users = [];
        }
        var dirty = false;
        for (var i=0;i<FmpSocket.collection.userData.length;i++) {
            var found = false,
                user1 = FmpSocket.collection.userData[i];
            for (var i2=0;i2<collection.users.length;i2++) {
                var user2 = collection.users[i2];
                if (user1.id == user2.id) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                collection.users.push(user1);
                dirty = true;
            }
        }
        if (dirty) {
            methods.save();
        }
    };

    $rootScope.$on("user-data", methods.onUserData);
    $rootScope.$on("socket-open", methods.syncUsers);

    logger.log("All good");
    return methods;
});
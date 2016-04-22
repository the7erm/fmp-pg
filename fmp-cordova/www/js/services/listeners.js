fmpApp
.factory('FmpListeners', function($http, $rootScope, FmpConfig,
                                  FmpLocalStorage, FmpSocket, FmpIpScanner){

    var logger = new Logger("FmpListeners", true);

    var collectionObj = {
            fetchLock: false,
            listener_user_ids: [],
            users: [],
            session_user_ids: [],
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
                    "session_user_ids",
                    "listener_user_ids",
                    "secondary_user_ids"
                ],
                "strings": [],
                "floats": []
            },
            "ip_addresses": [],
            "_ignore": ["dirty", "storeFields", "loaded", "fetchLock"]
        },
        collection = new Proxy(collectionObj, objHandler),
        methods = {
            "collection": collection
        };

    methods.load = function() {
        logger.log("LOAD LISTENERS <<<<<<<<<<<<<<<<<<<");
        FmpLocalStorage.load(collection);
        collection.loaded = true;
        collection.dirty = false;
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
        if (navigator.connection.type != Connection.WIFI) {
          logger.log("skipping !",Connection.WIFI);
          return;
        }
        if (!FmpIpScanner.collection.url) {
            setTimeout(methods.fetch, 1000);
            return;
        }
        logger.log("FETCHING LISTENERS");
        if (collection.fetchLock) {
            return;
        }
        collection.fetchLock = true;

        $http({
            method: 'GET',
            url: FmpIpScanner.collection.url+"ip_addresses"
        }).then(function(response) {
            collection.ip_addresses = response.ip_addresses;
            methods.save();
        });

        $http({
            method: 'GET',
            url: FmpIpScanner.collection.url+"listeners"
        }).then(function(response) {
            logger.log(FmpIpScanner.collection.url+"listeners", "FETCHED:", response);
            if (!collection.users) {
                collection.users = [];
            }
            var responseUsers = response.data;
            if (!responseUsers) {
                responseUsers = [];
            }
            for(var i=0;i<responseUsers.length;i++) {
                var found = false,
                    rUser = responseUsers[i];
                for (var i2=0;i2<collection.users.length;i2++) {
                    var cUser = collection.users[i2];
                    if (rUser.id == cUser.id) {
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    collection.users.push(rUser);
                    dirty = true;
                }
            }
            methods.save();
            $rootScope.$broadcast("listeners-loaded");
            collection.fetchLock = false;
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
        console.log("type:", type, "user_id:", user_id);
        if (["listening", "secondary"].indexOf(type) == -1) {
            return;
        }
        console.log("toggle collection.users:", collection.users);
        for (var i=0;i<collection.users.length;i++) {
            var user = collection.users[i];
            if (user.id != user_id) {
                continue;
            }
            user[type] = !user[type];
            collection.dirty = true;
            break;
        }
        methods.save();
    }

    methods.save = function() {
        if (!collection.dirty) {
            return;
        }
        session_user_ids = [];
        listener_user_ids = [];
        secondary_user_ids = [];
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
                listener_user_ids.push(user.id);
            }
            if (user.secondary) {
                secondary_user_ids.push(user.id);
            }
            if(user.secondary || user.primary) {
                session_user_ids.push(user.id);
            }
        }
        collection.session_user_ids = session_user_ids;
        collection.listener_user_ids = listener_user_ids;
        collection.secondary_user_ids = secondary_user_ids;

        logger.log("SAVE collection:", collection);
        FmpLocalStorage.save(collection);
        collection.dirty = false;
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
        methods.save();
    };

    // $rootScope.$on("user-data", methods.onUserData);
    // $rootScope.$on("socket-open", methods.syncUsers);
    $rootScope.$on("server-found", methods.fetch);

    return methods;
});
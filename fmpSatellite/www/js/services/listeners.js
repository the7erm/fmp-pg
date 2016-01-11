starterServices
.factory('FmpListeners', function($http, $rootScope, FmpConfig,
                                  FmpLocalStorage){

    var collection = {
            fetchLock: false,
            listener_user_ids: [],
            users: [],
            primary_user_id: 0, // user_id
            secondary_user_ids: [],
            prefetchNum: 50,
            secondaryPrefetchNum: 10,
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
            }
        },
        methods = {
            "collection": collection
        };

    methods.load = function() {
        console.log("LOAD <<<<<<<<<<<<<<<<<<<");
        FmpLocalStorage.load(collection);
        collection.loaded = true;
        console.log(">>>> LOADED", collection);
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
        console.log("FETCHING LISTENERS");
        if (collection.fetchLock) {
            // return;
        }
        collection.fetchLock = true;

        $http({
            method: 'GET',
            url: FmpConfig.url+"listeners"
        }).then(function(response) {
            console.log("FETCHED:", response);
            collection.users = response.data;
            if (collection.listener_user_ids.length == 0) {
                var listener_user_ids = [];
                for (var i=0;i<collection.users.length;i++) {
                    var user = collection.users[i];
                    if (user.listening) {
                        listener_user_ids.push(user.id);
                    }
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
            console.log("ERROR FETCHING LISTENERS:", response);
        });
    };

    methods.setPrimaryUserId = function() {
        console.log("-----------> setPrimaryUser:", collection.primary_user_id);
        localStorage.primary_user_id = collection.primary_user_id;
    };
    methods.save = function() {
        console.log("SAVE collection:", collection);
        FmpLocalStorage.save(collection);
        console.log("localStorage:", localStorage);
    };
    methods.updateSecondaryUserIds = function(scope, user_id) {
        console.log("updateSecondaryUserIds:", scope, user_id);
        if (scope.user.secondary) {
            console.log("ADD");
            if (typeof collection.secondary_user_ids == "string") {
                collection.secondary_user_ids = collection.secondary_user_ids.split(",");
            }
            if (collection.secondary_user_ids.indexOf(user_id) == -1) {
                collection.secondary_user_ids.push(user_id);
            }
        } else {
            console.log("remove");
            methods.removeId(collection.secondary_user_ids, user_id);
        }
        collection.secondary_user_ids.sort();
        methods.save();
        console.log("collection.secondary_user_ids:", collection.secondary_user_ids);
    };



    return methods;
});
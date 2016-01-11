starterServices
.factory('FmpSync', function($ionicPlatform, $rootScope, $http,
                             FmpLocalStorage, FmpUtils, FmpIpScanner,
                             FmpSocket){
    var collection = {
            payload: {},
            storeFields: {
                "objects": [
                    "sync"
                ]
            }
        },
        methods = {
            collection:collection
        };

    FmpLocalStorage.load(collection);

    methods.sync = function () {
        if (!FmpSocket.collection.connected) {
            // We're not connected to the socket so save it.
            FmpLocalStorage.save(collection);
            return;
        }
        FmpSocket.send({"action": "sync",
                        "payload": collection.payload});
    }

    methods.today = function () {
        var today = FmpUtils.today();
        if (typeof collection.payload[today] == 'undefined') {
            collection.payload[today] = {};
        }
        return today;
    }

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
        return collection.payload[today][file_id][elementType][action];
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
        obj['time'] = Date.now() / 1000;
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

        if (attr == 'rating' && (value < 0 || value > 5) {
            console.error("Rating out of range:", value);
            return;
        }

        if (attr == 'skip_score' && (value < -16 || value > 16) {
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
            "time": Date.now() / 1000
        });
        methods.sync();
    }



    return methods;
});
String.prototype.hexEncode = function(){
    var hex, i;

    var result = "";
    for (i=0; i<this.length; i++) {
        hex = this.charCodeAt(i).toString(16);
        result += ("0"+hex).slice(-2);
    }

    return result
};
fmpApp.factory('FmpRemote', function($rootScope, FmpPlaylist){
    var logger = new Logger("FmpRemote", true),
        enabled = false;

    var collection = {
            "clients":[],
            "sockets": {},
            "sents": []
        },
        methods = {
            "collection": collection
        };

    console.log("RemoteController loaded");
    if (typeof networking == "undefined") {
        console.log("networking == undefined")
        return;
    }

    return methods

    logger.log("networking exists:", networking);

    logger.log("networking.bluetooth:", networking.bluetooth);


    collection.discoveryLock = false;
    collection.devices = {};
    collection.uuid = "464d5076-3170-4cdc-9bc6-df14f2a9004c";
    collection.adapterInfo = {
        "enabled": false,
        "name": "",
        "address": "",
        "discovering": false,
        "discoverable": false
    }

    logger.log("1");

    networking.bluetooth.getAdapterState(function (adapterInfo) {
        // The adapterInfo object has the following properties:
        // address: String --> The address of the adapter, in the format 'XX:XX:XX:XX:XX:XX'.
        // name: String --> The human-readable name of the adapter.
        // enabled: Boolean --> Indicates whether or not the adapter is enabled.
        // discovering: Boolean --> Indicates whether or not the adapter is currently discovering.
        // discoverable: Boolean --> Indicates whether or not the adapter is currently discoverable.
        logger.log('getAdapterState Adapter adapterInfo:', adapterInfo);
        collection.adapterInfo = adapterInfo;
    }, function (errorMessage) {
        logger.log("getAdapterState errorMessage:", errorMessage);
    });
    networking.bluetooth.getAdapterState(function (adapterInfo) {
        collection.adapterInfo = adapterInfo;
    });

    logger.log("2");

    networking.bluetooth.onAdapterStateChanged.addListener(function (adapterInfo) {
        // The adapterInfo object has the same properties as getAdapterState
        collection.adapterInfo = adapterInfo;
        if (adapterInfo.enabled !== enabled) {
            enabled = adapterInfo.enabled;
            if (enabled) {
                logger.log('Adapter is enabled');
            } else {
                logger.log('Adapter is disabled');
            }
        }
    });

    logger.log("3");

    /*
    networking.bluetooth.requestEnable(function () {
        // The adapter is now enabled
    }, function () {
        // The user has cancelled the operation
    });
    */

    logger.log("4");

    var updateDeviceName = function (device) {
        collection.devices[device.address] = device;
        if (device.paired) {
            methods.connectToPeer(collection.devices[device.address]);
        }
    };

    logger.log("5");

    // Add listener to receive newly found devices
    networking.bluetooth.onDeviceAdded.addListener(updateDeviceName);

    methods.getDevices = function() {
        // With the listener in place, get the list of known devices
        networking.bluetooth.getDevices(function (devices) {
            for (var i = 0; i < devices.length; i++) {
                updateDeviceName(devices[i]);
            }
        });
    };


    logger.log("6");

    methods.startDiscovery = function() {
        if (collection.discoveryLock) {
            return;
        }
        collection.discoveryLock = true;
        // Now begin the discovery process.
        networking.bluetooth.startDiscovery(function () {
            // Stop discovery after 30 seconds.
            setTimeout(function () {
                collection.discoveryLock = false;
                networking.bluetooth.stopDiscovery();
            }, 30000);
        });
    }

    methods.requestDiscoverable = function() {
        networking.bluetooth.requestDiscoverable(function () {
            // The device is now discoverable
        }, function () {
            // The user has cancelled the operation
        });
    }

    methods.connectToPeer = function(device) {
        logger.log("connectToPeer:", device);
        networking.bluetooth.connect(device.address, collection.uuid, function (socketId) {
            // Profile implementation here.
            // collection.socketId = socketId;
            // methods.getDevices();
            console.log("connected:", device, socketId);
            collection.sockets[device.address] = socketId;
            collection.clients.push(socketId);
            $rootScope.$broadcast("client-connect");
        }, function (errorMessage) {
            logger.log('Connection failed: ' + errorMessage);
            if (typeof collection.sockets[device.address] != "undefined") {
                // delete collection.sockets[device.address];
            }
        });
    }

    var ab2str = function (buf) {
      return String.fromCharCode.apply(null, new Uint16Array(buf));
    }
    var str2ab = function (str) {
      var buf = new ArrayBuffer(str.length*2); // 2 bytes for each char
      var bufView = new Uint16Array(buf);
      var strLen = str.length;
      for (var i=0;i < strLen; i++) {
        bufView[i] = str.charCodeAt(i);
      }
      return buf;
    }

    methods.sendData = function(txt) {
        logger.log("sendData:", txt);
        var b64 = btoa(JSON.stringify(txt)),
            arrayBuffer = str2ab(b64);

        try {
            var s = ab2str(arrayBuffer);
        } catch(e) {
            console.error("unable to decode:",e, txt);
            return;
        }

        logger.log("arrayBuffer:", arrayBuffer);

        $.each(collection.clients, function(i, socketId){
            logger.log("send socketId:", socketId, "txt:", txt);
            networking.bluetooth.send(socketId, arrayBuffer, function(bytes_sent) {
                logger.log('Sent ' + bytes_sent + ' bytes');
                // collection.sents.push('Sent ' + bytes_sent + ' bytes');
            }, function (errorMessage) {
                logger.log('Send failed: ' + errorMessage);
                collection.sents.push('Send failed: ' + errorMessage);
                var idx = collection.clients.indexOf(socketId);
                if (idx != -1) {
                    collection.clients.splice(idx,1);
                }
            });
        });
    }


    methods.sendTest = function() {
        methods.sendData({"HELLO": collection.adapterInfo,
                          "time": new Date()});
    }
    logger.log("7");

    var onReceive = function (receiveInfo) {
        logger.log("onReceive receiveInfo:", receiveInfo);
        collection.receiveInfo = receiveInfo;
        // receiveInfo.data is an ArrayBuffer.
        var b64 = ab2str(receiveInfo.data),
            txt = atob(b64),
            obj = JSON.parse(txt);
        collection.decodedRecieveData = obj;
        $rootScope.$broadcast("bluetooth-receive", obj);
        if (obj.cmd && obj.cmd == "next") {
            FmpPlaylist.next();
            return;
        }
        if (obj.cmd && obj.cmd == "pause") {
            window.player.pause();
            return;
        }
        if (obj.cmd && obj.cmd == "prev") {
            FmpPlaylist.prev();
            return;
        }
    };

    methods.pause = function() {
        methods.sendData({"cmd":"pause"});
    };

    methods.prev = function() {
        methods.sendData({"cmd":"prev"});
    };

    methods.next = function() {
        methods.sendData({"cmd":"next"});
    };

    $rootScope.$on("time-status", function(scope, file){
        console.log("time-status scope:", scope, "file:", file);
        return;
        if (typeof file.spec != "undefined") {
            methods.sendData({"time-status": file.spec});
            return;
        }
        methods.sendData({"time-status": file});
    });

    networking.bluetooth.onReceive.addListener(onReceive);

    logger.log("8");
    networking.bluetooth.onReceiveError.addListener(function (errorInfo) {
        // Cause is in errorInfo.errorMessage.
        logger.log(errorInfo);
    });

    logger.log("9");
    networking.bluetooth.listenUsingRfcomm(collection.uuid, function (serverSocketId) {
        collection.serverSocketId = serverSocketId;
        // Keep a handle to the serverSocketId so that you can later accept connections (onAccept) from this socket.
    }, function (errorMessage) {
        console.error(errorMessage);
    });

    logger.log("10");
    networking.bluetooth.onAccept.addListener(function (acceptInfo) {
        console.log("onAccept:",acceptInfo);
        collection.onAccept = {
            "acceptInfo": acceptInfo
        };
        collection.clients.push(acceptInfo.clientSocketId);
        networking.bluetooth.onReceive.addListener(onReceive);
    });

    methods.getDevices();

    return methods;
});
String.prototype.hexEncode = function(){
    var hex, i;

    var result = "";
    for (i=0; i<this.length; i++) {
        hex = this.charCodeAt(i).toString(16);
        result += ("0"+hex).slice(-2);
    }

    return result
};

fmpApp.controller('RemoteController', function ($scope, $rootScope) {
    var logger = new Logger("RemoteController", true),
        enabled = false;

    console.log("RemoteController loaded");
    if (typeof networking == "undefined") {
        console.log("networking == undefined")
        return;
    }

    logger.log("networking exists:", networking);

    logger.log("networking.bluetooth:", networking.bluetooth);


    $scope.discoveryLock = false;
    $scope.devices = {};
    $scope.uuid = "464d5076-3170-4cdc-9bc6-df14f2a9004c";
    $scope.adapterInfo = {
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
        logger.log('Adapter ' + adapterInfo.address + ': ' + adapterInfo.name);
        $scope.adapterInfo = adapterInfo;
    }, function (errorMessage) {
        logger.error(errorMessage);
    });
    networking.bluetooth.getAdapterState(function (adapterInfo) {
        $scope.adapterInfo = adapterInfo;
    });

    logger.log("2");

    networking.bluetooth.onAdapterStateChanged.addListener(function (adapterInfo) {
        // The adapterInfo object has the same properties as getAdapterState
        $scope.adapterInfo = adapterInfo;
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

    networking.bluetooth.getDevices(function (devices) {
        for (var i = 0; i < devices.length; i++) {
            // The deviceInfo object has the following properties:
            // address: String --> The address of the device, in the format 'XX:XX:XX:XX:XX:XX'.
            // name: String --> The human-readable name of the device.
            // paired: Boolean --> Indicates whether or not the device is paired with the system.
            // uuids: Array of String --> UUIDs of protocols, profiles and services advertised by the device.
            logger.log(devices[i].address);
        }
    });


    var updateDeviceName = function (device) {
        $scope.devices[device.address] = device;
    };

    logger.log("5");

    // Add listener to receive newly found devices
    networking.bluetooth.onDeviceAdded.addListener(updateDeviceName);

    // With the listener in place, get the list of known devices
    networking.bluetooth.getDevices(function (devices) {
        for (var i = 0; i < devices.length; i++) {
            updateDeviceName(devices[i]);
        }
    });

    logger.log("6");

    $scope.startDiscovery = function() {
        if ($scope.discoveryLock) {
            return;
        }
        $scope.discoveryLock = true;
        // Now begin the discovery process.
        networking.bluetooth.startDiscovery(function () {
            // Stop discovery after 30 seconds.
            setTimeout(function () {
                $scope.discoveryLock = false;
                networking.bluetooth.stopDiscovery();
            }, 30000);
        });
    }

    $scope.requestDiscoverable = function() {
        networking.bluetooth.requestDiscoverable(function () {
            // The device is now discoverable
        }, function () {
            // The user has cancelled the operation
        });
    }

    $scope.connectToPeer = function(device) {
        logger.log("connectToPeer:", device);
        networking.bluetooth.connect(device.address, $scope.uuid, function (socketId) {
            // Profile implementation here.
            $scope.socketId = socketId;
        }, function (errorMessage) {
            logger.log('Connection failed: ' + errorMessage);
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

    $scope.sendData = function(txt) {
        logger.log("sendData:", txt);
        var socketId = $scope.acceptInfo.clientSocketId,
            b64 = btoa(JSON.stringify(txt)),
            arrayBuffer = str2ab(b64);

        logger.log("socketId:", socketId);
        logger.log("arrayBuffer:", arrayBuffer);

        networking.bluetooth.send(socketId, arrayBuffer, function(bytes_sent) {
            logger.log('Sent ' + bytes_sent + ' bytes');
        }, function (errorMessage) {
            logger.log('Send failed: ' + errorMessage);
        });
    }


    $scope.sendTest = function() {
        $scope.sendData({"HELLO": $scope.adapterInfo});
    }
    logger.log("7");

    var onReceive = function (receiveInfo) {
        $scope.receiveInfo = receiveInfo;
        // receiveInfo.data is an ArrayBuffer.
        var b64 = ab2str(receiveInfo.data),
            txt = atob(b64),
            obj = JSON.parse(txt);
        $scope.decodedRecieveData = obj;
    };

    networking.bluetooth.onReceive.addListener(onReceive);

    logger.log("8");
    networking.bluetooth.onReceiveError.addListener(function (errorInfo) {
        // Cause is in errorInfo.errorMessage.
        logger.log(errorInfo);
    });

    logger.log("9");
    networking.bluetooth.listenUsingRfcomm($scope.uuid, function (serverSocketId) {
        $scope.serverSocketId = serverSocketId;
        // Keep a handle to the serverSocketId so that you can later accept connections (onAccept) from this socket.
    }, function (errorMessage) {
        console.error(errorMessage);
    });

    logger.log("10");
    networking.bluetooth.onAccept.addListener(function (acceptInfo) {
        if (acceptInfo.socketId !== $scope.serverSocketId) {
            return;
        }
        $scope.acceptInfo = acceptInfo;

        // Set the onReceive listener
        networking.bluetooth.onReceive.addListener(onReceive);
    });

});
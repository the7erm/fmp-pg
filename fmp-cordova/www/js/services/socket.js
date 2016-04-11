fmpApp.factory('FmpSocket', function($websocket, FmpIpScanner, $rootScope,
                                     FmpUtils) {
  // Open a WebSocket connection

  var collection = {
    dataStream: false,
    connected: false,
    queue: [],
    processed: [],
    playlistData: [],
    preloadData: [],
    userData: [],
    connectionLock: false,
    hasError: false
  };

  var methods = {
    collection: collection,
    send: function(obj) {
      if (angular.equals(obj,{})) {
        console.error("empty sync object:", obj);
        return;
      }
      if (collection.dataStream && navigator.connection.type == "wifi") {
        while (collection.queue.length>0) {
          var msg = collection.queue.shift();
          console.log("SEND queued:", msg);
          collection.dataStream.send(JSON.stringify(msg));
        }
        console.log("SEND:", obj);
        collection.dataStream.send(JSON.stringify(obj));
      } else {
        console.log("SEND deferred:", obj);
        collection.queue.push(obj);
      }
    },
    onMessage: function(message) {
      collection.connected = true;
      var data = JSON.parse(message.data);
      if (typeof data['time-status'] == 'undefined') {
        console.log("onMessage:", data);
        if (typeof data['processed'] != 'undefined') {
          collection.processed.push(data);
          $rootScope.$broadcast("sync-processed");
        }
        if (typeof data.playlist != 'undefined') {
          collection.playlistData = data.playlist;
          $rootScope.$broadcast("playlist-data");
        }
        if (typeof data.preload != 'undefined') {
          collection.preloadData = data.preload;
          $rootScope.$broadcast("preload-data");
        }
        if (typeof data["playlist-item"] != "undefined") {
          if (FmpUtils.indexOfFile(collection.preloadData, data['playlist-item']) == -1) {
            collection.playlistData.push(data['playlist-item']);
            $rootScope.$broadcast("playlist-data");
          }
        }
        if (typeof data["preload-item"] != "undefined") {
          if (FmpUtils.indexOfFile(collection.preloadData, data['preload-item']) == -1) {
            collection.preloadData.push(data['preload-item']);
            $rootScope.$broadcast("preload-data");
          }
        }
        if (typeof data.users != 'undefined') {
          collection.userData = data.users;
          $rootScope.$broadcast("user-data");
        }
      }
    },
    onError: function() {
      collection.connected = false;
      collection.connectionLock = false;
      collection.hasError = true;
      console.error("socket onError:", arguments);
      console.log("waiting 10 seconds to reconnect");
      setTimeout(methods.connect, 10000);
    },
    onOpen: function() {
      collection.connected = true;
      collection.connectionLock = false;
      collection.hasError = false;
      console.log("socket onOpen:", arguments);
      $rootScope.$broadcast("socket-open");
    },
    onClose: function() {
      collection.connected = false;
      collection.connectionLock = false;
      console.log("socket onClose:", arguments);
      if (!collection.hasError) {
        setTimeout(methods.connect, 5000);
      }
      FmpIpScanner.collection.socketUrl = null;
    }
  };

  methods.connect = function() {
    if (collection.connectionLock || collection.connected) {
      // Don't run if we are already connected or in the process of
      // connecting.
      return;
    }
    collection.connectionLock = true;
    console.log("connecting to socket");
    if (collection.dataStream) {
      if (collection.connected) {
        collection.dataStream.close();
      }
      collection.dataStream = false;
    }
    collection.hasError = false;
    collection.dataStream = $websocket(FmpIpScanner.collection.socketUrl);
    collection.dataStream.onOpen(methods.onOpen);
    collection.dataStream.onMessage(methods.onMessage);
    collection.dataStream.onError(methods.onError);
    collection.dataStream.onClose(methods.onClose);
  };

  $rootScope.$on("server-found", methods.connect);

  return methods;
});
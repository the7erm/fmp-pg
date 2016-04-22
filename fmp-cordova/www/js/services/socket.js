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

  var logger = new Logger("FmpSocket", true);
  var methods = {
    collection: collection,
    send: function(obj) {
      logger.log("deprecated send()");
      return;
      if (angular.equals(obj,{})) {
        console.error("empty sync object:", obj);
        return;
      }
      if (collection.connected && collection.dataStream && navigator.connection.type == "wifi") {
        while (collection.queue.length>0) {
          var msg = collection.queue.shift();
          logger.log("SEND queued:", msg);
          collection.dataStream.send(JSON.stringify(msg));
        }
        logger.log("SEND:", obj);
        collection.dataStream.send(JSON.stringify(obj));
      } else {
        logger.log("SEND deferred:", obj);
        collection.queue.push(obj);
      }
    },
    onMessage: function(message) {
      logger.log("deprecated onMessage()");
      return;
      collection.connected = true;
      collection.connectionLock = false;
      collection.hasError = false;
      try {
        var data = JSON.parse(message.data);
      } catch (e) {
        console.error("var data = JSON.parse(message.data):",e);
        return;
      }
      if (typeof data['time-status'] == 'undefined') {
        logger.log("onMessage:", data);
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
    onError: function(arg1, arg2) {
      logger.log("deprecated onError()");
      return;
      collection.connected = false;
      collection.connectionLock = false;
      collection.hasError = true;
      console.error("socket onError:", arg1, arg2);
      logger.log("waiting 10 seconds to reconnect");
      collection.dataStream.close();
      setTimeout(methods.connect, 10000);
    },
    onOpen: function() {
      logger.log("deprecated onOpen()");
      return;
      collection.connected = true;
      collection.connectionLock = false;
      collection.hasError = false;
      logger.log("socket onOpen:", arguments);
      $rootScope.$broadcast("socket-open");
    },
    onClose: function() {
      logger.log("deprecated onClose()");
      return;
      collection.connected = false;
      collection.connectionLock = false;
      logger.log("socket onClose:", arguments);
      if (!collection.hasError) {
        setTimeout(methods.connect, 5000);
      }
      FmpIpScanner.collection.socketUrl = null;
    }
  };

  methods.connect = function() {
    logger.log("deprecated connect()");
    return;
    if (collection.connectionLock || collection.connected) {
      // Don't run if we are already connected or in the process of
      // connecting.
      logger.log("!connect collection.connectionLock:",
                  collection.connectionLock,
                  "collection.connected:", collection.connected)
      return;
    }
    collection.connectionLock = true;
    logger.log("connecting to socket");
    if (collection.dataStream) {
      if (collection.connected) {
        try {
          collection.dataStream.close();

        } catch(e) {
          console.error("collection.dataStream.close():", e);
        }
      }
      collection.dataStream = false;
    }
    collection.hasError = false;
    logger.log("FmpIpScanner.collection.socketUrl:", FmpIpScanner.collection.socketUrl);
    if (!FmpIpScanner.collection.socketUrl) {
        FmpIpScanner.startScan();
        collection.connectionLock = false;
        return;
    }
    collection.dataStream = $websocket(FmpIpScanner.collection.socketUrl);
    collection.dataStream.onOpen(methods.onOpen);
    collection.dataStream.onMessage(methods.onMessage);
    collection.dataStream.onError(methods.onError);
    collection.dataStream.onClose(methods.onClose);
  };

  // $rootScope.$on("server-found", methods.connect);
  logger.log("initialized - deprecated");
  return methods;
});
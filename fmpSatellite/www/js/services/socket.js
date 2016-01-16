starterServices.factory('FmpSocket', function($websocket, FmpIpScanner,
                                              $rootScope) {
  // Open a WebSocket connection

  var collection = {
    dataStream: false,
    connected: false,
    queue: [],
    processed: [],
    playlistData: [],
    preloadData: []
  };

  var methods = {
    collection: collection,
    send: function(obj) {
      if (collection.dataStream) {
        while (collection.queue.length>0) {
          var msg = queue.shift();
          console.log("SEND:", msg);
          collection.dataStream.send(JSON.stringify(msg));
        }
        console.log("SEND:", obj);
        collection.dataStream.send(JSON.stringify(obj));
      } else {
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
          playlistData = data.playlist;
          $rootScope.$broadcast("playlist-data");
        }
        if (typeof data.preload != 'undefined') {
          preloadData = data.preload;
          $rootScope.$broadcast("preload-data");
        }
      }
    },
    onError: function() {
      collection.connected = false;
      console.error("socket onError:", arguments);
    },
    onOpen: function() {
      collection.connected = true;
      console.log("onOpen:", arguments);
    },
    onClose: function() {
      collection.connected = false;
      console.log("onClose:", arguments);
    }
  };

  methods.connect = function() {
    if (collection.dataStream) {
      collection.dataStream.close();
      collection.dataStream = false;
    }
    collection.dataStream = $websocket(FmpIpScanner.collection.socketUrl);
    collection.dataStream.onOpen(methods.onOpen);
    collection.dataStream.onMessage(methods.onMessage);
    collection.dataStream.onError(methods.onClose);
    collection.dataStream.onClose(methods.onClose);
  };

  $rootScope.$on("server-found", methods.connect);

  return methods;
});
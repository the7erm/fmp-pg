starterServices
.factory('OldPlayer', function($http, $cordovaFileTransfer, $cordovaFile,
                               $ionicPlatform, $timeout){
  /****************************  ****/
  var collection = {
          url: 'http://192.168.1.117:5050',
          playlist: [],
          preload: [],
          preloadDict: {},
          idx:0,
          media: null,
          time_status: "",
          restored: false,
          initPreloadLocked: false,
          resumePosition: 0,
          remaining: -1000,
          uids: [],
          cacheDir: null,
          cacheDirEntries: [],
          preloadLock: false
      },
      methods = {
          collection: collection
      };



  methods.processCacheDir = function(entries) {
    console.log("methods.processCacheDir entries:", entries);
    collection.cacheDirEntries = entries;
    /*
      TODO:
        - loop through preload
        - loop through playlist
    */
  };

  methods.onError = function() {
      console.log("onError:", arguments);
  };

  methods.onComplete = function() {
    console.log("onComplete:", arguments);
  };

  methods.onStatusChange = function(playerStatus) {
    console.log("onStatusChange:", playerStatus);
  };



  methods.setIndex = function(idx) {
    console.log("methods.setIndex()");
    var src = null;
    if (typeof idx == 'undefined') {
        if (methods.isEmpty(collection.playlist)) {
          console.log("playlist is empty");
          return false;
        }
    }
    if (typeof collection.playlist[idx] == 'undefined') {
        console.log("collection.playlist["+idx+"] is undefined");
        return false;
    }
    src = collection.playlist[idx].filename;
    collection.media = new Media(src,
                                 methods.onComplete,
                                 methods.onError,
                                 methods.onStatusChange);

  }

  methods.play = function() {
    console.log("methods.play()", arguments);
    if (collection.media == null) {
      methods.setIndex();
      if (collection.media == null) {
          console.log("unable to set playlist index");
          methods.fetchPreload({
            "download": [{
                "success": methods.play
            }]
          });
          return;
      }
    }
    collection.media.play();
  };

  $ionicPlatform.ready(function() {
    // fetchPreload
    methods.play();
    methods.fetchPreload();

    // clean cache.
    collection.cacheDir = cordova.file.externalCacheDirectory;
    methods.listDir(collection.cacheDir, methods.processCacheDir);
  });

  return methods;
})
.factory('Chats', function() {
  // Might use a resource here that returns a JSON array

  // Some fake testing data
  var chats = [];

  return {
    all: function() {
      return chats;
    },
    remove: function(chat) {
      chats.splice(chats.indexOf(chat), 1);
    },
    get: function(chatId) {
      for (var i = 0; i < chats.length; i++) {
        if (chats[i].id === parseInt(chatId)) {
          return chats[i];
        }
      }
      return null;
    }
  };
});

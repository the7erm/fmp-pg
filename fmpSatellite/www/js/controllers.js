angular.module('starter.controllers', ['ionic', 'ngCordova',
                                       'starter.controllers',
                                       'starter.services',
                                       'ionic.rating'])

.controller('PlayerCtrl', function($scope, $ionicPlatform, FmpConductor,
                                   FmpConstants) {
  $ionicPlatform.ready(function() {
    var FmpPlayer = FmpConductor.collection.FmpPlayer,
        FmpDownloader = FmpConductor.collection.FmpDownloader,
        FmpPlaylist = FmpConductor.collection.FmpPlaylist,
        FmpUtils = FmpConductor.collection.FmpUtils;

    $scope.next = function(){
      FmpPlaylist.setIndex("+1");
    };
    $scope.prev = function(){
      FmpPlaylist.setIndex("-1");
    };

    $scope.pause = function() {
      FmpPlayer.pause();
      $scope.playerState = FmpPlayer.collection.playerState;
    };
    $scope.sync = function() {
      FmpConductor.sync();
    }
    $scope.FmpConstants = FmpConstants;
    $scope.FmpDownloader = FmpDownloader;
    $scope.downloading = FmpDownloader.collection.downloading;
    $scope.position = "0:00";
    $scope.duration = "0:00";
    $scope.remaining = "0:00";
    $scope.file = FmpPlaylist.collection.playing;
    $scope.state = FmpPlayer.collection.desiredState;

    $scope.$on("index-changed", function(){
        console.log("+++++++ index-changed", FmpPlaylist.collection.playing);
        $scope.file = FmpPlaylist.collection.playing;
    });

    $scope.$on("playing-data-changed", function(){
      console.log("+++++++ playing-data-changed", FmpPlaylist.collection.playing);
      $scope.file = FmpPlaylist.collection.playing;
    });

    $scope.$on("time-status", function(){
      $scope.position = FmpUtils.formatTime(FmpPlayer.collection.position);
      $scope.duration = FmpUtils.formatTime(FmpPlayer.collection.duration);
      $scope.remaining = FmpUtils.formatTime(FmpPlayer.collection.remaining);
      $scope.$apply();
    });

    $scope.$watch("FmpDownloader.collection.downloading", function(newValue, oldValue, scope){
      scope.downloading = FmpDownloader.collection.downloading;
    });

    $scope.$on("synced", function(){
      $scope.syncTime = FmpConductor.collection.syncTime;
    });

    $scope.syncTime = FmpConductor.collection.syncTime;
    $scope.setRating = FmpConductor.setRating;

    $scope.ratingStates = FmpConductor.stars;

  });
})

.controller('ListenerCtrl', function($scope, FmpConductor){
  $scope.users = FmpConductor.collection.FmpListeners.collection.users;
  $scope.FmpListeners = FmpConductor.collection.FmpListeners;
  $scope.sync = FmpConductor.sync;

  $scope.$on("listeners-loaded", function(){
    $scope.users = FmpConductor.collection.FmpListeners.collection.users;
  });
  $scope.$watch("users", function(newValue, oldValue, scope){
    console.log("USER NEW VALUE:", newValue);
  });
  $scope.updateUids = function(){
    var user_ids = [];
    for(var i=0;i<FmpConductor.collection.FmpListeners.collection.users.length;i++) {
      var user = FmpConductor.collection.FmpListeners.collection.users[i];
      if (user.listening) {
        user_ids.push(user.id);
      }
    }
    if (user_ids.indexOf(FmpConductor.collection.FmpListeners.collection.primary_user_id) == -1) {
      user_ids.push(FmpConductor.collection.FmpListeners.collection.primary_user_id);
    }
    console.log("USER IDS:", user_ids);
    FmpConductor.collection.FmpListeners.collection.secondary_user_ids = user_ids;
    FmpConductor.collection.FmpListeners.save();
  };

  $scope.updateSecondaryUserIds = FmpConductor.collection.FmpListeners.updateSecondaryUserIds;
  $scope.setPrimaryUserId = FmpConductor.collection.FmpListeners.setPrimaryUserId;
})
.controller("PlaylistCtrl", function($ionicPosition, $ionicScrollDelegate,
                                     $scope, FmpConductor, $timeout){
  console.log("PlaylistCtrl LOADED");
  $scope.shouldShowReorder = true;
  $scope.gotoAnchor = function(x) {
    var newHash = 'anchor' + x;
    console.log("gotoAnchor:", newHash);
    var pos = $ionicPosition.position(angular.element(document.getElementById(newHash)));
    console.log("POS:", pos);
    $ionicScrollDelegate.scrollTo(pos.left, pos.top-25);
  };
  $scope.loading = true;
  $scope.$on("preload-changed", function(){
    $scope.preload = FmpConductor.collection.FmpPreload.collection.files;
    $scope.playlist = FmpConductor.collection.FmpPlaylist.collection.files;
    $scope.playing = FmpConductor.collection.FmpPlaylist.collection.playing;
  });
  $scope.$on("media-set", function(){
    $scope.preload = FmpConductor.collection.FmpPreload.collection.files;
    $scope.playlist = FmpConductor.collection.FmpPlaylist.collection.files;
    $scope.playing = FmpConductor.collection.FmpPlaylist.collection.playing;
  });

  $scope.$on("playlist-changed", function(){
    $scope.preload = FmpConductor.collection.FmpPreload.collection.files;
    $scope.playlist = FmpConductor.collection.FmpPlaylist.collection.files;
    $scope.playing = FmpConductor.collection.FmpPlaylist.collection.playing;
  });

  $scope.moveItem = function(item, fromIndex, toIndex) {
    console.log("moveItem:", {
      "item": item,
      "fromIndex": fromIndex,
      "toIndex": toIndex
    });
    var item = $scope.playlist[fromIndex];
    $scope.playlist.splice(fromIndex, 1);
    $scope.playlist.splice(toIndex, 0, item);
  };

  $scope.playFile = FmpConductor.collection.FmpPlaylist.playFile;

  $scope.setRating = FmpConductor.setRating;
  $scope.ratingStates = FmpConductor.stars;

  $timeout(function(){
    $scope.preload = FmpConductor.collection.FmpPreload.collection.files;
    $scope.playlist = FmpConductor.collection.FmpPlaylist.collection.files;
    $scope.playing = FmpConductor.collection.FmpPlaylist.collection.playing;
    $timeout(function(){
      $scope.loading = false;
      $scope.gotoAnchor($scope.playing.id);
    });
  }, 100);
})
.controller('ChatsCtrl', function($scope, Chats) {
  // With the new view caching in Ionic, Controllers are only called
  // when they are recreated or on app start, instead of every page change.
  // To listen for when this page is active (for example, to refresh data),
  // listen for the $ionicView.enter event:
  //
  //$scope.$on('$ionicView.enter', function(e) {
  //});

  $scope.chats = Chats.all();
  $scope.remove = function(chat) {
    Chats.remove(chat);
  };
})

.controller('ChatDetailCtrl', function($scope, $stateParams, Chats) {
  $scope.chat = Chats.get($stateParams.chatId);
})
.controller('AccountCtrl', function($scope) {
  $scope.settings = {
    enableFriends: true
  };
});

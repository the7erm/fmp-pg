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
      $scope.playing = FmpPlaylist.collection.playing;

    });

    $scope.$on("time-status", function(){
      $scope.position = FmpUtils.formatTime(FmpPlayer.collection.position);
      $scope.duration = FmpUtils.formatTime(FmpPlayer.collection.duration);
      $scope.remaining = FmpUtils.formatTime(FmpPlayer.collection.remaining);
      $scope.$apply();
    });

    $scope.$on("download-progress", function () {
      $scope.downloading = FmpDownloader.collection.downloading;
      $scope.$apply();
    });

    $scope.setRating = FmpConductor.setRating;

    $scope.ratingStates = FmpConductor.stars;

  });
})

.controller('ListenerCtrl', function($scope, FmpConductor){
  $scope.users = FmpConductor.collection.FmpListeners.collection.users;
  $scope.$on("listeners-loaded", function(){
    $scope.users = FmpConductor.collection.FmpListeners.collection.users;
  });
  $scope.updateUids = function(){
    var user_ids = [];
    for(var i=0;i<$scope.users.length;i++) {
      var user = $scope.users[i];
      if (user.listening) {
        user_ids.push(user.id);
      }
    }
    FmpConductor.collection.FmpListeners.collection.user_ids = user_ids;
    FmpConductor.collection.FmpListeners.save();
  };
})
.controller("PlaylistCtrl", function($location, $anchorScroll, $scope, FmpConductor){
  $scope.gotoAnchor = function(x) {
    var newHash = 'anchor-' + x;
    $location.hash('anchor-' + x);
    console.log("gotoAnchor:", x);
    if ($location.hash() !== newHash) {
      // set the $location.hash to `newHash` and
      // $anchorScroll will automatically scroll to it

      console.log("$location.hash()");
    } else {
      // call $anchorScroll() explicitly,
      // since $location.hash hasn't changed
      $anchorScroll();
      console.log("$anchorScroll()");
    }
  };
  $scope.preload = FmpConductor.collection.FmpPreload.collection.files;
  $scope.playlist = FmpConductor.collection.FmpPlaylist.collection.files;
  $scope.playing = FmpConductor.collection.FmpPlaylist.collection.playing;
  $scope.gotoAnchor($scope.playing.id);
  $scope.$on("preload-changed", function(){
    $scope.preload = FmpConductor.collection.FmpPreload.collection.files;
    $scope.playlist = FmpConductor.collection.FmpPlaylist.collection.files;
    $scope.playing = FmpConductor.collection.FmpPlaylist.collection.playing;
    $scope.gotoAnchor($scope.playing.id);
  });
  $scope.$on("media-set", function(){
    $scope.preload = FmpConductor.collection.FmpPreload.collection.files;
    $scope.playlist = FmpConductor.collection.FmpPlaylist.collection.files;
    $scope.playing = FmpConductor.collection.FmpPlaylist.collection.playing;
    $scope.gotoAnchor($scope.playing.id);
  });

  $scope.setRating = FmpConductor.setRating;
  $scope.ratingStates = FmpConductor.stars;
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

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
    $scope.playing = FmpPlaylist.collection.playing;
    $scope.state = FmpPlayer.collection.desiredState;

    $scope.$on("index-changed", function(){
        console.log("+++++++ index-changed", FmpPlaylist.collection.playing);
        $scope.playing = FmpPlaylist.collection.playing;
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

    $scope.setRating = function(ufi) {
      console.log("setRating:", ufi);
      if (typeof ufi.satellite_history == 'undefined') {
        ufi.satellite_history = {};
      }

      if (typeof ufi.satellite_history == 'undefined') {
        ufi.satellite_history = {};
      }

      FmpUtils.calculateTrueScore(ufi);

      FmpUtils.updateHistory(ufi, {
        "rating": ufi.rating,
        "skip_score": ufi.skip_score,
        "true_score": ufi.true_score
      });

    };

    $scope.ratingStates = [
      {stateOn: 'red-no', stateOff: 'grey-no'},
      {stateOn: 'yellow-star', stateOff: 'grey-star'},
      {stateOn: 'yellow-star', stateOff: 'grey-star'},
      {stateOn: 'yellow-star', stateOff: 'grey-star'},
      {stateOn: 'yellow-star', stateOff: 'grey-star'},
      {stateOn: 'yellow-star', stateOff: 'grey-star'},
      {stateOn: 'question-mark-on', stateOff: 'question-mark-off'}
    ];

  });
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

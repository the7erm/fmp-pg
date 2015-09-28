angular.module('fmpApp', [
    'ngWebSocket', // you may also use 'angular-websocket' if you prefer
    'ui.bootstrap'
  ])
  .factory('PlayerData', function($websocket) {
    console.log("OPENING SOCKET")
    // Open a WebSocket connection
    var dataStream = $websocket('ws://localhost:5050/ws');

    var collection = {

    };

    dataStream.onMessage(function(message) {
      var obj = JSON.parse(message.data);
      console.log("message.data:", obj);
      if (typeof obj['time-status'] != 'undefined') {
          collection.time_status = obj['time-status']['str'];
          if (obj['time-status']['state'] == 'PAUSED') {
            collection.play_pause = 'Play';
          } else {
            collection.play_pause = 'Pause';
          }
          return;
      }

      if (typeof obj['CONNECTED'] != 'undefined') {
          return;
      }

      if (typeof obj['state-changed'] != 'undefined') {
          if (obj['state-changed'] == 'PLAYING') {
              collection.play_pause = 'Pause';
          }
          if (obj['state-changed'] == 'PAUSED') {
              collection.play_pause = 'Play';
          }
      }

      if (typeof obj['player-playing']  != 'undefined') {
          var artist_title = "",
              artist = "",
              title = obj['player-playing']['title'] || "";

          if (typeof obj['player-playing']['episode_title'] != 'undefined') {
              artist = obj['player-playing']['netcast_name'] || "";
              title = obj['player-playing']['episode_title'] || "";
          }
          if (typeof obj['player-playing']['artists'] != 'undefined' && 
              obj['player-playing']['artists'] && 
              typeof obj['player-playing']['artists'][0] != 'undefined' &&
              typeof obj['player-playing']['artists'][0]['artist'] != 'undefined') {
              artist = obj['player-playing']['artists'][0]['artist'];
          }

          if (artist) {
              artist_title = artist;
          }
          if (artist) {
              artist_title += " - "+ title;
          } else {
              artist_title = title;
          }
          collection.artist_title = artist_title;
          if (typeof obj['player-playing']['preloadInfo'] != 'undefined') {
            collection.reason = obj['player-playing']['preloadInfo']['reason'];
          } else {
            collection.reason = "";
          }
          if (typeof obj['player-playing']['user_file_info']['listeners'] != 'undefined') {
              var ratings = [];
              for (var i=0;i<obj['player-playing']['user_file_info']['listeners'].length; i++) {
                var listener = obj['player-playing']['user_file_info']['listeners'][i];
                ratings.push({
                  'fid': listener.fid,
                  'uid': listener.uid,
                  'rating': listener.rating,
                  'score': listener.score,
                  'uname': listener.uname,
                  'true_score': listener.true_score
                });
              }
              collection.ratings = ratings;
          } else {
            collection.ratings = [];
          }
      }
      // collection.push(JSON.parse(message.data));
      console.log("collection:",collection)
    });

    var methods = {
      collection: collection,
      get: function() {
        dataStream.send(JSON.stringify({"connected": "ok"}));
      }
    };

    dataStream.onOpen(function(){
      methods.get();
    });

    return methods;
  })
  .controller('PlayerController', function ($scope, PlayerData) {
    $scope.PlayerData = PlayerData;
  })
  .controller('RatingDemoCtrl', function ($scope) {
    $scope.isReadonly = false;

    $scope.setRating = function() {
        if ($scope.data.rating >= 6) {
          $scope.data.rating = 5;
        }
        console.log("data.rating:", $scope.data.rating);
        $(".play-pause").focus().blur();
        $.ajax({
          url: '/rate',
          data: $scope.data,
          cache: false
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
angular.module("template/rating/rating.html",[]).run(["$templateCache",function(a){
    a.put("template/rating/rating.html",'<span ng-mouseleave="reset()" ng-keydown="onKeydown($event)" tabindex="0" role="slider" aria-valuemin="0" aria-valuemax="{{range.length}}" aria-valuenow="{{value}}">\n    <span ng-repeat-start="r in range track by $index" class="sr-only">({{ $index < value ? \'*\' : \' \' }})</span>\n    <i ng-repeat-end ng-mouseenter="enter($index)" ng-click="rate($index)" class="glyphicon" ng-class="$index <= value && (r.stateOn || \'glyphicon-star\') || (r.stateOff || \'glyphicon-star-empty\')" ng-attr-title="{{r.title}}" ></i>\n</span>\n')
  }])
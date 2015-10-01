
window.next_click = function(e) {
    e.preventDefault();
    $.get("/next/");
};
window.pause_click = function(e) {
    alert("CALLED");
    e.preventDefault();
    $.get("/pause/");
};
window.prev_click = function(e) {
    e.preventDefault();
    $.get("/prev/");
};

var fmpApp = angular.module('fmpApp', [
    'ngWebSocket', // you may also use 'angular-websocket' if you prefer
    'ui.bootstrap',
    'ngRoute',
    'mgcrea.ngStrap'
  ])
  .factory('PlayerData', function($websocket) {
    // Open a WebSocket connection
    var collection = {},
        dataStream = $websocket('ws://erm76:5050/ws');

    var methods = {
      collection: collection,
      get: function() {
        dataStream.send(JSON.stringify({"connected": "ok"}));
      }
    };

    methods.votedToSkip = function(uid) {
      if (!collection) {
        collection = methods.collection;
      }
      var fid = collection.fid;
      
      if (!uid || !fid) {
        return false;
      }
      if (!collection.vote_data) {
        collection.vote_data = {};
      }
      if (!collection.vote_data[fid]) {
          collection.vote_data[fid] = {};
      }
      if (!collection.vote_data[fid][uid]) {
          collection.vote_data[fid][uid] = false;
      }
      return collection.vote_data[fid][uid];
    }

    methods.voteToSkip = function(uid) {
      var vote = !methods.votedToSkip(uid);
      console.log("***********************voteToSkip:", uid, vote);
      if (!collection.vote_data[collection.fid]) {
        collection.vote_data[collection.fid] = {};
      }
      if (!collection.vote_data[collection.fid][uid]) {
        collection.vote_data[collection.fid][uid] = false;
      }
      collection.vote_data[collection.fid][uid] = vote;
      $.ajax({
          'url': "/vote_to_skip/",
          'data': {
            'fid': collection.fid,
            'uid': uid,
            'vote': vote
          },
          'method': 'GET',
          'cache': false,
          'type': 'json'
      }).done(function(data){
          console.log("VOTE DATA:",data);
      });
    };

    dataStream.onOpen(function(){
      collection.CONNECTION = "OPEN";
      setTimeout(methods.get, 100);
    });

    dataStream.onClose(function(){
      collection.CONNECTION = "LOST";
      collection.RECONNECTING = "true";
      // dataStream.reconnect();
    });

    dataStream.initialTimeout = 500;
    dataStream.maxTimeout = 5000;
    dataStream.reconnectIfNotNormalClose = true;

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

      if (typeof obj['vote_data'] != 'undefined') {
          collection.vote_data = obj['vote_data'];
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

      if (typeof obj['seconds_left_to_skip'] != 'undefined') {
          collection.seconds_left_to_skip = obj['seconds_left_to_skip'];
      }

      if (typeof obj['player-playing']  != 'undefined') {
          var artist_title = "",
              artist = "",
              title = obj['player-playing']['title'] || obj['player-playing']['basename'] || "";

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
          collection.fid = obj['player-playing']['fid'];
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

    

    return methods;
  })
  .controller('PlayerController', function ($scope, PlayerData) {
    $scope.PlayerData = PlayerData;
    $scope.next = function(e) {
        $.get("/next/");
    };
    $scope.prev = function(e) {
        $.get("/prev/");
    };
    $scope.pause = function(e) {
        $.get("/pause/");
    };
  })
  .controller('ListenerCtrl', function($scope, $http){
    $scope.getUserForUid = function (uid)  {
      for(var i=0;i<$scope.listeners.length; i++) {
          var user = $scope.listeners[i];
          if (user.uid == uid) {
            return user;
          }
      }
      return null;
    }
    $scope.set_listening = function(uid, checkbox) {
      var user = $scope.getUserForUid(uid),
          listening = 'true';

      if (checkbox) {
        listening = user.listening;
        if (listening) {
          listening = 'true';
        } else {
          listening = 'false';
        }
      } else {
        if (user.listening) {
          listening = 'false';
          user.listening = false;
        } else {
          user.listening = true;
        }
      }
      console.log(user);
      if (user) {
        $http({
          method: 'GET',
          url: '/set_listening/?uid='+user.uid+'&listening='+listening
        }).then(function successCallback(response) {
          $scope.listeners = response.data;
          console.log(response);
        }, function errorCallback(response) {
          
        });
      }
    };

    $scope.set_admin = function(uid) {
      console.log('uid:', uid);
      var user = $scope.getUserForUid(uid);
      console.log(user);
    };
    
    $scope.listeners = [];
    $http({
      method: 'GET',
      url: '/listeners'
    }).then(function successCallback(response) {
      $scope.listeners = response.data;
      console.log(response);
    }, function errorCallback(response) {
      
    });
  })
  .controller('RatingCtrl', function ($scope) {
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
}).config(['$routeProvider',
  function($routeProvider) {
    $routeProvider
      .when('/home', {
        templateUrl: '/static/templates/player.html',
        controller: 'PlayerController'
      })
      .when('/listeners', {
        templateUrl: '/static/templates/listeners.html',
        controller: 'ListenerCtrl'
      })
      .otherwise({
        redirectTo: '/home'
      });
  }]);

angular.module("template/rating/rating.html",[]).run(["$templateCache",function(a){
    a.put("template/rating/rating.html",'<span ng-mouseleave="reset()" ng-keydown="onKeydown($event)" tabindex="0" role="slider" aria-valuemin="0" aria-valuemax="{{range.length}}" aria-valuenow="{{value}}">\n    <span ng-repeat-start="r in range track by $index" class="sr-only">({{ $index < value ? \'*\' : \' \' }})</span>\n    <i ng-repeat-end ng-mouseenter="enter($index)" ng-click="rate($index)" class="glyphicon" ng-class="$index <= value && (r.stateOn || \'glyphicon-star\') || (r.stateOff || \'glyphicon-star-empty\')" ng-attr-title="{{r.title}}" ></i>\n</span>\n')
  }]);

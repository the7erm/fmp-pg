
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
    'mgcrea.ngStrap',
    'ngCookies',
    'ngSanitize',
    'ui.tree',
    'ngTagsInput',
    'cgNotify'
  ])
  .factory('PlayerData', ['$websocket', '$cookies', '$http', '$sce', '$filter', function($websocket, $cookies, $http, $sce, $filter) {
    // Open a WebSocket connection
    var collection = {
          'ws_url': window.ws_url,
          "iam": $cookies.get('iam') || null,
          "jobs": {}
        },
        dataStream = $websocket(collection.ws_url);

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
      var watch_id = collection.fid || collection.eid;

      if (!uid || !watch_id) {
          return false;
      }
      if (!collection.vote_data) {
        collection.vote_data = {};
      }
      if (!collection.vote_data[watch_id]) {
          collection.vote_data[watch_id] = {};
      }
      if (!collection.vote_data[watch_id][uid]) {
          collection.vote_data[watch_id][uid] = false;
      }
      return collection.vote_data[watch_id][uid];
    }

    methods.voteToSkip = function(uid) {
      var vote = !methods.votedToSkip(uid);
      console.log("***********************voteToSkip:", uid, vote);
      var _id = collection.fid || collection.eid;
      if (!collection.vote_data[_id]) {
        collection.vote_data[_id] = {};
      }
      if (!collection.vote_data[_id][uid]) {
        collection.vote_data[_id][uid] = false;
      }
      collection.vote_data[_id][uid] = vote;
      $.ajax({
          'url': "/vote_to_skip/",
          'data': {
            'watch_id': _id,
            'uid': uid,
            'vote': vote
          },
          'method': 'GET',
          'cache': false,
          'type': 'json'
      }).done(function(data){
          // console.log("VOTE DATA:",data);
      });
    };

    methods.setIam = function(uid) {
      collection.iam = uid;
      var expires = new Date();
      expires.setFullYear(parseInt(expires.getFullYear()) + 1);
      $cookies.put('iam', uid, {
          'expires': expires
      });
      $http({
        method: 'GET',
        url: '/set_listening/?uid='+uid+'&listening=true'
      }).then(function successCallback(response) {
      }, function errorCallback(response) {
      });
    };

    if (collection.iam) {
        methods.setIam(collection.iam);
    }

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

    

    var htmlEntities = function(str) {
        return str.replace("<","&lt;").replace(">", "&gt;");
    };

    var fixedEncodeURIComponent = function (str) {
      return encodeURIComponent(str).replace(/[!'()*]/g, function(c) {
        return '%' + c.charCodeAt(0).toString(16);
      });
    }

    var searchLink = $filter('searchLink');
    dataStream.onMessage(function(message) {

      var obj = JSON.parse(message.data);
      
      // console.log("message.data:", obj);
      if (typeof obj['time-status'] != 'undefined') {
          collection.time_status = obj['time-status']['str'];
          if (obj['time-status']['state'] == 'PAUSED') {
            collection.play_pause = 'Play';
          } else {
            collection.play_pause = 'Pause';
          }
          //return;
      }

      if (typeof obj['jobs'] != 'undefined') {
        console.log("MESSAGE RECIEVED:", obj['jobs']);
        if (obj['jobs']) {
          for (var k in obj['jobs']) {
            collection.jobs[k] = obj['jobs'][k];
          }
        } else {
          collection.jobs =  {};
        }
        ///return;
      }

      if (typeof obj['vote_data'] != 'undefined') {
          collection.vote_data = obj['vote_data'];
      }

      if (typeof obj['CONNECTED'] != 'undefined') {
          //return;
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

          collection.owners = obj['player-playing']['owners'];
          collection.genres = obj['player-playing']['genres'];
          
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
              artist_title = searchLink(artist);
          }
          if (artist) {
              artist_title += " - " + searchLink(title);
          } else {
              artist_title = searchLink(title);
          }
          collection.fid = obj['player-playing']['fid'];
          collection.eid = obj['player-playing']['eid'];
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
                  'true_score': listener.true_score,
                  'sync_dir': listener.sync_dir
                });
              }
              collection.ratings = ratings;
          } else {
            collection.ratings = [];
          }


      }
      // collection.push(JSON.parse(message.data));
      // console.log("collection:",collection)

      collection.loadGenres = function(query) {
        return $http.get('/genres?query=' + query);
      };
    });

    

    return methods;
  }])
  .controller('PlayerController', function ($scope, PlayerData, $http, 
                                            notify) {

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

    $scope.addEntry = function(e){
      console.log("e:",e)
    }
    $scope.onAddGenre = function(fid, genre){
      console.log("onAddGenre fid:", fid, 'genre:', genre);
      $http({
        method: 'GET',
        url: '/add_genre',
        params: {"fid": fid, "genre": genre.genre}
      }).then(function successCallback(response) {

      }, function errorCallback(response) {
      });
    }
    $scope.onRemoveGenre = function(fid, genre){
      console.log("onRemoveGenre fid:", fid, 'genre:', genre);
      $http({
        method: 'GET',
        url: '/remove_genre',
        params: {"fid": fid, "genre": genre.genre}
      }).then(function successCallback(response) {
      }, function errorCallback(response) {
      });
    }

    $scope.sync = function(fid, uid) {
      $http({
        method: 'GET',
        url: '/sync',
        params: {"fid": fid, "uid": uid}
      }).then(function successCallback(response) {
        if (response.data.RESULT == "OK") {
           notify({
            "message": response.data.Message,
            "classes": "alert-success",
            "duration": 5000
          })
        } else {
          notify({
            "message": response.data.Error,
            "classes": "alert-danger",
            "duration": 5000
          })
        }
      }, function errorCallback(response) {
      });
    }
  })
  .controller('ArtistCtrl', function($scope, $http, $routeParams) {
      $scope.params = $routeParams;
      $http({
        method: 'GET',
        url: '/artist_letters'
      }).then(function successCallback(response) {
          $scope.artist_letters = response.data;
      }, function errorCallback(response) {
      });

      if ($scope.params.l) {
        $http({
          method: 'GET',
          url: '/artists/',
          params: $scope.params
        }).then(function successCallback(response){
          $scope.artists = response.data;

        }, function errorCallback(response){
        });
      }
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
    $scope.set_user_col = function(uid, col) {
        var user = $scope.getUserForUid(uid),
            url_map = {
              'admin': '/set_admin/',
              'cue_netcasts': '/set_cue_netcasts/',
              'listening': '/set_listening/'
            };
        if (!user || typeof url_map[col] == 'undefined') {
          // TODO display an alert or something.
          return;
        }
        var value = user[col];
        $http({
          method: 'GET',
          url: url_map[col]+'?uid='+uid+'&'+col+'='+value,
        }).then(function successCallback(response) {
          $scope.listeners = response.data;
        }, function errorCallback(response) {
          
        });
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
      $scope.set_user_col(user.uid, 'listening');
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
  .controller('SearchController', function($scope, $location, $route, $routeParams, $http, $cookies, PlayerData) {
      console.log("Loaded SearchController");
      $scope.params = $routeParams;
      $scope.loadedParams = "";
      $scope.$location = $location;
      $scope.$route = $route;
      $scope.maxSize = 5;
      $scope.bigTotalItems = 0;
      $scope.loadPageLocked = false;
      $scope.calledWhileLocked = false;

      $scope.$on('$routeUpdate', function(){
          $scope.params = $routeParams;
      });

      console.log("$scope.params:", $scope.params);
      $scope.loadPage = function() {
        console.log("LOAD PAGE");
       
        $scope.params.s = ($scope.bigCurrentPage - 1) * 10;
        if (!$scope.params.q) {
          $scope.params.q = "";
        }
        if ($scope.params.oc) {
          $scope.params.oc = true;
        }
        if (PlayerData.collection.iam) {
          $scope.params.uid = PlayerData.collection.iam;
        }
        if ($scope.loadedParams == JSON.stringify($scope.params)) {
          console.log("scope params == loadedParams not searching.");
          return;
        }
        if ($scope.loadPageLocked) {
          $scope.calledWhileLocked = true;
          return;
        }
        $scope.loadPageLocked = true;
        console.log("loading:", $scope.params);
        $scope.loadedParams = JSON.stringify($scope.params);
        $location.path("/search").search($scope.params);
        $http({
          method: 'GET',
          url: '/search',
          params: $scope.params
        }).then(function successCallback(response) {
          $cookies.put('search', $scope.loadedParams);
          $scope.response = response.data;
          $scope.bigTotalItems = response.data['total']['total'] || 0;
          $scope.loadPageLocked = false;
          if ($scope.calledWhileLocked) {
            $scope.calledWhileLocked = false;
            $scope.loadPage();
          }
        }, function errorCallback(response) {
          $scope.loadPageLocked = false;
          if ($scope.calledWhileLocked) {
            $scope.calledWhileLocked = false;
            $scope.loadPage();
          }
        });
      }

      if ($.isEmptyObject($scope.params) || !$scope.params) {
        console.log("loading cookie?")
        var stored = $cookies.get('search');
        if (stored) {
            console.log("stored");
            $scope.params = JSON.parse(stored);
            $scope.bigCurrentPage = $scope.params.s / 10;
            $scope.bigTotalItems = $scope.params.s + 10;
        }
      }

      if ($scope.params.s) {
        $scope.bigCurrentPage = ($scope.params.s / 10) + 1;
        $scope.bigTotalItems = $scope.params.s + 10;
        console.log("$scope.params.s", $scope.params.s);
      } else {
        $scope.bigCurrentPage = 1;
      }
      

      $scope.$watchCollection('params', function(newValue, oldValue) {
          console.log('params changed')
          $scope.loadPage();
      });
      

      $scope.pageChanged = function() {
        console.log("bigCurrentPage:",$scope.bigCurrentPage);
        $scope.loadPage();
      };

      
      $scope.cue = function(data) {
        if (!data.cued) {
          data.cued = data.fid;
          if (PlayerData.collection.iam) {
            data.uid = PlayerData.collection.iam
          } else {
            data.uid = null;
          }
        } else {
          data.cued = null;
          data.cued_for = null;
        }
        
        $http({
            method: 'GET',
            url: '/cue',
            params: data
          }).then(function successCallback(response) {
          }, function errorCallback(response) {

          });
      }

  })
  .controller('FolderCtrl', function($scope){

  })
  .controller('FoldersTreeCtrl', function($scope, $routeParams, $http, 
              PlayerData){

    $scope.jobs = PlayerData.collection.jobs;
    $scope.mtoggle = function(scope) {
      console.log("CALLED:", scope);
      scope.toggle();
      $http({
        method: 'GET',
        url: '/folders',
        params: scope['dir']
      }).then(function successCallback(response) {

          scope['dir']['children'] = response.data[0].children;
      }, function errorCallback(response) {

      });
    }
    $scope.applyToSubfolders = function(scope){
        console.log("APPLY TO SUBFOLDERS", scope);
        if (!$scope.jobs.folder_owner_progress) {
          $scope.jobs.folder_owner_progress = {};
        }
        $scope.jobs.folder_owner_progress[scope.dir.folder_id] = {
          'percent': '100%',
          'text': 'Added to job cue',
          'class': ''
        };
        $http({
          method: 'GET',
          url: '/set_owner_recursive',
          params: {
            'folder_id': scope.dir.folder_id
          }
        });
    }
    $scope.toggleOwner = function(scope) {
      scope.user.owner = !scope.user.owner;
      $http({
        method: 'GET',
        url: '/set_owner',
        params: {
          'folder_id': scope.dir.folder_id,
          'uid': scope.user.uid, 
          'owner': scope.user.owner
        }
      });
    }
    $scope.toggle = function (scope) {
      console.log("SCOPE:", scope);
      scope.toggle();
      
    };
    $http({
      method: 'GET',
      url: '/folders',
      params: {'folder_id': 0}
    }).then(function successCallback(response) {

        $scope.folders = response.data;
    }, function errorCallback(response) {

    });
  })
  .controller('GenreController', function($scope, $http){
    $scope.genres = [];
    $scope.toggleGenre = function(genre){
      genre.enabled = !genre.enabled;
      genre.query = $scope.query;
      $http({
        method: 'GET',
        url: '/genre_enabled/',
        params: genre
      }).then(function successCallback(response) {
          
      }, function errorCallback(response) {
      });
    }
    $scope.$watch('query', function(){
      var params = {
          'fetch_all':1,
          'query': $scope.query
      }
      $http({
        method: 'GET',
        url: '/genres/',
        params: params
      }).then(function successCallback(response) {
          $scope.genres = response.data;
      }, function errorCallback(response) {
      });
    })

    $http({
      method: 'GET',
      url: '/genres/?fetch_all=1'
    }).then(function successCallback(response) {
        $scope.genres = response.data;
    }, function errorCallback(response) {
    });
  })
  .controller('RatingCtrl', function ($scope, $http) {
    $scope.isReadonly = false;

    $scope.setTrueScore = function(data) {
      if (data.true_score <= -1) {
        data.score = parseInt(data.score) + 1;
      }
      if (data.true_score >= 125) {
        data.score = parseInt(data.score) - 1;
      }
      data.true_score = ((data.rating * 2 * 10) + 
                          data.score * 10) / 2.0;
      $http({
        "url":"/set_score",
        "params": data
      }).then(function successCallback(response) {
        console.log("response:", response)
      }, function errorCallback(response) {
      });
    }

    $scope.upScore = function(data) {
      data.score = parseInt(data.score) + 1;
      $scope.setTrueScore(data);
    };

    $scope.downScore = function(data) {
      data.score = parseInt(data.score) - 1;
      $scope.setTrueScore(data);
    };

    $scope.setRating = function() {
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
}).config(['$routeProvider', '$locationProvider',
  function($routeProvider) {
    $routeProvider
      .when('/artists', {
        templateUrl: '/static/templates/artists.html',
        controller: 'ArtistCtrl',
        reloadOnSearch: false
      })
      .when('/folders', {
        templateUrl: '/static/templates/folders.html',
        controller: 'FoldersTreeCtrl',
        reloadOnSearch: false
      })
      .when('/home', {
        templateUrl: '/static/templates/player.html',
        controller: 'PlayerController'
      })
      .when('/listeners', {
        templateUrl: '/static/templates/listeners.html',
        controller: 'ListenerCtrl'
      })
      .when('/search', {
        templateUrl: '/static/templates/search.html',
        controller: 'SearchController',
        reloadOnSearch: false
      })
      .when("/genres", {
        templateUrl:"/static/templates/genres.html",
        controller:"GenreController"
      })
      .otherwise({
        redirectTo: '/home'
      });
  }]).filter('encodeURIComponent', function() {
      return window.encodeURIComponent;
  }).filter('htmlEntities', function() {
      if (!text) {
        return '';
      }
      var htmlEntities = function(str) {
          return str.replace("<","&lt;").replace(">", "&gt;");
      };
      return htmlEntities;
  }).filter('fixedEncodeURIComponent', function(){
      var fixedEncodeURIComponent = function (text) {
        if (!text) {
          return '';
        }
        return encodeURIComponent(text).replace(/[!'()*]/g, function(c) {
          return '%' + c.charCodeAt(0).toString(16);
        });
      };
      return fixedEncodeURIComponent;
  }).filter('searchLink', ['$sce', function($sce){
    var searchLink = function(text) {
      if (!text) {
        return '';
      }
      var fixedEncodeURIComponent = function (text) {
        return encodeURIComponent(text).replace(/[!'()*]/g, function(c) {
          return '%' + c.charCodeAt(0).toString(16);
        });
      };
      var htmlEntities = function(text) {
          return text.replace("<","&lt;").replace(">", "&gt;");
      };
      var parts = text.split(","),
          res = [];
      for (var i=0;i<parts.length;i++) {
          if (parts[i]) {
            res.push("<a href='#/search?q="+fixedEncodeURIComponent(parts[i])+"&s=0' class='search-link'>"+htmlEntities(parts[i])+"</a>")
          }
      }
      return $sce.trustAsHtml(res.join(", "));
    }
    return searchLink;
  }]).filter('html', ['$sce', function ($sce) { 
    return function (text) {
        return $sce.trustAsHtml(text);
    }
  }]);

    

    

angular.module("template/rating/rating.html",[]).run(["$templateCache",function(a){
    a.put("template/rating/rating.html",'<span ng-mouseleave="reset()" ng-keydown="onKeydown($event)" tabindex="0" role="slider" aria-valuemin="0" aria-valuemax="{{range.length}}" aria-valuenow="{{value}}">\n    <span ng-repeat-start="r in range track by $index" class="sr-only">({{ $index < value ? \'*\' : \' \' }})</span>\n    <i ng-repeat-end ng-mouseenter="enter($index)" ng-click="rate($index)" class="glyphicon" ng-class="$index <= value && (r.stateOn || \'glyphicon-star\') || (r.stateOff || \'glyphicon-star-empty\')" ng-attr-title="{{r.title}}" ></i>\n</span>\n')
  }]);

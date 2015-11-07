var fmpApp = angular.module('fmpApp', [
    'cgNotify',
    'hc.marked',
    'ngAudio',
    'ngCookies',
    'ngRoute',
    'ngSanitize',
    'ngTagsInput',
    'ngWebSocket', // you may also use 'angular-websocket' if you prefer
    'ui.bootstrap',
    'ui.tree',
    'mgcrea.ngStrap',
    'mgcrea.ngStrap.helpers.debounce',
    'mgcrea.ngStrap.helpers.dimensions',
    'mgcrea.ngStrap.tab',
    'mgcrea.ngStrap.typeahead'
  ])
  .factory('UserUtils', ['$http', function($http){
      var methods = {};

      methods.calculateTrueScore = function(data) {
        if (data.true_score <= -20) {
          data.skip_score = parseInt(data.skip_score) + 1;
        }
        if (data.true_score >= 125) {
          data.skip_score = parseInt(data.skip_score) - 1;
        }
        data.true_score = ((data.rating * 2 * 10) +
                            data.skip_score * 10) / 2.0;
      }

      methods.setTrueScore = function(data) {
        methods.calculateTrueScore(data);
        $http({
          "url":"/set_score",
          "params": data
        }).then(function successCallback(response) {
        }, function errorCallback(response) {
        });
      };

      methods.formatTime = function(seconds) {
        var seconds = Math.floor(seconds),
            minutes = Math.floor(seconds / 60);
        seconds = seconds - (minutes * 60);
        if (seconds < 10 && seconds > -10) {
          seconds = "0"+seconds;
        }
        return minutes+":"+seconds;
      }

      methods.setListening = function(uid, listening) {
        console.log("DISABLED setListening");
        return;
        $http({
          method: 'GET',
          url: '/set_listening/',
          params: {
            'uid': uid,
            'listening': listening,
          }
        }).then(function successCallback(response) {
        }, function errorCallback(response) {
        });
      }

      methods.setListeningOnSatellite = function(uid, listening_on_satellite) {
        console.log("DISABLED setListeningOnSatellite");
        return;
        $http({
          method: 'GET',
          url: '/set_listening_on_satellite/',
          params: {
            'uid': uid,
            'listening_on_satellite': listening_on_satellite,
          }
        }).then(function successCallback(response) {
        }, function errorCallback(response) {
        });
      }

      return methods;
  }])
  .factory('ConfigUtils', ['$http', function($http){
      var collection = {
            'progress': {
              'connected': false,
              'postgres_installed': false,
              'config_exists': false,
              'config_readable': false,
              'db_connected': false,
              'db_created': false,
              'add_folders': false,
              'listen': false,
              'postgres': {
                'config': {
                  'user': '',
                  'password': '',
                  'database': 'fmp',
                  'host': 'localhost',
                  'port': '5432'
                }
              }
            }
          },
          methods = {
            'collection': collection
          };

      methods.check_install = function(scope) {
        $http({
            method: 'GET',
            url: '/check_install/'
        }).then(function successCallback(response) {
            collection.progress = response.data;
            if (scope) {
              scope.progress = response.data;
            }
        }, function errorCallback(response) {
        });
      };

      methods.addFolderToLibrary = function(dir) {
        console.log("addFolderToLibrary:", dir);
        $http({
          'method': 'POST',
          'url': '/add_folder/',
          'data': dir
        }).then(function successCallback(response){

        }, function errorCallback(response){

        });
      };
      return methods;
  }])
  .factory('SatellitePlayer', ['$http', '$cookies', '$filter', 'ngAudio',
    '$interval','UserUtils', 'notify', '$timeout', function($http, $cookies, $filter, ngAudio, $interval, UserUtils, notify, $timeout){
        var iam = $cookies.get('iam');
        if (!iam) {
          iam = -1;
        }

        var collection = {
                playlist: [],
                preload: [],
                preloadDict: {},
                idx:0,
                iam:iam,
                sound:null,
                time_status: "",
                restored: false,
                initPreloadLocked: false,
                resumePosition: 0,
                remaining: -1000,
                uids: [],
                mode:'remote'
            },
            methods = {
                collection: collection,
            };

        methods.addUid = function(uid) {
          console.log("addUid:", uid);
          uid = parseInt(uid);
          var idx = collection.uids.indexOf(uid);
          if (idx == -1) {
            collection.uids.push(uid);
            if (collection.restored) {
              collection.preload = [];
              methods.reloadCurrentIdx();
            }
            localStorage.uids = collection.uids.join(",");
            UserUtils.setListening(uid, true);
            UserUtils.setListeningOnSatellite(uid, true);
          }
        }

        methods.removeUid = function(uid) {
          console.log("removeUid:", uid);
          uid = parseInt(uid);
          var idx = collection.uids.indexOf(uid);
          if (idx != -1 && uid != collection.iam) {
            collection.uids = collection.uids.splice(idx-1, 1);
            if (collection.restored) {
              collection.preload = [];
              methods.reloadCurrentIdx();
            }
            localStorage.uids = collection.uids.join(",");
            UserUtils.setListeningOnSatellite(uid, false);
          }
        }
        methods.addUid(collection.iam);

        var uids = localStorage.uids || "";
        if (uids) {
          uids = uids.split(",");
          for (var i=0;i<uids.length; i++) {
            methods.addUid(uids[i]);
          }
        }

        methods.resume = function() {
            console.log("methods.resume()")
            if (!collection.sound || !collection.sound.canPlay || !collection.sound.duration) {
              console.log("collection.sound.duration:", collection.sound.duration);
              console.log("trying again position:", collection.resumePosition)
              $timeout(methods.resume, 500);
              return;
            }
            console.log("position:", collection.resumePosition * collection.sound.duration);
            // collection.sound.play();
            collection.sound.progress = collection.resumePosition;
            console.log("collection.sound.progress:", collection.sound.progress);
            collection.restored = true;
        }

        methods.initPlaylist = function() {
           console.log("initPlaylist")
           $http({
              "url": "/history",
              "params": {"uid": collection.uids.join(",") }
            }).then(function successCallback(response) {
              console.log("success", response.data);
              collection.playlist = response.data;
              collection.idx = collection.playlist.length - 1;
              console.log("collection.idx:", collection.idx);
              var user_file_info = collection.playlist[collection.idx]['user_file_info'];
              console.log("user_file_info:", user_file_info)
              collection.resumePosition = user_file_info['listeners'][0]['percent_played'] * 0.01;

              console.log("collection.resumePosition:", collection.resumePosition)
              $timeout(methods.resume, 1);
              methods.setIndex();
              collection.sound.play();
            }, function errorCallback(response) {

            });
        }

        methods.initPreload = function() {
            if (collection.initPreloadLocked) {
                return;
            }
            collection.initPreloadLocked = true;
            for (var i=0;i<collection.uids.length;i++) {
              var uid = collection.uids[i];
              $http({
                "url": "/preload",
                "params": {"uid": uid }
              }).then(function successCallback(response) {
                var uid = response.data.uids[0];
                for (var i=0;i<response.data.results.length;i++) {
                  collection.preload.push(response.data.results[i]);
                }
                collection.initPreloadLocked = false;
              }, function errorCallback(response) {
                collection.initPreloadLocked = false;
              });
            }
            $http({
              "url": "/preload",
              "params": {"uid": collection.uids.join(","), "limit":10 }
            }).then(function successCallback(response) {
              // Tell the server to convert the next files to .mp3 if needed.
            }, function errorCallback(response) {

            });
        }

        // collection.sound.play();

        methods.incIdx = function() {
          var idx = collection.idx + 1;
          methods.setIndex(idx);
          collection.sound.play();
        };
        methods.deIncIdx = function() {
          var idx = collection.idx - 1;
          methods.setIndex(idx);
          collection.sound.play();
        };
        methods.next = function() {
            methods.deIncScore();
            methods.incIdx();
        };
        methods.prev = function() {
            methods.deIncIdx();
        };
        methods.incScore = function() {
            angular.forEach(collection.playlist[collection.idx]['user_file_info']['listeners'], function(user) {
                if (user.uid == collection.iam) {
                  user.score = parseInt(user.score) + 1;
                  UserUtils.setTrueScore(user);
                }
            });
        };
        methods.deIncScore = function() {
          angular.forEach(collection.playlist[collection.idx]['user_file_info']['listeners'], function(user) {
                if (user.uid == collection.iam) {
                  user.score = parseInt(user.score) - 1;
                  UserUtils.setTrueScore(user);
                }
            });
        };



        methods.markAsPlayed = function(force) {
          if (collection.mode == 'remote') {
            // console.log("markAsPlayed - remote");
            return;
          }
          console.log("markAsPlayed - 1");
          if (typeof collection.sound == 'undefined' || !collection.sound) {
            return;
          }
          console.log("markAsPlayed - 2");
          if (collection.sound.paused && !force) {
            return;
          }
          console.log("markAsPlayed - 3");
          if (force) {
            console.log("forcing", force);
          }
          console.log("markAsPlayed - 4");
          var params = {
              "fid": collection.playlist[collection.idx].fid,
              "eid": collection.playlist[collection.idx].eid,
              "uid": collection.uids.join(","),
              "percent": (collection.sound.progress || 0) * 100
          };
          $http({
              "url":"/mark_as_played",
              "params": params
          }).then(function successCallback(response) {
            methods.fixPlaylist();
            if (collection.preload.length == 0) {
              console.log("markAsPlayed - 5");
              methods.initPreload();
            }
            console.log("markAsPlayed - 6");
          }, function errorCallback(response) {
          });
          return true;
        };

        methods.updateTime = function() {

          if (collection.mode == 'remote') {
            // console.log("updateTime - remote");
            return;
          }
          if (typeof collection.sound == 'undefined') {
            return;
          }
          if (typeof collection.sound.audio == 'undefined') {
            return;
          }

          // console.log("updateTime - satellite");
          if (collection.sound.paused) {
            if (collection.sound.progress >= 1.0) {
              console.log("marking at 100%");
              methods.markAsPlayed(true);
              methods.incScore();
              methods.incIdx();
            }
            return;
          }
          collection.time_status = "-"+UserUtils.formatTime(collection.sound.remaining) + " " + UserUtils.formatTime(collection.sound.currentTime)+"/"+UserUtils.formatTime(collection.sound.duration) +" "+(collection.sound.progress * 100).toFixed(2);

        };

        methods.fixPlaylist = function() {
          var playlistItem = collection.playlist[collection.idx];
          if (!playlistItem) {
            return;
          }
          for(var i=0;i<collection.preload.length;i++) {
              var preloadItem = collection.preload[i];
              if (playlistItem.fid == preloadItem.fid) {
                collection.preload.splice(i, 1);
                console.log("removed",i);
              }
          }
        };

        methods.setIndex = function(idx) {
          console.log("setIndex:", idx);

          if (typeof idx != 'undefined') {
            idx = parseInt(idx);
            if (idx >= collection.playlist.length ) {
              console.log("REMOVING ITEM FROM PRELOAD");
              var item = collection.preload.shift();
              if (item) {
                collection.playlist.push(item);
                methods.fixPlaylist();
                methods.initPreload();
              }
              if (idx >= collection.playlist.length) {
                idx = 0;
              }
            }
            if (idx < 0) {
              idx = collection.playlist.length - 1;
            }
          }

          if (collection.playlist[idx] == 'undefined') {
              console.log("undefined index1");
          }

          if (typeof idx != 'undefined' && typeof collection.playlist[idx] != 'undefined') {
            collection.idx = idx;
          }

          if (typeof collection.playlist[collection.idx] == 'undefined') {
            console.log("undefined index");
            return;
          }

          if (collection.sound) {
            console.log("stopping")
            collection.sound.stop();
          }

          console.log("loading audio:", '/download/?fid='+collection.playlist[collection.idx].fid);

          collection.sound = ngAudio.load('/download/?fid='+collection.playlist[collection.idx].fid);
          collection.sound.performance = 100;
          var obj = collection.playlist[collection.idx];
          console.log("setIndex obj:", obj);
          if (typeof methods.PlayerDataMethods == 'undefined') {
            return;
          }
          methods.PlayerDataMethods.setPlayingData(obj);

        };

        methods.playIndex = function(idx) {
          if (collection.sound && !collection.sound.paused) {
            collection.sound.stop();
          }
          methods.setIndex(idx);
          collection.sound.play();
        }

        methods.init = function() {
          methods.initPlaylist();
          methods.initPreload();
        }

        methods.reloadCurrentIdx = function() {
          var idx = collection.idx;
          console.log("reloadCurrentIdx:", collection.idx)
          $http({
              "url": "/history",
              "params": {
                  "uid": collection.uids.join(","),
                  "fid": collection.playlist[idx].fid
              }
          }).then(function successCallback(response) {
            if (response.data) {
              var obj = response.data[0];
              methods.PlayerDataMethods.setPlayingData(obj);
            }
          }, function errorCallback(response) {

          });
        }

        $interval(methods.updateTime, 1000);
        $interval(methods.markAsPlayed, 5000, 0, true, false);

        return methods;
  }])
  .factory('PlayerData', ['$websocket', '$cookies', '$http', '$sce', '$filter',
    'SatellitePlayer', 'UserUtils', function($websocket, $cookies, $http, $sce, $filter, SatellitePlayer, UserUtils) {
        // Open a WebSocket connection
        var collection = {
              'ws_url': window.ws_url,
              "iam": $cookies.get('iam') || null,
              "jobs": {},
              "mode": "remote",
              "show_locations": false
            },
            dataStream = $websocket(collection.ws_url);

        var mode = $cookies.get('mode');


        if (mode) {
            collection.mode = mode;
            SatellitePlayer.collection.mode = mode;

        }

        var methods = {
          collection: collection,
          get: function() {
            console.log("methods.get()")
            dataStream.send(JSON.stringify({"action": "broadcast-playing"}));
          }
        };

        methods.votedToSkip = function(user_id) {
          if (!collection.playingData) {
            return false;
          }
          if (!collection.playingData.user_file_info) {
            return false;
          }
          for(var i=0;i<collection.playingData.user_file_info.length;i++) {
            if (collection.playingData.user_file_info[i].user_id == user_id) {
              return collection.playingData.user_file_info[i].voted_to_skip;
            }
          }
          return false;
        }

        methods.userIdVoteToSkip = function(user_id) {
          if (!collection.playingData || !collection.playingData.user_file_info) {
            return;
          }
          for(var i=0;i<collection.playingData.user_file_info.length;i++) {
            if (collection.playingData.user_file_info[i].user_id == user_id) {
              methods.voteToSkip(collection.playingData.user_file_info[i]);
            }
          }
        }

        methods.voteToSkip = function(data) {
          console.log("voteToSkip:", data);
          data.voted_to_skip = !data.voted_to_skip;
          $http({
            method: 'GET',
            url: '/vote_to_skip',
            params: data
          }).then(function successCallback(response) {
          }, function errorCallback(response) {
          });
        };

        methods.setIam = function(uid) {
          collection.iam = uid;
          SatellitePlayer.collection.iam = uid;
          var expires = new Date();
          expires.setFullYear(parseInt(expires.getFullYear()) + 1);
          $cookies.put('iam', uid, {
              'expires': expires
          });
          UserUtils.setListening(uid, true);
          if (collection.mode == 'satellite') {
            UserUtils.setListeningOnSatellite(uid, true);
          } else {
            UserUtils.setListeningOnSatellite(uid, false);
          }
        };

        methods.setMode = function(mode) {
          mode = 'remote';
          console.log("setMode:", mode);
          var expires = new Date();
          expires.setFullYear(parseInt(expires.getFullYear()) + 1);
          $cookies.put('mode', mode, {
              'expires': expires
          });
          if (mode == 'satellite') {
            collection.play_pause = "Pause";
            SatellitePlayer.init();
            UserUtils.setListening(collection.iam, true);
            UserUtils.setListeningOnSatellite(collection.iam, true);
          } else {
            collection.play_pause = "Play";
            UserUtils.setListening(collection.iam, true);
            UserUtils.setListeningOnSatellite(collection.iam, false);
            methods.get();
          }
          SatellitePlayer.collection.mode = mode;
          if (SatellitePlayer.collection.sound && !SatellitePlayer.collection.sound.paused) {
              SatellitePlayer.collection.sound.pause();
          }
        };

        methods.setPlayingData = function(obj) {
            console.log("setPlayingData:", obj);
            collection.playingData = obj;
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
          // console.log("message",message);
          if (collection.mode != "remote") {
            // console.log("mode:", collection.mode);
            return;
          }
          try {
            var obj = JSON.parse(message.data);
          } catch (e) {
            console.log("error parsing message.data:", message.data);
            return;
          }


          // console.log("message.data:", obj);
          if (typeof obj['time-status'] != 'undefined') {
              collection.time_status = obj['time-status']['str'];
              collection.skip_countdown = obj['time-status']['skip_countdown'];
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
              methods.setPlayingData(obj['player-playing']);
          }
          // collection.push(JSON.parse(message.data));
          // console.log("collection:",collection)

          collection.loadGenres = function(query) {
            return $http.get('/genres?query=' + query);
          };
        });

        methods.init = function() {
          methods.setMode(collection.mode);

          if (collection.iam) {
              methods.setIam(collection.iam);
          }
        }

        SatellitePlayer.PlayerDataMethods = methods;

        methods.init();

        return methods;
  }])
  .controller('PlayerController', function ($scope, PlayerData, $http,
                                            notify, SatellitePlayer) {

    $scope.PlayerData = PlayerData;
    $scope.SatellitePlayer = SatellitePlayer;
    $scope.next = function(e) {
        if (PlayerData.collection.mode == 'remote') {
          $.get("/next/");
        } else {
          SatellitePlayer.next();
        }
    };
    $scope.prev = function(e) {
        if (PlayerData.collection.mode == 'remote') {
          $.get("/prev/");
        } else {
          SatellitePlayer.prev();
        }
    };
    $scope.pause = function(e) {
        console.log("PAUSED");
        if (PlayerData.collection.mode == 'remote') {
          $.get("/pause/");
        } else {
          var sound = SatellitePlayer.collection.sound;
          if (sound.paused) {
            sound.play();
            PlayerData.collection.play_pause = "Pause";
          } else {
            sound.pause();
            PlayerData.collection.play_pause = "Play";
          }
        }
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
  .controller('ListenerCtrl', function($scope, $http, SatellitePlayer, ConfigUtils){
    console.log("ListenerCtrl CALLED")
    $scope.SatellitePlayer = SatellitePlayer;
    $scope.getUserForUid = function (id)  {
      for(var i=0;i<$scope.listeners.length; i++) {
          var user = $scope.listeners[i];
          if (user.id == id) {
            return user;
          }
      }
      return null;
    }
    $scope.addUser = function(newUser) {
      console.log("newUser:", newUser);
      for(var i=0;i<$scope.listeners.length; i++) {
          var user = $scope.listeners[i];
          if (user.name == newUser.name) {
            return;
          }
      }
      $http({
        method: 'POST',
        url: '/add_user',
        data:newUser
      }).then(function successCallback(response) {
        $scope.listeners = response.data;
        ConfigUtils.check_install();
      }, function errorCallback(response) {

      });
    }
    $scope.set_user_col = function(id, col) {
        var user = $scope.getUserForUid(id),
            url_map = {
              'admin': '/set_admin/',
              'cue_netcasts': '/set_cue_netcasts/',
              'listening': '/set_listening/',
              'listening_on_satellite': '/set_listening_on_satellite/'
            };
        if (!user || typeof url_map[col] == 'undefined') {
          // TODO display an alert or something.
          return;
        }
        var value = user[col];
        $http({
          method: 'GET',
          url: url_map[col]+'?user_id='+id+'&'+col+'='+value,
        }).then(function successCallback(response) {
          $scope.listeners = response.data;
        }, function errorCallback(response) {

        });
    }
    $scope.set_listening = function(id, checkbox) {
      var user = $scope.getUserForUid(id),
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
      $scope.set_user_col(user.id, 'listening');
    };

    $scope.set_listening_with_me = function(uid) {
      var user = $scope.getUserForUid(uid);
      console.log("set_listening_with_me:", uid);
      console.log("user.on_this_browser_session:", user.on_this_browser_session);
      if (user.on_this_browser_session){
        SatellitePlayer.addUid(uid);
      } else {
        SatellitePlayer.removeUid(uid);
      }
    }

    $scope.listeners = [];
    $http({
      method: 'GET',
      url: '/listeners'
    }).then(function successCallback(response) {

      for (var i=0;i<response.data.length;i++) {
        var user = response.data[i];
        if (SatellitePlayer.collection.uids.indexOf(user.uid) != -1 || SatellitePlayer.collection.iam == user.uid) {
          response.data[i].on_this_browser_session = true;
        }
      }
      $scope.listeners = response.data;
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
      $scope.users = [];

      $http({
        method: 'GET',
        url: '/users'
      }).then(function successCallback(response) {
          $scope.users = response.data;
      }, function errorCallback(response) {
      });

      $scope.setOwner = function(uid) {
        $scope.params.owner = uid;
      }
      $scope.loadTags = function(query) {
          return $http.get('/tags?word='+encodeURIComponent(query));
      };
      $scope.onAddWord = function(word) {
        if (!word || !word.word || word.word == " ") {
          return;
        }
        console.log("q:", $scope.params.q);
        var words = $scope.params.q.split(" "),
            newWords = [];
        words.push(word.word);
        for (var i=0;i<words.length;i++) {
          if (!words[i] || words[i] == " ") {
            continue;
          }
          console.log("pushing:",words[i])
          newWords.push(words[i]);
        }
        $scope.params.q = words.join(" ");
      }
      $scope.onRemoveWord = function(word) {
        if (!word || !word.word) {
          return;
        }
        var words = $scope.params.q.split(" "),
            newWords = [];
        for (var i=0;i<words.length;i++) {
          if (!words[i] || words[i] == word.word) {
            continue;
          }
          newWords.push(words[i]);
        }
        $scope.params.q = newWords.join(" ");
      }

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
        $scope.tags = [];
        if ($scope.params.q) {
          var words = $scope.params.q.split(" "),
              tags = [];
          for (var i=0;i<words.length;i++) {
            if (words[i] && words[i] != " ") {
              tags.push(words[i]);
            }
          }
          $scope.tags = tags;
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
          $scope.bigTotalItems = response.data['total'] || 0;
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
          data.cued = true;
          if (PlayerData.collection.iam) {
            data.uid = PlayerData.collection.iam;
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
  .controller('FoldersCtrl', function($scope, $http, ConfigUtils){
      $scope.folder = "/";
      $scope.folders = [];

      $scope.toggle = function (scope) {
        console.log("SCOPE:", scope);
        scope.toggle();

      };
      $scope.mtoggle = function(scope) {
        scope.toggle();
        $http({
          method: 'GET',
          url: '/browse',
          params: {"folder": scope['dir']['realpath'] }
        }).then(function successCallback(response) {
            scope['dir']['children'] = response.data;
        }, function errorCallback(response) {

        });
      }
      $http({
        method: 'GET',
        url: '/browse',
        params: {"folder": "/"}
      }).then(function successCallback(response) {
          $scope.folders = response.data;
      }, function errorCallback(response) {

      });
      $scope.addFolderToLibrary = ConfigUtils.addFolderToLibrary;
  })
  .controller('FoldersTreeCtrl', function($scope, $routeParams, $http,
              PlayerData){

    $scope.jobs = PlayerData.collection.jobs;
    $scope.mtoggle = function(scope) {
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
  .controller('ConfigController', function($scope, $http, ConfigUtils){
    $scope.page = 1;
    $scope.progress = ConfigUtils.collection.progress;

    $scope.tabs = [];
    $scope.tabs.activeTab = "Welcome";
    if (localStorage.configActiveTab) {
      $scope.tabs.activeTab = localStorage.configActiveTab;
    }
    $scope.check_install = function(){
      ConfigUtils.check_install($scope);
      // $scope.progress = ConfigUtils.collection.progress;
    }
    $scope.check_install($scope);

    $scope.$watch('tabs.activeTab', function(newValue, oldValue){
        console.log("tabs.activeTab changed newValue:", newValue, "oldValue:",
                    oldValue);
        $scope.progress = ConfigUtils.collection.progress;
        $scope.check_install();
        localStorage.configActiveTab = newValue;
    })

    $scope.createRole = function() {
      $http({
        method: 'POST',
        url: '/create_role/',
        data: $scope.progress.postgres.config
      }).then(function successCallback(response) {
        $scope.check_install();
      }, function errorCallback(response) {
        $scope.check_install();
      });
    }

    $scope.createDb = function() {
      $http({
        method: 'POST',
        url: '/create_db/',
        data: $scope.progress.postgres.config
      }).then(function successCallback(response) {
        $scope.check_install();
      }, function errorCallback(response) {
        $scope.check_install();
      });
    }

    $scope.save = function() {
      console.log("progress.postgres.config:", $scope.progress.postgres.config);
      $http({
        method: 'POST',
        url: '/save_config/',
        data: $scope.progress.postgres.config
      }).then(function successCallback(response) {
          $scope.check_install();
      }, function errorCallback(response) {
      });
    }
    $scope.dbRowClass = function(data, can_connect) {
      if (!can_connect || data.name != can_connect.name || !can_connect.name) {
        return '';
      }
      if (!can_connect.connected) {
        return 'danger connected_db';
      }
      return 'success connected_db';
    }

  })
  .controller('GenreController', function($scope, $http){
    $scope.genres = [];
    $scope.toggleGenre = function(genre){
      genre.enabled = !genre.enabled;
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
  .controller('RatingCtrl', function ($scope, $http, UserUtils) {
    $scope.isReadonly = false;

    $scope.setTrueScore = UserUtils.setTrueScore;
    $scope.calculateTrueScore = UserUtils.calculateTrueScore;

    $scope.upScore = function(data) {
      console.log("data:", data);
      data.skip_score = parseInt(data.skip_score) + 1;
      $scope.setTrueScore(data);
    };

    $scope.downScore = function(data) {
      data.skip_score = parseInt(data.skip_score) - 1;
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
        $scope.calculateTrueScore($scope.data);
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
}).config(['$routeProvider', '$locationProvider', '$scrollspyProvider',
           '$affixProvider', '$typeaheadProvider',

  function($routeProvider, $locationProvider, $scrollspyProvider, $affixProvider,
           $typeaheadProvider) {

    angular.extend($typeaheadProvider.defaults, {
      animation: 'am-flip-x',
      minLength: 1,
      limit: 8
    });

    angular.extend($scrollspyProvider.defaults, {
      animation: 'am-fade-and-slide-top',
      placement: 'top'
    });

    angular.extend($affixProvider.defaults, {
      offsetTop: 100
    });
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
      .when("/genres", {
        templateUrl:"/static/templates/genres.html",
        controller:"GenreController"
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
      .when('/setup', {
        templateUrl: '/static/templates/setup.html',
        controller: 'ConfigController'
      })
      .when("/welcome/", {
        templateUrl: '/static/templates/setup.html',
        controller:"ConfigController"
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

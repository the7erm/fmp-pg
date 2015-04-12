var fmpApp = angular.module('fmpApp', [
    'ui.bootstrap',
    'mgcrea.ngStrap', 
    'mgcrea.ngStrap.modal', 
    'mgcrea.ngStrap.aside', 
    'mgcrea.ngStrap.tooltip', 
    'mgcrea.ngStrap.typeahead',
    'ngRoute', 
    'ngTagsInput',
    'bgf.paginateAnything'
]);


fmpApp.config(['$routeProvider',
    function($routeProvider) {
        $routeProvider.when('/home', {
            templateUrl: '/static/templates/home.html',
            controller: 'HomeCtrl'
        })
        .when("/search", {
            templateUrl: "/static/templates/search.html",
            controller: "SearchCtrl",
            reloadOnSearch: false
        })
        .when("/search/:query", {
            templateUrl: "/static/templates/search.html",
            controller: "SearchCtrl",
            reloadOnSearch: false
        })
        .when("/preload", {
            templateUrl: "/static/templates/preload.html",
            controller: "PreloadCtrl"
        })
        .when("/history", {
            templateUrl: "/static/templates/history.html",
            controller: "HistoryCtrl"
        })
        .when("/podcasts", {
            templateUrl: "/static/templates/podcasts.html",
            controller: "PodcastCtrl"
        })
        .when("/podcasts/:query", {
            templateUrl: "/static/templates/podcasts.html",
            controller: "PodcastCtrl"
        })
        .when("/listeners", {
            templateUrl: "/static/templates/listeners.html",
            controller: "ListenersCtrl"
        })
        .otherwise({
            redirectTo: '/home'
        });
}]);

fmpApp.factory('socket', ['$rootScope', function ($rootScope) {
    console.log("FACTORY SOCKET CALLED")
    var socket = io.connect('http://' + document.domain + ':' + location.port +"/fmp");
    return {
        on: function (eventName, callback) {
          socket.on(eventName, function () {
            var args = arguments;
            $rootScope.$apply(function () {
              callback.apply(socket, args);
            });
          });
        },
        emit: function (eventName, data, callback) {
          socket.emit(eventName, data, function () {
            var args = arguments;
            $rootScope.$apply(function () {
              if (callback) {
                callback.apply(socket, args);
              }
            });
          })
        }
    };
}]);


fmpApp.factory('Search', ['$http', '$timeout', function($http, $timeout) {
  console.log("Search factory")
  var Search = function(query, url, start, limit) {
    this.items = [];
    this.busy = false;
    this.done = false;
    this.after = '';
    this.start = parseInt(start) || 0;
    this.limit = parseInt(limit) || 10;
    this.url = url || "/search-data-new/";
    this.query = encodeURIComponent(query || "");
  };

  Search.prototype.nextPage = function() {
    if (this.busy) return;
    this.busy = true;
    console.log("Next page");
    // /search-data-new/
    var url = this.url+"?s="+this.start+"&l="+this.limit+"&q="+this.query;
    $http.get(url).success(function(data) {
      var items = data,
          _this = this;
      if (items.length == 0) {
        // Out of items leave as 'busy'
        this.done = true;
        return;
      }
      for (var i = 0; i < items.length; i++) {
        //this.items.push(items[i]);
        this.items.push(items[i]);
      }
      // this.after = "t3_" + this.items[this.items.length - 1].id;''
      this.start = this.start + this.limit;
      this.busy = false;
    }.bind(this));
  };
  return Search;
}]);

timeBetween = function(historyArray, $index, $modal, $aside, $tooltip) {
    if ($index == historyArray.length - 1) {
        return "";
    }
    var seconds_in_an_hour = 60 * 60,
        seconds_in_a_day = 24 * seconds_in_an_hour,
        seconds_in_a_month = Math.floor((365 * seconds_in_a_day) / 12),
        seconds_in_a_week = 7 * seconds_in_a_day,
        seconds_in_a_year = 365 * seconds_in_a_day,
        current = new Date(historyArray[$index]['time_played']), 
        next = new Date (historyArray[$index+1]['time_played']),
        ms = current.valueOf() - next.valueOf(),
        seconds = Math.floor(ms / 1000),
        years = Math.floor(seconds / seconds_in_a_year),
        seconds = seconds - (years * seconds_in_a_year),
        months = Math.floor(seconds / seconds_in_a_month),
        seconds = seconds - (months * seconds_in_a_month),
        weeks = Math.floor(seconds / seconds_in_a_week),
        seconds = Math.floor(seconds - (weeks * seconds_in_a_week)),
        days = Math.floor(seconds / seconds_in_a_day),
        seconds = Math.floor(seconds - (days * seconds_in_a_day)),
        hours = Math.floor(seconds / seconds_in_an_hour),
        seconds = Math.floor(seconds - (hours * seconds_in_an_hour)),
        minutes = Math.floor(seconds / 60),
        seconds = Math.floor(seconds - (minutes * 60));

    if (ms <= 0) {
        return "";
    }

    if (years) {
        var txt = "year";
        if (years > 1) {
            txt += "s";
        }
        txt = years+ " " + txt;
        if (months) {
            txt += " "+months+" month";
            if (months > 1) {
                txt += "s";
            }
        }
        return txt;
    }

    if (months) {
        if (months > 1) {
            return months+" months";
        }
        return months+" month";
    }

    if (weeks) {
        if (weeks > 1) {
            return weeks+" weeks";
        }
        return weeks+" week";
    }

    if (minutes < 10) {
        minutes = "0"+ minutes;
    }
    if (seconds < 10) {
        seconds = "0"+seconds;
    }

    if (days) {
        if (days > 1) {
            return days+" days";
        }
        return days+" day";
    }
    return hours+":"+minutes+":"+seconds;
};

fmpApp.factory('fmpService', ['$rootScope','$http', '$interval', '$timeout', '$q', 'socket',
    function($rootScope, $http, $interval, $timeout, $q, socket){
        var now = new Date();
        $rootScope.cacheFix = now.valueOf();
        var sharedService = {};
        sharedService.doCue = function(item, state) {
            var fid = item.fid;
            console.log("CUE");
            console.log("FID:", fid);
            console.log("this:", this);
            var url = "/cue/?fid="+fid+"&cue="+state
            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
                if (state == "true") {
                    item.cued = fid;
                } else {
                    item.cued = null;
                }
            })
            .error(function(data, status, headers, config) {
              // called asynchronously if an error occurs
              // or server returns response with an error status.
            });
        };
        sharedService.cue = function(item) {
            sharedService.doCue(item, "true");
        };
        sharedService.uncue = function(item) {
            sharedService.doCue(item, "false");
        };
        sharedService.getTags = function(viewValue) {
            var params = {"q": viewValue};
            return $http.get('/kw', {params: params})
            .then(function(res) {
                return res.data;
            });
        };
        sharedService.message = "";
        sharedService.prepForProadcast = function(msg){
            this.message = msg;
            this.broadcastItem();
        };

        sharedService.broadcastItem = function() {
            $rootScope.$broadcast('handleBroadcat');
        };


        sharedService.processStatus = function(data) {
            for (var i=0; i < data.extended.history.length; i++) {
                data.extended.history[i]["timeBetween"] = timeBetween(
                    data.extended.history, i);
            }
            $rootScope.playing_data = data.extended;
        };

        sharedService.rate = function(usid, fid, uid, rating, usi){
            var url = "/rate/"+usid+"/"+fid+"/"+uid+"/"+rating;

            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
                // this callback will be called asynchronously
                // when the response is available
                // $scope.playing_data = data.extended;
                // console.log("TEST:", data);
                /*
                fid: 18184
                percent_played: 45.7385899900328
                rating: 3
                score: 5
                true_score: 53.0179808308415
                uid: 1
                ultp: 1404259200000
                usid: 179278
                */
                // console.log("playing_data.ratings", $rootScope.playing_data.ratings)
                for(key in $rootScope.playing_data.ratings) {
                    var rating = $rootScope.playing_data.ratings[key];
                    // console.log("rating:", rating);
                    if (rating.usid == data.usid) {
                        $rootScope.playing_data.ratings[key].rating = data.rating;
                        $rootScope.playing_data.ratings[key].true_score = data.true_score;
                        $rootScope.playing_data.ratings[key].percent_played = data.percent_played;
                        $rootScope.playing_data.ratings[key].ultp = data.ultp;
                        $rootScope.playing_data.ratings[key].score = data.score;
                    }
                }
                // $rootScope.playing_data.rating = data.extended;
                console.log("usi:",usi);
                if (usi) {
                    usi.rating = data.rating;
                    usi.true_score = data.true_score;
                    usi.score = data.score;
                }
            })
            .error(function(data, status, headers, config) {
              // called asynchronously if an error occurs
              // or server returns response with an error status.
            });
        };

        sharedService.pause = function() {
        	console.log("PAUSE");
            $http({method: 'GET', url: '/player/pause'})
                .success(function(data, status, headers, config) {
                    // this callback will be called asynchronously
                    // when the response is available
                    sharedService.processStatus(data);
                })
                .error(function(data, status, headers, config) {
                  // called asynchronously if an error occurs
                  // or server returns response with an error status.
                });
        }
        sharedService.next = function() {
        	console.log("NEXT");
            $http({method: 'GET', url: '/player/next'})
                .success(function(data, status, headers, config) {
                    // this callback will be called asynchronously
                    // when the response is available
                    sharedService.processStatus(data);
                    // $rootScope.playing_data = data.extended;
                    
                })
                .error(function(data, status, headers, config) {
                  // called asynchronously if an error occurs
                  // or server returns response with an error status.
                });
        }
        sharedService.prev = function() {
            $http({method: 'GET', url: '/player/prev'})
                .success(function(data, status, headers, config) {
                    // this callback will be called asynchronously
                    // when the response is available
                    // $rootScope.playing_data = data.extended;
                    sharedService.processStatus(data);
                })
                .error(function(data, status, headers, config) {
                  // called asynchronously if an error occurs
                  // or server returns response with an error status.
                });
        }

        sharedService.getStatus = function(){
            socket.emit('status');
        };

        $rootScope.loadArtistTags = function(query) {
            return $http.get('/kwa?q=' + encodeURIComponent(query));
        };

        $rootScope.loadGenreTags = function(query) {
            return $http.get('/kwg?q=' + encodeURIComponent(query));
        };

        $rootScope.loadAlbumTags = function(query) {
            return $http.get('/kwal?q=' + encodeURIComponent(query));
        };

        $rootScope.removeArtistTag = function(fid, aid) {
            console.log("removeArtistTag", fid, aid);
            var url = "/remove-file-artist/?fid="+fid+"&aid="+aid;
            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
            })
            .error(function(data, status, headers, config) {
            });
        };

        $rootScope.addArtistTag = function(fid, $tag) {
            console.log("addArtistTag:", fid, $tag);
            var url = "/add-file-artist/?fid="+fid+"&artist="+encodeURIComponent($tag.artist);
            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
                console.log("DATA:",data);
                if(data.result == "success") {
                    $tag.aid = data.aid;
                }
            })
            .error(function(data, status, headers, config) {
            });
        };

        $rootScope.removeGenreTag = function(fid, gid) {
            console.log("removeGenreTag", fid, gid);
            var url = "/remove-file-genre/?fid="+fid+"&gid="+gid;
            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
                
            })
            .error(function(data, status, headers, config) {
            });
        };

        $rootScope.addGenreTag = function(fid, $tag) {
            console.log("addGenreTag:", fid, $tag);
            var url = "/add-file-genre/?fid="+fid+"&genre="+encodeURIComponent($tag.genre);
            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
                console.log("DATA:",data);
                if(data.result == "success") {
                    $tag.gid = data.gid;

                }
            })
            .error(function(data, status, headers, config) {
            });
        };

        $rootScope.removeAlbumTag = function(fid, alid) {
            console.log("removeAlbumTag", fid, alid);
            var url = "/remove-file-album/?fid="+fid+"&alid="+alid;
            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
            })
            .error(function(data, status, headers, config) {
            });
        };

        $rootScope.addAlbumTag = function(fid, $tag) {
            console.log("addAlbumTag:", fid, $tag);
            var url = "/add-file-album/?fid="+fid+"&album_name="+encodeURIComponent($tag.album_name);
            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
                if(data.result == "success") {
                    $tag.alid = data.alid;
                }
            })
            .error(function(data, status, headers, config) {
            });
        };

        $rootScope.log = function(){
            console.log(arguments);
        }

        $rootScope.setTitleTimeout = false;

        $rootScope.setTitle = function(fid, title) {
            if ($rootScope.setTitleTimeout) {
                clearTimeout($rootScope.setTitleTimeout);
                $rootScope.setTitleTimeout = false;
            }
            console.log("setTitle", fid, title);
            var url = "/set-title/?fid="+fid+"&title="+encodeURIComponent(title);
            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
                $rootScope.setTitleTimeout = false;
                console.log("data:",data)
            })
            .error(function(data, status, headers, config) {
                $rootScope.setTitleTimeout = false;
            });
        }

        socket.on("time-status", function(data){
            $rootScope.playing_data.pos_data = data;
        });

        socket.on("state-changed", function(data){
            // console.log("state-changed:", data)
            $rootScope.playing_data.playingState = data;
        });

        socket.on("mark-as-played", function(update_data){
            if (update_data.res.length > 0) {
                var keys = ['rating', 'score', 'true_score', 'percent_played',
                            'ultp'];
                for (var i=0;i<update_data.res.length;i++) {
                    for (var i2=0;i2<$rootScope.playing_data.ratings.length;i2++) {
                        if ($rootScope.playing_data.ratings[i2].usid == update_data.res[i].usid) {
                            for (var i3=0;i3<keys.length;i3++) {
                                var key = keys[i3];
                                $rootScope.playing_data.ratings[i2][key] = update_data.res[i][key];
                            }
                            break;
                        }
                    }
                }
            }
        });

        socket.on("status", function(playing_data){
            console.log("status:", playing_data);
            var process = {"extended": playing_data};
            sharedService.processStatus(process);
        });

        sharedService.moreInfo = function(item) {
            console.log("item:", item);
            // /file-info/<fid>/
            var url = "/file-info/"+item.fid+"/";
            $http({method: 'GET', url: url})
            .success(function(data, status, headers, config) {
                for (var i=0; i < data.history.length; i++) {
                    data.history[i]["timeBetween"] = timeBetween(data.history, i);
                }
                item.moreInfo = data;
            })
            .error(function(data, status, headers, config) {
            });
        };

        sharedService.initPagination = function($scope, $routeParams, $location, 
                                                $modal) {

            var infoModal = $modal({
                    scope: $scope, 
                    template: '/static/templates/popover.tpl.html', 
                    show: false, 
                    container: "body"
                });
            
            $scope.showModal = function() {
                infoModal.$promise.then(infoModal.show);
            };

            $scope.doSearch = function(query) {
                console.log("doSearch query:", query);
                document.location = "#/search/"+encodeURIComponent(query);
            };

            $scope.cue = sharedService.cue;
            $scope.uncue = sharedService.uncue;

            $scope.query = $routeParams.query || "";
            
            $scope.perPage = parseInt($location.search().perPage, 10) || 5;
            $scope.page = parseInt($location.search().page, 10) || 0;
            $scope.clientLimit = 20;

            $scope.$watch('page', function(page) { 
                $location.search('page', page); 
                console.log("page:", page);
            });
            $scope.$watch('perPage', function(page) { $location.search('perPage', page); });
            $scope.$on('$locationChangeSuccess', function() {
                var page = +$location.search().page,
                  perPage = +$location.search().perPage;
                if(page >= 0 && page != $scope.page) { 
                    $scope.page = page; 
                };
                if(perPage >= 0 && $scope.perPage != perPage) { 
                    $scope.perPage = perPage; 
                };
            });
            $scope.$on("pagination:loadPage", function(evt, status, config){
                $location.search('page', evt.targetScope.page);
                $location.search('perPage', evt.targetScope.perPage);
            });

            $scope.moreInfo = sharedService.moreInfo;
        };



        sharedService.getStatus();
        $interval(sharedService.getStatus, 10000);
        return sharedService;
}]);


fmpApp.controller('CurrentlyPlayingCtrl',['$scope', 'fmpService', 
    function($scope, fmpService){
        $scope.next = fmpService.next;
        $scope.pause = fmpService.pause;
        $scope.prev = fmpService.prev;
}]);

fmpApp.controller('ControlsCtrl',['$scope', 'fmpService', function($scope, fmpService){
	$scope.next = fmpService.next;
	$scope.pause = fmpService.pause;
	$scope.prev = fmpService.prev;
}]);

fmpApp.controller('HomeCtrl', ['$scope', '$rootScope', 'fmpService',
    function($scope, $rootScope, fmpService) {
    window.document.title = "fmp - home";
}]);


fmpApp.directive('starRating',['fmpService',
    function(fmpService) {
        return {
            restrict : 'A',
            template : '<ul class="rating"> <li ng-repeat="star in stars" ' + 
                       'ng-class="star" ng-click="toggle($index)">  ' + 
                       '<a ng-show="!$index"><img src="/static/images/raty/no.star.png" class="small-no"></a>'  + 
                       '<span ng-show="$index > 0">\u2605</span>' + 
                       '</li></ul>'+' <span ng-show="ratingValue.rating > 5" class="rate-me"><b>Rate me</b></span>',
            scope : {
                ratingValue : '=',
                max : '=',
                onRatingSelected : '&'
            },
            link : function(scope, elem, attrs) {
                var updateStars = function() {
                    scope.stars = [];
                    for ( var i = 0; i < scope.max; i++) {
                        scope.stars.push({
                            filled : i <= scope.ratingValue.rating
                        });
                    }
                };
             
                scope.toggle = function(index) {
                    scope.ratingValue.rating = index;
                    scope.onRatingSelected({
                        rating : index
                    });
                    // /rate/<usid>/<fid>/<uid>/<rating>
                    var usi = scope.ratingValue;
                    fmpService.rate(usi.usid, usi.fid, usi.uid, index, usi);
                };
             
                scope.$watch('ratingValue.rating',
                    function(oldVal, newVal) {
                        updateStars();
                });
            }
        };
}]);

fmpApp.controller('popoverCtrl', ['$scope', '$modal', 'fmpService',
    function($scope, $modal, $fmpService) {

    // Pre-fetch an external template populated with a custom scope
    var infoModal = $modal({
        scope: $scope, 
        template: '/static/templates/popover.tpl.html', 
        show: false,
        container: "body"
    });
    // Show when some event occurs (use $promise property to ensure the template has been loaded)
    $scope.showModal = function() {
        infoModal.$promise.then(infoModal.show);
    };

    
}]);

fmpApp.controller('PreloadCtrl', ['$scope', '$routeParams', 'fmpService', '$location', 
                                  '$modal',
    function($scope, $routeParams, fmpService, $location, $modal) {
        window.document.title = "fmp - Preload";
        $scope.queryUrl = '/preload';
        fmpService.initPagination($scope, $routeParams, $location, $modal);
}]);

fmpApp.controller('SearchCtrl', ['$scope', '$rootScope', '$routeParams', 
                                 'fmpService', '$modal', '$location',
    function($scope, $rootScope, $routeParams, fmpService, $modal, $location) {
    window.document.title = "fmp - Search";
    $scope.ctrler = "SearchCtrl";

    // Pre-fetch an external template populated with a custom scope

    console.log("SearchCtrl initialized")

    // $scope.getTags = fmpService.getTags;
    $scope.query = $routeParams.query || "";
    $scope.queryUrl = '/search-data-new/?q='+encodeURIComponent($scope.query);
    $scope.keyup = function(evt){
        if (evt.keyCode == 13) {
            document.location = "#/search/"+encodeURIComponent(evt.currentTarget.value);
        }
    };
    fmpService.initPagination($scope, $routeParams, $location, $modal);

}]);

fmpApp.controller('CurrentlyPlayingCtrl',['$scope', 'fmpService', '$modal', '$location',
    function($scope, fmpService, $modal, $location){
        $scope.next = fmpService.next;
        $scope.pause = fmpService.pause;
        $scope.prev = fmpService.prev;
    $scope.r = {};

    $scope.$watch('playing_data', function(newValue, oldValue) {
        // populate $scope.r so the modal dialog shows up.
        $scope.r = $scope.playing_data;
        // $scope.r['hide_cued'] = true;
    });

    // Pre-fetch an external template populated with a custom scope
    var infoModal = $modal({
        scope: $scope, 
        template: '/static/templates/popover.tpl.html', 
        show: false,
        container: "body",
        element: true
    });
    // Show when some event occurs (use $promise property to ensure the template has been loaded)
    $scope.showModal = function() {
        infoModal.$promise.then(infoModal.show);
    };

    $scope.navClass = function (page) {
        var currentRoute = $location.path().substring(1) || 'home';
        // var re = new RegExp("ab+c");
        if (page == 'search') {
            return currentRoute.indexOf(page) == 0 ? 'active' : '';
        }
        return page === currentRoute ? 'active' : '';
    };

    $scope.doSearchNow = function() {
        $scope.cancelTimeout();
        document.location = "#/search/"+encodeURIComponent($scope.query);
    };
}]);




fmpApp.controller('HistoryCtrl', ['$scope', '$routeParams', 'fmpService', 
                                  '$location', '$modal',
    function($scope, $routeParams, fmpService, $location, $modal) {
    window.document.title = "fmp - History";
    $scope.queryUrl = '/history-data/';
    $scope.ctrler = "";
    fmpService.initPagination($scope, $routeParams, $location, $modal);
}]);

fmpApp.controller("ListenersCtrl", ['$scope', '$http', function($scope, $http){
    $http({method: 'GET', url: "/users/"})
    .success(function(data, status, headers, config) {
        $scope.users = data;
    })
    .error(function(data, status, headers, config) {
      // called asynchronously if an error occurs
      // or server returns response with an error status.
    });
    $scope.setListening = function(uid, listening) {
        console.log("setListening:", uid, listening);
        $http({method: 'GET', url: "/listening/"+uid+"/"+listening})
        .success(function(data, status, headers, config) {
            for (var i=0;i<$scope.users.length;i++) {
                if ($scope.users[i]['uid'] == uid) {
                    $scope.users[i]['listening'] = listening;
                }
            }
        })
        .error(function(data, status, headers, config) {
          // called asynchronously if an error occurs
          // or server returns response with an error status.
        });
    };
}]);

fmpApp.controller("PodcastCtrl", ['$scope','$http', '$location', '$modal', 
  function($scope, $http, $location, $modal){
    $scope.oneAtATime = false;
    $scope.podcasts = [];
    $scope.subscribers = [];
    var url = "";
     $http({method: 'GET', url: "/podcasts/"})
    .success(function(data, status, headers, config) {
        console.log("re-fetched");
        $scope.podcasts = data;
    })
    .error(function(data, status, headers, config) {
      // called asynchronously if an error occurs
      // or server returns response with an error status.
    });

    $scope.loadEpisodes = function(nid, open) {
        
        $http({method: 'GET', url: "/feed-data/"+nid})
        .success(function(data, status, headers, config) {
            for (var i=0;i<$scope.podcasts.length;i++) {
                if ($scope.podcasts[i].nid == nid) {
                    for (i2=0;i2< data['episodes'].length; i2++) {
                        data['episodes'][i2]['pub_date'] = new Date(data['episodes'][i2]['pub_date']).toLocaleString(); 
                    }
                    $scope.podcasts[i].episodes = data['episodes'];
                    $scope.podcasts[i].subscribers = data['subscribers'];
                }
            }
        })
        .error(function(data, status, headers, config) {
          // called asynchronously if an error occurs
          // or server returns response with an error status.
        });
    };

    $scope.selectedIcons = ['Globe', 'Heart'];
    $scope.listeners = [
        {value: 'Gear', label: 'Gear'},
        {value: 'Globe', label: 'Globe'},
        {value: 'Heart', label: 'Heart'},
        {value: 'Camera', label: 'Camera'}
    ];

    $scope.subscribe = function(nid, uid, subscribe){
        console.log("nid:", nid);
        console.log("uid:", uid);
        console.log("subscribe:", subscribe);
        $http({method: 'GET', url: "/subscribe/"+nid+"/"+uid+"/"+subscribe})
        .success(function(data, status, headers, config) {
            for (var i=0;i<$scope.podcasts.length;i++) {
                if ($scope.podcasts[i].nid == nid) {
                    for (i2=0;i2< data['episodes'].length; i2++) {
                        data['episodes'][i2]['pub_date'] = new Date(data['episodes'][i2]['pub_date']).toLocaleString(); 
                    }
                    $scope.podcasts[i].episodes = data['episodes'];
                    $scope.podcasts[i].subscribers = data['subscribers'];
                }
            }
        })
        .error(function(data, status, headers, config) {
          // called asynchronously if an error occurs
          // or server returns response with an error status.
        });
    };

    var infoModal = $modal({
        scope: $scope,
        template: '/static/templates/add-feed.tpl.html', 
        show: false, 
        container: "body"
    });
    // Show when some event occurs (use $promise property to ensure the template has been loaded)
    $scope.showAddFeedModal = function() {
        $scope.newFeedUrl = "";
        infoModal.$promise.then(infoModal.show);
    };

    $scope.addFeed = function (newFeedUrl) {
        $scope.feedError = "Fetching feeds ...";
        $http({method: 'GET', url:"/add-rss-feed/?url="+encodeURIComponent(newFeedUrl)})
        .success(function(data, status, headers, config) {
            $scope.feedError = "";
            infoModal.hide();
            var d = new Date();
            document.location = "#/podcasts?_="+ d.valueOf();
        })
        .error(function(data, status, headers, config) {
          // called asynchronously if an error occurs
          // or server returns response with an error status.
          $scope.feedError = "Error Fetching feed";
        });
    };


}]);


function AccordionDemoCtrl($scope) {
  $scope.oneAtATime = true;

  $scope.groups = [
    {
      title: 'Dynamic Group Header - 1',
      content: 'Dynamic Group Body - 1'
    },
    {
      title: 'Dynamic Group Header - 2',
      content: 'Dynamic Group Body - 2'
    }
  ];

  $scope.items = ['Item 1', 'Item 2', 'Item 3'];

  $scope.addItem = function() {
    var newItemNo = $scope.items.length + 1;
    $scope.items.push('Item ' + newItemNo);
  };

  $scope.status = {
    isFirstOpen: true,
    isFirstDisabled: false
  };
}

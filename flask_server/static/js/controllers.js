var fmpApp = angular.module('fmpApp', ['ui.bootstrap',
    'mgcrea.ngStrap', 'mgcrea.ngStrap.modal', 
    'mgcrea.ngStrap.aside', 'mgcrea.ngStrap.tooltip', 
    'mgcrea.ngStrap.typeahead',
    'ngRoute','infinite-scroll'
    
]);


fmpApp.config(['$routeProvider',
    function($routeProvider) {
        $routeProvider.when('/home', {
            templateUrl: '/static/templates/home.html',
            controller: 'HomeCtrl'
        })
        .when("/search", {
            templateUrl: "/static/templates/search.html",
            controller: "SearchCtrl"
        })
        .when("/search/:query", {
            templateUrl: "/static/templates/search.html",
            controller: "SearchCtrl"
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
        .otherwise({
            redirectTo: '/home'
        });
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
        _this.items.push(items[i]);
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
        current = new Date(historyArray[$index]['date_played']), 
        next = new Date (historyArray[$index+1]['date_played']),
        ms = current.valueOf() - next.valueOf(),
        seconds = Math.floor(ms / 1000),
        months = Math.floor(seconds / seconds_in_a_month),
        seconds = seconds - (months * seconds_in_a_month),
        weeks = Math.floor(seconds / seconds_in_a_week),
        seconds = Math.floor(seconds - (weeks * seconds_in_a_week)),
        hours = Math.floor(seconds / seconds_in_an_hour),
        seconds = Math.floor(seconds - (hours * seconds_in_an_hour)),
        minutes = seconds / 60,
        seconds = Math.floor(seconds - (minutes * 60));

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
    return hours+":"+minutes+":"+seconds;
};

fmpApp.factory('fmpService', ['$rootScope','$http', '$interval', '$timeout', '$q',
    function($rootScope, $http, $interval, $timeout, $q){
        var sharedService = {};
        sharedService.cue = function($scope, fid) {
            console.log("CUE");
            for (var i=0; i<$scope.search.items.length; i++) {
                if ($scope.search.items[i].fid == fid) {
                    $scope.search.items[i].cued = fid;
                    var url = "/cue/?fid="+fid+"&cue=true"
                    $http({method: 'GET', url: url})
                    .success(function(data, status, headers, config) {

                    })
                    .error(function(data, status, headers, config) {
                      // called asynchronously if an error occurs
                      // or server returns response with an error status.
                    });
                }
            }
        };
        sharedService.uncue = function($scope, fid) {
            console.log("UNCUE");
            for (var i=0; i<$scope.search.items.length; i++) {
                if ($scope.search.items[i].fid == fid) {
                    $scope.search.items[i].cued = false;
                    var url = "/cue/?fid="+fid+"&cue=false"
                    $http({method: 'GET', url: url})
                    .success(function(data, status, headers, config) {
                        

                    })
                    .error(function(data, status, headers, config) {
                      // called asynchronously if an error occurs
                      // or server returns response with an error status.
                    });
                }
            }
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

        sharedService.rate = function(usid, fid, uid, rating){
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
            $http({method: 'GET', url: '/status/'})
                .success(function(data, status, headers, config) {
                    // this callback will be called asynchronously
                    // when the response is available
                    // console.log("data:", data.extended.history);
                    sharedService.processStatus(data);
                })
                .error(function(data, status, headers, config) {
                  // called asynchronously if an error occurs
                  // or server returns response with an error status.
                });
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

        sharedService.getStatus();
        $interval(sharedService.getStatus, 10000);
        return sharedService;
}]);


fmpApp.controller('CurrentlyPlayingCtrl',['$scope', 'fmpService', function($scope, fmpService){
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
                       '<span ng-show="$index > 0">\u2605</span></li></ul>',
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
                    fmpService.rate(usi.usid, usi.fid, usi.uid, index);
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

fmpApp.controller('PreloadCtrl', ['$scope', '$routeParams', 'fmpService', '$http', 'Search',
    function($scope, $routeParams, fmpService, $http, Search) {
    window.document.title = "fmp - Preload";
    $scope.cue = function(fid) {
        fmpService.cue($scope, fid);
    };
    $scope.uncue = function(fid) {
        fmpService.uncue($scope, fid);
    };
    $scope.search = new Search("", "/preload", 0, 20);
}]);

fmpApp.controller('SearchCtrl', ['$scope', '$rootScope', '$routeParams', 
                                 'fmpService', '$http', '$modal', 'Search',
    function($scope, $rootScope, $routeParams, fmpService, $http, $modal, Search) {
    window.document.title = "fmp - Search";
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

    $scope.new_artist = "";

    // $scope.getTags = fmpService.getTags;

    $scope.cue = function(fid) {
        fmpService.cue($scope, fid);
    };
    $scope.uncue = function(fid) {
        fmpService.uncue($scope, fid);
    };
    $scope.removeGenre = fmpService.removeGenre;

    console.log("TOP");
    $scope.query = $routeParams.query;
    if (!$scope.query) {
        $scope.query = "";
    }

    $scope.search = new Search($scope.query);

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

fmpApp.controller('HistoryCtrl', ['$scope', '$routeParams', 'fmpService', '$http', 'Search',
    function($scope, $routeParams, fmpService, $http, Search) {
    window.document.title = "fmp - history";
    $scope.cue = function(fid) {
        fmpService.cue($scope, fid);
    };
    $scope.uncue = function(fid) {
        fmpService.uncue($scope, fid);
    };
    $scope.search = new Search("", "/history-data/", 0, 20);
}]);


fmpApp.controller("PodcastCtrl", ['$scope','$http', '$location', function($scope, $http, $location){
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
        console.log("CLICKED", nid)
        
        $http({method: 'GET', url: "/feed-data/"+nid})
        .success(function(data, status, headers, config) {
            for (var i=0;i<$scope.podcasts.length;i++) {
                if ($scope.podcasts[i].nid == nid) {
                    for (i2=0;i2< data.length; i2++) {
                        data[i2]['pub_date'] = new Date(data[i2]['pub_date']).toLocaleString(); 
                    }
                    $scope.podcasts[i].episodes = data;
                }
            }
        })
        .error(function(data, status, headers, config) {
          // called asynchronously if an error occurs
          // or server returns response with an error status.
        });
    }
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

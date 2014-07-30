
var fmpApp = angular.module("fmpApp", [
        'ngRoute', 'ngTagsInput', 'mgcrea.ngStrap', 'mgcrea.ngStrap.modal', 
        'mgcrea.ngStrap.aside', 'mgcrea.ngStrap.tooltip', 
        'mgcrea.ngStrap.typeahead', 'infinite-scroll', 'angular-inview'])
        .filter('isEmpty', function () {
            var bar;
            return function (obj) {
                for (bar in obj) {
                    if (obj.hasOwnProperty(bar)) {
                        return false;
                    }
                }
                return true;
            };
        }),
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

fmpApp.factory('fmpService', ['$rootScope','$http', '$interval',
    function($rootScope, $http, $interval){
        var sharedService = {};
        sharedService.cue = function(fid) {
            for (var i=0; i<$scope.results.length; i++) {
                if ($scope.results[i].fid == fid) {
                    $scope.results[i].cued = fid;
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
        sharedService.uncue = function(fid) {
            for (var i=0; i<$scope.results.length; i++) {
                if ($scope.results[i].fid == fid) {
                    $scope.results[i].cued = false;
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

        sharedService.getStatus();
        $interval(sharedService.getStatus, 10000);
        return sharedService;
}]);

fmpApp.directive('starRating',['fmpService',
    function(fmpService) {
        return {
            restrict : 'A',
            template : '<ul class="rating"> <li ng-repeat="star in stars" ng-class="star" ng-click="toggle($index)">  <a ng-show="!$index">&nbsp;\u20E0&nbsp;</a><i ng-show="$index > 0">\u2605</i></li></ul>',
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

fmpApp.config(['$routeProvider',
    function($routeProvider) {
        $routeProvider.when('/', {
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
        .otherwise({
            redirectTo: '/'
        });
    }]);


fmpApp.controller("NavCtrl", ['$scope', '$rootScope', '$location', 'fmpService', 
    function($scope, $rootScope, $location, fmpService){
        $scope.next = fmpService.next;
        $scope.prev = fmpService.prev;
        $scope.pause = fmpService.pause;
        $scope.getTags = fmpService.getTags;

        $scope.navClass = function (page) {
            var currentRoute = $location.path().substring(1) || 'home';
            // var re = new RegExp("ab+c");
            if (page == 'search') {
                return currentRoute.indexOf(page) == 0 ? 'active' : '';
            }
            return page === currentRoute ? 'active' : '';
        };
        $scope.doSearch = function() {
            // console.log("$scope.query:",$scope.query);
            if ($scope.timeout) {
                clearTimeout($scope.timeout);
            }
            $scope.timeout = setTimeout(function(){
                document.location = "#/search/"+encodeURIComponent($scope.query);
                $scope.timeout = false;
            }, 1000);
            
        };

        $scope.doSearchNow = function() {
            if ($scope.timeout) {
                clearTimeout($scope.timeout);
            }
            document.location = "#/search/"+encodeURIComponent($scope.query);
        };
}]);

fmpApp.controller('HomeCtrl', ['$scope', '$routeParams', 'fmpService',
    function($scope, $routeParams) {
    
}]);


fmpApp.controller('popoverCtrl', ['$scope', '$modal', 'fmpService',
    function($scope, $modal, $fmpService) {

    var myModal = $modal({title: 'My Title', content: 'My Content', show: true});

    // Pre-fetch an external template populated with a custom scope
    var myOtherModal = $modal({scope: $scope, template: '/static/templates/popover.tpl.html', show: false});
    // Show when some event occurs (use $promise property to ensure the template has been loaded)
    $scope.showModal = function() {
        myOtherModal.$promise.then(myOtherModal.show);
    };

    
}]);

fmpApp.controller('PreloadCtrl', ['$scope', '$routeParams', 'fmpService', '$http', 'Search',
    function($scope, $routeParams, fmpService, $http, Search) {

    $scope.cue = fmpService.cue;
    $scope.uncue = fmpService.uncue;
    
    $scope.search = new Search("", "/preload");
    
}]);

fmpApp.controller('SearchCtrl', ['$scope', '$rootScope', '$routeParams', 'fmpService', '$http', '$modal', 'Search',
    function($scope, $rootScope, $routeParams, fmpService, $http, $modal, Search) {

    // Pre-fetch an external template populated with a custom scope
    var myOtherModal = $modal({scope: $scope, template: '/static/templates/popover.tpl.html', show: false});
    // Show when some event occurs (use $promise property to ensure the template has been loaded)
    $scope.showModal = function() {
        myOtherModal.$promise.then(myOtherModal.show);
    };

    $scope.new_artist = "";

    $scope.getTags = fmpService.getTags;

    $scope.cue = fmpService.cue;
    $scope.uncue = fmpService.uncue;
    $scope.removeGenre = fmpService.removeGenre;

    //console.log("TOP");
    $scope.query = $routeParams.query;
    if (!$scope.query) {
        $scope.query = "";
    }

    $scope.search = new Search($scope.query);

}]);

fmpApp.controller('CurrentlyPlayingCtrl',['$scope', 'fmpService', '$modal',
    function($scope, fmpService, $modal){
        $scope.next = fmpService.next;
        $scope.pause = fmpService.pause;
        $scope.prev = fmpService.prev;
    console.log($scope.playing_data)

    $scope.$watch('playing_data', function(newValue, oldValue) {
        $scope.r = $scope.playing_data;
    });
}]);

// Reddit constructor function to encapsulate HTTP and pagination logic
fmpApp.factory('Search', function($http) {
  var Search = function(query, url) {
    this.items = [];
    this.busy = false;
    this.after = '';
    this.start = 0;
    this.limit = 10;
    this.url = url || "/search-data-new/";
    this.query = encodeURIComponent(query || "");
    this.inview = function($index, inview){
        if (inview && !this.items[$index]['ratings']) {
            this.items[$index] = this.cacheItems[$index];
        }
    };
  };

  Search.prototype.nextPage = function() {
    if (this.busy) return;
    this.busy = true;

    var url = this.url+"?s="+this.start+"&l="+this.limit+"&q="+this.query;
    $http.get(url).success(function(data) {
      var items = data;
      for (var i = 0; i < items.length; i++) {
        this.items.push(items[i]);
      }
      // this.after = "t3_" + this.items[this.items.length - 1].id;''
      this.start = this.start + this.limit;
      this.busy = false;
    }.bind(this));
  };

  return Search;
});

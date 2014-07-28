
var fmpApp = angular.module("fmpApp", ['ngRoute', 'mgcrea.ngStrap', 'mgcrea.ngStrap.modal', 'mgcrea.ngStrap.aside', 'mgcrea.ngStrap.tooltip', 'mgcrea.ngStrap.typeahead']),
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
        sharedService.getStatus();
        $interval(sharedService.getStatus, 10000);
        return sharedService;
}]);

fmpApp.directive('starRating',['fmpService',
    function(fmpService) {
        return {
            restrict : 'A',
            template : '<ul class="rating"> <li ng-repeat="star in stars" ng-class="star" ng-click="toggle($index)">  <i class="fa fa-star-o">\u2605</i> </li></ul>',
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
                            filled : i < scope.ratingValue.rating
                        });
                    }
                };
             
                scope.toggle = function(index) {
                    scope.ratingValue.rating = index + 1;
                    scope.onRatingSelected({
                        rating : index + 1
                    });
                    // /rate/<usid>/<fid>/<uid>/<rating>
                    var usi = scope.ratingValue;
                    fmpService.rate(usi.usid, usi.fid, usi.uid, index+1);
                };
             
                scope.$watch('ratingValue.rating',
                    function(oldVal, newVal) {
                        if (newVal) {
                            updateStars();
                        }
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
    $scope.modal = "?"
    var myModal = $modal({title: 'My Title', content: 'My Content', show: true});

      // Pre-fetch an external template populated with a custom scope
      var myOtherModal = $modal({scope: $scope, template: '/static/templates/popover.tpl.html', show: false});
      // Show when some event occurs (use $promise property to ensure the template has been loaded)
      $scope.showModal = function() {
        myOtherModal.$promise.then(myOtherModal.show);
      };
}]);

fmpApp.controller('PreloadCtrl', ['$scope', '$routeParams', 'fmpService', '$http',
    function($scope, $routeParams, fmpService, $http) {
    $scope.cue = function(fid) {
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
    $scope.uncue = function(fid) {
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

    //console.log("TOP");
    $scope.query = $routeParams.query;
    if (!$scope.start) {
        // console.log("$scope.start:", $scope.start);
        $scope.start = 0;
    }
    ///console.log("$scope.start:", $scope.start);
    ///console.log("query:",$scope.query);

    if (!$scope.results) {
        $scope.results = [];
        $scope.locked = false;
    }

    $scope.loadMore = function(){
        if ($scope.done || $scope.locked) {
            // console.log("$scope.done,", $scope.done)
            return;
        }
        $scope.locked = true;
        $("#preload-loading").show();
        var url = "/preload";
        $scope.start += 10;
        $http({method: 'GET', url: url})
        .success(function(data, status, headers, config) {
            // console.log("-scope start:", $scope.start);
            $("#preload-loading").hide();
            if (data.length == 0) {
                $scope.done = true;
                // console.log("DONE!");
                $(window).unbind("scroll");
            }
            for(var i=0;i<data.length;i++) {
                // console.log("appending:", data[i]);
                $scope.results.push(data[i]);
            }
            $scope.locked = true;
            $scope.done = true;
             $(window).unbind("scroll");
        })
        .error(function(data, status, headers, config) {
          $scope.locked = false;
          // called asynchronously if an error occurs
          // or server returns response with an error status.
        });
    }
    $scope.loadMore();
}]);

fmpApp.controller('SearchCtrl', ['$scope', '$rootScope', '$routeParams', 'fmpService', '$http', '$modal',
    function($scope, $rootScope, $routeParams, fmpService, $http, $modal) {

    // Pre-fetch an external template populated with a custom scope
    var myOtherModal = $modal({scope: $scope, template: '/static/templates/popover.tpl.html', show: false});
    // Show when some event occurs (use $promise property to ensure the template has been loaded)
    $scope.showModal = function() {
        myOtherModal.$promise.then(myOtherModal.show);
    };

    $scope.new_artist = "";

    $scope.getTags = fmpService.getTags;

    $scope.cue = function(fid) {
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
    $scope.uncue = function(fid) {
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

    $scope.removeGenre = function(fid, gid){
        console.log("fid:", fid);
        console.log("gid:", gid);
        var found = false
        for (var i=0; i<$scope.results.length; i++) {
            if (found) {
                break;
            }
            if ($scope.results[i].fid == fid) {
                if (!$scope.results[i]['genres']) {
                    return;
                }
                for (var i2=0; i2<$scope.results[i]['genres'].length; i2++) {
                    if ($scope.results[i]['genres'][i2]['gid'] == aid) {
                        $scope.results[i]['genres'].splice(i2, 1);
                        found = true;
                        var url = "/remove-file-genre/?fid="+fid+"&gid="+gid
                        $http({method: 'GET', url: url})
                        .success(function(data, status, headers, config) {
                            
                        })
                        .error(function(data, status, headers, config) {
                        });
                    }
                }
            }
        }
    };

    $scope.removeArtist = function(fid, aid){
        console.log("fid:", fid);
        console.log("aid:", aid);
        var found = false
        for (var i=0; i<$scope.results.length; i++) {
            if (found) {
                break;
            }
            if ($scope.results[i].fid == fid) {
                if (!$scope.results[i]['artists']) {
                    return;
                }
                for (var i2=0; i2<$scope.results[i]['artists'].length; i2++) {
                    if ($scope.results[i]['artists'][i2]['aid'] == aid) {
                        $scope.results[i]['artists'].splice(i2, 1);
                        found = true;
                        var url = "/remove-file-artist/?fid="+fid+"&aid="+aid
                        $http({method: 'GET', url: url})
                        .success(function(data, status, headers, config) {
                            
                        })
                        .error(function(data, status, headers, config) {
                        });
                    }
                }
            }
        }
    };

    $scope.showCreateArtist = function (fid) {
        $scope.creatingArtist = true;
        $scope.new_artist = "";
    };

    $scope.setNewArtist = function(val) {
        $scope.new_artist = val;
    }

    $scope.assignArtist = function(fid) {
        $scope.creatingArtist = false;
        if (!$scope.new_artist) {
            return;
        }
        for (r in $scope.results) {
            console.log("r:",r);
            console.log("$scope.new_artist",$scope.new_artist)
            if ($scope.results[r]['fid'] != fid) {
                continue
            }
            var found = false;
            for (a in $scope.results[r]['artists']) {
                if ($scope.results[r]['artists'][a]['artist'] == $scope.new_artist) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                $scope.results[r]['artists'].push({
                    "aid": -1,
                    "artist": $scope.new_artist
                });
                var url = "/add-file-artist/?fid="+fid+"&artist="+encodeURIComponent($scope.new_artist);
                $http({method: 'GET', url: url})
                .success(function(data, status, headers, config) {
                    
                })
                .error(function(data, status, headers, config) {
                });
                // $scope.new_artist = "";
            }
        }
    };

    //console.log("TOP");
    $scope.query = $routeParams.query;
    $rootScope.query = $scope.query;
    if (!$scope.query) {
        $scope.query = "";
    }
    if (!$scope.start) {
        // console.log("$scope.start:", $scope.start);
        $scope.start = 0;
    }
    ///console.log("$scope.start:", $scope.start);
    ///console.log("query:",$scope.query);

    if (!$scope.results) {
        $scope.results = [];
        $scope.locked = false;
        $scope.done = false;
    }

    $scope.loadMore = function(){
        if ($scope.done || $scope.locked) {
            // console.log("$scope.done,", $scope.done);
            // console.log("$scope.locked:", $scope.locked);
            return;
        }
        $scope.locked = true;
        $("#search-loading").show();
        var url = "/search-data-new/?q="+encodeURIComponent($scope.query)+"&s="+$scope.start;
        $scope.start += 10;
        $http({method: 'GET', url: url})
        .success(function(data, status, headers, config) {
            // console.log("-scope start:", $scope.start);
            $("#search-loading").hide();
            if (data.length == 0) {
                $scope.done = true;
                // console.log("DONE! ***************************");
                $(window).unbind("scroll");
                $scope.locked = false;
                return
            }
            for(var i=0;i<data.length;i++) {
                // console.log("appending:", data[i]);
                $scope.results.push(data[i]);
            }
            $scope.locked = false;
        })
        .error(function(data, status, headers, config) {
          $scope.locked = false;
          // called asynchronously if an error occurs
          // or server returns response with an error status.
        });
    }
    $scope.loadMore();
    // console.log("SCOPE:", $scope);

}]);

fmpApp.controller('CurrentlyPlayingCtrl',['$scope', 'fmpService',
    function($scope, fmpService){
        $scope.next = fmpService.next;
        $scope.pause = fmpService.pause;
        $scope.prev = fmpService.prev;
}]);


fmpApp.directive('scroller', function () {
    return {
        restrict: 'A',
        // new
        scope: {
            loadingMethod: "&"
        },
        link: function (scope, elem, attrs) {
            $window = $(window);
            $document = $(document);
            $(window).unbind("scroll");
            $(window).bind('scroll', function () {
                if (scope.done) {
                    $(window).unbind("scroll");
                    console.log("UNBIND");
                    return;
                }
                if ($window.scrollTop() + ($window.height() * 2) >= 
                    ($document.height() - $window.height())) {
                    console.log("$apply")
                    scope.$apply(scope.loadingMethod); 
                }
            });
        }
    };
});



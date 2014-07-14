
var fmpApp = angular.module("fmpApp", ['ngRoute']),
    timeBetween = function(historyArray, $index) {
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
    }

fmpApp.factory('fmpService', ['$rootScope','$http', '$interval',
    function($rootScope, $http, $interval){
        var sharedService = {};
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
                console.log("TEST:", data);
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
                console.log("playing_data.ratings", $rootScope.playing_data.ratings)
                for(key in $rootScope.playing_data.ratings) {
                    var rating = $rootScope.playing_data.ratings[key];
                    console.log("rating:", rating);
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
                    console.log("data:", data.extended.history);
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
        .when("/search/:query", {
            templateUrl: "/static/templates/search.html",
            controller: "SearchCtrl"
        })
        .otherwise({
            redirectTo: '/'
        });
    }]);


fmpApp.controller("NavCtrl", ['$scope', '$location', 'fmpService', 
    function($scope, $location){
        $scope.navClass = function (page) {
            var currentRoute = $location.path().substring(1) || 'home';
            return page === currentRoute ? 'active' : '';
        };
}]);

fmpApp.controller('HomeCtrl', ['$scope', '$routeParams', 'fmpService',
    function($scope, $routeParams) {
    
}]);

fmpApp.controller('SearchCtrl', ['$scope', '$routeParams', 'fmpService', '$http',
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

    console.log("TOP");
    $scope.query = $routeParams.query;
    if (!$scope.start) {
        // console.log("$scope.start:", $scope.start);
        $scope.start = 0;
    }
    console.log("$scope.start:", $scope.start);
    console.log("query:",$scope.query);

    if (!$scope.results) {
        $scope.results = [];
        $scope.locked = false;
    }

    $scope.loadMore = function(){
        if ($scope.done || $scope.locked) {
            console.log("$scope.done,", $scope.done)
            return;
        }
        $scope.locked = true;
        // $scope.results.push({"title": "start:"+$scope.start})

        console.log("+scope start:", $scope.start);
        var url = "/search-data-new/?q="+encodeURIComponent($scope.query)+"&s="+$scope.start;
        $scope.start += 10;
        $http({method: 'GET', url: url})
        .success(function(data, status, headers, config) {
            // console.log("-scope start:", $scope.start);
            
            if (data.length == 0) {
                $scope.done = true;
                console.log("DONE!");
                $(window).unbind("scroll");
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
            $(window).bind('scroll', function () {
                if (scope.done) {
                    $(window).unbind("scroll");
                    console.log("UNBIND");
                    return;
                }
                if ($window.scrollTop() + ($window.height() * 2) >= 
                    ($document.height() - $window.height())) {
                    scope.$apply(scope.loadingMethod); 
                }
            });
        }
    };
});



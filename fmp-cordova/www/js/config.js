fmpApp.config(['$routeProvider', '$locationProvider', function($routeProvider, $locationProvider){
    $routeProvider
    .when('/playlist', {
        templateUrl: 'partials/playlist.html',
        controller: 'PlaylistCtrl',
        reloadOnSearch: false
    })
    .when('/player', {
        templateUrl: 'partials/player.html',
        controller: 'PlayerController'
    })
    .when("/listeners", {
        templateUrl: 'partials/listeners.html',
        controller: 'ListenersController'
    })
    .otherwise({
        redirectTo: '/playlist'
    });
}]);

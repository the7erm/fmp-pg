fmpApp.config(['$routeProvider', '$locationProvider', 'growlProvider', function($routeProvider, $locationProvider, growlProvider){
    growlProvider.globalTimeToLive(5000);
    growlProvider.globalPosition('bottom-left');
    $routeProvider
    .when('/playlist', {
        templateUrl: 'partials/playlist.html',
        controller: 'PlaylistCtrl',
        reloadOnSearch: false
    })
    .when('/player', {
        templateUrl: 'partials/player.html',
        controller: 'PlaylistCtrl',
        reloadOnSearch: false
    })
    .when("/listeners", {
        templateUrl: 'partials/listeners.html',
        controller: 'ListenersController',
        reloadOnSearch: false
    })
    .when("/remote",{
        templateUrl: "partials/remote.html",
        controller: "RemoteController",
        reloadOnSearch: false
    })
    .otherwise({
        redirectTo: '/player'
    });
}]);

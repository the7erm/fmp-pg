var fmpApp = angular.module('fmpApp', [
    'ngRoute',
    'ngTouch',
    'ngWebSocket',
    'rzModule'
]);

fmpApp.filter('formatTimer', function () {
    return function (input) {
        var z = function (n) { return (n < 10 ? '0' : '') + n; }
        var seconds = Math.floor(input % 60);
        var minutes = Math.floor((input % 3600) / 60);
        var hours = Math.floor(input / 3600);
        if (hours > 0) {
            return (hours + ':' + z(minutes) + ':' + z(seconds));
        }
        return (minutes + ':' + z(seconds));
    };
});

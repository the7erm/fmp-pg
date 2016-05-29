var fmpApp = angular.module('fmpApp', [
    'ngRoute',
    'ngTouch',
    'ngWebSocket',
    'rzModule',
    'angular-inview'
]).filter('filterPlaylist', function() {
    return function(input, search) {
      if (!input) return input;
      if (!search) return input;
      var expected = ('' + search).toLowerCase();
      var result = {};
      angular.forEach(input, function(value, key) {
        var actual = ('' + value.keywords_txt).toLowerCase();
        if (actual.indexOf(expected) !== -1) {
          result[key] = value;
        }
      });
      return result;
    }
});

fmpApp.filter('formatTimer', function () {
    return function (input) {
        // console.log("formatTimer:", input);
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

fmpApp.factory('FmpConfig', function($rootScope){
  /*
      Media.MEDIA_NONE = 0;
      Media.MEDIA_STARTING = 1;
      Media.MEDIA_RUNNING = 2;
      Media.MEDIA_PAUSED = 3;
      Media.MEDIA_STOPPED = 4;
  */
  var collection = {
    'url': '',
    'cacheDir': null
  };

  return collection;
});

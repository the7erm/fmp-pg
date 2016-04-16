fmpApp.factory('FmpConfig', function($rootScope){
  var logger = new Logger("FmpConfig", false);
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

  logger.log("initialized");
  return collection;
});

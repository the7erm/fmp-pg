fmpApp.factory("FmpIpScanner", function($http, $rootScope){
  var logger = new Logger("FmpIpScanner", true);
  logger.log("Connection:", navigator.connection);
  var collection = {
        "knownHosts": [],
        "scanHosts": [],
        "url": "",
        "socketUrl": "",
        "scanLock": false
      },
      methods = {
        collection: collection
      };


  methods.getKnownHosts = function() {
    var knownHosts = [];
    if (localStorage.knownHosts) {
      knownHosts = JSON.parse(localStorage.knownHosts);
    }
    collection.knownHosts = knownHosts;
    logger.log("collection.knownHosts:", collection.knownHosts);
  }

  methods.generateHosts = function() {
    collection.scanHosts = [];
    methods.getKnownHosts();
    for (var i=0;i<collection.knownHosts.length;i++) {
      var host = collection.knownHosts[i];
      if (collection.scanHosts.indexOf(host) == -1) {
        collection.scanHosts.push(host);
        logger.log("adding known host:", host);
      }
    }
    for(var i=1;i<255;i++) {
      var host = 'http://192.168.1.'+i+':5050/';
      if (collection.scanHosts.indexOf(host) == -1) {
        collection.scanHosts.push(host);
      }
    }
  }

  methods.scan = function(thread, FmpConfig) {
    if (collection.scanLock) {
        return;
    }
    if (collection.found || collection.scanHosts.length == 0) {
      return;
    }
    if (navigator.connection.type != Connection.WIFI) {
      logger.log("skipping !",Connection.WIFI);
      return;
    }
    if (thread == 4) {
      collection.scanLock = true;
    }
    var host = collection.scanHosts.shift();
    // logger.log("scan thread:", thread, host);
    try {
      logger.log("methods.scan:",host);
      $http({
          method: 'GET',
          url: host+"fmp_version",
          timeout: 100
      }).then(function(response) {
        if (response.data.fmp) {
          collection.found = true;
          collection.url = host;
          collection.socketUrl = host.replace("http://", "ws://")+"ws";
          var scanEnd = new Date();
          if (collection.knownHosts.indexOf(host) == -1) {
            collection.knownHosts.push(host);
            localStorage.knownHosts = JSON.stringify(collection.knownHosts);
          }
          window.fmpHost = host;
          logger.log("found fmp server at host:", host);
          logger.log("Running time:", scanEnd.valueOf() -
                                       collection.scanStart.valueOf());
          $rootScope.$broadcast("server-found");
          collection.scanLock = false;
        }
      }, function errorCallback(response) {
        try {
          methods.scan(thread, FmpConfig);
        } catch(e) {
          logger.log("methods.scan:",e);
        }
        collection.scanLock = false;
      });
    } catch(e) {
      logger.log("$http catch", e);
    }


  };

  methods.startScan = function(FmpConfig) {
    logger.log("startScan()");
    collection.found = false;
    methods.generateHosts();
    collection.scanStart = new Date();
    for (var i=1;i<=5;i++) {
      try {
        logger.log("started thread:",i);
        methods.scan(i, FmpConfig);
      } catch(e) {
        logger.log("methods.scan:",e);
      }
    }
  }
  logger.log("FmpIpScanner: Initialized");
  return methods;
});
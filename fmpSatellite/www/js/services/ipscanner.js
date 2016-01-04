starterServices.factory("FmpIpScanner", function($http, $rootScope){

  var collection = {
        "knownHosts": [],
        "scanHosts": [],
        "url": ""
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
    console.log("collection.knownHosts:", collection.knownHosts);
  }

  methods.generateHosts = function() {
    collection.scanHosts = [];
    methods.getKnownHosts();
    for (var i=0;i<collection.knownHosts.length;i++) {
      var host = collection.knownHosts[i];
      if (collection.scanHosts.indexOf(host) == -1) {
        collection.scanHosts.push(host);
        console.log("adding known host:", host);
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
    if (collection.found || collection.scanHosts.length == 0) {
      return;
    }
    var host = collection.scanHosts.shift();
    console.log("scan thread:", thread, host);
    $http({
        method: 'GET',
        url: host+"fmp_version",
        timeout: 100
    }).then(function(response) {
      if (response.data.fmp) {
        collection.found = true;
        collection.url = host;
        scanEnd = new Date();
        if (collection.knownHosts.indexOf(host) == -1) {
          collection.knownHosts.push(host);
          localStorage.knownHosts = JSON.stringify(collection.knownHosts);
        }
        console.log("found fmp server at host:", host);
        console.log("Running time:", scanEnd.valueOf() -
                                     collection.scanStart.valueOf());
        $rootScope.$broadcast("server-found");
      }
    }, function errorCallback(response) {
      methods.scan(thread, FmpConfig);
    });
  };

  methods.startScan = function(FmpConfig) {
    methods.generateHosts();
    collection.scanStart = new Date();
    for (var i=1;i<5;i++) {
      methods.scan(i, FmpConfig);
    }
  }

  return methods;
});
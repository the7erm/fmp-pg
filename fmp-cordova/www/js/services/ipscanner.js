fmpApp.factory("FmpIpScanner", function($http, $rootScope){
  console.log("Connection:", navigator.connection);
  var collection = {
        "knownHosts": [],
        "scanHosts": [],
        "url": "",
        "socketUrl": ""
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
    console.log("skipping ", Connection.WIFI);
    if (navigator.connection.type != "wifi") {
      console.log("skipping ", Connection.WIFI);
      return;
    }
    var host = collection.scanHosts.shift();
    // console.log("scan thread:", thread, host);
    try {

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
          console.log("found fmp server at host:", host);
          console.log("Running time:", scanEnd.valueOf() -
                                       collection.scanStart.valueOf());
          $rootScope.$broadcast("server-found");
        }
      }, function errorCallback(response) {
        try {
          methods.scan(thread, FmpConfig);
        } catch(e) {
          console.log("methods.scan:",e);
        }
      });
    } catch(e) {
      console.log("$http catch", e);
    }


  };

  methods.startScan = function(FmpConfig) {
    methods.generateHosts();
    collection.scanStart = new Date();
    for (var i=1;i<5;i++) {
      try {
        methods.scan(i, FmpConfig);
      } catch(e) {
        console.log("methods.scan:",e);
      }
    }
  }

  return methods;
});
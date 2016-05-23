

fmpApp.controller('RemoteController', function ($scope, $rootScope,
                                                FmpRemote) {
    var logger = new Logger("RemoteController", true),
        enabled = false;

    $scope.collection = FmpRemote.collection;
    $scope.connectToPeer = FmpRemote.connectToPeer;
    $scope.startDiscovery = FmpRemote.startDiscovery;
    $scope.requestDiscoverable = FmpRemote.requestDiscoverable;
    $scope.sendTest = FmpRemote.sendTest;
    $scope.pause = FmpRemote.pause;
    $scope.prev = FmpRemote.prev;
    $scope.next = FmpRemote.next;
    $scope.receiveObj = {};

    $rootScope.$on("client-connect", function(){
        $scope.$apply();
    });

    $rootScope.$on("bluetooth-receive", function(scope, receiveObj){
        $scope.receiveObj = receiveObj;
        $scope.$apply();
    });

});
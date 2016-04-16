fmpApp.controller('ListenersController', function ($scope, $rootScope, FmpListeners) {
    $scope.listenersCollection = FmpListeners.collection;
    $scope.ip_addresses = FmpListeners.collection.ip_addresses;
    $scope.save = FmpListeners.save;
    $scope.toggle = FmpListeners.toggle;
    $scope.setPrimary = FmpListeners.setPrimary;
});
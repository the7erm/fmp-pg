fmpApp.controller('ListenersController', function ($scope, $rootScope, FmpListeners) {
    $scope.listenersCollection = FmpListeners.collection;
    $scope.save = FmpListeners.save;
});
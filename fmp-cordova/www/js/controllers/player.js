fmpApp.controller('PlayerController', function ($scope, FmpSync, PlayerData,
                                                FmpPlayer, $rootScope) {
    $scope.PlayerData = PlayerData;
    $scope.FmpPlayerCollection = FmpPlayer.collection;
    $scope.syncCollections = FmpSync.syncCollections;
    $scope.player = window.player;
    $rootScope.$on("time-status", function(scope, file){
        $scope.$apply();
    });
});
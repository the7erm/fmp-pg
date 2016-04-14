fmpApp.controller('PlayerController', function ($scope, FmpSync, PlayerData,
                                                FmpPlayer, $rootScope) {
    $scope.PlayerData = PlayerData;
    $scope.FmpPlayerCollection = FmpPlayer.collection;
    $scope.syncCollections = FmpSync.newSync;
    $scope.syncFile = FmpSync.syncFile;
    $scope.FmpSyncCollection = FmpSync.collection;
    $scope.player = window.player;
    $rootScope.$on("time-status", function(scope, file){
        $scope.$apply();
    });

});
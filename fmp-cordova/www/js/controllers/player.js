fmpApp.controller('PlayerController', function ($scope, FmpSync, PlayerData,
                                                FmpPlayer) {
    $scope.PlayerData = PlayerData;
    $scope.FmpPlayerCollection = FmpPlayer.collection;
    $scope.syncCollections = FmpSync.syncCollections;
    $scope.player = window.player;

});
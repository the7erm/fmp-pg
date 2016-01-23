fmpApp.factory('PlayerData', function(){
    var collection = {
            play_pause: 'Pause',
            mode: "satellite",
            player: window.player
        },
        methods = {
            collection:collection
        }
    return methods;
});
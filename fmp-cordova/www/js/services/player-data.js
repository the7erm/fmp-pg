fmpApp.factory('PlayerData', function(){
    var logger = new Logger("PlayerData", false);
    var collection = {
            play_pause: 'Pause',
            mode: "satellite",
            player: window.player
        },
        methods = {
            collection:collection
        }
    logger.log("initialized");
    return methods;
});
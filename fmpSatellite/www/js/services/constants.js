starterServices.factory("FmpConstants", function(){
  return {
    "NONE": Media.MEDIA_NONE,
    "STARTING": Media.MEDIA_STARTING,
    "PLAYING": Media.MEDIA_RUNNING,
    "PAUSED": Media.MEDIA_PAUSED,
    "STOPPED": Media.MEDIA_STOPPED,
    "stars": [
        {stateOn: 'red-no', stateOff: 'grey-no'},
        {stateOn: 'yellow-star', stateOff: 'grey-star'},
        {stateOn: 'yellow-star', stateOff: 'grey-star'},
        {stateOn: 'yellow-star', stateOff: 'grey-star'},
        {stateOn: 'yellow-star', stateOff: 'grey-star'},
        {stateOn: 'yellow-star', stateOff: 'grey-star'},
        {stateOn: 'question-mark-on', stateOff: 'question-mark-off'}
      ]
  };
});

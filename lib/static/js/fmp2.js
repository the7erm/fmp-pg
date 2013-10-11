$(function(){

    /*************
     * Models
     ************/

    window.isModel = function(obj){
        return obj instanceof Backbone.Model;
    }

    window.isCollection = function(obj){
        return obj instanceof Backbone.Collection;
    }

    window.mylogger = function() {
        // this.debug = true;
        if (this.debug) {
            var first = _.first(arguments),
                args = [];
            if (_.isString(first)) {
                args.push(this["name"]+"."+first);
                args = args.concat(_.rest(arguments, 1));
            } else {
                args.push(this["name"]+".");
                _.each(arguments, function(a){
                    args.push(a);
                });
            }
            if (console.log) {
                console.log.apply(console, args);
            } else {
                var line = "";
                _.each(args, function(v, k){
                    if (k == 0) {
                        line += "<strong>"+v+"</strong>";
                        return;
                    }
                    try {
                        line += " "+JSON.stringify(v);
                    } catch(e) {
                        line += " ERROR: "+e+v;
                    }
                });
                $("#logger").append(line+"\n");
            }
        }
    };

    window.myInit = function() {
        this.log("initialize");
        this.log("arguments", arguments);
        this.log("this.options", this.options);
        this.log("this.attributes", this.attributes);
    }

    window.BaseView = Backbone.View.extend({
        debug: false,
        name: "BaseView",
        log: window.mylogger,
        initialize: function(){
            Backbone.View.prototype.initialize.apply(this, arguments);
            window.myInit.apply(this, arguments);
        }
    });

    window.BaseModel = Backbone.Model.extend({
        debug: false,
        name: "BaseModel",
        log: window.mylogger,
        initialize: function(){
            try {
                this.log("Start INIT of BACKBONE");
                Backbone.Model.prototype.initialize.apply(this, arguments);
                this.log("END INIT of BACKBONE");
            } catch (e) {
                alert("Error BaseModel:"+e);
            }
            window.myInit.apply(this, arguments);
        },
        initCollection: function(obj, model, collection) {
            if (isCollection(obj)) {
                this.log("obj is an instance of Backbone.Collection")
                if (obj instanceof collection) {
                    this.log("obj is an instance of collection")
                }
                return obj;
            }
            if (isModel(obj)) {
                this.log("obj is model");
                return new collection([obj]);
            }
            if (_.isArray(obj)) {
                this.log("obj is array",obj);
                var models = [];
                _.each(obj, function(modelData, k){
                    if (isModel(modelData)) {
                        models.push(modelData);
                    } else {
                        models.push(new model(modelData));
                    }
                }, this);
                this.log("models:", models);
                return new collection(models);
            }
            this.log("Creating new collection: FAILED:",obj)
            return new collection();
        }
    });

    window.BaseCollection = Backbone.Collection.extend({
        debug: false,
        name: "BaseCollection",
        log: window.mylogger,
        initialize: function(){
            Backbone.Collection.prototype.initialize.apply(this, arguments);
        }
    });

    window.TestModel = BaseModel.extend({
        debug: false,
        name: "TestModel",
        initialize: function(){
            var args = arguments || [];
            try {
                this.log("args:",args);
                BaseModel.prototype.initialize.apply(this, args);
            } catch(e) {
                return;
            }
            this.log("TestModel initialized");
        }
    });

    window.RatingModel = BaseModel.extend({
        debug: false,
        name: "RatingModel",
        idAttribute: "usid",
        initialize: function () {
            BaseModel.prototype.initialize.apply(this, arguments);
        },
        url: function() {
            return "/rate/"+this.get('usid')+"/"+this.get("fid")+"/"+this.get("uid")+"/"+this.get("rating");
        },
        getTrueScore: function () {
            var trueScore = this.get('true_score') || -1;
            return trueScore.toFixed(1);
        },
        getRating: function(defaultValue) {
            if (!defaultValue) {
                defaultValue = 6;
            }
            return this.get('rating') || defaultValue;
        },
    });

    window.RatingsCollection = BaseCollection.extend({
        model: RatingModel,
        name: "RatingsCollection",
        debug: false
    });

    window.AlbumModel = BaseModel.extend({
        idAttribute: "alid",
        name: "AlbumModel",
        debug: false
    });

    window.AlbumsCollection = BaseCollection.extend({
        model: AlbumModel,
        name: "AlbumsCollection",
        debug: false
    });


    window.GenreModel = BaseModel.extend({
        idAttribute: "gid",
        name: "GenreModel",
        debug: false
    });
    
    window.GenresCollection = BaseCollection.extend({
        debug: false,
        model: GenreModel,
        name: "GenresCollection"
    });

    window.ArtistModel = BaseModel.extend({
        debug: false,
        idAttribute: "aid",
        name: "ArtistModel"
    });

    window.ArtistsCollection = BaseCollection.extend({
        model: ArtistModel,
        name: "ArtistsCollection",
        debug: false
    });

    window.FileModel = BaseModel.extend({
        debug: false,
        name: "FileModel",
        idAttribute: "fid",
        artists: null,
        albums: null,
        genres: null,
        ratings: null,
        initialize: function(){
            this.log("START INIT of BaseModel")
            this.log("FileModel ACTUAL AGRUMENTS:", JSON.stringify(arguments, null, 4));
            
            this.log("FileModel ACTUAL AGRUMENTS:", arguments);
            BaseModel.prototype.initialize.apply(this, arguments);
            this.log("END INIT of BaseModel")
            var artists = this.get('artists');
            this.artists = this.initCollection(
                this.get('artists'),
                ArtistModel,
                ArtistsCollection
            );
            this.albums = this.initCollection(
                this.get('albums'),
                AlbumModel,
                AlbumsCollection
            );
            
            this.genres = this.initCollection(
                this.get('genres'),
                GenreModel,
                GenresCollection
            );
            this.log("**** RATING ****");
            var ratings = this.get('ratings');
            if (_.isObject(ratings) && !isModel(ratings)) {
                ratings = _.values(ratings);
            }
            this.ratings = this.initCollection(
                ratings,
                RatingModel,
                RatingsCollection
            );
            this.log("**** /RATING ****");
        },
        getArtistTitle: function() {
            var firstArtist = this.artists.at(0);
                title = this.get('title'),
                basename = this.get('basename'),
                artist_title = this.get('artist_title');
            if(firstArtist && title) {
                return firstArtist.get('artist')+" - "+title;
            }
            if (firstArtist) {
                return firstArtist.get('artist')+" - "+ basename;
            }
            if (artist_title) {
                return artist_title;
            }

            return basename;
        }
    });

    window.PlayingModel = FileModel.extend({
        url: "/playing/",
        name: "PlayingModel"
    });

    window.PlayerModel = FileModel.extend({
        url: "/player/status/",
        name: "PlayerModel"
    });

    window.VolumeModel = BaseModel.extend({
      url: function() {
          var val = this.get("value") || ""
          return "/volume/" + val;
      }
    });

    window.PosModel = BaseModel.extend({
        debug: false,
        name: "PosModel",
        url: function() {
            var val = this.get("value") || ""
            return "/seek/nano/" + val;
        },
        initialize: function() {
            setInterval(_.bind(this.inc, this), 1000)
            this.on("change", this.onChange, this);
        },
        inc: function() {
            var nanoSecond = 1000000000,
                val = parseInt(this.get("value") || 0) + nanoSecond,
                playingState = this.get("playingState") || "",
                left_int = parseInt(this.get("left_int") || 0) - nanoSecond,
                pos_str = formatTime(val),
                left_str = formatTime(left_int);

            if (playingState == "PLAYING" && val > 0 && val < this.get("max")) {
                this.set({
                    "value": val,
                    "pos_str": pos_str,
                    "left_int": left_int,
                    "left_str": left_str,
                    "pos_int": val
                });
            }
        },
        onChange: function() {
           this.log("onChange");
        }
    });

    window.ConductorModel = FileModel.extend({
        debug: false,
        name: "ConductorModel",
        idAttribute: "id",
        url:function() {
            var d = new Date();
            return "/status/?_"+d.valueOf();
        },
        playing: null,
        volume: null,
        pos: null,
        initialize: function(){
            this.attributes.extended.ratings = this.convertToArray(this.attributes.extended.ratings);
            this.attributes.playing.ratings = this.convertToArray(this.attributes.playing.ratings);
            this.log("<div style=\"color:red;\">**** START HERE");
            this.log("test array:", [])
            this.log("this.attributes.extended:",this.attributes.extended);
            var args = [this.attributes.extended];
            FileModel.prototype.initialize.apply(this, args);
            this.log("*** END HERE</div>");
            this.playing = new FileModel(this.attributes.extended);
            
            this.volume = new VolumeModel({value: this.attributes.volume});
            this.pos = new PosModel(this.attributes.extended.pos_data);

            this.onPlayingChange();
            this.onRatingsChange();
            this.onVolumeChange();
            
            // Triggers
            this.on("change:extended", this.onPlayingChange, this);
            this.on("change:volume", this.onVolumeChange, this);
            
            
            setInterval(_.bind(this.fetchPlaying, this), 5000);
            this.fetchPlaying();
        },

        onPlayingChange:function () {
            this.log("onPlayingChange:", this.changedAttributes());
            this.playing.set(this.attributes.extended);
            this.syncCollection('artists', ArtistModel);
            this.syncCollection('ratings', RatingModel);
            this.syncCollection('albums', AlbumModel);
            this.syncCollection('genres', GenreModel);
            this.log("onPlayerChange ", this.changedAttributes());
            this.pos.set(this.playing.get('pos_data'));
        },

        syncCollection: function(key, modelType) {
            if (_.isUndefined(this.attributes.playing)) {
                return;
            }

            var emptyModel = new modelType(),
                idAttribute = emptyModel.idAttribute;
            this.attributes.playing[key] = this.convertToArray(this.attributes.playing[key]);

            // Add models that are not in the collection
            _.each(this.attributes.playing[key], function(data){
                this.log("key:",key);
                var model = this[key].get(data[idAttribute]);
                if (!model) {
                    model = new modelType(data);
                    this.log("key:",key);
                    this[key].add(model);
                    return;
                }
                model.set(data);
            }, this);

            // Remove models that are not in the attributes.
            _.each(this[key].models, function(model){
                var id = model.get(idAttribute),
                    q = {};

                q[idAttribute] = id;
                var found = _.where(this.attributes.playing[key], q);
                this.log("q:",q, found);

                if (!found || found.length == 0) {
                    this.log("REMOVE:", q);
                    this[key].remove(model);
                }
            }, this);
        },

        convertToArray:function(obj){
            if (_.isArray(obj)) {
                return obj;
            }
            if (_.isObject(obj)) {
                obj = _.values(obj);
                return obj;
            }
            obj = [obj];
            return obj;
        },

        onVolumeChange:function () {
            this.log("onVolumeChange:", this.changedAttributes());
            this.volume.set({"value": this.attributes.volume});
        },

        onRatingsChange: function(model, options) {
            this.log("onRatingsChange:model", model);
            this.log("onRatingsChange:options", options);

        },

        fetchPlaying: function(){
            this.log("fetchPlaying:", new Date());
            this.fetch({reset: true});
        }
    });

    /********
     * Views
     ********/

    window.RatingView = BaseView.extend({
        debug: false,
        name: "RatingView",
        model: null,
        template: _.template($("#tpl-rating").html()),
        table: null,
        initialize:function(){
            BaseView.prototype.initialize.apply(this, arguments);
            this.model = this.options.model || new RatingModel();
            this.model.on("change", this.onChange, this);
            if (this.options.table) {
                this.table = this.options.table;
            }
        },
        onChange:function(){
            this.log("onChange changedAttributes:", this.model.changedAttributes());
            var changedAttributes = this.model.changedAttributes();
            if (!_.isUndefined(changedAttributes['true_score'])) {
                var true_score = this.model.getTrueScore();
                this.$el.find(".true_score").text(true_score);
            }
            if (!_.isUndefined(changedAttributes['rating'])) {
                var rating = this.model.get('rating');
                this.$tdStarRating.raty('score', this.model.getRating());
                if (rating == 6) {
                    this.$el.find(".rate-me").show();
                } else {
                    this.$el.find(".rate-me").hide();
                }
            }
        },
        render: function(){
            this.log("render");
            var table = $("<table />");
            table.append(this.template(this.model.toJSON()));
            this.$el = table.find('tr');
            delete table;
            this.table.append(this.$el);
            this.$tdStarRating = this.$el.find('.star-rating');
            this.renderStars()
            return this;
        },
        renderStars: function(){
              var view = this;
              this.$tdStarRating.raty({
                    path: "/static/images/raty",
                    score: function () {
                        return $(this).data("rating")
                    },
                    click: _.bind(this.onRate, this),
                    cancel: true,
                    cancelOff : 'cancel-off-big.png',
                    cancelOn  : 'cancel-on-big.png',
                    starHalf  : 'star-half-big.png',
                    starOff   : 'star-off-big.png',
                    starOn    : 'star-on-big.png',
                    size: 24,
                    hints: ['Not the greatest', 
                            'Meh',
                            'Good', 
                            'Really good', 
                            'Love it!'],
                    cancelHint: 'Please don\' play this ever again for me',
                });
          },
          onRate: function(score, evt){
              if (score == null) {
                  score = 0;
              }
              this.model.set("rating", score);
              this.model.save();
          },
          rate: function (ratingData) {
              if (_.isUndefined(ratingData) || $.isEmptyObject(ratingData)) {
                  return;
              }

              _.extend(ratingData, {
                  "cmd": "rate",
                  "status": 1,
                  "value": ratingData['rating']
              });
              $.ajax({
                  "url":"/",
                  "data": ratingData,
                  'dataType':'json'
              }).done(_.bind(this.processStatus, this));
          },
    });

    window.RatingsTableView = BaseView.extend({
        debug: true,
        name: "RatingsTableView",
        collection: null,
        template: _.template($("#tpl-ratings-table").html()),
        ratingViews: {},

        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            this.collection = this.options.collection || new RatingsCollection();
            
            this.collection.on("add", this.onAdd, this);
            this.collection.on("change", this.onChange, this);
            this.collection.on("remove", this.onRemove, this);
            
            if (this.options.$el) {
                this.$el = this.options.$el;
            }
        },
        onChange: function(model, arg2){
            if (!model) {
                return; 
            }
            this.log("?????????????????????????????");
            this.log("changedAttributes:", model.changedAttributes());
            var usid = model.get('usid');
            if (!this.ratingViews[usid]) {
                this.log("can't render rating:",usid);
                this.onAdd(model);
            }
            this.log("/?????????????????????????????");
            this.hideOrShow();
        },
        onAdd: function(model){
            this.log("++++++++++++++++++++++");
            this.log("onAdd:",model);
            var usid = model.get('usid');
            this.ratingViews[usid] = new RatingView({
                model: model,
                table: this.$el.find('.ratings-table')
            }).render();
            this.log("/++++++++++++++++++++++");
            this.hideOrShow();
        },
        onRemove: function(model){
            this.log("---------------------------");
            this.log("onRemove:",model);
            var usid = model.get('usid');
            this.$el.find("#usid-"+usid).remove();
            delete this.ratingViews[usid];
            this.log("/---------------------------");
            this.hideOrShow();
        },
        hideOrShow: function(){
            if (this.collection.length >= 1) {
                this.$el.show();
            } else {
                this.$el.hide();
            }
        },
        render: function(){
            this.$el.html(this.template({collection: this.collection}));
            this.collection.each(function(model){
                this.onAdd(model);
            }, this);
            this.hideOrShow();
            return this;
        }
    });

    window.FileView = BaseView.extend({
        debug: false,
        name: "FileView",
        albums: null,
        artists: null,
        genres: null,
        ratings: null,
        file: null,
        displayAdd: true,
        $fileInfo: null,
        $addDoPreloadDiv: null,
        template: _.template($("#tpl-row").html()),
        fileInfoTemplate: _.template($("#tpl-file-info").html()),
        ratingsTableView: null,
        initialize: function(){
            BaseView.prototype.initialize.apply(this, arguments);
            this.albums = this.options.albums || new AlbumsCollection();
            this.artists = this.options.artists || new ArtistsCollection();
            this.genres = this.options.genres || new GenresCollection();
            this.ratings = this.options.ratings || new RatingsCollection();
            this.file = this.options.file || new FileModel();
            this.ratingsTableView = new RatingsTableView({collection: this.ratings});
            this.artists.on("change", this.render, this);
            this.albums.on("change", this.render, this);
            this.ratings.on("change", this.render, this);
            this.genres.on("change", this.render, this);
        },
        render:function(){
            this.$el.html(this.template(this.file));
        }
    });

    window.SliderView = BaseView.extend({
        $slider: null,
        name: "SliderView",
        lock: false,
        step: 1,
        scrollLock: false,
        stack: null,
        saveLock: false,
        slideLock: false,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            this.model = this.options.model || new BaseModel;
            this.model.on("change", this.onModelChange, this);
        },
        save: function() {
            this.model.save();
            if (this.saveLock) {
                return;
            }
            this.saveLock = true;
            var val = this.getElVal(),
                url = _.isFunction(this.model.url) ? this.model.url() : this.model.url
            $.ajax(url, {"cache": false})
             .always(_.bind(function(){
                this.saveLock = false;
             }, this));
        },
        onMouseWheel: function(evt, delta){
            evt.preventDefault();
            if (delta == 1 || delta == -1) {
                var newVal = this.getElVal();
                if (delta == 1) {
                  // add to the val.
                  newVal = newVal + this.step;
                }
                if (delta == -1) {
                  // remove from the val
                  newVal = newVal - this.step;
                }
                this.lock = true;
                this.$el.val(newVal).slider("refresh");
                this.model.set({"value": newVal}, {silent:true});
                this.save();
                this.lock = false;
            }
        },
        getElVal: function(){
            return parseInt(this.$el.val());
        },
        changeValue: function(val, silent) {
            if (this.lock || this.slideLock) {
                return;
            }
            this.lock = true;
            var options = {
              "silent": _.isUndefined(silent) ?
                        false :
                        silent
            };
            this.model.set("value", val, options);
            this.$el.val(val).slider("refresh");
            this.lock = false;
            this.save();
        },
        onModelChange: function() {
          if (this.lock || this.slideLock) {
              return;
          }
          this.lock = true;
          var newVal = this.model.get("value"),
              mx = this.model.get("mx");
          this.$el.prop("max", this.model.get("max"));
          this.$el.val(newVal).slider("refresh");
          this.lock = false;
        },
        onSliderChangeValue: function(event, ui) {
          if (this.lock || this.slideLock) {
              return;
          }
          this.changeValue(this.getElVal(), true);
        },
        onSlideStart: function() {
          this.slideLock = true;
        },
        onSlideStop: function() {
          this.slideLock = false;
          this.changeValue(this.getElVal(), true);
        },
        render: function() {
          this.slider = this.$el.parent(".ui-slider");
          this.slider.bind("mousewheel", _.bind(this.onMouseWheel, this));

          this.step = parseInt(this.$el.prop("step"));
          if (!this.step) {
              this.step = 1;
          }
          this.onModelChange();
          this.$el.bind("change", _.bind(this.onSliderChangeValue, this));
          this.$el.bind("slidestart", _.bind(this.onSlideStart, this));
          this.$el.bind("slidestop", _.bind(this.onSlideStop, this));
          return this;
        }
    });

    window.formatTime = function(nanosecnods) {
        var seconds = Math.floor(parseInt(nanosecnods) / 1000000000),
            hrs = Math.floor(seconds / 3600);
        if (hrs) {
            seconds = seconds - (hrs * 3600);
        }
        var minutes = Math.floor(seconds / 60);
        if (minutes) {
            seconds = seconds - (minutes * 60);
        }
        var ret = "";
        if (hrs) {
            ret = hrs+":";
        }

        minutes = Math.floor(minutes);
        if (minutes<=0) {
            minutes = 0;
        }
        
        if (minutes < 10 && ret) {
            minutes = "0"+minutes;
        }
        ret += minutes+":";

        seconds = Math.floor(seconds);
        if (seconds<=0) {
            seconds = 0;
        }
        
        if (seconds < 10) {
            seconds = "0"+seconds;
        }
        ret += ""+seconds;
        return ret;
    };

    window.TimeSlider = SliderView.extend({
        "name": "TimeSlider",
        debug: false,
        $timeInput: null,
        
        initialize: function(){
            SliderView.prototype.initialize.apply(this, arguments);
            this.model.on("change:value", this.onValueChange, this);
        },
        onValueChange: function() {
            this.$timeInput.val(formatTime(this.model.get("value")));
        },
        render: function(){
            SliderView.prototype.render.apply(this, arguments);
            this.$el.hide();
            this.$timeInput = $("<input/>");
            this.$timeInput.prop("class", this.$el.prop("class"));
            this.$el.parent(".ui-slider").prepend(this.$timeInput);
            this.onValueChange();
            return this;
        } 
    });

    window.PlayingFileView = FileView.extend({
        debug: true,
        name: "PlayingFileView",
        conductor: null,
        displayAdd: false,
        template: _.template($("#tpl-mini-playing").html()),
        fileInfoTemplate: _.template($("#tpl-mini-file-info").html()),
        initialize: function(){
            try {
                FileView.prototype.initialize.apply(this, this.options.conductor.extended);
            } catch(e){
                alert("PlayingFileView:"+e);
                return;
            }
            this.conductor = this.options.conductor || new ConductorModel();
            this.connectConductor();
        },
        connectConductor: function() {
            this.conductor.playing.on("change:basename", this.updateFileInfo, this);
            this.conductor.playing.on("change:imgHash", this.onImgChange, this);
            this.conductor.on("change:imgHash", this.onImgChange, this);
            this.conductor.on("change:basename", this.updateFileInfo, this);
        },
        updateFileInfo:function(){
            this.$fileInfo.html(this.fileInfoTemplate({model:this.conductor.playing}));
            this.onImgChange();
        },
        onImgChange: function() {
            this.log("IMAGE HAS CHANGED:",this.conductor.playing.imgHash)
            if (this.conductor.playing.get('imgHash')) {
                this.$img.show();
                var now = new Date();
                this.$img.prop("src", "/playing/image.png?_="+now);
            } else {
                this.$img.hide();
            }
        },
        render: function(){
            this.log("render()");
            this.$el.html(this.template({model:this.conductor}));
            this.$fileInfo = this.$el.find('.file-info');
            this.$img = this.$el.find(".album-art");
            this.updateFileInfo();

            this.$addDoPreloadDiv = this.$el.find(".add-to-preload-div");
            this.$ratingsTable = this.$el.find('.ratings-table');
            if (!this.displayAdd) {
                this.$addDoPreloadDiv.hide();
            }
            this.ratingsTableView = new RatingsTableView({
                "$el": this.$ratingsTable,
                collection: this.conductor.ratings
            }).render();
            this.$img = this.$el.find(".album-art");
            this.onImgChange();
            return this;
        },
    });

    window.CommandModel = BaseModel.extend({
        debug: false,
        name: "CommandModel",
        "url": function(){
            return "/player/"+this.get('cmd')
        }
    });

    window.ControlView = BaseView.extend({
        debug: false,
        name: "ControlView",
        template: _.template($("#tpl-media-control").html()),
        playingState: null,
        events: {
            "click .action-link": "onClickAction"
        },
        initialize: function(){
            BaseView.prototype.initialize.apply(this, arguments);
            this.conductor = this.options.conductor;
            this.commandModel = new CommandModel();
            this.listenTo(this.conductor.playing, 'change:playingState', this.updateButton, this);
            this.listenTo(this.commandModel, 'change', this.commandUpdate, this);
        },
        onClickAction: function(evt) {
            evt.preventDefault();
            var $target = $(evt.target);
            this.commandModel.set({"cmd": $target.data('cmd')});
            this.commandModel.fetch();
            return false;
        },
        render: function(){
            BaseView.prototype.render.apply(this, arguments);
            this.$el.html(this.template(this.conductor.playing.toJSON()));
            this.$playPauseImg = this.$el.find("#play-pause-img");
            return this;
        },
        commandUpdate: function() {
            this.conductor.set(this.commandModel.attributes);
            this.updateButton();
        },
        updateButton: function() {
            var playingState = this.conductor.playing.get('playingState')
            if (_.isUndefined(playingState) || 
                playingState == this.playingState) {
                return;
            }
            this.playingState = playingState;
            if (this.playingState == 'PLAYING') {
                this.$playPauseImg.prop('src', '/static/images/media-playback-pause.png');
            } else {
                this.$playPauseImg.prop('src', '/static/images/media-playback-start.png');
            }
        }
    });

    window.TimeStatusView = BaseView.extend({
        debug: false,
        name: "TimeStatusView",
        conductor: null,
        $leftStr: null,
        $posStr: null,
        $durStr: null,
        initialize: function() {
            BaseView.prototype.initialize(this, arguments);
            if (this.options.conductor) {
                this.conductor = this.options.conductor;
                this.conductor.pos.on("change:left_str", this.onChangeLeft, this);
                this.conductor.pos.on("change:pos_str", this.onChangePos, this);
                this.conductor.pos.on("change:dur_str", this.onChangeDur, this);
            }
        },
        onChangeLeft: function(){
            this.$leftStr.text(this.conductor.pos.get("left_str"));
        },
        onChangePos: function() {
            this.$posStr.text(this.conductor.pos.get("pos_str"));
        },
        onChangeDur: function(){
            this.$durStr.text(this.conductor.pos.get("dur_str"));
        },
        render: function(){
            this.$leftStr = this.$el.find(".left_str");
            this.$posStr = this.$el.find(".pos_str");
            this.$durStr = this.$el.find(".dur_str");
            this.onChangeLeft();
            this.onChangePos();
            this.onChangeDur();
            return this;
        }
    });

});

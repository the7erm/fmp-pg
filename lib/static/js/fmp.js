// An example Backbone application contributed by
// [JÃ©rÃ´me Gravel-Niquet](http://jgn.me/). This demo uses a simple
// [LocalStorage adapter](backbone-localstorage.html)
// to persist Backbone models within your browser.

// Load the application once the DOM is ready, using `jQuery.ready`:
$(function(){
  window.RatingModel = Backbone.Model.extend({
      idAttribute: "usid",
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
      }
  });

  window.AlbumModel = Backbone.Model.extend({
      idAttribute: "alid"
  });

  window.GenreModel = Backbone.Model.extend({
      idAttribute: "gid"
  });

  window.ArtistModel = Backbone.Model.extend({
      idAttribute: "aid"
  });

  window.FileModel = Backbone.Model.extend({
      idAttribute: "fid",
      defaults: function () {
        return {
            albums: [],
            artists: [],
            basename: "",
            dirname: "",
            fid: "",
            genres: [],
            ratings: [],
            title: "",
            cued: false
        };
      },
      constructor: function() {
        Backbone.Model.apply(this, arguments);
        if (arguments.ratings) {
            _.each(ratings, function(uid, rinfo){
                var rating = new RatingModel(rinfo);
                this.ratings.append(rating);
            }, this);
        }
      }
  });

  window.PlayingModel = window.FileModel.extend({
      url: "/playing/"
  });

  window.PlayerModel = Backbone.Model.extend({
      url: "/player/status/"
  });

  window.VolumeModel = Backbone.Model.extend({
      url: function() {
          var val = this.get("value") || ""
          return "/volume/" + val;
      }
  });

  window.PosModel = Backbone.Model.extend({
      url: function() {
          var val = this.get("value") || ""
          return "/seek/nano/" + val;
      },
      initialize: function() {
          setInterval(_.bind(this.inc, this), 1000)
      },
      inc: function() {
          var val = parseInt(this.get("value") || 0) + 1000000000,
              playingState = this.get("playingState") || "";
          if (playingState == "PLAYING" && val > 0 && val < this.get("max")) {
              this.set({"value": val});
          }
      }
  });

  window.MediaPlayerModel = window.FileModel.extend({
      url:function() {
          var d = new Date();
          return "/status/?_"+d.valueOf();
      },
      playingModel: null,
      playerModel: null,
      volumeModel: null,
      lock:false,
      initialize: function() {
          var obj = this.toJSON()
          this.playerModel = new Backbone.Model(obj.player);
          this.playingModel = new Backbone.Model(obj.playing);
          this.volumeModel = new VolumeModel({"value": obj.volume});
          this.posModel = new PosModel(obj.player.pos_data);
          this.on("change:playing", this.updatePlayingModel, this);
          this.on("change:player", this.updatePlayerModel, this);
          this.on("change:volume", this.updateVolumeModel, this);
          this.playerModel.on("change", this.syncPlayerModel, this);
          this.playingModel.on("change", this.syncPlayingModel, this);
          this.volumeModel.on("change", this.syncVolumeModel, this);
          this.posModel.on("change", this.syncPosModel, this);
          setInterval(_.bind(this.fetchPlaying, this), 5000);
      },
      doLock:function(caller) {
          if (this.lock) {
              // console.log("locked by:",this.lock, "called from", caller);
              return true;
          } else {
             
          }
          this.lock = caller;
          return false;
      },
      unLock:function(){
          this.lock = false;
      },
      syncPlayerModel: function() {
          if (this.doLock("syncPlayerModel")) {
              return;
          }
          this.set({"player": this.playerModel.toJSON()});
          this.unLock();
      },
      syncPlayingModel: function() {
          if (this.doLock("syncPlayingModel")) {
              return;
          }
          this.set({"playing": this.playingModel.toJSON()});
          this.unLock();
      },
      syncVolumeModel: function() {
          if (this.doLock("syncVolumeModel")) {
              return;
          }
          this.set({"volume": this.volumeModel.get('value')});
          this.unLock();
      },
      syncPosModel: function() {
          if (this.doLock("syncPosModel")) {
              return;
          }
          var player = this.get('player');
          player.pos_data = this.posModel.toJSON();
          this.set({"player": player});
          this.unLock();
      },
      updatePlayerModel: function() {
          if (this.doLock("updatePlayerModel")) {
              return;
          }
          var player = this.get('player');
          this.playerModel.set(player);
          this.posModel.set(player.pos_data);
          this.unLock();
      },
      updatePlayingModel: function() {
          if (this.doLock("updatePlayingModel")) {
              return;
          }
          this.playingModel.set(this.get('playing'));
          this.unLock();
      },
      updateVolumeModel: function() {
          if (this.doLock("updateVolumeModel")) {
              return;
          }
          var player = this.get('player');
          this.volumeModel.set({"value": this.get('volume')});
          this.unLock();
      },
      fetchPlaying: function() {
          console.log("fetchPlaying:", new Date());
          this.fetch();
          return true;
      }
  });

  window.SearchResultsCollection = Backbone.Collection.extend({
      model: FileModel
  });

  window.CommandModel = Backbone.Model.extend({
      "url": function(){
          return "/player/"+this.get('cmd')
      }
  });

  window.SearchResults = new SearchResultsCollection;

  window.RatingRowView = Backbone.View.extend({
      template: _.template($("#tpl-rating").html()),
      rinfo: null,
      ratingModel: null,
      $trueScoreTd: null,
      $tdStarRating: null,
      initialize: function(){
          if (this.options.parent_el) {
              this.parent_el = this.options.parent_el;
          }
          this.rinfo = this.options.rinfo;
          this.ratingModel = new window.RatingModel(this.rinfo);
          this.ratingModel.on("change:true_score", this.updateTrueScore, this);
          this.ratingModel.on("change:rating", this.updateRating, this);
      },
      render: function() {
        console.log("RatingRowView.render()");
        var table = $("<table />");
        table.append(this.template(this.rinfo));
        this.$el = table.find('tr');
        this.parent_el.append(this.$el);
        this.$trueScoreTd = this.$el.find(".true_score_td");
        this.$tdStarRating = this.$("td.star-rating");
        this.renderStars();
        delete table;
      },
      onRate: function(score, evt){
          if (score == null) {
              score = 0;
          }
          this.ratingModel.set("rating", score);
          this.ratingModel.save();
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
      processStatus: function(data){
          var uid = this.rinfo.uid,
              trueScore = data["ratings"][uid]["true_score"];
          this.$trueScoreTd.text(this.ratingModel.getTrueScore());
      },
      updateTrueScore: function() {
          this.$trueScoreTd.text(this.ratingModel.getTrueScore());
      },
      updateRating: function() {
          this.$tdStarRating.raty('score', this.ratingModel.getRating());
      }
  });

  window.RatingTableView = Backbone.View.extend({
      tagName: "div",
      template: _.template($("#tpl-ratings-table").html()),
      ratings: [],
      ratingRowsViews: [],
      initialize: function() {
        if (this.options.$el) {
            this.$el = this.options.$el;
        }
        if (this.options.ratings) {
            this.ratings = this.options.ratings;
        }
      },
      render: function() {
        var table = this.template(),
            tst = this.$el.html(table),
            $table = this.$el.find(".ratings-table");

        _.each(this.ratings, function(rinfo){
            var ratingRowView = new window.RatingRowView({
                "rinfo": rinfo,
                "parent_el": $table
            });
            ratingRowView.render();
            this.ratingRowsViews.push(ratingRowView);
        }, this);
        return this;
      },
      update: function(newVals) {
          _.each(newVals, function(nv){
            _.each(this.ratingRowsViews, function (view) {
                var rmUid = view.ratingModel.get('uid');
                if (rmUid == nv['uid']) {
                    view.ratingModel.set(nv);
                }
            }, this);
          }, this);
      }
  });

  window.FileView = Backbone.View.extend({
    tagName: "div",

    template: _.template($('#tpl-row').html()),
    itemTemplate: _.template($("#tpl-item").html()),
    fileInfoTemplate: _.template($("#tpl-file-info").html()),

    initialize: function() {
        if (this.options.model) {
            this.model = this.options.model;
            this.listenTo(this.model, 'change', this.update, this);
        }
    },

    update: function() {
        this.updateRatings();
        this.updateFileInfo();
    },

    updateFileInfo: function(args, force) {
        if (!args) {
            args = _.extend(this.model.toJSON(), {
              itemTemplate: this.itemTemplate
            });
        }
        this.$fileInfoEl.html(this.fileInfoTemplate(args));
        return;
    },

    updateRatings: function() {
        this.ratingTableView.update(this.model.get('ratings'));
    },

    render: function() {
      console.log("FileView.render");
      if (!this.model) {
        this.model = new FileModel;
        this.listenTo(this.model, 'change', this.render);
      }

      var args = _.extend(this.model.toJSON(), {
              itemTemplate: this.itemTemplate,
              _: _
          });
      
      this.$el.html(this.template(args));
      this.$fileInfoEl = this.$el.find('.file-info');
      this.updateFileInfo(args, true);
      this.ratingTableView = new RatingTableView({
         "ratings": args['ratings'],
         "$el": this.$el.find(".ratings-table")
      });
      if (!_.isUndefined(this.options["showAddToPreload"]) && !this.options.showAddToPreload) {
          this.$(".add-to-preload-div").hide();
      }
      this.ratingTableView.render();
      return this;
    },

  });

  window.MediaControlView = Backbone.View.extend({
      template: _.template($("#tpl-media-control").html()),
      playingState: null,
      events: {
          "click .action-link": "onClickAction"
      },
      initialize: function(){
          this.commandModel = new window.CommandModel;
          this.playerModel = this.options.playerModel;
          this.listenTo(this.playerModel, 'change:playingState', this.updateButton, this);
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
          this.$el.html(this.template(this.playerModel.toJSON()));
          this.$playPauseImg = this.$el.find("#play-pause-img");
          return this;
      },
      commandUpdate: function() {
          this.playerModel.set(this.commandModel.toJSON().player);
      },
      updateButton: function() {
          var playingState = this.playerModel.get('playingState')
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

  window.SliderView = Backbone.View.extend({
      $slider: null,
      lock: false,
      step: 1,
      scrollLock: false,
      stack: null,
      saveLock: false,
      slideLock: false,
      initialize: function() {
          this.model = this.options.model || new Backbone.Model;
          this.model.on("change", this.onModelChange, this);
          this.$el = $(this.options.el);
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

});

window.RatingButtonView = Backbone.View.extend({
    rating: 6,
    uid: 0,
    fid: 0,
    template: _.template($("#tpl-rating-button").html()),
    initialize: function(options){
        this.fid = options.fid;
        this.rating = options.rating;
        this.uid = options.uid;
        this.user = options.user;
        this.menu_id = "rating-popup-menu-"+this.fid+"-"+this.uid;
    },
    render: function(){
        this.$el.html(this.template({
            "rating": this.rating,
            "uid": this.uid,
            "fid": this.fid,
            "menu_id": this.menu_id,
            "user": this.user,
        })).trigger( "create" );
        this.$popupMenu = $("#"+this.menu_id);
        this.$popupMenu.find('.rating-popup-link')
                       .bind("click", _.bind(this.onRate, this));
        return this;
    },
    onRate: function(evt) {
        evt.preventDefault();
        this.$popupMenu.popup("close");
        var _this = this;
        this.rating = $(evt.currentTarget).data("rating");
        this.syncRatingImg();
        $.ajax({
          url: evt.currentTarget.href,
          dataType: 'json'
        }).done(function(data, textStatus, jqXHR) {
            var conductor_fid = conductor.get("playing.fid") || 0;
            if (conductor_fid == _this.fid) {
                conductor.set(data);
            }
        });
    },
    syncRatingImg: function() {
        var popup_button = this.$(".open-popup");
        for (var i=0;i<7;i++) {
            popup_button.removeClass("rating-"+i)
        }
        popup_button.addClass("rating-"+this.rating);
    }
});

window.HistoryModel = Backbone.Model.extend({
    idAttribute: "uhid",
});

window.HistoryCollection = Backbone.Collection.extend({
    model: HistoryModel
})

window.HistoryViewLiView = Backbone.View.extend({
    initialize: function(options){
        this.model = options.model;
        this.model.on("change", this.onModelChange);
        this.parentEl = options.parentEl;
    },
    onModelChange: function(){
        // console.log("MODEL CHANGED:", self.model.toJSON());
    },
    render: function(){
        return this;
    }
});

window.HistoryView = Backbone.View.extend({
    template: _.template($("#tpl-history").html()),
    template_li_divider: _.template($("#tpl-history-li-divider").html()),
    template_li: _.template($("#tpl-history-li").html()),
    initialize: function(options) {
        this.collection = options.collection;
        this.model = options.model;
        this.el = options.el;
        this.collection.on("add", this.onAddCollection, this);
        this.conductor = options.conductor;
        this.conductor.on("change:playing.fid",_.bind(this.clearHistory, this));
        this.conductor.on("change:playing.history", _.bind(this.updateHistory, this));
    },
    clearHistory: function() {
        this.$ul.empty();
        this.collection.reset();
    },
    updateHistory: function(){
        var playing_history = this.conductor.get('playing.history');
        _.each(playing_history, function(v, k) {
            var present = this.collection.get(v.uhid);
            v.time_played = new Date(v.time_played);
            v.date = new Date(v.date);
            if (!present) {
                this.collection.add(v);
            } else {
                present.set(v);
            }
        }, this);
    },
    onAddCollection: function(model, collection, evt){
        console.log("onAddCollection evt:",evt)
        if (evt.add) {
            var attrs = model.toJSON();
            attrs['user'] = model.get('user.uname');
            this.$ul.append(this.template_li_divider(attrs));
            this.$ul.append(this.template_li(attrs));
            this.$ul.listview("refresh");
            model.el = this.$ul.find("li:last");
            model.on("change", this.onModelChange, this);
        }
    },
    onModelChange:function(model){
        _.each(model.changed, function(v, k){
            if (k == 'percent_played' || k == 'true_score') {
                v = v.toFixed(2);
            }
            model.el.find(".history-"+k).text(v);
        });
    },
    render: function() {
        this.$el.html(this.template({}));
        this.$ul = this.$el.find("ul");
        this.$ul.trigger("create");
        this.updateHistory();
        // this.$el.listview("refresh");
        return this;
    }
});

window.formatTime = function(seconds) {
    var seconds = Math.floor(parseFloat(seconds)),
        minutes = Math.floor(seconds / 60),
        seconds = seconds % 60;
    if (seconds < 10) {
        seconds = "0"+seconds;
    }
    return minutes+":"+seconds;
}
window.updateTime = function(seconds) {
    $('.playing-time-status').text(window.formatTime(seconds));
}

window.WebPlayerView = Backbone.View.extend({
    supportedMimeTypes: {},
    playlist: [],
    playlistIndex: 0,
    initialize: function(options){
        this.vid = document.createElement('audio');
        this.vid.id = "video-player";
        this.vid.style.width = "100%";
        this.vid.seekable = true;
        this.bindVideoEvents();
        this.checkSupportedTypes();
        this.el = options.el;
        this.vid.controls = true;
        this.fid = options.fid;
        this.resetTimes();
        this.conductor = options.conductor;
        this.$playingStateImg = $('.playing-state-img');
        this.vid.addEventListener("play", _.bind(this.onPlay, this));
        this.vid.addEventListener("pause", _.bind(this.onPause, this));
        this.conductor.on("change:playing.fid", _.bind(this.setSrcToConductor, this));
        this.conductor.on("change:mode", _.bind(this.onChangeMode, this));
    },
    onChangeMode: function(){
        if (this.conductor.isRemoteMode()) {
            this.$el.hide();
            this.vid.pause();
        } else {
            this.$el.show();
            this.vid.play();
        }
    },
    setSrcToConductor: function() {
        var fid = this.conductor.get("playing.fid");
        console.log("setSrcToConductor:", fid);
        this.playlist.push(fid);
        this.setSrc(fid, false);
    },
    onPlay: function() {
        if (this.conductor.isWebMode()) {
            this.$playingStateImg.attr('src', '/static/img/media-playback-pause.png');
        }
    },
    onPause: function(){
        if (this.conductor.isWebMode()) {
            this.$playingStateImg.attr('src', '/static/img/media-playback-start.png');
        }
    },
    resetTimes: function() {
        this.lastPercentPlayed = -100;
        this.lastCurrentTime = -100;
        this.lastUpdateTime = -100;
    },
    bindVideoEvents: function(){
        var $vid = $(this.vid);
        
        var events = [
            'abort',
            'canplay',
            'canplaythrough',
            'durationchange',
            'emptied',
            'ended',
            'error',
            'loadeddata',
            'loadedmetadata',
            'loadstart',
            'pause',
            'play',
            'playing',
             // 'progress',
            'ratechange',
            'seeked',
            'seeking',
            'stalled',
            // 'suspend',
            // 'timeupdate',
            'volumechange',
            'waiting'
        ];
        // _.bind(function, object, [*arguments])
        _.each(events, function(evt){
            this.vid.addEventListener(evt, _.bind(this.logEvent, this));
        }, this);
        this.vid.addEventListener('timeupdate', _.bind(this.onTimeStatus, this));
        this.vid.addEventListener('ended', _.bind(this.markAsCompleted, this));
        // this.vid.addEventListener('progress', _.bind(this.markeAsCompleted, this));
    },
    logEvent: function(evt, arg2){
        if (evt.type == "timeupdate") {

            return;
        }
        console.log("event:", evt.type, evt, arg2);
        if (evt.type == "progress") {
            this.markAsPlayed();
        }
    },
    onTimeStatus: function() {
        if (!this.vid.duration) {
            return;
        }
        var currentTime = parseFloat(this.vid.currentTime);
        /*
        conductor.on("change:pos_data.pos_str", on_change_time);
        conductor.on("change:state", on_state_change);
        */
        if (this.lastUpdateTime <= (currentTime + 1) ||
            this.lastUpdateTime >= (currentTime + 1)) {
            window.updateTime(currentTime);
            this.lastUpdateTime = currentTime;
        }
        this.markAsPlayed();
    },
    markAsPlayed: function() {
        
        var currentTime = parseFloat(this.vid.currentTime);

        if (currentTime > this.lastCurrentTime - 5 &&
            currentTime < this.lastCurrentTime + 5) {
            return;
        }
        this.lastCurrentTime = currentTime;
        var percent_played = this.vid.currentTime / this.vid.duration * 100;
        this.sendPercentPlayed(percent_played);
    },
    markAsCompleted: function() {
        console.log("markAsCompleted");
        this.sendPercentPlayed(100.0);
        this.resetTimes();
        this.incSkipScore();
        this.incIndex();
    },
    getUids: function(){
        return this.conductor.get("uids") || [];
    },
    sendPercentPlayed: function(percent_played) {
        if (this.conductor.isRemoteMode()) {
            return;
        }
        // /mark-as-played/<fid>/<percent_played>/<uids>
        var uids = this.getUids();
        if (!uids) {
            return;
        }
        console.log("sendPercentPlayed uids:", uids);
        $.ajax({
          url: "/mark-as-played/"+this.fid+"/"+percent_played+"/"+uids.join(","),
          dataType: 'json',
          cache: false
        });
    },
    checkSupportedTypes:function(){
        var mimeTypes = {
            'ogg': 'video/ogg',
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'mp3': 'audio/mpeg',
            'ogg': 'audio/ogg',
            'mp4': 'audio/mp4'
        };
        this.supportedMimeTypes = {};
        _.each(mimeTypes, function(mimeType, ext){
            if (this.vid.canPlayType(mimeType)) {
                this.supportedMimeTypes[ext] = mimeType;
            }
        }, this);
    },
    setSrc: function(fid, resume) {
        this.fid = fid;
        this.vid.src = this.getSrc();
        if (this.conductor.isWebMode()) {
            this.vid.play();
        }
        this.getFileInfo(resume);
        this.resetTimes();
    },
    doResume:function(data){
        if (this.conductor.isRemoteMode()) {
            return;
        }
        console.log("DATA:", data)
        console.log(data.listeners_ratings);
        console.log("this.vid.duration:",this.vid.duration);
        var resumeTime = this.vid.duration * parseFloat(data.listeners_ratings[0].percent_played) * 0.01;
        console.log("Resume Time:", resumeTime)
        this.vid.currentTime = resumeTime;
    },
    getFileInfo: function(resume) {
        console.log("getFileInfo")
        $.ajax({
          url: "/file-info/"+this.fid,
          dataType: 'json',
          cache: false
        }).done(_.bind(this.processFileInfo, this))
        .always(_.bind(function(data){
            if (resume) {
                this.vid.addEventListener("canplaythrough", _.once(_.bind(this.doResume, this, data)));
            }
        }, this));
    },
    processFileInfo:function(data, textStatus, jqXHR) {
        console.log("processFileInfo:", data);
        conductor.set('playing', data);
    },
    getSrc: function() {
        var uri = "/stream/"+this.fid+"/?mimetypes=",
            mimetypes = [];
        _.each(this.supportedMimeTypes, function(mimeType, ext){
            mimetypes.push(encodeURIComponent(mimeType))
            // this.$el.append(mimeType+"<br>");
        }, this);
        uri += mimetypes.join(",");
        return uri;
    },
    next: function() {
        console.log("webPlayer Next");
        this.deIncSkipScore();
        this.incIndex();
    },
    deIncSkipScore: function() {
        var uids = this.getUids();
        if (!uids) {
            return;
        }
        $.ajax({
          url: "/deinc-skip-score/"+this.fid+"/"+uids.join(","),
          dataType: 'json',
          cache: false
        });
    },
    incIndex: function(){
        var playlistIndex = this.playlistIndex + 1;
        console.log("this.playlistIndex:", playlistIndex);
        this.setIndex(playlistIndex);
        this.popPreload();
    },
    setIndex: function(idx, resume) {
        if (idx < 0) {
            return;
        }
        console.log("setIndex:this.playlist.length",this.playlist.length)
        console.log("IDX",idx)
        if (idx == this.playlist.length) {
            console.log("idx == this.playlist.length:", idx,'==', this.playlist.length);
            this.popPreload(_.once(
                _.bind(function(){
                    this.setIndex(idx);
                }, 
                this)
            ));
        }
        if (this.playlist[idx]) {
            this.playlistIndex = idx;
            this.setSrc(this.playlist[this.playlistIndex], resume);
        }
        if (idx == this.playlist.length) {
            this.popPreload();
        }
    },
    popPreload: function(cb) {
        if (this.popPreload_locked) {
            return;
        }
        this.popPreload_locked = true;
        $.ajax({
          url: "/pop-preload/",
          dataType: 'json',
          cache: false
        }).done(_.bind(this.appendToPlaylist, this, cb));
    },
    appendToPlaylist: function(cb, data, textStatus, jqXHR) {
        if (data) {
            this.playlist.push(data.fid);
            if (cb) {
                cb();
            }
        }
        this.popPreload_locked = false;
    },
    prev: function() {
        console.log("webPlayer Prev");
        var playlistIndex = this.playlistIndex;
        playlistIndex -= 1;
        this.setIndex(idx);
    },
    incSkipScore: function() {
        var uids = this.getUids();
        if (!uids) {
            return;
        }
        $.ajax({
          url: "/inc-skip-score/"+this.fid+"/"+uids.join(","),
          dataType: 'json',
          cache: false
        });
    },
    render: function(){
        if (_.isEmpty(this.supportedMimeTypes)) {
            this.$el.text("Your browser does not support the web player");
            return this;
        }
        this.$el.empty();
        this.$el.append(this.vid);
        this.$el.css("width","100%");
        this.vid.style.width="100%";
        this.$el.append("<br clear='all'>");
        this.vid.src = this.getSrc();
        if (this.conductor.isRemoteMode()) {
            // this.$el.hide();
        }
        return this;
    }
});

window.ConductorModel = Backbone.DeepModel.extend({
    url: "/status/",
    idAttribute: "fid",
    listenerLength: 0,
    fetchInterval: null,
    checkStateInterval: null,
    nano_second: 1000000000,
    initialize: function(options) {
        Backbone.DeepModel.prototype.initialize.apply(this, arguments);
        this.on("change:playing.listeners_ratings", this.checkListenersLength);
        options = options || {};
        var mode = options.mode || "remote",
            uids = options.uids || [];
        this.set({
            "mode": mode,
            "uids": uids
        });
        this.initInterval();
        this.on("change:mode", _.bind(this.setModeCookie, this));
    },
    setModeCookie: function() {
        eraseCookie("playerMode");
        createCookie('playerMode', conductor.get("mode"), 365);
    },
    initInterval: function(){
        if (this.isRemoteMode()) {
            this.initRemoteIntervals();
            return;
        }
        this.initWebIntervals();
    },
    initRemoteIntervals: function() {
        if (!this.fetchInterval) {
            this.fetchInterval = setInterval(_.bind(this.doFetch, this), 5000);
        }
        if (!this.checkStateInterval) {
            this.checkStateInterval = setInterval(_.bind(this.incSecond, this), 1000);
        }
    },
    initWebIntervals: function() {
        if (this.fetchInterval) {
            clearInterval(this.fetchInterval);
            this.fetchInterval = null;
        }
        if (this.checkStateInterval) {
            clearInterval(this.checkStateInterval);
            this.checkStateInterval = null;
        }
    },
    doFetch: function() {
        if (this.isRemoteMode()) {
            this.fetch();
        }
        return true;
    },
    isWebMode: function(){
        return this.get("mode") == 'web';
    },
    isRemoteMode: function(){
        return this.get("mode") != 'web';
    },
    incSecond: function() {
        var state = this.get('state');
        if (state != 'PLAYING') {
            return true;
        }
        var pos = parseInt(this.get('pos_data.pos_int')) || 1;
        pos += this.nano_second;
        this.set('pos_data.pos_int', pos);
        window.updateTime(Math.floor(pos / this.nano_second));
        return true;
    },
    checkListenersLength: function() {
        var listeners_ratings = this.get("playing.listeners_ratings") || [],
            listeners_ratings_length = listeners_ratings.length,
            rating_changed = false;

        _.each(this.changed.playing.listeners_ratings, function(ratingInfo){
            if (ratingInfo.rating) {
                rating_changed = true;
            }
        });
        if (rating_changed) {
            this.trigger("change:playing.listeners_ratings.length");
            this.listenerLength = listeners_ratings_length;
            return;
        }
        
        if (this.listenerLength == listeners_ratings_length) {
            return;
        }
        this.listenerLength = listeners_ratings_length;
        this.trigger("change:playing.listeners_ratings.length");
    }
});

window.ControllerView = Backbone.View.extend({
    rendered: false,
    pause_re: /\/pause\/$/i,
    next_re: /\/next\/$/i,
    prev_re: /\/prev\/$/i,
    initialize:function(options){
        Backbone.View.prototype.initialize.apply(this, arguments);
        this.$els = options.$els;
        this.conductor = options.conductor;
        this.webPlayer = options.webPlayer;
    },
    onClick: function(el, evt){
        evt.preventDefault();
        setTimeout(_.bind(this.clearActive, this), 10);
        var mode = this.conductor.get("mode");
        console.log("MODE:", mode);
        if (mode == "remote") {
            this.doRemoteAction(el);
            return;
        }
        this.doWebPlayerAction(el);
    },
    doRemoteAction: function(el){
        console.log("doRemoteAction el:", el);
        $.ajax({
          url: el.href,
          dataType: 'json',
          cache:false,
        }).done(_.bind(this.onDone, this));
    },
    doWebPlayerAction: function(el) {
        var href = el.href;
        console.log("doWebPlayerAction href:",href);
        if (this.pause_re.test(href)) {
            if (this.webPlayer.vid.paused) {
                this.webPlayer.vid.play();
            } else {
                this.webPlayer.vid.pause();
            }
        } else if (this.next_re.test(href)) {
            this.webPlayer.next();
        } else if (this.prev_re.test(href)) {
            this.webPlayer.prev();
        }
    },
    onDone:function(data, textStatus, jqXHR){
        this.conductor.set(data);
    },
    clearActive: function() {
        this.$els.removeClass("ui-btn-active");
    },
    render:function() {
        if (this.rendered) {
            return this;
        }
        this.rendered = true;
        var _this = this;
        this.$els.each(function(idx, el){
            $(el).bind("tap", _.bind(_this.onClick, _this, el));
        });
        return this;
    }
});

window.RatingView = Backbone.View.extend({
    initialize: function(options){
        Backbone.View.prototype.initialize.apply(this, arguments);
        this.conductor = options.conductor;
        this.conductor.on("change:playing.fid", this.renderRatings, this);
        this.conductor.on("change:playing.listeners_ratings.length", this.renderRatings, this);

    },
    renderRatings: function(){
        var ratings = this.conductor.get('playing.listeners_ratings') || [];
        this.$el.empty()
        _.each(ratings, function(rating){
            var ratingDiv = $("<div></div>");
            this.$el.append(ratingDiv);
            var ratingView = new RatingButtonView({
                "user": rating['user.uname'],
                "uid": rating.uid,
                "fid": rating.fid,
                "rating": rating.rating,
                "el": ratingDiv
            }).render();
        }, this);
    },
    render:function () {
        this.renderRatings();
        return this;
    }
});

window.createCookie = function(name, value, days) {
    if (days) {
        var date = new Date();
        date.setTime(date.getTime()+(days*24*60*60*1000));
        var expires = "; expires="+date.toGMTString();
    } else var expires = "";
    document.cookie = name+"="+value+expires+"; path=/";
}

window.readCookie = function(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

window.eraseCookie = function (name) {
    createCookie(name,"",-1);
}

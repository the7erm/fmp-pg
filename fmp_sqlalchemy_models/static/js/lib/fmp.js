window.RatingButtonView = Backbone.View.extend({
    rating: 6,
    uid: 0,
    fid: 0,
    template: _.template($("#tpl-rating-button").html()),
    initialize: function(options){
        Backbone.View.prototype.initialize.apply(this, arguments);
        this.fid = options.fid;
        this.rating = options.rating;
        this.uid = options.uid;
        this.user = options.user;
        this.conductor = options.conductor;
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
          dataType: 'json',
        }).done(function(data, textStatus, jqXHR) {
            var conductor_fid = this.conductor.get("playing.fid") || 0;
            if (conductor_fid == _this.fid) {
                this.conductor.set({"playing": data});
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
    model: HistoryModel,
    initialize: function() {
        Backbone.Collection.prototype.initialize.apply(this, arguments);
        this.sortField = "time_played";
        this.sortDirection = "DESC";
    },
    setSortField: function (field, direction) {
       this.sortField = field;
       this.sortDirection = direction;
    },

    comparator: function (m) {
       return m.get(this.sortField);
    },

    // Overriding sortBy (copied from underscore and just swapping left and right for reverse sort)
    sortBy: function (iterator, context) {
       var obj = this.models,
           direction = this.sortDirection;

       return _.pluck(_.map(obj, function (value, index, list) {
           return {
               value: value,
               index: index,
               criteria: iterator.call(context, value, index, list)
           };
       }).sort(function (left, right) {
           // swap a and b for reverse sort
           var a = direction === "ASC" ? left.criteria : right.criteria,
               b = direction === "ASC" ? right.criteria : left.criteria;

           if (a !== b) {
               if (a > b || a === void 0) return 1;
               if (a < b || b === void 0) return -1;
           }
           return left.index < right.index ? -1 : 1;
       }), 'value');
    }
})

window.HistoryViewLiView = Backbone.View.extend({
    initialize: function(options){
        Backbone.View.prototype.initialize.apply(this, arguments);
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
        Backbone.View.prototype.initialize.apply(this, arguments);
        this.collection = options.collection;
        this.model = options.model;
        this.el = options.el;
        this.collection.setSortField("time_played", "ASC");
        this.collection.on("add", this.onAddCollection, this);
        this.conductor = options.conductor;
        this.conductor.on("change:playing.fid", _.bind(this.clearHistory, this));
        this.conductor.on("change:playing.history", _.bind(this.updateHistory, this));
    },
    clearHistory: function() {
        this.$ul.empty();
        this.collection.reset();
    },
    updateHistory: function(){
        var playing_history = this.conductor.get('playing.history'),
            rebuild = false;
        _.each(playing_history, function(v, k) {
            var present = this.collection.get(v.uhid);
            v.time_played = new Date(v.time_played);
            v.date = new Date(v.date);
            if (!present) {
                rebuild = true;
            } else {
                present.set(v);
            }
        }, this);
        if (rebuild) {
            this.clearHistory();
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
        }
    },
    onAddCollection: function(model, collection, evt) {
        console.log("onAddCollection evt:", evt);
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
    refetchTimeout: null,
    initialize: function(options){
        Backbone.View.prototype.initialize.apply(this, arguments);
        this.vid = document.createElement('audio');
        this.vid.id = "video-player";
        this.vid.style.width = "100%";
        this.vid.seekable = true;
        this.vid.controls = true;
        this.vid.loop = false;
        this.bindEvents();
        this.checkSupportedTypes();
        this.el = options.el;
        this.fid = options.fid;
        this.resume = options.resume || false;
        this.resetTimes();
        this.$playingStateImg = $('.playing-state-img');
        this.conductor = options.conductor;
        this.conductor.on("change:playing.fid", _.bind(this.setSrcToConductor, this));
        this.conductor.on("change:mode", _.bind(this.onChangeMode, this));
        // this.conductor.on("change:pos_data.pos_str", _.bind(this.onPosChange, this));
        this.vid.addEventListener("canplay", function(){
            // alert("canplay");
        });
        this.vid.addEventListener("loadstart", function(){
            // alert("loadstart");
        });
        this.setSrcToConductor();
    },
    onChangeMode: function(){
        if (this.conductor.isRemoteMode()) {
            this.$el.hide();
            this.vid.pause();
        } else {
            this.$el.show();
            this.vid.play();
            var ns = parseInt(this.conductor.get("pos_data.pos_int"));
                seconds = ns / this.conductor.nano_second;
            this.vid.currentTime = seconds;
        }
    },
    setSrcToConductor: function() {
        if (this.conductor.isWebMode()) {
            return;
        }
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
    bindEvents: function(){
        
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
        /*
        _.each(events, function(evt){
            this.vid.addEventListener(evt, _.bind(console.logEvent, this));
        }, this); */
        this.vid.addEventListener('timeupdate', _.bind(this.onTimeStatus, this));
        this.vid.addEventListener('ended', _.bind(this.markAsCompleted, this));
        this.vid.addEventListener("play", _.bind(this.onPlay, this));
        this.vid.addEventListener("pause", _.bind(this.onPause, this));
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
        if (this.conductor.isRemoteMode()) {
            return this.conductor.get("uids") || [];
        }
        var uids = this.conductor.get("singleModeUid") || "";
        return [uids];
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
        console.log("sendPercentPlayed uids:", uids, percent_played);
        $.ajax({
          url: "/mark-as-played/"+this.fid+"/"+percent_played+"/"+uids.join(","),
          dataType: 'json',
          cache: false,
          type: 'POST',
          data: this.postData()
        }).done(_.bind(this.processFileInfo, this));
    },
    postData: function() {
        return {
            'mode': this.conductor.get('mode'),
            'webPlayerMode': this.conductor.get('webPlayerMode'),
            'singleModeUid': this.conductor.get('singleModeUid')
        }
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
    setSrc: function(fid) {
        this.fid = fid;
        this.vid.src = this.getSrc();

        var isWebMode = this.conductor.isWebMode();
        if (isWebMode) {
            this.vid.autoplay = true;
        } else {
            this.vid.autoplay = false;
        }
        this.vid.load();
        if (isWebMode) {
            // quirk with android.
            this.vid.autoplay = true;
        } else {
            this.vid.autoplay = false;
        }
        this.getFileInfo();
        this.resetTimes();
    },
    doResume:function(data){
        if (this.conductor.isRemoteMode()) {
            return;
        }
        if (!this.resume) {
            return;
        }
        this.resume = false;
        console.log("DATA:", data)
        console.log(data.listeners_ratings);
        console.log("this.vid.duration:", this.vid.duration);
        var resumeTime = this.vid.duration * parseFloat(data.listeners_ratings[0].percent_played) * 0.01;
        console.log("Resume Time:", resumeTime)
        this.vid.currentTime = resumeTime;
        this.vid.play();
    },
    getFileInfo: function() {
        console.log("getFileInfo");
        $.ajax({
          url: "/file-info/"+this.fid,
          dataType: 'json',
          cache: false
        }).done(_.bind(this.processFileInfo, this))
          .fail(_.bind(this.retryIn2Seconds, this));
    },
    clearRefetch: function(){
        if (this.refetchTimeout) {
            clearTimeout(this.refetchTimeout);
            this.refetchTimeout = null;
        }
    },
    retryIn2Seconds: function() {
        this.clearRefetch();
        this.refetchTimeout = setTimeout(_.bind(this.getFileInfo ,this), 2000);
    },
    processFileInfo: function(data, textStatus, jqXHR) {
        if (!data) {
            return;
        }
        this.clearRefetch();
        console.log("processFileInfo:", data);
        this.conductor.set('playing', data);
        if (this.resume) {
            this.vid.addEventListener("canplaythrough", _.once(
                _.bind(
                    this.doResume, this, data
                )));
        }
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
        var idx = this.playlistIndex + 1;
        console.log("incIndex idx:", idx);
        this.setIndex(idx);
        this.popPreload();
    },
    setIndex: function(idx) {
        if (idx < 0) {
            return;
        }
        console.log("setIndex:this.playlist.length", this.playlist.length);
        console.log("IDX", idx);
        console.log("this.playlist[idx]", this.playlist[idx]);

        if (idx == this.playlist.length) {
            console.log("idx == this.playlist.length:", idx,'==', this.playlist.length);
            this.popPreload(_.once(
                _.bind(function(){
                    this.setIndex(idx);
                }, 
                this)
            ));
            return;
        }

        if (!_.isUndefined(this.playlist[idx])) {
            this.playlistIndex = idx;
            this.setSrc(this.playlist[idx]);
        }
        
    },
    popPreload: function(cb) {
        if (this.popPreload_locked) {
            console.log("popPreload_locked")
            return;
        }
        this.popPreload_locked = true;
        this.resume = false;
        var uids = this.getUids();
        $.ajax({
          url: "/pop-preload/"+uids.join(","),
          dataType: 'json',
          cache: false
        }).done(_.bind(this.appendToPlaylist, this, cb))
          .fail(_.bind(
            function() {
                this.popPreload_locked = false;
            }, this));
    },
    appendToPlaylist: function(cb, data, textStatus, jqXHR) {
        if (data) {
            this.playlist.push(data.fid);
            if (cb) {
                cb();
            }
        } else {
            console.log("NO DATA");
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
        if (this.conductor.isRemoteMode()) {
            this.$el.hide();
            this.vid.pause();
        } else {
            this.$el.show();
            this.resume = true;
            this.vid.autoplay = true;
            this.playlist.push(this.fid);
            this.setIndex(0);
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
            uids = options.uids || [],
            webPlayerMode = options.webPlayerMode || "multi",
            singleModeUid = options.singleModeUid || uids[0] || [];
        this.set({
            "mode": mode,
            "uids": uids,
            "webPlayerMode": webPlayerMode,
            "singleModeUid": singleModeUid
        });
        this.initInterval();
        this.on("change:mode", _.bind(this.setPlayerMode, this));
        this.on("change:singleModeUid", _.bind(this.setSingleUid, this));
        this.on("change:webPlayerMode", _.bind(this.setWebPlayerMode, this));
    },
    setPlayerMode: function() {
        var mode = this.get("mode");
            currentTime = window.webPlayer.vid.currentTime;
        $.ajax({
          url: "/set-mode/"+mode+"/"+currentTime,
          dataType: 'json',
          cache:false,
        }).done(function(){});
    },
    setSingleUid: function() {
        $.ajax({
          url: "/set-single-player-uid/"+this.get("singleModeUid"),
          dataType: 'json',
          cache:false,
        }).done(function(){  });
    },
    setWebPlayerMode: function(){
        $.ajax({
          url: "/set-web-player-mode/"+this.get("webPlayerMode"),
          dataType: 'json',
          cache:false,
        }).done(function(){  });
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
        this.fetch();
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


window.createCookie = function(name, value, days) {
    if (typeof(days) == 'undefined') {
        days = 365;
    }
    var date = new Date();
    date.setTime(date.getTime()+(days*24*60*60*1000));
    var expires = "; expires="+date.toGMTString(),
        cookieData = name+"="+value+expires+"; path=/";
    console.log("createCookie:",cookieData)
    document.cookie = cookieData;
}

window.readCookie = function(name) {
    var nameEQ = name + "=",
        ca = document.cookie.split(';'),
        value = null;
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') {
            c = c.substring(1,c.length);
        }
        if (c.indexOf(nameEQ) == 0) {
            value = c.substring(nameEQ.length,c.length);
            break;
        }
    }
    console.log("readCookie:", name, value);
    return value;
}

window.eraseCookie = function (name) {
    createCookie(name, "", -1);
    console.log("eraseCookie:",name);
}

window.AppRouter = Backbone.Router.extend({
    routes:{
        "":"home",
        "search/": "search",
        "search/:query":        "search",  // #search/kiwis
        "search/:query/p:page": "search"   // #search/kiwis/p7
    },
 
    home: function () {
        $("#history").show();
        $("#search").hide();
        console.log("home");
    },
 
    search: function (keywords, page) {
        keywords = keywords || "";
        page = page || 0;
        console.log("keywords:", keywords)
        console.log("page:", page)
        $("#history").hide();
        $("#search").show().empty();
        $("#search").trigger("create");
        var searchView = new SearchView({
            el: "#search",
            collection: new SearchCollection({
                keywords: keywords,
                page: page
            })
        }).render();
    },
 
});

window.SearchCollection = Backbone.Collection.extend({
    model: null,
    pageModel: null,
    initialize: function(options){
        this.model = Backbone.DeepModel;
        this.pageModel = new Backbone.Model({});
        this.pageModel.idAttribute = "fid";
        Backbone.Collection.prototype.initialize.apply(this, arguments);
        var keywords = options.keywords || "",
            page = parseInt(options.page) || 0;
        this.pageModel.set({
            keywords: keywords,
            page: page,
        });
        this.pageModel.on("change", _.bind(this.fetch, this));
    },
    "url": function(){
        return "/search/?q="+encodeURIComponent(this.pageModel.get("keywords"))
    }
});

window.SearchView = Backbone.View.extend({
    template: _.template($("#tpl-search-view").html()),
    itemTemplate: _.template($("#tpl-search-item").html()),
    collection: null,
    initialize: function(options) {
        Backbone.View.prototype.initialize.apply(this, arguments);
        this.collection = options.collection || new SearchCollection();
        this.collection.on("add", _.bind(this.onAddCollection, this));
    },
    onAddCollection: function(model){
        console.log("onAddCollection", model);
        this.$results.append(this.itemTemplate({
            artist_title: model.get('artist_title') || "",
            artists: model.get('artists') || null,
            genres: model.get('genres') || null,
            titles: model.get('titles') || null,
            albums: model.get('albums') || null,
            listeners_ratings: model.get('listeners_ratings') || null,
            fid: model.get('fid') || null,
            ltp: model.get('ltp') || null
        }));
        try {
            this.$results.listview("refresh");
        } catch(e) {
            $("#search").trigger("create");
        }
        
    },
    render: function() {
        this.$el.html(this.template());
        this.$results = this.$el.find(".results");
        this.$results.trigger("create");
        console.log("CREATED")
        this.collection.fetch();
        return this;
    }
});

window.RatingModel = Backbone.DeepModel.extend({
    name: "RatingModel",
    idAttribute: "ufid",
    initialize: function () {
        Backbone.DeepModel.prototype.initialize.apply(this, arguments);
    },
    url: function() {
        var rating = parseInt(this.get('rating'));
        if (!rating) {
            rating = "0";
        }
        // /rate/<fid>/<uid>/<rating>
        return "/rate/"+this.get("fid")+"/"+this.get("uid")+"/"+rating;
    },
    getTrueScore: function () {
        var trueScore = this.get('true_score') || -1;
        return trueScore.toFixed(1);
    },
    getRating: function(defaultValue) {
        if (!defaultValue) {
            defaultValue = 6;
        }
        var rating = this.get('rating');
        if (parseInt(rating) === 0) {
            return 0;
        }
        return rating || defaultValue;
    },
});

window.RatingsCollection = Backbone.Collection.extend({
    model: RatingModel,
    name: "RatingsCollection"
});

window.RatingView = Backbone.View.extend({
    name: "RatingView",
    model: null,
    template: _.template($("#tpl-rating").html()),
    table: null,
    starSize: "big",
    iconSet: {
        cancelOff : 'cancel-off-big.png',
        cancelOn  : 'cancel-on-big.png',
        starHalf  : 'star-half-big.png',
        starOff   : 'star-off-big.png',
        starOn    : 'star-on-big.png'
    },
    initialize:function(options){
        Backbone.View.prototype.initialize.apply(this, arguments);
        this.model = options.model || new RatingModel();
        this.model.on("change", this.onChange, this);
        if (options.table) {
            this.table = options.table;
        }
        if (options.starSize && options.starSize == 'small') {
            this.iconSet = {
                cancelOff : 'cancel-off.png',
                cancelOn  : 'cancel-on.png',
                starHalf  : 'star-half.png',
                starOff   : 'star-off.png',
                starOn    : 'star-on.png'
            };
        }
    },
    onChange:function(){
        console.log("onChange changedAttributes:", this.model.changedAttributes());
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
        console.log("render");
        console.log("RatingView model:", this.model.toJSON());
        var table = $("<table />");
        table.append(this.template(this.model.toJSON()));
        this.$el = table.find('tr');
        delete table;
        this.table.append(this.$el);
        this.$tdStarRating = this.$el.find('.star-rating');
        this.renderStars();
        return this;
    },
    renderStars: function(){
        var initData = {
                path: "/static/img/raty/",
                score: function () {
                    var score = $(this).data("rating");
                    if (score == 6) {
                        return "0";
                    }
                    return score;
                },
                click: _.bind(this.onRate, this),
                cancel: true,
                hints: ['Not the greatest', 
                        'Meh',
                        'Good', 
                        'Really good', 
                        'Love it!'],
                cancelHint: 'Please don\' play this ever again for me',
            };
        _.extend(initData, this.iconSet);
        this.$tdStarRating.raty(initData);
      },
      onRate: function(score, evt){
          evt.preventDefault();
          if (score == null) {
              score = 0;
              this.$tdStarRating.raty('score', "0");
          }
          if (!score) {
              score = "0";
          }
          this.model.set("rating", score);
          this.model.save();
      },
      rate: function (ratingData) {
            return;
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

window.RatingsTableView = Backbone.View.extend({
    debug: false,
    name: "RatingsTableView",
    collection: null,
    template: _.template($("#tpl-ratings-table").html()),
    ratingViews: {},
    starSize:"big",
    log: function(){
        console.log.apply(console, args);
    },
    initialize: function(options) {
        Backbone.View.prototype.initialize.apply(this, arguments);
        this.collection = options.collection || new RatingsCollection();
        this.collection.on("add", this.onAdd, this);
        this.collection.on("change", this.onChange, this);
        this.collection.on("remove", this.onRemove, this);
        
        if (options.$el) {
            this.$el = options.$el;
        }
        if (options.starSize && options.starSize == "small") {
            this.starSize = "small";
        }
    },
    onChange: function(model, arg2){
        if (!model) {
            return; 
        }
        console.log("?????????????????????????????");
        console.log("changedAttributes:", model.changedAttributes());
        var ufid = model.get('ufid');
        if (!this.ratingViews[ufid]) {
            console.log("can't render rating:",ufid);
            this.onAdd(model);
        }
        console.log("/?????????????????????????????");
        this.hideOrShow();
    },
    onAdd: function(model){
        console.log("++++++++++++++++++++++");
        console.log("onAdd:",model);
        var ufid = model.get('ufid');
        this.ratingViews[ufid] = new RatingView({
            model: model,
            table: this.$el.find('.ratings-table'),
            starSize: this.starSize
        }).render();
        console.log("/++++++++++++++++++++++");
        this.hideOrShow();
    },
    onRemove: function(model){
        console.log("---------------------------");
        console.log("onRemove:",model);
        var ufid = model.get('ufid');
        this.$el.find("#ufid-"+ufid).remove();
        delete this.ratingViews[ufid];
        console.log("/---------------------------");
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
        console.log("render *(***");
        this.$el.html(this.template({collection: this.collection}));
        this.collection.each(function(model){
            console.log("ADD MODEL:", model);
            this.onAdd(model);
        }, this);
        this.hideOrShow();
        return this;
    }
});

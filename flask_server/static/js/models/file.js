
var RatingModel = Backbone.Model.extend({
    idAttribute: "usid"
});

var AlbumModel = Backbone.Model.extend({
    idAttribute: "alid"
});

var GenreModel = Backbone.Model.extend({
    idAttribute: "gid"
});

var ArtistModel = Backbone.Model.extend({
    idAttribute: "aid"
});

var FileModel = Backbone.Model.extend({
    idAttribute: "fid",
    initialize: function() {
        
    }
});

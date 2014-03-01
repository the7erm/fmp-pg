
var RatingView = Backbone.View.extend({
    className: "rating-box",
    template: $("#tpl-rating").html()
});

var FileView = Backbone.View.extend({

    className: "file-box",
    artists: [],
    albums: [],
    genres: [],
    ratings: [],
    template: $("#tpl-row").html(),

    events: {
    },

    initialize: function() {
        // this.listenTo(this.model, "change", this.render);
    },

    render: function() {
        console.log(this.$el);
        this.$el.html("<div>WORKS!</div>");
        return this;
    }
});

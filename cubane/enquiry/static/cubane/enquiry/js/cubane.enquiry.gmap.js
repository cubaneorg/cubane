(function(globals){
"use strict";


cubane.namespace('cubane.enquiry.gmap');


cubane.enquiry.gmap.DEFAULT_ZOOM_LEVEL = 8;


/*
 * Loads the google map javascript library
 * asynchoniously and initialises all google map canvases.
 */
cubane.enquiry.gmap.GMapController = function () {
    this.maps = [];
    var canvases = document.querySelectorAll('.enquiry-map-canvas');

    if ( canvases.length > 0 ) {
        this.loadGMap(canvases);
    }
};

cubane.enquiry.gmap.GMapController.prototype = {
    loadGMap: function (canvases) {
        var self = this;
        cubane.enquiry.gmap.initialize = function() {
            self.initializeMapCanvases(canvases);
        };

        // is google maps already loaded?
        if (window['google'] === undefined || window['google']['maps'] === undefined) {
            var script = document.createElement('script');
            script.type = 'text/javascript';
            script.src = 'https://maps.googleapis.com/maps/api/js?';

            var api_key = canvases[0].getAttribute('data-key');
            if (api_key !== '') {
                script.src += 'key=' + api_key + '&';
            }

            script.src += 'callback=cubane.enquiry.gmap.initialize';
            document.body.appendChild(script);
        } else {
            self.initializeMapCanvases(canvases);
        }
    },


    initializeMapCanvases: function (canvases) {
        for ( var i = 0; i < canvases.length; i++ ) {
            this.maps.push(
                new cubane.enquiry.gmap.GMapCanvasController(canvases[i])
            );
        }
    },


    dispose: function () {
        for ( var i = 0; i < this.maps.length; i++ ) {
            this.maps[i].dispose();
        }
        this.maps = null;
    }
};


/*
 * Initialises and manages one particular gooole map convas, auto-resizes
 * the map when it becomes visible or window gets resized and provides a
 * draggable marker and a search facility.
 */
cubane.enquiry.gmap.GMapCanvasController = function (canvas) {
    this.canvas = canvas;

    // extract data
    var lat = parseFloat(this.canvas.getAttribute('data-lat'));
    var lng = parseFloat(this.canvas.getAttribute('data-lng'));
    var zoom = parseFloat(this.canvas.getAttribute('data-zoom'));
    var title = this.canvas.getAttribute('data-title');

    // defaults
    if ( !zoom ) zoom = cubane.enquiry.gmap.DEFAULT_ZOOM_LEVEL;
    if ( !title ) title = '';

    // create map
    var pos = new google.maps.LatLng(lat, lng);
    var options = {
        zoom: zoom,
        center: pos,
        scrollwheel: false,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        draggable: !("ontouchend" in document)
    };
    this.map = new google.maps.Map(canvas, options);

    // create marker
    this.marker = new google.maps.Marker({
        position: pos,
        map: this.map,
        title: title
    });

    // create geo-coder
    this.geocoder = new google.maps.Geocoder();
};

cubane.enquiry.gmap.GMapCanvasController.prototype = {
    dispose: function () {
        this.geocoder = null;
        this.marker.setMap(null);
        this.marker = null;
        this.map = null;
        this.canvas = null;
    }
}


/*
 * Create new google map controller when page has been loaded.
 */
window.addEventListener('load', function() {
    var gmapController = new cubane.enquiry.gmap.GMapController();

    function dispose() {
        if (gmapController !== undefined) {
            gmapController.dispose();
            gmapController = undefined;
        }
    }

    // unload page
    window.addEventListener('unload', function() {
        dispose();
    });

    // support turbolinks/Single page website
    document.addEventListener('enter-page', function() {
        if (gmapController === undefined) {
            gmapController = new cubane.enquiry.gmap.GMapController();
        }
    });

    document.addEventListener('leave-page', function() {
        dispose();
    });
});

}(this));

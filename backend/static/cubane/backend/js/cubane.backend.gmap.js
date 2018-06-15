(function(globals){
"use strict";


cubane.namespace('cubane.backend.gmap');


cubane.backend.gmap.ZOOM_LEVEL_ROOFTOP     = 18;
cubane.backend.gmap.ZOOM_LEVEL_RANGE       = 14;
cubane.backend.gmap.ZOOM_LEVEL_CENTER      = 12;
cubane.backend.gmap.ZOOM_LEVEL_APPROXIMATE = 10;
cubane.backend.gmap.DEFAULT_ZOOM_LEVEL     = 8;


/*
 * Indicates if we are already loading google maps.
 */
var loading = false;


/*
 * Load gogole map api async.
 */
cubane.backend.gmap.load = function load(api_key) {
    // load google maps only once
    if (loading) return;
    loading = true;

    // callback function after we loaded google maps
    cubane.backend.gmap.initialize = function() {
        // notify others that google maps is now available
        $(document).trigger('google-maps-loaded');
    };

    // start loading google maps async.
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = 'https://maps.googleapis.com/maps/api/js?';
    if (api_key) {
        script.src += 'key=' + api_key + '&';
    }

    script.src += 'callback=cubane.backend.gmap.initialize';
    document.body.appendChild(script);
};


/*
 * Initialises and manages one particular gooole map convas, auto-resizes
 * the map when it becomes visible or window gets resized and provides a
 * draggable marker and a search facility.
 */
cubane.backend.gmap.GMapCanvasController = function (canvas) {
    this.canvas = $(canvas);

    var pos = this.getInitialPosition();
    var zoom = this.getInitialZoom();

    // create map
    var options = {
        zoom: zoom,
        center: pos,
        scrollwheel: false,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    this.map = new google.maps.Map(canvas, options);

    // create marker
    this.marker = new google.maps.Marker({
        position: pos,
        map: this.map,
        draggable: true,
        title: 'Your Location'
    });

    // create geo-coder
    this.geocoder = new google.maps.Geocoder();

    this._bound = {
        onTabSwitched: $.proxy(this.onTabSwitched, this),
        onResize: $.proxy(this.onResize, this),
        updateMap: $.proxy(this.updateMap, this),
        onSearch: $.proxy(this.onSearch, this),
        doSearch: $.proxy(this.doSearch, this),
        onFormSubmit: $.proxy(this.onFormSubmit, this)
    };

    $(document).on('cubane-tab-switched', this._bound.onTabSwitched);
    $(document).on('cubane-form-submit', this._bound.onFormSubmit);

    // fill space?
    if (this.canvas.hasClass('fill-space')) {
        $(window).on('resize', this._bound.onResize);
        this.updateMap();
    }

    // search input field
    if (this.canvas.hasClass('searchable')) {
        this.makeSearchable();
    }
};

cubane.backend.gmap.GMapCanvasController.prototype = {
    dispose: function () {
        $(document).off('cubane-tab-switched', this._bound.onTabSwitched);
        $(window).off('resize', this._bound.onResize);

        if ( this.searchField ) {
            this.searchField.off('keydown', this._bound.onSearch);
            this.searchField = null;
        }

        this.geocoder = null;
        this.marker.setMap(null);
        this.marker = null;
        this.map = null;
        this.canvas = null;
    },


    /*
     * Fired, whenever we switch tabs, which usually means that we have to
     * refresh the map because it became visible again.
     */
    onTabSwitched: function () {
        this.updateMap();
    },


    /*
     * Fired whenever we need to resize the map. We dellay the actual resize
     * of the map, since we might get quite a lot of resize events through...
     */
    onResize: function () {
		if ( this.updateMapTimer ) {
		    clearTimeout(this.updateMapTimer);
		}
		this.updateMapTimer = setTimeout(this._bound.updateMap, 200);
    },


    /*
     * Actually resize the map.
     */
    updateMap: function () {
        var wh = $(window).height();
		this.canvas.height(0);
		setTimeout($.proxy(function() {
    		this.canvas.height(wh);
	    	var h = wh - ($(document).height() - wh);
	    	this.canvas.height(h);
	    	google.maps.event.trigger(this.map, 'resize');
            this.map.setCenter(this.marker.getPosition());
	    }, this), 0);
    },


    /*
     * Create a search input field for searching a location by entering an
     * address.
     */
    makeSearchable: function () {
        this.searchField = $(
            '<input class="full-width gmap-search" name="_gmap_search" ' +
            'type="text" placeholder="Search for your location...">'
        );
        this._createField(this.searchField);
        this.searchField.focus();
        this.searchField.on('keydown', this._bound.onSearch);
    },


    /*
     * Fired when we change the search input field and we need to (re-)search.
     * This is quite delayed, so that we do not fire too many requests to
     * google.
     */
    onSearch: function (e) {
        // prevent form submission when pressing ENTER within search field
        var enter = e.keyCode === 13;
        if ( enter ) {
            e.preventDefault();
        }

        if ( this.onSearchTimer ) {
            clearTimeout(this.onSearchTimer);
        }

        // ask google right away if we see ENTER...
        if ( enter ) {
            this.doSearch();
        } else {
            this.onSearchTimer = setTimeout(this._bound.doSearch, 750);
        }
    },


    /*
     * Fired, before we submit the form, so that we have a chance to copy
     * the current marker's geo location into the corresponding input fields.
     */
    onFormSubmit: function () {
        // position
        var lat = $('#' + this.canvas.attr('data-lat'));
        var lng = $('#' + this.canvas.attr('data-lng'));
        if ( lat.length > 0 && lng.length > 0 ) {
            var pos = this.marker.getPosition();
            lat.val(pos.lat());
            lng.val(pos.lng());
        }

        // zoom
        var zoom = $('#' + this.canvas.attr('data-zoom'));
        if ( zoom.length > 0 ) {
            zoom.val(this.map.getZoom().toString());
        }
    },


    /*
     * Perform geo-location search by using google's geocoder. Updates the
     * marker and map's center position accordingly to the first result record
     * we get. Further, the zoom level is adjusted according to the level
     * of accuracy that google provides.
     */
    doSearch: function () {
        var onResponse = $.proxy(function(results, status) {
            if (status == google.maps.GeocoderStatus.OK) {
                var pos = results[0].geometry.location;
                this.map.setCenter(pos);
                this.zoomMapByAccuracy(results[0].geometry.location_type);
                this.marker.setPosition(pos);
            } else {
                // TODO: present error message as flash
            }
        }, this);

        this.geocoder.geocode({'address': this.searchField.val()}, onResponse);
    },


    /*
     * Return a zoom level that corresponds with the given level of accuracy
     * provided.
     */
    zoomMapByAccuracy: function (accuracy) {
        var zoom;

        if ( accuracy == 'ROOFTOP' ) {
            zoom = cubane.backend.gmap.ZOOM_LEVEL_ROOFTOP;
        } else if ( accuracy == 'RANGE_INTERPOLATED' ) {
            zoom = cubane.backend.gmap.ZOOM_LEVEL_RANGE;
        } else if ( accuracy == 'GEOMETRIC_CENTER' ) {
            zoom = cubane.backend.gmap.ZOOM_LEVEL_CENTER;
        } else if ( accuracy == 'APPROXIMATE' ) {
            zoom = cubane.backend.gmap.ZOOM_LEVEL_APPROXIMATE;
        } else {
            zoom = cubane.backend.gmap.DEFAULT_ZOOM_LEVEL;
        }

        this.map.setZoom(zoom);
    },


    /*
     * Return the initial marker and map position. We attempt to read this from
     * form fields first; otherwise we return a default geo location, which
     * is more or less norfolk with norwich at its center.
     */
    getInitialPosition: function () {
        var lat = $('#' + this.canvas.attr('data-lat')).val();
        var lng = $('#' + this.canvas.attr('data-lng')).val();
        if ( lat && lng ) {
            lat = parseFloat(lat);
            lng = parseFloat(lng);
            return new google.maps.LatLng(lat, lng);
        } else {
            if (window.CUBANE_DEFAULT_MAP_LOCATION) {
                // from settings
                var latlng = window.CUBANE_DEFAULT_MAP_LOCATION;
                return new google.maps.LatLng(latlng[0], latlng[1]);
            } else {
                // norfolk
                return new google.maps.LatLng(52.6370209, 1.2996577);
            }
        }
    },


    /*
     * Return the initial zoom level for the map.
     */
    getInitialZoom: function () {
        var zoom = $('#' + this.canvas.attr('data-zoom')).val();
        if ( zoom ) {
            return parseInt(zoom);
        } else {
            return cubane.backend.gmap.DEFAULT_ZOOM_LEVEL;
        }
    },


    /*
     * Create a new input field and attach it to the DOM.
     */
    _createField: function(field) {
        var c = $('<div class="controls"></div>');
        var f = $('<div class="field"></div>');
        c.append(f);
        f.append(field);
        c.insertBefore(this.canvas.closest('.controls'));
    }
};


/*
 * Create new google map controller when page has been loaded.
 */
$(window).load(function() {
    // load google maps if we have a map canvas
    var canvases = $('.map-canvas');
    var maps = [];
    if (canvases.length > 0) {
        var api_key = canvases.data('key')
        cubane.backend.gmap.load(api_key);

        // create a map controller for each canvas once google maps has
        // been loaded
        $(document).on('google-maps-loaded', function() {
            for ( var i = 0; i < canvases.length; i++ ) {
                maps.push(
                    new cubane.backend.gmap.GMapCanvasController(canvases.get(i))
                );
            }
        });
    }

    // dispose
    $(window).unload(function() {
        for ( var i = 0; i < maps.length; i++ ) {
            maps[i].dispose();
        }
        maps = null;
    });
});


}(this));

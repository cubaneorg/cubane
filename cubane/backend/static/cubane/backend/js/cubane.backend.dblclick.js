/*
 * Differentiates click and dbl-click.
 * Implementation is based on http://jsfiddle.net/Lhnqswpb/.
 * Original Source:
 * Author: Jacek Becela
 * Source: http://gist.github.com/399624
 * License: MIT
 */
(function (globals){
"use strict";


var matched, browser;

// Use of jQuery.browser is frowned upon.
// More details: http://api.jquery.com/jQuery.browser
// jQuery.uaMatch maintained for back-compat
jQuery.uaMatch = function( ua ) {
    ua = ua.toLowerCase();

    var match = /(chrome)[ \/]([\w.]+)/.exec( ua ) ||
        /(webkit)[ \/]([\w.]+)/.exec( ua ) ||
        /(opera)(?:.*version|)[ \/]([\w.]+)/.exec( ua ) ||
        /(msie) ([\w.]+)/.exec( ua ) ||
        ua.indexOf("compatible") < 0 && /(mozilla)(?:.*? rv:([\w.]+)|)/.exec( ua ) ||
        [];

    return {
        browser: match[ 1 ] || "",
        version: match[ 2 ] || "0"
    };
};

matched = jQuery.uaMatch( navigator.userAgent );
browser = {};

if ( matched.browser ) {
    browser[matched.browser] = true;
    browser.version = matched.version;
}

// Chrome is Webkit, but Webkit is also Safari.
if ( browser.chrome ) {
    browser.webkit = true;
} else if ( browser.webkit ) {
    browser.safari = true;
}

jQuery.browser = browser;


//
// Derived from above with support of live binding
//
jQuery.fn.onClickOrDblClick = function(scope, singleClickCallback, dblClickCallback, timeout) {
    return this.each(function() {
        var clicks = 0;
        if (jQuery.browser.msie) { // ie triggers dblclick instead of click if they are fast
            jQuery(this).on('dblclick', scope, function(event) {
                clicks = 2;
                dblClickCallback.call(this, event);
            }.bind(this));
            jQuery(this).on('click', scope, function(event) {
                setTimeout(function() {
                    if (clicks != 2) {
                        singleClickCallback.call(this, event);
                    }
                    clicks = 0;
                }, timeout || 200);
            }.bind(this));
        } else {
            jQuery(this).on('click', scope, function(event) {
                clicks++;
                if (clicks == 1) {
                    setTimeout(function() {
                        if (clicks == 1) {
                            singleClickCallback.call(this, event);
                        } else {
                            dblClickCallback.call(this, event);
                        }
                        clicks = 0;
                    }, timeout || 200);
                }
            }.bind(this));
        }
    });
};


}(this));

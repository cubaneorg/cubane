(function(globals){
"use strict";


/*
 * function.bind() helper (functionPrototypeBind.js)
 */
if (!Function.prototype.bind) {
    Function.prototype.bind = function (oThis) {
        if (typeof this !== "function") {
            // closest thing possible to the ECMAScript 5 internal IsCallable function
            throw new TypeError("Function.prototype.bind - what is trying to be bound is not callable");
        }

        var aArgs = Array.prototype.slice.call(arguments, 1),
        fToBind = this,
        fNOP = function () {},
        fBound = function () {
            return fToBind.apply(this instanceof fNOP && oThis
                ? this
                : oThis,
                aArgs.concat(Array.prototype.slice.call(arguments)));
        };

        fNOP.prototype = this.prototype;
        fBound.prototype = new fNOP();

        return fBound;
    };
}


/*
 * Add target=_blank for all external links
 */
var makeExternalLinksExternal = function () {
    $('a[rel="external"], a.external').each(function() {
        $(this).attr('target', '_blank');
    });
};


/*
 * Focus first input field of a POST form. If there is a visible error
 * on the screen, select the first field with an error.
 */
var focusFirstInputField = function () {
    // only consider forms with action=POST (case insensetive!)
    var base = $('form.auto-focus').filter(function() {
        return this.method.toLowerCase() == 'post';
    });

    // get condidates (fields)
    var fields = base
        .find('input, textarea, select')
        .not('.disabled')
        .not('[type="submit"], [type="reset"], [type="file"]')
        .filter(':visible');

    // is there a visible error on the page? -> only consider error fields
    if ( base.find('.error:visible').length > 0 ) {
        fields = fields.filter(function() {
            return $(this).closest('.error').length > 0;
        });
    }

    // focus
    fields.first().focus();
};


/*
 *  Make anything with class .clickable a link providing there is an <a href="link">
 */
var makeSectionClickable = function() {
    $('.clickable').on('click', function(){
        var url = $(this).find('a').attr('href');
        if (url) {
            window.location.href = url;
        }
    });
};

/*
 *  This gets the height of something with class .auto-height and gives that height to all things in .auto-height-container
 */
var getMaxHeight = function(cols) {
    var height = 0;
    for (var i = 0; i < cols.length; i++) {
        var h = cols.eq(i).height();
        if (h > height) {
            height = h;
        }
    }
    return height;
};

/*
 *  This finds the rows with .auto-height-container and sets the .auto-height into a var
 */
var resize_scheduled = false;   // timeout for a resize already?
var last_resize = 0;    //  time of the last resize

var makeColumnsSameHeight = function() {
    var rows = $('.auto-height-container');
    for (var i = 0; i < rows.length; i++) {
        var cols = rows.eq(i).find('.auto-height');
        cols.css('height', 'auto'); // reset to auto to resize to smaller height

        // exception for when used with row fluid spans that stack at this breakpoint
        // and the auto height is becoming unnecessary
        if (!rows.eq(i).hasClass('auto-height-no-phones') || $(window).width() > 767) {
            var h = getMaxHeight(cols);
            cols.height(h); // set the height instead of the css style (considers box-model)
        }
    }

    last_resize = (new Date()).getTime();
    resize_scheduled = false;
};

var onResize = function() {
    if (!resize_scheduled){
        resize_scheduled = true;
        setTimeout(makeColumnsSameHeight,
            // if waited more than 500ms execute now, otherwise wait till waited 500ms
            Math.max(0,  last_resize + 500 - (new Date()).getTime()));
    }
};


$(document).ready(function() {
    $(window).on('resize', onResize);
    $(window).on('load', makeColumnsSameHeight);
    makeColumnsSameHeight();

    makeExternalLinksExternal();
    focusFirstInputField();
    makeSectionClickable();
});


}(this));

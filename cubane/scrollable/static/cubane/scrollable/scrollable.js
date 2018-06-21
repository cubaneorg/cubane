(function (globals){
"use strict";


/*
 * Static
 */
var SNAP_WINDOW = 0.2;
var UPDATE_DELAY_MSEC = 50;


/*
 * State
 */
var timeout = undefined;
var handleScroll = false;
var touchend = true;


/*
 * Return the context for the given scrollable, which contains a set of
 * meta data about the scrollable, some of which is updated whenever the
 * scrollable resized.
 */
function _getContext(scrollable) {
    var container = scrollable.find('> .scrollable-container');
    var x = scrollable.hasClass('scrollable-x');

    // detect iOS
    var iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    if (iOS) scrollable.addClass('without-scrollbar');

    var context = {
        scrollable: scrollable,
        container: container,
        indicators: scrollable.find('.scrollable-indicators'),
        x: x,
        snap: scrollable.hasClass('scrollable-snap')
    };

    return _updateContext(context);
}


/*
 * Update the context with information that might have changed due to resizing
 * of the container, such as inner window size, max offset etc.
 */
function _updateContext(context) {
    // gutter
    context.gutter = parseInt(context.scrollable.attr('data-gutter'))
    if (isNaN(context.gutter)) context.gutter = 0;

    context.windowSize = context.x ? context.container.width() : context.container.height();
    context.innerSize = _getInnerSize(context.x, context.container);
    context.maxOffset = Math.max(0, context.innerSize - context.windowSize);
    context.pages = Math.ceil(context.innerSize / (context.windowSize + context.gutter));
    context.lastPageSize = context.innerSize - ( (context.windowSize + context.gutter) * (context.pages - 1) );

    return context;
}


/*
 * Update the relative position of the scroll handle to reflect the current
 * scroll position relative to the total amount of scrollable content.
 */
function _updateHandlePos(context, handle, pos) {
    handle.css('left', pos);
}


/*
 * Update the size of the scroll handle to refelect the amount of scrollable
 * content.
 */
function _updateHandleSize(context, handle, size) {
    if (context.x) {
        handle.width(size);
    } else {
        handle.height(size);
    }
}


/*
 * Update class annotation for 'can-scroll', which (when present) indicates
 * that the scrollable can scroll (at all).
 */
function _updateCanScroll(context) {
    if (context.innerSize > context.windowSize) {
        context.scrollable.addClass('can-scroll');
    } else {
        context.scrollable.removeClass('can-scroll');
    }

    // on touch devices, never show the scrollbar
    if (_isTouchDevice()) {
        context.scrollable.find('> .scrollbar').hide();
    }
}


/*
 * Update the button state for the given button and discabled state.
 */
function _updateButtonState(button, disabled) {
    if (disabled) {
        button.addClass('disabled');
        button.attr('disabled', '');
    } else {
        button.removeClass('disabled');
        button.removeAttr('disabled');
    }
}


/*
 * Update button state for left/right buttons.
 */
function _updateButtons(context) {
    var offset = _getOffset(context);

    _updateButtonState(context.scrollable.find('.scroll-btn-left'), offset <= 0);
    _updateButtonState(context.scrollable.find('.scroll-btn-right'), offset >= context.innerSize - context.windowSize);
}


/*
 * Return the inner size of the scrollable container, which contains all
 * items.
 */
function _getInnerSize(x, container) {
    var size = 0;

    container.find('> *').each(function() {
        size += x ? $(this).outerWidth(true) : $(this).outerHeight(true);
    });

    return size;
}


/*
 * Return the current scroll offset position.
 */
function _getOffset(context) {
    return context.x ? context.container.scrollLeft() : context.container.scrollTop()
}


/*
 * Return the current page index.
 */
function _getCurrentPage(context) {
    var offset = _getOffset(context);
    var windowSize = context.windowSize + context.gutter;

    var page = Math.round((offset) / windowSize);

    // last page, which might be a fraction of a page
    var lastPageOffset = (windowSize * (context.pages - 2)) + (0.5 * context.lastPageSize);
    if ( offset > lastPageOffset ) {
        page = context.pages - 1;
    }

    return page;
}


/*
 * Set or animate the scroll offset to the given offset.
 */
function _setOffset(context, offset, animate, complete) {
    if (animate === undefined) animate = true;
    if (complete === undefined) complete = function() {};

    if (offset < 0) offset = 0;
    if (offset > context.maxOffset) offset = context.maxOffset;

    // does the offset position actually change?
    if (_getOffset(context) === offset) animate = false;

    // stop previous animation, otherwise we will queue up
    // too many animations when clicking violantly...
    context.container.stop();

    if (animate) {
        if (context.x) {
            context.container.animate({
                scrollLeft: offset
            }, 300, 'swing', complete);
        } else {
            context.container.animate({
                scrollTop: offset
            }, 300, 'swing', complete);
        }
    } else {
        if (context.x) {
            context.container.scrollLeft(offset);
        } else {
            context.container.scrollTop(offset);
        }

        complete();
    }
}


/*
 * Update the internal state of the scrollable control after the offset
 * position changed, such as button states, scrollbar and page indicators.
 */
function _update(context, complete) {
    if (complete === undefined) complete = function() {};

    function _updateState() {
        // calculate handle pos and size
        var scrollbar = context.scrollable.find('> .scrollbar');
        var handle = scrollbar.find('> .scrollbar-handle');
        var scrollbarSize = context.x ? scrollbar.width() : scrollbar.height();
        var scale = context.windowSize / context.innerSize;
        var handleSize = context.windowSize * scale;
        var handlePos = _getOffset(context) * scale;

        _updateHandlePos(context, handle, handlePos);
        _updateHandleSize(context, handle, handleSize);
        _updateCanScroll(context);
        _updateButtons(context);
        _updateCurrentIndicator(context);
    }

    if (context.snap) {
        _snapToPage(context, true, function() {
            _updateState();
            complete();
        });
    } else {
        _updateState();
        complete();
    }
}


/*
 * Snap to current page, since the offset may be off as a concequence of
 * resizing the container.
 */
function _snapToPage(context, animate, complete) {
    var page = _getCurrentPage(context);
    _scrollToPage(context, page, animate, complete);
}


/*
 * Generate a list of indicators, one for each page. The number of pages
 * might have changed as a consequence of resizing the container.
 */
function _updateIndicators(context) {
    if (context.indicators.length > 0 && context.pages > 1) {
        context.indicators.empty();

        var page = _getCurrentPage(context);
        for (var i = 0; i < context.pages; i++) {
            var pageDisplay = (i + 1).toString();
            context.indicators.append('<button class="scrollable-indicator' + (page == i ? ' active' : '') + '" data-page="' + i.toString() + '" title="Go to page ' + pageDisplay + '">Page ' + pageDisplay + '</button>');
        }
    }
}


/*
 * Apply the active state to the current page indicator.
 */
function _updateCurrentIndicator(context) {
    if (context.indicators.length > 0 && context.pages > 1) {
        var page = _getCurrentPage(context);
        context.indicators.find('> .scrollable-indicator.active').removeClass('active');
        context.indicators.find('.scrollable-indicator').eq(page).addClass('active');
    }
}


/*
 * Scroll by given page delta.
 */
function _scrollByPage(context, deltaPages, animate) {
    var page = _getCurrentPage(context);
    _scrollToPage(context, page + deltaPages, animate);
}


/*
 * Scroll to the given page.
 */
function _scrollToPage(context, page, animate, complete) {
    var windowSize = context.windowSize + context.gutter;
    _setOffset(context, windowSize * page, animate, complete);
}


/*
 * Scroll one page to the left (previous page).
 */
function _scrollLeft(context) {
    _scrollByPage(context, -1);
}


/*
 * Scroll one page to the right (next page).
 */
function _scrollRight(context) {
    _scrollByPage(context, 1);
}


/*
 * Return true, if this is a touch device.
 */
function _isTouchDevice() {
    return 'ontouchstart' in window;
}


/*
 * Clear update timeout.
 */
function _clearTimeout() {
    if (timeout) {
        clearTimeout(timeout);
        timeout = undefined;
    }
}


/*
 * Record initial offset before scrolling started in order to identify
 * the direction of scrolling.
 */
function _recordInitialOffset(context) {
    // record initial scroll start position
    if (context.initialOffset === undefined) {
        context.initialOffset = _getOffset(context);
    }
}


/*
 * Schedule update of the internal state of the scrollable.
 */
function _scheduleUpdate(context) {
    timeout = setTimeout(function() {
        handleScroll = true;
        _update(context, function() {
            handleScroll = false;
            context.initialOffset = undefined;
        });
    }, UPDATE_DELAY_MSEC);
}


/*
 * Create a new scrollable control for the given scrollable container.
 */
function _createScrollable(scrollable) {
    var context = _getContext(scrollable);

    // resize
    $(window).on('resize', function() {
        _updateContext(context, scrollable);
        _snapToPage(context, false);
        _updateIndicators(context);
        _update(context);
    });

    // left/right
    scrollable.find('.scroll-btn-left').on('click', function() {
        _scrollLeft(context);
    });
    scrollable.find('.scroll-btn-right').on('click', function() {
        _scrollRight(context);
    });

    // indicator
    context.indicators.on('click', function(event) {
        var indicator = $(event.target).closest('.scrollable-indicator');
        if (indicator.length > 0) {
            var page = parseInt(indicator.attr('data-page'));
            _scrollToPage(context, page);
        }
    });

    // handle scroll event (throttled)
    if (_isTouchDevice()) {
        context.container.on('touchstart', function() {
            _clearTimeout();
            _recordInitialOffset(context);
            touchend = false;
        });

        context.container.on('touchend', function() {
            touchend = true;
            _scheduleUpdate(context);
        });
    }
    context.container.on('scroll', function() {
        // already handled?
        if (handleScroll) {
            return;
        }

        _recordInitialOffset(context);
        _clearTimeout();

        // do not schedule unless we see a touchend on touch devices
        if (touchend) {
            _scheduleUpdate(context);
        }
    });

    // initial state
    _updateIndicators(context);
    _update(context);
}


/*
 * On document ready, make each scrollable container a scrollable control.
 */
$(document).ready(function() {
    $('.scrollable').each(function() {
        _createScrollable($(this));
    });
});


}(this));
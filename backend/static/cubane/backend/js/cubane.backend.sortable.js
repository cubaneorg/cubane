(function (globals){
"use strict";


cubane.namespace('cubane.backend');


/*
 * const
 */
const AUTO_SCROLL_MSEC  = 16;
const AUTO_SCROLL_SPEED = 0.5;
const AUTOSCROLL_TOP    = -1;
const AUTOSCROLL_BOTTOM = 1;


/*
 * Operational data
 */
var autoScrollTimer = undefined;
var autoScrollEdge = undefined;
var autoScrollForce = undefined;
var placeholderX = undefined;
var placeholderY = undefined;


/*
 * Make a list of items sortable
 */
function sortable(itemsSelector, handleSelector, onChanged, placeholderClass, enabled) {
    if (enabled === undefined) enabled = true;
    _setupDraggable.call(this, itemsSelector, handleSelector, onChanged, placeholderClass, enabled);
}


/*
 * Setup basic drag capabilities with placeholder for sorting items.
 */
function _setupDraggable(itemsSelector, handleSelector, onChanged, placeholderClass, enabled) {
    var selection;
    var offset;
    var placeholder;
    var spacer;
    var seq;
    var grid = false;
    var originalX = undefined;
    var container = undefined;

    var interactObject = interact(itemsSelector).draggable({
        onstart: function(e) {
            if (!enabled) return;

            // collect sources (selected)
            selection = _getSelection($(e.target), itemsSelector);
            grid = _isGrid(selection);
            offset = _getHandleOffset(selection, e.pageX, e.pageY, handleSelector);
            placeholder = _createPlaceholder(selection, placeholderClass);
            spacer = _createSpacer(selection, grid);
            seq = _getSeqOfElement(selection);
            originalX = e.pageX;
            container = _getScrollableContainer(itemsSelector);

            _indicateSortingInProgress(selection);
            _movePlaceholder(placeholder, e.pageX, e.pageY, offset, grid, originalX);
        },

        onmove: function(e) {
            if (!enabled) return;

            placeholderX = e.pageX;
            placeholderY = e.pageY;

            _movePlaceholder(placeholder, e.pageX, e.pageY, offset, grid, originalX);
            _autoScroll(container, placeholder, spacer, offset, grid, originalX);

            // get new spacer position and move spacer
            var pos = _getSpacerPosition(selection, placeholder, grid);
            if (pos) {
                if (pos.dir == 'before') {
                    spacer.insertBefore(pos.el);
                } else {
                    spacer.insertAfter(pos.el);
                }
            }
        },

        onend: function(e) {
            if (!enabled) return;

            _disableAutoScroll(spacer);
            _indicateSortingStopped(selection);
            _destroyPlaceholder(placeholder);
            _replaceSpacer(spacer, selection);

            // trigger onChanged if seq indeed changed...
            if (onChanged) {
                var newSeq = _getSeqOfElement(selection);
                if (seq != newSeq) {
                    onChanged();
                }
            }

            spacer = placeholder = offset = container = undefined;
        },
        manualStart: 'ontouchstart' in window
    });

    if (handleSelector) {
        interactObject.allowFrom(handleSelector);
    }

    if ('ontouchstart' in window) {
        interact(itemsSelector).on('hold', function (event) {
            var interaction = event.interaction;

            if (!interaction.interacting()) {
                interaction.start(
                    { name: 'drag' },
                    event.interactable,
                    event.currentTarget
                );
            }
        });
    }
}


/*
 * Return the offet from the top/left corner of the selected element
 * and its clicked sorting handle.
 */
function _getHandleOffset(element, x, y) {
    var rect = element.get(0).getBoundingClientRect();
    var scrollTop = $(window).scrollTop();

    return {
        x: x - rect.left,
        y: y - rect.top - scrollTop
    };
}


/*
 * Return the scrollable container of the given sortable items.
 */
function _getScrollableContainer(itemsSelector) {
    var e = $(itemsSelector).eq(0).parent();
    while (e.length > 0 && e.get(0) !== document) {
        if (e.css('overflow-y') === 'scroll') {
            return e;
        }
        e = e.parent();
    }

    return $('body');
}


/*
 * Return list of selected items based on the given element that was attempted
 * to be dragged.
 */
function _getSelection(element, itemsSelector) {
    return element.closest(itemsSelector);
}


/*
 * Return true, if elements are aligned within a grid and NOT vertically.
 */
function _isGrid(selection) {
    return selection.css('float') == 'left';
}


/*
 * Indicate that a sorting operation for the given selection of elements
 * is in progress.
 */
function _indicateSortingInProgress(selection) {
    selection.addClass('sorting-in-progress');
}


/*
 * Indicate that a sorting operation for the given selection of elements
 * has stopped.
 */
function _indicateSortingStopped(selection) {
    selection.removeClass('sorting-in-progress');
}


/*
 * Create placeholder
 */
function _createPlaceholder(element, placeholderClass) {
    // measure actual size
    var w, h;
    if ($.browser.mozilla) {
        w = element.width();
        h = element.height() + parseFloat(element.css('padding-bottom').replace('px', ''));
    } else {
        w = element.outerWidth();
        h = element.outerHeight();
    }

    // clone element and style and apply width and height
    var placeholder = element.clone();
    placeholder.removeAttr('id');
    placeholder.addClass('sortable-placeholder');
    placeholder.width(w);
    placeholder.height(h);

    // custom placeholder class?
    if (placeholderClass) {
        placeholder.addClass(placeholderClass);
    }

    $('body').append(placeholder);
    return placeholder;
}


/*
 * Move placeholder to given position.
 */
function _movePlaceholder(placeholder, x, y, offset, grid, originalX) {
    // lock x-achis if not grid
    if (!grid) {
        x = originalX;
    }

    // offset adjustment
    x -= offset.x;
    y -= offset.y;

    // move placeholder to start position
    var target = placeholder.get(0);
    target.style.webkitTransform =
    target.style.transform =
      'translate(' + x + 'px, ' + y + 'px)';
}


/*
 * Destroy placeholder
 */
function _destroyPlaceholder(placeholder) {
    if (placeholder) {
        placeholder.remove();
    }
}


/*
 * Automatically scroll vertically as we approach the top/bottom edges
 * of the given container.
 */
function _autoScroll(container, placeholder, spacer, offset, grid, originalX) {
    var containerRect = container.get(0).getBoundingClientRect();
    var placeholderRect = placeholder.get(0).getBoundingClientRect();
    var scrollTop = container.get(0) === document.body ? $(window).scrollTop() : 0;
    var containerTop = containerRect.top + scrollTop;
    var containerBottom = containerRect.bottom + scrollTop;

    // test if we are intersection top/bottom edge
    if (placeholderRect.top < containerTop) {
        _enableAutoScroll(container, placeholder, spacer, AUTOSCROLL_TOP, containerTop - placeholderRect.top, offset, grid, originalX);
    } else if (placeholderRect.bottom > containerBottom) {
        _enableAutoScroll(container, placeholder, spacer, AUTOSCROLL_BOTTOM, placeholderRect.bottom - containerBottom, offset, grid, originalX);
    } else {
        _disableAutoScroll(spacer);
    }
}


/*
 * Enable automatic scrolling for the given container and edge.
 */
function _enableAutoScroll(container, placeholder, spacer, edge, force, offset, grid, originalX) {
    // update scroll edge and speed
    autoScrollEdge = edge;
    autoScrollForce = force;

    // enable background interval for scrolling
    if (!autoScrollTimer) {
        autoScrollTimer = setInterval(function() {
            // update scroll position
            var delta = autoScrollForce * autoScrollEdge * AUTO_SCROLL_SPEED;

            // update placeholder (unless we are scrolling body element)
            if (container.get(0) === document.body) {
                // determine max. scroll position
                var limit = Math.max(
                    document.body.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.clientHeight,
                    document.documentElement.scrollHeight,
                    document.documentElement.offsetHeight
                ) - window.innerHeight;
                var rect = placeholder.get(0).getBoundingClientRect();
                if (rect.bottom > window.innerHeight) {
                    limit -= rect.bottom - window.innerHeight;
                }

                // crop
                var y = $(window).scrollTop();
                if (y + delta < 0) delta = -y;
                if (y + delta > limit) delta = 0;

                // scroll
                y = Math.floor(y + delta);
                $('html, body').scrollTop(y);

                // correct last known placeholder position
                placeholderY = Math.floor(placeholderY + delta);

                // correct placeholder position
                _movePlaceholder(placeholder, placeholderX, placeholderY, offset, grid, originalX);
            } else {
                container.scrollTop(container.scrollTop() + delta);
            }
        }, AUTO_SCROLL_MSEC);
    }

    // while auto-scrolling is active, hide the spacer
    spacer.hide();
}


/*
 * Disable automatic scrolling.
 */
function _disableAutoScroll(spacer) {
    if (autoScrollTimer) {
        clearInterval(autoScrollTimer);
        autoScrollTimer = undefined;
        autoScrollEdge = undefined;
        autoScrollForce = undefined;
    }

    // show spacer
    spacer.show();
}


/*
 * Create spacer from given element.
 */
function _createSpacer(element, grid) {
    // create new element
    var spacer = $('<div></div>');
    spacer.attr('class', element.attr('class'));
    spacer.attr('style', element.attr('style'));
    spacer.addClass('sortable-spacer');

    if (grid) {
        spacer.css('float', 'left');
    }

    spacer.insertBefore(element);
    return spacer;
}


/*
 * Destroy spacer element.
 */
function _replaceSpacer(spacer, selection) {
    if (spacer) {
        // insert selection before spacer
        selection.insertBefore(spacer);

        // destroy spacer
        spacer.remove();
    }
}


/*
 * Return the element to which the dragged item is aliogned either
 * before or after.
 */
function _getSpacerPosition(element, placeholder, grid) {
    function _getCenterPos(el) {
        var rect = el.getBoundingClientRect();
        var w = rect.right - rect.left;
        var h = rect.bottom - rect.top;

        return {
            left: rect.left + (w / 2),
            top: rect.top + (h / 2),
            width: w,
            height: h
        };
    }

    var p0 = _getCenterPos(placeholder.get(0));
    var toleranceX = p0.width / 2;
    var toleranceY = p0.height / 2;
    var items = element.parent().find('> *:not(.sorting-in-progress):not(.sortable-spacer)');
    for (var i = 0; i < items.length; i++) {
        var p1 = _getCenterPos(items.get(i));
        var dx = p0.left - p1.left
        var dy = p0.top - p1.top;
        var mx = Math.abs(dx) < toleranceX;
        var my = Math.abs(dy) < toleranceY;

        if (my && (!grid || mx)) {
            var d = grid ? dx : dy;
            return {
                el: items.eq(i),
                dir: d > 0 ? 'after' : 'before'
            };
        }
    }

    return undefined;
}


/*
 * Return the index position of the given element.
 */
function _getSeqOfElement(selection) {
    return selection.parent().find('> *:not(.sortable-spacer)').index(selection);
}


/*
 * Export
 */
cubane.backend.sortable = sortable;


})(this);
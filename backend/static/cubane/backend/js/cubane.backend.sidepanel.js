(function (globals){
"use strict";


cubane.namespace('cubane.backend');


/*
 * Constructor
 */
function ResizableSidePanel(panel, id) {
    this._panel = $(panel);
    this._id = this._panel.attr('data-resize-panel-id');
    this._handle = this._panel.find('.cubane-listing-resize-panel-handle');

    var listing = this._panel.closest('.cubane-listing');
    this._header = listing.find('.cubane-listing-header');
    this._content = listing.find('.cubane-listing-content-frame');
    this._isReverse = this._handle.hasClass('left');

    this._bound = {
        onMouseDown: _onMouseDown.bind(this),
        onMouseMove: _onMouseMove.bind(this),
        onMouseUp: _onMouseUp.bind(this)
    };

    _bindEvents.call(this);
}


/*
 * Dispose
 */
ResizableSidePanel.prototype.dispose = function dispose() {
    this._handle.off('mousedown touchstart', this._bound.onMouseDown);
    this._handle = undefined;
    this._panel = undefined;
    this._header = undefined;
    this._content = undefined;
    this._offset = undefined;
};


/*
 * Bind events
 */
function _bindEvents() {
    this._handle.on('mousedown touchstart', this._bound.onMouseDown);
}


/*
 * Return additional delta offset between window edge and start of panel.
 */
function _getDeltaOffset() {
    var rect = this._panel.get(0).getBoundingClientRect();
    if (this._handle.hasClass('left')) {
        return window.innerWidth - rect.right;
    } else {
        return rect.left;
    }
}


/*
 * Mouse down
 */
function _onMouseDown(e) {
    e.preventDefault();
    var x = e.clientX || e.originalEvent.pageX;

    // calculate offset to handle
    var delta = _getDeltaOffset.call(this);

    // left-edge handle differs in offset calculation
    if (this._handle.hasClass('left')) {
        this._offset = (this._handle.offset().left + 5) - (x + delta);
        this._offset = -this._offset;
    } else {
        this._offset = (this._handle.offset().left + 10) - (x + delta);
    }

    // bind move and mouse up
    $(document).on('mousemove touchmove', this._bound.onMouseMove);
    $(document).on('mouseup touchend', this._bound.onMouseUp);
}


/*
 * Mouse move
 */
function _onMouseMove(e) {
    e.preventDefault();
    var x = e.clientX || e.originalEvent.pageX;
    var max = window.innerWidth > 767 ? window.innerWidth / 2 : window.innerWidth - 50;

    if (this._isReverse) {
        var width = (window.innerWidth - x) - this._offset;
    } else {
        var width = x + this._offset;
    }

    if (width < 160) {
        width = 160;
    } else if (width > max) {
        width = max;
    }

    this._panel.css({width: width + 'px'});

    if (this._isReverse) {
        this._header.css({right: width + 'px'});
        this._content.css({right: width + 'px'});
    } else {
        this._header.css({left: width + 'px'});
        this._content.css({left: width + 'px'});
    }

    this._width = width;
}


/*
 * Mouse up
 */
function _onMouseUp(e) {
    e.preventDefault();

    if (this._panel.closest('.related-listing').length == 0) {
        $.post('side-panel-resize/', {width: this._width, resize_panel_id: this._id}, function() {
        }, 'JSON');
    }

    $(document).off('mousemove touchmove', this._bound.onMouseMove);
    $(document).off('mouseup touchend', this._bound.onMouseUp);
}


/*
 * Export
 */
cubane.backend.ResizableSidePanel = ResizableSidePanel;


/*
 * Create resizable folder side panel.
 */
$(document).ready(function () {
    var resizePanels = $('.cubane-listing-resize-panel');
    if (resizePanels.length > 0) {
        resizePanels.each(function(index) {
            var resizePanel = new cubane.backend.ResizableSidePanel(this, index);

            $(window).unload(function () {
                resizePanel.dispose();
                resizePanel = undefined;
            });
        });
    }
});


}(this));

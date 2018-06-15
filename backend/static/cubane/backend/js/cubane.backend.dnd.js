(function (globals){
"use strict";


cubane.namespace('cubane.backend');


/*
 * Constructor
 */
function DragAndDropController() {
    this._placeholder = undefined;
    this._timeout = undefined;

    _createPlaceholder.call(this);
    _setupDraggable.call(this);
    _setupDropTargets.call(this);
}


/*
 * Static
 */
DragAndDropController.OPEN_TREE_NODE_TIMEOUT_MSEC = 1000;


/*
 * Dispose
 */
DragAndDropController.prototype.dispose = function dispose() {
    _destroyPlaceholder.call(this);
    _cancelOpenTreeNodeTimeout.call(this);
};


/*
 * Create placeholder
 */
function _createPlaceholder() {
    // create drag and drop placeholder
    this._placeholder = $('<div class="dnd-placeholder"><div class="dnd-placeholder-title"></div><div class="dnd-placeholder-count"></div></div>');
    $('body').append(this._placeholder);
}


/*
 * Destroy placeholder
 */
function _destroyPlaceholder() {
    if (this._placdeholder) {
        this._placeholder.remove();
        this._placeholder = undefined;
    }
}


/*
 * Set the content of the placeholder based on the given list of selected elements.
 */
function _setPlaceholderContent(selection) {
    this._placeholder.find('> .dnd-placeholder-title').text(selection.text());
    this._placeholder.find('> .dnd-placeholder-count').text(selection.length);
    if (selection.length > 1) {
        this._placeholder.addClass('multiple');
    } else {
        this._placeholder.removeClass('multiple');
    }
}


/*
 * Move placeholder to given position.
 */
function _movePlaceholder(x, y) {
    // move placeholder to start position
    var target = this._placeholder.get(0);
    target.style.webkitTransform =
    target.style.transform =
      'translate(' + x + 'px, ' + y + 'px)';
}


/*
 * Make placeholder visible.
 */
function _showPlaceholder() {
    this._placeholder.addClass('active');
}


/*
 * Make placeholder invisible.
 */
function _hidePlaceholder() {
    this._placeholder.removeClass('active');
}


/*
 * Return list of selected items based on the given element that was attempted
 * to be dragged.
 */
function _getSelection(element) {
    if (element.hasClass('selected')) {
        return element.parent().find('> .selected');
    } else if (element.parent().hasClass('tree-node') && element.parent().hasClass('active')) {
        return element.closest('.tree').find('.tree-node.active');
    } else {
        return element;
    }
}


/*
 * Indicate that a drag and drop operation for the given selection of elements
 * is in progress.
 */
function _indicateDragInProgress(selection) {
    selection.addClass('drag-in-progress');
}


/*
 * Indicate that a drag and drop operation for the given selection of elements
 * has stopped.
 */
function _indicateDragStopped(selection) {
    selection.removeClass('drag-in-progress');
}


/*
 * Setup basic drag capabilities with placeholder
 */
function _setupDraggable() {
    var isDragAndDrop = false;

    interact('.draggable').draggable({
        onstart: function(e) {
            // abort interaction if we are in edit mode
            if ($(e.target).closest('.cubane-listing').hasClass('edit-mode')) {
                isDragAndDrop = false;
                return;
            }

            // abort interaction if we started the move from ui-sortable-helper
            var targets = e.interaction.downEvent.path;
            if (!targets) targets = e.interaction.downTargets;
            if (targets && targets.length > 0) {
                if ($(targets[0]).hasClass('ui-sortable-handle')) {
                    isDragAndDrop = false;
                    return;
                }
            }

            isDragAndDrop = true;

            // collect sources (selected)
            var selection = _getSelection.call(this, $(e.target));
            _indicateDragInProgress.call(this, selection);
            _setPlaceholderContent.call(this, selection);
            _movePlaceholder.call(this, e.pageX, e.pageY);
            _showPlaceholder.call(this);
        }.bind(this),

        onmove: function(e) {
            if (isDragAndDrop) {
                _movePlaceholder.call(this, e.pageX, e.pageY);
            }
        }.bind(this),

        onend: function (e) {
            var selection = _getSelection.call(this, $(e.target));
            _indicateDragStopped.call(this, selection);
            _hidePlaceholder.call(this);
        }.bind(this),
        manualStart: 'ontouchstart' in window
    }).ignoreFrom('a, input, select, button, label');

    if ('ontouchstart' in window) {
        interact('.draggable').on('hold', function (event) {
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
 * Activate the given drop zone, which means that the drop zone is available
 * for dropping, but no element has been dropped yet.
 */
function _activateDropZone(dropzone) {
    dropzone.addClass('drop-active');
}


/*
 * Deactivate the given drop zone, which means that the drop zone is no longer
 * available for dropping.
 */
function _deactivateDropZone(dropzone) {
    dropzone.addClass('drop-active');
}


/*
 * Indicate for the given drop zone that a drop is possible.
 */
function _indicateDropPossible(dropzone) {
    dropzone.addClass('drop-target');
}


/*
 * Indicate for the given drop zone that a drop is not possible or no longer
 * possible.
 */
function _indicateDropInpossible(dropzone) {
    dropzone.removeClass('drop-target');
}


/*
 * Indicate that the placeholder can be dropped.
 */
function _placeholderCanDrop() {
    this._placeholder.addClass('can-drop');
}


/*
 * Indicate that the placeholder can not be dropped.
 */
function _placeholderCannotDrop() {
    this._placeholder.removeClass('can-drop');
}


/*
 * When hovering over a tree node during a drag and drop operation,
 * open the corresponding tree node after a certain amount of time.
 */
function _openTreeNodeOnTimeout(element) {
    if (element.hasClass('tn-title')) {
        if (this._timeout) clearTimeout(this._timeout);
        this._timeout = setTimeout(function() {
            element.closest('.tree-node').addClass('open');
        }, DragAndDropController.OPEN_TREE_NODE_TIMEOUT_MSEC);
    }
}


/*
 * Cancel opening a tree node.
 */
function _cancelOpenTreeNodeTimeout() {
    if (this._timeout) {
        clearTimeout(this._timeout);
        this._timeout = undefined;
    }
}


/*
 * Setup drop targets for draggable elements.
 */
function _setupDropTargets() {
    interact('.dropable').dropzone({
        accept: '.draggable',

        // listen for drop related events:
        ondropactivate: function (event) {
            // add active dropzone feedback
            _activateDropZone.call(this, $(event.target));
        }.bind(this),

        ondragenter: function (event) {
            var dropzone = $(event.target);
            _indicateDropPossible.call(this, dropzone);
            _placeholderCanDrop.call(this)
            _openTreeNodeOnTimeout.call(this, dropzone);
        }.bind(this),

        ondragleave: function (event) {
            var dropzone = $(event.target);
            _indicateDropInpossible.call(this, dropzone);
            _placeholderCannotDrop.call(this);
            _cancelOpenTreeNodeTimeout.call(this);
        }.bind(this),

        ondrop: function (event) {
            var dropzone = $(event.target);
            var selection = _getSelection.call(this, $(event.relatedTarget));

            if (dropzone.hasClass('tn-title')) {
                dropzone = dropzone.closest('.tree-node');
            }

            if (selection.hasClass('tn-title')) {
                selection = selection.closest('.tree-node');
            }

            dropzone.trigger('cubane-drop', [selection]);
        }.bind(this),

        ondropdeactivate: function (event) {
            var dropzone = $(event.target);
            _indicateDropInpossible.call(this, dropzone);
            _deactivateDropZone.call(this, dropzone);
            _placeholderCannotDrop.call(this);
            _cancelOpenTreeNodeTimeout.call(this);
        }.bind(this)
    }).dropChecker(function (pointer, dropped, interactable, dropzone, draggable, element) {
        if (!dropped) return false;

        var dropzone = $(dropzone);
        var element = $(element);

        if (element.hasClass('tn-title') && dropzone.hasClass('tn-title')) {
            var src = element.closest('.tree').find('.tree-node.active');
            var dst = dropzone.closest('.tree-node');

            for (var i = 0; i < src.length; i++) {
                // any source node cannot be the destination node
                if (src.get(i) === dst.get(0)) {
                    return false;
                }

                // dst cannot be a sub-node of any src node
                if ($.contains(src.get(i), dst.get(0))) {
                    return false;
                }

                // any src node cannot already be a child of dst
                if (src.eq(i).parents('.tree-node').get(0) === dst.get(0)) {
                    return false;
                }
            }
        }

        return true;
    });
}


/*
 * Export
 */
cubane.backend.DragAndDropController = DragAndDropController;


/*
 * Create new backend drag and drop controller when DOM is ready and dispose
 * it on unload.
 */
$(document).ready(function () {
    var dndController = new cubane.backend.DragAndDropController();

    $(window).unload(function () {
        dndController.dispose();
        dndController = null;
    });
});


}(this));

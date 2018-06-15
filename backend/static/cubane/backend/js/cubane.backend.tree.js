(function (globals){
"use strict";


cubane.namespace('cubane.backend');


/*
 * Constructor
 */
function TreeController() {
    this._bound = {
        onCaretClicked: this.onCaretClicked.bind(this),
        onTitleClicked: this.onTitleClicked.bind(this),
        onTitleDblClicked: this.onTitleDblClicked.bind(this),
        onDrop: this.onDrop.bind(this),
        onNew: this.onNew.bind(this),
        onEdit: this.onEdit.bind(this),
        onRefresh: this.onRefresh.bind(this)
    };

    _bindEvents.call(this);
    _initialState.call(this);
}


/*
 * Caret clicked -> open/close sub-tree.
 */
TreeController.prototype.onCaretClicked = function onCaretClicked(e) {
    var node = $(e.target).closest('.tree-node');
    this.toggle(node);
    this.updateServerNodeState(node);
};


/*
 * Title clicked -> Select tree node
 */
TreeController.prototype.onTitleClicked = function onTitleClicked(e) {
    // ignore if we clicked on the caret
    if ($(e.target).closest('.tn-caret').length === 0) {
        var node = $(e.target).closest('.tree-node');

        // open node if the node is closed
        if (this.hasChildren(node) && !this.isNodeOpen(node)) {
            this.open(node);
            this.updateServerNodeState(node);
        }

        if (e.shiftKey) {
            var root = this.getRoot(node);
            var firstNode = this.getFirstSelectedItem(root)
            this.selectRange(firstNode, node);
        } else if (e.metaKey || e.ctrlKey) {
            this.toggleSelect(node);
        } else {
            this.select(node);
        }
    }
};


/*
 * Title double-clicked -> Edit tree node
 */
TreeController.prototype.onTitleDblClicked = function onTitleDblClicked(e) {
    // ignore if we clicked on the caret
    if ($(e.target).closest('.tn-caret').length !== 0) {
        return;
    }

    var node = $(e.target).closest('.tree-node');
    var pk = this.getId(node);

    // when dbl-clicking, also select the new node
    this.onTitleClicked.call(this, e);

    // ignore if we clicked on root folder
    if (pk === -1) {
        return;
    }

    var container = node.closest('.cubane-listing-folders-tree');
    var modelName = container.attr('data-model-name')
    var url = container.attr('data-edit-url');

    url = cubane.urls.combineUrlArg(url, 'browse', true);
    url = cubane.urls.combineUrlArg(url, 'edit', true);
    url = cubane.urls.combineUrlArg(url, 'pk', pk);

    cubane.dialog.iframe('Edit ' + modelName, url, {
        onOK: function(iframe) {
            $(iframe).contents().find('form.form-horizontal').submit();
            return true;
        }
    });
    $('.modal-iframe .confirm').removeClass('disabled');
};


/*
 * Items dropped -> tell server and refresh tree
 */
TreeController.prototype.onDrop = function onDrop(e, selection) {
    var target = $(e.target);

    if (selection.hasClass('tree-node')) {
        this.moveTo(selection, target);
    }
};


/*
 * Folder created -> refresh
 */
TreeController.prototype.onNew = function onNew(e) {
    var node = $(document).find('.tree-node').first();
    this.refresh(node);
};


/*
 * Folder edited -> refresh
 */
TreeController.prototype.onEdit = function onEdit(e) {
    var node = $(document).find('.tree-node').first();
    this.refresh(node);
};


/*
 * Refresh tree content
 */
TreeController.prototype.onRefresh = function onRefresh(e) {
    var node = $(document).find('.tree-node').first();
    this.refresh(node);
};


/*
 * Return true, if the given node is open; otherwise false.
 */
TreeController.prototype.isNodeOpen = function isNodeOpen(node) {
    return node.hasClass('open');
};


/*
 * Return true, if the given node has children.
 */
TreeController.prototype.hasChildren = function hasChildren(node) {
    return node.hasClass('with-children');
};


/*
 * Toggle given tree node
 */
TreeController.prototype.toggle = function toggle(node) {
    node.toggleClass('open');
};


/*
 * Open given tree node
 */
TreeController.prototype.open = function open(node) {
    node.addClass('open');
};


/*
 * Close given tree node
 */
TreeController.prototype.close = function close(node) {
    node.removeClass('open');
};


/*
 * Open all parents of the given node except the given node.
 */
TreeController.prototype.openParents = function openParents(node) {
    var parents = node.parents('.tree-node');
    for (var i = 0; i < parents.length; i++) {
        this.open(parents.eq(i));
    }
};


/*
 * Get root node of the given tree node.
 */
TreeController.prototype.getRoot = function getRoot(node) {
    var parents = node.parents('.tree-node');
    return parents.length > 0 ? parents.last() : node;
};


/*
 * Get the tree node identifier of the given node.
 */
TreeController.prototype.getId = function getId(node) {
    return node.data('id');
};


/*
 * Get the tree node identifiers for all given nodes.
 */
TreeController.prototype.getIds = function getIds(nodes) {
    var ids = [];
    for (var i = 0; i < nodes.length; i++) {
        ids.push(nodes.eq(i).data('id'));
    }
    return ids;
};


/*
 * Return a list of node identifiers for all selected nodes within the tree.
 */
TreeController.prototype.getSelectedIds = function getSelectedIds(root) {
    var selectedNodes = root.find('.tree-node.active');
    var ids = [];
    for (var i = 0; i < selectedNodes.length; i++) {
        ids.push(this.getId(selectedNodes.eq(i)));
    }
    if (root.hasClass('active')) ids.push(-1);
    return ids;
};


/*
 * Return the first tree node of the current selection.
 */
TreeController.prototype.getFirstSelectedItem = function getFirstSelectedItem(root) {
    return root.parent().find('.tree-node.active').first();
};


/*
 * Unselect all nodes
 */
TreeController.prototype.unselectAll = function unselectAll(root) {
    root.removeClass('active');
    root.find('.tree-node.active').removeClass('active');
};


/*
 * Select the given tree node and unselect every other node currently selected.
 */
TreeController.prototype.select = function select(node) {
    var root = this.getRoot(node);
    this.unselectAll(root);

    node.addClass('active');
    root.trigger('cubane-tree-node-selected', [this.getSelectedIds(root)]);
};


/*
 * Toggle the selection state for the given node by adding or removing the given
 * node from the current selection; unless the given node is the only remaining
 * node, in which case the node remains selected.
 */
TreeController.prototype.toggleSelect = function toggleSelect(node) {
    var root = this.getRoot(node);

    // cannot toggle last remaining node in selection
    if (!(node.hasClass('active') && root.parent().find('.tree-node.active').length === 1)) {
        node.toggleClass('active');

        // unselect root node if we have multiple nodes selected...
        if (root.hasClass('active') && root.parent().find('.tree-node.active').length >= 2) {
            root.removeClass('active');
        }

        root.trigger('cubane-tree-node-selected', [this.getSelectedIds(root)]);
    }
};


/*
 * Select all items between the given start node and end node.
 */
TreeController.prototype.selectRange = function selectRange(nodeStart, nodeEnd) {
    if ( nodeStart.length === 0 || nodeEnd.length === 0 ) return;

    // unselect all
    var root = this.getRoot(nodeStart);
    this.unselectAll(root);

    // figure out indecies
    var nodes = root.find('.tree-node');
    var start = nodes.index(nodeStart);
    var end = nodes.index(nodeEnd);
    if ( start > end ) {
        var tmp = start;
        start = end;
        end = tmp;
    }

    // select
    for ( var i = start; i <= end; i++ ) {
        nodes.eq(i).addClass('active');
    }
    root.trigger('cubane-tree-node-selected', [this.getSelectedIds(root)]);
};


/*
 * Update the entire tree from server
 */
TreeController.prototype.refresh = function refresh(node) {
    var container = node.closest('.cubane-listing-folders-tree');
    var url = container.attr('data-get-tree-url');
    var args = {
        f: 'html'
    }

    $.get(url, args, function(content) {
        this.updateTree(container, content);
    }.bind(this));
};


/*
 * Inform server about the state of the given node.
 */
TreeController.prototype.updateServerNodeState = function updateServerNodeState(node) {
    var container = node.closest('.cubane-listing-folders-tree');
    var url = container.attr('data-tree-node-state-url');
    var args = {
        id: this.getId(node),
        open: this.isNodeOpen(node)
    }

    $.post(url, args);
};


/*
 * Move given tree node to given dest tree node, so that the src node becomes
 * a child of the new parent node.
 */
TreeController.prototype.moveTo = function moveTo(selection, targetNode) {
    var container = selection.closest('.cubane-listing-folders-tree');
    var url = container.attr('data-move-tree-node-url');
    var args = {
        src: this.getIds(selection),
        dst: this.getId(targetNode),
        f: 'html'
    }

    $.post(url, args, function(content) {
        this.updateTree(container, content);
    }.bind(this));
};


/*
 * Update tree content.
 */
TreeController.prototype.updateTree = function updateTree(container, content) {
    container.html(content);
};


/*
 * Dispose
 */
TreeController.prototype.dispose = function dispose() {
    _unbindEvents.call(this);
};


/*
 * Bind events
 */
function _bindEvents() {
    // caret
    $(document).on(
        'click',
        '.tn-caret',
        this._bound.onCaretClicked
    );

    // title
    $(document).onClickOrDblClick(
        '.tn-title',
        this._bound.onTitleClicked,
        this._bound.onTitleDblClicked
    );

    // drop
    $(document).on(
        'cubane-drop',
        this._bound.onDrop
    );

    // new node
    $(window).on('cubane-listing-create', this._bound.onNew);

    // edit node
    $(window).on('cubane-listing-edit', this._bound.onEdit);

    // refresh
    $(window).on('cubane-tree-refresh', this._bound.onRefresh);
}


/*
 * Unbind events
 */
function _unbindEvents() {
    // caret
    $(document).off(
        'click',
        '.tn-caret',
        this._bound.onCaretClicked
    );

    // drop
    $(document).off(
        'cubane-drop',
        this._bound.onDrop
    );

    // new node
    $(window).off('cubane-listing-create', this._bound.onNew);

    // edit node
    $(window).off('cubane-listing-edit', this._bound.onEdit);

    // refresh
    $(window).off('cubane-tree-refresh', this._bound.onRefresh);
}


/*
 * Setup initial tree state.
 */
function _initialState() {
    // make sure that all intermediate tree nodes are open relative to every
    // selected node
    var activeNodes = $('.tree-node.active');
    for (var i = 0; i < activeNodes.length; i++) {
        this.openParents(activeNodes.eq(i));
    }
}


/*
 * Export
 */
cubane.backend.TreeController = TreeController;


/*
 * Create new backend tree controller when DOM is ready and dispose it on unload.
 */
$(document).ready(function () {
    var treeController = new cubane.backend.TreeController();

    $(window).unload(function () {
        treeController.dispose();
        treeController = null;
    });
});


}(this));

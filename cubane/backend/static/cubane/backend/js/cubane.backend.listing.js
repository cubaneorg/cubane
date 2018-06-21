(function (globals){
"use strict";


cubane.namespace('cubane.backend');


cubane.require('cubane.urls');
cubane.require('cubane.dialog');
cubane.require('cubane.urls');


/*
 * Listing Controller
 */
cubane.backend.ListingController = function () {
    this._bound = {
        // listing
        onPreSelect: $.proxy(this.onPreSelect, this),
        onToggleSelectAll: $.proxy(this.onToggleSelectAll, this),
        onItemClicked: $.proxy(this.onItemClicked, this),
        onItemDblClicked: $.proxy(this.onItemDblClicked, this),
        onCheckboxClicked: $.proxy(this.onCheckboxClicked, this),
        onEditClicked: $.proxy(this.onEditClicked, this),
        onActionClicked: $.proxy(this.onActionClicked, this),
        onShortcutActionClicked: $.proxy(this.onShortcutActionClicked, this),
        onDeleteEmptyClicked: $.proxy(this.onDeleteEmptyClicked, this),
        onDisableEnableClicked: $.proxy(this.onDisableEnableClicked, this),
        onUndoClicked: $.proxy(this.onUndoClicked, this),
        onSearchChanged: $.proxy(this.onSearchChanged, this),
        onColumnClicked: $.proxy(this.onColumnClicked, this),
        onOrderApplyClicked: $.proxy(this.onOrderApplyClicked, this),
        onFilterClicked: $.proxy(this.onFilterClicked, this),
        onFilterChanged: $.proxy(this.onFilterChanged, this),
        onFilterSubmit: $.proxy(this.onFilterSubmit, this),
        onFilterClose: $.proxy(this.onFilterClose, this),
        onFilterReset: $.proxy(this.onFilterReset, this),
        onPageClicked: $.proxy(this.onPageClicked, this),
        onViewClicked: $.proxy(this.onViewClicked, this),
        onTreeNodeSelected: $.proxy(this.onTreeNodeSelected, this),
        onDrop: $.proxy(this.onDrop, this),
        onSelectorItemClicked: $.proxy(this.onSelectorItemClicked, this),
        onContentScrolled: $.proxy(this.onContentScrolled, this),
        onViewObjClicked: $.proxy(this.onViewObjClicked, this),
        onItemEditChanged: $.proxy(this.onItemEditChanged, this),
        onItemEditStart: $.proxy(this.onItemEditStart, this),
        onItemEditEnd: $.proxy(this.onItemEditEnd, this),
        onItemEditSaveChanges: $.proxy(this.onItemEditSaveChanges, this),
        onItemEditDiscardChanges: $.proxy(this.onItemEditDiscardChanges, this),
        onListingRefresh: $.proxy(this.onListingRefresh, this),
        onListingResize: $.proxy(this.onListingResize, this)
    };

    $(document).on(
        'cubane-listing-pre-select',
        this._bound.onPreSelect
    );

    $(document).on(
        'change',
        '.cubane-listing [name="selectall"]',
        this._bound.onToggleSelectAll
    );

    // click and dbl-click
    $(document).onClickOrDblClick(
        '.cubane-listing .cubane-listing-item',
        this._bound.onItemClicked,
        this._bound.onItemDblClicked
    );

    $(document).on(
        'click',
        '.cubane-listing [name="select"]',
        this._bound.onCheckboxClicked
    );
    $(document).on(
        'click',
        '.cubane-listing-edit',
        this._bound.onEditClicked
    );
    $(document).on(
        'click',
        '.cubane-listing-action',
        this._bound.onActionClicked
    );
    $(document).on(
        'click',
        '.cubane-shortcut-action',
        this._bound.onShortcutActionClicked
    );
    $(document).on(
        'click',
        '.cubane-listing-delete-empty',
        this._bound.onDeleteEmptyClicked
    );
    $(document).on(
        'click',
        '.cubane-listing-item-disable-enable',
        this._bound.onDisableEnableClicked
    );
    $(document).on(
        'click',
        '.cubane-listing-undo',
        this._bound.onUndoClicked
    );
    $(document).on(
        'keyup',
        '.search-query',
        this._bound.onSearchChanged
    );
    $(document).on(
        'click',
        '.cubane-listing-filter-toggle',
        this._bound.onFilterClicked
    );
    $(document).on(
        'keyup change',
        '.cubane-listing-filter input, ' +
        '.cubane-listing-filter textarea, ' +
        '.cubane-listing-filter select',
        this._bound.onFilterChanged
    );
    $(document).on(
        'cubane-listing-item-edit-changed',
        '.cubane-listing-filter .cubane-collection-items',
        this._bound.onFilterChanged
    );
    $(document).on(
        'submit',
        '.cubane-listing-filter form',
        this._bound.onFilterSubmit
    );
    $(document).on(
        'click',
        '.cubane-listing-filter .ui-listing-filter-close',
        this._bound.onFilterClose
    );
    $(document).on(
        'click',
        '.ui-listing-filter-reset',
        this._bound.onFilterReset
    );
    $(document).on(
        'click',
        '.cubane-listing .pagination a',
        this._bound.onPageClicked
    );
    $(document).on(
        'click',
        '.cubane-listing-column.sortable',
        this._bound.onColumnClicked
    );
    $(document).on(
        'click',
        '.cubane-listing-seq-apply',
        this._bound.onOrderApplyClicked
    );
    $(document).on(
        'click',
        '.cubane-listing-view > .btn',
        this._bound.onViewClicked
    );
    $(document).on(
        'cubane-tree-node-selected',
        '.cubane-listing.with-folders',
        this._bound.onTreeNodeSelected
    );
    $(document).on(
        'cubane-drop',
        this._bound.onDrop
    );
    $(document).on(
        'click',
        '.cubane-selector-item',
        this._bound.onSelectorItemClicked
    );
    $('.cubane-listing-content').on(
        'scroll',
        this._bound.onContentScrolled
    );
    $(document).on(
        'click',
        '.cubane-listing-item-view-obj > a',
        this._bound.onViewObjClicked
    );
    $(document).on(
        'change keydown',
        '.cubane-listing-item.edit-form input, .cubane-listing-item.edit-form select, .cubane-listing-item.edit-form textarea',
        this._bound.onItemEditChanged
    );
    $(document).on(
        'cubane-listing-item-edit-changed',
        '.cubane-listing-item.edit-form .cubane-collection-items',
        this._bound.onItemEditChanged
    );
    $(document).on(
        'focusin',
        '.cubane-listing-item.edit-form input, .cubane-listing-item.edit-form select, .cubane-listing-item.edit-form textarea',
        this._bound.onItemEditStart
    );
    $(window).on('cubane-listing-item-edit-start', this._bound.onItemEditStart);
    $(document).on(
        'focusout',
        '.cubane-listing-item.edit-form input, .cubane-listing-item.edit-form select, .cubane-listing-item.edit-form textarea',
        this._bound.onItemEditEnd
    );
    $(document).on(
        'click',
        '.cubane-listing-save-changes',
        this._bound.onItemEditSaveChanges
    );
    $(document).on(
        'click',
        '.cubane-listing-discard-changes',
        this._bound.onItemEditDiscardChanges
    );
    $(window).on('cubane-listing-refresh', this._bound.onListingRefresh);
    $(window).on('resize', this._bound.onListingResize);

    // initialize initial UI state for each listing control...
    $('.cubane-listing').each($.proxy(function (i, listing) {
        var listing = $(listing);
        this.setupInitialState(listing);
        this.updateUIState(listing);
    }, this));

    // enter neutral selection state in dialog window on page load
    if ( window.parent !== window ) {
        window.parent.$(window.parent).trigger('cubane-listing-neutral');
    }

    // initial resize
    this._bound.onListingResize();
};


cubane.backend.ListingController.prototype = {
    dispose: function () {
        $(document).off(
            'cubane-listing-pre-select',
            this._bound.onPreSelect
        );
        $(document).off(
            'change',
            '.cubane-listing [name="selectall"]',
            this._bound.onToggleSelectAll
        );
        $(document).off(
            'click',
            '.cubane-listing [name="select"]',
            this._bound.onCheckboxClicked
        );
        $(document).off(
            'click',
            '.cubane-listing-edit',
            this._bound.onEditClicked
        );
        $(document).off(
            'click',
            '.cubane-listing-action',
            this._bound.onActionClicked
        );
        $(document).off(
            'click',
            '.cubane-shortcut-action',
            this._bound.onShortcutActionClicked
        );
        $(document).off(
            'click',
            '.cubane-listing-delete-empty',
            this._bound.onDeleteEmptyClicked
        )
        $(document).off(
            'click',
            '.cubane-listing-item-disable-enable',
            this._bound.onDisableEnableClicked
        );
        $(document).off(
            'click',
            '.cubane-listing-undo',
            this._bound.onUndoClicked
        );
        $(document).off(
            'keyup',
            '.search-query',
            this._bound.onSearchChanged
        );
        $(document).off(
            'click',
            '.cubane-listing-filter-toggle',
            this._bound.onFilterClicked
        );
        $(document).off(
            'keyup change',
            '.cubane-listing-filter input, ' +
            '.cubane-listing-filter textarea, ' +
            '.cubane-listing-filter select',
            this._bound.onFilterChanged
        );
        $(document).off(
            'cubane-listing-item-edit-changed',
            '.cubane-listing-filter .cubane-collection-items',
            this._bound.onFilterChanged
        );
        $(document).off(
            'submit',
            '.cubane-listing-filter form',
            this._bound.onFilterSubmit
        );
        $(document).off(
            'click',
            '.cubane-listing-filter .ui-listing-filter-close',
            this._bound.onFilterClose
        );
        $(document).off(
            'click',
            '.ui-listing-filter-reset',
            this._bound.onFilterReset
        );
        $(document).off(
            'click',
            '.cubane-listing .pagination a',
            this._bound.onPageClicked
        );
        $(document).off(
            'click',
            '.cubane-listing-column.sortable',
            this._bound.onColumnClicked
        );
        $(document).off(
            'click',
            '.cubane-listing-seq-apply',
            this._bound.onOrderApplyClicked
        );
        $(document).off(
            'click',
            '.cubane-listing-view > .btn',
            this._bound.onViewClicked
        );
        $(document).off(
            'cubane-tree-node-selected',
            '.cubane-listing.with-folders',
            this._bound.onTreeNodeSelected
        );
        $(document).off(
          'cubane-drop',
          this._bound.onDrop
        );
        $(document).off(
            'click',
            '.cubane-selector-item',
            this._bound.onSelectorItemClicked
        );
        $('.cubane-listing-content').off(
            'scroll',
            this._bound.onContentScrolled
        );
        $(document).off(
            'click',
            '.cubane-listing-item-view-obj > a',
            this._bound.onViewObjClicked
        );
        $(document).off(
            'change keydown',
            '.cubane-listing-item.edit-form input, .cubane-listing-item.edit-form select, .cubane-listing-item.edit-form textarea',
            this._bound.onItemEditChanged
        );
        $(document).off(
            'cubane-listing-item-edit-changed',
            '.cubane-listing-item.edit-form .cubane-collection-items',
            this._bound.onItemEditChanged
        );
        $(document).off(
            'focusin',
            '.cubane-listing-item.edit-form input, .cubane-listing-item.edit-form select, .cubane-listing-item.edit-form textarea',
            this._bound.onItemEditStart
        );
        $(window).off('cubane-listing-item-edit-start', this._bound.onItemEditStart);
        $(document).off(
            'focusout',
            '.cubane-listing-item.edit-form input, .cubane-listing-item.edit-form select, .cubane-listing-item.edit-form textarea',
            this._bound.onItemEditEnd
        );
        $(document).off(
            'click',
            '.cubane-listing-save-changes',
            this._bound.onItemEditSaveChanges
        );
        $(document).off(
            'click',
            '.cubane-listing-discard-changes',
            this._bound.onItemEditDiscardChanges
        );
        $(window).off('cubane-listing-refresh', this._bound.onListingRefresh);
        $(window).off('resize', this._bound.onListingResize);

        this._bound = null;
    },


    /*
     * Initialise listing control based on current state
     */
    setupInitialState: function (listing) {
        var cb = listing.find('tbody').find('[name="select"]');
        for ( var i = 0; i < cb.length; i++ ) {
            var c = cb.eq(i);
            var item = c.closest('tr');

            if ( c.is(':checked') ) {
                this.selectItem(item);
            } else {
                this.unselectItem(item);
            }
        }

        // scroll to current selector item
        var item = listing.find('.cubane-selector-item.active:first');
        if ( item.length > 0 ) {
            listing.find('.cubane-selector-list').scrollTop(item.position().top);
        }

        this.enableSorting(listing);
        this.updateUIState(listing);
    },


    /*
     * Enable sorting of the list.
     */
    enableSorting: function (listing) {
        // listing is not sortable to begin with
        if ( !listing.hasClass('sortable') ) return;

        var view = listing.attr('data-view');
        var applyBtn = listing.find('.cubane-listing-seq-apply');

        // initially, we cannot apply order if we are sorting by order
        applyBtn.attr(
            'disabled',
            $('.cubane-listing-seq-column').hasClass('active')
        );

        var columnName = this.getColumnName(listing);
        var enabled = columnName === 'seq';

        if (enabled) {
            listing.addClass('cubane-listing-can-sort');
        } else {
            listing.removeClass('cubane-listing-can-sort');
        }

        // make list sortable
        cubane.backend.sortable('.cubane-listing-item', '.ui-sortable-handle', function() {
            // whenever we change the seq. manually via sortable, we switch back
            // to the seq. column, because the seq (which we manually changed)
            // is the one that is applied...
			listing.find('.cubane-listing-column.active').removeClass('active').attr('data-reverse-order', 0);
			listing.find('.cubane-listing-seq-column').addClass('active');

            // apply sorting
            this.applySorting(listing);
        }.bind(this), undefined, enabled);
    },


    /*
     * Return a list of indentifiers in the order in which they currently appear.
     */
    getListingSeqUrlData: function(listing) {
        var ids = [];
        var items = listing.find('.cubane-listing-item');
        for (var i = 0; i < items.length; i++) {
            ids.push('item[]=' + items.eq(i).attr('data-id'));
        }
        return ids.join('&');
    },


    /*
     * Apply current seq. ordering for the given listing.
     */
    applySorting: function(listing) {
        if ( !listing.hasClass('sortable') ) return;

        var url = listing.attr('data-seq-url');
        var applyBtn = listing.find('.cubane-listing-seq-apply');
        var page = this.getPage(listing);
        var columnName = this.getColumnName(listing);
        var reverseOrder = this.getReverseOrder(listing);
        var folders = this.getFolders(listing);
        var data = this.getListingSeqUrlData(listing);
        if (data !== '') data += '&';
        data += (
            'page=' + encodeURIComponent(page) +
            '&folders=' + encodeURIComponent(folders) +
            '&o=' + encodeURIComponent(columnName) +
            '&ro=' + encodeURIComponent(reverseOrder)
        );

        $.post(url, data, function(json) {
            if (json.success) {
                // after we applied sorting order, we cannot apply again,
                // unless we change the sorting order to something else that
                // is not 'seq'...
                applyBtn.attr('disabled', true);

                // after changing the order (or applying it), switch to 'seq'
                // order, so that the order is fronzen in and does not change
                // even after we filter or paginate the result...
                listing.find('.cubane-listing-column.active').removeClass('active');
                listing.find('.cubane-listing-seq-column').addClass('active');

                this.updateUIState(listing);
                this.enableSorting(listing);

                if (json.updated) {
                    // indicate that we can publish again if we updated at
                    // least one record...
                    $('.cms-publish').addClass('can-publish');

                    // update tree if we just changed the order of it...
                    if (listing.hasClass('single-model-with-folders')) {
                        $(window).trigger('cubane-tree-refresh');
                    }
                }
            }
        }.bind(this), 'json');
    },


    /*
     * Event for pre-selecting a set of items.
     */
    onPreSelect: function (e, ids) {
        if ( ids ) {
            var listings = $('.cubane-listing');
            for ( var i = 0; i < listings.length; i++ ) {
                var listing = listings.eq(i);

                for ( var j = 0; j < ids.length; j++ ) {
                    var item = listing.find(
                        '.cubane-listing-item[data-id="' + ids[j] + '"]'
                    );
                    this.selectItem(item);
                }

                this.updateUIState(listing);
            }
        }
    },


    /*
     * Select/Unselect all items
     */
    onToggleSelectAll: function (e) {
        var cb = $(e.target).closest('input');
        var listing = cb.closest('.cubane-listing');

        if ( cb.is(':checked') ) {
            this.selectAll(listing);
        } else {
            this.unselectAll(listing);
        }

        this.updateUIState(listing);
    },


    /*
     * Clickin on an item should select just that item, unless we clicked on
     * a link inside, the checkbox to select multiple items or we used keyboard
     * modifiers, such as SHIFT or CTRL.
     */
    onItemClicked: function (e) {
        var item = $(e.target).closest('.cubane-listing-item');
        var listing = item.closest('.cubane-listing');

        // ignore if we are in edit mode, trigger editing start instead
        if (listing.hasClass('edit-mode')) {
            this.onItemEditStart(e);
            return;
        }

        // primary column click action -> view/edit
        if ( $(e.target).closest('span.primary').length > 0 || $(e.target).closest('.cubane-listing-item-edit').length > 0) {
            var a = listing.find('.cubane-listing-edit');
            var url = this.constructActionUrl(a.prop('href'), item);

            if (listing.hasClass('cubane-open-in-new-window') || listing.hasClass('related-listing')) {
                // new window
                cubane.backend.openIndexDialog(url, false, false);
            } else {
                // direct
                window.location.href = url;
            }
        }

        if ( $(e.target).closest('a').length > 0 ) {
            // clicking on a link should go there
            return;
        } else {
            e.preventDefault();
            e.stopPropagation();

            // clicking anywhere else should select it
            // (taking modifiers into account)
            if ( e.shiftKey ) {
                this.selectRange(this.getFirstSelectedItem(listing), item);
            } else if ( e.metaKey || e.ctrlKey ) {
                this.toggleItemSelection(item);
            } else {
                // just clicking on an item (without any modifiers)
                // which is the only selected item should toggle selection.
                if (
                    item.hasClass('selected') &&
                    listing.find('.cubane-listing-item.selected').length === 1
                ) {
                    this.toggleItemSelection(item);
                } else {
                    this.selectItem(item, true);
                }
            }
        }

        this.updateUIState(listing);
        return false;
    },


    /*
     * Double-clicking an item goes into edit mode, unless it is presented on
     * a dialog window in which case we select the item (and only the item)
     * and confirm the dialog.
     */
    onItemDblClicked: function (e) {
        e.preventDefault();

        var item = $(e.target).closest('.cubane-listing-item');
        var listing = item.closest('.cubane-listing');

        // ignore if we are in edit mode
        if (listing.hasClass('edit-mode')) {
            return;
        }

        // when dbl-clicking a listing item, select the item first
        this.onItemClicked.call(this, e);

        if ( $('body').hasClass('browse-dialog') ) {
            this.selectItem(item);
            this.updateUIState(listing);

            window.parent.$('.modal-iframe .confirm').click();
        } else {
            var a = listing.find('.cubane-listing-edit');
            var url = this.constructActionUrl(a.prop('href'), item);

            if (listing.hasClass('related-listing')) {
                cubane.backend.openIndexDialog(url, false, false);
            } else {
                window.location.href = url;
            }
        }
    },


    onCheckboxClicked: function (e) {
        var item = $(e.target).closest('.cubane-listing-item');
        var listing = item.closest('.cubane-listing');
        this.toggleItemSelection(item);
        this.updateUIState(listing);
    },


    handleActionButtonClicked: function(e) {
        e.preventDefault();
        if ( $(e.target).closest('.cubane-listing-action').hasClass('disabled') ) return;

        var a = $(e.target).closest('a');
        var listing = a.closest('.cubane-listing');
        var selectedItems = this.getSelectedItems(listing);

        // determine url with selected items
        var url = this.constructActionUrl(
            a.prop('href'),
            selectedItems
        );

        if (a.hasClass('cubane-backend-open-dialog') || listing.hasClass('related-listing')) {
            var isExternal = a.hasClass('cubane-backend-open-dialog-external');
            var isSmallDialog = a.hasClass('cubane-backend-open-dialog-small');
            cubane.backend.openIndexDialog(url, isExternal, isSmallDialog);
        } else {
            document.location.href = url;
        }
    },


    onEditClicked: function (e) {
        e.preventDefault();
        e.stopPropagation();

        this.handleActionButtonClicked(e);
    },


    onActionClicked: function (e) {
        e.preventDefault();

        var btn = $(e.target).closest('.cubane-listing-action');
        if ( btn.hasClass('disabled') ) return;

        var a = $(e.target).closest('a');
        var listing = a.closest('.cubane-listing');

        // action is within an item?
        var items = a.closest('.cubane-listing-item');
        if (items.length === 0) {
            items = this.getSelectedItems(listing);
        }

        var ids = this.getIds(items);
        var method = a.attr('data-method');
        var title = a.attr('title');
        var hasPayload = (
            a.hasClass('cubane-listing-action-multiple') ||
            a.hasClass('cubane-listing-action-many') ||
            a.hasClass('cubane-listing-action-any')
        );
        var data = {};
        var pkPattern = a.attr('data-pk-pattern');
        if (pkPattern === undefined) pkPattern = 'pk';

        if ( hasPayload ) {
            data[pkPattern + 's'] = ids;
        } else {
            data[pkPattern] = ids[0];
        }

        var self = this;
        var executeAction = function() {
            if ( method === 'location' || method === undefined ) {
                // transition to given location
                var url = cubane.urls.combineUrlArgs(
                    a.attr('href'),
                    $.param(data)
                );

                // substitute known keys
                url = url.replace('%24pk', ids[0]);

                // open in current frame or within a new dialog window...
                if (a.hasClass('cubane-backend-open-dialog') || listing.hasClass('related-listing')) {
                    var isExternal = a.hasClass('cubane-backend-open-dialog-external');
                    var isSmallDialog = a.hasClass('cubane-backend-open-dialog-small');
                    cubane.backend.openIndexDialog(url, isExternal, isSmallDialog);
                } else {
                    document.location.href = url;
                }

                return false;
            }

            function _post(action, csrfToken) {
                // form post
                var form = $('<form></form');
                form.hide();
                form.attr('method', 'POST');
                form.attr('action', action);

                // attach payload
                if ( hasPayload ) {
                    for ( var i = 0; i < ids.length; i++ ) {
                        form.append('<input type="text" name="pks[]" value="' + ids[i] + '"/>');
                    }
                } else {
                    form.append('<input type="text" name="pk" value="' + ids[0] + '"/>');
                }

                // CSRF token
                if (csrfToken) {
                    form.append('<input type="hidden" name="csrfmiddlewaretoken" value="' + csrfToken + '"/>');
                }

                // submit form
                form.insertAfter(a);
                form.submit();
            }

            if ( method == 'form-post' ) {
                _post(a.attr('href'));
                return false;
            }

            if (method == 'download-with-encoding') {
                // create dialog window for choosing encoding
                var dialogUrl = cubane.urls.reverse('cubane.backend.download_with_encoding');
                dialogUrl = cubane.urls.combineUrlArg(dialogUrl, 'browse', true);
                dialogUrl = cubane.urls.combineUrlArg(dialogUrl, 'create', true);

                // open dialog window
                cubane.dialog.iframe('Download File', dialogUrl, {
                    dialogClasses: ['modal-small'],
                    okBtnLabel: 'Download File...',
                    okBtnIcon: 'icon-download',
                    closeBtn: false,
                    onOK: function(iframe) {
                        var form = $(iframe).contents().find('form');
                        var encoding = form.find('#id_encoding').val();
                        var csrfToken = form.find('input[name="csrfmiddlewaretoken"]').val();
                        var downloadUrl = cubane.urls.combineUrlArg(
                            a.attr('href'),
                            'encoding',
                            encoding
                        );
                        _post(downloadUrl, csrfToken);
                        return false;
                    }
                });

                return false;
            }

            // ajax
            var f = method === 'get' ? $.get : $.post;

            var performAction = function performAction() {
                cubane.backend.startLoading();

                f(a.attr('href'), data, function(json) {
                    cubane.backend.stopLoading();

                    // present multiple messages?
                    cubane.backend.presentMessagesFromResponse(json);

                    // success?
                    if (json.success) {
                        // refresh listing
                        this.refresh(listing);

                        // enable publish if action was delete
                        if (a.length > 0) {
                            var action = a.get(0).href;
                            if (action.length > 0 && action[action.length - 1] == '/') {
                                action = action.substring(0, action.length - 1);
                            }
                            action = action.split('/');
                            action = action[action.length - 1];

                            // indicate that we can publish again
                            if (action == 'delete') {
                                $('.cms-publish').addClass('can-publish');
                            }
                        }

                        // update tree?
                        if (listing.hasClass('single-model-with-folders')) {
                            $(window).trigger('cubane-tree-refresh');
                        }

                        if (window.parent !== window) {
                            // propagate to parent window if we are within
                            // a dialog window...
                            window.parent.$(window.parent).trigger('cubane-listing-delete', [ids]);
                        }
                    }
                }.bind(this), 'json').fail(function(xhr, status, error) {
                    // XHR error
                    cubane.backend.stopLoading();
                    cubane.backend.createMessage('error', 'This operation is currently not available.');
                });
            }.bind(this);

            if ( ids.length > 0 ) {
                // confirm?
                if ( a.attr('data-confirm') ) {
                    cubane.dialog.confirm(
                        'Confirmation Required',
                        a.attr('data-confirm'),
                        function () {
                            performAction();
                        }
                    );
                } else {
                    performAction();
                }
            }
        }.bind(this);

        // do we need to confirm this action?
        if ( a.hasClass('confirm') ) {
            var msg =
                'You have selected ' + ids.length + ' ' + (ids.length == 1 ? 'item' : 'items') + '. ' +
                (title ? title : 'Do you want to proceed') + '?';
            cubane.dialog.confirm('Confirm', msg, executeAction);
        } else {
            executeAction();
        }
    },


    onShortcutActionClicked: function(e) {
        var a = $(e.target).closest('.cubane-shortcut-action');
        var method = a.attr('data-method');

        if (method == 'download-with-encoding') {
            e.preventDefault();

            // create dialog window for choosing encoding
            var dialogUrl = cubane.urls.reverse('cubane.backend.download_with_encoding');
            dialogUrl = cubane.urls.combineUrlArg(dialogUrl, 'browse', true);
            dialogUrl = cubane.urls.combineUrlArg(dialogUrl, 'create', true);

            // open dialog window
            cubane.dialog.iframe('Download CSV File', dialogUrl, {
                dialogClasses: ['modal-small'],
                okBtnLabel: 'Download CSV File...',
                okBtnIcon: 'icon-download',
                closeBtn: false,
                onOK: function(iframe) {
                    var form = $(iframe).contents().find('form');
                    var encoding = form.find('#id_encoding').val();
                    var downloadUrl = cubane.urls.combineUrlArg(
                        a.attr('href'),
                        'encoding',
                        encoding
                    );
                    window.location.href = downloadUrl;
                    return false;
                }
            });
        }
    },


    onDeleteEmptyClicked: function(e) {
        e.preventDefault();
        if ( $(e.target).closest('.btn').hasClass('disabled') ) return;

        var a = $(e.target).closest('a');
        var listing = a.closest('.cubane-listing');

        var self = this;

        var executeAction = function() {
            $.post(a.attr('href'), [], function(json) {
                if (json.success) {
                    window.location.reload();
                }
            }, 'json');
        };


        if ( a.hasClass('confirm') ) {
            var msg = 'Do you want to proceed?';
            cubane.dialog.confirm('Confirm', msg, executeAction);
        } else {
            executeAction();
        }
    },


    onDisableEnableClicked: function(e) {
        e.preventDefault();
        if ( $(e.target).closest('.btn').hasClass('disabled') ) return;

        var a = $(e.target).closest('a');
        var listing = a.closest('.cubane-listing');
        var item = a.closest('.cubane-listing-item');
        var ids = this.getIds(item);
        var method = a.attr('data-method');
        var title = a.attr('title');
        var data = { pks: ids };

        var self = this;

        var executeAction = function() {
            // ajax
            var f = method === 'get' ? $.get : $.post;

            function performAction() {
                f(a.attr('href'), data, function (json) {
                    if ( json.success ) {
                        self.updateUIState(listing);
                        self.refresh(listing);
                    }
                }, 'json');
            }

            if ( ids.length > 0 ) {
                // confirm?
                if ( a.attr('data-confirm') ) {
                    cubane.dialog.confirm(
                        'Confirmation Required',
                        a.attr('data-confirm'),
                        function () {
                            performAction();
                        }
                    );
                } else {
                    performAction();
                }
            }
        };

        // do we need to confirm this action?
        if ( a.hasClass('confirm') ) {
            var msg =
                'You have selected ' + ids.length + ' ' + (ids.length == 1 ? 'item' : 'items') + '. ' +
                (title ? title : 'Do you want to proceed') + '?';
            cubane.dialog.confirm('Confirm', msg, executeAction);
        } else {
            executeAction();
        }
    },


    onUndoClicked: function (e) {
        e.preventDefault();
        if ( $(e.target).closest('.btn').hasClass('disabled') ) return;

        var a = $(e.target).closest('a');
        var pks = a.attr('data-ids').toString().split(',');
        $.post(a.prop('href'), { pks: pks }, function (json) {
            window.location.reload();
        }, 'json');
    },


    /*
     * Triggered whenever we change a search input field (listing or selector).
     */
    onSearchChanged: function (e) {
        // ignore SHIFT, CRTL, META
        if ( e.keyCode == 16 || e.keyCode == 17 || e.keyCode == 91 ) return;

        if ( this._searchChanged ) {
            clearTimeout(this._searchChanged);
        }

        var el = $(e.target).closest('.search-query');
        this._searchChanged = setTimeout(
            $.proxy(this.onSearch, this, el),
            250
        );
    },


    /*
     * Fired whenever we need to perform a search.
     */
    onSearch: function (el) {
        var listing = this.getListing(el);

        if ( el.hasClass('selector-search') ) {
            this.refreshSelectorListing(listing);
        } else {
            this.refresh(listing);
        }
    },


    getListing: function (el) {
        if (el.closest('.cubane-listing').length > 0) {
            return el.closest('.cubane-listing');
        } else {
            var actions = el.closest('.cubane-listing-nav-actions');
            var listing = $('#' + actions.attr('data-id'))[0];
            return $(listing);
        }
    },


    getListingAction: function (listing, action_class, attr) {
        if (listing.find(action_class).length > 0) {
            var item = listing.find(action_class);
        } else {
            var actions = $('.cubane-listing-nav-actions');
            for (var i = 0; i < actions.length; i++) {
                if ($(actions[i]).attr('data-id') == listing.attr('id')) {
                    var item = $(actions[i]).find(action_class);
                }
            }
        }

        if (attr && item) return item.attr(attr);
        return item;
    },


    /*
     * Fired whenever we toggle the filter by clicking on the filter button
     */
    onFilterClicked: function(e) {
        var listing = this.getListing($(e.target));

        // wait for bootstrap to toggle...
        setTimeout($.proxy(function () {
            this.updateUIState(listing);

            // automatically focus first field within filter form
            listing
                .find('.cubane-listing-filter-form')
                .find('input, textarea, select')
                .first()
                .focus();

            // refresh view, since we are changing view state which we need
            // to reflect on the server, but we do not need to update
            // the UI listing data
            this.refresh(listing, false);
        }, this), 0);
    },


    /*
     * Fired, whenever any form element of the filter form has been changed.
     */
    onFilterChanged: function(e) {
        // ignore change events from input fields, this will be
        // dealt with via key events already and would just couse another
        // roundtrip, unless this is a checkbox...
        if (e.type == 'change' && e.target && e.target.nodeName.toLowerCase() == 'input' && $(e.target).attr('type') != 'radio')
            return;

        // clear any previously scheduled update
        if (this._filterChanged) {
            clearTimeout(this._filterChanged);
            this._filterChanged = undefined;
        }

        // if we are hitting ENTER, do not delay key event...
        var listing = this.getListing($(e.target));
        if (!(e.type == 'keyup' && e.keyCode == 13)) {
            this._filterChanged = setTimeout(
                $.proxy(this.onFilter, this, listing),
                750
            );
        } else {
            this.onFilter(listing);
        }
    },


    /*
     * Fired, whenever we submit the filter form.
     */
    onFilterSubmit: function (e) {
        e.preventDefault();
        e.stopPropagation();

        var listing = this.getListing($(e.target));
        this.onFilter(listing);

        return false;
    },


    /*
     * Fired, whenever we click on the OK button within the listing filter form
     * which should then close the filter (the filter has already been applied
     * by just changing its content).
     */
    onFilterClose: function (e) {
        e.preventDefault();

        var listing = this.getListing($(e.target));
        listing.find('.cubane-listing-filter-toggle').removeClass('active');
        this.updateUIState(listing);
    },


    /*
     * Fired, whenever we click on the Clear button within the listing filter
     * form which should then reset the filter and close the filter window.
     */
    onFilterReset: function (e) {
        e.preventDefault();

        var listing = this.getListing($(e.target));

        // clear all filter form fields
        listing.find(
            '.cubane-listing-filter input,' +
            '.cubane-listing-filter textarea,' +
            '.cubane-listing-filter select'
        ).filter(function() {
            var type = $(this).attr('type');
            return type != 'radio' && type != 'checkbox';
        }).val('');

        // uncheck all radio and checkbox buttons
        listing.find('.cubane-listing-filter input[type="checkbox"], .cubane-listing-filter input[type="radio"]').removeAttr('checked');

        // clear general search fields
        listing.find('.search-query').val('');

        // select first radio button in each group (which is suppose to be the OFF switch)
        var groups = listing.find('.cubane-listing-filter ul').find('input[type="radio"]:first').click();

        // clear selector
        listing.find('.cubane-selector-item.active').removeClass('active');

        // close filter panel
        listing.find('.cubane-listing-filter-toggle').removeClass('active');

        // update listing
        this.onFilter(listing);
    },


    /*
     * User switches current page as part of pagination
     */
    onPageClicked: function (e) {
        e.preventDefault();

        var listing = $(e.target).closest('.cubane-listing');
        var item = $(e.target).closest('li');
        var paginator = item.closest('.pagination');

        // update ui state
        paginator.find('.active').removeClass('active');
        item.addClass('active');

        // update listing
        this.onFilter(listing);
    },


    /*
     * Fired whenever we need to perform a filter operation.
     */
    onFilter: function(listing) {
        this.refresh(listing);
    },


    /*
     * Clicking on a sortable data column should sort the listing by this
     * column.
     */
    onColumnClicked: function(e) {
        var column = $(e.target).closest('.cubane-listing-column');
		var listing = column.closest('.cubane-listing');

        // ignore if we are in edit mode
        if (listing.hasClass('edit-mode')) {
            return;
        }

        if ( column.hasClass('active') && column.attr('data-name') !== 'seq' ) {
			// update reverse order if active
			var reverseOrder = parseInt(column.attr('data-reverse-order')) === 1 ? 0 : 1;
			column.attr('data-reverse-order', reverseOrder);
		} else {
			listing.find('.cubane-listing-column.active').removeClass('active').attr('data-reverse-order', 0);
			column.addClass('active');
		}

        this.refresh(listing);
    },


    /*
     * Clicking on "Order Apply" button should apply (store) the current order
     * of listing item as the applied "sequence" of items.
     */
    onOrderApplyClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        var listing = this.getListing($(e.target));
        this.applySorting(listing);
    },


    /*
     * Toggling between listing view, grid view and other types of presentation.
     */
    onViewClicked: function (e) {
        // wait for bootstrap to toggle...
        setTimeout($.proxy(function () {
            var listing = this.getListing($(e.target));
            this.refresh(listing);
        }, this), 0);
    },


    /*
     * Tree node selected -> apply filter by folder
     */
    onTreeNodeSelected: function (e, nodeIds) {
        if (nodeIds === undefined || nodeIds.length === 0)
            return;

        // update create new node arguments
        var listing = $(e.currentTarget);
        var nodeId = nodeIds[0];
        listing.find('.cubane-listing-folders-create-folder').attr('data-args', 'parent_id=' + nodeId.toString());

        // update create new entity url
        var createBtn = listing.find('.cubane-listing-create');
        if (createBtn.length > 0) {
            var url = createBtn.attr('href');
            var folderAssignmentName = createBtn.data('folder-assignment-name');
            var re = RegExp(folderAssignmentName + '=[-0-9]+');
            url = url.replace(re, folderAssignmentName + '=' + nodeId);
            createBtn.attr('href', url);
        }

        // refresh listing
        this.refresh(listing);
    },


    /*
     * Items were dropped onto a folder -> tell server
     */
    onDrop: function onDrop(e, selection) {
        var target = $(e.target);
        this.moveSelectionToFolder(selection, target);
    },


    /*
     * Switch selector object when such is clicked.
     */
    onSelectorItemClicked: function (e) {
        e.preventDefault();
        var item = $(e.target).closest('.cubane-selector-item');
        var listing = item.closest('.cubane-listing');

        // toggle state
        if ( item.hasClass('active') ) {
            item.removeClass('active');
        } else {
            listing.find('.cubane-selector-item.active').removeClass('active');
            item.addClass('active');
        }

        // refresh main listing view
        this.refresh(listing);
    },


    /*
     * Lazy-load only detects when we scroll the window, not neccessarily when
     * we scroll a specific element. Therefore we have to detect it here and
     * then simply tell lazy-load to process new images.
     */
    onContentScrolled: function () {
        document.lazyloadImages();
    },


    /*
     * Called whenever to want to preview an object's presentation in another
     * window, for example when previewing a CMS page. We will add a random
     * argument to the URL, so that the content is always refreshed, otherwise
     * authors may see cached results after having just editing the content of
     * a page for example.
     */
    onViewObjClicked: function(e) {
        var a = $(e.target).closest('a');
        var href = a.attr('data-href');
        href += '?_=' + Math.floor((Math.random() * 99999999) + 1);
        a.attr('href', href);
    },


    /*
     * Triggered whenever we changed one inline form field in edit mode.
     */
    onItemEditChanged: function(e) {
        // ignore TAB, Shift, Alt
        if ([9, 16, 18, 91].indexOf(e.keyCode) !== -1) return;

        // arrow up/down
        var target = $(e.target);
        if ([38, 40].indexOf(e.keyCode) !== -1) {
            e.preventDefault();

            if (e.keyCode === 40) {
                this.editModeSelectRow(target, 'next');
            } else {
                this.editModeSelectRow(target, 'prev');
            }

            return;
        }

        // indicate that the item has been changed
        var item = target.closest('.cubane-listing-item');
        item.addClass('edit-mode-changed');

        // indicate that we can save/discard changes
        var listing = this.getListing(target);
        listing.find('.cubane-listing-header-save-changes-toolbar .btn').removeClass('disabled');
    },


    /*
     * Select next/prev row based on the currently focused item (target).
     */
    editModeSelectRow: function(target, direction) {
        var fieldname = target.attr('name');
        var item = target.closest('.cubane-listing-item');
        var nextItem = undefined;

        if (direction === 'next') {
            nextItem = item.next('.cubane-listing-item');
            if (nextItem.length === 0) {
                nextItem = item.parent().find('.cubane-listing-item').first();
            }
        } else if (direction === 'prev') {
            nextItem = item.prev('.cubane-listing-item');
            if (nextItem.length === 0) {
                nextItem = item.parent().find('.cubane-listing-item').last();
            }
        }

        if (nextItem && nextItem.length > 0) {
            var field = nextItem.find('[name="' + fieldname + '"]');
            if (field.length > 0) {
                field.focus().select();
            }
        }
    },


    /*
     * Start editing item in edit mode (focus in)
     */
    onItemEditStart: function(e) {
        // enter for current item
        var item = $(e.target).closest('.cubane-listing-item');
        item.addClass('edit-mode-editing');

        setTimeout(function() {
            // leave for any other item
            var listing = item.closest('.cubane-listing-root');
            listing.find('.cubane-listing-item.edit-mode-editing').not(item).removeClass('edit-mode-editing');
        }, 100);
    },


    /*
     * End editing item in edit mode (focus out)
     */
    onItemEditEnd: function(e) {
        var item = $(e.target).closest('.cubane-listing-item');

        // delay leaving edit mode a bit, so that a click on a new row
        // has a chance to actually go through, otherwise the position of
        // the element we clicked on might already be moved...
        setTimeout(function() {
            item.removeClass('edit-mode-editing');
        }, 100);
    },


    /*
     * Save changes due to inline editing.
     */
    onItemEditSaveChanges: function(e) {
        e.preventDefault();

        // endpoint url
        var a = $(e.target).closest('.cubane-listing-save-changes');
        var url = a.attr('href');

        // collect changed items data
        var data = {
            ids: []
        };
        var listing = a.closest('.cubane-listing');
        var changedItems = listing.find('.cubane-listing-item.edit-form.edit-mode-changed');
        for (var i = 0; i < changedItems.length; i++) {
            var item = changedItems.eq(i);
            var form = item.find('form');
            var pk = item.attr('data-id');
            var fields = form.find('input, select, textarea');

            var formData = []
            for (var j = 0; j < fields.length; j++) {
                var field = fields.eq(j);
                var key = field.attr('name');
                var value;

                if (key) {
                    if (field.attr('type') === 'checkbox') {
                        value = field.is(':checked') ? 'true' : 'false'
                    } else {
                        value = field.val();
                    }

                    // get field value
                    if (!Array.isArray(value)) {
                        value = [value];
                    }

                    // encode key/value
                    for (var k = 0; k < value.length; k++) {
                        var v = value[k];

                        if (!v) {
                            v = ''
                        }

                        // we do not fully url encode here, since this query
                        // string will become part of a much larger query string
                        formData.push(key.toString() + '=' + v.replace('&', '%26').replace('=', '%3D'));
                    }
                }
            }

            data['pk-' + pk] = formData.join('&');
            data.ids.push(pk);
        }

        // submit to server
        cubane.backend.startLoading();
        $.post(url, data, function(json) {
            cubane.backend.stopLoading();

            // mark everything as without errors
            changedItems.removeClass('error').find('.error').removeClass('error');

            if (json.success) {
                // mark everything as unchanged, since we now saved everything
                changedItems.removeClass('edit-mode-changed').removeClass('edit-mode-changed');

                // cannot save/discard until further change...
                listing.find('.cubane-listing-header-save-changes-toolbar .btn').addClass('disabled');

                // success message or messages
                cubane.backend.createMessage('success', json.message, json.change);
            } else {
                // process form errors
                var pks = Object.keys(json.errors);
                for (var i = 0; i < pks.length; i++) {
                    var pk = pks[i];
                    var unchangedItem = listing.find('#item_' + pk.replace('pk-', ''));
                    unchangedItem.addClass('edit-mode-changed error');
                    var fieldnames = Object.keys(json.errors[pk]);
                    for (var j = 0; j < fieldnames.length; j++) {
                        var fieldname = fieldnames[j];

                        if (fieldname === '__all__') {
                            // general form error
                            var msg = '';
                            for (var j = 0; j < json.errors[pk]['__all__'].length; j++) {
                                msg += '<p>' + json.errors[pk]['__all__'][j] + '</p>';
                            }
                            cubane.backend.createMessage('error', msg);
                        } else {
                            // field-specific error
                            var input = unchangedItem.find('[name="' + fieldname + '"]');
                            var container = input.closest('.control-group');
                            container.addClass('error');

                            var helpBlock = container.find('.help-block');
                            if (helpBlock.length === 0) {
                                helpBlock = $('<div class="help-block"></div>');
                                helpBlock.insertAfter(input);
                            }
                            helpBlock.html(json.errors[pk][fieldname]);
                        }
                    }
                }
            }
        }, 'JSON');
    },


    /*
     * Discard changes due to inline editing.
     */
    onItemEditDiscardChanges: function(e) {
        e.preventDefault();

        var listing = this.getListing($(e.target));
        this.refresh(listing);
    },


    /*
     * Triggered by other parts of the system to force-refresh the given listing.
     */
    onListingRefresh: function onListingRefresh(e, listing) {
        // only refresh if the listing is actually visible, it might be
        // within a hidden tab panel which we do not neccessarily need to
        // update...
        if (listing.is(':visible')) {
            this.refresh(listing, true, true);
        }
    },


    /*
     * On listing resize
     */
    onListingResize: function onListingResize() {
        var listing = $('.cubane-listing.related-listing.full-height');
        if (listing.length > 0) {
            // vertical layout for desktop
            var ww = $(window).width();
            if (ww > 767) {
                var h;

                if ($('body').hasClass('frontend-editing')) {
                    h = $(window).height() - 100;
                } else {
                    var wh = $(window).height();
                    var nav = $('.nav-container').length > 0 ? $('.nav-container').outerHeight() : 0;
                    var title = $('.page-title').length > 0 ? $('.page-title').outerHeight() : 0;
                    var summaryItems = $('.summary-items').length > 0 ? $('.summary-items').outerHeight() : 0;
                    var navSteps = $('.nav-steps').length > 0 ? $('.nav-steps').outerHeight() : 0;
                    var formActions = $('.form-actions').length > 0 ? $('.form-actions').outerHeight() : 0;

                    h = wh - nav - title - summaryItems - navSteps - formActions - 150;
                }

                for (var i = 0; i < listing.length; i++) {
                    listing.eq(i).height(h);
                }
            } else {
                for (var i = 0; i < listing.length; i++) {
                    listing.eq(i).css('height', 'auto');
                }
            }
        }

        if ($(window).width() > 767) {
            var listing = $('.cubane-listing');
            for (var i = 0; i < listing.length; i++) {
                // make listing container width the same as header columns
                var tHead = listing.eq(i).find('.t-head');
                var tBody = listing.eq(i).find('.t-body').get(0);
                if (tBody && tBody.scrollWidth !== undefined) {
                    var headWidth = tHead.innerWidth();
                    var bodyWidth = tBody.scrollWidth;
                    var margin = Math.max(0, headWidth - bodyWidth);
                    tHead.css('marginRight', margin + 'px');
                }
            }
        }
    },


    /*
     * Return the current page we are on.
     */
    getPage: function(listing) {
        return listing.find('.cubane-listing-pagination').find('.active').attr('data-page');
    },


    /*
     * Return the current folder.
     */
    getFolders: function(listing) {
        var nodes = listing.find('.cubane-listing-folders-tree .tree-node.active');
        var ids = [];
        for (var i = 0; i < nodes.length; i++) {
            ids.push(nodes.eq(i).attr('data-id'));
        }
        return ids;
    },


    /*
     * Return the name of the active column we are currently sorting by.
     */
    getColumnName: function(listing) {
        return listing.find('.cubane-listing-column.active').attr('data-name');
    },


    /*
     * Return the current reverse order flag for this listing.
     */
    getReverseOrder: function(listing) {
        return parseInt(listing.find('.cubane-listing-column.active').attr('data-reverse-order')) === 1;
    },


    /*
     * Load new data from server and update table based on current view, search
     * and filter settings. This method is called whenever we change view
     * options.
     */
    refresh: function (listing, updateDomListing, retainScrollPos) {
        if (updateDomListing === undefined) updateDomListing = true;
        if (retainScrollPos == undefined) retainScrollPos = false;

        var url = listing.attr('data-url');
        if ( url ) {
            var q = this.getListingAction(listing, '.listing-search').val();
            var columnName = this.getColumnName(listing);
            var view = this.getListingAction(listing, '.cubane-listing-view > .btn.active', 'data-view');
            var selector = listing.find('.cubane-selector-item.active').attr('data-id');
            var sortMode = listing.find('.cubane-listing-sort').hasClass('active');
            var filterFormEnabled = this.getListingAction(listing, '.cubane-listing-filter-toggle').hasClass('active');
            var page = this.getPage(listing);
            var folders = this.getFolders(listing);
            var reverseOrder = this.getReverseOrder(listing);
            var dialog = window.parent !== window;

            if ( !selector ) {
                selector = 0
            }

            // default arguments
            var arg = {
                q: q,
                o: columnName,
                v: view,
                s: selector,
                sm: sortMode,
                ff: filterFormEnabled,
                page: page,
                folders: folders,
				ro: reverseOrder,
                dialog: dialog
            };

            // arguments from filter from
            var fields = listing.find(
                '.cubane-listing-filter input,' +
                '.cubane-listing-filter textarea,' +
                '.cubane-listing-filter select'
            );
            for (var i = 0; i < fields.length; i++) {
                var field = fields.eq(i);
                var fieldtype = field.prop('type');
                var fieldname = field.attr('name');
                if (fieldname) {
                    fieldname = fieldname.replace('_filter_', '');
                    var fieldvalue = false;

                    // skip select2 input fields
                    if (field.closest('.select2').length > 0) {
                        continue;
                    }

                    // skip radio buttons that are not checked
                    if ( fieldtype == 'radio' && !field.is(':checked') ) {
                        continue;
                    }

                    // determine field type
                    if (fieldtype == 'checkbox') {
                        var relatedFields = fields.filter('[name="' + fieldname + '"]');

                        // type of checkbox
                        if (relatedFields.length > 1) {
                            // multiselect
                            fieldvalue = [];
                            for (var j = 0; j < relatedFields.length; j++) {
                                if (relatedFields.eq(j).is(':checked')) {
                                    fieldvalue.push(relatedFields.eq(j).val());
                                }
                            }

                            if (fieldvalue.length === 0) {
                                fieldvalue = null;
                            }
                        } else {
                            // standard checkbox (true/false)
                            fieldvalue = field.is(':checked');
                        }
                    } else {
                        // regular field, just copy the value
                        fieldvalue = field.val();
                    }

                    // remove empty values from array values
                    if (Array.isArray(fieldvalue)) {
                        var newFieldValue = [];
                        for (var j = 0; j < fieldvalue.length; j++) {
                            if (fieldvalue[j] !== '') {
                                newFieldValue.push(fieldvalue[j]);
                            }
                        }
                        fieldvalue = newFieldValue;
                    }

                    // if argument already exists, then create an Array or
                    // append to existing Array
                    var key = 'f_' + fieldname;
                    if (arg[key] !== undefined) {
                        // create array if not array yet
                        if (!Array.isArray(arg[key])) {
                            arg[key] = [arg[key]];
                        }

                        // append new value to array
                        arg[key].push(fieldvalue);
                    } else {
                        // new value
                        arg[key] = fieldvalue;
                    }
                }
            }

            // related listing
            if (listing.hasClass('related-listing')) {
                arg['r_listing'] = '1';
                arg['r_pk'] = listing.attr('data-related-instance-pk');
                arg['r_attr'] = listing.attr('data-related-instance-attr');
            }

            // retreive new content from server according to current options...
            if (updateDomListing) {
                listing.addClass('loading');
            }
            $.get(url, arg, $.proxy(function(content) {
                // ignore result if we do not want to update the dom listing...
                if (!updateDomListing) return;

                // remember current scroll position
                var container = listing.find('.cubane-listing-content');
                var scrollContainer = (view == 'grid') ?
                    listing.find('.cubane-listing-grid-items') :
                    listing.find('.t-body');
                var scrollPos = scrollContainer.scrollTop();

                // update content
                container.html(content);

                // restore scroll position, if possible
                if (retainScrollPos) {
                    scrollContainer = (view == 'grid') ?
                        listing.find('.cubane-listing-grid-items') :
                        listing.find('.t-body');
                    scrollContainer.scrollTop(scrollPos);
                }

                // indicating stat we are done and restore view properties
                listing.removeClass('loading');
                if ( view == 'grid' ) {
                    container.addClass('grid-view');
                } else {
                    container.removeClass('grid-view');
                }

                // load images as required and update ui state
                listing.attr('data-view', view);
                this.updateUIState(listing);
                this.enableSorting(listing);

                // re-initialize javascript controls in edit mode
                if (view === 'edit') {
                    $('.cubane-listing-content .select-tags').select2();
                    $('.cubane-listing-content .date-field input').datepicker({ format: 'dd/mm/yyyy' });
                }

                if ( document.lazyloadImages ) document.lazyloadImages();
                if ( document.lazyloadRefreshContainer ) document.lazyloadRefreshContainer();
            }, this));
        }
    },


    /*
     * Load new data from server regarding selector listing and update the
     * listing on the screen.
     */
    refreshSelectorListing: function (listing) {
        var url = listing.attr('data-selector-url');
        if ( url ) {
            var sq = listing.find('.selector-search').val();

            // retreive new content from server according to current options...
            $.get(url, { sq: sq }, $.proxy(function(content) {
                listing.find('.cubane-selector-list').html(content);
                if ( document.lazyloadImages ) document.lazyloadImages();
                this.updateUIState(listing);
            }, this));
        }
    },


    /*
     * Update UI state.
     */
    updateUIState: function (listing) {
        // filter form
        var filter = this.getListingAction(listing, '.cubane-listing-filter-toggle');
        var filterForm = listing.find('.cubane-listing-filter');
        if ( filter && filter.hasClass('active') ) {
            listing.addClass('with-filter');
            listing.find('.cubane-listing-content-frame, .cubane-listing-header').css({
                right: filterForm.width()
            });
        } else {
            listing.removeClass('with-filter');
            listing.find('.cubane-listing-content-frame, .cubane-listing-header').css({
                right: 0
            });
        }

        // filtered objects notice
        var objectsFiltered = parseInt(listing.find('.cubane-listing-root').attr('data-objects-filtered'));
        var objectsFilteredLabels = listing.find('.cubane-listing-filter-form-objects-filtered');
        if ( objectsFiltered > 0 ) {
            objectsFilteredLabels.addClass('filtered');
            listing.find('.cubane-listing-filter-form-objects-filtered.badge, .cubane-listing-filter-form-objects-filtered .badge').text(objectsFiltered.toString());
        } else {
            objectsFilteredLabels.removeClass('filtered');
        }

        // filter clear btn
        var filterClearBtn = $('.ui-listing-filter-reset');
        if ( objectsFiltered > 0 ) {
            filterClearBtn.addClass('filtered');
        } else {
            filterClearBtn.removeClass('filtered');
        }

        // if we did not find anything due to quick search box, make the box red
        // to indicate an error...
        var objectsCount = parseInt(listing.find('.cubane-listing-root').attr('data-objects'));
        var quickSearch = listing.find('.listing-search.search-query');
        if ( objectsCount == 0 && objectsFiltered > 0 && quickSearch.val() != '' ) {
            quickSearch.addClass('error');
        } else {
            quickSearch.removeClass('error');
        }

        // count of selected versus total count
        var items = this.getSelectedItems(listing);
        var count = items.length;
        var nitems = listing.find('.cubane-listing-item').length;

        // if not all items are selected, untick 'select all'
        if ( count !== nitems ) {
            listing.find('input[name="selectall"]').attr('checked', false);
        }

        // only sortable if we have more than one row
        if ( nitems > 1 ) {
            $('.cubane-listing-sort').removeClass('disabled');
        } else {
            $('.cubane-listing-sort').addClass('disabled');
        }

        // button state
        var controls = listing.find('.cubane-listing-header');
        this.buttonState(controls.find('.cubane-listing-edit'), count == 1);
        this.buttonState(controls.find('.cubane-listing-duplicate'), count == 1);
        this.buttonState(controls.find('.cubane-listing-action.cubane-listing-action-single'), count == 1);
        this.buttonState(controls.find('.cubane-listing-action.cubane-listing-action-multiple'), count > 0);
        this.buttonState(controls.find('.cubane-listing-action.cubane-listing-action-many'), count >= 2);
        this.buttonState(controls.find('.cubane-listing-action.cubane-listing-action-any'), nitems > 0);

        // inline editing
        var view = this.getListingAction(listing, '.cubane-listing-view > .btn.active', 'data-view');
        if (view === 'edit') {
            // indicate that we are in editing mode
            listing.addClass('edit-mode');
            listing.find('.cubane-listing-header-save-changes-toolbar .btn').addClass('disabled');
        } else {
            listing.removeClass('edit-mode');
        }

        // propagate to parent window if we are within a dialog window...
        if ( window.parent !== window ) {
            var json = this.getJson(items);
            window.parent.$(window.parent).trigger('cubane-listing-update', [json]);
        }
    },


    /*
     * Add the given item to the current selection.
     */
    selectItem: function (item, singleSelection) {
        if ( singleSelection ) this.unselectAll(item.closest('.cubane-listing'));

        item.addClass('selected');
        item.find('[name="select"]').prop('checked', true);
    },


    /*
     * Remove the given item from the current selection.
     */
    unselectItem: function (item) {
        item.removeClass('selected');
        item.find('[name="select"]').prop('checked', false);
    },


    /*
     * Return true, if the given item is part of the current selection.
     */
    isItemSelected: function (item) {
        return item.hasClass('selected');
    },


    /*
     * Toggle selection state for the given item.
     */
    toggleItemSelection: function (item) {
        if ( this.isItemSelected(item) ) {
            this.unselectItem(item);
        } else {
            this.selectItem(item);
        }
    },


    /*
     * Select all items.
     */
    selectAll: function (listing) {
        var content = listing.find('.cubane-listing-content');
        content.find('[name="select"]').prop('checked', 'checked');
        content.find('.cubane-listing-item').addClass('selected');
    },


    /*
     * Select no item (clear selection).
     */
    unselectAll: function (listing) {
        var content = listing.find('.cubane-listing-content');
        content.find('[name="select"]').prop('checked', '');
        content.find('.cubane-listing-item').removeClass('selected');
    },


    /*
     * Select all items starting with the first given item, all items in between
     * and the last given item.
     */
    selectRange: function (itemStart, itemEnd) {
        if ( itemStart.length === 0 || itemEnd.length === 0 ) return;

        // figure out listing indecies
        var listing = itemStart.closest('.cubane-listing');
        var items = listing.find('.cubane-listing-item');
        var start = items.index(itemStart);
        var end = items.index(itemEnd);
        if ( start > end ) {
            var tmp = start;
            start = end;
            end = tmp;
        }

        // select
        for ( var i = start; i <= end; i++ ) {
            this.selectItem(items.eq(i));
        }

        this.updateUIState(listing);
    },


    /*
     * Return a list of all selected items.
     */
    getSelectedItems: function (listing) {
        return listing.find('.cubane-listing-item.selected');
    },


    /*
     * Return the first of the items within the current selection.
     */
    getFirstSelectedItem: function (listing) {
        return listing.find('.cubane-listing-item.selected:first');
    },


    /*
     * Return a list of identifiers for all items that are currently selected.
     */
    getIds: function (items, selector) {
        if (selector !== undefined) {
            items = items.filter(selector);
        }

        return this.getItemData(items, 'id');
    },


    /*
     * Return a list of json objects that represents all given items.
     */
    getJson: function (items) {
        var json = [];
        for ( var i = 0; i < items.length; i++ ) {
            var item = items.eq(i);
            var title = item.attr('data-title');
            if (!title) title = item.attr('title');

            json.push({
                'id': item.attr('data-id'),
                'title': title,
                'imageUrl': item.attr('data-image-url'),
                'imageAR': item.attr('data-image-ar')
            });
        }
        return json;
    },


    /*
     * Return a list of data attribute values for a data attribute with given
     * name for the given list of items.
     */
    getItemData: function (items, dataName) {
        var ids = [];
        var dataAttrName = 'data-' + dataName;
        for ( var i = 0; i < items.length; i++ ) {
            ids.push(items.eq(i).attr(dataAttrName));
        }
        return ids;
    },


    /*
     * Construct a url that is based on given base url but contains an argument
     * holding all identifiers for all selected items.
     */
    constructActionUrl: function (baseUrl, items) {
        var ids = this.getIds(items);
        var url = baseUrl;

        // add dialog arguments
        var dialogArgs = ['index-dialog', 'external-dialog'];
        for (var i = 0; i < dialogArgs.length; i++) {
            var value = cubane.urls.getQueryParamaterByName(dialogArgs[i]);
            if (value) {
                url = cubane.urls.combineUrlArgs(
                    url,
                    dialogArgs[i] + '=' + encodeURIComponent(value)
                );
            }
        }

        // add pk argument
        if ( ids.length === 1 ) {
            url = cubane.urls.combineUrlArgs(
                url,
                this.buildQueryString('pk', ids)
            );
        }

        return url;
    },


    /*
     * Construct query string with given name and values.
     */
    buildQueryString: function (varname, values) {
        var s = [];
        for ( var i = 0; i < values.length; i++ ) {
            s.push(varname + '=' + values[i]);
        }
        return s.join('&');
    },


    /*
     * Update enabled/disabled state for given button according to the given
     * enabled-state.
     */
    buttonState: function (btn, enabled) {
        if ( enabled ) {
            btn.removeClass('disabled');
        } else {
            btn.addClass('disabled');
        }
    },


    /*
     * Move given selection of listing items to the given folder.
     */
    moveSelectionToFolder: function moveSelectionToFolder(selection, folder) {
        if (selection.hasClass('cubane-listing-item')) {
            var listing = selection.closest('.cubane-listing');
            var url = listing.attr('data-move-to-tree-node-url');

            var args = {
                src: this.getIds(selection, '.cubane-listing-item'),
                dst: folder.attr('data-id'),
                cur: this.getFolders(listing)
            }

            if (args.src.length > 0) {
                // move selection to folder
                $.post(url, args, function(json) {
                    if (json.success) {
                        selection.remove()
                        this.refresh(listing);

                        // update tree as well?
                        if (listing.hasClass('single-model-with-folders')) {
                            $(window).trigger('cubane-tree-refresh');
                        }
                    }
                }.bind(this), 'JSON');
            }
        }
    }
};


/*
 * Create new backend controller(s) when DOM is ready and dispose it on unload.
 */
$(document).ready(function () {
    var listingController = new cubane.backend.ListingController();

    $(window).unload(function () {
        listingController.dispose();
        listingController = null;
    });
});


}(this));

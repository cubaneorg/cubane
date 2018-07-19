(function (globals){
"use strict";


cubane.namespace('cubane.backend');


cubane.require('cubane.urls');
cubane.require('cubane.dialog');


/*
 * Keeps track of selected items within the dialog window and the current
 * selection box.
 */
var itemJson = [];
var btn = null;
var select = null;


/*
 * Update UI State after the control changed its internal state.
 */
var updateUIState = function(collection) {
    var container = collection.find('.cubane-collection-items-container');
    var title = getTitle(collection);

    // present empty message if we do not have any images yet...
    var n = container.find('.cubane-listing-item').length;
    if ( n == 0 ) {
        container.html('<div class="empty-message">Empty ' + title + '. <span class="empty-message-more"> Click <b>Add...</b> in order to add items to this collection.</span></div>');
    } else {
        container.find('.empty-message').remove();
    }

    // hide + button, if we've exceeded max-items
    var maxItems = parseInt(collection.attr('data-max-items'));
    if (!isNaN(maxItems)) {
        var addBtn = collection.find('.add-collection-items');
        addBtn.attr('disabled', n >= maxItems);
    }

    // create generic hidden input field if no item exists, remove generic
    // input if we have at least one item...
    collection.find('> input[type="hidden"]').remove();
    if (n === 0) {
        var fieldName = collection.attr('data-name');
        collection.append('<input type="hidden" name="' + fieldName + '" value=""/>');
    }
};


/*
 * Return True, if we are on an create or edit page.
 */
var isCreateOrEditPage = function(iframe) {
    return $(iframe).contents().find('body').hasClass('create-edit-page');
};


/*
 * Clicking on OK within the dialog should receive the ids of all selected
 * element from the dialog before it is closed, which is then used to add
 * to elements to the collection.
 */
var onDialogOK = function(iframe) {
    if (isCreateOrEditPage(iframe)) {
        cubane.backend.submitForm($(iframe).contents().find('form.form-horizontal').get(0));
        return true;
    }

    if ( btn && itemJson.length >= 1 ) {
        // get context
        var collection = btn.closest('.cubane-collection-items');
        var allowDuplicates = collection.attr('data-allow-duplicates') === 'True';
        var sortable = collection.attr('data-sortable') === 'True' && collection.closest('.cubane-listing-filter').length === 0;
        var c = collection.find('.cubane-collection-items-container');
        var isGrid = c.hasClass('cubane-listing-grid-items');
        var name = collection.attr('data-name');
        var currentIds = [];
        var inputFields = collection.find('input[name="' + name + '"]');
        for (var i = 0; i < inputFields.length; i++) {
            currentIds.push(inputFields.eq(i).val());
        }

        // process all new items
        for ( var i = 0; i < itemJson.length; i++ ) {
            // avoid dupicates if we do not allow duplication...
            var id = itemJson[i].id;
            if (!allowDuplicates && currentIds.indexOf(id.toString()) !== -1) {
                continue;
            }

            // get item details
            var title = itemJson[i].title;
            var imageUrl = itemJson[i].imageUrl;
            var imageAR = itemJson[i].imageAR;
            var item;

            // create new DOM element representing the new item
            if (isGrid) {
                item = $([
                    '<div class="cubane-listing-item cubane-listing-grid-item collection-item" title="', title, '" data-id="', id, '">',
                        '<div class="thumbnail">',
                            '<div class="ui-remove"><svg viewBox="0 0 9.5 12"><use xlink:href="#icon-delete"/></svg><span class="ui-remove-label">Remove</span></div>',
                            '<div class="thumbnail-image-frame">',
                                '<div class="thumbnail-image lazy-load thumbnail-image-contain lazy-loaded" style="background-image: url(\'' + imageUrl + '\');"></div>' +
                            '</div>',
                            '<div class="thumbnail-filename primary"><span>', title, '</span></div>',
                        '</div>',
                        '<input type="hidden" name="', name, '" value="', id, '"/>',
                    '</div>'
                ].join(''));
            } else {
                item = $([
                    '<div class="cubane-listing-item cubane-listing-list collection-item" title="', title, '" data-id="', id, '">',
                        '<div class="cubane-collection-item-container' + (sortable ? ' ui-sortable' : '') + '" tabindex="0">',
                            '<div class="cubane-collection-item-title primary ui-edit">', title, '</div>',
                            '<div class="ui-remove"><svg viewBox="0 0 9.5 12"><use xlink:href="#icon-delete"/></svg><span class="ui-remove-label">Remove</span></div>',
                            '<div class="ui-sortable-handle"></div>',
                        '</div>',
                        '<input type="hidden" name="', name, '" value="', id, '"/>',
                    '</div>'
                ].join(''));
            }

            // append new item
            c.append(item);
        }

        updateUIState(collection);

        collection.trigger('cubane-listing-item-edit-changed');
    }
};


/*
 * Make listing sortable
 */
var makeSortable = function() {
    // lists
    cubane.backend.sortable(
        '.cubane-collection-items-container.cubane-listing-list.ui-sortable .cubane-listing-item',
        '.ui-sortable-handle'
    );

    // grids
    cubane.backend.sortable(
        '.cubane-collection-items-container.cubane-listing-grid-items.ui-sortable .cubane-listing-item'
    );
};


/*
 * Open browse dialog after a Add button was clicked.
 */
var onAddModels = function(e) {
    e.preventDefault();

    btn = $(this);
    itemJson = [];
    var collection = $(e.target).closest('.cubane-collection-items');
    var url, title;

    if ($(e.target).hasClass('alternative-collection-items')) {
        url = getAlternativeAddURL(collection);
        title = getAlternativeModelTitle(collection);
    } else {
        url = getAddURL(collection);
        title = getModelTitle(collection);
    }

    // construct dialog window url
    url = cubane.urls.combineUrlArg(url, 'browse', true);
    if (cubane.urls.getQueryParamaterByName('frontend-editing') === 'true') {
        url = cubane.urls.combineUrlArg(url, 'frontend-editing', true);
    }

    // open url in a dialog window...
    cubane.dialog.iframe('Browse ' + title, url, {
        onOK: onDialogOK
    });
};


/*
 * Open edit dialog after clicking primary
 */
var onEditModel = function(e) {
    e.preventDefault();

    var item = $(e.target).closest('.cubane-listing-item');
    var collection = item.closest('.cubane-collection-items');
    var pk = item.attr('data-id');
    var url = getAddURL(collection);
    var title = getModelTitle(collection);

    // ignore when in bulk editing
    if (item.closest('.cubane-listing-form').length > 0) {
        $(collection).trigger('cubane-listing-item-edit-start');
        return;
    }

    // construct dialog window url
    url = cubane.urls.combineUrlArg(url + 'edit/', 'pk', pk);
    url = cubane.urls.combineUrlArg(url, 'edit', true);

    // open url in a dialog window...
    cubane.dialog.iframe('Edit ' + title, url, {
        onOK: onDialogOK,
    });
    $('.modal-iframe .confirm').removeClass('disabled');
};


/*
 * Clicking on the remove icon should remove the element from the
 * collection.
 */
var onRemoveModel = function(e) {
    e.preventDefault();

    var item = $(e.target).closest('.cubane-listing-item');
    var collection = item.closest('.cubane-collection-items');

    item.fadeOut('fast', function() {
        item.remove();
        updateUIState(collection);
        collection.trigger('cubane-listing-item-edit-changed');
    });
};


/*
 * Listing selection update from within dialog window
 */
var onListingSelectionUpdate = function(e, json) {
    var btn = $('.modal-iframe .confirm');
    if ( btn.length > 0 ) {
        if ( json.length >= 1 ) {
            btn.removeClass('disabled');
        } else {
            btn.addClass('disabled');
        }
    }

    // keep track of selection
    itemJson = json;
};


/*
 * Listing item deleted from within dialog window
 */
var onListingDelete = function(e, ids) {
    for (var i = 0; i < ids.length; i++) {
        $('.cubane-collection-items .cubane-listing-item[data-id="' + ids[i] + '"]').remove();
    }
};


/*
 * Clicking on an Add button should open the browse dialog for model.
 */
var enableModelSupport = function() {
    $(window).on('cubane-listing-update', onListingSelectionUpdate);
    $(window).on('cubane-listing-delete', onListingDelete);
    $(document).on('click', '.add-collection-items', onAddModels);
    $(document).on('click', '.cubane-collection-items-container .ui-remove', onRemoveModel);
    $(document).on('click', '.cubane-collection-items-container .ui-edit', onEditModel);

    // collections within filter panels should not be sortable
    $('.cubane-collection-items-container.ui-sortable').each(function() {
        if ($(this).closest('.cubane-listing-filter').length > 0) {
            $(this).removeClass('ui-sortable');
            $(this).find('.ui-sortable').removeClass('ui-sortable');
        }
    });

    // enable sorting
    makeSortable();

    $('.cubane-collection-items').each(function() {
        updateUIState($(this));
    });
};


/*
 * Get url to open when adding models.
 */
var getAddURL = function(collection) {
    return collection.attr('data-url');
};


/*
 * Get the alternative url to open when adding models.
 */
var getAlternativeAddURL = function(collection) {
    return collection.attr('data-alt-url');
};


/*
 * Get title for displaying if empty collection.
 */
var getTitle = function(collection) {
    return collection.attr('data-title');
};


/*
 * Get model title for dialog window title.
 */
var getModelTitle = function(collection) {
    return collection.attr('data-model-title');
};


/*
 * Get model title for dialog window title.
 */
var getAlternativeModelTitle = function(collection) {
    return collection.attr('data-model-alt-title');
};


/*
 * Support for browsing for backend entities (browse button).
 */
$(document).ready(function () {
    enableModelSupport();
});


}(this));
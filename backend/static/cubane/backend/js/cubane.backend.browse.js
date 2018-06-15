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
var initialIds = []
var browseBtn = null;
var thumbnailBtn = null;
var addBtn = null;
var editBtn = null;
var select = null;


/*
 * Return True, if we are on an create or edit page.
 */
var isCreateOrEditPage = function (iframe) {
    return $(iframe).contents().find('body').hasClass('create-edit-page');
};


/*
 * Clicking on OK within the dialog should receive the ids of all selected
 * element from the dialog before it is closed, which is then used to select
 * the corresponding select option.
 */
var onDialogOK = function (iframe) {
    if (isCreateOrEditPage(iframe)) {
        cubane.backend.submitForm($(iframe).contents().find('form.form-horizontal').get(0));
        return true;
    }

    if (itemJson.length === 1) {
        if (browseBtn && select && select.length > 0) {
            // update select box
            if (select.find('option[value="' + itemJson[0].id + '"]').length === 0) {
                select.append('<option value="' + itemJson[0].id + '">' + itemJson[0].title + '</option>')
                sortSelectOptions(select.get(0));
            }

            // change selected value to the one we selected via 'Browse'
            select.val(itemJson[0].id);

            // re-initialize select2
            if (jQuery().select2) {
                select.select2();
            }

            // trigger onchange event for select dropdown...
            select.trigger('change');
        }

        if (thumbnailBtn) {
            // update hidden input
            var pk = itemJson[0].id
            var input = thumbnailBtn.find('input');
            input.val(pk);

            // load image (in-place)
            thumbnailBtn.addClass('with-image');
            thumbnailBtn.attr('data-pk', pk);
            var imageUrl = cubane.urls.reverse('cubane.media_api.pk', [pk]);
            var imageFrame = thumbnailBtn.find('.cubane-backend-browse-thumbnail-image');
            imageFrame.html('<img src="' + imageUrl + '" alt="">');
            thumbnailBtn.find('.cubane-backend-browse-thumbnail-enlarge').attr('href', imageUrl);
            thumbnailBtn = null;
        }
    }
};


/*
 * Remove thumbnail
 */
var onRemoveThumbnail = function onRemoveThumbnail(e) {
    e.preventDefault();

    var thumbnailBtn = $(e.target).closest('.cubane-backend-browse-thumbnail');
    var input = thumbnailBtn.find('input');
    input.val('');

    thumbnailBtn.removeClass('with-image');
    thumbnailBtn.find('.cubane-backend-browse-thumbnail-image').html('');
};


/*
 * Pre-select current select option within listing of dialog window,
 * after dialog window content has been loaded...
 */
var onDialogLoad = function (iframe) {
    if ( browseBtn ) {
        var w = iframe.get(0).contentWindow;
        var d = w.document;
        w.$(d).trigger('cubane-listing-pre-select', [initialIds]);
    }
};


/*
 * Open index dialog window with given url.
 */
var openIndexDialog = function openIndexDialog(url, isExternal, isSmallDialog) {
    // append dialog argument to url
    if (isExternal) {
        url = cubane.urls.combineUrlArg(url, 'external-dialog', true);
    } else {
        url = cubane.urls.combineUrlArg(url, 'index-dialog', true);
    }

    // small dialog?
    var dialogClasses = [];
    if (isSmallDialog) dialogClasses.push('modal-small');

    // open url in a dialog window...
    var dlg = cubane.dialog.iframe(undefined, url, {
        onClose: onCloseIndexDialog,
        footer: false,
        dialogClasses: dialogClasses
    });

    // remove ok button, since we can only close dialog
    dlg.find('.btn.btn-primary').hide();
};


/*
 * Open general index dialog window
 */
var onOpenIndexDialog = function(e) {
    e.preventDefault();

    var link = $(e.target).closest('.cubane-backend-open-dialog');
    var url = link.attr('href');
    var isExternal = link.hasClass('cubane-backend-open-dialog-external');
    var isSmallDialog = link.hasClass('cubane-backend-open-dialog-small');

    // ignore if this is a regular listing action, this is handled by
    // the listing controller itself...
    if (link.hasClass('cubane-listing-action')) {
        return;
    }

    openIndexDialog(url, isExternal, isSmallDialog);
};


/*
 * Close index dialog
 */
var onCloseIndexDialog = function onCloseIndexDialog(e) {
    // if we are on an index page, simply trigger a refresh, otherwise
    // reload the page...
    var listing = $('.cubane-listing');
    if (listing.length > 0) {
        // trigger refresh (and close dialog window)
        cubane.dialog.closeAll();
        cubane.backend.fetchMessages();
        cubane.backend.ferchSummaryInfo();

        for (var i = 0; i < listing.length; i++) {
            $(window).trigger('cubane-listing-refresh', [listing.eq(i)]);
        }
    } else {
        if (!$('body').hasClass('create-edit-page')) {
            // re-load current page
            window.location.reload();
        } else {
            cubane.dialog.closeAll();
            cubane.backend.fetchMessages();
        }
    }
};


/*
 * Open browse dialog after a browse button was clicked.
 */
var onBrowse = function (e) {
    var modelName, url;
    e.preventDefault();

    if ($(this).closest('.cubane-backend-browse-thumbnail').length > 0) {
        thumbnailBtn = $(this).closest('.cubane-backend-browse-thumbnail');
        var input = thumbnailBtn.find('input');
        initialIds = [input.val()];
        modelName = thumbnailBtn.attr('data-model-name')
        url = thumbnailBtn.attr('data-browse-url');
    } else {
        browseBtn = $(this);
        select = browseBtn.closest('.cubane-backend-browse').find('select');
        initialIds = [select.val()];
        modelName = browseBtn.attr('data-model-name');
        url = browseBtn.attr('data-browse-url');
    }

    // append browse argument to url
    url = cubane.urls.combineUrlArg(url, 'browse', true);

    // open url in a dialog window...
    cubane.dialog.iframe('Browse ' + modelName, url, {
        onOK: onDialogOK,
        onLoad: onDialogLoad
    });
};


/*
 * Open create dialog after a "+" button was clicked.
 */
var onAdd = function (e) {
    e.preventDefault();

    if ($(this).closest('.cubane-backend-browse-thumbnail').length > 0) {
        addBtn = $(this).closest('.cubane-backend-browse-thumbnail');
    } else {
        addBtn = $(this);
        select = addBtn.closest('.cubane-backend-browse').find('select');
    }

    var modelName = addBtn.attr('data-model-name')
    var url = addBtn.attr('data-create-url');

    // append arguments, if given
    var args = addBtn.attr('data-args');
    if (args) {
        url = cubane.urls.combineUrlArgs(url, args);
    }

    // append browse argument to url
    url = cubane.urls.combineUrlArg(url, 'browse', true);

    // append create argument to url
    url = cubane.urls.combineUrlArg(url, 'create', true);

    // open url in a dialog window...
    var dialogClasses = [];
    cubane.dialog.iframe('Create ' + modelName, url, {
        dialogClasses: dialogClasses,
        onOK: function(iframe) {
            cubane.backend.submitForm($(iframe).contents().find('form.form-horizontal').get(0));
            return true;
        }
    });
    $('.modal-iframe .confirm').removeClass('disabled');
};


/*
 * Open edit dialog when clicking edit button
 */
var onEdit = function(e) {
    e.preventDefault();

    editBtn = $(this).closest('.cubane-backend-browse-thumbnail');

    var modelName = editBtn.attr('data-model-name')
    var url = editBtn.attr('data-edit-url');
    var pk = editBtn.attr('data-pk');

    // append pk and edit argument to url
    url = cubane.urls.combineUrlArg(url, 'pk', pk);
    url = cubane.urls.combineUrlArg(url, 'edit', true);

    // open url in a dialog window...
    cubane.dialog.iframe('Edit ' + modelName, url, {
        onOK: function(iframe) {
            cubane.backend.submitForm($(iframe).contents().find('form.form-horizontal').get(0));
            return true;
        }
    });
    $('.modal-iframe .confirm').removeClass('disabled');
}


/*
 * Listing selection update from within dialog window
 */
var onListingSelectionUpdate = function onListingSelectionUpdate(e, json) {
    var btn = $('.modal-iframe .confirm');
    if ( btn.length > 0 ) {
        if ( json.length === 1 ) {
            btn.removeClass('disabled');
        } else {
            btn.addClass('disabled');
        }
    }

    // keep track of selection
    itemJson = json;
};


/*
 * Apply neutral listing selection and make the OK button enabled.
 */
var onListingSelectionNeutral = function onListingSelectionNeutral() {
    var btn = $('.modal-iframe .confirm');
    btn.removeClass('disabled');
};


/*
 * Listing item deleted from within dialog window
 */
var onListingDelete = function(e, ids) {
    if (select) {
        for (var i = 0; i < ids.length; i++) {
            select.find('option[value="' + ids[i] + '"]').remove();
        }
    }
};


/*
 * Entity create form (not submitted yet)
 */
var onListingCreateForm = function (e) {
    $('.modal-iframe .confirm').removeClass('disabled');
}


/*
 * Sort select options of the given select element alphabetically
 */
var sortSelectOptions = function (sel) {
    var opts = [];

    // extract items
    for (var i=sel.options.length-1; i >= 1; i--) {
        opts.push(sel.removeChild(sel.options[i]));
    }

    // sort
    opts.sort(function (a, b) {
        return a.innerText.localeCompare(b.innerText);
    });

    // put items back
    while(opts.length) {
        sel.appendChild(opts.shift());
    }
};


/*
 * Entity created within dialog window
 */
var onListingCreate = function(e, json) {
    if (addBtn) {
        if (addBtn.hasClass('cubane-backend-browse-thumbnail')) {
            // update hidden input
            addBtn.find('input').val(json.id);

            // load image (in-place)
            addBtn.addClass('with-image');
            var imageUrl = cubane.urls.reverse('cubane.cms.images.download') + '?pk=' + json.id;
            var imageFrame = addBtn.find('.cubane-backend-browse-thumbnail-image');
            imageFrame.html('<img src="' + imageUrl + '" alt="">');
            addBtn.find('.cubane-backend-browse-thumbnail-enlarge').attr('href', imageUrl);
        } else if (select && select.length > 0) {
            // add option to the list of options, if it does not exist yet
            if (select.find('option[value="' + json.id + '"]').length === 0) {
                select.append('<option value="' + json.id + '">' + json.title + '</option>')
                sortSelectOptions(select.get(0));
            }

            // select neew option that we've just created...
            select.val(json.id);

            // re-initialize select2
            if (jQuery().select2) {
                select.select2();
            }

            // trigger onchange event for select dropdown...
            select.trigger('change');
        }

        addBtn = null;
        select = null;
    }

    cubane.dialog.closeAll();
};


/*
 * Initialise browse button and "+" button
 */
var enableBrowseSupport = function () {
    // bind events
    $(document).on('click', '.cubane-backend-browse-thumbnail-image', onBrowse);
    $(document).on('click', '.cubane-backend-browse-thumbnail-remove', onRemoveThumbnail);
    $(document).on('click', '.cubane-backend-browse-thumbnail-upload', onAdd);
    $(document).on('click', '.cubane-backend-browse-thumbnail-edit', onEdit);
    $(document).on('click', '.cubane-backend-browse-button > .btn', onBrowse);
    $(document).on('click', '.cubane-backend-browse-add-button > .btn', onAdd);
    $(document).on('click', '.cubane-backend-open-dialog', onOpenIndexDialog);

    $(window).on('cubane-listing-update', onListingSelectionUpdate);
    $(window).on('cubane-listing-neutral', onListingSelectionNeutral);
    $(window).on('cubane-listing-delete', onListingDelete);
    $(window).on('cubane-listing-create-form', onListingCreateForm);
    $(window).on('cubane-listing-create', onListingCreate);
    $(window).on('cubane-close-index-dialog', onCloseIndexDialog);
};


/*
 * Support for browsing for backend entities (browse button).
 */
$(document).ready(function () {
    enableBrowseSupport();
});


/*
 * Allow access to selected item from external
 */
globals.cubane.backend.getItemJson = function() {
    return itemJson;
};

globals.cubane.backend.openIndexDialog = openIndexDialog;


}(this));

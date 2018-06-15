(function (globals){
"use strict";


cubane.namespace('cubane.backend');


cubane.require('cubane.utils');
cubane.require('cubane.urls');
cubane.require('cubane.dialog');


var backendController = undefined;


/*
 * Return the form prefix for the given embedded form and prefix pattern.
 */
function getEmbeddedFormPrefix(embeddedForm, prefixPattern) {
    var seq = embeddedForm.find('.embed-form-seq-index').val();
    return prefixPattern + '_' + seq + '--';
}


/*
 * Submit the given form by creating a submit button and clicking it,
 * rather than using form.submit(). This will execute any on-submit
 * event handlers that may be attached to the form, while form.submit()
 * will not on most browsers.
 */
cubane.backend.submitForm = function submitForm(form) {
    var button = form.ownerDocument.createElement('input');
    button.style.display = 'none';
    button.type = 'submit';
    form.appendChild(button).click();
    form.removeChild(button);
};


/*
 * Backend notification message
 */
cubane.backend.createMessage = function(type, message, change) {
    // create new message popup
    var container = $('.popup-notification-container');
    var undo = change ? (
        '<div class="cubane-undo popup-notification-undo" data-change="' + change + '">Undo</div>'
    ) : '';
    var notification = $(
        '<div class="popup-notification' + (type === 'error' ? ' error' : '') + '">' +
            '<div class="popup-notification-message">' + message + '</div>' +
            undo +
            '<div class="popup-notification-btns">' +
                '<div class="popup-notification-btn view-btn">View</div>' +
                '<div class="popup-notification-btn close-btn">Close</div>' +
            '</div>' +
        '</div>'
    );
    container.append(notification);

    // create new message alert record
    var alertContainer = $('.alert-messages-container');
    var alertMessage = $(
        '<div class="alert alert-' + type + '">' +
            '<div class="alert-icon">' +
                (type === 'error' ?
                    '<svg viewBox="0 0 19 18.8"><use xlink:href="#icon-close"/></svg>' :
                    '<svg viewBox="0 0 27 27.1"><use xlink:href="#icon-tick"/></svg>'
                ) +
            '</div>' +
            '<div class="alter-message-container">' + message + '</div>' +
            (change ? (
                '<div class="cubane-undo alert-undo" data-change="' + change + '">Undo</div>'
            ) : '') +
            '<button type="button" class="close" data-dismiss="alert"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-delete"/></svg>Remove</button>' +
        '</div>'
    );
    alertContainer.append(alertMessage);

    // update number of messages badge
    $('.cms-notifications .badge').text(alertContainer.find('> .alert').length);

    // animate
    setTimeout(function() {
        window.backendController.animateNotifications();
    }, 0);

    // indicate that we have new messages
    $('body').addClass('has-messages');

    // start pulse if we have an error
    var link = $('.cms-notifications');
    if (type === 'error' && !link.hasClass('pulse')) {
        link.addClass('pulse');
        cubane.pulse.place(link);
    }
};


/*
 * Present messages from JSON response.
 */
cubane.backend.presentMessagesFromResponse = function presentMessagesFromResponse(json) {
    if (json) {
        // single message
        if (json.message) {
            cubane.backend.createMessage(
                json.success ? 'success' : 'error',
                json.message,
                json.change
            );
        }

        // multiple messages
        if (json.messages) {
            for (var i = 0; i < json.messages.length; i++) {
                cubane.backend.createMessage(
                    json.messages[i].type,
                    json.messages[i].message,
                    json.messages[i].change
                );
            }
        }
    }
};


/*
 * Load latest system messages from server and present messages in the backend.
 */
cubane.backend.fetchMessages = function fetchMessages() {
    $.post(cubane.urls.reverse('cubane.backend.messages'), function(json) {
        cubane.backend.presentMessagesFromResponse(json);
    }, 'JSON');
};


/*
 * Fetch and update summary information for the current item if we have
 * summary information available.
 */
cubane.backend.ferchSummaryInfo = function ferchSummaryInfo() {
    var summary = $('.summary-items');
    if (summary.length > 0) {
        var pk = summary.attr('data-instance-pk');
        var url = summary.attr('data-fetch-url') + '?pk=' + pk;
        $.post(url, function(html) {
            summary.replaceWith(html);
        })
    }
};


/*
 * Undo given operation and reload page.
 */
cubane.backend.undo = function undo(change, success) {
    var args = {
        'change': change
    };

    cubane.backend.startLoading();
    $.post(cubane.urls.reverse('cubane.backend.undo'), args, function(json) {
        cubane.backend.stopLoading();
        cubane.backend.presentMessagesFromResponse(json);

        if (json.success) {
            cubane.backend.refreshListingsOrPage(json.undo_create);
            if (success) {
                success();
            }
        } else {
            cubane.backend.createMessage('error', json.message)
        }
    }, 'JSON');
};


/*
 * Start indicate loading
 */
cubane.backend.startLoading = function startLoading() {
    $('.cubane-listing').addClass('loading');
};


/*
 * Stop indicate loading
 */
cubane.backend.stopLoading = function stopLoading() {
    $('.cubane-listing.loading').removeClass('loading');
};


/*
 * Enable given from after form submission.
 */
cubane.backend.enableForm = function enableForm(form) {
    var form = $(form).closest('form');

    setTimeout(function() {
        form.removeClass('disabled');
        form.find('input, textarea, select, button').attr('disabled', false);
    }, 100);

    // indicate loading
    var btn = form.find('[type="submit"]');
    btn.find('[class^="icon-"]').show();
    btn.find('i.icon-refresh.icon-spin').remove();
};


/*
 * Present form errors
 */
cubane.backend.presentFormErrors = function presentFormErrors(form, errors) {
    form = $(form);

    cubane.backend.enableForm(form);

    if (errors) {
        // remove any previous errors
        form.find('.control-group.error .help-inline').remove();
        form.find('.control-group.error').removeClass('error');

        // process error messages
        var fieldnames = Object.keys(errors);
        for (var i = 0; i < fieldnames.length; i++) {
            var msg = errors[fieldnames[i]];
            var field = form.find('[name="' + fieldnames[i] + '"]');
            if (field) {
                var group = field.closest('.control-group');
                group.addClass('error');
                group.find('.controls').append('<div class="help-inline">' + msg + '</div>');
            }
        }
    }
};


/*
 * Refresh all listings
 */
cubane.backend.refreshListingsOrPage = function refreshListings(backToListing) {
    if (backToListing === undefined) backToListing = false;

    var listings = $('.cubane-listing');
    if (listings.length > 0) {
        cubane.backend.fetchMessages();

        for (var i = 0; i < listings.length; i++) {
            var listing = listings.eq(i);

            // update listing
            $(window).trigger('cubane-listing-refresh', [listing]);

            // update tree?
            if (listing.hasClass('with-folders')) {
                $(window).trigger('cubane-tree-refresh');
            }
        }
    } else {
        if (backToListing) {
            // go back to index page
            var href = window.location.href;
            var path = href.split('?')[0];
            var parts = href.split('/');
            var index = parts.slice(0, parts.length - 2).join('/') + '/';
            window.location.href = index;
        } else {
            // reload current window
            window.location.reload();
        }
    }
};


/*
 * Copy arbitary text to the user's clipboard.
 * Based on: https://stackoverflow.com/questions/400212/how-do-i-copy-to-the-clipboard-in-javascript
 */
cubane.backend.copyTextToClipboard = function copyTextToClipboard(text) {
    var textArea = document.createElement("textarea");
    textArea.style.position = 'fixed';
    textArea.style.top = 0;
    textArea.style.left = 0;
    textArea.style.width = '2em';
    textArea.style.height = '2em';
    textArea.style.padding = 0;
    textArea.style.border = 'none';
    textArea.style.outline = 'none';
    textArea.style.boxShadow = 'none';
    textArea.style.background = 'transparent';
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();

    try {
        document.execCommand('copy');
    } catch (err) {}

    document.body.removeChild(textArea);
};


cubane.backend.downloadWithEncoding = function downloadWithEncoding(url, title, btnLabel) {
    if (title === undefined) title = 'Download File';
    if (btnLabel === undefined) btnLabel = title + '...';

    // create dialog window for choosing encoding
    var dialogUrl = cubane.urls.reverse('cubane.backend.download_with_encoding');
    dialogUrl = cubane.urls.combineUrlArg(dialogUrl, 'browse', true);
    dialogUrl = cubane.urls.combineUrlArg(dialogUrl, 'create', true);

    function _post(action) {
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

        // submit form
        form.insertAfter(a);
        form.submit();
    }

    // open dialog window
    cubane.dialog.iframe(title, dialogUrl, {
        dialogClasses: ['modal-small'],
        okBtnLabel: btnLabel,
        okBtnIcon: 'icon-download',
        closeBtn: false,
        onOK: function(iframe) {
            var form = $(iframe).contents().find('form');
            var encoding = form.find('#id_encoding').val();
            var downloadUrl = cubane.urls.combineUrlArg(
                url,
                'encoding',
                encoding
            );
            window.location.href = downloadUrl;
            return false;
        }
    });
};


/*
 * Provides user-friendly backend UI by improving form usability, auto-focus
 * form fields etc.
 */
cubane.backend.BackendController = function () {
    this.bound = {
        onTabSwitched: $.proxy(this.onTabSwitched, this),
        onFormSubmit: $.proxy(this.onFormSubmit, this),
        onAlertClosed: $.proxy(this.onAlertClosed, this),
        onToggleMessages: $.proxy(this.onToggleMessages, this),
        onDismissMessages: $.proxy(this.onDismissMessages, this),
        onUndoClicked: $.proxy(this.onUndoClicked, this),
        onEditDialogClicked: $.proxy(this.onEditDialogClicked, this),
        onEditDialogCompleted: $.proxy(this.onEditDialogCompleted, this),
        onFormSaveAndContinue: $.proxy(this.onFormSaveAndContinue, this),
        onFormCancel: $.proxy(this.onFormCancel, this),
        onFormStep: $.proxy(this.onFormStep, this),
        onFormResize: $.proxy(this.onFormResize, this),
        onFormLoad: $.proxy(this.onFormLoad, this),
        onFormWithVisibilityRulesChanged: $.proxy(this.onFormWithVisibilityRulesChanged, this),
        onFormWithBlueprintRulesChanged: $.proxy(this.onFormWithBlueprintRulesChanged, this),
        onFormWithLimitRulesChanged: $.proxy(this.onFormWithLimitRulesChanged, this),
        onOffCanvasNavToggle: $.proxy(this.onOffCanvasNavToggle, this),
        onCloseOffCanvasNav: $.proxy(this.onCloseOffCanvasNav, this),
        onNavStepSelectChange: $.proxy(this.onNavStepSelectChange, this),
        onNavStepChange: $.proxy(this.onNavStepChange, this),
        onPrintPage: $.proxy(this.onPrintPage, this),
        onAlertMessageLink: $.proxy(this.onAlertMessageLink, this),
        onNotifications: $.proxy(this.onNotifications, this),
        onCloseNotifications: $.proxy(this.onCloseNotifications, this),
        onClosePopupNotifications: $.proxy(this.onClosePopupNotifications, this),
        onDialogInit: $.proxy(this.onDialogInit, this),
        onInitControls: $.proxy(this.onInitControls, this),
        onDownloadWithEncodingClicked: $.proxy(this.onDownloadWithEncodingClicked, this),
        onBtnSummaryItemsClicked: $.proxy(this.onBtnSummaryItemsClicked, this)
    };

    this.enableSelect2();
    this.externalLinks();
    this.showFirstTabOrError();
    this.focusFirstInputField();
    this.focusFirstInputFieldWhenSwitchingTabs();
    this.lazyLoadImagesWhenSwitchingTabs();
    this.setupForm();
    this.disableFormWhileSubmitting();
    this.autoSlugify();
    this.alertMessagesContainer();
    this.autoEditDialog();
    this.onFormResize();
    this.onFormLoad();
    this.showPhoneOnLoginScreen();
    this.stopAutoCapsOnLoginForm();
    this.postConfirm();
    this.autoPulse();
    this.autoEnableTinyMCE('textarea.editable-html');
    this.autoEnableTinyMCE('textarea.many-editable-html');
    this.notifications();
    this.animateNotifications();
    this.enableDatepicker();
    this.enableTimepicker();
    this.enableShareMedia();
    this.enableColorPicker();
    this.evaluateAllLimitsForForms();

    $(document).on('click', '.nav-steps a', this.bound.onFormStep);
    $(window).on('resize', this.bound.onFormResize);
    $(document).on('click', '#offcanvas-nav-toggle', this.bound.onOffCanvasNavToggle);
    $(document).on('click', '.close-nav', this.onCloseOffCanvasNav);
    $(document).on('change', '#phone-nav-steps', this.bound.onNavStepSelectChange);
    $(document).on('click', '.nav-steps > li > a', this.bound.onNavStepChange);
    $(document).on('click', '.print-page', this.bound.onPrintPage);
    $(document).on('click', '.alert-messages .alert a', this.bound.onAlertMessageLink);
    $(document).on('click', '.cubane-undo', this.bound.onUndoClicked);
    $(document).on('cubane-dialog-init', this.bound.onDialogInit);
    $(document).on('change keyup cubane-listing-item-edit-changed', 'form[data-visibility-rules], .embed-forms[data-visibility-rules]', this.bound.onFormWithVisibilityRulesChanged);
    $(document).on('change', 'form[data-blueprint-rules] select, .embed-forms[data-blueprint-rules] select', this.bound.onFormWithBlueprintRulesChanged);
    $(document).on('keyup', 'form[data-limit-rules] input, form[data-limit-rules] textarea', this.bound.onFormWithLimitRulesChanged);
    $(document).on('click', '.download-with-encoding', this.bound.onDownloadWithEncodingClicked);
    $(document).on('init-controls', this.bound.onInitControls);
    $(document).on('click', '.btn-summary-items', this.bound.onBtnSummaryItemsClicked);
};

cubane.backend.BackendController.prototype = {
    dispose: function() {
        $('a[data-toggle="tab"]').off('shown', this.bound.onTabSwitched);
        $('#phone-nav-steps').off('change', this.bound.onTabSwitched);
        $('form').off('submit', this.bound.onFormSubmit);
        $(document).off('click', '.alert-messages > .alert > button', this.bound.onAlertClosed);
        $(document).off('click', '.alert-messages', this.bound.onToggleMessages);
        $('.alert-messages-close-all').off('click', this.bound.onDismissMessages);
        $(document).off('click', '.open-edit-dialog', this.bound.onEditDialogClicked);
        $(window).off('cubane-listing-edit', this.bound.onEditDialogCompleted);
        $('.btn-save-and-continue').off('click', this.bound.onFormSaveAndContinue);
        $('.btn-cancel').off('click', this.bound.onFormCancel);
        $(document).off('click', '.nav-steps a', this.bound.onFormStep);
        $(window).off('resize', this.bound.onFormResize);
        $(document).off('click', '#offcanvas-nav-toggle', this.bound.onOffCanvasToggle);
        $(document).off('click', '.close-nav', this.onCloseOffCanvasNav);
        $(document).off('change', '#phone-nav-steps', this.bound.onNavStepSelectChange);
        $(document).off('click', '.nav-steps > li > a', this.bound.onNavStepChange);
        $(document).off('click', '.print-page', this.bound.onPrintPage);
        $(document).off('click', '.alert-messages .alert > a', this.bound.onAlertMessageLink);
        $(document).off('click', '.cms-notifications', this.bound.onNotifications);
        $(document).off('click', '.popup-notification-btn.view-btn', this.bound.onNotifications);
        $(document).off('click', '.notifications-messages-overlay', this.bound.onCloseNotifications);
        $(document).off('click', '.popup-notification-btn.close-btn', this.bound.onClosePopupNotifications);
        $(document).off('cubane-dialog-init', this.bound.onDialogInit);
        $(document).off('change keyup cubane-listing-item-edit-changed', 'form[data-visibility-rules], .embed-forms[data-visibility-rules]', this.bound.onFormWithVisibilityRulesChanged);
        $(document).off('change', 'form[data-blueprint-rules] select, .embed-forms[data-blueprint-rules] select', this.bound.onFormWithBlueprintRulesChanged);
        $(document).off('keyup', 'form[data-limit-rules] input, form[data-limit-rules] textarea', this.bound.onFormWithLimitRulesChanged);
        $(document).off('click', '.download-with-encoding', this.bound.onDownloadWithEncodingClicked);
        $(document).off('init-controls', this.bound.onInitControls);
        $(document).off('click', '.btn-summary-items', this.bound.onBtnSummaryItemsClicked);
        this.bound = null;
    },


    /*
     * Open external links in a new tab.
     */
    externalLinks: function() {
        $('[rel="external"]').each(function () {
            $(this).attr('target', '_blank');
        });
    },


    /*
     * Select first tab of each tab control of the first tab that has a form
     * field with an error if there are any errors.
     */
    showFirstTabOrError: function (tabContainer) {
        if ( tabContainer === undefined ) {
            var tabs = $('.nav-tabs');
            for ( var i = 0; i < tabs.length; i++ ) {
                this.showFirstTabOrError(tabs.eq(i));
            }
        } else {
            if ( tabContainer.parent().find('.error').length > 0 ) {
                // scan through all tabs and find the one that has an error
                var ids = [];
                var tabSelected = false;
                tabContainer.find('li > a').each(function() {
                    ids.push($(this).attr('href').replace('#', ''));
                });
                for ( var i = 0; i < ids.length; i++ ) {
                    var tab = $('#' + ids[i]);
                    var n = tab.find('.error').length;
                    var a = tabContainer.find('li').eq(i).find('a');

                    if ( n > 0 ) {
                        // select first tab with error
                        if ( !tabSelected ) {
                            a.tab('show');
                            tabSelected = true;
                        }

                        // annotate tabs with errors
                        if ( n > 0 ) {
                            a.append('<span class="badge badge-important">' + n + '</span>');
                        }
                    } else {
                        var step = a.find('.nav-tab-step');
                        step.addClass('visited');
                    }
                }
            } else {
                // no errors -> show first tab
                tabContainer.find('li:first > a').tab('show');
            }

            document.lazyloadImages();
        }
    },


    /*
     * Give focus to the first visible input field or the first input field with
     * an error on the screen.
     */
    focusFirstInputField: function(base, embeddedForm) {
        // return if on tablet or phone
        if (window.innerWidth < 979) return;
        if (base === undefined) base = $('.content');
        if (embeddedForm === undefined) embeddedForm = true;

        // potential (visible) form fields to focus
        var fields = base
            .find('input, textarea, select')
            .not('.disabled')
            .not('[type="submit"], [type="reset"], [type="file"]')
            .filter(':visible, .editable-html');

        // is there a visible error on the page? -> only consider error fields
        if ( base.find('.error:visible').length > 0 ) {
            fields = fields.filter(function() {
                // has error but not within an embedded form
                return $(this).closest('.error').length > 0 && $(this).closest('.embed-form').length === 0;
            });
        }

        // get first field
        var field = fields.first();

        // is the containing form labeled as focus-empty-only?
        var form = field.closest('form');
        if (form.hasClass('focus-empty')) {
            // select first field that is non-empty
            for (var i = 0; i < fields.length; i++) {
                if (fields.eq(i).val() === '') {
                    field = fields.eq(i);
                    break;
                }
            }
        }

        // got field?
        if (field.length === 0)
            return;

        // field must not be within an embedded form...
        if (field.closest('.embed-form').length > 0 && !embeddedForm) {
            return;
        }

        // different types of field may receive focus differently...
        if ( field.hasClass('editable-html') ) {
            // focus tinymce editor
            if ( tinymce ) {
                var f = tinymce.get(field.attr('id'));
                if ( f ) f.focus();
            }
        } else if (field.get(0).nodeName.toLowerCase() == 'select' && jQuery().select2) {
            // open drop down if we have an embedded form, otherwise simply
            // focus it.
            if (field.closest('.embed-form').length > 0) {
                field.select2('open');
            } else {
                field.select2('focus');
            }
        } else {
            // give focus to first field
            field.focus();
        }
    },


    /*
     * Focus first input field on the screen after switching tabs.
     */
    focusFirstInputFieldWhenSwitchingTabs: function () {
        $('a[data-toggle="tab"]').on('shown', this.bound.onTabSwitched);
        $('#phone-nav-steps').on('change', this.bound.onTabSwitched);
    },


    /*
     * Lazy-load images whenever we switch tabs.
     */
    lazyLoadImagesWhenSwitchingTabs: function lazyLoadImagesWhenSwitchingTabs() {
        $(document).on('cubane-tab-switched', function() {
            if (document.lazyloadImages) {
                document.lazyloadImages();
            }
        });
    },


    /*
     * Add 'Save and Continue' button and make cancel button go back to
     * listing.
     */
    setupForm: function () {
        // turn off html5 native validation
        var form = $('form.form-horizontal');
        if (form.length > 0) {
            form.get(0).noValidate = true;
        }

        // buttons
        $('.btn-save-and-continue').on('click', this.bound.onFormSaveAndContinue);
        $('.btn-cancel').on('click', this.bound.onFormCancel);
    },


    /*
     * Disable a form while submitting it.
     */
    disableFormWhileSubmitting: function () {
        // disable form when submitting
        $('form:not(.no-form-disable)').on('submit', this.bound.onFormSubmit);
    },


    /*
     * Provide facility to slugify certain input fields automatically.
     */
    autoSlugify: function () {
        // when editing a slugify field, the corresponding slug should be updated automatically,
        // unless the user started to edit the slug field or the slug field was not empty to begin with
        $('form').each(function() {
            var form = $(this);
            if ( form.closest('.cubane-listing-filter').length > 0 ) return;

            if ( form.find('.slug').val() == '' ) {
                var slugEdited = false;
                form.find('.slugify').keyup(function() {
                    if ( slugEdited === false ) {
                        var slug = form.find('.slug');
        	            slug.val(cubane.utils.slugify($(this).val()))
                        slug.change();
        	        }
                });
                form.find('.slug').keyup(function() {
                    slugEdited = true;
                });
            }

            // after changing the slug field, automatically slugify it
            form.find('.slug').change(function() {
                $(this).val(cubane.utils.slugify($(this).val()));
            });

            // provide a button for (re-)generating the slug based on the title.
            var btn = $('<span class="btn field-addon">Generate</span>');
            var field = form.find('.slug').closest('.field').addClass('with-addon-button');
            btn.insertAfter(field);
            btn.bind('click', function(e) {
                e.preventDefault();
                $(this).prev('.field').find('.slug').val(
                    cubane.utils.slugify(
                        form.find('.slugify').val()
                    )
                );
            });

            // after changing an identifier field, automatically make an identifier
            form.find('.make-identifier').change(function() {
                $(this).val(cubane.utils.makeIdentifier($(this).val()));
            });
        });
    },


    /*
     * Automatically close alert message container if we close all messages.
     * Also closes alert message container if we press the "Dismiss Messages"
     * button. Clicking on the message container itself enlarges/collapses it.
     */
    alertMessagesContainer: function () {
        $(document).on('click', '.alert-messages-container > .alert > button', this.bound.onAlertClosed);
        $('.alert-messages-close-all').on('click', this.bound.onDismissMessages);
        $(document).on('click', '.alert-messages', this.bound.onToggleMessages);
    },


    /*
     * Open link if clicked inside of alert.
     */
    onAlertMessageLink: function(e) {
        if ($(e.target).attr('href')) {
            window.open($(e.target).attr('href'), '_blank')
        } else {
            window.open($(e.target).closest('a').attr('href'), '_blank')
        }
    },


    /*
     * Automatically open .edit-dialog links and/or buttons within a dialog
     * window
     */
    autoEditDialog: function () {
        $(document).on('click', '.open-edit-dialog', this.bound.onEditDialogClicked);
        $(window).on('cubane-listing-edit', this.bound.onEditDialogCompleted);
    },


    /*
     * Enable select2 select fields, if available
     */
    enableSelect2: function() {
        // test if select2 jquery plugin is available
        if (!jQuery().select2) return;

        // ordinary select with auto-completion, select with multi-select
        // becomes tag selection...
        $('select').filter(function() {
            return $(this).closest('.embed-form-template').length === 0;
        }).select2();
    },


    /*
     * Enable date-picker control for date fields.
     */
    enableDatepicker: function() {
        $('.date-field input').datepicker({
            format: 'dd/mm/yyyy',
            todayHighlight: true
        });
        $(document).on('click', '.date-field .add-on', function() {
            $(this).prev('input').focus();
        });
    },


    /*
     * Enable time-picker control for time fields.
     */
    enableTimepicker: function() {
        $('.time-field input').timepicker({
            template: false,
            showWidgetOnFocus: false,
            defaultTime: false
        });
        $(document).on('click', '.time-field .add-on', function() {
            $(this).prev('input').timepicker('showWidget');
        });
    },


    /*
     * Event handler for making disabled links non-clickable.
     */
    onDisabledLinkClicked: function (e) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    },


    /*
     * Event handler for switching tabs and re-focus input field within the
     * new tab.
     */
    onTabSwitched: function (e) {
        var _id;
        if (e.target.id == 'phone-nav-steps') {
            _id = $(e.target).val();
        } else {
            _id = $(e.target).attr('href');
        }

        _id = _id.replace('#', '')
        var tab = $('#' + _id);

        this.focusFirstInputField(tab, false);
        $(document).trigger('cubane-tab-switched');
    },


    /*
     * Event handler for disabling a form while submitting it.
     */
    onFormSubmit: function (e) {
        // ignore if this is a filter form as part of a listing control
        if ( $(e.target).closest('.cubane-listing-filter').length > 0 )
            return;

        // fire event, so that other components have a chance to prepare for
        // form submission...
        $(document).trigger('cubane-form-submit');

        // disable form elements. We have to do this deferred, since otherwise
        // the browser will not send the data.
        var form = $(e.target).closest('form');
        setTimeout(function() {
            form.addClass('disabled');
            form.find('input, textarea, select, button').attr('disabled', true);
        }, 100);

        // indicate loading
        var btn = form.find('[type="submit"]');
        btn.find('[class^="icon-"]').hide();
        btn.prepend('<i class="icon-refresh icon-spin"></i> ');
    },


    /*
     * Event handler for closing alert message boxes. Should close alert message
     * container automatically, once the last alert message was closed.
     */
    onAlertClosed: function (e) {
        var n = $('.alert-messages-container > .alert').length;
        $('.cms-notifications span').text(n);
        if ( n == 0 ) {
            $('body').removeClass('has-messages');
            $('.content').removeClass('show-messages');
            $('.cms-notifications').removeClass('pulse');
        }
    },


    /*
     * Clicking on the message container enlarges or collapses it.
     */
    onToggleMessages: function (e) {
        e.preventDefault();

        var messages = $(e.target).closest('.alert-messages');
        messages.toggleClass('expanded');
    },


    /*
     * Event handler for clicking on the "Dismiss Messages" button for closing
     * the alert message container and dismissing all alert messages at once.
     */
    onDismissMessages: function (e) {
        e.preventDefault();
        $('.content').removeClass('show-messages');
        $('.cms-notifications').removeClass('pulse');
    },


    /*
     * Event handler for clicking on a button or anker with the class
     * .open-edit-dialog which should open the link within a new dialog window.
     */
    onEditDialogClicked: function (e) {
        e.preventDefault();

        var a = $(e.target).closest('.open-edit-dialog');
        var url = a.attr('href');

        url = cubane.urls.combineUrlArg(url, 'browse', true);
        url = cubane.urls.combineUrlArg(url, 'edit', true);

        cubane.dialog.iframe(a.attr('title'), url, {
            onLoad: function(iframe) {
                $('.modal-iframe .confirm').removeClass('disabled');
            },
            onOK: function(iframe) {
                $(iframe).contents().find('form:last').submit();
                return true;
            }
        });
    },


    /*
     * Triggered by child iframe to signal completion of an edit operation
     * that was initiated by clicking an .open-edit-dialog button/anker.
     */
    onEditDialogCompleted: function (e) {
        cubane.dialog.closeAll();
    },


    /*
     * Clicking on 'save and continue' should save the form but then stay on the
     * page rather than redirecting back to the listing page.
     */
    onFormSaveAndContinue: function (e) {
        // inject hidden field to trigger save and continue (by default we
        // would redirect back to the listing page).
        var form = $(e.target).closest('form');
        var value;
        var activeTab = $('.nav-tabs .active > a');

        if (activeTab.length > 0) {
            value = activeTab.attr('href').replace('#', '#nav-step-');
        } else {
            value = '#1';
        }

        form.append('<input type="hidden" name="cubane_save_and_continue" value="' + value + '"/>');
    },


    /*
     * Clicking on 'cancel' should go back to the listing page.
     */
    onFormCancel: function (e) {
        e.preventDefault();

        // inject hidden field to trigger redirect to corresponding index page
        var form = $(e.target).closest('form');
        form.append('<input type="hidden" name="cubane_form_cancel" value="1"/>');
        form.get(0).submit();
    },


    onFormStep: function (e) {
        var step = $(e.target).find('.nav-tab-step');
        if (step.length < 1) step = $(e.target);

        step.addClass('visited');
    },


    /*
     *
     */
    onFormResize: function () {
        if (window.innerWidth == 0)
            return;

        var steps = $('.nav-steps li');
        var numberOfStepsPerRow = Math.floor(window.innerWidth / 170);
        var numberOfRows = Math.floor(steps.length / numberOfStepsPerRow);
        var extraWidth = window.innerWidth - (170 * numberOfStepsPerRow);

        if (steps.length > numberOfStepsPerRow) {
            for (var i = 0; i < steps.length; i++) {
                var extraLine = $(steps[i - 1]).find('.extra-line');
                if (this.isStepAtEnd(i, steps.length, numberOfRows, numberOfStepsPerRow)) {
                    extraLine.css({
                        width: extraWidth
                    });
                } else {
                    extraLine.css({
                        width: 0
                    });
                }
            }
        } else {
            $('.nav-steps li .extra-line').css({
                width: 0
            });
        }
    },


    onFormLoad: function () {
        // change first visible tab based on hash
        var hash = window.location.hash.substr(1);
        if (hash) {
            hash = '#' + hash.replace('nav-step-', '');
            var firstStep = $('.nav-steps .nav-tab-step.visited');
            if (firstStep.closest('a').attr('href') !== hash) {
                firstStep.removeClass('visited');
            }

            this.changeNavStep(hash);
            this.changeNavStepSelectOption(hash);
        }

        // evaluate visibility rules after page has been loaded....
        this.onFormWithVisibilityRulesChanged();
    },


    /*
     * Triggered whenever a form with visibility rules has been changed.
     */
    onFormWithVisibilityRulesChanged: function(e) {
        function isPredicateTrue(form, predicate, prefix) {
            if (prefix === undefined) prefix = '';

            if (predicate) {
                var fieldname = predicate.f;
                var fieldvalue = predicate.v;
                var compare = predicate.c;
                if (fieldname && fieldvalue !== undefined) {
                    var field = form.find('[name="' + prefix + fieldname + '"]');

                    // if the form field does not exist, then ignore this rule
                    // and return true; so that we are not ending up with hidden
                    // fields...
                    if (field.length === 0) {
                        return true;
                    }

                    // get current value
                    var currentValue;
                    if (field.is(':checkbox')) {
                        currentValue = field.is(':checked');
                    } else if (field.is(':radio')) {
                        currentValue = field.filter(':checked').val();
                    } else {
                        currentValue = field.val();
                    }

                    // convert to integer if expected value is integer too
                    if (Number.isInteger(fieldvalue) && !Number.isInteger(currentValue)) {
                        currentValue = parseInt(currentValue);
                    }

                    // compare with expected value depending on
                    // method of comparison...
                    var result = false;
                    if (compare == '==') {
                        result = currentValue == fieldvalue;
                    } else if (compare == '!=') {
                        result = currentValue != fieldvalue;
                    } else if (compare == '>') {
                        result = currentValue > fieldvalue;
                    } else if (compare == '>=') {
                        result = currentValue >= fieldvalue;
                    } else if (compare == '<') {
                        result = currentValue < fieldvalue;
                    } else if (compare == '<=') {
                        result = currentValue <= fieldvalue;
                    }

                    return result
                }
            }

            // default
            return false;
        }

        function arePredicatesTrue(form, predicates, prefix) {
            for (var k = 0; k < predicates.length; k++) {
                if (!isPredicateTrue(form, predicates[k], prefix)) {
                    return false;
                }
            }
            return true;
        }

        function predicateContainsFieldRef(predicates, targetName) {
            if (predicates && targetName) {
                for (var i = 0; i < predicates.length; i++) {
                    if (predicates[i].f === targetName) {
                        return true;
                    }
                }
            }

            return false;
        }

        function extendFieldList(resultList, fieldList) {
            if (fieldList) {
                for (var i = 0; i < fieldList.length; i++) {
                    if (resultList.indexOf(fieldList[i]) === -1) {
                        resultList.push(fieldList[i]);
                    }
                }
            }
        }

        function extendFields(fields, rules, visible) {
            if (rules.v) {
                // result maintains list of keys (in order)
                if (!('__keys' in fields)) {
                    fields.__keys = [];
                }

                // extract list of field names
                var fieldnames = [];
                for (var i = 0; i < rules.p.length; i++) {
                    fieldnames.push(rules.p[i].f);
                }

                // If any existing rule is rendering any component invisible,
                // then we simply ignore this rule, since the field will be
                // invisible to begin with...
                for (var i = 0; i < fieldnames.length; i++) {
                    var fieldname = fieldnames[i];
                    for (var j = 0; j < fields.__keys.length; j++) {
                        var key = fields.__keys[j];
                        if (fields[key].hidden.indexOf(fieldname) !== -1) {
                            return;
                        }
                    }
                }

                // add unique field reference to result.
                var key = fieldnames.join('-');
                if (!(key in fields)) {
                    fields[key] = {
                        visible: [],
                        hidden: []
                    }

                    fields.__keys.push(key);
                }

                // add visibility instructions to result
                var bucket = visible ? 'visible' : 'hidden';
                for (var i = 0; i < rules.v.length; i++) {
                    if (fields[key][bucket].indexOf(rules.v[i]) === -1) {
                        fields[key][bucket].push(rules.v[i]);
                    }
                }
            }
        }

        function setVisibilityForField(field, visible) {
            var group = field.closest('.control-group');
            if (visible) {
                group.removeClass('control-group-visibility-rule-hidden');
            } else {
                group.addClass('control-group-visibility-rule-hidden');
            }
        }

        function getFieldByName(form, prefix, fieldname) {
            if (prefix === undefined) prefix = '';

            var field = form.find('[name="' + prefix + fieldname + '"]');

            // some fields may only present some information and may not
            // have a regular input field. Try to find the field by
            // it's group container
            if (field.length === 0) {
                field = form.find('.control-group.control-group-' + fieldname);
            }

            return field;
        }

        function setVisibilityForFields(form, fieldnames, visible, prefix) {
            if (prefix === undefined) prefix = '';

            for (var i = 0; i < fieldnames.length; i++) {
                var field = getFieldByName(form, prefix, fieldnames[i]);
                if (field.length > 0) {
                    setVisibilityForField(field, visible);
                }
            }
        }

        function isSectionEmpty(section) {
            var group = section.next('.control-group');
            while (group.length > 0 && group.find('.form-section').length == 0) {
                if (!group.hasClass('control-group-visibility-rule-hidden')) {
                    return false;
                }

                group = group.next('.control-group');
            }

            return true;
        }

        function updateSectionVisibility(form) {
            var sections = form.find('.form-section').parent('.control-group');
            for (var i = 0; i < sections.length; i++) {
                var section = sections.eq(i);
                if (isSectionEmpty(section)) {
                    section.addClass('control-group-visibility-rule-hidden');
                } else {
                    section.removeClass('control-group-visibility-rule-hidden');
                }
            }
        }

        function clearFieldByName(form, prefix, fieldname) {
            if (prefix === undefined) prefix = '';

            var field = getFieldByName(form, prefix, fieldname);
            if (field.length > 0) {
                field.val('');
            }
        }

        function evaluateVisibilityRules(form, visibilityRules, prefix, targetName) {
            // determine hidden and visible fields
            var fields = {};
            var fieldnamesToClear = [];
            for (var i = 0; i < visibilityRules.length; i++) {
                var visibilityRule = visibilityRules[i];
                if (visibilityRule && visibilityRule.p) {
                    var predicatesTrue = arePredicatesTrue(form, visibilityRule.p, prefix);
                    extendFields(
                        fields,
                        visibilityRule,
                        predicatesTrue
                    );

                    if (predicatesTrue && predicateContainsFieldRef(visibilityRule.p, targetName)) {
                        extendFieldList(fieldnamesToClear, visibilityRule.c);
                    }
                }
            }

            // update visibility
            for (var i = 0; i < fields.__keys.length; i++) {
                var key = fields.__keys[i];
                setVisibilityForFields(form, fields[key]['hidden'], false, prefix);
                setVisibilityForFields(form, fields[key]['visible'], true, prefix);
            }

            // make empty sections hidden, non-empty sections visible
            updateSectionVisibility(form);

            // clear fields
            for (var i = 0; i < fieldnamesToClear.length; i++) {
                clearFieldByName(form, prefix, fieldnamesToClear[i]);
            }
        }

        function evaluateForm(form, targetName) {
            var visibilityJson = form.attr('data-visibility-rules');
            if (visibilityJson) {
                var visibilityRules = JSON.parse(visibilityJson);
                if (visibilityRules) {
                    evaluateVisibilityRules(form, visibilityRules, undefined, targetName);
                }
            }
        }

        function evaluateEmbeddedForm(embeddedForm) {
            var container = embeddedForm.closest('.embed-forms[data-visibility-rules]');
            if (container.length > 0) {
                var visibilityJson = container.attr('data-visibility-rules');
                if (visibilityJson) {
                    var visibilityRules = JSON.parse(visibilityJson);
                    if (visibilityRules) {
                        var prefixPattern = container.attr('data-prefix-pattern');
                        var prefix = getEmbeddedFormPrefix(embeddedForm, prefixPattern);
                        evaluateVisibilityRules(embeddedForm, visibilityRules, prefix);
                    }
                }
            }
        }

        function evaluateEmbeddedForms(containers) {
            for (var i = 0; i < containers.length; i++) {
                var container = containers.eq(i);
                var visibilityJson = container.attr('data-visibility-rules');
                if (visibilityJson) {
                    var visibilityRules = JSON.parse(visibilityJson);
                    if (visibilityRules) {
                        var embeddedForms = container.find('.embed-form');
                        var prefixPattern = container.attr('data-prefix-pattern');
                        for (var j = 0; j < embeddedForms.length; j++) {
                            var embeddedForm = embeddedForms.eq(j);
                            var prefix = getEmbeddedFormPrefix(embeddedForm, prefixPattern);
                            evaluateVisibilityRules(embeddedForm, visibilityRules, prefix);
                        }
                    }
                }
            }
        }

        // determine target field
        var target = e ? e.target : undefined;
        var targetName = target && target.name ? target.name : undefined;

        // parse visibility rules on forms
        var forms = $('form[data-visibility-rules]');
        for (var i = 0; i < forms.length; i++) {
            evaluateForm(forms.eq(i), targetName);
        }

        // embedded forms
        if (e) {
            // check visibility rules on embedded form that triggered change
            var embeddedForm = $(e.target).closest('.embed-form');
            if (embeddedForm.length > 0) {
                evaluateEmbeddedForm(embeddedForm);
            }
        } else {
            // check visibility for all forms
            evaluateEmbeddedForms($('.embed-forms[data-visibility-rules]'));
        }
    },


    /*
     * Triggered whenever a select drop down changed in order to apply blueprint
     * rules for the corresponding form or embedded form.
     */
    onFormWithBlueprintRulesChanged: function(e) {
        function evaluateForm(form, fieldName, pk, rules, prefix) {
            if (prefix === undefined) prefix = '';

            if (prefix && fieldName.indexOf(prefix) === 0) {
                fieldName = fieldName.substr(prefix.length);
            }

            var rules = rules[fieldName];
            if (rules) {
                // make ajax request to REST API in order to fetch the
                // current object
                var url = cubane.urls.reverse('cubane.backend.api.db.get', [rules.model, pk]);
                $.getJSON(url, function(json) {
                    if (json.success) {
                        for (var i = 0; i < rules.fields.length; i++) {
                            var refName = rules.fields[i];
                            if (refName) {
                                var remoteName = refName;

                                // split ref. name into local and remote
                                if (refName.indexOf('=') !== -1) {
                                    var p = refName.split('=', 2);
                                    refName = p[0].trim();
                                    remoteName = p[1].trim();
                                }

                                var fieldName = prefix + refName;
                                var field = form.find('[name="' + fieldName + '"]');
                                if (field.length > 0) {
                                    var refValue = json.result[remoteName];
                                    if (refValue === undefined) refValue = json.result[remoteName + '_id'];

                                    if (refValue !== undefined) {
                                        // null becomes empty
                                        if (refValue === null) refValue = '';

                                        // change field value. different types
                                        // of field may receive focus
                                        // differently...
                                        if (field.hasClass('editable-html')) {
                                            var editor = tinymce.get(field.attr('id'));
                                            editor.setContent(refValue);
                                        } else if (field.attr('type') == 'checkbox') {
                                            field.prop('checked', refValue).trigger('change');
                                        } else {
                                            field.val(refValue).trigger('change');
                                        }
                                    }
                                }
                            }
                        }
                    }
                });
            }
        }

        // apply blueprint rules to form or embedded form
        var select = $(e.target).closest('select');
        var form = select.closest('.embed-form');
        var blueprintRules;
        var prefix;
        if (form.length > 0) {
            var container = form.closest('.embed-forms');
            blueprintRules = container.attr('data-blueprint-rules');
            var prefixPattern = container.attr('data-prefix-pattern');
            prefix = getEmbeddedFormPrefix(form, prefixPattern);
        } else {
            form = select.closest('form');
            blueprintRules = form.attr('data-blueprint-rules');
        }

        // parse JSON and evaluate
        if (blueprintRules) {
            blueprintRules = JSON.parse(blueprintRules);
            evaluateForm(form, select.attr('name'), select.val(), blueprintRules, prefix);
        }
    },


    /*
     * Update form limits for all fields or a specific field (if given).
     */
    evaluateLimits: function(form, input, rules, prefix) {
        function updateRuleInfo(input, message, tooMany) {
            var field = input.closest('.field');
            var limitContainer = field.next('.field-limit');
            if (limitContainer.length == 0) {
                limitContainer = $('<div class="field-limit"></div>');
                field.after(limitContainer);
            }

            limitContainer.html(message);
            if (tooMany) {
                limitContainer.addClass('field-limit-too-many');
            } else {
                limitContainer.removeClass('field-limit-too-many');
            }
        }

        function getRemainingInfo(len, maxCharacters) {
            var remaining = Math.max(0, maxCharacters - len);
            var tooMany = Math.max(0, len - maxCharacters);

            var remainingInfo;
            if (tooMany > 0) {
                remainingInfo = tooMany.toString() + ' too many';
            } else if (remaining > 0) {
                remainingInfo = remaining.toString() + ' remaining';
            } else {
                remainingInfo = 'spot on';
            }

            return {
                message: remainingInfo,
                remaining: remaining,
                tooMany: tooMany
            }
        }

        if (prefix === undefined) prefix = '';

        var fieldName = input.attr('name')
        if (prefix && fieldName.indexOf(prefix) === 0) {
            fieldName = fieldName.substr(prefix.length);
        }

        if (rules[fieldName]) {
            var rule = rules[fieldName];
            if (rule.max_characters) {
                var v = input.val();
                var len = v.length;
                var remainingInfo = getRemainingInfo(len, rule.max_characters);
                updateRuleInfo(input, '<b>' + len + '</b> characters (' + remainingInfo.message + ')', remainingInfo.tooMany > 0);
            }
        }
    },


    evaluateAllLimitsForForms: function() {
        var forms = $('form, .embed-form');
        for (var i = 0; i < forms.length; i++) {
            this.evaluateAllLimits(forms.eq(i));
        }
    },


    evaluateAllLimits: function(form) {
        var rules;
        var prefix;
        if (form.hasClass('.embed-form')) {
            var container = form.closest('.embed-forms');
            rules = container.attr('data-limit-rules');
            var prefixPattern = container.attr('data-prefix-pattern');
            prefix = getEmbeddedFormPrefix(form, prefixPattern);
        } else {
            rules = form.attr('data-limit-rules');
        }

        // parse JSON and evaluate
        if (rules) {
            rules = JSON.parse(rules);
            var fieldNames = Object.keys(rules);
            for (var i = 0; i < fieldNames.length; i++) {
                var fieldName = fieldNames[i];
                if (prefix) fieldName = prefix + fieldName
                var field = form.find('[name="' + fieldName + '"]');
                if (field.length > 0) {
                    this.evaluateLimits(form, field, rules, prefix);
                }
            }
        }
    },


    /*
     * Triggered whenever the user is typing to update limit rules.
     */
    onFormWithLimitRulesChanged: function(e) {
        var input = $(e.target).closest('input, textarea');
        var form = input.closest('.embed-form');
        var rules;
        var prefix;
        if (form.length > 0) {
            var container = form.closest('.embed-forms');
            rules = container.attr('data-limit-rules');
            var prefixPattern = container.attr('data-prefix-pattern');
            prefix = getEmbeddedFormPrefix(form, prefixPattern);
        } else {
            form = input.closest('form');
            rules = form.attr('data-limit-rules');
        }

        // parse JSON and evaluate
        if (rules) {
            rules = JSON.parse(rules);
            this.evaluateLimits(form, input, rules, prefix);
        }
    },


    onOffCanvasNavToggle: function (e) {
        e.preventDefault();
        var wrapper = $('body > .wrapper');
        var body = $('body');

        if (wrapper.hasClass('nav-open')) {
            wrapper.removeClass('nav-open');
        } else {
            wrapper.addClass('nav-open');
        }

        if (body.hasClass('nav-open')) {
            body.removeClass('nav-open');
        } else {
            body.addClass('nav-open');
        }
    },


    onCloseOffCanvasNav: function(e) {
        $('body > .wrapper').removeClass('nav-open');
        $('body').removeClass('nav-open');
    },


    isStepAtEnd: function (index, numberOfSteps, rows, stepsPerRow) {
        for (var i = 0; i < rows; i++) {
            var indexn = stepsPerRow * (i + 1);
            if (index == indexn && index < numberOfSteps) {
                return true;
            }
        }
        return false;
    },


    onNavStepSelectChange: function (e) {
        e.preventDefault();
        var activeTab = e.target;
        this.changeNavStep(activeTab.value);
    },


    onNavStepChange: function (e) {
        var activeTab = $(e.target).closest('a');
        this.changeNavStepSelectOption(activeTab.attr('href'));
    },


    changeNavStepSelectOption: function (activeId) {
        var formTab = $('.form-content > .tab');
        var options = formTab.find('#phone-nav-steps option');

        for (var i = 0; i < options.length; i++) {
            if (options[i].value == activeId) options[i].selected = true;
        }
    },


    changeNavStep: function (activeId) {
        var formTab = $('.form-content > .tab');

        formTab.find('.tab-pane.active').removeClass('active').addClass('fade');
        formTab.find(activeId).removeClass('fade').addClass('active');

        var navTabs = formTab.find('.nav-tabs > li');
        for (var i = 0; i < navTabs.length; i++) {
            var tab = $(navTabs[i]);
            if (tab.hasClass('active')) tab.removeClass('active');
            if (tab.find('a').attr('href') == activeId) tab.addClass('active');

            // trigger lazyload
            document.lazyloadImages();
        }
    },


    showPhoneOnLoginScreen: function () {
        var halfIphone = $('.half-iphone');
        if (halfIphone.length > 0) {
            halfIphone.removeClass('hide-phone');
        }
    },


    stopAutoCapsOnLoginForm: function () {
        var loginForm = $('.login-form');
        if (loginForm.length > 0) {
            // stop iphones from having cap on first character
            loginForm.find('input').attr('autocapitalize', 'none');
        }
    },


    postConfirm: function() {
        $('.post-confirm').click(function(e) {
            e.preventDefault();

            var btn = $(e.target).closest('.post-confirm');
            var confirmText = btn.data('confirm');
            var href = btn.attr('href')

            cubane.dialog.confirm('Confirm', confirmText, function() {
                $.post(href, function(json) {
                    if (json.success) {
                        window.location.reload();
                    }
                }, 'JSON')
            });
        });
    },


    /*
     * Automatically start pulse animation for certain elements.
     */
    autoPulse: function() {
        cubane.pulse.place($('.pulse'));
    },


    /*
     * Enable tinymce for all textarea fields with the class 'editable-html'.
     */
    autoEnableTinyMCE: function(textarea) {
        var plugins = [];

        // default plugins
        if (CUBANE_SETTINGS.CUBANE_BACKEND_EDITOR_PLUGINS) {
            Array.prototype.push.apply(plugins, CUBANE_SETTINGS.CUBANE_BACKEND_EDITOR_PLUGINS);
        }

        // add youtube
        if (CUBANE_SETTINGS.CUBANE_BACKEND_EDITOR_YOUTUBE) {
            plugins.push('-cubaneyoutube')
        }

        // add additional advanced plugins that we usually do not want ordinary
        // users to use, but we add them if they have been turned on...
        if (CUBANE_SETTINGS.CMS_ADV_EDITOR_PLUGINS) {
            Array.prototype.push.apply(plugins, [
                '-textcolor',
                '-emoticons'
            ]);
        }

        if (textarea != 'textarea.many-editable-html') {
            plugins.push('-cubanefillresize');
        }

        // if cubane.media is available, make images plugin available.
        if ( cubane.urls.reverse('cubane.cms.images.index') ) {
            plugins.push('-cubaneimage');
        }

        // initialize tinymce editor(s)
        tinyMCE.baseURL = '/static/cubane/backend/tinymce/js/tinymce';
        tinyMCE.init({
            selector: textarea,
            relative_urls: false,
            convert_urls: false,
            content_css: '/static/cubane/backend/tinymce/css/tinymce.css',

            menubar: 'edit insert view format table tools spellchecker',
            toolbar1: 'undo redo | styleselect | bold italic | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image',
            toolbar2: 'forecolor backcolor emoticons | nonbreaking | removeformat | youtube',
            paste_as_text: true,
            plugins: plugins,
            theme: 'cubane',

            // FIX for IE11, otherwise IE11 will not load theme files...
            skin_url: '/static/cubane/backend/tinymce/js/tinymce/skins/lightgray',
            theme_url: '/static/cubane/backend/tinymce/js/tinymce/themes/cubane/theme.min.js',

            image_list: cubane.urls.reverse('cubane.backend.api.images'),
            link_list: cubane.urls.reverse('cubane.backend.api.links'),

            browser_spellcheck: true,
            contextmenu: false,

            setup: function(editor) {
                // set editor to readyonly mode if underlying textarea is
                // readonly
                if ( $('#' + editor.id).attr('readonly') ) {
                    editor.settings.readonly = true;
                }

                // set initial height
                setTimeout(function() {
                    var iframe = $('#' + editor.id + '_ifr');
                    iframe.height(300);
                }, 50);
            }
        });
    },


    /*
     * Print current page.
     */
    onPrintPage: function(e) {
        e.preventDefault();
        window.print();
    },


    /*
     * Undo given operation.
     */
    onUndoClicked: function(e) {
        e.preventDefault();

        var undo = $(e.target).closest('.cubane-undo');
        var change = undo.attr('data-change');
        if (change) {
            undo.remove();
            cubane.backend.undo(change, $.proxy(function() {
                // remove any notifications that contain an undo regarding the
                // given undo identifier...
                var items = $('.cubane-undo');
                for (var i = 0; i < items.length; i++) {
                    var item = items.eq(i);
                    if (item.attr('data-change') === change) {
                        if (item.hasClass('popup-notification-undo')) {
                            // remove popup notification button
                            var notification = item.closest('.popup-notification');
                            notification.find('.cubane-undo').remove();
                        } else if (item.hasClass('alert-undo')) {
                            // remove alert message undo button
                            var alertContainer = item.closest('.alert');
                            alertContainer.find('.cubane-undo').remove();
                        }
                    }
                }
            }, this));
        }
    },


    /*
     * Show notifications when clicked
     */
    notifications: function() {
        $(document).on('click', '.cms-notifications', this.bound.onNotifications);
        $(document).on('click', '.popup-notification-btn.view-btn', this.bound.onNotifications);
        $(document).on('click', '.notifications-messages-overlay', this.bound.onCloseNotifications);
        $(document).on('click', '.popup-notification-btn.close-btn', this.bound.onClosePopupNotifications);
    },


    /*
     * Show Notifications.
     */
    onNotifications: function(e) {
        e.preventDefault();

        if ($('#content').hasClass('show-messages')) {
            $('#content').removeClass('show-messages');
        } else {
            $('#content').addClass('show-messages');
        }
    },


    onCloseNotifications: function(e) {
        e.preventDefault();
        if ($('#content').hasClass('show-messages')) {
            $('#content').removeClass('show-messages');
        }
    },


    onClosePopupNotifications: function(e) {
        e.preventDefault();
        if ($('.popup-notification').hasClass('on-screen')) {
            $('.popup-notification').removeClass('on-screen');
        }
    },


    onDialogInit: function(e) {
        this.focusFirstInputField(undefined, false);
    },


    /*
     * Instead of downloading a file direct, we first ask for the encoding
     * that is required for such file and proceed to the requested resource
     * afterwards...
     */
    onDownloadWithEncodingClicked: function(e) {
        var a = $(e.target).closest('.download-with-encoding');
        var url = a.attr('href');
        var title = a.attr('title');

        if (a.length > 0) {
            e.preventDefault();
            cubane.backend.downloadWithEncoding(url, title);
        }
    },


    onInitControls: function(e) {
        var container = $(e.target);

        // select2
        if (jQuery().select2) {
            container.find('select').select2();
        }

        // date picker
        container.find('.date-field input').datepicker({
          format: 'dd/mm/yyyy',
          todayHighlight: true
        });

        // time picker
        container.find('.time-field input').timepicker({
            template: 'modal',
            showWidgetOnFocus: false,
            defaultTime: false,
        });
    },


    onBtnSummaryItemsClicked: function(e) {
        e.preventDefault();
        var panel = $(e.target).closest('.summary-items');
        var btn = panel.find('.btn-summary-items');

        panel.toggleClass('expand');
        if (panel.hasClass('expand')) {
            btn.text('Close');
        } else {
            btn.text('Show Summary Details');
        }
    },


    animateNotifications: function () {
        var popupNotifications = $('.popup-notification:not(.hidden)');
        if (popupNotifications.length > 0) {
            popupNotifications.addClass('on-screen');
            this.hideNotifications(popupNotifications);
        }
    },


    hideNotifications: function (popupNotifications, withDelay) {
        if (withDelay === undefined) withDelay = true;

        if (this.hideNotificationTimer) {
            clearTimeout(this.hideNotificationTimer);
        }

        if (withDelay) {
            this.hideNotificationTimer = setTimeout(function() {
                popupNotifications.removeClass('on-screen');
                popupNotifications.addClass('hidden');
            }, 5000);

            $('.popup-notification').mouseover(function () {
                clearTimeout(this.hideNotificationTimer);
            });

            $('.popup-notification').mouseout($.proxy(function () {
                this.hideNotifications($('.popup-notification'), withDelay);
            }, this));
        } else {
            popupNotifications.removeClass('on-screen');
            popupNotifications.addClass('hidden');
        }
    },


    enableShareMedia: function enableShareMedia() {
        var panel = $('#cubane-share-media-panel');
        if (panel.length === 0) {
            return;
        }

        function updateUIState() {
            var enabled = $('#id_share_enabled').is(':checked');
            if (enabled) {
                $('#id_copy_link').show();
                $('#id_share_btn_text').text('Share');
            } else {
                $('#id_copy_link').hide();
                $('#id_share_btn_text').text('Turn Off Sharing');
            }
        }

        // copy download link
        $('#id_copy_link').on('click', function(e) {
            e.preventDefault();
            var form = $(e.target).closest('form');
            var filename = $('#id_share_filename').val();
            var baseUrl = panel.attr('data-base-url');
            cubane.backend.copyTextToClipboard(baseUrl + filename);
            setTimeout(function() {
                form.submit();
            }, 0);
        });

        // toggle enable state
        $('#id_share_enabled').on('change', updateUIState);
    },


    /*
     * Enable Color Picker
     */
    enableColorPicker: function() {
        var settings = {
            animationSpeed: 50,
            animationEasing: 'swing',
            change: null,
            changeDelay: 0,
            control: 'hue',
            defaultValue: '',
            hide: null,
            hideSpeed: 100,
            inline: false,
            letterCase: 'lowercase',
            opacity: false,
            position: 'bottom left',
            show: null,
            showSpeed: 100,
            theme: 'default'
        }

        if ($('.color-text').length > 0) {
            $('.color-text').minicolors(settings);
        }
    },
};


/*
 * Create new backend controller when DOM is ready and dispose it on unload.
 */
$(document).ready(function () {
    window.backendController = new cubane.backend.BackendController();

    $(window).unload(function () {
        window.backendController.dispose();
        window.backendController = null;
    });
});


}(this));

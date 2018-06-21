(function(globals){
"use strict";


cubane.namespace('cubane.cms');


cubane.require('cubane.html');
cubane.require('cubane.dialog');
cubane.require('cubane.format');
cubane.require('cubane.urls');


/*
 * Provides user-friendly and rich UI for editing CMS content with live
 * page preview.
 */
cubane.cms.CMSController = function() {
    this.bound = {
        onResizePagePreview: $.proxy(this.onResizePagePreview, this),
        onTemplateChanged: $.proxy(this.onTemplateChanged, this),
        onPublish: $.proxy(this.onPublish, this),
        updatePreviewSizeAndScale: $.proxy(this.updatePreviewSizeAndScale, this),
    };

    this.createPagePreview();
    this.updatePreviewOnTemplateChange();
    this.autoResizePagePreview();
    this.publish();

    // create page preview slot controller
    this.previewController = new cubane.cms.PreviewController();

    // create meta data preview controller
    this.metaPreviewController = new cubane.cms.MetaPreviewController();
};

cubane.cms.CMSController.prototype = {
    dispose: function() {
        $(window).off('resize', this.bound.onFillSpace);
        $(document).off('cubane-tab-switched', this.bound.onResizePagePreview);
        $('#id_template').off('change', this.bound.onTemplateChanged);
        $('.cms-publish').off('click', this.bound.onPublish);
        this.bound = null;

        this.previewController.dispose();
        this.previewController = null;

        this.metaPreviewController.dispose();
        this.metaPreviewController = null;
    },


    /*
     * Create page view iframe
     */
    createPagePreview: function() {
        // create page preview for first editable with preview
        var editable = $('.editable-html.preview:first');
        var form = editable.closest('.preview-form');
        if ( form.length > 0 ) {
            var src = form.data('preview-url');
            if ( src ) {
                var c = editable.closest('.tab-pane');
                var row = $('<div class="row-fluid"></div>');
                var left = $('<div class="span4"></div>');
                var right = $('<div class="span8"></div>');

                row.append(left);
                row.append(right);
                left.append(c.children());
                right.append(
                    '<div id="page-preview-frame" class="page-preview-frame">' +
                    '<iframe id="page-preview" class="page-preview" ' +
                    'frameborder="no" src="' + src + '"></iframe>' +
                    '</div>'
                );

                c.append(row);
            }
        }

        // hide the remaining ones...
        editable.closest('.control-group').addClass('active-editor');
        var editables = $('.editable-html.preview').not(':first').closest('.control-group').addClass('inactive-editor');
    },


    /*
     * Updates the preview page once we changed the template to use, so that
     * we get a representation of the change before we change the content.
     */
    updatePreviewOnTemplateChange: function () {
        $('#id_template').on('change', this.bound.onTemplateChanged);
    },


    /*
     * Automatically resize pageview according to the size of the corresponding
     * editor box (tinymce).
     */
    autoResizePagePreview: function() {
        $(window).on('resize', this.bound.onResizePagePreview);
        $(document).on('cubane-tab-switched', this.bound.onResizePagePreview);
    },


    /*
     * Publish changes when pressing the publish button
     */
    publish: function() {
        $('.cms-publish').on('click', this.bound.onPublish);
    },


    /*
     * Event handler for auto-resizing the page preview iframe.
     */
    onResizePagePreview: function() {
        var frame = $('#page-preview-frame');
        if ( frame.length > 0 ) {
            var editor = $('.active-editor .mce-tinymce');
            if ( editor.length > 0) {
                setTimeout(function() {
                    frame.height(editor.height());
                }, 500);
            }
        }
    },


    /*
     * Event handler that is fired whenever we change the page template.
     * If so, we need to update the page preview to reflect the change in
     * template before we even save the page content.
     * The page might not even exist yet, because we are still in the process
     * of creating the page in the first place.
     */
    onTemplateChanged: function (e) {
        var template = $('#id_template').val();
        var preview = $('#page-preview');
        var form = preview.closest('.preview-form');
        var src = form.data('preview-url');
        if ( src ) {
            preview.attr('src', src + '?template=' + encodeURIComponent(template));
        }
    },


    /*
     * Publish cms content.
     */
    onPublish: function(e) {
        e.preventDefault();

        var dlg = cubane.dialog.working('Publishing...', 'Publishing Changes ...Please Wait...');

        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: cubane.urls.reverse('cubane.cms.api.publish'),
            success: function(json){
                dlg.close();

                $('.cms-publish').removeClass('can-publish');

                var msg = json.items + ' ' +
                        cubane.format.pluralize(json.items, 'file', 'files') +
                        ' (' + cubane.format.filesize(json.size) + ').';

                if ( $('.post-publish').length > 0 ) {
                    $('.pre-publish').hide();
                    $('.post-publish').show();
                    $('.publish-msg').text(msg);
                } else {
                    cubane.dialog.info(
                        'Published Successfully',
                        msg
                    );
                }
            },
            error: function() {
                dlg.close();
                cubane.dialog.info(
                    'Oops',
                    'Oops, something went wrong while publishing your ' +
                    'changes. Please try again later. We get busy in the meantime...'
                );
            }
        });
    }
};


/*
 * The preview controller is responsible for managing the content inside the
 * preview iframe, so that the current slot is selected and that slots can be
 * selected by clicking them.
 */
cubane.cms.PreviewController = function() {
    this._bound = {
        onSlotClicked: $.proxy(this.onSlotClicked, this),
        onTabSwitched: $.proxy(this.onTabSwitched, this),
        onCmsReady: $.proxy(this.onCmsReady, this)
    };

    this.document = null;

    // wait for theme.min.js to finish loading...
    var deferCounter = 0;
    function defer(func) {
        if (tinymce.ThemeManager.items.length === 0 || deferCounter < 10) {
            deferCounter += 1;
            setTimeout(function() {
                defer(func);
            }, 50);
        } else {
            func();
        }
    }

    // make slots within preview selectable
    var iframe = $('#page-preview');
    if (iframe.length > 0) {
        iframe.on('load', $.proxy(function() {
            var f = $.proxy(function() {
                var w = iframe.get(0).contentWindow;
                this.document = w.document;

                // force preview to load additional editor stylesheet
                var style = this.document.createElement('link');
                style.rel = 'stylesheet';
                style.media = 'screen';
                style.href = '/static/cubane/cms/css/preview.css';
                this.document.head.appendChild(style);

                // inject preview class to body
                this.document.body.className += ' preview';

                // clicking on a slot should switch to the corresponding content
                // within the editor...
                $(this.document).on('click', '.cms-slot', $(this.document), this._bound.onSlotClicked);
                $(this.document).on('cmsSlotClicked', this._bound.onSlotClicked);
                $(this.document).on('cmsReady', this._bound.onCmsReady);

                // select first slot on page by default
                // (only if preview is actually visible)
                if ( iframe.is(':visible') ) {
                    var slot = $();

                    if (CUBANE_SETTINGS.CMS_DEFAULT_SLOTNAME) {
                        // specific slot as given by settings
                        var slot = $('.cms-slot[data-slotname="' + CUBANE_SETTINGS.CMS_DEFAULT_SLOTNAME + '"]', this.document);
                    } else {
                        // first slot on page
                        var slot = $('.cms-slot:first', this.document);
                    }

                    // fallback -> first slot on page
                    if (slot.length === 0) {
                        slot = $('.cms-slot:first', this.document);
                    }

                    // select slot
                    slot.click();
                }

                $(document).on('cubane-tab-switched', this._bound.onTabSwitched);

                this.iframe = iframe;
                this.updateSlotContent();

                $(w).on('unload', $.proxy(function() {
                    this.disposeIFrame();
                }, this));
            }, this);

            defer(f);
        }, this));
    }
};

cubane.cms.PreviewController.prototype = {
    disposeIFrame: function () {
        if ( this._bound !== null ) {
            $(this.document).off('click', '.cms-slot', $(this.document), this._bound.onSlotClicked);
            $(this.document).off('cmsSlotClicked', this._bound.onSlotClicked);
            $(this.document).off('cmsReady', this._bound.onCmsReady);
            $(document).off('cubane-tab-switched', this._bound.onTabSwitched);
        }
        this.document = null;
    },


    dispose: function () {
        this.disposeIFrame();
        this._bound = null;
    },


    /*
     * Update the content of all slots for this preview page. This basically
     * happens whenever we finished loading the iframe content. In the case
     * that we switch the template (which ultimatly triggers a reload of the
     * preview iframe), we also copy the content across (we might changed
     * content and reloading the preview page would cause changes to disappear
     * otherwise).
     */
    updateSlotContent: function () {
        var slots = $('.cms-slot', this.document);
        for ( var i = 0; i < slots.length; i++ ) {
            this.updateSlotContentFor(slots.eq(i));
        }
    },


    /*
     * Copy the html content of the corresponding tinymce editor across
     * to the given slot within the preview page.
     */
    updateSlotContentFor: function (slot) {
        var slotname = slot.data('slotname');
        var editor = tinymce.get('id_slot_' + slotname);
        if ( editor ) {
            var container = slot.find('> .cms-slot-container');
            if ( container.length == 0 ) container = slot;

            // get headline transpose
            var headlineTranspose = parseInt(slot.attr('data-headline-transpose'));
            if (headlineTranspose == NaN) headlineTranspose = 0;

            // get html content
            var html = editor.getContent({format: 'raw', no_events: true});

            // transpose headlines
            if (headlineTranspose > 0) {
                html = cubane.html.transposeHtmlHeadlines(html, headlineTranspose);
            }

            // update content
            container.html(html);
        }
    },


    /*
     * Event handler whenever we click on a slot. This selects the slot and also
     * makes the corresponding tinymce editor visible.
     */
    onSlotClicked: function (e) {
        if ( this.document === null ) return;

        var slot = $(e.target).closest('.cms-slot');
        var slotname = undefined;

        if (slot.length > 0) {
            slotname = slot.data('slotname');
        } else {
            try {
                slotname = e.originalEvent.detail.slotname || undefined;
            }
            catch (err) {
                slotname = undefined;
            }

            if (slotname) {
                slot = $('.cms-slot[data-slotname="' + slotname + '"]', this.document);
            }
        }

        if (slot.length > 0 && slotname !== undefined) {
            var el = $('#id_slot_' + slotname);
            var editor = el.closest('.control-group');
            if ( editor.length > 0 ) {
                $('.cms-slot.active', this.document).removeClass('active');
                slot.addClass('active');

                $('.active-editor').removeClass('active-editor').addClass('inactive-editor');
                editor.removeClass('inactive-editor').addClass('active-editor');

                // resize new editor
                $(window).trigger('resize');

                // focus it
                tinymce.get('id_slot_' + slotname).focus();
            }
        }
    },


    /*
     * Whenever we switch tabs, we need to select the first cms slot within the
     * preview if no slot has been selected yet.
     */
    onTabSwitched: function (e) {
        if ( this.iframe.is(':visible') ) {
            if ( $('.cms-slot.active', this.document).length === 0 ) {
                $('.cms-slot:first', this.document).click();
            }
        }
    },


    /*
     * May be triggered by the site to signal that the page has been fully loaded
     * and rendered and it is safe to select the first cms-slot automatically.
     */
    onCmsReady: function(e) {
        if ( this.iframe.is(':visible') ) {
            $('.cms-slot:first', this.document).click();
        }
    }
};


/*
 * The meta preview controller is links input field with a representation
 * that mimics a Search Engine result
 */
cubane.cms.MetaPreviewController = function() {
    this._bound = {
        onChange: $.proxy(this.onChange, this),
        onTitleChange: $.proxy(this.onTitleChange, this),
    };

    /*
     *  Select every watch-field object in meta-preview
     */
    var watching_fields = $('.meta-preview').find('[data-watch-field]');
    this._watching_fields = watching_fields;

    var watched_fields = [];
    $.each(watching_fields, function(){
        var to_watch = $(this).data('watch-field');
        if ($.inArray(to_watch, watched_fields) === -1){
            watched_fields.push(to_watch);
        }
    });
    this._watched_fields = watched_fields;

    // binding the change events to the fields
    var self = this;
    $.each(this._watched_fields, function(index, value){
        $('#id_' + value).on('keyup', self._bound.onChange);
        $('#id_' + value).on('change', self._bound.onChange);
    });

    $('#id_title').on('change keyup', self._bound.onTitleChange);

    this._meta_title_differs_from_title = !($('#id__meta_title').val() == $('#id_title').val());
};

cubane.cms.MetaPreviewController.prototype = {
    dispose: function () {
        var self = this;
        if ( this._bound !== null ) {
            $.each(this._watched_fields, function(index, value){
                $(value).off('keyup', self._bound.onChange);
                $(value).off('change', self._bound.onChange);
            });
            $('#id_title').off('change keyup', self._bound.onTitleChange);
        }
        this._bound = null;
    },

    /*
     * Update the watching elements upon change of watched field
     */
    onChange: function (e) {
        var target = e.target;

        var input = $(target).closest('input, textarea');

        var id = input.attr('id').replace('id_','');

        if (id == '_meta_title' && input.val() != $('#id_title').val()){
            this._meta_title_differs_from_title = true;
        }

        // update watching fields that are watching this field
        var self = this;
        $.each(this._watching_fields, function(){
            if ($(this).data('watch-field') == id) {
                var newVal = input.val();

                // replace _ with regular space
                newVal.replace('_', '');

                // replace new Value with placeholders if empty
                if (id == '_meta_title') newVal = newVal || '<Page Title>';
                if (id == 'slug') {
                    if (newVal.length > 0 && newVal.charAt(newVal.length - 1) !== '/'){
                        newVal += '/'
                    }
                    newVal = newVal || '<slug>/';
                }
                if (id == '_meta_description') newVal = newVal || 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum ornare ligula ut aliquet accumsan. Morbi faucibus lectus libero, nec condimentum ligula aliquam ut. Duis fringilla massa ac arcu fermentum, at ullamcorper mi placerat. Nam eros augue.';
                if (id == '_meta_title') newVal = newVal || '<Page Title>';

                $(this).text(newVal);
            }
        })
    },

    /*
     *  Prefill the Meta Title with the page title value
     *  unless we typed something into meta title.
     */
    onTitleChange: function (e) {
        var target = e.target;

        var title = $(target).val();
        var $metaTitle = $('#id__meta_title');
        var metaTitle = $metaTitle.val();
        if (
            ($metaTitle.prop('defaultValue') == $(target).prop('defaultValue') &&
                !this._meta_title_differs_from_title)) {
            // copy value over to meta title if meta title empty or hasn't
            // diverged from the page title yet
            $metaTitle.val(title.replace('_', ' '));
            $metaTitle.change();
        }
    },
};


/*
 * Create new cms controller when DOM is ready and dispose it on unload.
 */
$(document).ready(function() {
    var controller = new cubane.cms.CMSController();
    $(window).unload(function() {
        controller.dispose();
        controller = null;
    });
});


}(this));

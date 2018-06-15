(function (globals){
"use strict";


cubane.namespace('cubane.backend');


cubane.require('cubane.urls');


cubane.backend.lightboxController = function () {
    this._bound = {
        onLightboxClicked: $.proxy(this.onLightboxClicked, this),
        onLightboxLinkClicked: $.proxy(this.onLightboxLinkClicked, this),
        onLightboxClose: $.proxy(this.onLightboxClose, this),
        onNextLightbox: $.proxy(this.onNextLightbox, this),
        onPrevLightbox: $.proxy(this.onPrevLightbox, this),
    };

    $(document).on(
        'click',
        '.cubane-listing-item-lightbox',
        this._bound.onLightboxClicked
    );
    $(document).on(
        'click',
        '.cubane-lightbox',
        this._bound.onLightboxLinkClicked
    );
    $(document).on(
        'click',
        '.cubane-cms-lightbox-close',
        this._bound.onLightboxClose
    );
    $(document).on(
        'click',
        '.cubane-cms-lightbox-next',
        this._bound.onNextLightbox
    );
    $(document).on(
        'click',
        '.cubane-cms-lightbox-prev',
        this._bound.onPrevLightbox
    );
};


cubane.backend.lightboxController.prototype = {
    dispose: function () {
        $(document).off(
            'click',
            '.cubane-listing-item-lightbox',
            this._bound.onLightboxClicked
        );
        $(document).off(
            'click',
            '.cubane-lightbox',
            this._bound.onLightboxLinkClicked
        );
        $(document).off(
            'click',
            '.cubane-cms-lightbox-close',
            this._bound.onLightboxClose
        );
        $(document).off(
            'click',
            '.cubane-cms-lightbox-next',
            this._bound.onNextLightbox
        );
        $(document).off(
            'click',
            '.cubane-cms-lightbox-prev',
            this._bound.onPrevLightbox
        );
    },


    setActiveLightboxItem: function (elem) {
        this.activeItem = elem;
        return this.activeItem;
    },


    getActiveLightboxItem: function (elem) {
        if (this.activeItem) {
            return this.activeItem;
        }
        return undefined;
    },


    createOverlay: function () {
        return $('<div class="cubane-cms-lightbox-overlay cubane-cms-lightbox-close"></div>');
    },


    createLightbox: function () {
        var lightbox = ['<div class="cubane-cms-lightbox">',
                            '<div class="cubane-cms-lightbox-items">',
                            '<div class="cubane-cms-lightbox-item">',
                                '<div class="cubane-cms-lightbox-filename">',
                                    '<svg viewBox="0 0 23.4 22.9"><use xlink:href="#icon-image"/></svg>',
                                    '<span></span>',
                                '</div>',
                                '<div class="btn cubane-cms-lightbox-close">',
                                    '<svg viewBox="0 0 19 18.8"><use xlink:href="#icon-close"/></svg>',
                                '</div>',
                            '</div>',
                        '</div>',
                        '<div class="cubane-cms-lightbox-arrow cubane-cms-lightbox-prev">',
                            '<div class="cubane-cms-lightbox-arrow-cover"></div>',
                            '<svg viewBox="0 0 29.8 52.7"><use xlink:href="#icon-arrow-left"/></svg>',
                        '</div>',
                        '<div class="cubane-cms-lightbox-arrow cubane-cms-lightbox-next">',
                        '<div class="cubane-cms-lightbox-arrow-cover"></div>',
                            '<svg viewBox="0 0 29.8 52.7"><use xlink:href="#icon-arrow-right"/></svg>',
                        '</div>',
                    '</div>'].join('');
        $('body').append(lightbox);
    },


    onLightboxClicked: function (e) {
        e.preventDefault();
        if ( $(e.target).closest('.btn').hasClass('disabled') ) return;

        var a = $(e.target).closest('a');
        var activeItem = this.setActiveLightboxItem(a);

        // create lightbox overlay
        var overlay = this.createOverlay();

        $('body').append(overlay);
        $('.cubane-cms-lightbox').addClass('open');
        this.addActiveLightboxItemImage(activeItem);
    },


    onLightboxLinkClicked: function(e) {
        e.preventDefault();
        var link = $(e.target).closest('.cubane-lightbox');
        if ( link.hasClass('disabled') ) return;

        var imgURL = link.attr('href');
        var filename = link.attr('title');

        // create lightbox overlay
        var overlay = this.createOverlay();
        $('body').append(overlay);
        $('.cubane-cms-lightbox').addClass('open single-image');

        this.showLightbox(imgURL, null, filename);
    },


    onLightboxClose: function (e) {
        e.preventDefault();
        if ( $(e.target).closest('.btn').hasClass('disabled') ) return;

        $('.cubane-cms-lightbox').removeClass('open');
        $('.cubane-cms-lightbox-item-img').remove();
        $('.cubane-cms-lightbox-item-video').remove();
        $('.cubane-cms-lightbox-overlay').remove();
    },


    onNextLightbox: function (e) {
        e.preventDefault();
        if ( $(e.target).closest('.btn').hasClass('disabled') ) return;
        var activeElem = this.getActiveLightboxItem().closest('.cubane-listing-item');
        var nextElem = activeElem.next().find('.cubane-listing-item-lightbox');

        if (nextElem.length === 0) {
            nextElem = this.getFirstLightboxItem().find('.cubane-listing-item-lightbox');
        }
        this.setActiveLightboxItem(nextElem);
        this.addActiveLightboxItemImage(nextElem);
    },


    onPrevLightbox: function (e) {
        e.preventDefault();
        if ( $(e.target).closest('.btn').hasClass('disabled') ) return;
        var activeElem = this.getActiveLightboxItem().closest('.cubane-listing-item');
        var prevElem = activeElem.prev().find('.cubane-listing-item-lightbox');

        if (prevElem.length === 0) {
            prevElem = this.getLastLightboxItem().find('.cubane-listing-item-lightbox');
        }
        this.setActiveLightboxItem(prevElem);
        this.addActiveLightboxItemImage(prevElem);
    },


    addActiveLightboxItemImage: function (activeItem) {
        $('.cubane-cms-lightbox-item-img').remove();
        $('.cubane-cms-lightbox-item-video').remove();
        var imgURL = activeItem.attr('data-image-url');
        var video  = activeItem.attr('data-video');
        var filename = activeItem.attr('data-filename');
        this.showLightbox(imgURL, video, filename);
    },


    showLightbox: function(imgURL, video, filename) {
        var lightbox = $('.cubane-cms-lightbox').find('.cubane-cms-lightbox-item');
        $(lightbox).find('.cubane-cms-lightbox-filename span').html(filename);

        if (video) {
            $(lightbox).append('<div class="cubane-cms-lightbox-item-video">' + video + '</div>');
        } else {
            $(lightbox).append('<div class="cubane-cms-lightbox-item-img"><img src="' + imgURL + '"></div>');
        }
    },


    getFirstLightboxItem: function (e) {
        return $('.cubane-listing-item').first();
    },


    getLastLightboxItem: function (e) {
        return $('.cubane-listing-item').last();
    },
};


/*
 * Create new backend controller(s) when DOM is ready and dispose it on unload.
 */
$(document).ready(function () {
    var lightboxController = new cubane.backend.lightboxController();
    lightboxController.createLightbox();

    $(window).on('resize', function () {
        var activeItem = lightboxController.getActiveLightboxItem();
    });

    $(window).unload(function () {
        lightboxController.dispose();
        lightboxController = null;
    });
});


}(this));

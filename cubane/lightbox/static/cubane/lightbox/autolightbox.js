/*
 * cubane.lightbox is using Magnific Popup, which is a responsive
 * lightbox implementation.
 *
 * http://dimsemenov.com/plugins/magnific-popup/
 * http://coding.smashingmagazine.com/2013/05/02/truly-responsive-lightbox/
 */
(function (globals){
"use strict";


/*
 * Initialize lightbox for all given elements. If gallery is true, all images
 * form a group of images as part of a gallery, so that we can quickly
 * flip through all images in the group.
 */
var initLightbox = function (elements, gallery) {
    elements.magnificPopup({
        type: 'image',
        gallery: {
            enabled: gallery
        },

        zoom: {
	        enabled: window.LIGHTBOX_ZOOM !== undefined ? window.LIGHTBOX_ZOOM : true,
        },

        image: {
			verticalFit: true
		},
    });
};


/*
 * Initialise image-based lightbox for individual images and for galleries
 */
var init = function () {
    // get elements where we can apply lightbox to a set of images (gallery)
    var galleries = $('.gallery');
    for ( var i = 0; i < galleries.length; i++ ) {
        initLightbox(galleries.eq(i).find('.lightbox'), true);
    }

    // find individual images that are not part of any gallery
    var images = $('.lightbox:noparents(.gallery)');
    initLightbox(images, false);
};


/*
 * automatically initializes lightbox control for images.
 */
$(document).ready(function () {
    init();
});


}(this));

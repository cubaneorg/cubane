/*
 * Provides responsive javascript-driven image loading for fast and responsive
 * websites.
 * - Medium-quality images are loaded with javascript disabled.
 * - Otherwise, images are loaded in the appropiate size depending on current
 *   resolution.
 * - Retina displays are taken into consideration where possible.
 * - Supports lightbox, where the fullscreen image version depends on the device.
 */
(function(globals){
"use strict";

/*
 * const
 */
var SVG_NS                = 'http://www.w3.org/2000/svg';
var XLINK_NS              = 'http://www.w3.org/1999/xlink';
var MEDIA_URL             = '{{ MEDIA_URL }}';
var MEDIA_API_URL         = '{{ MEDIA_API_URL }}';
var ART_DIRECTION         = {{ image_art_direction_json|safe }};
var IMAGE_SIZE_LIST       = {{ image_size_list_json|safe }};
var IMAGE_SIZE_NAMES      = {{ image_size_names_json|safe }};
var ASPECT_RATIO_BY_SHAPE = {{ aspect_ratio_by_shape|safe }};


/*
 * private
 */
var timeout = null;
var lastLoad = null;
var isApp = 'APP' in globals && globals.APP;


/*
 * Returns true, if the given element has the given class assigned.
 */
var hasClass = function (el, selector) {
    var className = " " + selector + " ";
    return (' ' + el.className + ' ').replace(/[\n\t]/g, ' ').indexOf(className) > -1;
};


/*
 * Add given class to given element.
 */
var addClass = function (el, classname) {
    if ( !hasClass(el, classname) ) {
        el.className += ' ' + classname;
    }
};


/*
 * Return a list of dom elements representing all lazy load image containers
 * that have not been processed yet.
 */
var getLazyLoadImages = function () {
    if ( document.querySelectorAll ) {
        return document.querySelectorAll('.lazy-load:not(.lazy-loaded)');
    } else {
        var elements = document.getElementsByClassName('lazy-load');
        var images = [];

        for ( var i = 0; i < elements.length; i++ ) {
            if ( !hasClass(elements[i], 'lazy-loaded') ) {
                images.push(elements[i]);
            }
        }

        return images;
    }
};


/*
 * Returns true, if the given element is in the current viewport (an element
 * is considered as visible if any part of the element is visible in the
 * current viewport).
 */
var isElementInViewport = function (el) {
    // if the element is not visible due to display: none etc., we do not
    // consider the element to be within the viewport to begin with, unless
    // the element is using the data-size loading mechanism...
    if (!el.hasAttribute('data-size')) {
        if (!el.offsetParent && el.offsetWidth === 0 && el.offsetHeight === 0) {
            return false;
        }
    }

    // see if the element is within the current viewport depending on scroll
    // position etc...
    if ( el.getBoundingClientRect ) {
        var rect = el.getBoundingClientRect();
        var ww = window.innerWidth;
        var wh = window.innerHeight;

        // An element is within the viewport, if its top-left corner is
        // to the north-west of the bottom-right corner of the viewport and
        // its bottom-right corner is to the south-east of the top-left
        // corner of the viewport.
        //
        // We are basically comparing each corner of the element with its
        // opposite facing corner of the viewport.
        //
        // For this purpose, we extend the visible viewport by a factor of 0.5
        // from its centre point, so that images are fetched a bit earlier than
        // they actually needed to.
        return (
            rect.left <= ww * 1.5 &&
            rect.top <= wh * 1.5 &&
            rect.right >= -(ww / 2) &&
            rect.bottom >= -(wh / 2)
        );
    } else {
        // if we cannot determine bounding rect, just assume the image is
        // visible
        return true;
    }
};


/*
 * Recursivly scan through all parents of the given node until we find a node
 * that has the attribute 'data-size-template'; otherwise return null.
 */
var getParentWithAttribute = function (node, attrname, whenVisible) {
    while ( node && node['hasAttribute'] && !node.hasAttribute(attrname) ) {
        if (whenVisible) {
            if (node.offsetParent === null) {
                return undefined;
            }
        }

        node = node.parentNode;
    }

    return node;
};


/*
 * Return the aspect ratio of the given shape in percent or (if the shape is
 * unknown or the original shape) the given default aspect ratio.
 */
var getAspectRatioPercentForShape = function getAspectRatioPercentForShape(shape, defaultAspectRatio) {
    if (ASPECT_RATIO_BY_SHAPE[shape] !== undefined) {
        return ASPECT_RATIO_BY_SHAPE[shape];
    } else {
        return defaultAspectRatio;
    }
};


/*
 * Return the device pixel ratio for the client device, for example a retina
 * device should return 2, since the physical screen resolution is twice of
 * the actual one that is returned by window.width and window.height.
 */
var getDevicePixelRatio = function () {
    if ({{ disable_device_ratio }} == 'false' || !{{ disable_device_ratio }}) {
        return window.devicePixelRatio || 1;
    } else {
        return 1;
    }
};


/*
 * Return the total width of the window in pixels.
 */
var getWindowWidth = function () {
    return document.documentElement.clientWidth;
};


/*
 * Return the total width of the given lazy image container in pixels.
 */
var getImageWidth = function (imageContainer) {
    return imageContainer.offsetWidth;
};


/*
 * Return the total height of the given lazy image container in pixels.
 */
var getImageHeight = function (imageContainer) {
    return imageContainer.offsetHeight;
};


/*
 * Return the name of the image version that we should use depending on
 * the screen resolution of the client device.
 */
var getImageVersion = function (imgWidth) {
	var devicePixelRatio = getDevicePixelRatio();
	var w = imgWidth * devicePixelRatio;
    var previousWidth = undefined;
    var midpoint = undefined;

    for (var i = 0; i < IMAGE_SIZE_LIST.length; i++) {
        // ignore if not defined
        if (!IMAGE_SIZE_LIST[i])
            continue;

        if (previousWidth) {
            // mid-point between two image sizes
            midpoint = IMAGE_SIZE_LIST[i] + ((previousWidth - IMAGE_SIZE_LIST[i]) / 2);
            if (w >= midpoint) {
                return IMAGE_SIZE_NAMES[i - 1];
            }
        } else {
            // image size as given
            if (w >= IMAGE_SIZE_LIST[i]) {
                return IMAGE_SIZE_NAMES[i];
            }
        }

        previousWidth = IMAGE_SIZE_LIST[i];
    }

    // default (last one that is defined)
    for (var i = IMAGE_SIZE_LIST.length - 1; i >= 0; i--) {
        if (IMAGE_SIZE_LIST[i]) {
            return IMAGE_SIZE_NAMES[i];
        }
    }

    // default
    return 'xx-small';
};

/*
 * Based on the image version provided, return the next smaller image version or
 * undefined if there is no smaller one.
 */
var getNextSmallerImageVersion = function (imageVersion) {
    if ( imageVersion == 'xxx-large' ) {
        return 'xx-large';
    } else if ( imageVersion == 'xx-large' ) {
        return 'x-large';
    } else if ( imageVersion == 'x-large' ) {
        return 'large';
    } else if ( imageVersion == 'large' ) {
        return 'medium';
    } else if ( imageVersion == 'medium' ) {
        return 'small';
    } else if ( imageVersion == 'small' ) {
        return 'x-small';
    } else if ( imageVersion == 'x-small' ) {
        return 'xx-small';
    } else if ( imageVersion == 'xx-small' ) {
        return 'xxx-small';
    }
};


/*
 * Return the base url components that is independent of size and shape
 * for the given image reference.
 */
var getImagBaseSrc = function getImagBaseSrc(img) {
    return img.getAttribute('data-path');
};


/*
 * Return the media base url based on the given base url. It is ensured that
 * the resulting base url starts and ends with a /.
 */
var getMediaUrlBase = function getMediaUrlBase(baseUrl) {
    if (baseUrl.charAt(0) !== '/') {
        baseUrl = '/' + baseUrl;
    }

    if (baseUrl.charAt(baseUrl.length - 1) !== '/') {
        baseUrl += '/';
    }

    return baseUrl;
};


/*
 * Return the original image url for the given image reference.
 */
var getOriginalImageSrc = function getOriginalImageSrc(img) {
    return getFinalMediaUrl(img, 'originals' + getImagBaseSrc(img));
};


/*
 * Return true, if the given image reference is an SVG file.
 */
var isSvgImage = function isSvgImage(img) {
    return img.getAttribute('data-svg') === '1';
}


/*
 * Return true, if the given image reference is an image.
 */
var isInlineImage = function isInlineImage(img) {
    return img.getAttribute('data-inline') === '1';
};


/*
 * Return media-api specific shape colorisation information for the given image.
 */
var getImageColorOverwriteAttr = function getImageColorOverwriteAttr(img) {
    return img.getAttribute('data-attr');
};


/*
 * Return the final image url for the given image based on the given url
 * component. If the image does not contain any color customisations or
 * is not an SVG image, then the regular media url (pre-rendered set of images)
 * is used; otherwise we use the media-api path to render a custom one-off
 * SVG image that may contain color overrides.
 */
var getFinalMediaUrl = function getFinalMediaUrl(img, url) {
    if (isSvgImage(img)) {
        var attr = getImageColorOverwriteAttr(img);
        if (attr) {
            // color overwrites through media-api
            return getMediaUrlBase(MEDIA_API_URL) + url + '?' + attr;
        }
    }

    // default -> pre-rendered image, no color overwrites
    return getMediaUrlBase(MEDIA_URL) + url;
};


/*
 * Return the image url for the given image reference in the given
 * image version (size) and shape. If the given image is an SVG file,
 * then the actual file path is based on the 'original' shape.
 */
var getImageShapeVersionSrc = function getImageShapeVersionSrc(img, shape, imageVersion) {
    // construct the full url based on given size and shape. Make sure that
    // the url is absolute and starts with /
    return getFinalMediaUrl(img, (
        'shapes/' +
        shape +
        '/' +
        imageVersion +
        getImagBaseSrc(img)
    ));
};


/*
 * Return the name of the target shape if the given directive matches the given
 * screen width; otherwise undefined.
 */
var matchesArtDirectionDirective = function matchesArtDirectionDirective(directive, width) {
    var minw = directive[0];
    var maxw = directive[1];
    var shape = directive[2];

    if ( (minw === -1 || width >= minw) && (maxw === -1 || width <= maxw) ) {
        return shape;
    }
};


/*
 * Return the name of the shape that best matches the given list of art
 * direction directives based on the given screen width. Each directive encodes
 * a minimum width, a maximum width and the target name of the shape and aspect
 * ratio, where -1 for min. or max. width is obmitted.
 */
var getImageShapeFromArtDirection = function getImageShapeFromArtDirection(directives, width) {
    var shape = undefined;
    for (var i = 0; i < directives.length; i++) {
        var target_shape = matchesArtDirectionDirective(directives[i], width);
        if (target_shape !== undefined) {
            shape = target_shape;
        }
    }
    return shape;
};


/*
 * Determine the shape that is used for the given image reference. The shape
 * may refer to an art direction, in which case we attempt to resolve the actual
 * shape at runtime based on art direction directives (defined in settings) and
 * the actual screen width.
 */
var getImageShape = function getImageShape(img) {
    var shape = img.getAttribute('data-shape');

    // art direction?
    if (shape in ART_DIRECTION) {
        shape = getImageShapeFromArtDirection(
            ART_DIRECTION[shape],
            window.innerWidth
        );

        // if we cannot resolve the art direction into a valid shape,
        // then we simply assume the original shape...
        if (shape === undefined) {
            shape = 'original';
        }
    }

    return shape;
};


/*
 * Get the image url for the particular image version. If this image
 * version is not available, we recursivly ask for the next lower
 * version until we find one that is available. Particular for smaller
 * images, not all sizes are always available.
 */
var getImageVersionSrc = function(img, imageVersion) {
    // blank images always resolve to the orginal uploaded file,
    // since we have to assume that no image processing has been carried out
    // for those images yet...
    if (img.getAttribute('data-blank') === '1') {
        return getOriginalImageSrc(img);
    }

    // determine the target shape
    var shape = getImageShape(img);

    // find an image version that is supported...
    var src = null;
    var sizes = img.getAttribute('data-sizes');
    if (sizes !== undefined && sizes !== null) {
        var supportedSizes = sizes.split('|');
        while (!src && imageVersion) {
            if (supportedSizes.indexOf(imageVersion) !== -1) {
                src = getImageShapeVersionSrc(img, shape, imageVersion);
            }

    		if ( !src ) {
    		    imageVersion = getNextSmallerImageVersion(imageVersion);
    		}
    	}
    }

	return src;
};


/*
 * Load background image by injecting background-image style attribute based
 * on the given size of the given element.
 */
var lazyloadBackgroundImage = function (image, container) {
    // visible?
    if (!isApp && !isElementInViewport(image) ) {
        return;
    }

    // determine if we use height or width.
    var heightAR = image.hasAttribute('data-background-image-height-ar');

    // determine actual width of the element, so that we can determine the
    // size that is needed.
    var containerWidth = getImageWidth(container);
    if (heightAR) {
        heightAR = image.getAttribute('data-background-image-height-ar');
        var imgHeight = getImageHeight(container);
        var imgWidth = imgHeight * heightAR;
        if (imgWidth < containerWidth) {
            imgWidth = containerWidth;
        }
    } else {
        var imgWidth = containerWidth;
    }

    var imageVersion = getImageVersion(imgWidth);
    var src = getImageVersionSrc(image, imageVersion);

    // add background-image style
    image.style.backgroundImage = "url('" + src + "')";

    // indicate that the image has been loaded
    addClass(image, 'lazy-loaded');
};


/*
 * Replace given image container (<noscript>) with an actual image, where
 * the image version depends on the screen resolution of the client device.
 */
var lazyloadImage = function (imageContainer, callback) {
	// no element?
	if (!imageContainer || !imageContainer.children) {
		return;
	}

	// already loaded?
	if ( hasClass(imageContainer, 'lazy-loaded') ) {
	    return;
	}

    // background image?
    if (imageContainer.hasAttribute('data-background-image')) {
        var container = imageContainer;
	    if ( container && container.hasAttribute('data-size') ) {
    	    container = getParentWithAttribute(
    	        container,
    	        'data-size-template'
    	    );
	    }
        return lazyloadBackgroundImage(imageContainer, container);
    }

    // requires children
    if (!imageContainer.children || imageContainer.children.length === 0) {
        return;
    }

	var padder = imageContainer.children[0];
    var img = padder.children[0];
    var originalImageContainer = imageContainer;

	if (img) {
	    var imgWidth = 0;
	    var container = img.parentNode.parentNode.parentNode;
	    if ( container && container.hasAttribute('data-size') ) {
	        // some images might not have a width because they are not visible
    	    // (for example a carousel). We identify those cases, where the
    	    // direct parent has the attribute 'data-size'. In this case we scan
    	    // throught all parents to find the one with the attribute
    	    // 'data-size-template' and use it for measuring the size instead.
    	    imageContainer = getParentWithAttribute(
    	        container,
    	        'data-size-template',
                container.hasAttribute('when-visible')
    	    );

            if (!imageContainer) return;
	    }

	    // if this sits inside a lightbox, determine the image to use for
	    // fullscreen lightbox...
	    if ( container && hasClass(container, 'lightbox') && !container.getAttribute('href') ) {
	        var w = getWindowWidth();
	        var lightboxSrc = getImageVersionSrc(img, getImageVersion(w));
	        container.setAttribute('href', lightboxSrc);
	    }

        // do not proceed if the image (or its container) is not on the screen
        // (does not apply for apps)
        if (!isApp && !isElementInViewport(imageContainer) ) {
            return;
        }

        // determine actual width of the image, so that we can determine the
        // size that is needed. We do this based on the width of the image
        // rather than the screen width, since we may have an image that is not
        // stretched out to the full screen width.
        if ( imageContainer ) {
    	    imgWidth = getImageWidth(imageContainer);
    	}

	    // determine the image size that we have to load for this image taking
	    // into consideration the width of the image placeholder (as determined
	    // above) and the device pixel ratio (e.g. retina displays).
	    var imageVersion = getImageVersion(imgWidth);

	    // get the image url for the particular image version.
	    var src = getImageVersionSrc(img, imageVersion);

	    // inject proper image tag in the correct size and alt tag and remove
	    // noscript tag.
		if (src) {
            // get meta data
    		var alt = img.getAttribute('data-alt');
            var title = img.getAttribute('data-title');

            // create image element and container
        	if ( hasClass(imageContainer, 'lazy-load-svg') ) {
                // svg-based image with clip path
                var ar = img.getAttribute('data-ar');
                var clippath = img.getAttribute('data-clippath');
        	    createSvgImage(padder, src, title, alt, ar, clippath, callback);
        	} else if (isInlineImage(img) && isSvgImage(img)) {
                // inline svg image
                createInlineImage(padder, src);
            } else {
                // image reference
        	    createHtmlImage(padder, src, title, alt, callback);
        	}
		}
	}

	// indicate that we've processed this image...
	addClass(originalImageContainer, 'lazy-loaded');
};


/*
 * Create a new html-based image tag for loading a responsive image.
 */
var createHtmlImage = function createHtmlImage(container, src, title, alt, callback) {
	var image = new Image();
	image.setAttribute('alt', alt ? alt : '');
    image.setAttribute('title', title ? title : '');

    // loading handler
    image.addEventListener('load',  function() {
        // create new object boundary, so that any inline style, identifiers
        // and references are not leaking into the actual document.
        var obj = document.createElement('object');


		// replace noscript tag and padder
		insertResponsiveImage(container, image);

		// call callback function if available
		if (callback !== undefined) callback(true);
    });

    // start loading image
    image.src = src;
};


/*
 * Download svg image from given source and embeed the actual svg
 * markup into the current document's DOM.
 */
var createInlineImage = function createInlineImage(container, src) {
    // download svg image
    var xhr = new XMLHttpRequest();
    xhr.open('GET', src, true);
    xhr.overrideMimeType('image/svg+xml');
    xhr.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            // inline svg into dom
            insertResponsiveImage(container, xhr.responseXML.documentElement);
        }
    };
    xhr.send();
};


/*
 * Create a new svg-based image tag with svg inline container for loading
 * a responsive image.
 */
var createSvgImage = function createSvgImage(container, src, title, alt, ar, clippath, callback) {
    // create svg container
    var svgContainer = document.createElementNS(SVG_NS, 'svg');
    svgContainer.setAttribute('viewBox', '0 0 100 ' + ar);
    svgContainer.setAttribute('width', '100%');
    svgContainer.setAttribute('height', '100%');

    // create svg image element
    var image = document.createElementNS(SVG_NS, 'image');
    image.setAttribute('width', '100%');
    image.setAttribute('height', '100%');

    // clippath (if available)
    if (clippath) {
        image.style.clipPath = 'url(#' + clippath + ')';
    }

    // loading handler
    image.addEventListener('load',  function() {
		// call callback function if available
		if (callback !== undefined) callback(true);
    });

    // start loading image
    image.setAttributeNS(XLINK_NS, 'href', src);
    svgContainer.appendChild(image);
    insertResponsiveImage(container, svgContainer);
};


/*
 * Replace inner img fallback tag with responsive image.
 */
var insertResponsiveImage = function insertResponsiveImage(container, element) {
    // replace child with actual image data
    container.replaceChild(element, container.children[0]);

    // fire event that the image has been loaded
    var event;
    if (document.createEvent) {
        event = document.createEvent('CustomEvent');
        event.initCustomEvent('lazy-loaded', true, true, {});
    } else {
        event = new CustomEvent(
        	'lazy-loaded',
        	{
        		bubbles: true,
        		cancelable: true
        	}
        );
    }

    container.dispatchEvent(event);
};


/*
 * Lazy-load all images that are in the current viewport. Returns the amount of
 * images that were loaded.
 */
var lazyLoadImages = function () {
    var images = getLazyLoadImages();

    for ( var i = 0; i < images.length; i++ ) {
        lazyloadImage(images[i]);
    }

    lastLoad = new Date().getTime();
};


/*
 * Load one lazy load image and call given callback function when the image has
 * been loaded.
 */
var lazyLoadNextImage = function(callback) {
    var images = getLazyLoadImages();
    if (images.length > 0) {
        lazyloadImage(images[0], callback);
    } else {
        callback(false);
    }
};


/*
 * Defered image loader. This function may be called quite frequently (for
 * example as a responder to resize or scroll events). However, we will defer
 * loading images by a certain amount of time, so that subsequent calls may
 * not execute the image loader directly.
 */
var imageLoader = function () {
    if ( timeout ) clearTimeout(timeout);

    var timeEllapsed = lastLoad !== null ? new Date().getTime() - lastLoad : 0;
    var timeRemaining = Math.max(0, 250 - timeEllapsed);

    timeout = setTimeout(lazyLoadImages, timeRemaining);
};


/*
 * Return a list of all scrollable containers that we need to watch for
 * scroll events to happen.
 */
var getScrollableContainers = function() {
    if ( document.querySelectorAll ) {
        return document.querySelectorAll('.lazy-load-container');
    } else {
        return document.getElementsByClassName('lazy-load-container');
    }
};


/*
 * Watch given list of containers for scroll events to happen, in which case
 * we lazy-load images.
 */
var watchScrollableContainers = function(containers) {
    for ( var i = 0; i < containers.length; i++ ) {
        watchScrollableContainer(containers[i]);
    }
};


/*
 * Watch given container for scroll events to happen, in which case
 * we laz-load images inside the given container.
 */
var watchScrollableContainer = function(container) {
    if (window.addEventListener) {
        container.addEventListener('scroll', imageLoader, false);
    } else if (window.attachEvent)  {
        container.attachEvent('scroll', imageLoader);
    }
};


/*
 * Lazy-load all images that have not been loaded yet.
 */
var lazyloadImagesWhenVisible = function () {
    // Initially load all images that are visible to begin with, nothing more...
    lazyLoadImages();

    // then we watch viewport scroll events to load images when we need to...
    if (window.addEventListener) {
        addEventListener('scroll', imageLoader, false);
        addEventListener('resize', imageLoader, false);
    } else if (window.attachEvent)  {
        attachEvent('scroll', imageLoader);
        attachEvent('resize', imageLoader);
    }

    // watch any scrollable containers for scrolling
    watchScrollableContainers(getScrollableContainers());
};


/*
 * Refresh scrollable container
 */
var lazyLoadRefreshContainer = function() {
    watchScrollableContainers(getScrollableContainers());
};


/*
 * Create a new lazy-load image at runtime.
 */
var createLazyloadImage = function createLazyloadImage(container, data, shape) {
    var ar = getAspectRatioPercentForShape(shape, data.ar);

    var html = (
        '<span class="lazy-load><span class="lazy-load-shape-' + shape + '"' +
        (shape == 'original' ? ' style="padding-bottom:' + ar + '%;"' : '') + '>' +
        '<noscript' +
        ' data-shape="' + shape + '"' +
        ' data-path="' + data.path + '"' +
        ' data-blank="' + (data.is_blank ? '1' : '0') + '"' +
        ' data-sizes="' + data.sizes.join('|') + '"' +
        ' data-alt="' + data.caption + '"' +
        ' data-title="' + data.caption + '"' +
        ' data-svg="' + (data.is_svg ? '1' : '0') + '"' +
        '><img src="' +
        data.def_url + '" alt="' + data.caption + '"' +
        ' title="' + data.caption + '"' +
        '></noscript></span></span>'
    );

    container.innerHTML = html;
};


var createLazyloadBackgroundImage = function createLazyloadBackgroundImage(container, data, shape) {
    var ar = getAspectRatioPercentForShape(shape, data.ar);

    container.setAttribute('data-background-image', '');
    container.setAttribute('data-shape', shape);
    container.setAttribute('data-path', data.path);
    container.setAttribute('data-blank', data.is_blank ? '1' : '0');
    container.setAttribute('data-sizes', data.sizes.join('|'));
    container.setAttribute('data-svg', data.is_svg ? '1' : '0');
    container.setAttribute('data-background-image-height-ar', ar);
    container.classList.add('lazy-load');
    container.classList.remove('lazy-loaded');
};


// Make lazyload available publicly, so other components can manually trigger
// to lazy load images whenever this may become neccessary after the DOM
// has changed for example by reinjecting new markup (including images) into
// the DOM.
document.lazyloadImages = lazyLoadImages;

// Provide a way to load only one image at a time
document.lazyloadNextImage = lazyLoadNextImage;
document.lazyloadRefreshContainer = lazyLoadRefreshContainer;

// Provide a way to inject layz-load constructs at runtime
document.createLazyloadImage = createLazyloadImage;
document.createLazyloadBackgroundImage = createLazyloadBackgroundImage;

// Provide ability to watch containers that have been added dynamically...
document.watchScrollableContainer = watchScrollableContainer;

// Load all images on DOM ready (we assume this is inlined at the bottom of the
// website, so we do not need to wait for the DOM-ready event.
lazyloadImagesWhenVisible();


}(this));

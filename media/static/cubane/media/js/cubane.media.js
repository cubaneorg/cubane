(function (globals){
"use strict";


cubane.namespace('cubane.media');


cubane.require('cubane.dom');
cubane.require('cubane.urls');
cubane.require('cubane.dialog');


var droppedFiles = undefined;


function setup() {
    // files changed
    var fileInput = document.querySelector('input[type=file]');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            var holder = cubane.dom.closest(fileInput, '.cubane-file-upload');
            onImageChanged(holder, e.target.files);
        });
    }

    // set image boundaries
    window.addEventListener('resize', setImageBoundaries);
    setImageBoundaries();

    // image drag and drop
    var container = document.querySelectorAll('.cubane-file-upload');
    for (var i = 0; i < container.length; i++) {
        setupDragAndDrop(container[i]);
    }

    // submit
    for (var i = 0; i < container.length; i++) {
        setupUpload(container[i]);
    }

    // set initial focal point
    setupFocalPoint();

    // set shape previews
    window.addEventListener('resize', updateCropPreviews);
    updateCropPreviews();
}


/*
 * Setup drag and drop support for given drop target
 */
function setupDragAndDrop(holder) {
    holder.ondragover = function () {
        this.classList.add('hover');
        return false;
    };

    holder.ondragleave = function() {
        this.classList.remove('hover');
        return false;
    }

    holder.ondragend = function () {
        this.classList.remove('hover');
        return false;
    };

    holder.ondrop = function (e) {
        e.preventDefault();

        this.classList.remove('hover');

        // single or multiple?
        var input = holder.querySelector('input[type="file"]');
        if (input.getAttribute('multiple') === 'multiple') {
            droppedFiles = e.dataTransfer.files;
        } else {
            droppedFiles = [e.dataTransfer.files[0]];
        }

        onImageChanged(holder, droppedFiles);
    };
}


/*
 * Setup form data upload
 */
function setupUpload(holder) {
    var form = cubane.dom.closest(holder, 'form');
    if (form) {
        form.addEventListener('submit', onUploadFormSubmit);

        var input = form.querySelector('input[type="file"]');
        if (input) {
            input.required = false;
        }
    }
}


/*
 * Ensures that the given image is loaded and then calls the given callback.
 */
function ensureImageLoaded(img, callback) {
    if (!img) return;

    var handler = function() {
        img.removeEventListener('load', handler);
        callback();
    };

    if (!img.naturalWidth || !img.naturalHeight) {
        img.addEventListener('load', handler);
    } else {
        handler();
    }
}


/*
 * Set max. boundaries for the image based on the aspect ratio of the image.
 */
function setImageBoundaries() {
    // wait for the image to be fully loaded, so that we have image dimensions
    var img = document.querySelector('.cubane-media-editor-preview-panel-frame img');
    if (!img) return;

    ensureImageLoaded(img, function() {
        if (img.naturalHeight == 0) return;

        var frame = document.querySelector('.cubane-media-editor-preview-frame');
        var panel = document.querySelector('.cubane-media-editor-preview-panel');
        var ar = img.naturalWidth / img.naturalHeight;
        var w = frame.offsetWidth;
        var h = w / ar;
        if (h > frame.offsetHeight) {
            h = frame.offsetHeight;
            w = h * ar
        }

        panel.style.width = w.toString() + 'px';
        panel.style.height = h.toString() + 'px';
    });
}


/*
 * Return the crop rectangle for an image with given width and height to
 * be cropped and fitted into the given target width and height.
 * The resulting crop width and height might be smaller (or larger) than the
 * given target width and height depending on the input image size; however
 * the aspect ratio is the same.
 * The crop region is based around the given focal point which describes the
 * main focal point of the image which should become the center of the new
 * image. If no focal point is given, the image center position is assumed.
 * Focal point coordinates are in relative coordinates between 0.0 and 1.0.
 */
function getImageCropArea(width, height, targetWidth, targetHeight, fx, fy) {
    // division by zero guarde
    if (!targetHeight || !targetHeight || !width || !height)
        return {
            x: 0,
            y: 0,
            w: Math.round(targetWidth),
            h: 0
        };

    // focal point
    if (isNaN(fx)) fx = 0.5;
    if (isNaN(fy)) fy = 0.5;
    fx = Math.max(0, Math.min(1, fx));
    fy = Math.max(0, Math.min(1, fy));

    // aspect ratios
    var srcAR = width / height;
    var targetAR = targetWidth / targetHeight;
    var srcLandscape = srcAR > 1;
    var targetLandscape = targetAR > 1;

    // focal point in image space
    var imgFx = width * fx;
    var imgFy = height * fy;

    // find largest possible crop region where focal point is relative to
    // where it is in the original image (binary search)...
    var top = width;
    var bottom = 0;
    var targetThreshold = targetWidth * 1.01;
    var w = top;
    var i = 0;
    while (true) {
        var h = w / targetAR;
        var x = imgFx - (fx * w);
        var y = imgFy - (fy * h);

        if (w < targetThreshold) {
            if (x < 0) x = 0;
            if (y < 0) y = 0;
            if (x + w > width) x = width - w;
            if (y + h > height) y = height - h;
        }

        var valid = x >= 0 && y >= 0 && x + w <= width && y + h <= height;
        if (valid) {
            // valid -> increase
            bottom = w;
        } else {
            // not valid -> decrease
            top = w;
        }

        w = bottom + ((top - bottom) / 2);

        // good enought?
        if (valid && top - bottom < 1)
            break;

        i++;
        if (i > 10) break;
    }

    if (x < 0) x = 0;
    if (y < 0) y = 0;

    // return crop region (integers)
    return {
        x: Math.round(x),
        y: Math.round(y),
        w: Math.round(w),
        h: Math.round(h)
    };
}


/*
 * Update the crop preview images based on the current focal point and image.
 */
function updateCropPreviews() {
    // get focal point
    var fx = parseFloat(document.querySelector('#id_focal_x').value);
    var fy = parseFloat(document.querySelector('#id_focal_y').value);

    if (isNaN(fx)) fx = 0.5;
    if (isNaN(fy)) fy = 0.5;

    // get preview image shapes
    var shapes = document.querySelectorAll('.cubane-media-editor-shape');
    if (shapes.length === 0) return;
    var img = document.querySelector('.cubane-media-editor-preview-panel-frame img');
    if (!img) return;

    ensureImageLoaded(img, function() {
        var width = img.naturalWidth;
        var height = img.naturalHeight;
        var targetWidth = shapes[0].offsetWidth;

        function _updateCropForShape(shape, img) {
            ensureImageLoaded(img, function() {
                // determine crop area for the shape
                var ar = parseFloat(shape.getAttribute('data-ar'));
                var targetHeight = targetWidth / ar;
                var crop = getImageCropArea(width, height, targetWidth, targetHeight, fx, fy);

                // adjust image width and position
                var r = targetWidth / crop.w;
                img.width = width * r;
                img.style.webkitTransform =
                img.style.transform =
                    'translate(' + (-crop.x * r).toString() + 'px, ' + (-crop.y * r).toString() + 'px)';
            });
        }

        // process shapes
        for (var i = 0; i < shapes.length; i++) {
            // make sure that we have the correct image for all preview shapes
            var shapeImg = shapes[i].querySelector('img');
            if (shapeImg.src != img.src) {
                shapeImg.src = img.src;
            }

            // update crop placement
            _updateCropForShape(shapes[i], shapeImg, i == 0);
        }
    });
}


/*
 * Setup focal point editor
 */
function setupFocalPoint() {
    // editor required
    var editor = document.querySelector('.cubane-media-editor');
    if (!editor) return;

    // image required, does not work for documents
    var isImages = editor.getAttribute('data-images') === 'True';
    if (!isImages) return;

    var target = editor.querySelector('.cubane-media-editor-focal-point');

    // interact
    interact('.cubane-media-editor-focal-point').draggable({
        inertia: true,
        restrict: {
            restriction: 'parent',
            endOnly: true,
            elementRect: { top: 0.5, left: 0.5, bottom: 0.5, right: 0.5 }
        },
        onmove: dragMoveListener
    });

    // move handler
    function dragMoveListener (event) {
        var x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx;
        var y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;
        setFocalPointFromScreen(x, y);
        updateCropPreviews();
    }

    // resize
    window.addEventListener('resize', function() {
        var focal_x = document.querySelector('#id_focal_x');
        var focal_y = document.querySelector('#id_focal_y');
        if (focal_x && focal_y) {
            setFocalPointFromCoords(parseFloat(focal_x.value), parseFloat(focal_y.value));
        }
    });

    // enable if we are in edit mode, which means that we should have an image
    var isEdit = editor.getAttribute('data-edit') === 'True';
    if (isEdit) {
        enableFocalPoint(false);
    }

    // allow auto detect focal point (button)
    document.querySelector('.cubane-media-editor-auto-detect-focal-point').addEventListener('click', function(e) {
        e.preventDefault();
        enableFocalPoint(true);
    });

    // allow for resetting focal point to center position
    document.querySelector('.cubane-media-editor-center-focal-point').addEventListener('click', function(e) {
        e.preventDefault();
        enableFocalPoint(true, 0.5, 0.5);
    });

    // auto-detection of focal point supported by browser?
    if (!supportsAutoDetectFocalPoint()) {
        $('.cubane-media-editor-auto-detect-focal-point').hide();
    }
}


/*
 * Set focal point position from screen coordinates.
 */
function setFocalPointFromScreen(screenX, screenY) {
    var target = document.querySelector('.cubane-media-editor-focal-point');
    if (!target) return;

    var panel = document.querySelector('.cubane-media-editor-preview-panel');
    var focal_x = document.querySelector('#id_focal_x');
    var focal_y = document.querySelector('#id_focal_y');
    if (!focal_x || !focal_y) return;

    // translate the element
    target.style.webkitTransform =
    target.style.transform =
        'translate(' + screenX + 'px, ' + screenY + 'px)';

    // update the posiion attributes
    target.setAttribute('data-x', screenX);
    target.setAttribute('data-y', screenY);

    // update form fields (relative coordinates)
    focal_x.value = (screenX + 50) / panel.offsetWidth;
    focal_y.value = (screenY + 50) / panel.offsetHeight;
}


/*
 * Set focal point position from relative coordinates.
 */
function setFocalPointFromCoords(x, y) {
    if (!isNaN(x) && !isNaN(y)) {
        var panel = document.querySelector('.cubane-media-editor-preview-panel');
        if (panel) {
            x = (panel.offsetWidth * x) - 50;
            y = (panel.offsetHeight * y) - 50;
            setFocalPointFromScreen(x, y);
        }
    }
}


/*
 * Enable focal point
 */
function enableFocalPoint(newImage, newX, newY) {
    if (newImage === undefined) newImage = false;

    var target = document.querySelector('.cubane-media-editor-focal-point');
    if (!target) return;

    // set initial position. Use centre position if no focal point is
    // available yet...
    var focal_x = document.querySelector('#id_focal_x');
    var focal_y = document.querySelector('#id_focal_y');
    if (focal_x && focal_y) {
        var initialX = parseFloat(focal_x.value);
        var initialY = parseFloat(focal_y.value);

        function applyFocalPoint(x, y) {
            setFocalPointFromCoords(x, y);
            target.classList.add('active');
            updateCropPreviews();
        }

        if (isNaN(initialX) || isNaN(initialY) || newImage) {
            // default focal point
            initialX = 0.5;
            initialY = 0.5;

            // detect focal point automatically if this is a new image
            if (newImage) {
                if (newX && newY) {
                    initialX = newX;
                    initialY = newY;
                } else if (supportsAutoDetectFocalPoint()) {
                    // auto-detect
                    var img = document.querySelector('.cubane-media-editor-preview-panel-frame img');
                    ensureImageLoaded(img, function() {
                        smartcrop.crop(img, {width: 100, height: 100}).then(function(result){
                            var x = (result.topCrop.x + (result.topCrop.width / 2)) / img.naturalWidth;
                            var y = (result.topCrop.y + (result.topCrop.height / 2)) / img.naturalHeight;
                            applyFocalPoint(x, y);
                        });
                    });
                    return;
                }
            }
        }

        applyFocalPoint(initialX, initialY);
    }
}


/*
 * Return True, if the browser can support the auto-detection of the focal
 * point. We need a modern browser with Promise support for this to work.
 */
function supportsAutoDetectFocalPoint() {
    return window.Promise !== undefined;
}


/*
 * Disable focal point
 */
function disableFocalPoint() {
    var target = document.querySelector('.cubane-media-editor-focal-point');
    if (!target) return;

    target.classList.remove('active');
}


/*
 * Handle form submit and upload media data
 */
function onUploadFormSubmit(e) {
    e.preventDefault();

    // get form and elements...
    var form = cubane.dom.closest(e.target, 'form');
    var input = form.querySelector('input[type="file"]');
    var editor = cubane.dom.closest(form, '.cubane-media-editor');

    // prevent duplicate submission...
    if (form.classList.contains('uploading')) return;
    form.classList.add('uploading');

    // construct upload form data and append data that was dragged and
    // dropped...
    var data = new FormData(form);
    if (droppedFiles) {
        for (var i = 0; i < droppedFiles.length; i++) {
            data.append(input.name, droppedFiles[i]);
        }
    }

    var dlg = cubane.dialog.progress(
        'Uploading files...',
        'Uploading files...Please Wait...'
    );
    var processing = false;
    var completed = false;
    var progressId = Math.random();
    var progressUrl = cubane.urls.reverse('cubane.backend.progress') + '?progressId=' + progressId;
    var action = form.getAttribute('action');
    if (!action) action = document.location.href;
    action = cubane.urls.combineUrlArg(action, 'progressId', progressId);
    $.ajax({
        url: action,
        type: form.getAttribute('method'),
        data: data,
        dataType: 'json',
        cache: false,
        contentType: false,
        processData: false,
        xhr: function(){
            //upload Progress
            var xhr = $.ajaxSettings.xhr();
            if (xhr.upload) {
                xhr.upload.addEventListener('progress', function(event) {
                    // calculate progress (percent)
                    var percent = 0;
                    var position = event.loaded || event.position;
                    var total = event.total;
                    if (event.lengthComputable) {
                        percent = Math.ceil(position / total * 100);
                    }

                    // report progress made
                    dlg.progress(percent);

                    if (!processing && percent > 99) {
                        // we're done upload. Now we need to monitor progress
                        // being made on the server side while processing
                        // all uploaded media files...
                        processing = true;
                        cubane.dialog.closeAll();
                        dlg = cubane.dialog.progress(
                            'Processing data...',
                            'Processing uploaded data. This may take a moment...Please Wait...'
                        );

                        var interval = setInterval(function() {
                            $.getJSON(progressUrl, function(json) {
                                dlg.progress(json.percent);

                                if (json.percent > 99 || completed) {
                                    clearInterval(interval);
                                }
                            });
                        }, 1000);
                    }
                }, true);
            }
            return xhr;
        },
        complete: function() {
            dlg.progress(100);
            completed = true;
            form.classList.remove('uploading');
            cubane.dialog.closeAll();
        },
        success: function(json) {
            if (json.success) {
                if ($('body').hasClass('create-dialog') && window.parent !== window) {
                    window.parent.$(window.parent).trigger('cubane-listing-create', [{
                        id: json.instance_id,
                        title: json.instance_title
                    }]);
                } else if ($('body').hasClass('browse-dialog') && window.parent !== window) {
                    if (json.next) {
                        document.location = json.next;
                    }
                } else if ($('body').hasClass('index-dialog') && window.parent !== window) {
                    window.parent.$(window.parent).trigger('cubane-close-index-dialog');
                } else if ($('body').hasClass('edit-dialog') && window.parent !== window) {
                    window.parent.$(window.parent).trigger('cubane-listing-edit', [{
                        id: json.instance_id,
                        title: json.instance_title
                    }]);
                } else if (json.next) {
                    document.location = json.next;
                } else {
                    document.location.reload();
                }
            } else {
                if (json.errors) {
                    cubane.backend.presentFormErrors(form, json.errors);
                } else {
                    document.location.reload();
                }
            }
        }
    });
}


/*
 * Uploaded image changed
 */
function onImageChanged(holder, files) {
    // reflect selected image label in upload box
    var label = holder.querySelector('.cubane-file-label');
    if (label) {
        label.innerText = files.length > 1 ? (files.length + ' files selected') : files[0].name;
    }

    // enable/disable caption input field, which does not apply if we are
    // uploading multiple images at once...
    var container = document.getElementById('id_caption');
    if (container) {
        container = cubane.dom.closest(container, '.control-group');
        if (files.length > 1) {
            container.style.display = 'none';
        } else {
            container.style.display = 'block';
        }
    }

    // toggle between preview panel and preview images, depending on
    // whether we have multiple images or not...
    var editor = document.querySelector('.cubane-media-editor');
    if (editor) {
        var isImages = editor.getAttribute('data-images') === 'True';
        var images = document.querySelector('.cubane-media-editor-preview-images');
        var panelFrame = document.querySelector('.cubane-media-editor-preview-panel-frame');
        if (files.length > 1) {
            editor.classList.add('multiple');
            images.innerText = '';
            for (var i = 0; i < files.length; i++) {
                getFileUrl(files[i], function(url) {
                    addPreviewImageFromUrl(url, isImages);
                });
            }

            // focal point not available
            disableFocalPoint();
        } else {
            panelFrame.innerText = '';
            editor.classList.remove('multiple');
            getFileUrl(files[0], function(url) {
                createPreviewImageFromUrl(url, isImages);

                // enable focal point when working with single image
                if (isImages) {
                    setImageBoundaries();
                    enableFocalPoint(true);
                }
            });
        }

        // check save and continue, which we cannot do if this is a create
        // with multiple assets...
        var isEdit = editor.getAttribute('data-edit') === 'True';
        if (!isEdit && files.length > 1) {
            $('.btn-save-and-continue').hide();
        } else {
            $('.btn-save-and-continue').show();
        }
    }
}


/*
 * Return the file url for the given file object.
 */
function getFileUrl(file, loaded) {
    if (URL.createObjectURL) {
        loaded(URL.createObjectURL(file));
    } else {
        var reader = new FileReader();
        reader.onload = function (event) {
            loaded(event.target.result);
        };
        reader.readAsDataURL(file);
    }
}


/*
 * Add given image as a preview image from given image url (multiple files).
 */
function addPreviewImageFromUrl(url, isImages) {
    var images = document.querySelector('.cubane-media-editor-preview-images');
    var node = document.createElement('div');
    if (isImages) {
        node.classList.add('cubane-media-editor-preview-image');
        node.style.backgroundImage = 'url(' + url + ')';
        images.appendChild(node);
    }
}


/*
 * Create new preview image for the given url (single file).
 */
function createPreviewImageFromUrl(url, isImages) {
    var panelFrame = document.querySelector('.cubane-media-editor-preview-panel-frame');

    if (isImages) {
        var node = document.createElement('img');
        node.src = url;
        node.alt = '';
    } else {
        var node = document.createElement('iframe');
        node.src = cubane.urls.reverse('cubane.cms.documents.preview') + '?url=' + url;
    }

    panelFrame.appendChild(node);
}


/*
 * Init
 */
if (document.querySelector('.cubane-file-upload')) {
    setup();
}


}(this));

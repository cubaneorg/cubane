/*
 * Provides the ability to insert cms images to a page.
 * Based on the tinymce image plugin.
 *
 * This implementation is based on the original tinymce plugin "image".
 */
tinymce.PluginManager.add('cubaneimage', function(editor) {
	function getImageSize(url, callback) {
        // valid image url?
        if (!url) return;

		var img = document.createElement('img');

		function done(width, height) {
			img.parentNode.removeChild(img);
			callback({width: width, height: height});
		}

		img.onload = function() {
			done(img.clientWidth, img.clientHeight);
		};

		img.onerror = function() {
			done();
		};

		img.src = url;

		var style = img.style;
		style.visibility = 'hidden';
		style.position = 'fixed';
		style.bottom = style.left = 0;
		style.width = style.height = 'auto';

		document.body.appendChild(img);
	}


    /*
     * Get list of images and call given callback if such list is available
     * (which may take a bit if we are going over the wire to the it).
     */
	function createImageList(callback) {
		return function() {
			var imageList = editor.settings.image_list;

			if (typeof(imageList) == "string") {
				tinymce.util.XHR.send({
					url: imageList,
					success: function(text) {
						callback(tinymce.util.JSON.parse(text));
					}
				});
			} else {
				callback(imageList);
			}
		};
	}


    /*
     * Present image dialog that allows users to select the image they want to
     * insert or to change an existing image.
     */
	function showDialog(imageList) {
		var win, data, dom = editor.dom, imgElm = editor.selection.getNode();
		var width, height, imageListCtrl;
        var imgWidth, imgHeight;

		function buildImageList() {
			var linkImageItems = [{text: '-------', value: ''}];

			tinymce.each(imageList, function(link) {
				linkImageItems.push({
					text: link.caption,
					value: link.url,
				});
			});

			return linkImageItems;
		}

		function getImageIdByUrl(url) {
		    for ( var i = 0; i < imageList.length; i++ ) {
		        if ( imageList[i].url === url ) {
		            return imageList[i].id;
		        }
		    }
		    return null;
		}

        function getImageUrlById(id) {
		    for ( var i = 0; i < imageList.length; i++ ) {
		        if ( imageList[i].id == id ) {
		            return imageList[i].url;
		        }
		    }
		    return null;
        }

		function recalcSize(e) {
			var widthCtrl, heightCtrl, newWidth, newHeight;

            if (!imgWidth || !imgHeight)
                return;

			widthCtrl = win.find('#width')[0];
			heightCtrl = win.find('#height')[0];
			newWidth = widthCtrl.value();
			newHeight = heightCtrl.value();

            if (isNaN(newWidth) || isNaN(newHeight))
                return;

            // overflow width
            if (newWidth > imgWidth) {
                newWidth = imgWidth;
                widthCtrl.value(newWidth);
            }

            // overflow height
            if (newHeight > imgHeight) {
                newHeight = imgHeight;
                heightCtrl.value(newHeight);
            }

            // change corresponding dimension according to AR.
            var ar = imgWidth / imgHeight;
			if (e.control == widthCtrl) {
				newHeight = Math.round(newWidth / ar);
				heightCtrl.value(newHeight);
			} else {
				newWidth = Math.round(newHeight * ar);
				widthCtrl.value(newWidth);
			}

			width = newWidth;
			height = newHeight;
		}

		function onSubmitForm() {
			function waitLoad(imgElm) {
				function selectImage() {
					imgElm.onload = imgElm.onerror = null;
					editor.selection.select(imgElm);
					editor.nodeChanged();
				}

				imgElm.onload = function() {
					if (!data.width && !data.height) {
						dom.setAttribs(imgElm, {
							width: imgElm.clientWidth
						});
					}

					selectImage();
				};

				imgElm.onerror = selectImage;
			}

			var data = win.toJSON();

			if (data.width === '') {
				data.width = null;
			}

			if (data.height === '') {
				data.height = null;
			}

            // not sure what this is about. Perhabs it rebuilds data from
            // scratch in order to delete some properties?
			var customsize = data.customsize;
			var _id = getImageIdByUrl(data.src);
			data = {
				src: data.src,
				alt: '',
				width: data.width,
				'data-width': data.width,
				'data-height': data.height,
				'data-cubane-lightbox': data.lightbox
			};

			editor.undoManager.transact(function() {
				if (!data.src) {
					if (imgElm) {
						dom.remove(imgElm);
						editor.nodeChanged();
					}

					return;
				}

                // remove width and height attributes if we go for a custom
                // image size...
			    if ( !customsize ) {
			        data.width = null;
			        data.height = null;
			    }

				if (!imgElm) {
				    // inserting new image into document, but wrap the image
                    // into a block element to prevent tinymce from placing
                    // the img tag inside p tags by default. In particular when
                    // using tiny-mce's alignment options, this works better
                    // because the alignment is actually applied to the image
                    // and not to the paragraph.
					data.id = '__mcenew';
                    var img = dom.createHTML('img', data);
                    var div = '<div>' + img + '</div>';
					editor.selection.setContent(div);
					imgElm = dom.get(data.id);
				} else {
				    // updating existing image...
					dom.setAttribs(imgElm, data);
				}

				dom.setAttrib(imgElm, 'id', null);
				dom.setAttrib(imgElm, 'data-cubane-media-id', _id);
      		    dom.setAttrib(imgElm, 'data-cubane-media-size', customsize ? 'custom' : 'auto');

				waitLoad(imgElm);
			});
		}

		function updateSize(imageUrl) {
			getImageSize(imageUrl, function(data) {
				if (data.width && data.height) {
					width = data.width;
					height = data.height;

                    // assign new image size
                    imgWidth = width;
                    imgHeight = height;

                    // update custom size input fields
					var _widthField = win.find('#width');
					var _heightField = win.find('#height');
                    if (!_widthField.value() && !_heightField.value()) {
                        // both fields are empty, so simply put the new
                        // dimensions in
                        _widthField.value(width);
                        _heightField.value(height);
                    } else if (!_widthField.value()) {
                        // determine new size based on height
                        recalcSize({control: win.find('#height')[0]});
                    } else {
                        // determine new size based on width
                        recalcSize({control: win.find('#width')[0]});
                    }
				}
			});
		}

        // configure form with default values...
     	width = dom.getAttrib(imgElm, 'data-width');
		height = dom.getAttrib(imgElm, 'data-height');
		if (imgElm.nodeName == 'IMG' && !imgElm.getAttribute('data-mce-object')) {
			data = {
				src: dom.getAttrib(imgElm, 'src'),
				customsize: dom.getAttrib(imgElm, 'data-cubane-media-size') === 'custom',
				width: width,
				height: height,
				lightbox: dom.getAttrib(imgElm, 'data-cubane-lightbox') === 'true'
			};
		} else {
			imgElm = null;
		}

        // create image selection dropdown...
		if (imageList) {
			imageListCtrl = {
				name: 'src',
				type: 'listbox',
				label: 'Image list',
				autofocus: true,
				minWidth: 300,
				values: buildImageList(),
				onselect: function(e) {
					updateSize(e.control.value());
				}
			};
		}

		// dialog layout
		var generalFormItems = [
		    {
			    type: 'container',
			    label: 'Image',
			    layout: 'flex',
			    direction: 'row',
			    spacing: 5,
			    items: [
			        imageListCtrl,
			        {
			            name: 'btnBrowseImage',
			            text: 'Browse',
			            type: 'button',
			        }
			    ]
			},
			{name: 'lightbox', label: 'Lightbox', type: 'checkbox', text: 'Clicking the image presents a larger version'},
			{name: 'customsize', label: 'Size', type: 'checkbox', text: 'Custom Image Size'},
			{
				type: 'container',
				name: 'dim',
				label: ' ',
				layout: 'flex',
				direction: 'row',
				align: 'center',
				spacing: 5,
				items: [
					{name: 'width', type: 'textbox', maxLength: 4, size: 4, onchange: recalcSize},
					{type: 'label', text: 'x'},
					{name: 'height', type: 'textbox', maxLength: 4, size: 4, onchange: recalcSize},
				]
			}
		];

        // open dialog
		win = editor.windowManager.open({
			title: 'Insert/Edit Image',
			data: data,
			body: generalFormItems,
			width: 500,
			height: 150,
			onSubmit: onSubmitForm
		});

        // provide custom image size checkbox, so that we are able to insert
        // images that auto-resize by themselves and images with a fixed
        // size.
        var src = win.find('#src')[0];
		var dim = win.find('#dim')[0];
		var customsize = win.find('#customsize')[0];
		var onCustomImageSizeChanged = function() {
		    if ( customsize.checked() ) {
                dim.show();
                recalcSize({control: win.find('#width')[0]});
            } else {
                dim.hide();
            }
		};
		customsize.on('click', onCustomImageSizeChanged);
		onCustomImageSizeChanged();

        // determine initial width and height of the image
        updateSize(src.value());

        // re-calc. size whenever we change a value for custom width/height
        var _width = win.find('#width')[0];
        var _height = win.find('#height')[0];
        _width.on('keyup', recalcSize);
        _height.on('keyup', recalcSize);

		// browse button
		var btnBrowse = win.find('#btnBrowseImage')[0];
		btnBrowse.on('click', function() {
		    cubane.dialog.iframe('Browse Images', '/admin/images/?browse=true', {
                onOK: function(iframe) {
                    // TODO: Are we on create page?
                    if ($(iframe).contents().find('body').hasClass('create-edit-page')) {
                        $(iframe).contents().find('form.form-horizontal').submit();
                        return true;
                    }

                    var itemJson = cubane.backend.getItemJson();
                    if (itemJson.length === 1 ) {
                        var imageUrl = getImageUrlById(itemJson[0].id);
                        src.value(imageUrl);
                        updateSize(src.value());
                    }
                }
            });
		});
	}


	editor.addButton('image', {
		icon: 'image',
		tooltip: 'Insert/edit image',
		onclick: createImageList(showDialog),
		stateSelector: 'img:not([data-mce-object])'
	});

	editor.addMenuItem('image', {
		icon: 'image',
		text: 'Insert image',
		onclick: createImageList(showDialog),
		context: 'insert',
		prependToContext: true
	});

	// This tinymce version does'nt seem to fire this event.
	// Therefore we simply correct the aspect ratio after
	// we resized (see below: ObjectResizeStart).
	editor.on('ObjectResizeStart', function(e) {
	    e.preventDefault();
	});

	//  fix image proportions after resizing an image
	editor.on('ObjectResized', function(e) {
	    // make sure that we maintain the aspect ratio of the original image
	    // in any case...
	    var img = e.target;
	    editor.dom.setAttrib(img, 'height', null);

        var _width = $(img).width();
        var _height = $(img).height();

	    // for automatic sized images, enter custom sized images...
	    if ( editor.dom.getAttrib(img, 'data-cubane-media-size') === 'auto' ) {
            editor.dom.setAttrib(img, 'data-cubane-media-size', 'custom')
        }

        // update underlying data properties to keep track of current size
        editor.dom.setAttrib(img, 'data-width', _width);
        editor.dom.setAttrib(img, 'data-height', _height);
    });
});

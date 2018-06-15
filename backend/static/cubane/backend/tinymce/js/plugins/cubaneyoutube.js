/*
 * Simple Youtube Plugin based on TinyMCE's original youtube plugin
 * by Gerits Aurelien.
 */
tinymce.PluginManager.add('cubaneyoutube', function(editor) {
    /*
     * Return the youtube video identifier from the given url.
     */
    function getYoutubeIdFromUrl(url) {
        var match = url.match((/^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/));
        return match && match[2].length === 11 ? match[2] : false;
    }


    /*
     * Return the short youtube url based on the given video identifier.
     */
    function getYouttubeUrl(identifier) {
        return 'https://youtu.be/' + identifier;
    }


    /*
     * Return the url to the preview image for the youtube video with the
     * given identifier.
     */
    function getYoutubeImageUrl(identifier) {
        return 'https://img.youtube.com/vi/' + identifier + '/0.jpg';
    }


    /*
     * Return the given options as cleaned data.
     */
    function getCleanedOptions(options) {
        if (options === undefined) options = {};
        return {
            width: options.width || '',
            relatedVideos: (options.relatedVideos === true || options.relatedVideos === 1) ? 1 : 0,
            autoPlay: (options.autoPlay === true || options.autoPlay === 1) ? 1 : 0,
            style: options.style || ''
        }
    }


    /*
     * Return the full (embeddable, iframe-based) url for embedding the youtube
     * video with the given identifier and given options, such as auto-play
     * and related videos.
     */
    function getYouttubeIFrameUrl(identifier, options) {
        options = getCleanedOptions(options);
        return (
            'https://www.youtube.com/embed/' + identifier +
            '?rel=' + options.relatedVideos.toString() +
            '&hd=1' +
            '&autoplay=' + options.autoPlay.toString()
        );
    }


    /*
     * Return the full youtube (iframe) embed code fragement.
     */
    function getYoutubeIFrame(identifier, options) {
        options = getCleanedOptions(options);

        var url = getYouttubeIFrameUrl(identifier, options);
        var display = '';
        var width = '';
        var classes = ['youtube-video'];

        // compute inline style based on custom width
        if (options.width) {
            display = 'block'
            width = 'width:' + options.width.toString() + 'px;';
        } else {
            display = 'block';

            // ignore custom inline style if we do not have a custom width
            options.style = '';
        }

        // rewrite inline style for alignment, replaceing it with classes that
        // are generally used for image alignment...
        var style = options.style.replace(/\s/g, '').toLowerCase();
        if (style === 'float:left;') {
            classes.push('img-align-left');
        } else if (style === 'float:right;') {
            classes.push('img-align-right');
        } else if (style === 'display:block;margin-left:auto;margin-right:auto;') {
            classes.push('img-align-center');
        }

        return (
            '<div class="' + classes.join(' ') + '" style="display:' + display + ';' + width + options.style + '">' +
                '<div style="display:block;position:relative;height:0;padding-bottom:56.24999999999993%;">' +
                    '<iframe style="position:absolute;top:0;left:0;right:0;bottom:0;width:100%;height:100%;" src="' + url + '" frameborder="0" allowfullscreen></iframe>' +
                '</div>' +
            '</div>'
        );
    }


    /*
     * Return placeholder code to be inserted into the editor.
     */
    function getYoutubePlaceholder(identifier, options, id) {
        options = getCleanedOptions(options);
        return (
            '<img id="' + id + '" data-video="youtube" data-mce-object class="youtube-video" style="display:block;" src="' + getYoutubeImageUrl(identifier) + '" ' +
            'alt="" data-identifier="' + identifier + '" ' +
            'width="' + options.width + '" ' +
            'data-width="' + options.width + '" ' +
            'data-related="' + options.relatedVideos.toString() + '" ' +
            'data-autoplay="' + options.autoPlay.toString() + '">'
        );
    }


    /*
     * Open Youtube Dialog Window.
     */
    function openYoutubeDialogWindow() {
        var dom = editor.dom;
        var el = editor.selection.getNode();

		function waitLoad(el) {
			function selectImage() {
				el.onload = el.onerror = null;
				editor.selection.select(el);
				editor.nodeChanged();
			}

			el.onload = selectImage;
            el.onerror = selectImage;
		}

        function onOK() {
            var data = win.toJSON();
            var identifier = getYoutubeIdFromUrl(data.src);

            // clear width if we do not have custo width enabled
            if (!data.customwidth) {
                data.width = '';
            }

            editor.undoManager.transact(function() {
				if (!data.src && el) {
                    // remove element if we do not have a valid src url
					dom.remove(el);
					editor.nodeChanged();
                    return;
				}

                if (!el || !(el.nodeName == 'IMG' && el.getAttribute('data-video'))) {
                    // insert new node
                    var id = tinymce.DOM.uniqueId();
                    var content = getYoutubePlaceholder(identifier, data, id);
                    parent.tinymce.activeEditor.insertContent(content);
                    el = dom.get(id);
                } else {
                    // update existing node
                    dom.setAttrib(el, 'data-video', 'youtube');
                    dom.setAttrib(el, 'data-identifier', identifier);
                    dom.setAttrib(el, 'data-width', data.width);
                    dom.setAttrib(el, 'width', data.width);
                    dom.setAttrib(el, 'data-related', data.relatedVideos === true ? 1 : 0);
                    dom.setAttrib(el, 'data-autoplay', data.autoPlay === true ? 1 : 0);
                    dom.setAttrib(el, 'src', getYoutubeImageUrl(identifier));
                }

                waitLoad(el);
            });

            parent.tinymce.activeEditor.windowManager.close();
        }

        var formItems = [
            {
                name: 'src',
                label: 'Youtube URL',
                text: 'Youtube URL',
                type: 'textbox',
                classes: 'youtube-url-input'
            }, {
                name: 'autoPlay',
                label: 'Autoplay',
                type: 'checkbox',
                text: 'Automatically start playing the video.'
            }, {
                name: 'relatedVideos',
                label: 'Related Videos',
                type: 'checkbox',
                text: 'Show related videos when the video finishes.'
            }, {
				type: 'container',
				name: 'dim',
				label: 'Width',
				layout: 'flex',
				direction: 'row',
				align: 'center',
				spacing: 5,
				items: [
                    {name: 'customwidth', type: 'checkbox', text: 'Custom Width'},
					{name: 'width', type: 'textbox', maxLength: 4, size: 4},
                    {name: 'pixels', type: 'label', text: 'pixels'}
				]
			}
        ];

        // load initial data from dom node
        var data = {};
		if (el && el.nodeName == 'IMG' && el.getAttribute('data-video')) {
            var width = dom.getAttrib(el, 'data-width');
			data = {
				identifier: dom.getAttrib(el, 'data-identifier'),
                customwidth: width !== '',
				width: width,
				height: dom.getAttrib(el, 'data-height'),
				relatedVideos: dom.getAttrib(el, 'data-related') === '1',
                autoPlay: dom.getAttrib(el, 'data-autoplay') === '1'
			};

            data.src = getYouttubeUrl(data.identifier);
		}

        // open dialog window
        var win = editor.windowManager.open({
            title: 'Insert Youtube Video',
            data: data,
            body: formItems,
            width: 500,
            height: 160,
            onSubmit: onOK
        });

        // handle custom width UI visibility state
        var customwidth = win.find('#customwidth')[0];
        var width = win.find('#width')[0];
        var pixels = win.find('#pixels')[0];
		function onCustomWidthChanged() {
		    if (customwidth.checked()) {
                width.show();
                pixels.show();
            } else {
                width.hide();
                pixels.hide();
            }
		};
		customwidth.on('click', onCustomWidthChanged);
		onCustomWidthChanged();
    }


    /*
     * Toolbar button
     */
    editor.addButton('youtube', {
        image: '/static/cubane/backend/tinymce/img/Google-YouTube-128.png',
        classes: 'youtube-btn btn',
        tooltip: 'Insert Youtube Video',
        onclick: openYoutubeDialogWindow,
        stateSelector: 'img[data-video]'
    });


    /*
     * Menu entry
     */
    editor.addMenuItem('youtube', {
        image: '/static/cubane/backend/tinymce/img/Google-YouTube-128.png',
        text: 'Insert Youtube Video',
        onclick: openYoutubeDialogWindow,
        context: 'insert',
        prependToContext: true
    });


    function getContentAttr(s, attrname) {
        var re = RegExp(attrname + '="(.*?)"', 'g');
        var m = re.exec(s);
        if (m && m.length >= 1) {
            return m[1];
        } else {
            return '';
        }
    }


    function getWidthStyle(s) {
        var re = RegExp('width\\s*:\\s*(\\d+)px;', 'g');
        var m = re.exec(s);
        if (m && m.length >= 1) {
            return m[1];
        } else {
            return '';
        }
    }


    function getUrlComponent(s, name) {
        var re = RegExp(name + '=([^&]+)', 'g');
        var m = re.exec(s);
        if (m && m.length >= 1) {
            return m[1];
        } else {
            return '';
        }

    }


    /*
     * Encode Youtube videos as full-embed code when exporting HTML content
     */
    editor.on('GetContent', function(e) {
        e.content = e.content.replace(/<img(.*?)\>/g, function(match, contents, offset, s) {
            if (match.indexOf('data-video=') !== -1) {
                var identifier = getContentAttr(match, 'identifier');
                var options = {
                    style: getContentAttr(match, 'style'),
                    width: getContentAttr(match, 'data-width'),
                    relatedVideos: getContentAttr(match, 'data-related') === '1',
                    autoPlay: getContentAttr(match, 'data-autoplay') === '1'
                }
                return getYoutubeIFrame(identifier, options);
            } else {
                return match;
            }
        });
    });


    /*
     * Decode to Youtube placeholder when loading HTML code into the editor
     */
    editor.on('BeforeSetContent', function(e) {
        e.content = e.content.replace(/<div class="youtube-video".*?(width\s*:\s*(\d+)px;)?<\/div><\/div>/g, function(match, contents, offset, s) {
            var url = getContentAttr(match, 'src');
            var identifier = getYoutubeIdFromUrl(url);
            var options = {
                width: getWidthStyle(match),
                relatedVideos: getUrlComponent(url, 'rel') === '1',
                autoPlay: getUrlComponent(url, 'autoplay') === '1'
            };
            var id = tinymce.DOM.uniqueId();
            return getYoutubePlaceholder(identifier, options, id);
        });
    });
});
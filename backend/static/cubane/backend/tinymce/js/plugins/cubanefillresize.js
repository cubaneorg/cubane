/*
 * Resizes tinymce window automatically to fill maximum space available.
 */
tinymce.PluginManager.add('cubanefillresize', function(editor) {
	var settings = editor.settings;

    // doesn't work in inline mode
	if (editor.settings.inline) {
		return;
	}

	// we should only resize if we are in a tab container or dialog window for
    // frontend editing; otherwise we have to assume that we are editing html
    // content along with other properties...
    var el = editor.getElement();
    var frontendEditing = $('body').hasClass('frontend-editing');
    var shouldResize = frontendEditing || $(el).closest('.tab-content').length > 0;
	if (!shouldResize) {
	    return;
	}

	// only resize if we have the full-height class
	if (!$(el).hasClass('full-height'))
	{
	    return;
	}

    /*
     * Resize handler.
     */
	function resize(e) {
	    // do not resize on touch devices
	    if ('ontouchstart' in window) {
	        return;
	    }

        // do not resize is we are initialising or we are in fullscreen mode
		if (
		    (
		        e &&
		        e.type == "setcontent" &&
		        e.initial
		    ) ||
		    (
		        editor.plugins.fullscreen &&
		        editor.plugins.fullscreen.isFullscreen()
		    )
		) {
			return;
		}

		// resize to 0 height, then to window height to work out the max. space
		// available by comparing the window height with the resulting document
		// height.
		var iframe = $('#' + editor.id + '_ifr');
		var content = iframe.closest('.form-horizontal');
		var wh = $(window).height();
		iframe.height(0);

		// give the browser time to update the iframe's size before we make
		// the actual measurement.
		setTimeout(function() {
		    iframe.height(wh);

            var h;
            if (frontendEditing) {
                h = wh - (content.height() - wh);
            } else {
                h = wh - (content.height() + 270 - wh);
            }

	    	iframe.height(h);
	    }, 50);
	}


	// resize whenever we resize the window or we initialise the editor
    var timeout = undefined;
	$(window).on('resize', function() {
	    if (timeout) clearTimeout(timeout);
	    timeout = setTimeout(resize, 50);
	});
	editor.on('load', resize);
    $(document).on('cubane-tab-switched', resize);

	// after editor has been loaded, trigger window resize, so that other
	// components may have a chance to adjust theire sizing based on the editor.
	editor.on('load', function() {
	    $(window).trigger('resize');
	});

	// Register the command so that it can be invoked by using
	// tinyMCE.activeEditor.execCommand('mceFillResize');
	editor.addCommand('mceFillResize', resize);
});

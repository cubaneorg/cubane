cubane.require('cubane.html');


/*
 * Automatically updates external iframe reference while content
 * is changed through the tinymce editor.
 */
tinymce.PluginManager.add('cubanepreview', function(editor) {
    var TIMEOUT_MSEC = 400;


	var settings = editor.settings;
    var timeout = undefined;


    /*
     * Get current content form editor.
     */
    function getContent() {
        return editor.getContent({format: 'raw', no_events: false});
    }


    /*
     * Content changed handler.
     */
	function updateContent() {
        var iframe = $('#page-preview');
        if ( iframe.length > 0 ) {
            var el = editor.getElement();
            var slotname = $(el).attr('data-slotname');

            // cleanup image sizes
            $(editor.contentAreaContainer).find('iframe').contents().find('img').each(function() {
                if ($(this).attr('data-cubane-media-size') === 'auto') {
                    $(this).removeAttr('width').removeAttr('height');
                }
            });

            // get slot and optionally base container
            var slot = iframe.contents().find('.cms-slot[data-slotname="' + slotname + '"]');
            if (slot.length > 0) {
                var container = slot.find('> .cms-slot-container');
                if ( container.length == 0 ) container = slot;

                // get headline transpose for this slot
                var headlineTranspose = parseInt(slot.attr('data-headline-transpose'));
                if (headlineTranspose == NaN) headlineTranspose = 0;

                // get content to update
                var html = getContent();

                // apply headline transpose to content
                if (headlineTranspose > 0) {
                    html = cubane.html.transposeHtmlHeadlines(html, headlineTranspose);
                }

                // update slot content
                container.html(html);
            }
        }
	}


    /*
     * Content changed handler.
     */
	function changed(e) {
        if (timeout !== undefined) {
            clearTimeout(timeout);
        }

        timeout = setTimeout(updateContent, TIMEOUT_MSEC);
    }


	// resize whenever we resize the window or we initialise the editor
	editor.on('load change setcontent paste keyup', changed);

	// Register the command so that it can be invoked by
	// using tinyMCE.activeEditor.execCommand('mcePreview');
	editor.addCommand('mcePreview', changed);
});

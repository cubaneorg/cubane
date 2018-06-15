 (function (globals){
"use strict";


cubane.namespace('cubane.html');


/*
 * Javascript-version of the headline transpose function as found
 * in cubane.lib.html in order to provide a preview experience that
 * matches the final render of the page more accurately.
 */
cubane.html.transposeHtmlHeadlines = function transposeHtmlHeadlines(html, level) {
    /*
    Transpose existing headlines within the given html by the given
    amount of levels, for example a transpose of headlines by a level of 1
    would change every h1 headline into a h2 headline, every h2 headline into
    a h3 headline and so forth. The max. number of headlines supported by html
    is h6, therefore transposing an h6 would result into an h6.
    */
    if (level <= 0)
        return html;

    return html.replace(/(<\/?)(h1|h2|h3|h4|h5|h6)/g, function(s, bracket, tag) {
        var index = parseInt(tag.charAt(1));
        index += level;
        index = Math.max(0, Math.min(6, index));
        return bracket + 'h' + index.toString();
    });
}


}(this));
/*
 * String formating.
 */
 (function (globals){
"use strict";


cubane.namespace('cubane.format');


var FILE_SIZES = ['bytes', 'KB', 'MB', 'GB'];


/*
 * Returns a human-readable representation of the given filesize, which is
 * given in bytes.
 */
cubane.format.filesize = function (num) {
    for ( var i = 0; i < FILE_SIZES.length; i++ ) {
        if (num < 1024.0 && num > -1024.0) {
            return num.toFixed(1) + FILE_SIZES[i];
        }
        num /= 1024.0;
    }

    return num.toFixed(1) + 'TB';
};


/*
 * Pluralises the given word based on the given value.
 */
cubane.format.pluralize = function (x, singular, plural) {
    if ( !plural ) {
        plural = singular + 's';
    }

    return Math.abs(x) == 1 ? singular : plural;
};


}(this));

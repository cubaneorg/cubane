/*
 * InnerShed Website and Application Framework
 * (C) Copyright 2013 InnerShed Ltd. All rights reserved.
 *
 * InnerShed Core Framework.
 *
 */
(function (globals){
"use strict";


cubane.namespace('cubane.urls');


cubane.require('cubane.string');


/*
 * List of resolvable url patterns.
 */
if ( !('patterns' in cubane.urls) ) {
    cubane.urls.patterns = {};
}


/*
 * Resolves a url by given url pattern name and given url arguments. This works
 * inn the veryb same way as django's reverse function provided that
 * cubane.urls.patterns contains a list of all resolvable url patterns.
 */
cubane.urls.reverse = function reverse(patternName, args) {
    if ( args === undefined || args === null ) args = [];

    if ( patternName in cubane.urls.patterns ) {
        var url = cubane.urls.patterns[patternName];

        for ( var i = 0; i < args.length; i++ ) {
            url = url.replace('*', args[i]);
        }

        return url;
    } else {
        return null;
    }
};


/*
 * Return a new url based on the given url by combining all existing url
 * arguments that may exist in the existing url and appending the given
 * url argument with given argument value.
 */
cubane.urls.combineUrlArg = function combineUrlArg(url, arg, value) {
    // replace existing argument
    var pattern = new RegExp('\\b(' + arg + '=).*?(&|$)')
    if (url.search(pattern) >= 0) {
        return url.replace(pattern,'$1' + value + '$2');
    }

    // else: append new argument
    if ( url.indexOf('?') === -1 ) {
        url += '?';
    } else if ( !cubane.string.endsWith(url, '&') ) {
        url += '&';
    }

    return url + arg + '=' + value;
};


/*
 * Combine given base url with given url-encoded list of url arguments.
 */
cubane.urls.combineUrlArgs = function combineUrlArgs(url, args) {
    if ( url.indexOf('?') === -1 ) {
        url += '?';
    } else if ( !cubane.string.endsWith(url, '&') ) {
        url += '&';
    }
    return url + args;
};


/*
 * Get query parameters by name from url
 */
cubane.urls.getQueryParamaterByName = function(param) {
    param = param.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + param + "=([^&#]*)")
    var results = regex.exec(location.search);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}


}(this));

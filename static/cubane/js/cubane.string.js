/*
 * InnerShed Website and Application Framework
 * (C) Copyright 2013 InnerShed Ltd. All rights reserved.
 *
 * InnerShed Core Framework.
 *
 */
 (function (globals){
"use strict";


cubane.namespace('cubane.string');


/*
 * Formats the given string s like:
 * "{0} is dead, but {1} is alive! {0} {2}".format("ASP", "ASP.NET")
 *
 * http://stackoverflow.com/questions/610406/javascript-equivalent-to-printf-string-format
 */
cubane.string.format = function (s) {
    var args = arguments;
    return s.replace(/{(\d+)}/g, function(m, i) {
        return args[i] ? args[i] : m;
    });
};


/*
 * Returns true, if the given string s starts with the given string p.
 */
cubane.string.startsWith = function (s, p) {
    return s.indexOf(p) == 0;
};


/*
 * Returns true, if the given string s ends with the given string p.
 */
cubane.string.endsWith = function (s, p) {
    return s.indexOf(p, s.length - p.length) !== -1;
};


}(this));

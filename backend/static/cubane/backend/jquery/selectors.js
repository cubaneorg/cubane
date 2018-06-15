(function (globals){
"use strict";


/*
 * Filters a list of jquery elements that do not have
 * a parent of given expression.
 */
jQuery.expr[':'].noparents = function(a ,i, m) {
    return jQuery(a).parents(m[3]).length < 1;
};


}(this));

/*
 * Helper methods for accessing CSRF token.
 */
(function (globals){
"use strict";


cubane.namespace('cubane.csrf');


/*
 * Return the CSRF token from the CSRF cookie.
 */
cubane.csrf.getToken = function getToken() {
    return getCookie('csrftoken');
};


/*
 * Return true, if the given method is save regarding CSRF and does not
 * require a CSRF token to be attached via header.
 */
cubane.csrf.csrfSafeMethod = function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
};


/*
 * Return the cookie value of given name or undefined.
 */
function getCookie(name) {
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
    }
}


}(this));
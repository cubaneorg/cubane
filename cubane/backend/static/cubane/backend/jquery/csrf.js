(function (){
"use strict";


/*
 * inject CSRF token header for every same-site AJAX request that requires
 * the CSRF token...
 */
var csrftoken = cubane.csrf.getToken();
if (csrftoken) {
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!cubane.csrf.csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
}


}());

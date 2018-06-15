/*
 * Default frontend javascript.
 */
(function (globals){
"use strict";


cubane.require('cubane.urls');
cubane.require('cubane.dom');


/*
 * Submit form field when changed.
 */
function _autoSubmitFormField(id, arg) {
    var select = document.getElementById(id);
    if (select) {
        select.addEventListener('change', function (e) {
            e.preventDefault();

            var value = e.target.value
            var url = cubane.urls.combineUrlArg(window.location.href, arg, value);
            if (id === 'id_pagination_view_all') {
                url = cubane.urls.combineUrlArg(url, 'page', '1');
            }
            window.location.href = url;
        });
    }
}


/*
 * Auto-submit sort form for product listing
 */
function autoSubmitProductSortOrderForm() {
    _autoSubmitFormField('id_sort_by', 'o');
}


/*
 * Auto-submit view all component of paginator
 */
function autoSubmitProductShowPerPage() {
    _autoSubmitFormField('id_pagination_view_all', 'all');
}


/*
 * Print Order if button is clicked
 */
function printOrder() {
    $('.btn-print-order').on('click', function(e) {
        window.print();
    });
}


/*
 * Make password field not required when clicking password reset button
 */
function resetPasswordButton() {
    $('button[name="password_forgotten"]').on('click', function(e) {
        $(e.target).closest('form').find('input[type="password"]').removeAttr('required');
    });
}


/*
 * Main
 */
autoSubmitProductSortOrderForm();
autoSubmitProductShowPerPage();
printOrder();
resetPasswordButton();


}(this));

/*
 * Focus on first input of form that has class focus-first.
 */
(function (globals){
"use strict";


/*
 * Focus the first input of the form.
 */
function _focusFirstInput() {
    var form = $('form.focus-first').first();
    var firstInput = form.find('input:first');
    if (is_touch_device()) {
        firstInput.focus();
    }
}


/*
 * Return true, if the device is a touch device.
 */
function is_touch_device() {
    return 'ontouchstart' in window        // works on most browsers
        || navigator.maxTouchPoints;       // works on IE10/11 and Surface
};


/*
 * Support the ability to close alert messages
 */
function _alertMessages() {
    $(document).on('click', '.alert > button.close', function() {
        $(this).closest('.alert').fadeOut('fast');
    });
}


_focusFirstInput();
_alertMessages();


}(this));

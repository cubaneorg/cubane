/*
 * Mailchimp Subscription form
 */
(function (globals){
"use strict";


function initForm() {
    $(document).on('click', '.mailchimp-subscription-form button[type="submit"]', function(e) {
        e.preventDefault();
        submitForm($(e.target).closest('form'));
    });
}


function submitForm(form) {
    $.post('/mailchimp-subscription-ajax', form.serialize(), function(response) {
        _updateMailchimpForm(form, response.html);
    }, 'JSON');
}

function _updateMailchimpForm(form, html) {
    var container = $(form).closest('.mailchimp-subscription-form');
    container.html(html);
}


initForm();

}(this));

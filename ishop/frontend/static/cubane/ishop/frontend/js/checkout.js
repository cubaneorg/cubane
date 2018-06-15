(function (globals){
"use strict";


function updateUIState() {
    if ( $('.checkout-form #id_signup').is(':checked') ) {
        $('.checkout-form #id_password, .checkout-form #id_password_confirm').closest('.control-group').fadeIn('fast');
    } else {
        $('.checkout-form #id_password, .checkout-form #id_password_confirm').closest('.control-group').fadeOut('fast');
    }

    var deliverTo0 = $('#id_deliver_to_0');
    var deliverToLast = deliverTo0.closest('ul').find('input[value="new_address"]').last();
    var freeDeliveryTo = deliverTo0.closest('ul').find('input[value="free_delivery_to"]').last();

    if ( deliverTo0.length > 0 && deliverToLast.length > 0 ) {
        if ( deliverToLast.is(':checked') ) {
            $('.checkout-delivery-address').fadeIn('fast');
        } else  {
            $('.checkout-delivery-address').fadeOut('fast');
        }
    } else {
        $('.checkout-delivery-address').fadeOut('fast');
    }

    if ( deliverTo0.length > 0 && freeDeliveryTo.length > 0 ) {
        if ( freeDeliveryTo.is(':checked') ) {
            $('.free-delivery-to').fadeIn('fast');
        } else  {
            $('.free-delivery-to').fadeOut('fast');
        }
    }

    var submitBtn = $('input[name="deliver_to"]:checked').closest('form').find('.form-action .btn-primary').first();
    if ($('input[name="deliver_to"]:checked').val() == 'click_and_collect') {
        submitBtn.html('Continue to Click and Collect');
    } else {
        submitBtn.html('Continue to Shipping Method');
    }
}


$('#id_signup').bind('click change', updateUIState);
$('input[name="deliver_to"]').bind('click change', updateUIState);
updateUIState();


// support USA states and zipcode
var usstates = new innershed.USStates();
var usstates_delivery = new innershed.USStates(
    $('#id_delivery_country'),
    $('#id_delivery_county'),
    $('#id_delivery_postcode')
);

// pay now form with autosubmit true should be submitted straightaway
$(function() {
    if (window.location.search.indexOf('?autosubmit=true') !== -1) {
        document.getElementById("pay-now-form").submit();
    }
});

}(this));

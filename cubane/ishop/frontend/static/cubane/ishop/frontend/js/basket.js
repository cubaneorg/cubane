/*
 * Basket
 */
(function (globals){
"use strict";


var timeout = undefined;


function initBasket() {
    // Clicking basket link should open basket
    $(document).on('click', '.open-basket', function(e) {
        e.preventDefault();

        var prefix = $(e.target).attr('data-prefix');
        if (prefix === undefined) {
            // use the prefix that is currently used
            prefix = $('.basket-panel .basket').attr('data-prefix');
        }

        openBasket(prefix);
    });

    // Clicking basket panel toggle button should toggle basket panel...
    $('.basket-panel-toggle').on('click', function(e) {
        e.preventDefault();

        var prefix = $(e.target).attr('data-prefix');
        if (prefix === undefined) {
            // use the prefix that is currently used
            prefix = $('.basket-panel .basket').attr('data-prefix');
        }

        toggleBasketPanel(prefix);
    });

    // Clicking overlay should close basket
    $('.panel-overlay').on('click', function(e) {
        if (basketIsOpen()) {
            closeBasket();
        }
    });

    // Clicking on filter toggle should close basket if open
    $('.variety-filter-toggle').on('click', function(e) {
        if (basketIsOpen()) {
            closeBasket();
        }
    });

    // Clicking plus/minus should increase/decrease quantity...
    $(document).on('click', '.basket-item-quantity .quantity-plus', function(e) {
        e.preventDefault();

        var quantity = $(e.target).closest('.basket-item-quantity').find('input');
        updateQuantityDelta(quantity, 1);
    });
    $(document).on('click', '.basket-item-quantity .quantity-minus', function(e) {
        e.preventDefault();

        var quantity = $(e.target).closest('.basket-item-quantity').find('input');
        updateQuantityDelta(quantity, -1);
    });

    // Changing quanity value should submit basket change to server
    $(document).on('change', '.basket-item input.quantity', function(e) {
        updateBasket($(e.target).closest('.basket'));
    });

    // Clicking remove should set quanity to 0
    $(document).on('click', '.basket-item-remove-btn', function(e) {
        e.preventDefault();

        var quantity = $(e.target).closest('.basket-item').find('.basket-item-quantity input');
        updateQuantity(quantity, 0);
    });

    // ticking processing state should toggle processing state for line item
    // (BACKEND ONLY)
    $(document).on('click', '.basket-item-processed .item-processed', function(e) {
        updateBasket($(e.target).closest('.basket'));
    });

    // Clicking on Apply should update discount voucher code
    $(document).on('click', '.basket-voucher > button', function(e) {
        e.preventDefault();
        updateBasket($(e.target).closest('.basket'));
    });

    // Clicking on Update button should update custom total price for basket
    // (backend only)
    $(document).on('click', '.basket-custom-total > button', function(e) {
        e.preventDefault();
        updateBasket($(e.target).closest('.basket'));
    });

    // Changing delivery option should update basket
    $(document).on('change', '#id_delivery_option', function(e) {
        var prefix = $(e.target).closest('.basket').attr('data-prefix');
        var deliveryOption = $(e.target).closest('#id_delivery_option');
        updateDeliveryOption(prefix, deliveryOption)
    });

    // Changing click and collect tickbox should update basket
    $(document).on('change', '.basket-delivery-form #id_click_and_collect', function(e) {
        var prefix = $(e.target).closest('.basket').attr('data-prefix');
        var clickAndCollect = $(e.target).closest('#id_click_and_collect').is(':checked');
        updateClickAndCollect(prefix, clickAndCollect)
    });

    // Changing country should update basket to reflect delivery
    // charges
    $(document).on('change', '.checkout-form #id_country', _onUpdateCountry);
    $(document).on('change', '.checkout-form #id_delivery_country', _onUpdateCountry);

    // changing delivery option
    $('.checkout-form input[name="deliver_to"]').on('change', _onUpdateCountry);

    // Add to basket should add item to basket and open the basket side panel
    $(document).on('click', '.btn-add-to-basket', function(e) {
        e.preventDefault();
        addToBasket($(e.target).closest('form'));
    });
}


function toggleBasketPanel(prefix) {
    if (basketIsOpen()) {
        closeBasket();
    } else {
        openBasket(prefix);
    }
}


function openBasket(prefix) {
    var panel = $('.basket-panel');
    var wrapper = $('.wrapper');
    var body = $('body');

    if (!panel.hasClass('open')) {
        panel.addClass('open');
        wrapper.addClass('basket-open');
        body.addClass('body-basket-open');
        $('#google-badge-container').addClass('with-basket-open');
    }

    // if the basket is open and has not been loaded yet, load the basket
    // content for the first time...
    if (basketIsOpen() && !basketLoaded(prefix)) {
        loadBasket(prefix);
    }
}


function closeBasket() {
    var panel = $('.basket-panel');
    var wrapper = $('.wrapper');
    var body = $('body');

    if (panel.hasClass('open')) {
        panel.removeClass('open');
        wrapper.removeClass('basket-open');
        body.removeClass('body-basket-open');
        $('#google-badge-container').removeClass('with-basket-open');
    }
}


function loadBasket(prefix) {
    $.get('/shop/basket/', {f: 'html', prefix: prefix}, function(html) {
        if (html) {
            _updateBasketPanelContent(html, prefix);
        }
    });
}


function _updateBasketPanelContent(html, prefix) {
    if (basketLoaded(prefix)) {
        _updateBasketContent($('.basket-panel').find('.basket'), html);
    } else {
        $('.basket-panel-frame').html(html);
        $('.basket-panel').addClass('loaded');
        document.lazyloadImages();
    }
}


function updateQuantityDelta(quantity, delta) {
    var q = parseInt(quantity.val());
    if (isNaN(q)) q = 0;

    q += delta;
    if (q < 0) q = 0;
    if (q > 9999) q = 9999;

    updateQuantity(quantity, q);
}


function updateQuantity(quantity, value) {
    quantity.val(value.toString());
    updateBasket(quantity.closest('.basket'));
}


function updateBasket(basket) {
    if (timeout) {
        clearTimeout(timeout);
    }

    timeout = setTimeout(function() {
        _updateBasket(basket)
    }, 200);
}


function serialize(element) {
    var data = {};
    var fields = element.find('input, select, textarea');
    for (var i = 0; i < fields.length; i++) {
        var field = fields.eq(i);
        var fieldname = field.attr('name');
        var value = field.val();

        if (field.is('[type="checkbox"]')) {
            value = field.is(':checked') ? 'on' : 'off';
        }

        data[fieldname] = value;
    }

    return data;
}


function _updateBasket(basket) {
    var data = serialize(basket);

    // add prefix
    if (basket.attr('data-prefix')) {
        data['prefix'] = basket.attr('data-prefix');
    }

    $.post('/shop/basket/update/', data, function(json) {
        if (json.success) {
            if (json.removed) {
                _gaRemoveFromBasket(json.removed);
            }

            _updateBasketContent(basket, json.html);
            _updateCollectionOnlyState(basket, json.is_collection_only);
            _updateFinanceOptionState(basket, json.finance_options);
        }
    }, 'JSON');
}


function _updateBasketContent(basket, html) {
    var focusedElement = $(":focus");
    var container = basket.parent();

    var focusInsideContainer = container.length > 0 && focusedElement.length > 0 ? $.contains(container.get(0), focusedElement.get(0)) : false;
    var focusedElementName = focusInsideContainer ? focusedElement.attr('name') : undefined;

    // replace content
    container.html(html);

    // re-focus element if we replaced it
    if (focusedElementName) {
        container.find('[name="' + focusedElementName + '"]').focus();
    }

    // update every other instance of a basket (if any) with the
    // same prefix
    var prefix = container.find('.basket').attr('data-prefix');
    $('.basket[data-prefix="' + prefix + '"]').parent().not(container).each(function() {
        $(this).html(html);
    });

    // load images
    document.lazyloadImages();
}


function basketIsOpen() {
    return $('.basket-panel').hasClass('open');
}


function basketLoaded(prefix) {
    var panel = $('.basket-panel');
    return panel.hasClass('loaded') && panel.find('.basket').attr('data-prefix') == prefix;
}


function addErrorsToForm(form, errors) {
    for (var key in errors) {
        var input = $(form).find('[name="' + key + '"]');
        var errorMessage = '<div class="help-inline">' + errors[key] + '</div>';
        var controlGroup = $(input).closest('.control-group');
        if (!controlGroup.hasClass('error')) {
            controlGroup.addClass('error').append(errorMessage);
        }
    }
}


function addToBasket(addToBasketForm) {
    var data = serialize(addToBasketForm);

    $.post('/shop/basket/add/', data, function(response) {
        if (response.errors) {
            addErrorsToForm(addToBasketForm, response.errors);
        } else {
            _updateBasketPanelContent(response.html, data.prefix);
            openBasket(response.prefix);

            if (response.added) {
                _gaAddToBasket(response.added);
            }
        }
    }, 'JSON');
}


function updateDeliveryOption(prefix, select) {
    var params = {
        prefix: prefix,
        delivery_option_id: select.val()
    };

    $.post('/shop/basket/update/', params, function(json) {
        if (json.success) {
            // update basket
            $('.basket').each(function() {
                _updateBasketContent($(this), json.html);
            });

            // update delivery option details
            var container = select.closest('.delivery-options').find('.delivery-option-details');
            container.html(json.delivery);
        }
    }, 'JSON');
}


function updateClickAndCollect(prefix, clickAndCollect) {
    var params = {
        prefix: prefix,
        click_and_collect: clickAndCollect
    };

    $.post('/shop/basket/update/', params, function(json) {
        if (json.success) {
            $('.basket').each(function() {
                _updateBasketContent($(this), json.html);
            });
        }
    }, 'JSON');
}


function updateDeliveryDestination(clickAndCollect, countryISO) {
    var params = {
        click_and_collect: clickAndCollect,
        country_iso: countryISO
    };

    $.post('/shop/basket/update/', params, function(json) {
        if (json.success) {
            $('.basket').each(function() {
                _updateBasketContent($(this), json.html);
            });
        }
    }, 'JSON');
}


function _onUpdateCountry(e) {
    var checkout = $(e.target).closest('.checkout-form');
    var deliverTo = $('.checkout-form input[name="deliver_to"]:checked').val();

    var billingCountry = checkout.find('#id_country').val();
    var deliveryCountry = checkout.find('#id_delivery_country').val();
    var clickAndCollect = deliverTo === 'click_and_collect';
    var deliveryToBillingAddress = deliverTo === 'billing_address';
    var newDeliveryAddress = deliverTo === 'new_address';

    if (clickAndCollect) {
        updateDeliveryDestination(true, null);
    } else if (deliveryToBillingAddress) {
        updateDeliveryDestination(false, billingCountry);
    } else if (newDeliveryAddress) {
        updateDeliveryDestination(false, deliveryCountry);
    } else {
        // check pre-stored delivery address from customer's profile
        for (var i = 0; i < DELIVERY_ADDRESSES.length; i++) {
            var addr = DELIVERY_ADDRESSES[i];
            var field = checkout.find('#id_deliver_to_' + addr.id);
            if (field.is(':checked')) {
                updateDeliveryDestination(false, addr.iso);
            }
        }
    }
}


function _updateCollectionOnlyState(basket, isCollectionOnly) {
    var checkout = $('.checkout-form');
    if (isCollectionOnly) {
        checkout.addClass('collection-only');
        checkout.find('#id_deliver_to_0').attr('checked', true);
    } else {
        checkout.removeClass('collection-only');
    }
}


function _updateFinanceOptionState(basket, financeOptions) {
    var checkout = $('.checkout-form');
    var select = checkout.find('#id_finance_option');

    if (financeOptions.length > 0) {
        checkout.addClass('checkout-loan-available');

        // generate available finance options
        select.find('option[value!=""]').remove();
        for (var i = 0; i < financeOptions.length; i++) {
            select.append($('<option value="' + financeOptions[i].id + '">' + financeOptions[i].title + '</option>'));
        }

    } else {
        checkout.removeClass('checkout-loan-available');
        select.val('');
    }
}


function _gaAddToBasket(product) {
    if (window['ga'] === undefined)
        return;

    ga('ec:addProduct', {
        'id': product.id,
        'name': product.name,
        'category': product.category,
        'brand': product.brand || '',
        'variant': product.variant,
        'price': product.price,
        'quantity': product.quantity
    });
    ga('ec:setAction', 'add');
    ga('send', 'event', 'UX', 'click', 'add to cart');
}


function _gaRemoveFromBasket(products) {
    if (window['ga'] === undefined)
        return;

    if (products.length > 0) {
        for (var i = 0; i < products.length; i++) {
            var product = products[i];
            ga('ec:addProduct', {
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'brand': product.brand || '',
                'price': product.price,
                'variant': product.variant
            });
        }

        ga('ec:setAction', 'remove');
        ga('send', 'event', 'UX', 'click', 'remove from cart');
    }
}


/*
 * Main
 */
initBasket();


}(this));

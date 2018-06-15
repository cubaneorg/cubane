/*
 * Product Details Page
 */
(function (globals){
"use strict";


/*
 * Product image gallery
 */
var initProductImages = function initProductImages() {
    // product page?
    if ($('form.add-to-basket, .product').length === 0)
        return;

    // clicking on thumbnail should make bigger version visible
    $(document).on('click', '.product-image-gallery .scroll-item, .add-to-basket-gallery-item', function(e) {
        var item = $(e.target).closest('.scroll-item, .add-to-basket-gallery-item');
        _showProductImageByIndex(item.index());
    });
};


/*
 * Present the n.th product image based on given index (0-based).
 */
function _showProductImageByIndex(index) {
    $('.product-image.active').removeClass('active');
    $('.product-image-gallery .scroll-item.active, .add-to-basket-gallery-item.active').removeClass('active');

    $('.product-image').eq(index).addClass('active');
    $('.product-image-gallery .scroll-item').eq(index).addClass('active');
    $('.add-to-basket-gallery-item').eq(index).addClass('active');

    document.lazyloadImages();
}


/*
 * Submit GA information whenever we click a product from a listing
 */
function submitGAOnProductClickFromListing() {
    $(document).on('click', '.product-listing .item-product a', function(e) {
        if (!ga.loaded)
            return;

        e.preventDefault();

        var a = $(e.target).closest('a');
        var product = a.closest('.item-product')
        var listing = product.closest('.product-listing')
        var href = a.attr('href');
        var id = product.attr('data-id');
        var name = product.attr('data-name');
        var brand = product.attr('data-brand');
        var category = product.attr('data-category');
        var list = listing.attr('data-list');

        var productData = {
            'id': id,
            'name': name,
            'category': category
        };
        if (brand) {
            productData['brand'] = brand;
        }

        // Send click with an event, then send user to product page.
        ga('ec:addProduct', productData);
        ga('ec:setAction', 'click', {list: list});
        ga('send', 'event', 'UX', 'click', 'Results', {
            hitCallback: function() {
                document.location = href;
            }
        });
    });
}


/*
 * Return the current value of the given variety.
 */
function _getVarietyValue(variety) {
    if (variety.hasClass('select-list')) {
        return parseInt(variety.find('input[type="hidden"]').val());
    } else {
        return parseInt(variety.val());
    }
}


/*
 * Set variety value.
 */
function _setVarietyValue(variety, value) {
    if (variety.hasClass('select-list')) {
        variety.find('.select-list-option.selected').removeClass('selected disabled');
        variety.find('input[type="hidden"]').val(value);

        var selectedOption = variety.find('.select-list-option[data-value="' + value.toString() + '"]');
        selectedOption.addClass('selected');
    } else {
        variety.val(value);
    }
}


/*
 * Return a list of current variety option values for the given set of
 * varieties (current values).
 */
function _getVarietyValues(varieties) {
    var values = [];
    for (var i = 0; i < varieties.length; i++) {
        values.push(_getVarietyValue(varieties.eq(i)));
    }
    return values;
}


/*
 * Return the variety option value of the given variety option.
 */
function _getOptionValue(option) {
    return parseInt(option.attr('data-value'));
}


/*
 * Return the combination that matches the given set of variety options.
 * The returned combination contains additional information, such as price.
 */
function _getCombination(combination, validCombinations) {
    for (var i = 0; i < validCombinations.length; i++) {
        if (combination.length === validCombinations[i].ids.length) {
            var match = true;
            for (var j = 0; j < combination.length; j++) {
                if (validCombinations[i].ids.indexOf(combination[j]) === -1) {
                    match = false;
                    break;
                }
            }

            if (match) {
                return validCombinations[i];
            }
        }
    }
}


/*
 * Return true, if the given combination of variety options is a valid
 * combination according to the given list of possible combinations.
 */
function _isValidCombination(combination, validCombinations) {
    return _getCombination(combination, validCombinations) !== undefined;
}


/*
 * Set or unset the option disabled state for the given option.
 */
function _setOptionState(option, isActive) {
    if (isActive) {
        option.removeClass('disabled');
    } else {
        option.addClass('disabled');
    }
}


/*
 * Return the bast (alternative) combination of the current variety selection,
 * given that the customer has just changed the given variety.
 */
function _findBestVarietyCombination(variety, validCombinations) {
    // the current variety value that the customer just changed.
    var varietyValue = _getVarietyValue(variety);

    // determine the remaining varieties that were not changed
    // by the customer and the current variety values. Only consider varieties
    // that are actually taken part in SKU numbers...
    var varities = $('form.add-to-basket .product-variety.sku');
    var remainingVarieties = varities.not(variety);
    var remainingCombination = _getVarietyValues(remainingVarieties);

    // test all possible combinations and determine the amount of changes
    // it requires...
    var lowest = remainingCombination.length + 1;
    var bestCombination = undefined;
    for (var i = 0; i < validCombinations.length; i++) {
        var combination = validCombinations[i].ids;

        // combination does not apply, because it does not include the
        // customer's choice of the variety that was just changed...
        if (combination.indexOf(varietyValue) === -1) {
            continue;
        }

        // count the amount of differences
        var d = 0;
        for (var j = 0; j < remainingCombination.length; j++) {
            if (combination.indexOf(remainingCombination[j]) === -1) {
                d += 1;
            }
        }

        // determine best combination
        if (d < lowest) {
            lowest = d;
            bestCombination = combination;
        }
    }

    return bestCombination;
}


/*
 * Apply the given combination of variety options.
 */
function _selectVarietyCombination(combination) {
    for (var i = 0; i < combination.length; i++) {
        var option = $('form.add-to-basket .variety-option[data-value="' + combination[i].toString() + '"]');
        var variety = option.closest('.product-variety');
        var value = _getVarietyValue(variety);
        if (value !== combination[i]) {
            _setVarietyValue(variety, combination[i]);
        }
    }
}


/*
 * Since the current variety selection might have been changed, the new
 * selection might not be valid anymore. If this is the case, we are analysing
 * all possible combinations to find a one that:
 *
 * (a) does not change the given variety as given, since the customer
 *     just changed it.
 *
 * (b) Has the least impact in change, which meanst that it changes the least
 *     amount of (other) variety options.
 */
function _makeValidVarietySelection(variety, validCombinations) {
    if (variety === undefined) return;

    // ignore variety that does not take part in SKU numbers...
    if (!variety.hasClass('sku'))
        return;

    // find best (alternative) combination of variety options
    var bestCombination = _findBestVarietyCombination(variety, validCombinations);

    // if we found a possible alternative, apply this combination by changing
    // the variety options accordingly.
    if (bestCombination !== undefined) {
        _selectVarietyCombination(bestCombination);
    }
}


/*
 * Determine the correct active/disabled state for each variety option.
 */
function _updateVarietyState(validCombinations) {
    // go through each option and determine if we could enable it, given
    // that all other varieties stay how they currently are
    var varities = $('form.add-to-basket .product-variety.sku');
    for (var i = 0; i < varities.length; i++) {
        var variety = varities.eq(i);
        var remainingVarieties = varities.not(variety);
        var remainingCombination = _getVarietyValues(remainingVarieties);
        var options = variety.find('.variety-option');
        for (var j = 0; j < options.length; j++) {
            // determine current combination of variety option we are looking
            // at, where we are examining each possible option of one variety
            // while having the pther variety options fixed to the current
            // selection.
            var option = options.eq(j);
            var combination = [_getOptionValue(option)];
            Array.prototype.push.apply(combination, remainingCombination);

            // if the current combination is valid, make the option we are
            // currently examening active/disabled...
            _setOptionState(option, _isValidCombination(combination, validCombinations));
        }
    }
}


/*
 * Return the current combination that is currently selected.
 */
function _getCurrentCombination(validCombinations) {
    var varities = $('form.add-to-basket .product-variety.sku');
    return _getCombination(_getVarietyValues(varities), validCombinations);
}


/*
 * Update product price according to the given combination.
 */
function _updateProductPrice(combination) {
    if (combination !== undefined) {
        $('form.add-to-basket .product-price .price').html(combination.price.display);
    }
}


/*
 * Return the SVG layer overwrite information for all varieties.
 */
function _getSVGLayerOverwrites() {
    var result = {};
    var varieties = $('form.add-to-basket .product-variety[data-layer]');
    for (var i = 0; i < varieties.length; i++) {
        var variety = varieties.eq(i);
        var layer = variety.attr('data-layer');
        var color = variety.find('.variety-option.selected').attr('data-layer-color');
        if (layer && color) {
            if (!result[layer]) {
                color = color.trim();
                if (color.indexOf('#') === 0) {
                    color = color.substring(1)
                }
                result[layer] = color;
            }
        }
    }

    return result;
}


/*
 * Update current product image's SVG layer colour information according to
 * the given variety (or if no specific variety is given) for all varieties.
 */
function _updateProductSvgLayers(variety) {
    if (variety === undefined) {
        // update all varieties with layer overwrite information
        var varieties = $('form.add-to-basket .product-variety[data-layer]');
        for (var i = 0; i < varieties.length; i++) {
            _updateProductSvgLayers(varieties.eq(i));
        }
    } else {
        // update given variety (if applicable)
        var layer = variety.attr('data-layer');
        var color = variety.find('.variety-option.selected, .variety-option:selected').attr('data-layer-color');
        if (layer && color) {
            overwriteSvgLayer(layer, color);
        }
    }
}


/*
 * Update the fill style of the SVG layer(s) with given identifier for
 * all product images to the given color.
 */
function overwriteSvgLayer(layer, color) {
    var svgs = $('.product-image svg, .product-image-gallery-item svg');
    for (var i = 0; i < svgs.length; i++) {
        var svg = svgs.eq(i);

        // get unqiue identifier prefix for the particular svg
        var prefix = svg.attr('data-prefix');
        if (prefix === undefined || prefix === null) prefix = '';
        if (prefix !== '') prefix += '_';

        // change layer fill style to given color
        var el = $('#' + prefix + layer, svg);
        el.css({'fill': color});
    }
}


/*
 * Update price based on server request
 */
function _onUpdatePriceForAddToBasketForm(variety) {
    var addToBasketForm = $('form.add-to-basket');
    $.post('/shop/basket/get-basket-item-price/', addToBasketForm.serialize(), function(response) {
        if (!response.errors) {
            var pp = addToBasketForm.find('.product-price');
            pp.html(response.html);
        }
    }, 'JSON');
}


/*
 * Update the product preview url based on all SVG layer overwrite information.
 */
function _updateProductSvgLayersPreviewUrl() {
    var overwrites = _getSVGLayerOverwrites();
    var layers = Object.keys(overwrites);

    if (layers.length > 0) {
        // construct url arguments to include layer overwrite information
        var urlArgs = []
        for (var i = 0; i < layers.length; i++) {
            urlArgs.push(
                layers[i] +
                '=' +
                overwrites[layers[i]]
            );
        }
        urlArgs = urlArgs.join('&');

        // process each product image on the page...
        var productImages = $('.product-image.lightbox');
        for (var i = 0; i < productImages.length; i++) {
            var productImage = productImages.eq(i);

            // store actual image url, since we are going to overwrite it...
            if (!productImage.attr('data-preview-url')) {
                productImage.attr('data-preview-url', productImage.attr('href'));
            }

            // construct new url based on media-api and overwrite arguments
            var url = productImage.attr('data-preview-url');
            if (url.indexOf('/media/') !== -1) {
                url = url.replace('/media/', '/media-api/');
            }
            url += '?' + urlArgs;

            // set new preview url
            productImage.attr('href', url)
        }
    }
}


/*
 * Update the visibility of variety option labels
 */
function _updateLabelVisibility() {
    var labels = $('.variety-text-label');
    for (var i = 0; i < labels.length; i++) {
        var label = labels.eq(i);
        var group = label.closest('.control-group');
        var varietyName = label.attr('data-variety-name');
        var varietyOptionIds = label.attr('data-varity-option-ids').split(',');

        // get variety field
        var variety = $('input[name="' + varietyName + '"], select[name="' + varietyName + '"]');
        var varietyOptionId = variety.val();

        if (varietyOptionIds.indexOf(varietyOptionId) !== -1) {
            // show box
            group.show();

            // update placeholder and help text
            var option = $('.variety-option[data-value="' + varietyOptionId + '"]');
            var placeholder = option.attr('data-label-placeholder');
            var helpText = option.attr('data-label-help-text');
            var field = label.closest('.field');

            if (!placeholder) placeholder = 'Label Text...';

            label.attr('placeholder', placeholder);
            group.find('.help-block').remove();
            if (helpText) {
                field.after('<div class="help-block">' + helpText + '</div>');
            }
        } else {
            group.hide();
        }
    }
}


/*
 * Disabled invalid product variety combinations and update SVG image layers
 */
function _updateVarieties(variety, validCombinations, varietyChanged) {
    if (varietyChanged === undefined) varietyChanged = true;

    // SKU: enforce valid variety selection
    if (validCombinations.length > 0) {

        _makeValidVarietySelection(variety, validCombinations);
        _updateVarietyState(validCombinations);
    }

    // ask server for updated price information
    if (varietyChanged) {
        _onUpdatePriceForAddToBasketForm(variety);
    }

    // update svg image layers and preview urls
    _updateProductSvgLayers(variety);
    _updateProductSvgLayersPreviewUrl();

    // update name label visibility
    _updateLabelVisibility();
}


/*
 * Make sure that only valid variety combinations are presented to the customer.
 * Some specific variety combination might not be a valid combination.
 */
function initProductVarieties() {
    // product page?
    if ($('form.add-to-basket').length === 0)
        return;

    var validCombinations = window.CUBANE_VARIETY_OPTION_IDS || [];
    var timeout = undefined;

    // change selection (select list mode)
    $('.select-list .select-list-option').on('click', function(e) {
        e.preventDefault();

        var option = $(this);
        var variety = option.closest('.product-variety');
        _setVarietyValue(variety, _getOptionValue(option));
    });

    // update varieties whenever we change varieties...
    $('form.add-to-basket select.product-variety').on('change', function() {
        _updateVarieties($(this), validCombinations);
    });
    $('form.add-to-basket .product-variety.select-list .variety-option').on('click', function(e) {
        e.preventDefault();
        _updateVarieties($(this).closest('.product-variety'), validCombinations);
    });

    // update varieties whenever the active product image finsihed loading
    $(document).on('lazy-loaded', '.product-image.active, .product-image-gallery-item', function(e) {
        _updateVarieties(undefined, validCombinations, false);
    });

    // initial state
    _updateVarieties(undefined, validCombinations, false);
}


/*
 * Main
 */
initProductImages();
submitGAOnProductClickFromListing();
initProductVarieties();


/*
 * Export
 */
document.initProductImages = initProductImages;
document.initProductVarieties = initProductVarieties;

}(this));
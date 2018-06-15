(function() {
    "use strict";


    cubane.require('cubane.urls');


    const TIMEOUT_SEARCH_MSEC = 250;


    var timeout = undefined;


    /*
     * Initialize
     */
    function init() {
        $(document).on('change, keyup', '.basket-editor-search-input', searchInputChanged);
        $(document).on('click', '.basket-editor-panel-listing-item', productSelected);
    }


    /*
     * Product search input changed, schedule new search
     */
    function searchInputChanged(e) {
        if (timeout !== undefined) {
            clearTimeout(timeout);
        }

        timeout = setTimeout(search, TIMEOUT_SEARCH_MSEC);
    }


    /*
     * Product selected
     */
    function productSelected(e) {
        e.preventDefault();

        // change active state
        var item = $(e.target).closest('.basket-editor-panel-listing-item');
        selectProduct(item);


    }


    /*
     * Select the given product item
     */
    function selectProduct(item) {
        if (item.length === 0 || item.hasClass('active'))
            return;

        $('.basket-editor-panel-listing-item.active').removeClass('active');
        item.addClass('active');

        // load add-to-basket form
        var pk = item.attr('data-pk');
        var prefix = item.closest('.basket-editor').attr('data-prefix');
        var data = {
            pk: pk,
            prefix: prefix
        };
        $.post(cubane.urls.reverse('cubane.ishop.orders.basket_editor_add_to_basket'), data, function(html) {
            $('.basket-editor-panel-product').html(html);
            document.lazyloadImages();
            document.initProductImages();
            document.initProductVarieties();
        });
    }


    /*
     * Select first product in the list
     */
    function selectFirstProduct() {
        var item = $('.basket-editor-panel-listing-item').first();
        selectProduct(item);
    }


    /*
     * Perform product search
     */
    function search() {
        var q = $('.basket-editor-search-input').val();
        $.post(cubane.urls.reverse('cubane.ishop.orders.basket_editor_search'), {q: q}, function(html) {
            $('.basket-editor-panel-listing').html(html);
            document.lazyloadImages();

            // always select the first item in the list automatically
            selectFirstProduct();
        });
    }


    if ($('.basket-editor').length > 0) {
        init();
    }
})();
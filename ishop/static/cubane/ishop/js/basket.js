(function() {
    "use strict";


    cubane.require('cubane');
    cubane.require('cubane.urls');
    cubane.require('cubane.dialog');


    /*
     * Initialize
     */
    function init() {
        $(document).on('click', '.basket .btn-basket-add', onAddClicked);
        $(document).on('click', '.btn-order-print', onPrintClicked);
    }


    /*
     * Add button clicked
     */
    function onAddClicked(e) {
        e.preventDefault();

        var basket = $(e.target).closest('.basket');
        var panel = basket.closest('.basket-panel');
        var prefix = basket.attr('data-prefix');
        var url = cubane.urls.reverse('cubane.ishop.orders.basket_editor');
        url = cubane.urls.combineUrlArg(url, 'prefix', prefix);
        url = cubane.urls.combineUrlArg(url, 'index-dialog', true);
        var dlg = cubane.dialog.iframe('Add Product', url, {
            closeBtn: false,
            onClose: function() {
                // reload basket
                $.get('/shop/basket/', {f: 'html', prefix: prefix}, function(html) {
                    if (html) {
                        panel.html(html);
                        document.lazyloadImages();
                    }
                });

            }
        });
    }


    /*
     * Print order
     */
    function onPrintClicked(e) {

    }


    if ($('.basket').length > 0) {
        init();
    }
})();
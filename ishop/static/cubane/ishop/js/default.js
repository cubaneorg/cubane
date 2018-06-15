(function(){
"use strict";


cubane.require('cubane.dialog');


if ( window['ishop'] === undefined ) window.ishop = {};


/*******************************************************************************
 * Calculate and round price and convert from net to gross based on current vat
 * rate.
 ******************************************************************************/
ishop.PriceInputController = function(url, vat, net, gross, price_calculation) {
    this.init(url, vat, net, gross, price_calculation);
};

ishop.PriceInputController.prototype = {
    PRICE_CALCULATION: {
        GROSS:      'gross',
        GROSS_ONLY: 'gross-only',
        NET:        'net'
    },


    init: function(url, vat, net, gross, price_calculation) {
        this._bound = {
            onVatChanged: $.proxy(this.onVatChanged, this),
            onNetChanged: $.proxy(this.onNetChanged, this),
            onGrossChanged: $.proxy(this.onGrossChanged, this),
        };

        this._url = url;
        this._vat = vat;
        this._net = net;
        this._gross = gross;
        this._price_calculation = price_calculation;

        this._vat.bind('change', this._bound.onVatChanged);
        this._net.bind('change', this._bound.onNetChanged);
        this._gross.bind('change', this._bound.onGrossChanged);
    },


    dispose: function() {
        this._vat.unbind('change', this._bound.onVatChanged);
        this._net.unbind('change keyup', this._bound.onNetChanged);
        this._gross.unbind('change keyup', this._bound.onGrossChanged);
        this._bound = null;
        this._url = null;
        this._vat = null;
        this._net = null;
        this._gross = null;
        this._price_calculation = null;
    },


    onVatChanged: function() {
        if ( this._price_calculation == this.PRICE_CALCULATION.GROSS ) {
            this.update($('#id_net_price').val(), null);
        } else if ( this._price_calculation == this.PRICE_CALCULATION.NET ) {
            this.update(null, $('#id_gross_price').val());
        }
    },


    onNetChanged: function() {
        this.update($('#id_net_price').val(), null);
    },


    onGrossChanged: function() {
        this.update(null, $('#id_gross_price').val());
    },


    update: function(net, gross) {
        var data = {
            vat: $('#id_vat').val()
        };

        if ( net !== null ) data['net'] = net;
        if ( gross !== null ) data['gross'] = gross;

        $.post(this._url, data, $.proxy(function(json) {
            $('#id_net_price').val(json.net);
            $('#id_gross_price').val(json.gross);
        }, this), 'json');
    }
};


/*******************************************************************************
 * Round price values after changing them
 ******************************************************************************/
ishop.PriceRounder = function(url, elements) {
    this.init(url, elements);
};

ishop.PriceRounder.prototype = {
    init: function(url, elements) {
        this._bound = {
            onChanged: $.proxy(this.onChanged, this)
        }

        this._url = url
        this._elements = elements;
        this._elements.bind('change', this._bound.onChanged);
    },


    dispose: function() {
        this._elements.unbind('change', this._bound.onChanged);
        this._url = null;
        this._elements = null;
        this._bound = null;
    },


    onChanged: function(e) {
        var input = $(e.target);
        $.post(this._url, { value: input.val() }, function(json) {
            input.val(json.value);
        }, 'json');
    }
};


/*******************************************************************************
 * Stock level controller
 ******************************************************************************/
ishop.StockLevelController = function () {
    this.init();
};
ishop.StockLevelController.prototype = {
    init: function () {
        this._bound = {
            onStockChanged: $.proxy(this.onStockChanged, this)
        };

        $('.stock').bind('change', this._bound.onStockChanged);

        this.updateUIState();
    },


    dispose: function () {
        $('.stock').unbind('change', this._bound.onStockChanged);
        this._bound = null;
    },


    onStockChanged: function (e) {
        var select = $(e.target);
        this.updateUIState(select);
    },


    updateUIState: function(select) {
        if ( !select ) {
            var elements = $('.stock');
            for ( var i = 0; i < elements.length; i++ ) {
                this.updateUIState(elements.eq(i));
            }
        } else {
            var level = select.closest('tr').find('.stocklevel');
            if ( select.val() == '3' ) {
                level.css('opacity', 1).attr('disabled', false);

            } else {
                level.css('opacity', 0.3).attr('disabled', true);
            }
        }
    }
};


/*
 * US States
 */
$(document).ready(function() {
    var usstates = new innershed.USStates();
    var usstates_delivery = new innershed.USStates(
        $('#id_delivery_country'),
        $('#id_delivery_county'),
        $('#id_delivery_postcode')
    );
});


/*
 * Shop Data Import
 */
$(document).ready(function() {
    $('.cubane-ishop-dataimport-form form').on('submit', function() {
        cubane.dialog.working('Importing data', 'This process may take a minute,  Please Wait...');
    });
});


}());
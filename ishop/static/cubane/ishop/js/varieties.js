/*******************************************************************************
 * Variety Options: Change offset prepend label based on selected type
 ******************************************************************************/
ishop.VarietyOptionController = function(currency, updateSeqUrl, sortable) {
    if ( updateSeqUrl === undefined ) updateSeqUrl = '';
    if ( sortable === undefined ) sortable = false;
    this.init(currency, updateSeqUrl, sortable);
};

ishop.VarietyOptionController.prototype = {
    OFFSET: {
        NONE: '0',
        VALUE: '1',
        PERCENT: '2'
    },


    OPACITY: 0.6,


    init: function(currency, updateSeqUrl, sortable) {
        this._currency = currency;
        this._updateSeqUrl = updateSeqUrl;
        this._sortable = sortable;
        this._bound = {
            onChanged: $.proxy(this.onChanged, this),
            onSubmit: $.proxy(this.onSubmit, this),
            onVarietyChanged: $.proxy(this.onVarietyChanged, this)
        };

        $('.variety-offset-type').bind('change', this._bound.onChanged);
        $('input[type="checkbox"]').bind('change', this._bound.onChanged);
        $('#content form').bind('submit', this._bound.onSubmit);
        $('#id_import_variety').on('click change', this._bound.onVarietyChanged);

        this.updateImporterState();

        // initialize visual state for all rows
        var rows = $('#content tbody tr');
        for ( var i = 0; i < rows.length; i++ ) {
            this.update(rows.eq(i));
        }

        // make it sortable if required
        if ( this._sortable ) {
            // inject sortable helper icon and row id
            $('#content thead tr').append('<th class="form-column-move">Move</th>');
            for ( var i = 0; i < rows.length; i++ ) {
                rows.eq(i).append('<td class="form-column-move"><div class="ui-sortable-handle"></div></td>');
                rows.eq(i).attr('id', 'option-' + $('#id_form-' + i + '-_id').val());
            }

            // make items sortable
            cubane.backend.sortable('#content tbody tr', '.ui-sortable-handle', function() {
                // we are not submitting anything here, since we rely on the
                // normal form post...
                var items = $('#content tbody tr');
                for (var i = 0; i < items.length; i++) {
                    var formId = items.eq(i).find('.form-column-title input').attr('id').replace('id_form-', '').replace('-title', '');
                    var seqField = $('#id_form-' + formId + '-seq');
                    seqField.val(i + 1);
                }
            }, 'cubane-variety-options-placeholder');
        }
    },


    dispose: function() {
        $('.variety-offset-type').unbind('change', this._bound.onChanged);
        $('input[type="checkbox"]').unbind('change', this._bound.onChanged);
        $('#content form').unbind('submit', this._bound.onSubmit);
        this._bound = null;
    },


    onChanged: function(e) {
        var row = $(e.target).closest('tr');
        this.update(row);
    },


    update: function(row) {
        var typ_select = row.find('.variety-offset-type');
        var value_input = row.find('.variety-offset-value');

        // update enabled state (enabled and not delete)
        var enabled = row.find('.variety-enabled').is(':checked');
        var deleted = false;
        if ( row.find('.form-column-DELETE input[type="checkbox"]').attr('id') !== row.find('.variety-enabled').attr('id') ) {
            deleted = row.find('.form-column-DELETE input[type="checkbox"]').is(':checked');
        }

        if ( enabled && !deleted ) {
            row.find('input, select').removeAttr('disabled').css('opacity', 1);
            row.find('.input-prepend').css('opacity', 1);
        } else {
            row.find('input, select').attr('disabled', 'disabled').css('opacity', this.OPACITY);
            row.find('.input-prepend').css('opacity', this.OPACITY);
        }
        row.find('.variety-enabled').removeAttr('disabled').css('opacity', 1);

        // update value
        var typ = typ_select.val();
        if ( typ === this.OFFSET.NONE ) {
            // remove value if typ is none and disable input field
            value_input.closest('.input-prepend').find('.add-on').text('');
            value_input.closest('.input-prepend').css('opacity', this.OPACITY);
            value_input.val('');
            value_input.attr('disabled', 'disabled');
        } else if ( typ === this.OFFSET.VALUE ) {
            // change prefix to currency
            value_input.closest('.input-prepend').find('.add-on').text(this._currency);
            value_input.removeAttr('disabled');
        } else if ( typ === this.OFFSET.PERCENT ) {
            // change prefix to percent
            value_input.closest('.input-prepend').find('.add-on').text('%');
            value_input.removeAttr('disabled');
        }
    },


    onSubmit: function(e) {
        $('#content form').find('input, select').removeAttr('disabled');
    },


    onVarietyChanged: function (e) {
        this.updateImporterState();
    },


    updateImporterState: function() {
        var value = $('#id_import_variety').val();
        $('#cubane-btn-variety-options-import').attr('disabled', value === '');
    }
};

$(document).ready(function() {
    if ($('.cubane-variety-options').length > 0) {
        var options = $('.cubane-variety-options');
        var currency = options.attr('data-currency');
        var url = options.attr('data-url');

        var varietyController = new ishop.VarietyOptionController(
            currency,
            url,
            true
        );

        options.show();

        $(document).unload(function() {
            varietyController.dispose();
            varietyController = null;
        });
    }
});
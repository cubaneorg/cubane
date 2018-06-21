(function (globals){
"use strict";


cubane.namespace('cubane.backend');


/*
 * Main
 */
initAll();


/*
 * Initialize
 */
function initAll() {
    $(document).on('click', '.embed-forms-add', onAdd);
    $(document).on('click', '.ui-remove', onRemove);

    var forms = $('.embed-forms');
    for (var i = 0; i < forms.length; i++) {
        init(forms.eq(i));
    }
}


/*
 * Initialize given embedded form
 */
function init(container) {
    var sortable = container.attr('data-sortable') === 'True';
    if (sortable) {
        makeSortable(container);
    }
}


/*
 * Make given embedded forms sortable.
 */
function makeSortable(container) {
    // @Incomplete: item selector should be container.find('.embed-form').
    // Would this work with two embedded forms on the same page?
    cubane.backend.sortable(
        '.embed-form',
        '.ui-sortable-handle',
        function() {
            reindexSequence(container);
        }
    );
}


/*
 * Clicking 'Add' button
 */
function onAdd(e) {
    e.preventDefault();

    // make copy of template row and append to list
    var container = $(e.target).closest('.embed-forms');
    var rows = container.find('> .embed-forms-container > .embed-forms-body');
    var template = container.find('> .embed-form-template');

    // create new row and change index seq number
    var row = $(template.html());
    var seqIndex = getHighestSeqIndex(container) + 1;

    // rewrite form prefix and append to listing
    rewriteSeqIndex(container, row, seqIndex);
    rows.append(row);

    // initialize custom controls
    row.trigger('init-controls');

    // auto-focus first input field
    window.backendController.focusFirstInputField(row);
}


/*
 * Rewrite form seq index of the given form to the given seq index.
 */
function rewriteSeqIndex(container, row, seq) {
    var prefixPattern = container.attr('data-prefix-pattern');
    var seqField = row.find('.embed-form-seq-index');
    var currentSeq = seqField.val();
    var fields = row.find('[name]');
    for (var i = 0; i < fields.length; i++) {
        var field = fields.eq(i);
        var fieldName = field.attr('name');
        var prevFieldName = fieldName
        if (fieldName.indexOf(prefixPattern) === 0) {
            var regex = new RegExp('^' + prefixPattern + '_' + '\\d+' + '--', 'i');
            fieldName = fieldName.replace(regex, '');
            fieldName = prefixPattern + '_' + seq + '--' + fieldName;

            // change field name and id
            field.attr('name', fieldName);
            if (field.attr('id')) {
                field.attr('id', 'id_' + fieldName);
            }

            // change label targets
            row.find('label[for="id_' + prevFieldName + '"]').attr('for', 'id_' + fieldName);

            // change prefix of embedded forms
            var embeddedContainers = row.find('.embed-forms');
            for (var j = 0; j < embeddedContainers.length; j++) {
                // rewrite prefix pattern for embedded form
                var embeddedContainer = embeddedContainers.eq(j);
                var pattern = embeddedContainer.attr('data-prefix-pattern');
                pattern = pattern.replace(regex, '');
                pattern = prefixPattern + '_' + seq + '--' + pattern;
                embeddedContainer.attr('data-prefix-pattern', pattern);

                // recursivly rewrite entire index for embedded form
                reindexSequence(embeddedContainer);
            }
        }
    }
    seqField.val(seq);
}


/*
 * Clicking 'Remove' should remove row
 */
function onRemove(e) {
    e.preventDefault();

    // get item and container based on remove button clicked
    var row = $(e.target).closest('.embed-form');
    var container = row.closest('.embed-forms');

    // remove row and re-index all seq. indicies.
    row.remove();
    reindexSequence(container);
}


/*
 * Return the highest index seq number.
 */
function getHighestSeqIndex(container) {
    var rows = container.find('.embed-forms-body .embed-form-seq-index');
    var seq = 0;
    for (var i = 0; i < rows.length; i++) {
        var newSeq = parseInt(rows.eq(i).val());
        if (newSeq > seq) {
            seq = newSeq;
        }
    }
    return seq;
}


/*
 * reindex all sequence numbers in DOM order
 */
function reindexSequence(container) {
    var rows = container.find('> .embed-forms-container > .embed-forms-body > .embed-form');
    for (var i = 0; i < rows.length; i++) {
        rewriteSeqIndex(container, rows.eq(i), i + 1);
    }
}


}(this));
/*
 * SKU Editor
 */
(function() {
"use strict";


cubane.require('cubane.utils');
cubane.require('cubane.dialog');


var _template = undefined;


/*
 * Return the markup for the form template.
 */
function getFormTemplate() {
    if (_template === undefined) {
        _template = $('#sku-editor-form-template').html();
    }
    return _template;
}


/*
 * Return the title of the variety with the given id.
 */
function getVarietyTitleById(varietyId) {
    return window.SKU_VARIETY_INDEX[varietyId].title;
}


/*
 * Return the title of the variety option with the given variety id and
 * variety option id.
 */
function getVarietyOptionTitleById(varietyId, optionId) {
    return window.SKU_VARIETY_INDEX[varietyId].options[optionId].title;
}


/*
 * Return the full title (combination of variety title and option title) for
 * the given combination of variety and option.
 */
function getVarietyOptionFullTitleById(varietyId, optionId) {
    return window.SKU_VARIETY_INDEX[varietyId].options[optionId].fullTitle;
}


/*
 * Return a list of currently assigned varieties and corresponding variety
 * optons in the correct order.
 */
function getAssignedVarieties() {
    var varieties = [];
    $('.sku-editor-variety-options').each(function() {
        // ignore varieties that do not take part in SKU combinations
        if (!$(this).hasClass('sku-editor-active-variety'))
            return;

        var varietyId = parseInt($(this).attr('data-variety-id'));
        var variety = {
            'id': varietyId,
            'title': getVarietyTitleById(varietyId),
            'options': []
        };

        // receive variety options for given variety
        var optionIds = $(this).val();
        if (optionIds) {
            for (var i = 0; i < optionIds.length; i++) {
                var optionId = parseInt(optionIds[i]);
                var title = getVarietyOptionTitleById(varietyId, optionId);
                variety.options.push({
                    'id': optionId,
                    'title': title,
                    'fullTitle': getVarietyOptionFullTitleById(varietyId, optionId)
                });
            }

            // sort by variety option title
            variety.options.sort(function(a, b) {
                return a.title.localeCompare(b.title);
            });
        }

        if (variety.options.length > 0) {
            varieties.push(variety);
        }
    });

    // sort by variety title
    varieties.sort(function(a, b) {
        return a.title.localeCompare(b.title);
    });

    return varieties;
}


/*
 * Generate a list of all possible permutations for all given assigned
 * varieties and options.
 */
function getVarietyPermutations(assignedVarieties) {
    if (assignedVarieties.length === 0) {
        return [];
    }

    // determine total number of permutations and start indicies
    var n = 1
    var indicies = [];
    for (var i = 0; i < assignedVarieties.length; i++) {
        n = n * assignedVarieties[i].options.length;
        indicies.push(0);
    }

    // generate permutations
    var permutations = [];
    for (var i = 0; i < n; i++) {
        // extract current permutation
        var permutation = [];
        for (var j = 0; j < assignedVarieties.length; j++) {
            permutation.push({
                'variety': assignedVarieties[j],
                'option': assignedVarieties[j].options[indicies[j]]
            });
        }
        permutations.push(permutation);

        // increase indicies with overflow
        indicies[assignedVarieties.length - 1] += 1;
        for (j = assignedVarieties.length - 1; j >= 0; j--) {
            if (indicies[j] > assignedVarieties[j].options.length - 1) {
                indicies[j] = 0;
                if (j > 0) {
                    indicies[j - 1] += 1;
                }
            }
        }
    }
    return permutations;
}


/*
 * Prefix field attributes
 */
function prefixFormField(nodes, prefix, attrname) {
    nodes.each(function() {
        var v = $(this).attr(attrname);
        if (v) {
            var _id = (attrname == 'id') ? 'id_' : '';
            if (v.indexOf('id_') === 0) v = v.substring(3);
            v = _id + 'f-' + prefix + '-' + v;
            $(this).attr(attrname, v);
        }
    });
}


/*
 * Create and insert a new form into the DOM for the given variety permutation.
 */
function createSKUForm(permutation, data) {
    if (data === undefined) data = {};

    // construct list of variety option ids for this permutation
    var optionIds = [];
    for (var i = 0; i < permutation.length; i++) {
        optionIds.push(permutation[i].option.id);
    }

    // get template markup
    var template = getFormTemplate();

    // create new DOM node and configure variety option identifiers for it
    var node = $(template);
    node.attr('data-ids', optionIds.join(','));

    // set primary id if given in initial data
    if (data.id) {
        node.attr('data-id', data.id);
    }

    // populate intial data for this form based on the given data
    var keys = Object.keys(data);
    for (var i = 0; i < keys.length; i++) {
        var field = node.find('input[name="' + keys[i] + '"]');
        if (field.attr('type') === 'checkbox') {
            if (data[keys[i]]) {
                field.attr('checked', 'checked');
            } else {
                field.removeAttr('checked');
            }
        } else {
            field.val(data[keys[i]]);
        }
    }

    // populate form field errors
    if (data.errors) {
        for (var i = 0; i < data.errors.length; i++) {
            var field = node.find('input[name="' + data.errors[i].field + '"]');
            if (field.length > 0) {
                var group = field.closest('.control-group');
                group.addClass('error');
                group.append($('<div class="help-inline">' + data.errors[i].error + '</div>'));
            }
        }
    }

    // construct list of variety option assignments for this form
    var container = node.find('.sku-editor-option-varieties');
    for (var i = 0; i < permutation.length; i++) {
        var j = i + 1;
        container.append($('<div class="sku-editor-option-variety" data-id="' + permutation[i].option.id + '">' + permutation[i].option.fullTitle + '</div>'));
        container.append($('<input class="sku-editor-option-variety-assignment" data-index="' + j + '" type="hidden" id="id_vo_' + j + '" name="vo_' + j + '" value="' + permutation[i].option.id + '">'));
    }

    // prefix id and name attributes to make them unique
    var prefix = optionIds.join('-');
    var labels = node.find('label');
    var inputs = node.find('input').not('[name="skus"]');
    prefixFormField(labels, prefix, 'for');
    prefixFormField(inputs, prefix, 'id');
    prefixFormField(inputs, prefix, 'name');

    // populate sku identifier field (hidden)
    node.find('input[name="skus"]').val(prefix);

    // apply visual class to reflect enabled/disabled state
    if (data.enabled) {
        node.addClass('sku-enabled');
    }

    return node
}


/*
 * Find initial data for the given permutation in the given set of SKU data
 * records.
 */
function getInitialFormDataForPermutation(permutation, data) {
    // collect a list of possible matches
    var matches = [];
    if (permutation.length > 0) {
        // for each data record...
        var _ids = Object.keys(data);
        for (var i = 0; i < _ids.length; i++) {
            // determine match for each record based on matching variety
            // option identifiers. Variety options may not appear in the same
            // order as the permutation. Also we may not require all fields to
            // match, so that we can still map the best possible combination
            // whenever we add another variety.
            var nMatches = 0;
            for (var j = 0; j < permutation.length; j++) {
                // one varity matching will consider it. The match with the
                // most correlating variety options will win in the end...
                if (data[_ids[i]].variety_options.indexOf(permutation[j].option.id) !== -1) {
                    nMatches += 1;
                }
            }

            if (nMatches > 0) {
                matches.push({
                    nMatches: nMatches,
                    dataKey: _ids[i]
                });
            }
        }
    }

    // find the match with the highest number of matches
    var bestMatch = undefined;
    var numberMatches = 0;
    for (var i = 0; i < matches.length; i++) {
        if (matches[i].nMatches > numberMatches) {
            bestMatch = matches[i];
            numberMatches = matches[i].nMatches;
        }
    }

    // return best match or empty data.
    if (bestMatch) {
        // return clone
        return {
            numberMatches: numberMatches,
            data: cubane.utils.clone(data[bestMatch.dataKey])
        };
    } else {
        return {
            numberMatches: 0,
            data: undefined
        };
    }
}


/*
 * Update SKU form entries for all possible combinations for the currently
 * assigned variety options.
 */
function updateSKUForms(data, incremental) {
    if (data === undefined) data = {};
    if (incremental === undefined) incremental = true;

    // get currently assigned varieties and options
    var assignedVarieties = getAssignedVarieties();

    // get all possible permutations for all assigned varieties
    var permutations = getVarietyPermutations(assignedVarieties);

    // collect all data ids from DOM
    var dataIds = getInitialDataIds();

    // remove all previous forms
    var frame = $('.sku-editor-options-container');
    var container = $('.sku-editor-options');
    container.empty();

    // construct initial data for each form permutation
    var formData = [];
    var scores = []
    for (var i = 0; i < permutations.length; i++) {
        // get initial data for this permutation (best match)
        scores.push(getInitialFormDataForPermutation(permutations[i], data));
    }

    // eleminate duplicates by only keeping the ones with the highest scores
    var initialData = []
    for (var i = 0; i < permutations.length; i++) {
        // find best matching SKU record
        var numberMatches = scores[i].numberMatches;
        var bestMatch = undefined;
        for (var j = 0; j < scores.length; j++) {
            if (i != j && scores[j].data !== undefined && scores[i].data !== undefined && scores[j].data.id == scores[i].data.id) {
                if (scores[j].numberMatches > numberMatches) {
                    numberMatches = scores[j].numberMatches
                    bestMatch = scores[j];
                }
            }
        }

        // determine initial form data for permutation
        var initialData = {};
        if (bestMatch === undefined) {
            // no other record has been found. Take the one we have...
            if (scores[i].data !== undefined) {
                initialData = scores[i].data;
            }
        } else {
            // a new (higher scoring) record has been found for a different
            // combination, so this combination becomes in-active in favour
            // of the combination yet to come...
            initialData.enabled = false;
        }

        // keep track of which data identifiers we've assigned so far
        if (incremental && initialData.id !== undefined) {
            var index = dataIds.indexOf(initialData.id);
            if (index !== -1) {
                dataIds.splice(index, 1);
            } else {
                initialData.enabled = false;
            }
        }

        // add form data to the list
        formData.push({
            permutation: permutations[i],
            initialData: initialData
        });
    }

    // sort options, so that we present the ones enabled first...
    formData.sort(function(a, b) {
        return (
            a.initialData.enabled > b.initialData.enabled) ?
                -1 : ((b.initialData.enabled > a.initialData.enabled) ? 1 : 0
        );
    });

    // create forms and add them to the DOM
    if (formData.length > 0) {
        for (var i = 0; i < formData.length; i++) {
            var form = createSKUForm(formData[i].permutation, formData[i].initialData);
            container.append(form);
        }
        frame.removeClass('empty');
    } else {
        frame.addClass('empty');
    }
}


/*
 * Return intial form data based on all existing data of form elements within
 * the current DOM structure; so that the new form elements will contain the
 * same form data.
 */
function getInitialDataFromDOM() {
    var container = $('.sku-editor-options');
    var nodes = container.find('.sku-editor-option');

    var data = {};
    for (var i = 0; i < nodes.length; i++) {
        var node = nodes.eq(i);
        var id = parseInt(node.attr('data-id'));
        if (isNaN(id)) id = undefined;

        data[i.toString()] = {
            'id': id,
            'enabled': node.find('input[name$="enabled"]').is(':checked'),
            'sku': node.find('input[name$="sku"]').val(),
            'barcode': node.find('input[name$="barcode"]').val(),
            'price': node.find('input[name$="price"]').val(),
            'stocklevel': node.find('input[name$="stocklevel"]').val(),

        };

        var assignments = node.find('.sku-editor-option-variety-assignment');
        var varietyOptions = []
        for (var j = 0; j < assignments.length; j++) {
            var assignment = assignments.eq(j);
            varietyOptions.push(parseInt(assignment.val()));
        }
        data[i.toString()].variety_options = varietyOptions;
    }

    return data;
}


/*
 * Return a list of data identifiers that should be present to start with after
 * the page has been loaded.
 */
function getInitialDataIds() {
    var keys = Object.keys(window.SKU_INITIAL);
    var ids = [];

    for (var i = 0; i < keys.length; i++) {
        ids.push(parseInt(keys[i]));
    }

    return ids;
}


/*
 * Return the count of SKU combinations that are currently selected.
 */
function getActiveSKUCount() {
    var data = getInitialDataFromDOM();
    var keys = Object.keys(data);
    var count = 0;
    for (var i = 0; i < keys.length; i++) {
        if (data[keys[i]].enabled) {
            count += 1;
        }
    }
    return count;
}


/*
 * initialise SKU editor
 */
function init() {
    // are we on the correct page?
    if ($('.sku-editor').length === 0) {
        return;
    }

    // recognise a variety option being added
    $('.sku-editor-variety-options').on('change', function (e) {
        updateSKUForms(getInitialDataFromDOM(), true);
    });

    // variety option enable/disable toggle
    $(document).on('change', '.sku-editor-option .field-enabled input[type="checkbox"]', function(e) {
        var checkbox = $(e.target).closest('input[type="checkbox"]');
        var node = checkbox.closest('.sku-editor-option');

        if (checkbox.is(':checked')) {
            node.addClass('sku-enabled');
        } else {
            node.removeClass('sku-enabled');
        }
    });

    // attempt to save should veryfy that we are not accedentally removing all
    // varieties...
    $('.form-actions [type="submit"]').on('click', function(e) {
        if (getActiveSKUCount() == 0) {
            e.preventDefault();

            cubane.dialog.confirm('No Varieties Assigned', 'No SKU combinations have been enabled. This will remove all variety assignments. Are you sure that you want to continue?', function() {
                $('form.sku-editor').submit();
            });
        }
    });

    // initial setup
    updateSKUForms(window.SKU_INITIAL, false);
}


/*
 * Main
 */
init();


})();
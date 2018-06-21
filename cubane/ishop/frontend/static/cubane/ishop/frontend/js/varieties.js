/*
 * Variety filter panel
 */
(function (globals){
"use strict";


cubane.require('cubane.urls');


function initVarietyFilter() {
    // Toggle variety filter should toggle variety filter panel...
    $('.variety-filter-toggle').bind('click', function(e) {
        toggleFilter();
    });

    // Clicking overlay should close variety filter panel
    $('.panel-overlay').on('click', function(e) {
        if (panelIsOpen()) {
            closePanel();
        }
    });

    // Clicking basket toggle should close variety filter panel if open
    $('.basket-panel-toggle').on('click', function(e) {
        if (panelIsOpen()) {
            closePanel();
        }
    });

    // Clicking on group title or arrow should close or open group
    $('.variety-filter-group-title').on('click', function(e) {
        var group = $(e.target).closest('.variety-filter-group');
        group.toggleClass('closed');
    });

    // Check and submit when changing filter by clicking on the filter title
    //$('.variety-filter-option').bind('click keyup', function(e) {
    //    submit();
    //});
    $('.variety-filter-apply').bind('click', function(e) {
        submit();
    });

    // clear all filters per group...
    $('.variety-filter-clear-group').bind('click', function(e) {
        e.preventDefault();
        $(e.target).closest('.variety-filter-group').find('.variety-filter-option-price').removeAttr('value');
        $(e.target).closest('.variety-filter-group').find('.variety-filter-option-check').removeAttr('checked');
        submit();
    });

    // remove active filter
    $('.active-variety-filter-option-remove').bind('click', function(e) {
        var id = $(e.target).closest('.active-variety-filter-option-remove').attr('data-id');
        var activeOption = $(e.target).closest('.active-variety-filter-option').first();
        var option = $('#' + id);
        if (option.length > 0) {
            option.removeAttr('checked');

            if ($('.active-variety-filter-option').length == 1) {
                // fade out entire filter group, since this is the last
                // remaining filter option left...
                $('.variety-filter-footer .variety-filter-group').fadeOut('fast', function() {
                    activeOption.remove();
                });
            } else {
                // fade out option clicked
                activeOption.fadeOut('fast', function() {
                    activeOption.remove();
                });
            }
        }
    });
}


function toggleFilter() {
    if (panelIsOpen()) {
        closePanel();
        ga('send', 'event', 'Filter Panel', 'Close');
    } else {
        openPanel();
        ga('send', 'event', 'Filter Panel', 'Open');
    }
}


function closePanel() {
    var panel = $('.variety-filter-panel');
    var wrapper = $('.wrapper');
    var body = $('body');

    if (panel.hasClass('open')) {
        panel.removeClass('open');
        wrapper.removeClass('variety-filter-open');
        body.removeClass('body-variety-filter-open');
    }
}


function openPanel() {
    var panel = $('.variety-filter-panel');
    var wrapper = $('.wrapper');
    var body = $('body');

    if (!panel.hasClass('open')) {
        panel.addClass('open');
        wrapper.addClass('variety-filter-open');
        body.addClass('body-variety-filter-open');
    }
}


function panelIsOpen() {
    return $('.variety-filter-panel').hasClass('open');
}


function getFilterArguments() {
    var args = {};
    var inputs = $('.variety-filter-option-check');
    for (var i = 0; i < inputs.length; i++) {
        var input = inputs.eq(i);
        var argname = input.attr('name');
        if (argname == '') continue

        if (args[argname] === undefined) {
            args[argname] = [];
        }

        if (input.is(':checked')) {
            args[argname].push(input.val());
        }
    }
    return args
}


function getFilterUrl(currentUrl, args) {
    var argnames = Object.keys(args);
    var url = currentUrl;
    for (var i = 0; i < argnames.length; i++) {
        var argname = argnames[i];
        var url = cubane.urls.combineUrlArg(url, argname, args[argname].join(','));
    }
    return url;
}


function submit() {
    var args = getFilterArguments();
    var url = getFilterUrl(window.location.href, args);
    window.location.href = url
}


/*
 * Main
 */
initVarietyFilter();


}(this));

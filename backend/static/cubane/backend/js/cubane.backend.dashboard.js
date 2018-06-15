(function() {
    "use strict";


    cubane.require('cubane.dialog');
    cubane.require('cubane.urls');


    cubane.namespace('cubane.backend.dashboard');


    /*
     * Update widget list by hiding options that are not available anymore
     */
    function updateWidgetList() {
        // build index of widgets that we have installed
        var installed = {};
        var widgets = $('.dashboard-widget');
        for (var i = 0; i < widgets.length; i++) {
            installed[widgets.eq(i).attr('data-identifier')] = true;
        }

        // show/hide options that we've already installed
        var options = $('.dashboard-add-widget-toolbar select option');
        for (var i = 0; i < options.length; i++) {
            var option = options.eq(i);
            option.attr('disabled', installed[option.attr('value')] !== undefined);
        }

        // enable select2 for add widget select field
        if (jQuery().select2) {
            $('.dashboard-add-widget-toolbar select').select2();
        }
    }


    /*
     * Update UI State
     */
    function updateUIState(widget) {
        if (jQuery().select2) {
            widget.find('select').select2();
        }
    }


    /*
     * Return the widget with the given identifier.
     */
    function getWidgetByIdentifier(widgetIdentifier) {
        return $('.dashboard-widget[data-identifier="' + widgetIdentifier + '"]');
    }


    /*
     * Update widget options
     */
    function updateWidgetOptions(widgetIdentifier, options) {
        var widget = getWidgetByIdentifier(widgetIdentifier);
        if (widget.length > 0) {
            $.post(cubane.urls.reverse('cubane.backend.dashboard_widget_options') + '?widget=' + widgetIdentifier, options, function(json) {
                if (json.success) {
                    widget.replaceWith(json.widget_html);

                    widget = getWidgetByIdentifier(widgetIdentifier);
                    updateUIState(widget);
                }
            }, 'JSON');
        }
    }


    /*
     * Main
     */
    if ($('.dashboard').length > 0) {
        // go to edit page when clicking on an element that has been annotated
        // to be editable or interactable...
        $(document).on('click', '.dashboard-widget [data-target]', function(e) {
            var url = $(e.target).closest('[data-target]').attr('data-target');
            if (url) {
                cubane.backend.openIndexDialog(url, false, false);
            }
        });

        // selecting a dashboard widget should add the widget to the dashboard
        // for the current user...
        $('.dashboard-add-widget-toolbar button').on('click', function(e) {
            e.preventDefault();
            var widgetIdentifier = $('.dashboard-add-widget-toolbar select').val();
            if (widgetIdentifier) {
                $.post(cubane.urls.reverse('cubane.backend.add_dashboard_widget'), {'widget': widgetIdentifier}, function(json) {
                    if (json.success) {
                        $('.dashboard-widgets').append(json.widget_html);
                        $('.dashboard-add-widget-toolbar select').val('');
                        updateWidgetList();

                        var widget = getWidgetByIdentifier(widgetIdentifier);
                        updateUIState(widget);
                    }
                }, 'JSON');
            }
        });

        // removing a dashboard widget
        $(document).on('click', '.dashboard-widget .ui-remove', function(e) {
            e.preventDefault();
            var widget = $(e.target).closest('.dashboard-widget');
            var widgetIdentifier = widget.attr('data-identifier');
            if (widgetIdentifier) {
                $.post(cubane.urls.reverse('cubane.backend.remove_dashboard_widget'), {'widget': widgetIdentifier}, function(json) {
                    if (json.success) {
                        widget.remove();
                        updateWidgetList();
                    }
                }, 'JSON');
            }
        });

        // update options due to changing select field or clicking on an item
        $(document).on('change', '.dashboard-widget select[data-option]', function(e) {
            var select = $(e.target).closest('select');
            var widgetIdentifier = select.closest('.dashboard-widget').attr('data-identifier');
            var optionName = select.attr('data-option');
            var value = select.val();
            var options = {}
            options[optionName] = value;
            updateWidgetOptions(widgetIdentifier, options);
        });

        // make dashboard widgets sortable
        cubane.backend.sortable('.dashboard-widget', '.ui-sortable-handle', function() {
            var seq = [];
            var widgets = $('.dashboard-widget');
            for (var i = 0; i < widgets.length; i++) {
                var widgetIdentifier = widgets.eq(i).attr('data-identifier');
                seq.push(widgetIdentifier);
            }
            console.log('seq:', seq);
            $.post(cubane.urls.reverse('cubane.backend.dashboard_seq'), {'seq': seq}, function(json) {}, 'JSON');
        }.bind(this), undefined, true, true);

        // every few seconds, cycle through welcome messages
        setInterval(function() {
            var current = $('.dashboard-welcome-message.active');
            if (current.length > 0) {
                var next = current.next('.dashboard-welcome-message');
                if (next.length === 0) {
                    next = current.parent().find('.dashboard-welcome-message').first();
                }
                if (next.length > 0) {
                    current.removeClass('active');
                    next.addClass('active');
                }
            }
        }, 3000);

        // update state
        updateWidgetList();
    }


    /*
     * Exports
     */
    cubane.backend.dashboard.updateWidgetOptions = updateWidgetOptions;
})();
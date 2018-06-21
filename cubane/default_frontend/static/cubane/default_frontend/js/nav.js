/*
 * Provides realyable second level navigation menues.
 */
(function (globals){
"use strict";


/*
 * Enable javascript-based navigation on given navigation items.
 */
function _cubane_navigation(rootSelector, itemSelector, containerSelector, minimumDeviceWidth) {
    // take over control and ownership of the navigation, which
    // should disable css-based solution that might already be in place
    var root = $(rootSelector);
    _takeControl(root);
    _bindHover(root);


    function _takeControl(root) {
        root.addClass('cubane-navigation');
    }


    function _bindHover(root) {
        // mouse enter
        $(document).on('mouseenter', itemSelector, function(e) {
            var item = $(e.target).closest(itemSelector);
            var container = item.find(containerSelector);
            _presentItemContainer(item, container);
        });

        // mouse leave
        $(document).on('mouseleave', itemSelector, function(e) {
            var item = $(e.target).closest(itemSelector);
            var container = item.find(containerSelector);
            _hideItemContainer(item, container);
        });
    }


    function _presentItemContainer(item, container) {
        // do not interfer with mobile navigation
        if (minimumDeviceWidth !== undefined && window.innerWidth < minimumDeviceWidth)
            return;

        if (item.hasClass('cubane-navigation-hover'))
            return;

        item.addClass('cubane-navigation-hover');
        _positionItem(item, container);
    }


    function _hideItemContainer(item, container) {
        item.removeClass('cubane-navigation-hover');
        container.removeAttr('style');
    }


    function _positionItem(item, container) {
        var pos = container.offset();
        var d = pos.left + container.width() - window.innerWidth;
        if (d > 0) {
            container.css('margin-left', (-d).toString() + 'px');
        }
    }
}


/*
 * Exports
 */
globals.cubane_navigation = _cubane_navigation;


}(this));
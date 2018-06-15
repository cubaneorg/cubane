/*
 * InnerShed Website and Application Framework
 * (C) Copyright 2013 InnerShed Ltd. All rights reserved.
 *
 * InnerShed Core Framework.
 *
 */
(function (globals){
"use strict";


cubane.namespace('cubane.pulse');


var positionCheck = undefined;


/*
 * Creates a pulsing element in the same position as the element given.
 */
cubane.pulse.place = function place(element) {
    this.remove();
    if (element.length > 0) {
        var bounds = element[0].getBoundingClientRect();
        var container = _createElement(bounds);

        $('body').append(container);

        element.eq(0).on('click', cubane.pulse.remove);

        positionCheck = setInterval(function(){
            bounds = element[0].getBoundingClientRect();
            _positionElement(container, bounds);
        }, 150);
    }
};


/*
 * Removes any existing pulse elements from the DOM.
 */
cubane.pulse.remove = function remove() {
    $('.pulse-item-container').remove();
    if (positionCheck) clearInterval(positionCheck);
};


function _createElement(bounds) {
    var pulse = $('<span class="pulse-item"></span>');
    var container = $('<span class="pulse-item-container"></span>');
    _positionElement(container, bounds);
    container.append(pulse);
    return container;
};


function _positionElement(element, bounds) {
    for (var key in bounds) {
        if (['top', 'left', 'right', 'bottom', 'x', 'y', 'width', 'height'].indexOf(key) !== -1) {
            element.css(key, bounds[key])
        }
    }
}


}(this));

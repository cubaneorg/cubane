/*
 * Provides off canvas navigation for responsive websites.
 */
(function(globals){
"use strict";

// open state starts false as we do not want the navigation open on load
var navOpen = false;
var toggle = document.getElementById('offcanvas-nav-toggle');
var navigation = document.getElementById('offcanvas-nav-items');
var content = document.getElementsByClassName('offcanvas-content');

// toggle phone navigation
if (toggle) {
    if (window.addEventListener) {
        toggle.addEventListener('click', function() {
            navOpen = _toggleNav();
        });
    } else if (window.attachEvent)  {
        toggle.attachEvent('click', function() {
            navOpen = _toggleNav();
        });
    }
}

function hasClass(elem, className) {
    return elem.className.indexOf(className) > -1;
}


function _toggleNav() {
    if (hasClass(navigation, 'open')) {
        navigation.className = navigation.className.replace(new RegExp('\\s' + 'open', 'g'), '');
        _toggleContent();

        return false;
    } else {
        navigation.className += ' open';
        _toggleContent();

        return true;
    }
}


function _toggleContent() {
    for (var i = 0; i < content.length; i++) {
        if (hasClass(content[i], 'open')) {
            content[i].className = content[i].className.replace(new RegExp('\\s' + 'open', 'g'), '');
        } else {
            content[i].className += ' open';
        }
    }
}

}(this));

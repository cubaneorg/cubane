(function () {
    "use strict";


    cubane.require('cubane.dom');
    cubane.require('cubane.string');


    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('field')) {
            var controls = cubane.dom.closest(e.target, '.url-input');
            if (controls) {
                var input = controls.querySelector('input[type="url"]');
                if (input && input.value) {
                    var url = input.value.toLowerCase();
                    if (cubane.string.startsWith(url, 'http://') || cubane.string.startsWith(url, 'https://')) {
                        var win = window.open(input.value, '_blank');
                        win.focus();
                    }
                }
            }
        }
    })
})();
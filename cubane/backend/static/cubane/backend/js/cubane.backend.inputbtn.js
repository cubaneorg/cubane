(function () {
    "use strict";


    cubane.require('cubane.dom');
    cubane.require('cubane.string');


    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('field')) {
            var group = cubane.dom.closest(e.target, '.control-group');
            if (group) {
                var isUrlField = group.classList.contains('url-input');
                var isEmailField = group.classList.contains('email-input');
                var isTelField = group.classList.contains('tel-input');
                if (isUrlField || isEmailField || isTelField) {
                    var input = group.querySelector('input');
                    if (input && input.value) {
                        if (isUrlField) {
                            var url = input.value.toLowerCase();
                            if (cubane.string.startsWith(url, 'http://') || cubane.string.startsWith(url, 'https://')) {
                                var win = window.open(input.value, '_blank');
                                win.focus();
                            }
                        } else if (isEmailField) {
                            window.location.href = 'mailto:' + input.value;
                        } else if (isTelField) {
                            window.location.href = 'tel:' + input.value;
                        }
                    }
                }
            }
        }
    })
})();
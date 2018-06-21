(function() {
    "use strict";


    cubane.require('cubane.dom');


    var addresses = [];
    var activeInput = null;
    var errorMessage = null;


    function removePostcodeLookup() {
        clearError();
        var select = document.querySelector('.postcode-lookup-select');
        if (select) {
            select.parentNode.classList.remove('postcode-lookup-container');
            select.remove();
        }

        addresses = [];
        activeInput = null;
    }


    function displayError(message) {
        // remove old errors first
        clearError();
        activeInput.parentElement.parentElement.parentElement.classList.add('error');
        errorMessage = document.createElement('div');
        errorMessage.setAttribute('class', 'help-inline postcode-lookup-error');
        errorMessage.innerHTML = message;
        activeInput.parentElement.parentElement.append(errorMessage);
    }

    function clearError() {
        if (activeInput) {
            activeInput.parentElement.parentElement.parentElement.classList.remove('error');
            var errorMessage = document.querySelector('.postcode-lookup-error');
            if (errorMessage) errorMessage.remove();
        }
    }


    function postcodeLookup(postcode) {
        if (postcode == '') return;

        var request = new XMLHttpRequest();
        request.open('GET', '/postcode-lookup/?postcode=' + postcode, true);
        request.onload = function() {
            if (this.status >= 200 && this.status < 400) {
                var data = JSON.parse(this.response);
                var oldSelect = document.querySelector('.postcode-lookup-select');
                if (oldSelect) {
                    oldSelect.parentNode.classList.remove('postcode-lookup-container');
                    oldSelect.remove();
                }

                if (data) {
                    addresses = data;
                    if (data.length > 0) {
                        var select = document.createElement('div');
                        select.setAttribute('class', 'postcode-lookup-select');

                        var height = 0;
                        for (var i = 0; i < data.length; i++) {
                            select.innerHTML += '<div class="postcode-lookup-select-option" data-value="' + i + '" >' + data[i]['address_full'] + '</div>';
                        }

                        activeInput.parentNode.append(select);

                        var option = document.querySelector('.postcode-lookup-select-option');
                        select = document.querySelector('.postcode-lookup-select');
                        select.style.height = (option.offsetHeight * parseInt(activeInput.getAttribute('data-size')))  + 'px';

                        // indication on parent
                        activeInput.parentNode.classList.add('postcode-lookup-container');
                    }
                } else {
                    displayError('Postcode not found.');
                }
            } else {
                displayError('Address Finder is temporarily not available. Please fill in all required fields.');
            }
        };

        request.onerror = function() {
            displayError('Address Finder is temporarily not available. Please fill in all required fields.');
        };

        request.send();
    }


    function setupLookupField(input) {
        var newButton = document.createElement('button');
        newButton.setAttribute('type', 'button');
        newButton.setAttribute('data-id', input.id);
        newButton.setAttribute('class', 'postcode-lookup-button');
        newButton.innerHTML = 'Find';
        input.parentNode.appendChild(newButton);
    }


    function setField(container, prefix, fieldname, value) {
        var refFieldname = activeInput.getAttribute('data-' + fieldname.replace(/_/g, '-'));
        if (refFieldname) {
            // support filter form within the backend system
            if (cubane.dom.closest(activeInput, '.cubane-listing-filter-form')) {
                refFieldname = 'id__filter_' + refFieldname.substr(3);
            }

            // prefix?
            if (prefix) {
                if (refFieldname.indexOf('id_') === 0) {
                    refFieldname = refFieldname.substr(2);
                }
                prefix += '--';
            }

            var field = container.querySelector('#' + prefix + refFieldname);
            if (field) {
                field.value = value;
            }
        }
    }


    /*
     * Main
     */
    var inputs = document.querySelectorAll('.postcode-lookup');
    if (inputs) {
        // create buttons
        for (var i = 0; i < inputs.length; i++) {
            setupLookupField(inputs[i]);
        }
    }

    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('postcode-lookup-select-option')) {
            var address = addresses[e.target.getAttribute('data-value')];
            var singleField = activeInput.getAttribute('data-single-field');

            // embedded form?
            var embeddedForm = cubane.dom.closest(activeInput, '.embed-form');
            var prefix = '';
            var container = cubane.dom.closest(activeInput, 'form');
            if (embeddedForm) {
                var parts = activeInput.getAttribute('id').split('--');
                prefix = parts[0];
                container = embeddedForm;
            }

            if (singleField) {
                // set single field
                setField(container, prefix, 'single_field', address['address_full']);
            } else {
                // set individual fields
                for (var key in address) {
                    if (address.hasOwnProperty(key)) {
                        setField(container, prefix, key, address[key]);
                    }
                }
            }

            removePostcodeLookup();
        } else if (e.target.classList.contains('postcode-lookup-button')) {
            var field = cubane.dom.closest(e.target, '.field');
            var input = field.querySelector('.postcode-lookup');

            addresses = [];
            activeInput = input;
            postcodeLookup(input.value);
        } else if (e.target.classList.contains('.postcode-lookup')) {
            removePostcodeLookup();
        }
    }, false);
})();

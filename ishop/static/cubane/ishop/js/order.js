/*
 * Order
 */
(function() {
"use strict";


    var btn = document.querySelector('.backend-payment-btn');
    if (btn) {
        btn.addEventListener('click', function() {
            var form = document.getElementById('backend-order-form');

            if (form) {
                var input = document.createElement("input");
                input.setAttribute("type", "hidden");
                input.setAttribute("name", "autosubmit");
                input.setAttribute("value", "1");
                form.appendChild(input);

                form.submit();
            }
        });
    }


    var btnNextStatuses = document.querySelectorAll('.backend-next-status-btn');

    btnNextStatuses.forEach(function(btnNextStatus) {
        btnNextStatus.addEventListener('click', function() {
            var form = document.getElementById('backend-order-form');

            if (form) {
                var input = document.createElement("input");
                input.setAttribute("type", "hidden");
                input.setAttribute("name", "next-status");
                input.setAttribute("value", btnNextStatus.getAttribute('data-id'));
                form.appendChild(input);


                var activeTab = document.querySelector('.nav-tabs .active > a');
                var value = '#1';

                if (activeTab) {
                    value = activeTab.getAttribute('href').replace('#', '#nav-step-');
                }

                var input2 = document.createElement("input");
                input2.setAttribute("type", "hidden");
                input2.setAttribute("name", "cubane_save_and_continue");
                input2.setAttribute("value", value);
                form.appendChild(input2);

                form.submit();
            }
        });
    });
})();

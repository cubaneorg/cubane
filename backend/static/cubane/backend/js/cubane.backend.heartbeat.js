(function() {
"use strict";


/*
 * List of body class names that would result in NOT running heartbeat,
 * for example dialog windows or login page...
 */
var EXCEMPT_CLASSES = [
    'login',
    'browse-dialog',
    'create-dialog',
    'edit-dialog',
    'is-dialog'
];


cubane.namespace('cubane.backend');
cubane.require('cubane.urls');


/*
 * Check session and if we do not have a valid session anymore, reload the
 * page, which will let us redirect to the login page.
 */
function checkSession(sessionInfo) {
    // no session -> reload page to redirect back to login page
    if (sessionInfo === 'error') {
        location.reload();
    }
}


/*
 * Present current status information of the task runner.
 */
function updateTaskInformation(taskInfo) {
    // task info bar available?
    if ($('.taskinfo').length === 0) {
        return
    }

    if (!taskInfo) return

    // reflect percentage value
    if (taskInfo.percent) {
        var percent = taskInfo.percent ? taskInfo.percent : 0;
        $('.taskinfo-percent').css({
            'width': percent.toString() + '%'
        });
    }

    // reflect message
    var message = '';
    if (!taskInfo.stopped) {
        message = taskInfo.message ? taskInfo.message : '';
    }
    $('.taskinfo-message').html(message);
}


/*
 * Send heartbeat ajax request to receive data from the server periodically.
 * This is mainly for dealing with remotely triggered logout and receiving
 * task runner status information.
 */
function heartbeat() {
    $.ajax({
        method: 'POST',
        url: cubane.urls.reverse('cubane.backend.heartbeat'),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json'
    }).done(function(response) {
        if (response) {
            if (response.result) {
                checkSession(response.result);
            }

            updateTaskInformation(response.taskInfo);
        }
    });
}


/*
 * Return true, if heartbeat should run, e.g. we should have a valid
 * login session at this point.
 */
function shouldRunHeartbeat() {
    // continue to check session regularly (except on the login screen)
    var body = $('body');
    for (var i = 0; i < EXCEMPT_CLASSES.length; i++) {
        if (body.hasClass(EXCEMPT_CLASSES[i])) {
            return false;
        }
    }

    return true;
}


/*
 * Main: Run heartbeat if we should have a valid login session on the
 * current page.
 */
if (shouldRunHeartbeat()) {
    setInterval(heartbeat, 5000);
    heartbeat();
}


})();

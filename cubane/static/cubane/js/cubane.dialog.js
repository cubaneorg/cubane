(function(globals){
"use strict";


cubane.namespace('cubane.dialog');
cubane.require('cubane.utils');


/*
 * Present dialog window to confirm something (Yes/No).
 */
cubane.dialog.confirm = function(title, msg, onOk) {
    function dispose(dlg) {
        dlg.find('.action-confirm').unbind('click');
        dlg.find('.action-close').unbind('click');
        dlg.remove();
    }

    function close(dlg) {
        dlg.modal('hide');
        dispose(dlg);
    }

    function init() {
        var dlg = $([
            '<div class="modal"><div class="modal-header"><a class="close" data-dismiss="modal">×</a>',
            '<h3>', cubane.utils.escapeHtml(title), '</h3></div>',
            '<div class="modal-body"><p>', msg, '</p></div>',
            '<div class="modal-footer">',
            '<button class="btn btn-primary confirm"><i class="icon-white icon-ok"></i> Confirm</button>',
            '<button href="#" class="btn close"><i class="icon-black icon-remove"></i> Close</button>',
            '</div></div>'].join(''));

        dlg.find('.confirm').bind('click', function() {
            close(dlg);
            if ( onOk !== undefined ) onOk();
        });

        dlg.find('.close').bind('click', function() {
            close(dlg);
        });

        dlg.modal();
        dlg.find('.btn.btn-primary').focus();
    }

    init();
};


/*
 * Present generic information dialog window.
 */
cubane.dialog.info = function(title, msg, onClosed) {
    var dlg = $([
        '<div class="modal"><div class="modal-header"><a class="close" data-dismiss="modal">×</a>',
        '<h3>', cubane.utils.escapeHtml(title), '</h3></div>',
        '<div class="modal-body"><p>', msg, '</p></div>',
        '<div class="modal-footer">',
        '<button class="btn btn-primary confirm"><i class="icon-white icon-ok"></i> OK</button>',
        '</div></div>'
    ].join(''));

    dlg.modal();

    dlg.close = function() {
        dlg.modal('hide');
        dlg.find('.confirm, .close').off('click');
        dlg.remove();

        if ( onClosed !== undefined ) onClosed();
    };

    dlg.find('.confirm, .close').on('click', function() {
        dlg.close(dlg);
    });

    dlg.find('.btn.btn-primary').focus();

    return dlg;
};


/*
 * Open dialog window to indicate server working busy indication.
 */
cubane.dialog.working = function(title, msg) {
    var dlg = $([
        '<div class="modal"><div class="modal-header">',
        '<h3>', cubane.utils.escapeHtml(title), '</h3></div>',
        '<div class="modal-body"><i class="icon icon-"></i><p>', msg, '</p></div>',
        '</div>'
    ].join(''));

    dlg.modal();

    dlg.close = function() {
        dlg.modal('hide');
        dlg.remove();
    };

    return dlg;
};


/*
 * Open dialog window to present progress.
 */
cubane.dialog.progress = function(title, msg) {
    var dlg = $([
        '<div class="modal"><div class="modal-header">',
            '<h3>', cubane.utils.escapeHtml(title), '</h3></div>',
            '<div class="modal-body">',
                '<div class="modal-body-progress-msg"><i class="icon icon-"></i><p>', msg, '</p></div>',
                '<div class="model-body-progress-bar-frame">',
                    '<div class="model-body-progress-bar" style="width: 0;"></div>',
                    '<div class="model-body-progress-bar-text">0%</div>',
                '</div>',
            '</div>',
        '</div>'
    ].join(''));

    dlg.modal();

    dlg.close = function close() {
        dlg.modal('hide');
        dlg.remove();
    };

    dlg.progress = function progress(percent) {
        if (percent < 0) percent = 0;
        if (percent > 100) percent = 100;
        var percentText = percent.toString() + '%';
        dlg.find('.model-body-progress-bar').css('width', percentText);
        dlg.find('.model-body-progress-bar-text').text(percentText);
    };

    dlg.finish = function finish() {
        dlg.progress(100);
    }

    return dlg;
};


/*
 * Open dialog window presenting iframe-ed content.
 */
cubane.dialog.iframe = function(title, url, _options) {
    var options = $.extend({}, {
        okBtnLabel: 'OK',
        okBtnIcon: 'icon-ok',
        onOK: function () {},
        onClose: function() {},
        onLoad: function () {},
        dialogClasses: [],
        closeBtn: true,
        closeBtnLabel: 'Close',
        footer: true
    }, _options);

    function dispose(dlg) {
        dlg.find('.action-confirm').unbind('click');
        dlg.find('.action-close').unbind('click');
        dlg.remove();
    }

    function close(dlg) {
        dlg.modal('hide');
        options.onClose();
        dispose(dlg);
    }

    function init() {
        // construct markup for dialog window
        var dialogClasses = options.dialogClasses;
        if (!options.footer) dialogClasses.push('modal-without-footer');
        dialogClasses = dialogClasses.join(' ');
        var html = [
            '<div class="modal modal-iframe ' + dialogClasses + '"><div class="modal-header"><a class="close" data-dismiss="modal"><i class="icon icon-remove"></i></a>',
            '<h3>', (title === null || title === undefined || title.length === 0 ? '&nbsp' : cubane.utils.escapeHtml(title)), '</h3></div>',
            '<div class="modal-body"><div class="scroll-container scroll-ios"><iframe class="dialog-iframe" frameborder="0" src="', url, '"></iframe></div></div>'
        ];

        if (options.footer) {
            Array.prototype.push.apply(html, [
                '<div class="modal-footer">',
                '<button class="btn btn-primary confirm disabled"><i class="icon-white ' + options.okBtnIcon + '"></i> ', options.okBtnLabel, '</button>',
            ]);

            if (options.closeBtn) {
                Array.prototype.push.apply(html, [
                    '<button class="btn close"><i class="icon-black icon-remove"></i> ',
                    options.closeBtnLabel,
                    '</button>'
                ]);
            }

            html.push('</div>');
        }
        html.push('</div>');
        var dlg = $(html.join(''));

        // obtain title from iframe if title is not available...
        var iframe = dlg.find('iframe');
        iframe.bind('load', function() {
            // if we do not have a title, use the meta title of the iframe.
            // if the meta title is empmty, use the first h1 on the page...
            if ( !title ) {
                var t = dlg.find('iframe').contents().find('title').text();
                if (t) {
                    dlg.find('h3').text(t);
                } else {
                    t = dlg.find('iframe').contents().find('.content-frame h1:first').text();
                    if (t) {
                        dlg.find('h3').text(t);
                    }
                }
            }

            // custom on load handler
            options.onLoad(iframe);
        });

        dlg.find('.confirm').bind('click', function(e) {
            e.preventDefault();

            if ( !$(e.target).hasClass('disabled') ) {
                var iframe = dlg.find('iframe').get(0);
                var result = options.onOK(iframe);
                if ( !result ) {
                    close(dlg);
                }
            }
        });

        dlg.find('.close').bind('click', function(e) {
            e.preventDefault();
            close(dlg);
        });

        dlg.modal();
        dlg.find('.btn.btn-primary').focus();
        return dlg;
    }

    return init();
};


/*
 * Close all dialog windows.
 */
cubane.dialog.closeAll = function() {
    var dlg = $('.modal');
    dlg.modal('hide');
    dlg.find('.action-confirm').unbind('click');
    dlg.find('.action-close').unbind('click');
    dlg.remove();
};


}(this));

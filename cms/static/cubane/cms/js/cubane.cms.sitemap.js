(function(globals){
"use strict";


cubane.namespace('cubane.cms.sitemap');


/*
 * Provides user-friendly and rich UI for editing CMS content with live
 * page preview.
 */
cubane.cms.sitemap.SitemapController = function() {
    this.bound = {
        onNodeClicked: $.proxy(this.onNodeClicked, this)
    };

    // clicking on a sitemap node should open it
    $(document).on('click', '.sitemap-row > span.sitemap-title', this.bound.onNodeClicked);

    // load root node
    var node = $('.cubane-sitemap');
    if (node.length > 0) {
        $.get('/admin/sitemap/node/', function(json) {
            this.loadNodeChildren(node, json, true);
        }.bind(this), 'JSON');
    }
};


cubane.cms.sitemap.SitemapController.prototype = {
    /*
     * Dispose
     */
    dispose: function() {
        $(document).off('click', '.sitemap-row > span.sitemap-title', this.bound.onNodeClicked);
        this.bound = null;
    },


    /*
     * Clicking on a sitemap node should open the node and load sub-notes
     * for the node that was clicked on.
     */
    onNodeClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        // load child node markup from server
        var node = $(e.target).closest('li');

        // if the node is open or closed, simply toggle state
        if (node.hasClass('open')) {
            // close node
            node.removeClass('open');
            node.addClass('closed');
        } else if (node.hasClass('closed')) {
            // open node
            node.removeClass('closed');
            node.addClass('open');
        } else if (node.find('> ul').length === 0 && !node.hasClass('empty')) {
            // load children data and open node
            var root = node.closest('ul');
            var pk = parseInt(node.attr('data-pk'));
            var type = node.attr('data-type');
            $.get('/admin/sitemap/node/', {'pk': pk, 'type': type}, function(json) {
                this.loadNodeChildren(node, json);
            }.bind(this), 'JSON');
        }
    },


    loadNodeChildren: function(node, json, header) {
        if (header === undefined) header = false;

        if (json.success) {
            if (json.items.length > 0) {
                var ul = $('<ul></ul>');

                if (header) {
                    ul.append($([
                        '<li>',
                        '<div class="sitemap-row-header">',
                            '<span class="sitemap-title">Page Title</span>',
                            '<span class="sitemap-name">Name</span>',
                            '<span class="sitemap-include-tags">Include Tags</span>',
                            '<span class="sitemap-tags">Tags</span>',
                            '<span class="sitemap-edit"></span>',
                            '<span class="sitemap-view"></span>',
                        '</div>',
                        '</li>'].join(''))
                    );
                }

                for (var i = 0; i < json.items.length; i++) {
                    var item = json.items[i];
                    var li = $('<li></li>');
                    var row = $('<div class="sitemap-row"></div>');

                    if (item.title == 'Home') console.log(item);

                    // add title (first column)
                    var title = $('<span class="sitemap-title"><span class="sitemap-caret icon icon-caret-right"></span>' + item.title + '</span>');
                    row.append(title);

                    // add verbose name
                    row.append($('<span class="sitemap-name">' + (item.name ? item.name : '&nbsp;')  + '</span>'));

                    // add include tags column
                    row.append($('<span class="sitemap-include-tags">' + (item.include_tags ? item.include_tags : '&nbsp;') + '</span>'));

                    // add tags column
                    row.append($('<span class="sitemap-tags">' + (item.tags ? item.tags : '&nbsp;') + '</span>'));

                    // add edit column
                    row.append($('<span class="sitemap-edit"><a class="open-edit-dialog" href="' + item.edit_url + '" title="Edit ' + item.title + '">Edit</a></span>'));

                    // add view column
                    row.append($('<span class="sitemap-view">' + (item.url ? ('<a href="' + item.url + '" target="_blank">View</a>') : '&nbsp;') + '</span>'));

                    // add attributes and classes
                    li.attr('data-pk', item.pk);
                    li.attr('data-type', item.type);
                    li.attr('role', 'button');
                    li.append(row);
                    ul.append(li);

                    if (item.has_children) {
                        li.addClass('has-children');
                    } else {
                        li.addClass('empty');
                    }

                    if (!item.url) {
                        li.addClass('not-navigatable');
                    }
                }
                node.append(ul);
                node.addClass('has-children');
                node.addClass('open');
            } else {
                // remember that we do not have children for this one
                node.addClass('empty');
            }
        }
    }
};


/*
 * Create new sitemap controller when DOM is ready and dispose it on unload.
 */
$(document).ready(function() {
    var controller = new cubane.cms.sitemap.SitemapController();
    $(window).unload(function() {
        controller.dispose();
        controller = null;
    });
});


}(this));
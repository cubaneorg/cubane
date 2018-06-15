/*
 * Provides a list of uploaded documents to choose from as well as a list
 * of cms pages.
 *
 * This implementation is based on the original tinymce plugin "link.
 */
tinymce.PluginManager.add('cubanelink', function(editor) {
	function createLinkList(callback) {
		return function() {
			var linkList = editor.settings.link_list;

			if (typeof(linkList) == "string") {
				tinymce.util.XHR.send({
					url: linkList,
					success: function(text) {
						callback(tinymce.util.JSON.parse(text));
					}
				});
			} else {
				callback(linkList);
			}
		};
	}

	function showDialog(linkList) {
		var data = {}, selection = editor.selection, dom = editor.dom, selectedElm, anchorElm, initialText;
		var win, linkListCtrl, pagesListCtrl, documentsListCtrl, relListCtrl, targetListCtrl, categoryListCtrl, productListCtrl, relatedProductsListCtrl;
        var initialDisplayText = undefined;
        var linkControls = [];

        function selectRef(controlName, value, text) {
            // unselect all other link drop downs
            for (var i = 0 ; i < linkControls.length; i++) {
                if (linkControls[i].items[0].name != controlName) {
                    var control = win.find('#' + linkControls[i].items[0].name);
                    control.value('');
                }
            }
		    win.find('#' + controlName).value(value);

            // update display text if it has been empty initially
		    if (initialDisplayText == '') {
                var textCtrl = win.find('#text');
			    textCtrl.value(text);
		    }

            // update link field
		    win.find('#href').value(value);
        }

        function getSelectHandler(controlName) {
            return function(e) {
                selectRef(controlName, e.control.value(), e.control.text());
		    }
        }

        function buildTypedLink(type, id) {
            return '#link[' + type + ':' + id + ']';
        }

		function buildTypedLinkList(dataList, type) {
			var linkListItems = [{text: '--------', value: ''}];

			tinymce.each(dataList, function(link) {
				linkListItems.push({
					text: link.title,
					value: buildTypedLink(type, link.id)
				});
			});

			return linkListItems;
		}

		function buildLinkList(dataList) {
			var linkListItems = [{text: '--------', value: ''}];

			tinymce.each(dataList, function(link) {
				linkListItems.push({
					text: link.caption || link.title,
					value: link.value || link.url
				});
			});

			return linkListItems;
		}

		function buildRelList(relValue) {
			var relListItems = [{text: '--------', value: ''}];

			tinymce.each(editor.settings.rel_list, function(rel) {
				relListItems.push({
					text: rel.text || rel.title,
					value: rel.value,
					selected: relValue === rel.value
				});
			});

			return relListItems;
		}

		function buildTargetList(targetValue) {
			var targetListItems = [{text: '--------', value: ''}];

			if (!editor.settings.target_list) {
				targetListItems.push({text: 'New window', value: '_blank'});
			}

			tinymce.each(editor.settings.target_list, function(target) {
				targetListItems.push({
					text: target.text || target.title,
					value: target.value,
					selected: targetValue === target.value
				});
			});

			return targetListItems;
		}

		function buildAnchorListControl(url) {
			var anchorList = [];

			tinymce.each(editor.dom.select('a:not([href])'), function(anchor) {
				var id = anchor.name || anchor.id;

				if (id) {
					anchorList.push({
						text: id,
						value: '#' + id,
						selected: url.indexOf('#' + id) != -1
					});
				}
			});

			if (anchorList.length) {
				anchorList.unshift({text: '--------', value: ''});

				return {
					name: 'anchor',
					type: 'listbox',
					label: 'Anchors',
					values: anchorList,
					onselect: getSelectHandler('anchor')
				};
			}
		}

		function updateText() {
			if (!initialText && data.text.length === 0) {
				this.parent().parent().find('#text')[0].value(this.value());
			}
		}

		selectedElm = selection.getNode();
		anchorElm = dom.getParent(selectedElm, 'a[href]');

		data.text = initialText = anchorElm ? (anchorElm.innerText || anchorElm.textContent) : selection.getContent({format: 'text'});
		data.href = anchorElm ? dom.getAttrib(anchorElm, 'href') : '';
		data.target = anchorElm ? dom.getAttrib(anchorElm, 'target') : '';
		data.rel = anchorElm ? dom.getAttrib(anchorElm, 'rel') : '';

		if (selectedElm.nodeName == "IMG") {
			data.text = initialText = " ";
		}

		if (linkList) {
            for (var i = 0; i < linkList.items.length; i++) {
                var item = linkList.items[i];
                var title = item.title;
                var type = item.type;
                var slug = item.slug;
                var links = item.links;
                var elementName = 'link-' + i.toString();

                if (links.length > 0) {
                    linkControls.push({
        			    type: 'container',
        			    label: title,
                        layout: 'flex',
        			    direction: 'row',
        			    spacing: 5,
        			    items: [{
                            name: elementName,
            				type: 'listbox',
            				label: title,
                            minWidth: 300,
            				values: buildTypedLinkList(links, type),
            				value: data.href,
            				onselect: getSelectHandler(elementName)
            			}, {
    			            name: elementName + 'Browse',
    			            text: 'Browse',
    			            type: 'button',
    			        }]
        			});
                }
            }

            if (linkList.links) {
    			linkListCtrl = {
    			    name: 'links',
    				type: 'listbox',
    				label: 'Links',
    				values: buildLinkList(linkList.links),
    				value: data.href,
    				onselect: getSelectHandler('links')
    			};
            }
		}

		if (editor.settings.target_list !== false) {
			targetListCtrl = {
				name: 'target',
				type: 'listbox',
				label: 'Target',
				values: buildTargetList(data.target)
			};
		}

		if (editor.settings.rel_list) {
			relListCtrl = {
				name: 'rel',
				type: 'listbox',
				label: 'Rel',
				values: buildRelList(data.rel)
			};
		}

        var body = [
			{
				name: 'href',
				type: 'filepicker',
				filetype: 'file',
				size: 40,
				autofocus: true,
				label: 'Url',
				value: data.href,
				onchange: updateText,
				onkeyup: updateText
			},
			{name: 'text', type: 'textbox', size: 40, label: 'Text to display', onchange: function() {
				data.text = this.value();
			}},
			buildAnchorListControl(data.href),
		];

        for (var i = 0; i < linkControls.length; i++) {
            body.push(linkControls[i]);
        }

		body.push(linkListCtrl);
		body.push(relListCtrl);
		body.push(targetListCtrl);

		win = editor.windowManager.open({
			title: 'Insert link',
			data: data,
			body: body,
			onSubmit: function(e) {
				var data = e.data, href = data.href;

				// Delay confirm since onSubmit will move focus
				function delayedConfirm(message, callback) {
					window.setTimeout(function() {
						editor.windowManager.confirm(message, callback);
					}, 0);
				}

				function insertLink() {
					if (data.text != initialText) {
						if (anchorElm) {
							editor.focus();
							anchorElm.innerHTML = data.text;

							dom.setAttribs(anchorElm, {
								href: href,
								target: data.target ? data.target : null,
								rel: data.rel ? data.rel : null
							});

							selection.select(anchorElm);
						} else {
							editor.insertContent(dom.createHTML('a', {
								href: href,
								target: data.target ? data.target : null,
								rel: data.rel ? data.rel : null
							}, data.text));
						}
					} else {
						editor.execCommand('mceInsertLink', false, {
							href: href,
							target: data.target,
							rel: data.rel ? data.rel : null
						});
					}
				}

				if (!href) {
					editor.execCommand('unlink');
					return;
				}

				// Is email and not //user@domain.com
				if (href.indexOf('@') > 0 && href.indexOf('//') == -1 && href.indexOf('mailto:') == -1) {
					delayedConfirm(
						'The URL you entered seems to be an email address. Do you want to add the required mailto: prefix?',
						function(state) {
							if (state) {
								href = 'mailto:' + href;
							}

							insertLink();
						}
					);

					return;
				}

				// Is www. prefixed
				if (/^\s*www\./i.test(href)) {
					delayedConfirm(
						'The URL you entered seems to be an external link. Do you want to add the required http:// prefix?',
						function(state) {
							if (state) {
								href = 'http://' + href;
							}

							insertLink();
						}
					);

					return;
				}

				insertLink();
			}
		});
        initialDisplayText = win.find('#text').value();

        function getImageUrlById(id) {
		    for ( var i = 0; i < imageList.length; i++ ) {
		        if ( imageList[i].id == id ) {
		            return imageList[i].url;
		        }
		    }
		    return null;
        }

        function setupBrowseButton(elementName, type, title, slug) {
            var src = win.find('#' + elementName)[0];
        	var btnBrowse = win.find('#' + elementName + 'Browse')[0];
        	btnBrowse.on('click', function() {
        	    cubane.dialog.iframe('Browse ' + title, '/admin/' + slug + '/?browse=true', {
                    onOK: function(iframe) {
                        if ($(iframe).contents().find('body').hasClass('create-edit-page')) {
                            $(iframe).contents().find('form.form-horizontal').submit();
                            return true;
                        }

                        var itemJson = cubane.backend.getItemJson();
                        if (itemJson.length === 1 ) {
                            var value = buildTypedLink(type, itemJson[0].id);
                            src.value(value);
                            selectRef(elementName, value, src.text());
                        }
                    }
                });
        	});
        }

    	// browse button
    	if (linkList) {
            for (var i = 0; i < linkList.items.length; i++) {
                var item = linkList.items[i];
                var title = item.title;
                var type = item.type;
                var slug = item.slug;
                var links = item.links;
                var elementName = 'link-' + i.toString();

                if (links.length > 0) {
                    setupBrowseButton(elementName, type, title, slug);
                }
            }
        }
	}

	editor.addButton('link', {
		icon: 'link',
		tooltip: 'Insert/edit link',
		shortcut: 'Ctrl+K',
		onclick: createLinkList(showDialog),
		stateSelector: 'a[href]'
	});

	editor.addButton('unlink', {
		icon: 'unlink',
		tooltip: 'Remove link',
		cmd: 'unlink',
		stateSelector: 'a[href]'
	});

	editor.addShortcut('Ctrl+K', '', createLinkList(showDialog));

	this.showDialog = showDialog;

	editor.addMenuItem('link', {
		icon: 'link',
		text: 'Insert link',
		shortcut: 'Ctrl+K',
		onclick: createLinkList(showDialog),
		stateSelector: 'a[href]',
		context: 'insert',
		prependToContext: true
	});
});

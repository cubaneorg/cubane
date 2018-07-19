(function() {
    "use strict";


    const SLOT_PADDING_X = 5;
    const SLOT_PADDING_Y = 5;


    var panel = undefined;
    var slotContainer = undefined;
    var btnEdit = undefined;
    var editMode = false;
    var slotElements = [];
    var slots = [];
    var slotPositionInterval = undefined;


    function openDialog(url, title) {
        // close any dialog window that might be open already
        closeDialogWindows();

        // create markup
        var dlg = document.createElement('div');
        dlg.classList.add('cubane-frontend');
        dlg.classList.add('cubane-frontend-modal');
        dlg.innerHTML = (
            '<div class="cubane-frontend cubane-frontend-modal-header">' +
                '<button class="cubane-frontend cubane-frontend-modal-close">X</button>' +
                '<div class="cubane-frontend cubane-frontend-modal-header-title"></div>' +
            '</div>' +
            '<div class="cubane-frontend cubane-frontend-modal-body">' +
                '<iframe class="cubane-frontend cubane-frontend-modal-iframe" frameborder="0"></iframe>' +
            '</div>' +
            '<div class="cubane-frontend cubane-frontend-modal-footer">' +
                '<button class="cubane-frontend cubane-frontend-button cubane-frontend-modal-btn-submit">OK</button>' +
                '<button class="cubane-frontend cubane-frontend-button cubane-frontend-modal-btn-close">Close</button>' +
            '</div>'
        );
        document.body.appendChild(dlg);

        // create backdrop
        var backdrop = document.createElement('div');
        backdrop.classList.add('cubane-frontend');
        backdrop.classList.add('cubane-frontend-modal-backdrop');
        document.body.appendChild(backdrop);

        // load iframe content
        var titleElement = dlg.querySelector('.cubane-frontend-modal-header-title');
        var iframe = dlg.querySelector('.cubane-frontend-modal-iframe');
        iframe.src = url;

        // set title or obtain title from iframe document. Also resize dialog
        // based on iframe content
        if (title !== undefined) {
            titleElement.innerText = title;
        } else {
            iframe.addEventListener('load', function() {
                // title tag
                var d = iframe.contentDocument;
                var documentTitle = d.querySelector('title');
                if (documentTitle) title = documentTitle.innerText;

                // first headline on page
                if (!title) {
                    var headline = d.querySelector('.page-title');
                    if (headline) title = headline.innerText;
                }

                // set title
                if (title) {
                    title = title.replace(/\n/g, ' ');
                    titleElement.innerText = title;
                }

                // make dialog window visible
                document.body.classList.add('cubane-frontend-modal-open');

                // resize dialog window based on content size.
                // If we have drop downs, extend the size so that we can
                // use the drop down control adequately...
                var form = d.querySelector('form.form-horizontal .form-content');
                if (form) {
                    var rect = form.getBoundingClientRect();
                    var h = rect.height;
                    if (
                        d.querySelector('form.form-horizontal .form-content select') ||
                        d.querySelector('form.form-horizontal .form-content .date-field')
                    ) {
                        h += 220;
                    }

                    h = Math.min(window.innerHeight * 0.9, h);
                    iframe.style.minHeight = h + 'px';
                }

                // if we have a map, tinymce, gallery or related listing
                // inside, maximize the window size
                if (d.querySelector('.editable-html, .map-canvas, .cubane-listing, .cubane-collection-items')) {
                    maximizeDialog();
                }

                // tell iframe to resize itself
                d.dispatchEvent(new CustomEvent('cubane-dialog-init'));
            });
        }

        // clicking OK should submit form within iframe
        var btnSubmit = dlg.querySelector('.cubane-frontend-modal-btn-submit');
        btnSubmit.addEventListener('click', function(e) {
            e.preventDefault();

            // if we have another modal inside it, submit that one first
            submitInnerForm(iframe);
        });

        // clicking X should close dialog window
        var btnClose = dlg.querySelector('.cubane-frontend-modal-btn-close');
        btnClose.addEventListener('click', function(e) {
            e.preventDefault();
            closeDialogWindows();
        });

        // clicking close button should close dialog window as well
        var btnX = dlg.querySelector('.cubane-frontend-modal-close');
        btnX.addEventListener('click', function(e) {
            e.preventDefault();
            closeDialogWindows();
        });
    }


    /*
     * Submit form within most-inner iframe (nested)
     */
    function submitInnerForm(iframe, modal) {
        iframe.classList.add('visited');

        var innerModal = iframe.contentDocument.querySelector('.modal');
        if (innerModal) {
            var innerFrame = innerModal.querySelector('iframe');
            submitInnerForm(innerFrame, innerModal);
        } else {
            if (modal !== undefined) {
                // footer present?
                var btnConfirm = modal.querySelector('.modal-footer .btn-primary.confirm');
                if (btnConfirm) {
                    btnConfirm.click();
                    return;
                }
            }

            // otherwise simply submit the form we have
            var form = iframe.contentDocument.querySelector('form.form-horizontal');
            if (form) {
                iframe.classList.add('form-submit');
                submitForm(form);
            }
        }
    }


    /*
     * Close all open dialog windows
     */
    function closeDialogWindows() {
        // hide dialog
        document.body.classList.remove('cubane-frontend-modal-open');

        // remove dialog window
        var dlg = document.querySelector('.cubane-frontend-modal');
        if (dlg) {
            document.body.removeChild(dlg);
        }

        // remove backdrop
        var backdrop = document.querySelector('.cubane-frontend-modal-backdrop');
        if (backdrop) {
            document.body.removeChild(backdrop);
        }
    }


    /*
     * Maximise dialog window size
     */
    function maximizeDialog() {
        var dlg = document.querySelector('.cubane-frontend-modal');
        if (dlg) {
            dlg.classList.add('cubane-frontend-modal-maximized');
        }
    }


    /*
     * Submit given form
     */
    function submitForm(form) {
        // submit form by creating a button and clicking it
        var button = form.ownerDocument.createElement('input');
        button.style.display = 'none';
        button.type = 'submit';
        form.appendChild(button).click();
        form.removeChild(button);
    }


    /*
     * Return true, if there is at least one editable slot on the page.
     */
    function isPageEditable() {
        var elements = document.querySelectorAll('[edit]');
        for (var i = 0; i < elements.length; i++) {
            if (elements[i].offsetHeight !== 0) {
                return true;
            }
        }

        return false;
    }


    /*
     * Create slot container
     */
    function createSlotContainer() {
        var element = document.createElement('div');
        element.classList.add('cubane-frontend');
        element.classList.add('cubane-frontend-slot-container');
        document.body.appendChild(element);
        return element;
    }


    /*
     * Create edit panel
     */
    function createPanel(parentElement, cssClass) {
        var panel = document.createElement('div');
        panel.classList.add('cubane-frontend');
        panel.classList.add(cssClass);
        parentElement.appendChild(panel);
        return panel;
    }


    /*
     * Create button
     */
    function createButton(title) {
        var btn = document.createElement('button');
        btn.classList.add('cubane-frontend');
        btn.classList.add('cubane-frontend-button');
        btn.innerText = title;
        return btn;
    }


    /*
     * Create edit button
     */
    function createEditButton(panel) {
        var editLabel = document.querySelector('body').getAttribute('data-edit-label') || 'Edit';
        var btn = createButton(editLabel);
        btn.classList.add('cubane-frontend-edit-button');
        btn.title = 'Enter Edit Mode';

        if (isPageEditable()) {
            btn.removeAttribute('disabled');
        } else {
            btn.setAttribute('disabled', 'disabled');
        }

        btn.addEventListener('click', onEditClicked);
        panel.appendChild(btn);
        return btn;
    }


    /*
     * Init
     */
    function init() {
        // create UI elements
        createControls();

        // when the document has re-loaded, re-enter edit mode if reloaded
    	if (window.location.hash == '#/reload/') {
            enterEditMode();
            window.location.hash = '#reloaded';
    	}
    }


    /*
     * Create editing controls
     */
    function createControls() {
        slotContainer = createSlotContainer();
        panel = createPanel(document.body, 'cubane-frontend-panel');

        if (isPageEditable()) {
            // create buttons
            var shortcutCreatePanel = createPanel(panel, 'cubane-frontend-shortcut-create-panel');
            if (!createShotcutCreateButtons(shortcutCreatePanel)) {
                shortcutCreatePanel.parentNode.removeChild(shortcutCreatePanel);
            }

            // shortcut edit buttons
            var shortcutEditPanel = createPanel(panel, 'cubane-frontend-shortcut-edit-panel');
            if (!createShotcutEditButtons(shortcutEditPanel)) {
                shortcutEditPanel.parentNode.removeChild(shortcutEditPanel);
            }
        }

        // main edit button
        var editPanel = createPanel(panel, 'cubane-frontend-edit-panel');
        btnEdit = createEditButton(editPanel);

        document.querySelector('body').classList.add('cubane-frontend-editing');
    }


    /*
     * Create shortcut create buttons
     */
    function createShotcutCreateButtons(panel) {
        var elements = document.querySelectorAll('[create]');
        var hasBtns = false;
        for (var i = 0; i < elements.length; i++) {
            var ref = getCreateReference(elements[i]);
            if (ref && ref.title && ref.url) {
                hasBtns = true;
                createShortcutCreateButton(panel, ref);
            }
        }

        return hasBtns;
    }


    /*
     * Create shortcut create button
     */
    function createShortcutCreateButton(panel, ref) {
        var btn = createButton(ref.title);
        btn.classList.add('cubane-frontend-create-shortcut-button');
        btn.title = ref.title;
        btn.setAttribute('create', getCreateReferenceString(ref));
        btn.addEventListener('click', onShortcutCreateButtonClicked);
        panel.appendChild(btn);
        return btn;
    }


    /*
     * Create shortcut edit buttons
     */
    function createShotcutEditButtons(panel) {
        // label
        var label = document.createElement('label');
        label.classList.add('cubane-frontend-edit-shortcut-label');
        label.innerText = 'Edit';
        panel.appendChild(label);

        // buttons
        var elements = document.querySelectorAll('[edit]');
        var hasBtns = false;
        for (var i = 0; i < elements.length; i++) {
            var ref = getSlotReference(elements[i]);
            if (ref && ref.shortcut && ref.helpText) {
                hasBtns = true;
                createShortcutEditButton(panel, ref);
            }
        }

        return hasBtns;
    }


    /*
     * Create shortcut edit button
     */
    function createShortcutEditButton(panel, ref) {
        var btn = createButton(ref.helpText);
        btn.classList.add('cubane-frontend-edit-shortcut-button');
        btn.classList.add('cubane-frontend-secondary-button');
        btn.title = ref.helpText;
        btn.setAttribute('edit', getSlotReferenceString(ref));
        btn.addEventListener('click', onShortcutEditButtonClicked);
        panel.appendChild(btn);
        return btn;
    }


    /*
     * on edit clicked
     */
    function onEditClicked(e) {
        e.preventDefault();
        toggleEditMode();
    }


    /*
     * Toggle edit mode
     */
    function toggleEditMode() {
        if (editMode) {
            leaveEditMode();
        } else {
            enterEditMode();
        }
    }


    /*
     * Enter edit mode
     */
    function enterEditMode() {
        if (!editMode) {
            editMode = true;
            document.body.classList.add('cubane-frontend-edit-mode-enabled');
            createSlots();
        }
    }


    /*
     * Leave edit mode
     */
    function leaveEditMode() {
        if (editMode) {
            editMode = false;
            document.body.classList.remove('cubane-frontend-edit-mode-enabled');
            removeSlots();
        }
    }


    /*
     * Create editable slots indicators
     */
    function createSlots() {
        // create slots
        var elements = document.querySelectorAll('[edit]');
        for (var i = 0, j = 0; i < elements.length; i++) {
            if (elements[i].offsetHeight !== 0) {
                var slot = createSlotForElement(elements[i], j);
                slotElements.push(elements[i]);
                slots.push(slot);
                j += 1;
            }
        }

        // monitor slot position
        updateSlotPositions();
        slotPositionInterval = setInterval(updateSlotPositions, 250);

        // listen to notifications that we've saved some data
        window.addEventListener('cubane-data-saved', onDataSaved);

        // listen to browse notifications
        window.addEventListener('cubane-browse', onBrowse);
    }


    /*
     * Return true, if the given two rectangles are overlapping each other.
     * We do allow rectangles to touch.
     */
    function overlap(a, b) {
        return !(
            a.x + a.w <= b.x + 1 ||
            a.x >= b.x + b.w - 1 ||
            a.y + a.h <= b.y + 1 ||
            a.y >= b.y + b.h - 1
        );
    }


    /*
     * Update slot positions
     */
    function updateSlotPositions() {
        var px = SLOT_PADDING_X;
        var py = SLOT_PADDING_Y;
        var ww = window.innerWidth;
        var dx = window.pageXOffset;
        var dy = window.pageYOffset;

        // compute initial bounds for all elements
        var bounds = [];
        for (var i = 0; i < slotElements.length; i++) {
            var rect = slotElements[i].getBoundingClientRect();
            bounds.push({
                x: dx + rect.left,
                y: dy + rect.top,
                w: rect.width,
                h: rect.height
            });
        }

        // test two areas to overlap or not
        function overlapAny(excludeIndex, x, y, w, h) {
            var rect = { x: x, y: y, w: w, h: h };

            for (var k = 0; k < bounds.length; k++) {
                if (k !== excludeIndex) {
                    if (overlap(rect, bounds[k])) {
                        return true;
                    }
                }
            }

            return false;
        }

        // apply each bounding box without overlaps
        for (var i = 0; i < slotElements.length; i++) {
            var r = bounds[i];

            // apply padding
            if (px !== 0 || py !== 0) {
                if (r.x - px > 0 && r.x + r.w + px < ww && !overlapAny(i, r.x - px, r.y, r.w + (2 * px), r.h)) {
                    r.x -= px;
                    r.w += 2 * px;
                    slots[i].classList.add('cubane-frontend-slot-pull-x');
                } else {
                    slots[i].classList.remove('cubane-frontend-slot-pull-x');
                }

                if (r.y - py > 0 && !overlapAny(i, r.x, r.y - py, r.w, r.h + (2 * py))) {
                    r.y -= py;
                    r.h += 2 * py;
                    slots[i].classList.add('cubane-frontend-slot-pull-y');
                } else {
                    slots[i].classList.remove('cubane-frontend-slot-pull-y');
                }
            }

            slots[i].style.left = r.x + 'px';
            slots[i].style.top = r.y + 'px';
            slots[i].style.width = r.w + 'px';
            slots[i].style.height = r.h + 'px';
        }
    }


    /*
     * Create slot for given editable element.
     */
    function createSlotForElement(element, index) {
        // create slot element
        var slot = document.createElement('div');
        slot.classList.add('cubane-frontend');
        slot.classList.add('cubane-frontend-slot');
        slot.setAttribute('data-slot', index);
        slotContainer.appendChild(slot);

        // optional help text
        var ref = getSlotReference(element);
        if (ref.helpText) {
            var helpText = document.createElement('div');
            helpText.classList.add('cubane-frontend');
            helpText.classList.add('cubane-frontend-slot-help-text');
            helpText.innerText = ref.helpText;
            slot.appendChild(helpText);
        }

        // mark underlying element
        element.classList.add('cubane-frontend-slot-element');

        // click on slot should open dialog window
        slot.addEventListener('click', onSlotClicked);

        return slot;
    }


    function removeSlots() {
        // stop listen to data saved and browse notifications
        window.removeEventListener('cubane-listing-edit', onDataSaved);
        window.removeEventListener('cubane-browse', onBrowse);

        // stop monitoring slot positions
        clearInterval(slotPositionInterval);
        slotPositionInterval = undefined;

        // remove slots
        var _slots = document.querySelectorAll('.cubane-frontend-slot');
        for (var i = 0; i < _slots.length; i++) {
            _slots[i].removeEventListener('click', onSlotClicked);
            slotContainer.removeChild(_slots[i]);
        }

        // unmark slot elements
        var elements = document.querySelectorAll('.cubane-frontend-slot-element');
        for (var i = 0; i < elements.length; i++) {
            elements[i].classList.remove('cubane-frontend-slot-element');
        }

        // remove references
        slotElements = [];
        slots = [];
    }


    /*
     * Slot clicked
     */
    function onSlotClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        var target = e.target;
        while (target && !target.classList.contains('cubane-frontend-slot')) {
            target = target.parentNode;
        }

        var index = parseInt(target.getAttribute('data-slot'));
        var element = slotElements[index];
        var ref = getSlotReference(element);
        var url = getSlotReferenceUrl(ref);

        openDialog(url);
    }


    /*
     * Clicking on shortcut create button
     */
    function onShortcutCreateButtonClicked(e) {
        e.preventDefault();

        enterEditMode();

        var ref = getCreateReference(e.target);
        var url = getCreateReferenceUrl(ref);

        openDialog(url);
    }


    /*
     * Clicking on shortcut edit button
     */
    function onShortcutEditButtonClicked(e) {
        e.preventDefault();

        enterEditMode();

        var ref = getSlotReference(e.target);
        var url = getSlotReferenceUrl(ref);

        openDialog(url);
    }


    /*
     * Data saved
     */
    function onDataSaved() {
        closeDialogWindows();
        reloadPage();
    }


    /*
     * Browse dialog opened
     */
    function onBrowse() {
        maximizeDialog();
    }


    /*
     * Reload current page
     */
    function reloadPage() {
        // reload current page (gracefully)
        window.location.hash = '/reload/';
    	window.location.reload();
    }


    /*
     * Parse create reference
     */
    function getCreateReference(element) {
        var create = element.getAttribute('create');
        var parts = create.split('|');
        return {
            'title': parts[0],
            'url': parts[1]
        };
    }


    /*
     * Reencode create reference
     */
    function getCreateReferenceString(ref) {
        return ref.title + '|' + ref.url
    }


    /*
     * Return the edit url for the given slot reference
     */
    function getCreateReferenceUrl(ref) {
        return (
            ref.url +
            '&frontend-editing=true&index-dialog=true'
        );
    }


    /*
     * Parse the slot reference of the given markup element and return its
     * components.
     */
    function getSlotReference(element) {
        var edit = element.getAttribute('edit');
        var parts = edit.split('|');

        var model = parts[0];
        var shortcut = model.charAt(0) == '!';
        if (shortcut) model = model.substr(1);

        return {
            'model': model,
            'pk': parts[1],
            'propertyName': parts[2],
            'helpText': parts.length >= 4 ? parts[3] : undefined,
            'shortcut': shortcut
        };
    }


    /*
     * Reencode slot reference
     */
    function getSlotReferenceString(ref) {
        return (
            (ref.shortcut ? '!' : '') +
            ref.model + '|' +
            ref.pk + '|' +
            ref.propertyName + '|' +
            ref.helpText
        );
    }


    /*
     * Return the edit url for the given slot reference
     */
    function getSlotReferenceUrl(ref) {
        return (
            '/admin/frontend-edit/' + encodeURIComponent(ref.model) +
            '/?pk=' + encodeURIComponent(ref.pk) +
            '&property-names=' + encodeURIComponent(ref.propertyName) +
            '&frontend-editing=true'
        );
    }


    /*
     * Main
     */
    init();
})();

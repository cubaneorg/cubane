(function() {
    "use strict";


    /*
     * List of resources to load for frontend editing
     */
    var resources = {{ resources|safe }};


    /*
     * We do not load frontend editing on mobile devices
     */
    if (window.innerWidth < 768) {
        return;
    }

    /*
     * See if we have the frontend-editing cookie set and if so, load the
     * actual frontend editing code...
     */
    if (document.cookie.match(/^(.*;)?\s*frontend-editing\s*=\s*[^;]+(.*)?$/)) {
        for (var i = 0; i < resources.length; i++) {
            load(resources[i].typ, resources[i].path);
        }
    }


    /*
     * Load given stylesheet resource
     */
    function load(ext, src) {
        if (ext === 'css') {
            var ref = document.createElement('link');
            ref.rel  = 'stylesheet';
            ref.type = 'text/css';
            ref.href = src;
        } else if (ext === 'js') {
            var ref = document.createElement('script');
            ref.type = 'text/javascript';
            ref.src = src;
        }

        document.getElementsByTagName('head')[0].appendChild(ref);
    }
})();

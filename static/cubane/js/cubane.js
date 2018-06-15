/*
 * InnerShed Website and Application Framework
 * (C) Copyright 2013 InnerShed Ltd. All rights reserved.
 *
 * InnerShed Core Framework.
 *
 */
(function (globals){
"use strict";


if ( !('cubane' in globals) ) {
    globals.cubane = {};
}


/*
 * Core cubane namespace.
 */
globals.cubane.NAMESPACE_SEPARATOR = '.';
globals.cubane.__CURRENT_NAMESPACE = 'cubane';


/*
 * Base Exception
 */
globals.KitError = function (message) {
    this.message = message;
};


KitError.prototype.toString = function () {
    return this.message;
}


/*
 * Return the parts of the given namespace (string) as a list of strings. If the
 * namespace is invalid, the empty string is returned.
 */
cubane.getNamespaceParts = function (namespace) {
    if ( !namespace ) return [];
    if ( !namespace.split ) return [];
    return namespace.split(cubane.NAMESPACE_SEPARATOR);
};


/*
 * Return the current namespace.
 */
cubane.getCurrentNamespace = function () {
    return cubane.__CURRENT_NAMESPACE;
};


/*
 * Creates and returns a new namespace with the given name (string). Please note
 * that the namespace may contain multiple nodes, like 'cubane.geo', in which case
 * each subsequent part of the namespace is created if it does not exist yet.
 * False is returned if the given namespace is invalid and could not be created.
 */
cubane.namespace = function (namespace) {
    var parts = cubane.getNamespaceParts(namespace);
    if ( parts.length === 0 ) return false;

    var g = globals;
	for (var i = 0; i < parts.length; i++) {
		if (!g[parts[i]]) {
			g[parts[i]] = {};
		}
		g = g[parts[i]];
	}

	if ( typeof g !== 'object' ) {
	    throw new KitError(
	        'Unable to create namespace "' + namespace +
    	    '". namespace already exists and is not an object'
    	)
	}

	cubane.__CURRENT_NAMESPACE = namespace;

	return g;
};


/*
 * Get the given namespace (string). If the namespace does not exist, false
 * is returned.
 */
cubane.getNamespace = function (namespace) {
    var parts = cubane.getNamespaceParts(namespace);
    if ( parts.length === 0 ) return false;

    var g = globals;
	for (var i = 0; i < parts.length; i++) {
		if (!g[parts[i]]) {
			return false;
		}
		g = g[parts[i]];
	}

	return g;
};


/*
 * Requires the given namespace (string). If the namespace does not exist, an
 * exception is thrown.
 */
cubane.require = function (namespace) {
    var ns = cubane.getNamespace(namespace);
    if ( !ns ) {
        throw new KitError(
            'Unable to include namespace ' + "'" + namespace + "'" + ' in ' +
            "'" + cubane.getCurrentNamespace() + "'" + '. Please include the ' +
            'corresponding file that defines ' + "'" + namespace + "'" +
            ' before including ' + "'"+ cubane.getCurrentNamespace() + "'."
        );
    }

    return ns;
};


/*
 * Declare given method name on given class as a wrapper for function f;
 */
cubane.declarePrototypeMethod = function (klass, methodName, f) {
    if ( klass.prototype[methodName] ) {
        throw new KitError(
            'Cannot declare prototype method ' + methodName + ' on class ' +
            klass + '. Method is already declared.'
        );
    }

    klass.prototype[methodName] = function () {
        var args = Array.prototype.slice.call(arguments);
        args.unshift(this);
        f.apply(this, args);
    };
};


}(this));

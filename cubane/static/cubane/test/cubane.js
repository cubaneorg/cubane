(function(globals){
"use strict";


module('cubane');


var namespace = 'cubane_test_namespace';


test('cubane.namespace() should create namespace as javascript object', function() {
    ok(!globals[namespace], 'this test requires the namespace "' + namespace + '" not to exist yet.')

    var ns = cubane.namespace(namespace);
    equal(typeof ns, 'object', 'cubane.namespace() should return object');
    equal(typeof globals[namespace], 'object', 'cubane.namespace() should create namespace in gloabl javascript namespace.');
});


test('cubane.namespace() should succeed, if given namespace already exists and is an object.', function() {
    cubane.namespace(namespace);
    cubane.namespace(namespace);
    ok(globals[namespace], 'namespace exists after creating it twice and we did not fail.');
});


test('cubane.namespace() should fail if given namespace already exists and is not an object.', function() {
    globals[namespace] = function() {};

    throws(function() {
        cubane.namespace(namespace);
    }, KitError, 'cubane.namespace() raised KitError.');
});


test('cubane.require() should return given namespace if namespace exists.', function() {
    var ns = cubane.require('cubane.string');
    equal(typeof ns, 'object', 'cubane.require() should return given namespace.');
});


test('cubane.require() should fail if given namespace does not exist yet.', function() {
    throws(function() {
        cubane.require('cubane.doesNotExist');
    }, KitError, 'cubane.require raised KitError.');
});


}(this));

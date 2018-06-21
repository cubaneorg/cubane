/*
 * Point
 */
define(function(require, exports, module) {
    /*
     * Create a new point with given coordinates.
     */
    var Point = function(x, y) {
        this.x = x;
        this.y = y;
    };
    
    
    /*
     * Add given vector to the point vector.
     */
    Point.prototype.add = function add(x, y) {
        this.x += x;
        this.y += y;
    };
    
    
    module.exports = Point;
});
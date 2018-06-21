(function(globals){
"use strict";

$.ajax({
    url:'http://captcha.innershed.com/captcha_api_jsonp.php?action=register',
    dataType: 'jsonp', // Notice! JSONP <-- P (lowercase)
    success:function(json){
        $('#id_captcha_hash').val(json);
        getCaptcha(json);
    }   
});
var getCaptcha = function(hash_tag){
    $.ajax({
        url:'http://captcha.innershed.com/captcha_api_jsonp.php?action=get_captcha&hash='+hash_tag,
        dataType: 'jsonp', // Notice! JSONP <-- P (lowercase)
        success:function(json){
            $('#id_captcha').before(json);
        }   
    });
};


}(this));

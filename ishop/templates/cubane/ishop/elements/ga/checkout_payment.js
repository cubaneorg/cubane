{% for item in order.basket.items %}
ga('ec:addProduct', {
    'id': '{{item.product_id}}',
    'name': '{{item.title}}',
    'price': '{{item.total}}',
    'variant': '{{item.variant}}',
    'quantity': {{item.quantity}}
});
{% endfor %}
ga('ec:setAction','checkout', {'step': {{ step }}});
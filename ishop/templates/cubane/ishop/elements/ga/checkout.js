{% for item in basket.ga_items %}
ga('ec:addProduct', {
    'id': '{{item.id}}',
    'name': '{{item.name}}',
    'category': '{{item.category}}',
    {% if item.brand %}'brand': '{{item.brand}}',{% endif %}
    'variant': '{{item.variant}}',
    'price': '{{item.price}}',
    'quantity': {{item.quantity}}
});
{% endfor %}
ga('ec:setAction','checkout', {'step': {{ step }}});
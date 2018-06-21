ga('ec:addProduct', {
    'id': '{{product.id}}',
    'name': '{{product.title}}',
    {% if product.get_brand_title %}'brand': '{{ product.get_brand_title }}',{% endif %}
    'category': '{{product.category.title}}',
    'price': '{{product.price}}'
});
ga('ec:setAction', 'detail');
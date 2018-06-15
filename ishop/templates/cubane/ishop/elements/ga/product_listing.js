{% for p in products.object_list %}
ga('ec:addImpression', {
    'id': '{{p.id}}',
    'name': '{{p.title}}',
    'category': '{{p.category.title}}',
    {% if p.get_brand_title %}'brand': '{{ p.get_brand_title }}',{% endif %}
    'price': '{{p.price}}',
    'list': '{%if galist%}{{galist}}{%endif%}'
});
{% endfor %}

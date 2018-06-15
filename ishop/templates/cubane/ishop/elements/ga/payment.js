{% if not order.ga_sent %}
    {% for item in order.basket.items %}
    ga('ec:addProduct', {
        'id': '{{item.product_id}}',
        'name': '{{item.title}}',
        'price': '{{item.total}}',
        'variant': '{{item.variant}}',
        'quantity': {{item.quantity}}
    });
    {% endfor %}

    ga('ec:setAction', 'purchase', {
        'id': '{{order.order_id}}',
        'affiliation': '{{settings.name}} - Online',
        'revenue': '{{order.total}}',
        'tax': '{{order.tax_total}}',
        'shipping': '{{order.delivery}}',
        'coupon': '{%if order.voucher_code %}{{order.voucher_code}}{% endif %}'
    });
{% endif %}

from __future__ import unicode_literals
from django import template
register = template.Library()

@register.filter
def get_item_after_divisible(count, divisiblybynumber):
    """
    when in a for loop we want to know if the current count is one after divisibleby filter
    for example we want to insert a new div every 5 items {% if forloop.counter|get_item_after_divisible:'4' %}<div>{% endif %}
    """
    if not isinstance(count, int):
        count = int(count)
    if not isinstance(divisiblybynumber, int):
        divisiblybynumber = int(divisiblybynumber)
    return (count - 1) % divisiblybynumber == 0


@register.filter
def number_to_range(end_range):
    """
    Create a iterable forloop for iterating a number of times.
    {% for i in 3|number_to_range %}
        Do something
    {% endfor %}
    for i in end_range:
    return range to iterate over.
    """
    if not isinstance(end_range, int):
        end_range = int(end_range)

    return range(end_range)

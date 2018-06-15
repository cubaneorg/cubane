# coding=UTF-8
# Template filters to partition lists into rows or columns.
# Originally based on template tag snippet by jacobian,
# https://djangosnippets.org/snippets/6/.
from __future__ import unicode_literals
from django.template import Library


register = Library()


@register.filter
def rows(thelist, n):
    """
    Break a list into ``n`` rows, filling up each row to the maximum equal
    length possible. For example::

        >>> l = range(10)

        >>> rows(l, 2)
        [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

        >>> rows(l, 3)
        [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]

        >>> rows(l, 4)
        [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]

        >>> rows(l, 5)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]

        >>> rows(l, 9)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [], [], [], []]

        # This filter will always return `n` rows, even if some are empty:
        >>> rows(range(2), 3)
        [[0], [1], []]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]

    if n == 0:
        return None

    list_len = len(thelist)
    split = list_len // n

    if list_len % n != 0:
        split += 1
    return [thelist[split*i:split*(i+1)] for i in range(n)]


@register.filter
def rows_distributed(thelist, n):
    """
    Break a list into ``n`` rows, distributing columns as evenly as possible
    across the rows. For example:

        >>> l = range(10)

        >>> rows_distributed(l, 2)
        [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

        >>> rows_distributed(l, 3)
        [[0, 1, 2, 3], [4, 5, 6], [7, 8, 9]]

        >>> rows_distributed(l, 4)
        [[0, 1, 2], [3, 4, 5], [6, 7], [8, 9]]

        >>> rows_distributed(l, 5)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]

        >>> rows_distributed(l, 9)
        [[0, 1], [2], [3], [4], [5], [6], [7], [8], [9]]

        # This filter will always return `n` rows, even if some are empty:
        >>> rows(range(2), 3)
        [[0], [1], []]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]

    if n == 0:
        return None

    list_len = len(thelist)
    split = list_len // n

    remainder = list_len % n
    offset = 0
    rows = []
    for i in range(n):
        if remainder:
            start, end = (split+1)*i, (split+1)*(i+1)
        else:
            start, end = split*i+offset, split*(i+1)+offset
        rows.append(thelist[start:end])
        if remainder:
            remainder -= 1
            offset += 1
    return rows


@register.filter
def columns(thelist, n):
    """
    Break a list into ``n`` columns, filling up each column to the maximum equal
    length possible. For example::

        >>> from pprint import pprint
        >>> for i in range(7, 11):
        ...     print '%sx%s:' % (i, 3)
        ...     pprint(columns(range(i), 3), width=20)
        7x3:
        [[0, 1, 2],
         [3, 4],
         [5, 6]]

        # Note that this filter does not guarantee that `n` columns will be
        # present:
        >>> pprint(columns(range(4), 3), width=10)
        [[0, 1],
         [2, 3]]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]

    if n == 0:
        return None

    list_len = len(thelist)
    split = list_len // n
    if list_len % n != 0:
        split += 1
    return [thelist[i*n:(i+1)*n] for i in range(split)]
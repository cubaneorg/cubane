# coding=UTF-8
from __future__ import unicode_literals
import re
import string


def fts_query(queryset, attr, term, alt_attr=None, all_words_must_match=True, by_rank=True):
    """
    Returns the given queryset by adding the required where-clause
    for full text searching the given (indexed) full text search attribute
    name for the given raw user search input term. Further the result set is
    ordered by postgresql's full text search ranking.
    """
    # sanitise raw search input
    sanitized_term = sanitize_search_term(term, all_words_must_match)

    # ranking
    if by_rank:
        queryset = queryset.extra(
            select={'rank': 'ts_rank_cd(' + attr + ', to_tsquery(\'pg_catalog.english\', %s))'},
            select_params=[sanitized_term]
        )

    # tsquery
    where = attr + ' @@ to_tsquery(\'pg_catalog.english\', %s)'
    params = [sanitized_term]
    if alt_attr:
        where += ' OR ' + alt_attr + ' ilike %s'
        params.append(term + '%')

    queryset = queryset.extra(
        where=[where],
        params=params
    )

    # order by rank desc.
    if by_rank:
        if alt_attr:
            queryset = queryset.order_by('-rank', alt_attr)
        else:
            queryset = queryset.order_by('-rank')

    return queryset


def sanitize_search_term(term, all_words_must_match=True):
    """
    Sanitise the raw user input search term and return
    a search query string that can be used safely for postgresql
    fulltext search.
    """
    # only allow text, numbers and some punctoation characters
    term = re.sub(r'[^-.;,\/\w\d\s]', ' ', term)

    # split into words
    words = re.split(r'\s', term)

    # trim each word
    words = [word.strip() for word in words]

    # filter out empty words
    words = [word for word in words if len(word) > 0]

    # prefix filter for each word
    words = [word + ':*' for word in words]

    # match all word filters
    if all_words_must_match:
        return ' & '.join(words)
    else:
        return ' | '.join(words)
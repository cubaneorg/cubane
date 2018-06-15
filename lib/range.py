# coding=UTF-8
from __future__ import unicode_literals
import math
import decimal


def get_ranges_for_min_max(min_max, number_of_choices, divisible_list):
    if min_max[0] is None: min_max = (0, min_max[1])
    if min_max[1] is None: min_max = (min_max[0], 0)

    chunk_size = _get_chunk_size(min_max, number_of_choices)
    sections = _get_sections_from_range(min_max[0], number_of_choices, chunk_size)
    sections = _get_normalised_sections(min_max, sections, divisible_list)

    return _get_list_of_ranges(sections)


def _get_chunk_size(min_max, number_of_sections):
    """
    Return the size of a chunk when dividing the range into given sections evenly.
    """
    return (min_max[1] - min_max[0]) / number_of_sections


def _get_sections_from_range(_min, number_of_sections, chunk_size):
    """
    Return range split into sections based on n sections with a given difference.
    """
    range_sections = [_min]
    for i in range(number_of_sections + 1):
        range_sections.append(_min + (i * chunk_size))
    return range_sections


def _get_normalised_sections(min_max, sections, divisible_list):
    """
    Return sections sorted into divisible_list.
    """
    new_sections = []
    for section in sections:
        new_section = _get_divisible_by_list(section, divisible_list)
        if new_section not in new_sections:
            new_sections.append(new_section)

    return _add_upper_lower_bound(min_max, new_sections, divisible_list)


def _get_list_of_ranges(sections):
    """
    Return a list of ranges created from the given sections.
    """
    ranges = []
    for i, option in enumerate(sections):
        if i < len(sections) - 1:
            ranges.append([option, sections[i + 1]])
    return ranges


def _get_divisible_by_list(number, divisible_list, is_upper_bound=False):
    """
    Return largest divisible number from given list.
    """
    n = 0
    for item in divisible_list:
        if is_upper_bound:
            if math.floor(item / number) > 0:
                n = item
        else:
            if math.floor(number / item) > 0:
                n = item
                break
    return n


def _add_upper_lower_bound(min_max, sections, divisible_list):
    """
    Add min or max range if not already included.
    """
    _min = min(sections)
    _max = max(sections)
    if min_max[0] < _min:
        sections.append(_get_lower_bound(min_max[0], _min, divisible_list))
    if min_max[1] > _max:
        sections.append(_get_upper_bound(min_max[1], _max, divisible_list))
    return sections


def _get_upper_bound(_max, max_sections, divisible_list):
    """
    Get upper bound for sections.
    """
    n = _max - max_sections
    return max_sections + _get_divisible_by_list(n, divisible_list, is_upper_bound=True)


def _get_lower_bound(_min, min_sections, divisible_list):
    """
    Get lower bound for sections.
    """
    n = min_sections - _min
    return min_sections - _get_divisible_by_list(n, divisible_list)

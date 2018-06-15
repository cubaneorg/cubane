# coding=UTF-8
from __future__ import unicode_literals
from django.db.models.query import QuerySet
from django.forms.models import ModelChoiceIterator
from django.utils.safestring import mark_safe
import sys


def is_any_child_of(child, parent):
    """
    Return True, if child is a child (or indirect child) of parent.
    """
    if not child or not parent:
        return False

    if not child.id or not parent.id:
        return False

    node = child
    while node:
        node = node.parent
        if node and parent and node.id == parent.id:
            return True
    return False


class TreeBuilder(object):
    LEVEL_INDENTATION = 2


    def __init__(self, id_name='id', parent_id_name='parent_id', children_name='children', level_name='level', title_name='title'):
        def _get_id(node):
            return getattr(node, id_name)

        def _get_parent_id(node):
            return getattr(node, parent_id_name, None)

        def _is_root(node):
            return _get_parent_id(node) == None

        def _set_children(node, children):
            setattr(node, children_name, children)

        def _get_children(node):
            return getattr(node, children_name)

        def _is_child_of(child, parent):
            return _get_parent_id(child) == _get_id(parent)

        def _get_level(node):
            return getattr(node, level_name)

        def _set_level(node, level):
            setattr(node, level_name, level)

        def _find_children(parent, items, level):
            return [_get_node_with_children(child, items, level) for child in items if _is_child_of(child, parent)]

        def _get_node_with_children(node, items, level=0):
            _set_children(node, _find_children(node, items, level + 1))
            _set_level(node, level)
            return node

        def _get_title(node):
            return getattr(node, title_name)

        def _get_title_with_level(node, level):
            return (' ' * self.LEVEL_INDENTATION * level) + _get_title(node)

        def _get_title_with_level_html(node, level):
            return mark_safe(('&nbsp;' * self.LEVEL_INDENTATION * level) + _get_title(node))


        self.get_id = _get_id
        self.get_parent_id = _get_parent_id
        self.is_root = _is_root
        self.set_children = _set_children
        self.is_child_of = _is_child_of
        self.get_level = _get_level
        self.set_level = _set_level
        self.get_children = _get_children
        self.find_children = _find_children
        self.get_node_with_children = _get_node_with_children
        self.get_title = _get_title
        self.get_title_with_level = _get_title_with_level
        self.get_title_with_level_html = _get_title_with_level_html


    def make_tree(self, items):
        """
        Take a list of given items and turn it into a tree by injecting a children property
        into every instance that gives a list of all children. The original order of the list
        in maintained per tree level.
        """
        if items == None:
            return []

        if isinstance(items, QuerySet):
            items = list(items)

        return [self.get_node_with_children(node, items) for node in items if self.is_root(node)]


    def make_choices(self, tree):
        """
        Take a tree and generate a list of choices in the correct order, where the title
        reflects the level of the tree node.
        """
        result = []

        def walk(node, level=0):
            result.append(
                (self.get_id(node), self.get_title_with_level_html(node, level))
            )
            for child in self.get_children(node):
                walk(child, level + 1)

        for node in tree:
            walk(node)

        return result


    def print_tree(self, tree, channel=sys.stdout, level=0):
        """
        Print the tree on the terminal
        """
        for node in tree:
            channel.write(self.get_title_with_level(node, level) + '\n')
            self.print_tree(self.get_children(node), channel, level + 1)


    def iterate(self, tree):
        """
        Iterate over the given tree.
        """
        for root in tree:
            yield root
            for child in self.iterate(self.get_children(root)):
                yield child


class TreeModelChoiceIterator(ModelChoiceIterator):
    """
    Iterates over model choices and returns choices for the given queryset that represent
    the underlying tree structure.
    """
    def __init__(self, field, queryset, id_name='id', parent_id_name='parent_id', children_name='children'):
        super(TreeModelChoiceIterator, self).__init__(field)
        self.builder = TreeBuilder(id_name, parent_id_name, children_name)
        self.queryset = queryset
        self.tree = None


    def __iter__(self):
        if self.field.empty_label is not None:
            yield ('', self.field.empty_label)

        if self.tree is None:
            self.tree = self.builder.make_tree(self.queryset)

        for node in self.builder.iterate(self.tree):
            yield self.choice(node)


    def __len__(self):
        return (
            len(self.queryset) +
            (1 if self.field.empty_label is not None else 0)
        )
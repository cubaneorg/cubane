# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.tree import is_any_child_of
from cubane.lib.tree import TreeBuilder
from cubane.lib.tree import TreeModelChoiceIterator
from cubane.media.models import MediaFolder
from cubane.backend.forms import BrowseTreeField
import StringIO


class LibTreeBaseTestCase(CubaneTestCase):
    """
    Base Test Case
    """
    def _title_with_level_html(self, title, level):
        return ('&nbsp;' * TreeBuilder.LEVEL_INDENTATION * level) + title


    def _title_with_level(self, title, level):
        return (' ' * TreeBuilder.LEVEL_INDENTATION * level) + title + '\n'



class LibTreeIsAnyChildOfTestCase(LibTreeBaseTestCase):
    """
    cubane.lib.tree.is_any_child_of()
    """
    def setUp(self):
        self.root = MediaFolder(id=1)
        self.a    = MediaFolder(id=2, parent=self.root)
        self.a1   = MediaFolder(id=3, parent=self.a)
        self.a2   = MediaFolder(id=4, parent=self.a)
        self.b    = MediaFolder(id=5, parent=self.root)
        self.c    = MediaFolder(id=6, parent=self.root)
        self.items = [self.root, self.a, self.a1, self.a2, self.b, self.c]


    def test_should_return_false_if_none(self):
        self.assertFalse(is_any_child_of(None, None))
        self.assertFalse(is_any_child_of(self.a, None))
        self.assertFalse(is_any_child_of(None, self.root))


    def test_should_return_false_if_no_id(self):
        self.assertFalse(is_any_child_of(self.a, MediaFolder()))
        self.assertFalse(is_any_child_of(MediaFolder(), self.root))


    def test_should_return_false_if_not_a_child(self):
        self.assertFalse(is_any_child_of(self.a, self.a1))
        self.assertFalse(is_any_child_of(self.a1, self.c))


    def test_should_return_true_if_direct_parent(self):
        self.assertTrue(is_any_child_of(self.a, self.root))


    def test_should_return_true_if_indirect_parent(self):
        self.assertTrue(is_any_child_of(self.a1, self.root))


class LibTreeBuilderTestCase(LibTreeBaseTestCase):
    """
    cubane.lib.tree.TreeBuilder()
    """
    def _createNode(self, title, id, parent_id):
        node = MediaFolder()
        node.id_ = id
        node.parent_id_ = parent_id
        node.title_ = title
        return node


    def setUp(self):
        self.root = self._createNode('root', 1, None)
        self.a    = self._createNode('a', 2, 1)
        self.a1   = self._createNode('a1', 3, 2)
        self.a2   = self._createNode('a2', 4, 2)
        self.b    = self._createNode('b', 5, 1)
        self.c    = self._createNode('c', 6, 1)
        self.items = [self.root, self.a, self.a1, self.a2, self.b, self.c]
        self.builder = TreeBuilder('id_', 'parent_id_', 'children_', 'level_', 'title_')
        self.tree = self.builder.make_tree(self.items)


    def test_make_tree_should_inject_children(self):
        # assert hierarchie
        self.assertEqual(self.tree, [self.root])
        self.assertEqual(self.tree[0].children_, [self.a, self.b, self.c])
        self.assertEqual(self.tree[0].children_[0].children_, [self.a1, self.a2])
        self.assertEqual(self.tree[0].children_[0].children_[0].children_, [])
        self.assertEqual(self.tree[0].children_[0].children_[1].children_, [])
        self.assertEqual(self.tree[0].children_[1].children_, [])
        self.assertEqual(self.tree[0].children_[2].children_, [])

        # assert level
        self.assertEqual(self.builder.get_level(self.root), 0)
        self.assertEqual(self.builder.get_level(self.a),    1)
        self.assertEqual(self.builder.get_level(self.a1),   2)
        self.assertEqual(self.builder.get_level(self.a2),   2)
        self.assertEqual(self.builder.get_level(self.b),    1)
        self.assertEqual(self.builder.get_level(self.c),    1)


    def test_make_tree_with_none_items_should_return_empty_list(self):
        self.assertEqual(self.builder.make_tree(None), [])


    def test_make_tree_should_materialise_queryset(self):
        self.root.save()
        self.a.save()
        builder = TreeBuilder()
        tree = builder.make_tree(MediaFolder.objects.all())
        self.assertEqual(tree, [self.root, self.a])
        [f.delete() for f in MediaFolder.objects.all()]


    def test_make_choices_should_reflect_tree(self):
        choices = self.builder.make_choices(self.tree)
        self.assertEqual(len(choices), 6)
        self.assertEqual(choices[0], (1, self._title_with_level_html('root', 0)))
        self.assertEqual(choices[1], (2, self._title_with_level_html('a',    1)))
        self.assertEqual(choices[2], (3, self._title_with_level_html('a1',   2)))
        self.assertEqual(choices[3], (4, self._title_with_level_html('a2',   2)))
        self.assertEqual(choices[4], (5, self._title_with_level_html('b',    1)))
        self.assertEqual(choices[5], (6, self._title_with_level_html('c',    1)))


    def test_print_tree(self):
        output = StringIO.StringIO()
        txt = self.builder.print_tree(self.tree, output)
        self.assertEqual(output.getvalue(), ''.join([
            self._title_with_level('root', 0),
            self._title_with_level('a',    1),
            self._title_with_level('a1',   2),
            self._title_with_level('a2',   2),
            self._title_with_level('b',    1),
            self._title_with_level('c',    1)
        ]))


    def test_iterate_over_tree(self):
        self.assertEqual([item for item in self.builder.iterate(self.tree)], self.items)


class LibTreeModelChoiceIteratorTestCase(LibTreeBaseTestCase):
    """
    cubane.lib.tree.TreeModelChoiceIterator()
    """
    def setUp(self):
        self.root = MediaFolder(id=1, title='root', parent_id=None)
        self.a    = MediaFolder(id=2, title='a',    parent_id=1)
        self.a1   = MediaFolder(id=3, title='a1',   parent_id=2)
        self.a2   = MediaFolder(id=4, title='a2',   parent_id=2)
        self.b    = MediaFolder(id=5, title='b',    parent_id=1)
        self.c    = MediaFolder(id=6, title='c',    parent_id=1)
        self.items = [self.root, self.a, self.a1, self.a2, self.b, self.c]
        [item.save() for item in self.items]


    def tearDown(self):
        [f.delete() for f in MediaFolder.objects.all()]


    def test_model_choice_iterator(self):
        field = BrowseTreeField(model=MediaFolder)
        choices = list(TreeModelChoiceIterator(field, MediaFolder.objects.all().order_by('title')))
        self.assertEqual(len(choices), 7)
        self.assertEqual(choices[0], ('', '---------'))
        self.assertEqual(choices[1], (1, self._title_with_level_html('root', 0)))
        self.assertEqual(choices[2], (2, self._title_with_level_html('a',    1)))
        self.assertEqual(choices[3], (3, self._title_with_level_html('a1',   2)))
        self.assertEqual(choices[4], (4, self._title_with_level_html('a2',   2)))
        self.assertEqual(choices[5], (5, self._title_with_level_html('b',    1)))
        self.assertEqual(choices[6], (6, self._title_with_level_html('c',    1)))
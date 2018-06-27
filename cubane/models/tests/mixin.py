# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.tree import TreeBuilder
from cubane.cms.models import Page
from cubane.models import Country
from cubane.models.mixin import NationalAddressMixin, AddressMixin, SEOMixin
from cubane.testapp.models import Category


class PageMock(SEOMixin):
    pass


class CubaneModelsSEOMixinTestCase(CubaneTestCase):
    def test_meta_title_should_return_meta_title(self):
        s = Page(_meta_title='Meta Title', title='Title')
        self.assertEqual('Meta Title', s.meta_title)


    def test_meta_title_should_return_title_if_meta_title_is_none(self):
        s = Page(_meta_title=None, title='Title')
        self.assertEqual('Title', s.meta_title)


    def test_meta_title_should_return_title_if_meta_title_is_empty(self):
        s = Page(_meta_title='', title='Title')
        self.assertEqual('Title', s.meta_title)


    def test_meta_description_should_return_meta_description_if_available(self):
        s = Page(_meta_description='Meta Description')
        self.assertEqual('Meta Description', s.meta_description)


    def test_meta_description_should_return_meta_description_based_on_excerpt_if_available(self):
        s = Page(_meta_description=None)
        s.set_slot_content('content', '<h1>Einstein:</h1><p>We cannot solve our problems with the same thinking we used when we created them.</p>')
        self.assertEqual('Einstein: We cannot solve our problems with the same thinking we used when we created them.', s.meta_description)


    def test_meta_description_should_truncate_words(self):
        s = Page(_meta_description=None)
        s.set_slot_content('content', '<h1>Einstein:</h1><p>A human being is a part of a whole, called by us _universe_, a part limited in time and space. He experiences himself, his thoughts and feelings as something separated from the rest... a kind of optical delusion of his consciousness. This delusion is a kind of prison for us, restricting us to our personal desires and to affection for a few persons nearest to us. Our task must be to free ourselves from this prison by widening our circle of compassion to embrace all living creatures and the whole of nature in its beauty.</p>')
        self.assertEqual('Einstein: A human being is a part of a whole, called by us _universe_, a part limited in time and space. He experiences himself, his thoughts and feelings as something', s.meta_description)


    def test_meta_description_should_return_empty_string_if_no_meta_description_nor_slot_content_is_available(self):
        s = PageMock(_meta_description=None)
        self.assertEqual('', s.meta_description)


    @override_settings(CMS_SLOTNAMES=['b'])
    def test_meta_description_should_be_based_on_configured_slot(self):
        s = Page(_meta_description=None)
        s.set_slot_content('b', '<h1>Einstein:</h1><p>A human being is a part of a whole, called by us _universe_, a part limited in time and space. He experiences himself, his thoughts and feelings as something separated from the rest... a kind of optical delusion of his consciousness. This delusion is a kind of prison for us, restricting us to our personal desires and to affection for a few persons nearest to us. Our task must be to free ourselves from this prison by widening our circle of compassion to embrace all living creatures and the whole of nature in its beauty.</p>')
        self.assertEqual('Einstein: A human being is a part of a whole, called by us _universe_, a part limited in time and space. He experiences himself, his thoughts and feelings as something', s.meta_description)


    @override_settings(CMS_SLOTNAMES=['c', 'b'])
    def test_meta_description_can_be_based_on_multiple_slots(self):
        s = Page(_meta_description=None)
        s.set_slot_content('c', '<h1>Foo</h1>')
        s.set_slot_content('b', '<p>Bar</p>')
        self.assertEqual('Foo Bar', s.meta_description)


    def test_meta_keywords_should_return_meta_keywords_if_available(self):
        s = Page(_meta_keywords='einstein, relativity, speed of light')
        self.assertEqual('einstein, relativity, speed of light', s.meta_keywords)


    def test_meta_keywords_should_return_empty_string_if_no_keywords_are_available_and_content_is_empty(self):
        s = Page()
        self.assertEqual('', s.meta_keywords)


    def test_meta_keywords_should_generate_meta_keywords_automatically_from_content_if_no_meta_keywords_are_available(self):
        # source: wikipedia: https://en.wikipedia.org/wiki/Albert_Einstein
        s = Page()
        s.set_slot_content('content', """
            <p><b>Albert Einstein</b> (<span class="nowrap"><span class="IPA nopopups"><a href="/wiki/Help:IPA_for_English" title="Help:IPA for English">/<span style="border-bottom:1px dotted"><span title="/ˈ/ primary stress follows">ˈ</span><span title="/aɪ/ long 'i' in 'tide'">aɪ</span><span title="'n' in 'no'">n</span><span title="'s' in 'sigh'">s</span><span title="'t' in 'tie'">t</span><span title="/aɪ/ long 'i' in 'tide'">aɪ</span><span title="'n' in 'no'">n</span></span>/</a></span></span>;<sup id="cite_ref-3" class="reference"><a href="#cite_note-3"><span>[</span>3<span>]</span></a></sup> <small>German:</small> <span title="Representation in the International Phonetic Alphabet (IPA)" class="IPA"><a href="/wiki/Help:IPA_for_German" title="Help:IPA for German">[ˈalbɛɐ̯t ˈaɪnʃtaɪn]</a></span><small class="nowrap metadata">&nbsp;(<a href="/wiki/File:Albert_Einstein_german.ogg" title="File:Albert Einstein german.ogg"><img alt="" src="//upload.wikimedia.org/wikipedia/commons/thumb/2/21/Speaker_Icon.svg/13px-Speaker_Icon.svg.png" width="13" height="13" srcset="//upload.wikimedia.org/wikipedia/commons/thumb/2/21/Speaker_Icon.svg/20px-Speaker_Icon.svg.png 1.5x, //upload.wikimedia.org/wikipedia/commons/thumb/2/21/Speaker_Icon.svg/26px-Speaker_Icon.svg.png 2x" data-file-width="500" data-file-height="500"></a> <a href="//upload.wikimedia.org/wikipedia/commons/6/6b/Albert_Einstein_german.ogg" class="internal" title="Albert Einstein german.ogg">listen</a>)</small>; 14 March 1879&nbsp;– 18 April 1955) was a German-born <a href="/wiki/Theoretical_physicist" title="Theoretical physicist" class="mw-redirect">theoretical physicist</a>. He developed the <a href="/wiki/General_theory_of_relativity" title="General theory of relativity" class="mw-redirect">general theory of relativity</a>, one of the two pillars of <a href="/wiki/Modern_physics" title="Modern physics">modern physics</a> (alongside <a href="/wiki/Quantum_mechanics" title="Quantum mechanics">quantum mechanics</a>).<sup id="cite_ref-frs_2-2" class="reference"><a href="#cite_note-frs-2"><span>[</span>2<span>]</span></a></sup><sup id="cite_ref-YangHamilton2010_4-0" class="reference"><a href="#cite_note-YangHamilton2010-4"><span>[</span>4<span>]</span></a></sup><sup class="reference" style="white-space:nowrap;">:274</sup> Einstein's work is also known for its influence on the <a href="/wiki/Philosophy_of_science" title="Philosophy of science">philosophy of science</a>.<sup id="cite_ref-5" class="reference"><a href="#cite_note-5"><span>[</span>5<span>]</span></a></sup><sup id="cite_ref-6" class="reference"><a href="#cite_note-6"><span>[</span>6<span>]</span></a></sup> Einstein is best known in popular culture for his <a href="/wiki/Mass%E2%80%93energy_equivalence" title="Mass–energy equivalence">mass–energy equivalence</a> formula <span class="nowrap"><i>E</i> = <i>mc</i><sup>2</sup></span> (which has been dubbed "the world's most famous equation").<sup id="cite_ref-7" class="reference"><a href="#cite_note-7"><span>[</span>7<span>]</span></a></sup> He received the 1921 <a href="/wiki/Nobel_Prize_in_Physics" title="Nobel Prize in Physics">Nobel Prize in Physics</a> for his "services to theoretical physics", in particular his discovery of the law of the <a href="/wiki/Photoelectric_effect" title="Photoelectric effect">photoelectric effect</a>, a pivotal step in the evolution of <a href="/wiki/Introduction_to_quantum_mechanics" title="Introduction to quantum mechanics">quantum theory</a>.<sup id="cite_ref-8" class="reference"><a href="#cite_note-8"><span>[</span>8<span>]</span></a></sup></p>
            <p>Near the beginning of his career, Einstein thought that <a href="/wiki/Newtonian_mechanics" title="Newtonian mechanics" class="mw-redirect">Newtonian mechanics</a> was no longer enough to reconcile the laws of <a href="/wiki/Classical_mechanics" title="Classical mechanics">classical mechanics</a> with the laws of the <a href="/wiki/Electromagnetic_field" title="Electromagnetic field">electromagnetic field</a>. This led to the development of his <a href="/wiki/Special_theory_of_relativity" title="Special theory of relativity" class="mw-redirect">special theory of relativity</a>. He realized, however, that the principle of relativity could also be extended to <a href="/wiki/Gravitational_fields" title="Gravitational fields" class="mw-redirect">gravitational fields</a>, and with his subsequent theory of gravitation in 1916, he published a paper on general relativity. He continued to deal with problems of <a href="/wiki/Statistical_mechanics" title="Statistical mechanics">statistical mechanics</a> and quantum theory, which led to his explanations of <a href="/wiki/Particle" title="Particle">particle</a> theory and the <a href="/wiki/Brownian_motion" title="Brownian motion">motion of molecules</a>. He also investigated the thermal properties of light which laid the foundation of the <a href="/wiki/Photon" title="Photon">photon</a> theory of light. In 1917, Einstein applied the general theory of relativity to model the large-scale structure of the <a href="/wiki/Universe" title="Universe">universe</a>.<sup id="cite_ref-Nobel_9-0" class="reference"><a href="#cite_note-Nobel-9"><span>[</span>9<span>]</span></a></sup><sup id="cite_ref-NYT-20151124_10-0" class="reference"><a href="#cite_note-NYT-20151124-10"><span>[</span>10<span>]</span></a></sup></p>
            <p>He was visiting the United States when <a href="/wiki/Adolf_Hitler" title="Adolf Hitler">Adolf Hitler</a> came to power in 1933 and, being Jewish, did not go back to Germany, where he had been a professor at the <a href="/wiki/Prussian_Academy_of_Sciences" title="Prussian Academy of Sciences">Berlin Academy of Sciences</a>. He settled in the U.S., becoming an <a href="/wiki/American_citizen" title="American citizen" class="mw-redirect">American citizen</a> in 1940.<sup id="cite_ref-BoyerDubofsky2001_11-0" class="reference"><a href="#cite_note-BoyerDubofsky2001-11"><span>[</span>11<span>]</span></a></sup> On the eve of World War II, he endorsed a <a href="/wiki/Einstein%E2%80%93Szil%C3%A1rd_letter" title="Einstein–Szilárd letter">letter to President Franklin D. Roosevelt</a> alerting him to the potential development of "extremely powerful bombs of a new type" and recommending that the U.S. begin similar research. This eventually led to what would become the <a href="/wiki/Manhattan_Project" title="Manhattan Project">Manhattan Project</a>. Einstein supported defending the Allied forces, but largely denounced the idea of using the newly discovered <a href="/wiki/Nuclear_fission" title="Nuclear fission">nuclear fission</a> as a weapon. Later, with the British philosopher <a href="/wiki/Bertrand_Russell" title="Bertrand Russell">Bertrand Russell</a>, Einstein signed the <a href="/wiki/Russell%E2%80%93Einstein_Manifesto" title="Russell–Einstein Manifesto">Russell–Einstein Manifesto</a>, which highlighted the danger of nuclear weapons. Einstein was affiliated with the <a href="/wiki/Institute_for_Advanced_Study" title="Institute for Advanced Study">Institute for Advanced Study</a> in <a href="/wiki/Princeton,_New_Jersey" title="Princeton, New Jersey">Princeton, New Jersey</a>, until his death in 1955.</p>
            <p>Einstein published <a href="/wiki/List_of_scientific_publications_by_Albert_Einstein" title="List of scientific publications by Albert Einstein">more than 300 scientific papers</a> along with over 150 non-scientific works.<sup id="cite_ref-Nobel_9-1" class="reference"><a href="#cite_note-Nobel-9"><span>[</span>9<span>]</span></a></sup><sup id="cite_ref-Paul_Arthur_Schilpp.2C_editor_1951_730.E2.80.93746_12-0" class="reference"><a href="#cite_note-Paul_Arthur_Schilpp.2C_editor_1951_730.E2.80.93746-12"><span>[</span>12<span>]</span></a></sup> On 5 December 2014, universities and archives announced the release of Einstein's papers, comprising more than 30,000 unique documents.<sup id="cite_ref-FOOTNOTEStachel2008_13-0" class="reference"><a href="#cite_note-FOOTNOTEStachel2008-13"><span>[</span>13<span>]</span></a></sup><sup id="cite_ref-NYT-20141204-DB_14-0" class="reference"><a href="#cite_note-NYT-20141204-DB-14"><span>[</span>14<span>]</span></a></sup> Einstein's intellectual achievements and originality have made the word "Einstein" synonymous with "<a href="/wiki/Genius" title="Genius">genius</a>".<sup id="cite_ref-wordnetweb.princeton.edu_15-0" class="reference"><a href="#cite_note-wordnetweb.princeton.edu-15"><span>[</span>15<span>]</span></a></sup></p>
        """)

        self.assertEqual(
            'einstein, theory, relativity, mechanics, quantum, general, physics, german, world, scientific, nuclear, russell, published, theoretical, papers, development, light, laws, endorsed, developed',
            s.meta_keywords
        )


    def test_meta_keywords_should_return_empty_string_if_no_meta_keywrods_nor_slot_content_is_available(self):
        s = PageMock(_meta_keywords=None)
        self.assertEqual('', s.meta_keywords)


    @override_settings(CMS_SLOTNAMES=['c', 'b'])
    def test_meta_keywords_should_generate_from_slot_content_as_specified(self):
        s = Page()
        s.set_slot_content('c', '<h1>Wonderful</h1>')
        s.set_slot_content('b', '<p>World</p>')
        self.assertEqual('world, wonderful', s.meta_keywords)


@CubaneTestCase.complex()
class CubaneModelsHierarchyMixinTestCase(CubaneTestCase):
    def setUp(self):
        self.c1 = Category.objects.create(title='A', slug='a', seq=1)
        self.c2 = Category.objects.create(title='A.1', slug='a1', seq=1, parent=self.c1)
        self.c3 = Category.objects.create(title='A.2', slug='a2', seq=2, parent=self.c1)
        self.c4 = Category.objects.create(title='B', slug='b', seq=2)


    def tearDown(self):
        [c.delete() for c in Category.objects.all()]


    #
    # append_before
    #
    def test_append_before_should_append_node_before_reference_node(self):
        self.c4.append_before(self.c1)
        self.assertEqual(
            ['B:1', ('A:2', ['A.1:1', 'A.2:2'])],
            self._get_categories()
        )


    def test_append_before_should_not_change_seq_if_node_order_is_already_intact(self):
        self.c1.append_before(self.c4)
        self.assertEqual(
            [('A:1', ['A.1:1', 'A.2:2']), 'B:2'],
            self._get_categories()
        )


    def test_append_before_should_ignore_if_nodes_are_the_same(self):
        self.c1.append_before(self.c1)
        self.assertEqual(
            [('A:1', ['A.1:1', 'A.2:2']), 'B:2'],
            self._get_categories()
        )


    def test_append_before_should_ignore_if_reference_is_none(self):
        self.c1.append_before(None)
        self.assertEqual(
            [('A:1', ['A.1:1', 'A.2:2']), 'B:2'],
            self._get_categories()
        )


    #
    # append_after
    #
    def test_append_after_should_append_node_after_reference_node(self):
        self.c1.append_after(self.c4)
        self.assertEqual(
            ['B:1', ('A:2', ['A.1:1', 'A.2:2'])],
            self._get_categories()
        )


    def test_append_after_should_not_change_seq_if_node_order_is_already_intact(self):
        self.c4.append_after(self.c1)
        self.assertEqual(
            [('A:1', ['A.1:1', 'A.2:2']), 'B:2'],
            self._get_categories()
        )


    def test_append_after_should_ignore_if_nodes_are_the_same(self):
        self.c1.append_after(self.c1)
        self.assertEqual(
            [('A:1', ['A.1:1', 'A.2:2']), 'B:2'],
            self._get_categories()
        )


    def test_append_after_should_ignore_if_reference_is_none(self):
        self.c1.append_after(None)
        self.assertEqual(
            [('A:1', ['A.1:1', 'A.2:2']), 'B:2'],
            self._get_categories()
        )


    #
    # append_to (different container)
    #
    def test_append_to_last_pos_should_append_to_container_at_last_position(self):
        self.c4.append_to(self.c1, 'last')
        self.assertEqual(
            [('A:1', ['A.1:1', 'A.2:2', 'B:3'])],
            self._get_categories()
        )


    def test_append_to_first_pos_should_append_to_container_at_first_position(self):
        self.c4.append_to(self.c1, 'first')
        self.assertEqual(
            [('A:1', ['B:1', 'A.1:2', 'A.2:3'])],
            self._get_categories()
        )


    def test_append_to_should_append_to_empty_container(self):
        self.c3.append_to(self.c4)
        self.assertEqual(
            [('A:1', ['A.1:1']), ('B:2', ['A.2:1'])],
            self._get_categories()
        )


    #
    # append_to (same container)
    #
    def test_append_to_last_pos_should_move_node_within_same_container_to_last_position(self):
       self.c2.append_to(self.c1, 'last')
       self.assertEqual(
           [('A:1', ['A.2:1', 'A.1:2']), 'B:2'],
           self._get_categories()
       )


    def test_append_to_first_pos_should_move_node_within_same_container_to_first_position(self):
       self.c3.append_to(self.c1, 'first')
       self.assertEqual(
           [('A:1', ['A.2:1', 'A.1:2']), 'B:2'],
           self._get_categories()
       )


    def test_append_to_last_pos_should_ignore_moving_node_within_same_container_if_already_at_last_position(self):
       self.c3.append_to(self.c1, 'last')
       self.assertEqual(
           [('A:1', ['A.1:1', 'A.2:2']), 'B:2'],
           self._get_categories()
       )


    def test_append_to_first_pos_should_ignore_moving_node_within_same_container_if_already_at_first_position(self):
       self.c2.append_to(self.c1, 'first')
       self.assertEqual(
           [('A:1', ['A.1:1', 'A.2:2']), 'B:2'],
           self._get_categories()
       )


    #
    # append_top_level()
    #
    def test_append_top_level_should_append_after_last_root_node(self):
        self.c3.append_top_level()
        self.assertEqual(
            [('A:1', ['A.1:1']), 'B:2', 'A.2:3'],
            self._get_categories()
        )


    def test_append_top_level_should_ignore_if_already_last_root_node(self):
        self.c4.append_top_level()
        self.assertEqual(
            [('A:1', ['A.1:1', 'A.2:2']), 'B:2'],
            self._get_categories()
        )


    def test_append_top_level_should_create_first_root_node(self):
        self.c1.delete()
        self.c2.delete()
        self.c3.delete()
        self.c4.delete()

        c = Category(title='A', slug='a')
        c.append_top_level()
        self.assertEqual(1, c.seq)
        self.assertIsNone(c.parent)


    #
    # has_parent()
    #
    def test_has_parent_should_return_true_if_node_has_parent_node(self):
        self.assertTrue(self.c2.has_parent())


    def test_has_parent_should_return_false_if_node_is_root_node(self):
        self.assertFalse(self.c1.has_parent())


    #
    # get_parent()
    #
    def test_get_parent_should_return_parent(self):
        self.assertEqual(self.c1, self.c2.get_parent())


    def test_get_parent_should_return_none_for_root_node(self):
        self.assertIsNone(self.c1.get_parent())


    #
    # get_children()
    #
    def test_get_children_should_return_empty_list_for_leaf_node(self):
        self.assertEqual([], self.c2.get_children())


    def test_get_children_should_return_list_of_children(self):
        self.assertEqual([self.c2, self.c3], self.c1.get_children())


    #
    # get_children_queryset()
    #
    def test_get_children_should_return_empty_list_for_leaf_node(self):
        self.assertEqual([], list(self.c2.get_children_queryset()))


    def test_get_children_should_return_list_of_children(self):
        self.assertEqual([self.c2, self.c3], list(self.c1.get_children_queryset()))


    #
    # get_children_reversed()
    #
    def test_get_children_reversed_should_return_empty_list_for_leaf_node(self):
        self.assertEqual([], self.c2.get_children_reversed())


    def test_get_children_reversed_should_return_list_of_children_in_reverse_order(self):
        self.assertEqual([self.c3, self.c2], self.c1.get_children_reversed())


    #
    # get_path()
    #
    def test_get_path_should_return_list_containing_item_for_isolated_root_node(self):
        self.assertEqual([self.c4], self.c4.get_path())


    def test_get_path_should_return_list_containing_only_items_same_or_higher_in_hierarchie_level(self):
        self.assertEqual([self.c1], self.c1.get_path())


    def test_get_path_should_return_list_containing_all_items_within_hierarchie_path_starting_with_root(self):
        self.assertEqual([self.c1, self.c2], self.c2.get_path())


    #
    # get_root()
    #
    def test_get_root_should_return_self_if_already_root_node(self):
        self.assertEqual(self.c1, self.c1.get_root())


    def test_get_root_should_return_root_node_of_child(self):
        self.assertEqual(self.c1, self.c3.get_root())


    def _get_categories(self):
        # make tree
        categories = Category.objects.all().order_by('seq')
        tree = TreeBuilder().make_tree(categories)

        def _tree_node(node):
            if node.children:
                return ('%s:%d' % (node.title, node.seq), [_tree_node(child) for (child) in node.children])
            else:
                return '%s:%d' % (node.title, node.seq)
        return [_tree_node(node) for node in tree]


class CubaneModelsNationalAddressMixinTestCase(CubaneTestCase):
    def test_has_address_should_return_true_if_all_required_address_components_are_set(self):
        a = NationalAddressMixin(address1='Oak Tree Business Park', postcode='NR13 6PZ', city='Norwich')
        self.assertTrue(a.has_address)


    def test_has_address_should_return_false_with_address1_missing(self):
        a = NationalAddressMixin(address1=None, postcode='NR13 6PZ', city='Norwich')
        self.assertFalse(a.has_address)


    def test_has_address_should_return_false_with_postcode_missing(self):
        a = NationalAddressMixin(address1='Oak Tree Business Park', postcode=None, city='Norwich')
        self.assertFalse(a.has_address)


    def test_has_address_should_return_false_with_city_missing(self):
        a = NationalAddressMixin(address1='Oak Tree Business Park', postcode='NR13 6PZ', city=None)
        self.assertFalse(a.has_address)


    def test_address_fields_should_return_address_fields_that_are_not_empty(self):
        fields = [
            ('address1', 'Unit 7'),
            ('address2', 'Oak Tree Business Park'),
            ('city', 'Norwich'),
            ('county', 'Norfolk'),
            ('postcode', 'NR13 6PZ'),
        ]

        a = NationalAddressMixin()
        c = []
        self.assertEqual(c, a.address_fields)

        for field, value in fields:
            setattr(a, field, value)
            c.append(value)
            self.assertEqual(c, a.address_fields)


    def test_address_lines_should_return_address_fields_seperated_with_br(self):
        a = NationalAddressMixin(
            address1='InnerShed Ltd.',
            address2='Oak Tree Business Park',
            postcode='NR13 6PZ',
            city='Norwich',
            county='Norfolk'
        )
        self.assertEqual('InnerShed Ltd.<br/>Oak Tree Business Park<br/>Norwich<br/>Norfolk<br/>NR13 6PZ', a.address_lines)


class CubaneModelsAddressMixinTestCase(CubaneTestCase):
    def test_address_fields_should_return_address_fields_that_are_not_empty(self):
        fields = [
            ('address1', 'Unit 7'),
            ('address2', 'Oak Tree Business Park'),
            ('city', 'Norwich'),
            ('county', 'Norfolk'),
            ('postcode', 'NR13 6PZ'),
        ]

        # GB is default value for foreign key (country)
        a = AddressMixin()
        c = ['United Kingdom']
        self.assertEqual(c, a.address_fields)

        for field, value in fields:
            setattr(a, field, value)
            c.insert(len(c) - 1, value)
            self.assertEqual(c, a.address_fields)


    def test_local_address_fields_should_return_national_address_fields(self):
        a = AddressMixin(
            address1='InnerShed Ltd.',
            address2='Oak Tree Business Park',
            postcode='NR13 6PZ',
            city='Norwich',
            county='Norfolk',
            country=Country.objects.get(iso='GB')
        )
        self.assertEqual(
            ['InnerShed Ltd.', 'Oak Tree Business Park', 'Norwich', 'NR13 6PZ'],
            a.local_address_fields
        )


    def test_short_address_fields_should_return_short_list_of_address_components(self):
        a = AddressMixin(
            address1='InnerShed Ltd.',
            address2='Oak Tree Business Park',
            postcode='NR13 6PZ',
            city='Norwich',
            county='Norfolk',
            country=Country.objects.get(iso='GB')
        )
        self.assertEqual(
            ['InnerShed Ltd.', 'Oak Tree Business Park', 'Norwich', 'Norfolk', 'NR13 6PZ'],
            a.short_address_fields
        )
# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.bad_words import BAD_WORDS
from cubane.lib.bad_words import normalise_text
from cubane.lib.bad_words import is_suspicious_username
from cubane.lib.bad_words import contains_bad_word
from cubane.lib.bad_words import get_bad_words
from cubane.lib.bad_words import is_latin


class LibBadWordsTestCase(CubaneTestCase):
    """
    cubane.lib.bad_words.BAD_WORDS
    """
    def test_should_import_bad_words(self):
        self.assertIsInstance(BAD_WORDS, list)


class LibBadWordsNormaliseTextTestCase(CubaneTestCase):
    """
    cubane.lib.bad_words.normalise_text()
    """
    def test_should_lowercase(self):
        self.assertEqual(
            normalise_text('This Text Conatins Uppercase Characters'),
            'this text conatins uppercase characters'
        )


    def test_should_remove_special_characters(self):
        self.assertEqual(
            normalise_text('This text contains @#$^&*(_)[]{}<>,./?~Special)*(&*^&$^*$&*&()) characters.'),
            'this text contains special characters'
        )


    def test_should_remove_space_between_single_character_words(self):
        self.assertEqual(
            normalise_text('This text contains one encoded bad word, f   u  c k    e   r'),
            'this text contains one encoded bad word fucker'
        )


    def test_should_remove_space_between_tweo_character_words(self):
        self.assertEqual(
            normalise_text('This text contains one encoded bad word, fu  ck  er'),
            'this text contains one encoded bad word fucker'
        )


    def test_should_remove_explanation_marks(self):
        self.assertEqual(normalise_text('bitch!!!'), 'bitch')
        self.assertEqual(normalise_text('b!tch'), 'bitch')
        self.assertEqual(normalise_text('bitch !'), 'bitch')
        self.assertEqual(normalise_text('bitch !!!'), 'bitch')
        self.assertEqual(normalise_text('b!tch!!!'), 'bitch')


    def test_should_substitute_common_letter_encodings(self):
        self.assertEqual(normalise_text('5h1t'), 'shit')
        self.assertEqual(normalise_text('b!tch'), 'bitch')
        self.assertEqual(normalise_text('b00bs', remove_numbers=False), 'boobs')


    def test_should_not_substitute_numbers(self):
        self.assertEqual(normalise_text('si.ngles542'), 'singles')


    def test_random_examples(self):
        self.assertEqual(normalise_text('f u c k e r'), 'fucker')
        self.assertEqual(normalise_text('*fuck*'), 'fuck')
        self.assertEqual(normalise_text('sun-of-a-bitch!'), 'sunofabitch')
        self.assertEqual(normalise_text('sfucks'), 'sfucks')
        self.assertEqual(normalise_text('f*ck'), 'fck')
        self.assertEqual(normalise_text('d*ck'), 'dck')
        self.assertEqual(normalise_text('c*ck'), 'cck')
        self.assertEqual(normalise_text('s3̒x'), 'sex')
        self.assertEqual(normalise_text('sooَn'), 'soon')
        self.assertEqual(normalise_text('Un̟beliٝev֮able anal puñisheͤr'), 'unbelievable anal punisher')
        self.assertEqual(normalise_text('i\'m loּoki֒ng to f@ck righ̖t now'), 'im looking to fck right now')
        self.assertEqual(normalise_text('are yͮou avͯai͟lable? se͆nd m͙e a quiͩck msg'), 'are you available send me a quick msg')
        self.assertEqual(normalise_text('A̎lrite my bab̅y'), 'alrite my baby')
        self.assertEqual(normalise_text('seͤnd me a f%ckfr̎iend'), 'send me a fuckfriend')
        self.assertEqual(normalise_text('s̻o wet right n֥ow'), 'so wet right now')
        self.assertEqual(normalise_text('T͢A֚LK Sͯ00N', remove_numbers=False), 'talk soon')
        self.assertEqual(normalise_text('f u c k dick'), 'fuck dick')
        self.assertEqual(normalise_text('Hello! I\'m Reeses.'), 'hello im reeses')


    def test_unicode_normalisation(self):
        self.assertEqual(normalise_text('yourseͩlf'), 'yourself')
        self.assertEqual(normalise_text('l̘oo͓kͩi̒ng f́o͍r a f%ckbuddy'), 'looking for a fuckbuddy')
        self.assertEqual(normalise_text('ẖaͣv̷e hot sxx'), 'have hot sxx')


class LibBadWordsContainsBadWordTestCase(CubaneTestCase):
    """
    cubane.lib.bad_words.contains_bad_word()
    """
    def test_should_return_true_if_matches_bad_word(self):
        self.assertTrue(contains_bad_word('fucker'))
        self.assertTrue(contains_bad_word('f u c k e r'))
        self.assertTrue(contains_bad_word('f u c k dick'))
        self.assertTrue(contains_bad_word('*f.u.c.k!!!dick!!!*'))
        self.assertTrue(contains_bad_word('5h1t'))
        self.assertTrue(contains_bad_word('b!tch'))
        self.assertTrue(contains_bad_word('b00bs'))
        self.assertTrue(contains_bad_word('phonesxx'))
        self.assertTrue(contains_bad_word('H0rny Sarah'))
        self.assertTrue(contains_bad_word('f*ck'))
        self.assertTrue(contains_bad_word('c*ck?'))
        self.assertTrue(contains_bad_word('fuck ri0t'))
        self.assertTrue(contains_bad_word('fucks'))
        self.assertTrue(contains_bad_word('@gi_r.ls'))
        self.assertTrue(contains_bad_word('@meet_hot_lo.cal_si.ngles542'))
        self.assertTrue(contains_bad_word('@get_3laid_toni3ght'))


    def test_should_match_against_custom_words(self):
        self.assertTrue(contains_bad_word('I need some Money!', ['money']))


    def test_should_return_false_if_no_match(self):
        self.assertFalse(contains_bad_word('In the light of recent events, we all need to stay calm.'))
        self.assertFalse(contains_bad_word('thisisafuckingword'))
        self.assertFalse(contains_bad_word('Money!'))
        self.assertFalse(contains_bad_word('show'))
        self.assertFalse(contains_bad_word('mass'))
        self.assertFalse(contains_bad_word('They\'re playing Norwich I\'m so blessed'))
        self.assertFalse(contains_bad_word('#followfriday @sarajgreenfield \u2013 friendly marketeer whose Bright Yellow Marketing provides Social Media Training,SM Mangt &amp; SM Hub Norwich.'))


    def test_should_return_false_if_none(self):
        self.assertFalse(contains_bad_word(None))


class LibBadWordsGetBadWordsTestCase(CubaneTestCase):
    """
    cubane.lib.bad_words.get_bad_words()
    """
    def test_should_return_empty_set_if_no_bad_words_are_found(self):
        self.assertEqual(set(), get_bad_words('Hello World'))


    def test_should_return_set_of_bad_words_in_text(self):
        self.assertEqual(set(['fuck']), get_bad_words('f u c k'))


class LibBadWordsIsSuspiciousUsernameTestCase(CubaneTestCase):
    """
    cubane.lib.bad_words.is_suspicious_username()
    """
    def test_suspicious_usernames(self):
        self.assertTrue(is_suspicious_username('@riot.'))
        self.assertTrue(is_suspicious_username('foo_bar_'))
        self.assertTrue(is_suspicious_username('foo.bar.'))


    def test_regular_usernames(self):
        self.assertFalse(is_suspicious_username('foo'))
        self.assertFalse(is_suspicious_username('@foo'))
        self.assertFalse(is_suspicious_username('foo79'))
        self.assertFalse(is_suspicious_username('foo_79'))


class LibBadWordsIsForeignLanguageTestCase(CubaneTestCase):
    """
    cubane.lib.bad_words.is_foreign_language()
    """
    def test_is_not_latin(self):
        self.assertFalse(is_latin('Привет мир'))
        self.assertFalse(is_latin('مرحبا بالعالم'))
        self.assertFalse(is_latin('Բարեւ աշխարհ'))
        self.assertFalse(is_latin('Прывітанне свет'))
        self.assertFalse(is_latin('ওহে বিশ্ব'))
        self.assertFalse(is_latin('Здравей Свят'))
        self.assertFalse(is_latin('မင်္ဂလာပါကမ္ဘာလောက'))
        self.assertFalse(is_latin('你好，世界'))
        self.assertFalse(is_latin('你好，世界'))
        self.assertFalse(is_latin('Γειά σου Κόσμε'))
        self.assertFalse(is_latin('હેલો વર્લ્ડ'))
        self.assertFalse(is_latin('שלום עולם'))
        self.assertFalse(is_latin('हैलो वर्ल्ड'))
        self.assertFalse(is_latin('こんにちは世界'))
        self.assertFalse(is_latin('Сәлем Әлем'))
        self.assertFalse(is_latin('ជំរាបសួរ ពិភពលោក'))
        self.assertFalse(is_latin('안녕하세요'))
        self.assertFalse(is_latin('ສະ​ບາຍ​ດີ​ຊາວ​ໂລກ'))
        self.assertFalse(is_latin('Здраво свету'))
        self.assertFalse(is_latin('ഹലോ വേൾഡ്'))
        self.assertFalse(is_latin('हॅलो वर्ल्ड'))
        self.assertFalse(is_latin('Сайн байна уу , Дэлхийн'))
        self.assertFalse(is_latin('नमस्कार संसार'))
        self.assertFalse(is_latin('سلام دنیا'))
        self.assertFalse(is_latin('ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ ਦੁਨਿਆ'))
        self.assertFalse(is_latin('Привет мир'))
        self.assertFalse(is_latin('Здраво Свете'))
        self.assertFalse(is_latin('හෙලෝ වර්ල්ඩ්'))
        self.assertFalse(is_latin('Салом Ҷаҳон'))
        self.assertFalse(is_latin('ஹலோ உலகம்'))
        self.assertFalse(is_latin('హలో వరల్డ్'))
        self.assertFalse(is_latin('สวัสดีชาวโลก'))
        self.assertFalse(is_latin('Привіт Світ'))
        self.assertFalse(is_latin('ہیلو دنیا والو'))
        self.assertFalse(is_latin('העלא וועלט'))


    def test_is_latin(self):
        self.assertTrue(is_latin('Hello World'))
        self.assertTrue(is_latin('Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis eget ipsum justo. Maecenas pretium nisl ipsum, a venenatis lorem facilisis egestas.'))
        self.assertTrue(is_latin('Norfolk is a county that packs into it all that is British, with a diverse mix of heritage, history, culture and outdoor activities the county boasts a wealth of locations ideal for relaxing retreats and inspiring weekend breaks and escapes.'))


    def test_is_latin_with_emoicons(self):
        self.assertTrue(is_latin('Started now on thrle Road BJ ❤🎸💙💼💃'))
        self.assertTrue(is_latin('Just your average night 🍻'))
        self.assertTrue(is_latin('I just loves to sleep 😊😴'))
        self.assertTrue(is_latin('Autumn ❤🍁🍂🍃'))
        self.assertTrue(is_latin('Hoppy! 😊'))
        self.assertTrue(is_latin('#porridge with a variety of toppings available all day ☕️🍌💛'))


    def test_should_return_true_for_empty_or_none(self):
        self.assertTrue(is_latin(''))
        self.assertTrue(is_latin(None))
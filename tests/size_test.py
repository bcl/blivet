# pylint: disable=environment-modify
#
# tests/storage/size_tests.py
# Size test cases for the blivet module
#
# Copyright (C) 2010  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): David Cantrell <dcantrell@redhat.com>

# we need integer division to work the same with both Python 2 and 3
from __future__ import division

import locale
import os
import unittest

from six.moves import cPickle # pylint: disable=import-error

from decimal import Decimal

from blivet.i18n import _
from blivet.errors import SizePlacesError
from blivet import size
from blivet.size import Size, _EMPTY_PREFIX, _BINARY_PREFIXES, _DECIMAL_PREFIXES
from blivet.size import B, KiB, MiB, GiB, TiB

class SizeTestCase(unittest.TestCase):

    def testExceptions(self):
        zero = Size(0)
        self.assertEqual(zero, Size("0.0"))

        s = Size(500)
        with self.assertRaises(SizePlacesError):
            s.humanReadable(max_places=-1)

        self.assertEqual(s.humanReadable(max_places=0), "500 B")

    def _prefixTestHelper(self, numunits, unit):
        """ Test that units and prefix or abbreviation agree.

            :param int numunits: this value times factor yields number of bytes
            :param unit: a unit specifier
        """
        c = numunits * unit.factor

        s = Size(c)
        self.assertEqual(s, Size(c))

        u = size._makeSpec(unit.prefix, size._BYTES_WORDS[0], False)
        s = Size("%ld %s" % (numunits, u))
        self.assertEqual(s, c)
        self.assertEqual(s.convertTo(unit), numunits)

        u = size._makeSpec(unit.abbr, size._BYTES_SYMBOL, False)
        s = Size("%ld %s" % (numunits, u))
        self.assertEqual(s, c)
        self.assertEqual(s.convertTo(unit), numunits)

    def testPrefixes(self):
        numbytes = 47

        for unit in [_EMPTY_PREFIX] + _BINARY_PREFIXES + _DECIMAL_PREFIXES:
            self._prefixTestHelper(numbytes, unit)

    def testHumanReadable(self):
        s = Size(58929971)
        self.assertEqual(s.humanReadable(), "56.2 MiB")

        s = Size(478360371)
        self.assertEqual(s.humanReadable(), "456.2 MiB")

        # humanReable output should be the same as input for big enough sizes
        # and enough places and integer values
        s = Size("12.68 TiB")
        self.assertEqual(s.humanReadable(max_places=2), "12.68 TiB")
        s = Size("26.55 MiB")
        self.assertEqual(s.humanReadable(max_places=2), "26.55 MiB")
        s = Size("300 MiB")
        self.assertEqual(s.humanReadable(max_places=2), "300 MiB")

        # when min_value is 10 and single digit on left of decimal, display
        # with smaller unit.
        s = Size("9.68 TiB")
        self.assertEqual(s.humanReadable(max_places=2, min_value=10), "9912.32 GiB")
        s = Size("4.29 MiB")
        self.assertEqual(s.humanReadable(max_places=2, min_value=10), "4392.96 KiB")
        s = Size("7.18 KiB")
        self.assertEqual(s.humanReadable(max_places=2, min_value=10), "7352 B")

        # rounding should work with max_places limitted
        s = Size("12.687 TiB")
        self.assertEqual(s.humanReadable(max_places=2), "12.69 TiB")
        s = Size("23.7874 TiB")
        self.assertEqual(s.humanReadable(max_places=3), "23.787 TiB")
        s = Size("12.6998 TiB")
        self.assertEqual(s.humanReadable(max_places=2), "12.7 TiB")

        # byte values close to multiples of 2 are shown without trailing zeros
        s = Size(0xff)
        self.assertEqual(s.humanReadable(max_places=2), "255 B")
        s = Size(8193)
        self.assertEqual(s.humanReadable(max_places=2, min_value=10), "8193 B")

        # a fractional quantity is shown if the value deviates
        # from the whole number of units by more than 1%
        s = Size(16384 - (1024/100 + 1))
        self.assertEqual(s.humanReadable(max_places=2), "15.99 KiB")

        # if max_places is set to None, all digits are displayed
        s = Size(0xfffffffffffff)
        self.assertEqual(s.humanReadable(max_places=None), "3.9999999999999991118215803 PiB")
        s = Size(0x10000)
        self.assertEqual(s.humanReadable(max_places=None), "64 KiB")
        s = Size(0x10001)
        self.assertEqual(s.humanReadable(max_places=None), "64.0009765625 KiB")

        # test a very large quantity with no associated abbreviation or prefix
        s = Size(1024**9)
        self.assertEqual(s.humanReadable(max_places=2), "1024 YiB")
        s = Size(1024**9 - 1)
        self.assertEqual(s.humanReadable(max_places=2), "1024 YiB")
        s = Size(1024**9 + 1)
        self.assertEqual(s.humanReadable(max_places=2, strip=False), "1024.00 YiB")
        s = Size(1024**10)
        self.assertEqual(s.humanReadable(max_places=2), "1048576 YiB")

    def testHumanReadableFractionalQuantities(self):
        s = Size(0xfffffffffffff)
        self.assertEqual(s.humanReadable(max_places=2), "4 PiB")
        s = Size(0xfffff)
        self.assertEqual(s.humanReadable(max_places=2, strip=False), "1024.00 KiB")
        s = Size(0xffff)
        # value is not exactly 64 KiB, but w/ 2 places, value is 64.00 KiB
        # so the trailing 0s are stripped.
        self.assertEqual(s.humanReadable(max_places=2), "64 KiB")
        # since all significant digits are shown, there are no trailing 0s.
        self.assertEqual(s.humanReadable(max_places=None), "63.9990234375 KiB")

        # deviation is less than 1/2 of 1% of 1024
        s = Size(16384 - (1024/100//2))
        self.assertEqual(s.humanReadable(max_places=2), "16 KiB")
        # deviation is greater than 1/2 of 1% of 1024
        s = Size(16384 - ((1024/100//2) + 1))
        self.assertEqual(s.humanReadable(max_places=2), "15.99 KiB")

        s = Size(0x10000000000000)
        self.assertEqual(s.humanReadable(max_places=2), "4 PiB")


    def testMinValue(self):
        s = Size("9 MiB")
        self.assertEqual(s.humanReadable(), "9 MiB")
        self.assertEqual(s.humanReadable(min_value=10), "9216 KiB")

        s = Size("0.5 GiB")
        self.assertEqual(s.humanReadable(max_places=2, min_value=1), "512 MiB")
        self.assertEqual(s.humanReadable(max_places=2, min_value=Decimal("0.1")), "0.5 GiB")
        self.assertEqual(s.humanReadable(max_places=2, min_value=Decimal(1)), "512 MiB")

    def testConvertToPrecision(self):
        s = Size(1835008)
        self.assertEqual(s.convertTo(None), 1835008)
        self.assertEqual(s.convertTo(B), 1835008)
        self.assertEqual(s.convertTo(KiB), 1792)
        self.assertEqual(s.convertTo(MiB), Decimal("1.75"))

    def testNegative(self):
        s = Size("-500MiB")
        self.assertEqual(s.humanReadable(), "-500 MiB")
        self.assertEqual(s.convertTo(B), -524288000)

    def testPartialBytes(self):
        self.assertEqual(Size("1024.6"), Size(1024))
        self.assertEqual(Size("%s KiB" % (1/1025.0,)), Size(0))
        self.assertEqual(Size("%s KiB" % (1/1023.0,)), Size(1))

    def testNoUnitsInString(self):
        self.assertEqual(Size("1024"), Size("1 KiB"))

    def testScientificNotation(self):
        self.assertEqual(size.parseSpec("1e+0 KiB"), Decimal(1024))
        self.assertEqual(size.parseSpec("1e-0 KiB"), Decimal(1024))
        self.assertEqual(size.parseSpec("1e-1 KB"), Decimal(100))
        self.assertEqual(size.parseSpec("1E-4KB"), Decimal("0.1"))
        self.assertEqual(Size("1E-10KB"), Size(0))

        with self.assertRaises(ValueError):
            # this is an exponent w/out a base
            size.parseSpec("e+0")

    def testFloatingPointStr(self):
        self.assertEqual(size.parseSpec("1.5e+0 KiB"), Decimal(1536))
        self.assertEqual(size.parseSpec("0.0"), Decimal(0))
        self.assertEqual(size.parseSpec("0.9 KiB"), Decimal("921.6"))
        self.assertEqual(size.parseSpec("1.5 KiB"), Decimal(1536))
        self.assertEqual(size.parseSpec("0.5 KiB"), Decimal(512))
        self.assertEqual(size.parseSpec(".5 KiB"), Decimal(512))
        self.assertEqual(size.parseSpec("1. KiB"), Decimal(1024))
        self.assertEqual(size.parseSpec("-1. KiB"), Decimal(-1024))
        self.assertEqual(size.parseSpec("+1. KiB"), Decimal(1024))
        self.assertEqual(size.parseSpec("+1.0000000e+0 KiB"), Decimal(1024))
        self.assertEqual(size.parseSpec("+.5 KiB"), Decimal(512))

        with self.assertRaises(ValueError):
            # this is a fragment of an arithmetic expression
            size.parseSpec("+ 1 KiB")

        with self.assertRaises(ValueError):
            # this is a fragment of an arithmetic expression
            size.parseSpec("- 1 KiB")

        with self.assertRaises(ValueError):
            # this is a lonely .
            size.parseSpec(". KiB")

        with self.assertRaises(ValueError):
            # this has a fragmentary exponent
            size.parseSpec("1.0e+ KiB")

        with self.assertRaises(ValueError):
            # this is a version string, not a number
            size.parseSpec("1.0.0")

    def testWhiteSpace(self):
        self.assertEqual(size.parseSpec("1 KiB "), Decimal(1024))
        self.assertEqual(size.parseSpec(" 1 KiB"), Decimal(1024))
        self.assertEqual(size.parseSpec(" 1KiB"), Decimal(1024))
        self.assertEqual(size.parseSpec(" 1e+0KiB"), Decimal(1024))
        with self.assertRaises(ValueError):
            size.parseSpec("1 KiB just a lot of stray characters")
        with self.assertRaises(ValueError):
            size.parseSpec("just 1 KiB")

    def testLeadingZero(self):
        self.assertEqual(size.parseSpec("001 KiB"), Decimal(1024))
        self.assertEqual(size.parseSpec("1e+01"), Decimal(10))

    def testPickling(self):
        s = Size("10 MiB")
        self.assertEqual(s, cPickle.loads(cPickle.dumps(s)))

class TranslationTestCase(unittest.TestCase):

    def __init__(self, methodName='runTest'):
        super(TranslationTestCase, self).__init__(methodName=methodName)

        # es_ES uses latin-characters but a comma as the radix separator
        # kk_KZ uses non-latin characters and is case-sensitive
        # ml_IN uses a lot of non-letter modifier characters
        # fa_IR uses non-ascii digits, or would if python supported that, but
        #       you know, just in case
        self.TEST_LANGS = ["es_ES.UTF-8", "kk_KZ.UTF-8", "ml_IN.UTF-8", "fa_IR.UTF-8"]

    def setUp(self):
        self.saved_lang = os.environ.get('LANG', None)

    def tearDown(self):
        os.environ['LANG'] = self.saved_lang
        locale.setlocale(locale.LC_ALL, '')

    def testMakeSpec(self):
        """ Tests for _makeSpecs(). """
        for lang in  self.TEST_LANGS:
            os.environ['LANG'] = lang
            locale.setlocale(locale.LC_ALL, '')

            # untranslated specs
            self.assertEqual(size._makeSpec("", "BYTES", False), "bytes")
            self.assertEqual(size._makeSpec("Mi", "b", False), "mib")

            # un-lower-cased specs
            self.assertEqual(size._makeSpec("", "BYTES", False, False), "BYTES")
            self.assertEqual(size._makeSpec("Mi", "b", False, False), "Mib")
            self.assertEqual(size._makeSpec("Mi", "B", False, False), "MiB")

            # translated specs
            res = size._makeSpec("", "bytes", True)

            # Note that exp != _("bytes").lower() as one might expect
            exp = (_("") + _("bytes")).lower()
            self.assertEqual(res, exp)

    def testParseSpec(self):
        """ Tests for parseSpec(). """
        for lang in  self.TEST_LANGS:
            os.environ['LANG'] = lang
            locale.setlocale(locale.LC_ALL, '')

            # Test parsing English spec in foreign locales
            self.assertEqual(size.parseSpec("1 kibibytes"), Decimal(1024))
            self.assertEqual(size.parseSpec("2 kibibyte"), Decimal(2048))
            self.assertEqual(size.parseSpec("2 kilobyte"), Decimal(2000))
            self.assertEqual(size.parseSpec("2 kilobytes"), Decimal(2000))
            self.assertEqual(size.parseSpec("2 KB"), Decimal(2000))
            self.assertEqual(size.parseSpec("2 K"), Decimal(2048))
            self.assertEqual(size.parseSpec("2 k"), Decimal(2048))
            self.assertEqual(size.parseSpec("2 Ki"), Decimal(2048))
            self.assertEqual(size.parseSpec("2 g"), Decimal(2 * 1024 ** 3))
            self.assertEqual(size.parseSpec("2 G"), Decimal(2 * 1024 ** 3))

            # Test parsing foreign spec
            self.assertEqual(size.parseSpec("1 %s%s" % (_("kibi"), _("bytes"))), Decimal(1024))

            # Can't parse a valueless number
            with self.assertRaises(ValueError):
                size.parseSpec("Ki")

            self.assertEqual(size.parseSpec("2 %s" % _("K")), Decimal(2048))
            self.assertEqual(size.parseSpec("2 %s" % _("Ki")), Decimal(2048))
            self.assertEqual(size.parseSpec("2 %s" % _("g")), Decimal(2 * 1024 ** 3))
            self.assertEqual(size.parseSpec("2 %s" % _("G")), Decimal(2 * 1024 ** 3))

    def testTranslated(self):
        s = Size("56.19 MiB")
        for lang in  self.TEST_LANGS:
            os.environ['LANG'] = lang
            locale.setlocale(locale.LC_ALL, '')

            # Check English parsing
            self.assertEqual(s, Size("56.19 MiB"))

            # Check native parsing
            self.assertEqual(s, Size("56.19 %s%s" % (_("Mi"), _("B"))))

            # Check native parsing, all lowercase
            self.assertEqual(s, Size(("56.19 %s%s" % (_("Mi"), _("B"))).lower()))

            # Check native parsing, all uppercase
            self.assertEqual(s, Size(("56.19 %s%s" % (_("Mi"), _("B"))).upper()))

            # If the radix separator is not a period, repeat the tests with the
            # native separator
            radix = locale.nl_langinfo(locale.RADIXCHAR)
            if radix != '.':
                self.assertEqual(s, Size("56%s19 MiB" % radix))
                self.assertEqual(s, Size("56%s19 %s%s" % (radix, _("Mi"), _("B"))))
                self.assertEqual(s, Size(("56%s19 %s%s" % (radix, _("Mi"), _("B"))).lower()))
                self.assertEqual(s, Size(("56%s19 %s%s" % (radix, _("Mi"), _("B"))).upper()))

    def testHumanReadableTranslation(self):
        s = Size("56.19 MiB")
        size_str = s.humanReadable()
        for lang in self.TEST_LANGS:

            os.environ['LANG'] = lang
            locale.setlocale(locale.LC_ALL, '')
            self.assertTrue(s.humanReadable().endswith("%s%s" % (_("Mi"), _("B"))))
            self.assertEqual(s.humanReadable(xlate=False), size_str)

    def testRoundToNearest(self):
        self.assertEqual(size.ROUND_DEFAULT, size.ROUND_HALF_UP)

        s = Size("10.3 GiB")
        self.assertEqual(s.roundToNearest(GiB), Size("10 GiB"))
        self.assertEqual(s.roundToNearest(GiB, rounding=size.ROUND_DEFAULT),
                         Size("10 GiB"))
        self.assertEqual(s.roundToNearest(GiB, rounding=size.ROUND_DOWN),
                         Size("10 GiB"))
        self.assertEqual(s.roundToNearest(GiB, rounding=size.ROUND_UP),
                         Size("11 GiB"))
        # >>> Size("10.3 GiB").convertTo(MiB)
        # Decimal('10547.19999980926513671875')
        self.assertEqual(s.roundToNearest(MiB), Size("10547 MiB"))
        self.assertEqual(s.roundToNearest(MiB, rounding=size.ROUND_UP),
                         Size("10548 MiB"))
        self.assertIsInstance(s.roundToNearest(MiB), Size)
        with self.assertRaises(ValueError):
            s.roundToNearest(MiB, rounding='abc')

        # arbitrary decimal rounding constants are not allowed
        from decimal import ROUND_HALF_DOWN
        with self.assertRaises(ValueError):
            s.roundToNearest(MiB, rounding=ROUND_HALF_DOWN)

        s = Size("10.51 GiB")
        self.assertEqual(s.roundToNearest(GiB), Size("11 GiB"))
        self.assertEqual(s.roundToNearest(GiB, rounding=size.ROUND_DEFAULT),
                         Size("11 GiB"))
        self.assertEqual(s.roundToNearest(GiB, rounding=size.ROUND_DOWN),
                         Size("10 GiB"))
        self.assertEqual(s.roundToNearest(GiB, rounding=size.ROUND_UP),
                         Size("11 GiB"))

        s = Size("513 GiB")
        self.assertEqual(s.roundToNearest(GiB), s)
        self.assertEqual(s.roundToNearest(TiB), Size("1 TiB"))
        self.assertEqual(s.roundToNearest(TiB, rounding=size.ROUND_DOWN),
                         Size(0))

        # test Size parameters
        self.assertEqual(s.roundToNearest(Size("128 GiB")), Size("512 GiB"))
        self.assertEqual(s.roundToNearest(Size("1 KiB")), Size("513 GiB"))
        self.assertEqual(s.roundToNearest(Size("1 TiB")), Size("1 TiB"))
        self.assertEqual(s.roundToNearest(Size("1 TiB"), rounding=size.ROUND_DOWN), Size(0))
        self.assertEqual(s.roundToNearest(Size(0)), Size(0))
        self.assertEqual(s.roundToNearest(Size("13 GiB")), Size("507 GiB"))

        with self.assertRaises(ValueError):
            s.roundToNearest(Size("-1 B"))

class UtilityMethodsTestCase(unittest.TestCase):

    def testLowerASCII(self):
        """ Tests for _lowerASCII. """
        self.assertEqual(size._lowerASCII(""), "")
        self.assertEqual(size._lowerASCII("B"), "b")

    def testArithmetic(self):
        s = Size("2GiB")

        # Make sure arithmatic operations with Size always result in the expected type
        self.assertIsInstance(s+s, Size)
        self.assertIsInstance(s-s, Size)
        self.assertIsInstance(s*s, Size)
        self.assertIsInstance(s/s, Size)
        self.assertIsInstance(s**Size(2), Decimal)
        self.assertIsInstance(s % Size(7), Size)


        # Make sure operations with non-Size on the right result in the expected type
        self.assertIsInstance(s+2, Size)
        self.assertIsInstance(s-2, Size)
        self.assertIsInstance(s*2, Size)
        self.assertIsInstance(s/2, Size)
        self.assertIsInstance(s//2, Size)
        self.assertIsInstance(s**2, Decimal)
        self.assertIsInstance(s % 127, Size)

        # Make sure operations with non-Size on the left result in the expected type
        self.assertIsInstance(2+s, Size)
        self.assertIsInstance(2-s, Decimal)
        self.assertIsInstance(2*s, Size)
        self.assertIsInstance(2/s, Decimal)
        self.assertIsInstance(2**Size(2), Decimal)
        self.assertIsInstance(1024 % Size(127), Decimal)

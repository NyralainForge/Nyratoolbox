import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import number


class NumberTests(unittest.TestCase):
    def run_cli(self, *args):
        output = io.StringIO()
        with patch('sys.argv', ['number.py', *args]), contextlib.redirect_stdout(output):
            number.main()
        return output.getvalue().strip()

    def test_length_argument(self):
        for length in (1, 7, 10, 11):
            self.assertRegex(self.run_cli(str(length)), rf'^[1-9][0-9]{{{length - 1}}}$')

    def test_invalid_length(self):
        for length in ('0', '-1', 'abc', '1.5'):
            with self.assertRaises(ValueError):
                self.run_cli(length)

    def test_suffixes(self):
        self.assertRegex(self.run_cli('10', '-m', '163.com'), r'^[1-9][0-9]{9}@163.com$')
        self.assertRegex(self.run_cli('10', '-m'), r'^[1-9][0-9]{9}@(139|163|162)\.com$')

    def test_dictionary_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            for extension, content in (
                ('csv', 'number,region\n1380013,北京\n13900139000,上海\n'),
                ('tsv', 'number\tregion\n1380013\t北京\n13900139000\t上海\n'),
                ('txt', '# comment\n1380013;13900139000\n// comment\n'),
            ):
                path = Path(tmp) / ('numbers.' + extension)
                path.write_text(content, encoding='utf-8-sig')
                self.assertEqual(number.load_dict_file(str(path)), ['1380013', '13900139000'])
        self.assertRegex(number.generate_normal_email(['1380013']), r'^1380013[0-9]{4}$')
        self.assertEqual(number.generate_normal_email(['13900139000']), '13900139000')

    def test_file_output_and_deduplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'out.txt'
            self.run_cli('1', '-n', '9', '-o', str(path))
            self.assertEqual(path.read_text().splitlines(), list('123456789'))

    def test_capacity_limits(self):
        with self.assertRaises(ValueError):
            self.run_cli('1', '-n', '10')
        with self.assertRaises(ValueError):
            self.run_cli('-q', '1', '-n', '10')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'numbers.txt'
            path.write_text('13800138000\n13800138000\n')
            with self.assertRaises(ValueError):
                self.run_cli('-dict', str(path), '-n', '2')
            path.write_text('1\n')
            with self.assertRaises(ValueError):
                self.run_cli('-dict', str(path), '-q', '1', '-m', 'qq.com', '-n', '10')

    def test_qq_modes(self):
        self.assertRegex(self.run_cli('-q'), r'^[1-9][0-9]{8,10}@qq\.com$')
        self.assertRegex(self.run_cli('-q', '10'), r'^[1-9][0-9]{9}@qq\.com$')
        self.assertRegex(self.run_cli('-qn'), r'^[1-9][0-9]{6,10}@qq\.com$')


if __name__ == '__main__':
    unittest.main()

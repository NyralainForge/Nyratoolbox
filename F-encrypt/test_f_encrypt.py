import base64
import contextlib
import importlib.util
import io
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("F-encrypt.py")
spec = importlib.util.spec_from_file_location("f_encrypt", SCRIPT)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class FormatTests(unittest.TestCase):
    def test_roundtrip_and_wrong_password(self):
        for sutra in (False, True):
            for ecc in (False, True):
                for data in (b"", b"\xef\xbb\xbf\r\n\x00\xff\xfe\n", bytes(range(256))):
                    with self.subTest(sutra=sutra, ecc=ecc, size=len(data)):
                        text = app.encrypt(data, "password", ecc, sutra)
                        self.assertEqual(text.startswith(app.PREFIX), sutra)
                        self.assertEqual(app.decrypt(text, "password"), data)
                        if not sutra:
                            self.assertTrue(text.isascii())
                            if not ecc:
                                self.assertEqual(len(base64.urlsafe_b64decode(
                                    text + "=" * (-len(text) % 4))), len(data) + 44)
                        with self.assertRaises((ValueError, app.InvalidTag)):
                            app.decrypt(text, "wrong")

    def test_all_single_symbol_errors(self):
        for alphabet, ecc_alphabet in (
            (app.ALPHABET, app.ECC_ALPHABET),
            (app.BASE64_ALPHABET, app.BASE64_ECC_ALPHABET),
        ):
            for length in (1, 2, 63, 64):
                values = [i % len(alphabet) for i in range(length)]
                block = app.encode_ecc_block(values, ecc_alphabet)
                expected = "".join(alphabet[i] for i in values)
                for position in range(len(block)):
                    for replacement in ecc_alphabet + "?":
                        damaged = block[:position] + replacement + block[position + 1:]
                        self.assertEqual(
                            app.decode_ecc_block(damaged, alphabet, ecc_alphabet), expected)

    def test_damaged_ciphertext(self):
        data = bytes(range(256))
        for sutra in (False, True):
            text = app.encrypt(data, "password", True, sutra)
            start = len(app.PREFIX) if sutra else 0
            damaged = list(text)
            for position in range(start, len(text), app.ECC_DATA_SYMBOLS + 2):
                damaged[position] = "?"
            self.assertEqual(app.decrypt("".join(damaged), "password"), data)
            # Two distinct erasures in one block exceed the supported capacity.
            damaged[start + 1] = "?"
            with self.assertRaises((ValueError, app.InvalidTag)):
                app.decrypt("".join(damaged), "password")

    def test_cli_files_and_literal_text(self):
        def run(argv):
            with patch.object(sys, "argv", [str(SCRIPT), *argv]), patch(
                "getpass.getpass", return_value="password"
            ), contextlib.redirect_stdout(io.StringIO()) as output:
                runpy.run_path(str(SCRIPT), run_name="__main__")
                return output.getvalue()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.conf"
            cipher = root / "cipher.txt"
            restored = root / "restored.conf"
            original = b"\xef\xbb\xbfkey=value\r\n\x00\xff\xfe\n"
            source.write_bytes(original)
            for sutra in (False, True):
                for ecc in (False, True):
                    flags = (["-sutra"] if sutra else []) + (["-ecc"] if ecc else [])
                    self.assertEqual(run(["-encrypt", str(source), *flags,
                                          "-o", str(cipher)]), "")
                    self.assertEqual(run(["-decrypt", str(cipher),
                                          "-o", str(restored)]), "")
                    self.assertEqual(restored.read_bytes(), original)
            args = app.parse_args(["-decrypt", "--", "-abc"])
            self.assertEqual(args.text, "-abc")
            self.assertIsNone(args.input_path)
            self.assertFalse(app.parse_args(["hello"]).sutra)
            self.assertEqual(app.resolve_output_path(None, True), app.DEFAULT_FILE_OUTPUT)


if __name__ == "__main__":
    unittest.main()

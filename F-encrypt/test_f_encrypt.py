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


class DirectoryTests(unittest.TestCase):
    def test_directory_requires_flag_and_valid_delete_input(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                app.parse_args(["-encrypt", directory])
            for argv in (["-delete-source", "hello"],
                         ["-decrypt", "-recursive", directory],
                         ["-recursive", "hello"],
                         ["-delete-source", "-decrypt", "--", "hello"]):
                with self.assertRaises(ValueError):
                    app.parse_args(argv)

    def test_recursive_cli_and_binary_recovery(self):
        for sutra in (False, True):
            for delete in (False, True):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    source = root / "input"
                    (source / "nested").mkdir(parents=True)
                    files = {"a.conf": b"\xef\xbb\xbf\r\n\x00\xff",
                             "nested/a.conf": bytes(range(256)), "no_extension": b""}
                    for relative, data in files.items():
                        (source / relative).write_bytes(data)
                    output = root / "output"
                    argv = [str(SCRIPT), "-encrypt", "-recursive", str(source),
                            "-ecc", "-o", str(output)]
                    if sutra:
                        argv.append("-sutra")
                    if delete:
                        argv.append("-delete-source")
                    with patch.object(sys, "argv", argv), patch(
                        "getpass.getpass", return_value="password"
                    ) as password, contextlib.redirect_stdout(io.StringIO()):
                        runpy.run_path(str(SCRIPT), run_name="__main__")
                    password.assert_called_once()
                    for relative, data in files.items():
                        cipher = output / (relative + ".encrypted.txt")
                        self.assertEqual(app.decrypt(cipher.read_text(), "password"), data)
                        self.assertEqual((source / relative).exists(), not delete)

    def test_output_guards_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input"
            source.mkdir()
            file = source / "a.txt"
            file.write_bytes(b"keep")
            (source / "link.txt").symlink_to(file)
            (source / "loop").symlink_to(source, target_is_directory=True)
            output = root / "output"
            self.assertEqual(len(app.directory_jobs(source, output)), 1)
            for destination in (source, source / "child"):
                with self.assertRaises(ValueError):
                    app.directory_jobs(source, destination)
            output.mkdir()
            (output / "a.txt.encrypted.txt").write_bytes(b"existing")
            with self.assertRaises(ValueError):
                app.directory_jobs(source, output)
            args = app.parse_args(["-encrypt", str(file), "-delete-source"])
            for target in (file, output / "a.txt.encrypted.txt"):
                with self.assertRaises((ValueError, OSError)):
                    app.encrypt_file(file, target, "password", args)
            self.assertEqual(file.read_bytes(), b"keep")

    def test_default_in_place_recursive_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "nested").mkdir()
            original = source / "nested" / "settings.ini"
            original.write_bytes(b"\xef\xbb\xbfkey=value\r\n")
            existing = source / "previous.encrypted.txt"
            existing.write_bytes(b"leave unchanged")
            argv = [str(SCRIPT), "-encrypt", str(source), "-recursive", "-delete-source"]
            with patch.object(sys, "argv", argv), patch(
                "getpass.getpass", return_value="password"
            ), contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(SCRIPT), run_name="__main__")
            self.assertFalse(original.exists())
            cipher = original.with_name(original.name + ".encrypted.txt")
            self.assertEqual(app.decrypt(cipher.read_text(), "password"),
                             b"\xef\xbb\xbfkey=value\r\n")
            self.assertEqual(existing.read_bytes(), b"leave unchanged")
            self.assertEqual(app.directory_jobs(source, source, in_place=True), [])
            # A conflicting sibling must stop the batch before deleting its source.
            original.write_bytes(b"keep")
            with self.assertRaises(ValueError):
                app.directory_jobs(source, source, in_place=True)
            self.assertEqual(original.read_bytes(), b"keep")

    def test_failures_preserve_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "a.txt"
            source.write_bytes(b"keep")
            args = app.parse_args(["-encrypt", str(source), "-delete-source"])
            with patch.object(app.os, "fsync", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    app.encrypt_file(source, root / "failed.txt", "password", args)
            self.assertEqual(source.read_bytes(), b"keep")
            with patch.object(app, "decrypt", return_value=b"incorrect"):
                with self.assertRaises(ValueError):
                    app.encrypt_file(source, root / "unverified.txt", "password", args)
            self.assertTrue(source.exists())
            real_encrypt = app.encrypt
            def change_source(*values):
                source.write_bytes(b"new data")
                return real_encrypt(*values)
            with patch.object(app, "encrypt", side_effect=change_source):
                with self.assertRaises(ValueError):
                    app.encrypt_file(source, root / "changed.txt", "password", args)
            self.assertEqual(source.read_bytes(), b"new data")
            app.encrypt_file(source, root / "success.txt", "password", args)
            self.assertFalse(source.exists())
            self.assertEqual(app.decrypt((root / "success.txt").read_text(), "password"),
                             b"new data")


if __name__ == "__main__":
    unittest.main()

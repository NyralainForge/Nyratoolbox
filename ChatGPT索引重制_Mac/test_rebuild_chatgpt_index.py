"""Offline regression tests; all writes use temporary synthetic databases."""
import contextlib
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import rebuild_chatgpt_index as tool


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'catalog.sqlite'
        self.backups = Path(self.temp.name) / 'backups'
        with sqlite3.connect(self.db) as c:
            for table, columns in tool.SCHEMA.items():
                c.execute('CREATE TABLE ' + table + ' (' + ','.join(columns.split()) + ')')
            c.execute('INSERT INTO local_thread_catalog_metadata VALUES (1, 7)')
            for host, kind in [('chatgpt:test', 'chatgpt'), ('local', 'local')]:
                c.execute('INSERT INTO local_thread_catalog_hosts VALUES (?,?)', (host, kind))
                c.execute('INSERT INTO local_thread_catalog '
                          '(host_id,thread_id,display_title,source_kind) VALUES (?,?,?,?)',
                          (host, 'test-thread', 'Synthetic title', kind))
                c.execute('INSERT INTO local_thread_catalog_scan_entries VALUES (?,?,0)',
                          (host, 'test-thread'))
                c.execute('INSERT INTO local_thread_catalog_scan_checkpoints VALUES (?,?,NULL)',
                          (host, 'test-checkpoint'))
                c.execute('INSERT INTO local_thread_catalog_sync_state VALUES (?,123,1,9,123)', (host,))

    def snapshot(self):
        with sqlite3.connect(self.db) as c:
            return {table: c.execute('SELECT * FROM ' + table).fetchall() for table in tool.SCHEMA}

    def change(self, restore=None):
        with patch.object(tool, 'idle_check'), contextlib.redirect_stdout(io.StringIO()):
            return tool.run_change(self.db, self.backups, restore)

    def test_rebuild_restore_and_preserve_new_local_changes(self):
        before = self.snapshot()
        backup = self.change()
        after = self.snapshot()
        self.assertEqual(after['local_thread_catalog_metadata'], [(1, 8)])
        for table in tool.TABLES[:3]:
            self.assertFalse(any(row[0] == 'chatgpt:test' for row in after[table]))
        self.assertIn(('chatgpt:test', None, 0, 0, None), after[tool.TABLES[3]])
        with sqlite3.connect(backup / 'catalog-before.sqlite') as c:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
            self.assertEqual(c.execute('SELECT * FROM local_thread_catalog').fetchall(), before[tool.TABLES[0]])
        self.assertEqual((backup / 'catalog-before.sqlite').stat().st_mode & 0o777, 0o600)
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE local_thread_catalog SET display_title='New local title' WHERE host_id='local'")
        self.change(backup)
        restored = self.snapshot()
        for table in tool.TABLES:
            self.assertEqual([r for r in restored[table] if r[0] == 'chatgpt:test'],
                             [r for r in before[table] if r[0] == 'chatgpt:test'])
        self.assertEqual([r[2] for r in restored[tool.TABLES[0]] if r[0] == 'local'], ['New local title'])

    def test_exception_rolls_back(self):
        before = self.snapshot()
        original = tool.rebuild_rows
        def fail(c, selected):
            original(c, selected)
            raise RuntimeError('Injected failure')
        with patch.object(tool, 'rebuild_rows', side_effect=fail), self.assertRaises(RuntimeError):
            self.change()
        self.assertEqual(self.snapshot(), before)

    def test_schema_change_rejected(self):
        with sqlite3.connect(self.db) as c:
            c.execute('ALTER TABLE local_thread_catalog ADD COLUMN unknown TEXT')
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, '结构'):
            self.change()
        self.assertEqual(self.snapshot(), before)

    def test_corrupt_backup_rejected(self):
        backup = self.change()
        with (backup / 'catalog-before.sqlite').open('ab') as f:
            f.write(b'tampered')
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, '校验值'):
            self.change(backup)
        self.assertEqual(self.snapshot(), before)

    def test_changed_accounts_rejected(self):
        backup = self.change()
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO local_thread_catalog_hosts VALUES ('chatgpt:other','chatgpt')")
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, '账户集合'):
            self.change(backup)
        self.assertEqual(self.snapshot(), before)

    def test_running_app_rejected(self):
        result = tool.subprocess.CompletedProcess([], 0, '123 /Applications/Codex.app/Contents/MacOS/Codex', '')
        with patch.object(tool.subprocess, 'run', return_value=result), self.assertRaisesRegex(RuntimeError, '仍在运行'):
            tool.idle_check(self.db)

    def test_unavailable_process_check_rejected(self):
        result = tool.subprocess.CompletedProcess([], 1, '', 'denied')
        with patch.object(tool.subprocess, 'run', return_value=result), self.assertRaisesRegex(RuntimeError, '无法检查'):
            tool.idle_check(self.db)


if __name__ == '__main__':
    unittest.main()

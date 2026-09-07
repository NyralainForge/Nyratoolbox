#!/usr/bin/env python3
"""Offline, transactional rebuild of the inspected ChatGPT catalog schema."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

DEFAULT_DB = Path.home() / '.codex/sqlite/codex-dev.db'
TABLES = ('local_thread_catalog', 'local_thread_catalog_scan_entries',
          'local_thread_catalog_scan_checkpoints', 'local_thread_catalog_sync_state')
SCHEMA = {
 'local_thread_catalog': 'host_id thread_id display_title source_created_at source_updated_at cwd source_kind source_detail model_provider git_branch observation_sequence missing_candidate thread_source source_recency_at pending_observed_title project_id conversation_origin',
 'local_thread_catalog_scan_entries': 'host_id thread_id removed',
 'local_thread_catalog_scan_checkpoints': 'host_id checkpoint failed_at',
 'local_thread_catalog_sync_state': 'host_id watermark_updated_at initial_build_complete observation_sequence last_full_reconciled_at',
 'local_thread_catalog_hosts': 'host_id host_kind',
 'local_thread_catalog_metadata': 'id catalog_revision',
}

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def connect(path, readonly=False):
    require(path.is_file(), '数据库不存在：' + str(path))
    mode = 'ro' if readonly else 'rw'
    c = sqlite3.connect(path.resolve().as_uri() + '?mode=' + mode,
                        uri=True, timeout=5, isolation_level=None)
    c.execute('PRAGMA busy_timeout=5000')
    if not readonly:
        c.execute('PRAGMA synchronous=FULL')
    return c

def validate(c):
    require(c.execute('PRAGMA quick_check').fetchall() == [('ok',)],
            '数据库完整性检查未通过，停止。')
    for table, columns in SCHEMA.items():
        actual = [r[1] for r in c.execute('PRAGMA table_info("' + table + '")')]
        require(actual == columns.split(), '数据库结构与已检查版本不同：' + table)
    require(c.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0] == 0,
            '数据库存在未审查的触发器，停止。')
    require(c.execute('SELECT count(*) FROM local_thread_catalog_metadata WHERE id=1').fetchone()[0] == 1,
            '缺少索引版本记录，停止。')

def hosts(c):
    ids = [r[0] for r in c.execute(
        "SELECT host_id FROM local_thread_catalog_hosts WHERE host_kind='chatgpt' ORDER BY host_id")]
    require(ids and all(x.startswith('chatgpt:') for x in ids), '未找到可识别的 ChatGPT 索引。')
    for host in ids:
        require(c.execute("SELECT count(*) FROM local_thread_catalog WHERE host_id=? AND source_kind!='chatgpt'",
                          (host,)).fetchone()[0] == 0, 'ChatGPT 索引中混有其他类型记录，停止。')
    return ids

def idle_check(db):
    # Fail closed if process inspection is unavailable; never stop any process.
    r = subprocess.run(['/bin/ps', '-axo', 'pid=,comm='], capture_output=True, text=True)
    require(r.returncode == 0, '无法检查应用进程；未修改数据库。请从普通终端运行。')
    pattern = r'/(?:ChatGPT|ChatGPT Classic|Codex)\.app/Contents/'
    pids = [x.strip().split()[0] for x in r.stdout.splitlines() if re.search(pattern, x)]
    require(not pids, 'ChatGPT/Codex 仍在运行（进程 ' + ', '.join(pids) + '）。请先用 ⌘Q 完全退出，再运行。')
    paths = [str(p) for p in (db, Path(str(db)+'-wal'), Path(str(db)+'-shm')) if p.exists()]
    r = subprocess.run(['/usr/sbin/lsof', '-t', '--'] + paths, capture_output=True, text=True)
    require(r.returncode in (0, 1) and not r.stderr.strip(), '无法可靠检查数据库占用，停止：' + r.stderr.strip())
    require(not r.stdout.strip(), '数据库仍被其他进程占用；请退出相关应用后重试。')

def digest_rows(c, table, where='', params=()):
    q = 'SELECT * FROM "' + table.replace('"', '""') + '"' + where
    # Order-independent digest, includes full row values but prints no private data.
    rows = sorted(hashlib.sha256(repr(tuple(r)).encode()).digest() for r in c.execute(q, params))
    return hashlib.sha256(b''.join(rows)).hexdigest()

def unaffected(c, selected):
    result = {}
    placeholders = ','.join('?' for _ in selected)
    for (table,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        if table == 'local_thread_catalog_metadata':
            continue
        where = ' WHERE host_id NOT IN (' + placeholders + ')' if table in TABLES else ''
        result[table] = digest_rows(c, table, where, selected if table in TABLES else ())
    return result

def make_backup(db, parent, purpose):
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    directory = parent / (purpose + '-' + stamp)
    directory.mkdir(mode=0o700)
    path = directory / 'catalog-before.sqlite'
    # Caller holds BEGIN IMMEDIATE. A separate reader takes a coherent snapshot,
    # including committed WAL data, while other database writers are blocked.
    source = connect(db, True)
    dest = sqlite3.connect(str(path))
    try:
        source.backup(dest)
        require(dest.execute('PRAGMA integrity_check').fetchall() == [('ok',)], '备份完整性检查失败。')
    finally:
        source.close()
        dest.close()
    path.chmod(0o600)
    manifest = {'format': 1, 'database': str(db.resolve()),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'purpose': purpose}
    (directory / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (directory / 'manifest.json').chmod(0o600)
    return directory

def rebuild_rows(c, selected):
    for host in selected:
        for table in TABLES:
            c.execute('DELETE FROM ' + table + ' WHERE host_id=?', (host,))
        c.execute('INSERT INTO local_thread_catalog_sync_state '
                  '(host_id, watermark_updated_at, initial_build_complete, observation_sequence, last_full_reconciled_at) '
                  'VALUES (?, NULL, 0, 0, NULL)', (host,))
    c.execute('UPDATE local_thread_catalog_metadata SET catalog_revision=catalog_revision+1 WHERE id=1')

def restore_rows(c, saved, selected):
    for host in selected:
        for table in TABLES:
            c.execute('DELETE FROM ' + table + ' WHERE host_id=?', (host,))
            rows = saved.execute('SELECT * FROM ' + table + ' WHERE host_id=?', (host,)).fetchall()
            if rows:
                columns = SCHEMA[table].split()
                c.executemany('INSERT INTO ' + table + ' (' + ','.join(columns) + ') VALUES (' +
                              ','.join('?' for _ in columns) + ')', rows)
    c.execute('UPDATE local_thread_catalog_metadata SET catalog_revision=catalog_revision+1 WHERE id=1')

def run_change(db, parent, restore=None):
    idle_check(db)
    saved = None
    if restore:
        restore = restore.resolve()
        info = json.loads((restore / 'manifest.json').read_text())
        snapshot = restore / 'catalog-before.sqlite'
        require(info.get('format') == 1 and info.get('database') == str(db.resolve()), '备份不属于此数据库，停止。')
        require(hashlib.sha256(snapshot.read_bytes()).hexdigest() == info['sha256'], '备份校验值不匹配，停止。')
        saved = connect(snapshot, True)
        validate(saved)
    c = connect(db)
    directory = None
    try:
        c.execute('BEGIN IMMEDIATE')
        validate(c)
        selected = hosts(c)
        if saved:
            require(hosts(saved) == selected, 'ChatGPT 账户集合已变化，不能自动恢复。')
        before = unaffected(c, selected)
        directory = make_backup(db, parent, 'before-restore' if saved else 'before-rebuild')
        print('完整备份已验证：' + str(directory), flush=True)
        if saved:
            restore_rows(c, saved, selected)
            for table in TABLES:
                for host in selected:
                    require(digest_rows(c, table, ' WHERE host_id=?', (host,)) ==
                            digest_rows(saved, table, ' WHERE host_id=?', (host,)), '恢复验证失败。')
        else:
            rebuild_rows(c, selected)
            for host in selected:
                for table in TABLES[:3]:
                    require(c.execute('SELECT count(*) FROM ' + table + ' WHERE host_id=?', (host,)).fetchone()[0] == 0,
                            '重建验证失败。')
                state = c.execute('SELECT watermark_updated_at,initial_build_complete,observation_sequence,last_full_reconciled_at '
                                  'FROM local_thread_catalog_sync_state WHERE host_id=?', (host,)).fetchone()
                require(state == (None, 0, 0, None), '同步状态重置验证失败。')
        require(unaffected(c, selected) == before, '发现范围外的数据变化，回滚。')
        validate(c)
        c.execute('COMMIT')
        # No WAL files are manually deleted, and unrelated tables are not restored.
    except BaseException:
        if c.in_transaction:
            c.execute('ROLLBACK')
        raise
    finally:
        c.close()
        if saved:
            saved.close()
    print('已恢复 ChatGPT 索引。' if restore else '已重置 ChatGPT 索引，并标记为需要完整重建。')
    print('现在可以手动打开 ChatGPT。网络验证错误或应用本身故障仍可能影响同步。')
    print('恢复命令（先退出应用）：')
    import shlex
    print('/usr/bin/python3 ' + shlex.quote(str(Path(__file__).resolve())) +
          ' --restore ' + shlex.quote(str(directory)))
    return directory

def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description='离线备份并重建 ChatGPT 本地聊天索引，不改云端聊天。')
    group = p.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true', help='只检查，不修改；可在应用运行时使用')
    group.add_argument('--rebuild', action='store_true', help='退出应用后，备份并重建')
    group.add_argument('--restore', type=Path, metavar='BACKUP_DIRECTORY', help='只恢复备份中的 ChatGPT 索引')
    a = p.parse_args()
    db = DEFAULT_DB
    c = connect(db, True)
    try:
        validate(c)
        selected = hosts(c)
        count = sum(c.execute('SELECT count(*) FROM local_thread_catalog WHERE host_id=?', (x,)).fetchone()[0] for x in selected)
    finally:
        c.close()
    print('数据库：' + str(db))
    print('识别到 %d 个 ChatGPT 账户索引，共 %d 条本地列表记录。' % (len(selected), count))
    print('只处理 ChatGPT 索引及扫描状态；保留本地/远程任务、项目、登录信息和云端聊天。')
    if a.check:
        print('检查通过。未修改数据库。')
        return
    if not (a.rebuild or a.restore):
        print('请先用 ⌘Q 退出 ChatGPT 和 Codex；本脚本不会替你退出应用。')
        if input('输入 REBUILD 并回车才会开始；其他输入取消：').strip() != 'REBUILD':
            print('已取消。未修改数据库。')
            return
    run_change(db, Path(__file__).resolve().parent / 'chatgpt-index-backups', a.restore)

if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as e:
        print('\n已停止：' + str(e), file=sys.stderr)
        print('未完成的数据库事务会回滚；已生成的备份会保留。', file=sys.stderr)
        sys.exit(1)

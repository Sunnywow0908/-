"""公共基础模块的数据库连接生命周期测试。"""
from pathlib import Path
from unittest.mock import patch

from 功能代码及实际项目文件.公共基础模块 import db


def test_database_initialize_closes_connection(tmp_path: Path):
    """初始化数据库后资源应显式释放，而非等待垃圾回收。"""
    real_connect = db.connect
    seen = []

    class ConnectionProxy:
        def __init__(self, real):
            self.real = real
            self.closed = False
            seen.append(self)
        def __enter__(self):
            return self.real.__enter__()
        def __exit__(self, *args):
            return self.real.__exit__(*args)
        def executescript(self, *args):
            return self.real.executescript(*args)
        def execute(self, *args):
            return self.real.execute(*args)
        def executemany(self, *args):
            return self.real.executemany(*args)
        def close(self):
            self.closed = True
            return self.real.close()

    with patch.object(db, "connect", side_effect=lambda p: ConnectionProxy(real_connect(p))):
        db.initialize_database(tmp_path / "check.sqlite3")
    assert seen and all(obj.closed for obj in seen)

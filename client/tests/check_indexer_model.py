"""Headless smoke test for IndexerListModel against a real running backend.
No display needed -- QNetworkAccessManager works fine under a plain QCoreApplication.
Run from src/: `python ../tests/check_indexer_model.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os

from api_client import ApiClient
from PySide6.QtCore import QCoreApplication, QTimer

from models.indexer_model import IndexerListModel

BASE_URL = os.environ.get("DEN_URL", "http://127.0.0.1:8686")
TOKEN = os.environ.get("DEN_API_TOKEN", "")
api = ApiClient(BASE_URL, TOKEN, persist=False)
app = QCoreApplication(sys.argv)
model = IndexerListModel(api)
failures = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def dump_rows(label: str) -> None:
    rows = [model.data(model.index(i), IndexerListModel.NameRole) for i in range(model.rowCount())]
    print(f"{label}: {rows}")


def step1_initial_refresh() -> None:
    print("-- step 1: initial refresh --")
    model.refresh()
    QTimer.singleShot(1000, step2_add)


def step2_add() -> None:
    dump_rows("after initial refresh")
    print("-- step 2: add indexer --")
    model.addIndexer("Client Test Indexer", "http://127.0.0.1:9999/api", "", "torznab")
    QTimer.singleShot(1000, step3_verify_added)


def step3_verify_added() -> None:
    dump_rows("after add")
    if not any(
        model.data(model.index(i), IndexerListModel.NameRole) == "Client Test Indexer"
        for i in range(model.rowCount())
    ):
        fail("added indexer not found after refresh")
    QTimer.singleShot(200, step4_test)


def step4_test() -> None:
    print("-- step 3: test connection (expected to fail, nothing listening on :9999) --")
    added_id = next(
        model.data(model.index(i), IndexerListModel.IndexerIdRole)
        for i in range(model.rowCount())
        if model.data(model.index(i), IndexerListModel.NameRole) == "Client Test Indexer"
    )
    model.testResult.connect(lambda iid, ok, msg: print(f"testResult: id={iid} ok={ok} msg={msg[:80]}"))
    model.testIndexer(added_id)
    QTimer.singleShot(1000, lambda: step5_delete(added_id))


def step5_delete(added_id: int) -> None:
    print("-- step 4: delete indexer --")
    model.deleteIndexer(added_id)
    QTimer.singleShot(1000, lambda: step6_verify_deleted(added_id))


def step6_verify_deleted(added_id: int) -> None:
    dump_rows("after delete")
    if any(model.data(model.index(i), IndexerListModel.IndexerIdRole) == added_id for i in range(model.rowCount())):
        fail("deleted indexer still present")
    print("-- done --")
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


model.errorOccurred.connect(lambda msg: fail(f"errorOccurred: {msg}"))
QTimer.singleShot(0, step1_initial_refresh)
sys.exit(app.exec())

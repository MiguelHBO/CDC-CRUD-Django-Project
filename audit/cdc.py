"""
audit/cdc.py
------------
CDC layer for the portfolio project.

Conceptually mirrors the production service:
  - Production : SQL Server CDC (log-based) → Microsoft Fabric Warehouse
  - Portfolio  : Django signals (post_save / post_delete) → DuckDB (local file)

Every INSERT / UPDATE / DELETE on a monitored model fires a signal.
The signal handler serialises the change and calls write_event(), which
appends a row to the DuckDB audit table — same schema used in the dashboard.
"""
import json
import threading
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import duckdb
from django.conf import settings

logger = logging.getLogger(__name__)

# Thread-local DuckDB connections (DuckDB connections are not thread-safe to share)
_local = threading.local()

# Tables monitored — mirrors TABLE_MAP in the production warehouse_writer.py
MONITORED_TABLES = {"Product", "Order"}

# DDL executed once on first connection
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cdc_audit_log (
    cdc_id        INTEGER PRIMARY KEY,
    table_name    VARCHAR,
    entity_id     INTEGER,
    operation     VARCHAR,        -- INSERT | UPDATE | DELETE
    change_date   TIMESTAMP,
    change_user   VARCHAR,
    column_name   VARCHAR,        -- NULL for INSERT/DELETE (whole-row event)
    old_value     VARCHAR,
    new_value     VARCHAR,
    row_snapshot  VARCHAR         -- JSON of the full row at change time
);

CREATE SEQUENCE IF NOT EXISTS cdc_id_seq START 1;
"""


def _get_conn() -> duckdb.DuckDBPyConnection:
    """Return a thread-local DuckDB connection, creating it if needed."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = duckdb.connect(settings.DUCKDB_PATH)
        _local.conn.execute(_SCHEMA_SQL)
    return _local.conn


def write_event(
    *,
    table_name: str,
    entity_id: int,
    operation: str,
    change_user: str = "system",
    column_name: Optional[str] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    row_snapshot: Optional[Dict] = None,
) -> None:
    """
    Persist a single CDC event to DuckDB.

    For UPDATE operations this is called once per changed column (same
    granularity as the production LSN-based CDC).
    For INSERT / DELETE it is called once with the full row snapshot.
    """
    try:
        conn = _get_conn()
        conn.execute(
            """
            INSERT INTO cdc_audit_log
                (cdc_id, table_name, entity_id, operation, change_date,
                 change_user, column_name, old_value, new_value, row_snapshot)
            VALUES (nextval('cdc_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                table_name,
                entity_id,
                operation,
                datetime.now(timezone.utc).replace(tzinfo=None),
                change_user,
                column_name,
                str(old_value) if old_value is not None else None,
                str(new_value) if new_value is not None else None,
                json.dumps(row_snapshot, default=str) if row_snapshot else None,
            ],
        )
    except Exception as exc:
        logger.error("[CDC] Failed to write audit event for %s #%s: %s", table_name, entity_id, exc)


def _model_to_dict(instance) -> Dict:
    """Serialise a Django model instance to a plain dict."""
    from django.forms.models import model_to_dict
    data = model_to_dict(instance)
    # model_to_dict skips auto fields; add pk and timestamps manually
    data["id"] = instance.pk
    for field in ("created_at", "updated_at"):
        if hasattr(instance, field):
            data[field] = str(getattr(instance, field))
    return data


# ---------------------------------------------------------------------------
# Signal handlers — registered in audit/apps.py → ready()
# ---------------------------------------------------------------------------

# Store pre-save snapshots per instance to detect changed columns on UPDATE
_presave_snapshots: Dict[str, Dict] = {}


def _snapshot_key(instance) -> str:
    return f"{type(instance).__name__}:{instance.pk}"


def handle_pre_save(sender, instance, **kwargs):
    """Capture the current DB state before an UPDATE so we can diff columns."""
    if instance.pk is None:
        return  # INSERT — nothing to snapshot
    try:
        old = sender.objects.get(pk=instance.pk)
        _presave_snapshots[_snapshot_key(instance)] = _model_to_dict(old)
    except sender.DoesNotExist:
        pass


def handle_post_save(sender, instance, created, **kwargs):
    table = type(instance).__name__
    if table not in MONITORED_TABLES:
        return

    snapshot = _model_to_dict(instance)

    if created:
        write_event(
            table_name=table,
            entity_id=instance.pk,
            operation="INSERT",
            row_snapshot=snapshot,
        )
        return

    # UPDATE — emit one row per changed column (mirrors production CDC granularity)
    key = _snapshot_key(instance)
    old_snapshot = _presave_snapshots.pop(key, {})

    changed_any = False
    for col, new_val in snapshot.items():
        old_val = old_snapshot.get(col)
        if col in ("updated_at",):
            continue  # always changes; not meaningful
        if str(old_val) != str(new_val):
            write_event(
                table_name=table,
                entity_id=instance.pk,
                operation="UPDATE",
                column_name=col,
                old_value=old_val,
                new_value=new_val,
            )
            changed_any = True

    if not changed_any:
        # No column diff detected (e.g. save() called without real change)
        write_event(
            table_name=table,
            entity_id=instance.pk,
            operation="UPDATE",
            row_snapshot=snapshot,
        )


def handle_post_delete(sender, instance, **kwargs):
    table = type(instance).__name__
    if table not in MONITORED_TABLES:
        return
    write_event(
        table_name=table,
        entity_id=instance.pk,
        operation="DELETE",
        row_snapshot=_model_to_dict(instance),
    )

import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from audit.cdc import _get_conn


def dashboard(request):
    conn = _get_conn()

    # Summary counts
    counts = conn.execute("""
        SELECT operation, COUNT(*) as total
        FROM cdc_audit_log
        GROUP BY operation
        ORDER BY operation
    """).fetchall()
    op_counts = {row[0]: row[1] for row in counts}

    # Recent events (last 50)
    events = conn.execute("""
        SELECT cdc_id, table_name, entity_id, operation, change_date,
               column_name, old_value, new_value, row_snapshot
        FROM cdc_audit_log
        ORDER BY cdc_id DESC
        LIMIT 50
    """).fetchall()

    event_list = []
    for row in events:
        event_list.append({
            "cdc_id":      row[0],
            "table_name":  row[1],
            "entity_id":   row[2],
            "operation":   row[3],
            "change_date": row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else "—",
            "column_name": row[5] or "—",
            "old_value":   row[6] or "—",
            "new_value":   row[7] or "—",
            "has_snapshot": bool(row[8]),
        })

    # Operations per hour (last 24h) for the timeline chart
    timeline = conn.execute("""
        SELECT
            strftime(change_date, '%Y-%m-%d %H:00') as hour,
            operation,
            COUNT(*) as cnt
        FROM cdc_audit_log
        WHERE change_date >= NOW() - INTERVAL '24 hours'
        GROUP BY 1, 2
        ORDER BY 1
    """).fetchall()

    # Ops per table
    per_table = conn.execute("""
        SELECT table_name, operation, COUNT(*) as cnt
        FROM cdc_audit_log
        GROUP BY table_name, operation
        ORDER BY table_name, operation
    """).fetchall()

    total_events = conn.execute("SELECT COUNT(*) FROM cdc_audit_log").fetchone()[0]

    ctx = {
        "op_counts": op_counts,
        "events": event_list,
        "timeline_json": json.dumps([{"hour": r[0], "op": r[1], "cnt": r[2]} for r in timeline]),
        "per_table_json": json.dumps([{"table": r[0], "op": r[1], "cnt": r[2]} for r in per_table]),
        "total_events": total_events,
    }
    return render(request, "audit/dashboard.html", ctx)


@require_GET
def api_recent(request):
    """JSON endpoint — polled every 5s for live updates."""
    conn = _get_conn()
    since = request.GET.get("since", 0)
    rows = conn.execute("""
        SELECT cdc_id, table_name, entity_id, operation,
               change_date, column_name, old_value, new_value
        FROM cdc_audit_log
        WHERE cdc_id > ?
        ORDER BY cdc_id DESC
        LIMIT 20
    """, [int(since)]).fetchall()

    data = [
        {
            "cdc_id":      r[0],
            "table_name":  r[1],
            "entity_id":   r[2],
            "operation":   r[3],
            "change_date": r[4].strftime("%H:%M:%S") if r[4] else "—",
            "column_name": r[5] or "—",
            "old_value":   r[6] or "—",
            "new_value":   r[7] or "—",
        }
        for r in rows
    ]
    return JsonResponse({"events": data})

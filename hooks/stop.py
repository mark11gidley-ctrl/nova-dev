"""Stop: record this session in the band ledger, send the optional webhook, and block
stopping while the last test run is failing (fresh log only). Honors stop_hook_active to avoid loops."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger import build_payload, make_row, send_webhook, upsert_row  # noqa: E402
from tests_gate import status  # noqa: E402


def main(data):
    cwd = data.get("cwd") or os.getcwd()
    transcript = data.get("transcript_path") or ""
    from settings import get as setting
    # the ledger is best effort: a failure here must never skip the test gate below
    try:
        if setting("ledger") and transcript and os.path.isfile(transcript):
            row = make_row(data.get("session_id"), transcript, cwd)
            upsert_row(row)
            url = setting("webhook_url")
            if url:
                try:
                    send_webhook(build_payload(row, setting("send_names")), url, setting("webhook_token"))
                except (OSError, ValueError) as exc:
                    sys.stderr.write(f"nova-dev: webhook not sent: {exc}\n")
    except Exception as exc:  # noqa: BLE001 - reported, never fatal
        sys.stderr.write(f"nova-dev: ledger not written: {exc}\n")
    if not data.get("stop_hook_active") and status(cwd) == "fail":
        sys.stderr.write("Tests still fail. Fix them before stopping, or say why they cannot pass.\n")
        return 2
    return 0


if __name__ == "__main__":
    try:
        payload = json.load(sys.stdin)
        if os.environ.get("NOVA_DEV_HOOK_LOG"):  # opt-in debug: which fields Claude Code sends to the Stop hook
            with open(os.environ["NOVA_DEV_HOOK_LOG"], "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"stop_keys": sorted(payload.keys()), "payload": {
                    k: (v if isinstance(v, (int, float, bool)) or v is None else str(v)[:60]) for k, v in payload.items()}}) + "\n")
    except ValueError:
        payload = {}
    sys.exit(main(payload))

"""Show what the guards have saved, in the terminal. Usage: nd.py savings

Counts are exact: each blocked repeat read or repeated command. Tokens for reads are an estimate
(file size in characters divided by 4). Run nd.py report for the full web page."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
import savings  # noqa: E402


def lines(data=None):
    data = savings.load() if data is None else data
    if not data:
        return ["no savings recorded yet"]
    out = []
    read = data.get("read", {"count": 0, "bytes": 0})
    out.append(f"repeat reads blocked:    {read['count']:>6}  (about {read['bytes'] // 4:,} tokens kept out, estimate)")
    bash = data.get("bash", {"count": 0, "bytes": 0})
    out.append(f"repeat commands blocked: {bash['count']:>6}")
    return out


if __name__ == "__main__":
    for row in lines():
        print(row)
    sys.exit(0)

#!/usr/bin/env python3
# satoramy.py — X² · ∞ = 1 · ∞
# Server + DB. Eine Datei. Eine Formel.

import json, sqlite3, hashlib, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DB = Path("satoramy.db")
PORT = 8420

# ───── Die Formel ─────
# X ∈ {+1, -1}, X² = 1
# Übergang: x_next = x_prev * op   (op ∈ {+1, -1})
# Kette ist geschlossen, wenn Produkt aller X = 1

def parity_of(data: str) -> int:
    """Bestimmt X ∈ {+1,-1} aus den Daten via XOR aller Bits."""
    h = hashlib.sha256(data.encode()).digest()
    b = 0
    for byte in h:
        b ^= byte
    return +1 if (bin(b).count("1") % 2 == 0) else -1

def block_hash(index: int, prev_x: int, x: int, data: str) -> str:
    raw = f"{index}|{prev_x}|{x}|{data}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]

# ───── Die DB ─────

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            idx       INTEGER PRIMARY KEY,
            prev_x    INTEGER NOT NULL,
            x         INTEGER NOT NULL,
            data      TEXT    NOT NULL,
            hash      TEXT    NOT NULL,
            ts        REAL    NOT NULL
        )
    """)
    # Genesis: X = +1 (die Einheit)
    cur = con.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
    if cur == 0:
        h = block_hash(0, 0, +1, "GENESIS::X²·∞=1·∞")
        con.execute("INSERT INTO blocks VALUES (0, 0, 1, ?, ?, ?)",
                    ("GENESIS::X²·∞=1·∞", h, time.time()))
    con.commit()
    con.close()

def add_block(data: str):
    con = sqlite3.connect(DB)
    row = con.execute("SELECT idx, x FROM blocks ORDER BY idx DESC LIMIT 1").fetchone()
    idx, prev_x = (row[0] + 1, row[1]) if row else (0, 0)
    x = prev_x * parity_of(data)   # ← X · X = 1-Kern
    h = block_hash(idx, prev_x, x, data)
    con.execute("INSERT INTO blocks VALUES (?,?,?,?,?,?)",
                (idx, prev_x, x, data, h, time.time()))
    con.commit()
    con.close()
    return {"idx": idx, "prev_x": prev_x, "x": x, "hash": h}

def get_chain():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT idx, prev_x, x, data, hash, ts FROM blocks ORDER BY idx").fetchall()
    con.close()
    return [{"idx":r[0],"prev_x":r[1],"x":r[2],"data":r[3],"hash":r[4],"ts":r[5]} for r in rows]

def verify_chain():
    """Kette ist gültig, wenn jeder Übergang konsistent ist.
       UND: Produkt aller X ist ±1 (X²=1 für jedes X).
    """
    chain = get_chain()
    prod = 1
    for i, b in enumerate(chain):
        prod *= b["x"]
        if i == 0:
            continue
        # Übergang prüfen: x[i] = x[i-1] * parity(data[i])
        if b["x"] != b["prev_x"] * parity_of(b["data"]):
            return {"valid": False, "bad_index": i}
        if b["prev_x"] != chain[i-1]["x"]:
            return {"valid": False, "bad_index": i, "reason": "prev_x mismatch"}
    return {"valid": True, "product": prod, "closed": prod == 1}

# ───── HTTP ─────

class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self._json(200, {"name":"SATORAMY","formula":"X·X·∞ = 1·∞","status":"running"})
        elif self.path == "/chain":
            self._json(200, get_chain())
        elif self.path == "/verify":
            self._json(200, verify_chain())
        else:
            self._json(404, {"error":"not found"})

    def do_POST(self):
        if self.path != "/add":
            return self._json(404, {"error":"not found"})
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n).decode())["data"]
        except Exception as e:
            return self._json(400, {"error": str(e)})
        self._json(201, add_block(data))

    def log_message(self, *a): pass

if __name__ == "__main__":
    init_db()
    print(f"SATORAMY · X·X·∞ = 1·∞ · DB={DB} · http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()

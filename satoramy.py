#!/usr/bin/env python3
# satoramy.py — X² · ∞ = 1 · ∞ — Server
import json, sqlite3, hashlib, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DB = Path(__file__).parent / "satoramy.db"
HTML = Path(__file__).parent / "index.html"
PORT = 8420

def parity_of(data):
    h = hashlib.sha256(data.encode()).digest()
    b = 0
    for byte in h: b ^= byte
    return 1 if bin(b).count("1") % 2 == 0 else -1

def block_hash(idx, prev_x, x, data):
    return hashlib.sha256(f"{idx}|{prev_x}|{x}|{data}".encode()).hexdigest()[:16]

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS blocks (
        idx INTEGER PRIMARY KEY, prev_x INTEGER, x INTEGER,
        data TEXT, hash TEXT, ts REAL)""")
    if con.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
        h = block_hash(0, 0, 1, "GENESIS")
        con.execute("INSERT INTO blocks VALUES (0,0,1,?,?,?)",
                    ("GENESIS::X²·∞=1·∞", h, time.time()))
    con.commit(); con.close()

def add_block(data):
    con = sqlite3.connect(DB)
    row = con.execute("SELECT idx, x FROM blocks ORDER BY idx DESC LIMIT 1").fetchone()
    idx, prev_x = (row[0]+1, row[1]) if row else (0, 0)
    x = prev_x * parity_of(data)
    h = block_hash(idx, prev_x, x, data)
    con.execute("INSERT INTO blocks VALUES (?,?,?,?,?,?)",
                (idx, prev_x, x, data, h, time.time()))
    con.commit(); con.close()
    return {"idx": idx, "prev_x": prev_x, "x": x, "hash": h}

def get_chain():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT idx,prev_x,x,data,hash,ts FROM blocks ORDER BY idx").fetchall()
    con.close()
    return [dict(zip(["idx","prev_x","x","data","hash","ts"], r)) for r in rows]

def verify_chain():
    chain = get_chain(); prod = 1
    for i, b in enumerate(chain):
        prod *= b["x"]
        if i == 0: continue
        if b["x"] != b["prev_x"] * parity_of(b["data"]):
            return {"valid": False, "bad": i}
        if b["prev_x"] != chain[i-1]["x"]:
            return {"valid": False, "bad": i, "reason": "prev_x"}
    return {"valid": True, "product": prod, "closed": prod == 1, "blocks": len(chain)}

def reset_db():
    con = sqlite3.connect(DB)
    con.execute("DELETE FROM blocks")
    h = block_hash(0, 0, 1, "GENESIS")
    con.execute("INSERT INTO blocks VALUES (0,0,1,?,?,?)",
                ("GENESIS::X²·∞=1·∞", h, time.time()))
    con.commit(); con.close()
    return {"ok": True}

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False, indent=2)
        if isinstance(body, str): body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            if HTML.exists():
                self._send(200, HTML.read_text(encoding="utf-8"), "text/html")
            else:
                self._send(404, "index.html nicht gefunden", "text/plain")
        elif self.path == "/api/status":
            self._send(200, {"status":"running","blocks":len(get_chain())})
        elif self.path == "/api/chain":
            self._send(200, get_chain())
        elif self.path == "/api/verify":
            self._send(200, verify_chain())
        elif self.path == "/api/reset":
            self._send(200, reset_db())
        else:
            self._send(404, {"error":"not found"})

    def do_POST(self):
        if self.path == "/api/add":
            n = int(self.headers.get("Content-Length", 0))
            try: data = json.loads(self.rfile.read(n).decode()).get("data","")
            except: return self._send(400, {"error":"bad json"})
            self._send(201, add_block(data))
        else:
            self._send(404, {"error":"not found"})

    def log_message(self, *a): pass

if __name__ == "__main__":
    init_db()
    print(f"SATORAMY · X·X·∞=1·∞ · http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()

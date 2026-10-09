import os
import psycopg2
import redis
from flask import Flask, jsonify, request

app = Flask(__name__)

cache = redis.Redis(
    host=os.getenv("REDIS_HOST", "cache"),
    port=6379
)

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/notes")
def list_notes():
    hits = cache.incr("hits")
    with get_db() as conn, conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS notes "
            "(id SERIAL PRIMARY KEY, text TEXT)"
        )
        cur.execute("SELECT id, text FROM notes ORDER BY id")
        rows = [{"id": r[0], "text": r[1]} for r in cur.fetchall()]
    return jsonify(
        hits=hits,
        notes=rows,
        served_by=os.uname().nodename
    )

@app.post("/notes")
def add_note():
    text = request.json["text"]
    with get_db() as conn, conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS notes "
            "(id SERIAL PRIMARY KEY, text TEXT)"
        )
        cur.execute(
            "INSERT INTO notes (text) VALUES (%s) RETURNING id",
            (text,)
        )
        new_id = cur.fetchone()[0]
    return {"id": new_id, "text": text}, 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

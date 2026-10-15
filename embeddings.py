import os
import re
import json
import threading

import mysql.connector


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model = None
_model_lock = threading.Lock()


# ==========================================
# 1. CARGA DEL MODELO
# ==========================================

def get_model():
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                print("Cargando modelo de embeddings...", flush=True)

                _model = SentenceTransformer(
                    MODEL_NAME,
                    device="cpu"
                )

                print("Modelo cargado correctamente", flush=True)

    return _model


# ==========================================
# 2. CONEXIÓN A MYSQL
# ==========================================

def get_db_connection():
    config = {
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASS"),
        "database": os.environ.get("DB_NAME"),
        "unix_socket": f"/cloudsql/{os.environ.get('INSTANCE_CONNECTION_NAME')}",
        "charset": "utf8mb4",
        "connection_timeout": 15,
    }

    return mysql.connector.connect(**config)


# ==========================================
# 3. LIMPIAR TWEET
# ==========================================

def limpiar_tweet(texto):
    if texto is None:
        return ""

    texto = str(texto)

    # Eliminar URLs
    texto = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        texto,
        flags=re.IGNORECASE
    )

    # Eliminar menciones
    texto = re.sub(r"(?<!\w)@\w+", " ", texto)

    # Eliminar RT al inicio
    texto = re.sub(
        r"^\s*RT\s*:?\s*",
        " ",
        texto,
        flags=re.IGNORECASE
    )

    # Eliminar símbolos decorativos
    texto = re.sub(
        r"[★☆◆◉•▪🔴🟡🟠✅✔️✳️🔹🔸▶️🔻🔺]+",
        " ",
        texto
    )

    # Eliminar separadores
    texto = re.sub(r"\s[-–—]{2,}\s", " ", texto)

    # Normalizar espacios
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


# ==========================================
# 4. OBTENER TWEETS PENDIENTES
# ==========================================

def get_tweets():
    sql = """
        SELECT
            t.tweetid,
            t.text
        FROM Tweets t
        LEFT JOIN tweet_embeddings e
            ON t.tweetid = e.tweetid
        WHERE e.tweetid IS NULL
        ORDER BY t.tweetid
        LIMIT 50
    """

    conn = get_db_connection()

    try:
        cur = conn.cursor(dictionary=True)

        try:
            cur.execute(sql)
            return cur.fetchall()
        finally:
            cur.close()

    finally:
        conn.close()


# ==========================================
# 5. PREPARAR EMBEDDINGS
# ==========================================

def data_to_insert(embeddings, texts, tweet_ids):
    data = []

    for tweetid, texto, embedding in zip(
        tweet_ids,
        texts,
        embeddings
    ):
        data.append((
            tweetid,
            MODEL_NAME,
            len(embedding),
            json.dumps(embedding.tolist()),
            texto
        ))

    return data


# ==========================================
# 6. GENERAR Y GUARDAR EMBEDDINGS
# ==========================================

def insert_embeddings():
    tweets = get_tweets()

    if not tweets:
        print("No hay tweets sin embeddings", flush=True)
        return 0

    print(
        f"Tweets pendientes seleccionados: {len(tweets)}",
        flush=True
    )

    tweet_ids = []
    texts = []

    for tweet in tweets:
        tweet_ids.append(tweet["tweetid"])
        texts.append(limpiar_tweet(tweet["text"]))

    # Cargar modelo únicamente cuando se necesite
    model = get_model()

    print("Generando embeddings...", flush=True)

    embeddings = model.encode(
        texts,
        batch_size=16,
        show_progress_bar=False,
        normalize_embeddings=True
    )

    data = data_to_insert(
        embeddings,
        texts,
        tweet_ids
    )

    query = """
        INSERT INTO tweet_embeddings (
            tweetid,
            model_name,
            embedding_dim,
            embedding_vector,
            texto_preprocesado
        )
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            embedding_vector = VALUES(embedding_vector),
            texto_preprocesado = VALUES(texto_preprocesado),
            embedding_dim = VALUES(embedding_dim),
            model_name = VALUES(model_name),
            created_at = CURRENT_TIMESTAMP
    """

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        try:
            cur.executemany(query, data)
            conn.commit()

            print(
                f"Embeddings guardados: {len(data)}",
                flush=True
            )

        except Exception:
            conn.rollback()
            raise

        finally:
            cur.close()

    finally:
        conn.close()

    return len(data)
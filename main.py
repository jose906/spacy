
import mysql.connector
from typing import List, Tuple
from mysql.connector import Error
from flask import Flask, jsonify
from spacyscript import get_entities
import os 
from spacyscript import get_entities_detailed
from entity_resolver import resolve_entity

app = Flask(__name__)


db_config = {
            # IP pública o nombre interno de Cloud SQL
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASS"),
    "database": os.environ.get("DB_NAME"),
    "unix_socket": f"/cloudsql/{os.environ.get('INSTANCE_CONNECTION_NAME')}",
    "charset": "utf8mb4",
    "port": "3306",
}


@app.route('/spacy', methods=['GET'])
def spacy():
    try:
        conexion = mysql.connector.connect(**db_config)

        if conexion.is_connected():
            print("✅ Conexión exitosa a MySQL", flush=True)

            cursor = conexion.cursor(dictionary=True)

            # --- 3. Obtener el último tweet YA clasificado ---
            # Detectamos si alguna columna de entidades tiene contenido
            last_sql = """
                SELECT MAX(created) AS last_processed
                FROM Tweets
                WHERE Lugar <> ''
                OR Persona <> ''
                OR Organizacion <> ''
                OR Locacion <> ''
                OR Otros <> ''
            """
            cursor.execute(last_sql)
            row = cursor.fetchone()
            last_processed = row["last_processed"]

            if last_processed is None:
                print("ℹ️ No hay tweets clasificados aún. Se procesarán TODOS los registros.")
                select_sql = """
                    SELECT tweetid, text
                    FROM Tweets
                    ORDER BY created ASC
                """
                cursor.execute(select_sql)
            else:
                print(f"ℹ️ Último tweet clasificado tiene created = {last_processed}", flush=True)
                select_sql = """
                    SELECT tweetid, text
                    FROM Tweets
                    WHERE created > %s
                    ORDER BY created ASC
                """
                cursor.execute(select_sql, (last_processed,))

            tweets = cursor.fetchall()

            if not tweets:
                print("✅ No hay nuevos tweets para clasificar.")
            else:
                print(f"📄 Procesando {len(tweets)} tweets nuevos...")
                a = 0

                for t in tweets:
                    entidades = get_entities(t["text"])

                    lugar = ", ".join(entidades["LOC"])
                    persona = ", ".join(entidades["PER"])
                    organizacion = ", ".join(entidades["ORG"])
                    locacion = lugar   # si quieres que locacion = lugar
                    otros = ", ".join(entidades["MISC"])

                    update_sql = """
                        UPDATE Tweets
                        SET Lugar = %s,
                            Persona = %s,
                            Organizacion = %s,
                            Locacion = %s,
                            Otros = %s
                        WHERE tweetid = %s
                    """
                    cursor.execute(update_sql, (
                        lugar, persona, organizacion, locacion, otros, t["tweetid"]
                    ))
                    a += 1
                    if a % 100 == 0:
                        print(f"✅ Procesados {a} tweets...")
                        break
                    

                conexion.commit()
                print("✅ Entidades actualizadas correctamente.",flush=True)

    except Error as e:
        print(f"❌ Error en la conexión o actualización: {e}")

    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()
            print("🔒 Conexión cerrada.")
    return jsonify({"status": "completed"}), 200

def get_db_connection():
    return mysql.connector.connect(**db_config)



@app.route("/test", methods=["GET"])
def health():
    try:
        conn = get_db_connection()
        if conn.is_connected():
            return "OK - DB Connected", 200
        return "DB Not Connected", 500

    except Exception as e:
        return f"DB Error: {e}", 500

    finally:
        try:
            conn.close()
        except:
            pass
        
@app.route("/spacy_entities_v2", methods=["GET"])
def spacy_entities_v2():

    conexion = None
    cursor = None

    try:
        conexion = mysql.connector.connect(**db_config)
        cursor = conexion.cursor(dictionary=True)

        print("✅ Conexión exitosa a MySQL", flush=True)

        # =====================================================
        # 1. BUSCAR TWEETS QUE TODAVÍA NO ESTÁN EN tweet_entities
        # =====================================================
        #
        # IMPORTANTE:
        # No usamos MAX(created).
        #
        # Buscamos directamente tweets que todavía no tengan
        # relaciones en tweet_entities.
        #
        # LIMIT 100 para probar de forma controlada.
        # =====================================================

        select_sql = """
            SELECT
                t.tweetid,
                t.text,
                t.created
            FROM Tweets t
            WHERE NOT EXISTS (
                SELECT 1
                FROM tweet_entities te
                WHERE te.tweetid = t.tweetid
            )
            AND t.text IS NOT NULL
            AND TRIM(t.text) <> ''
            ORDER BY t.created ASC, t.tweetid ASC
            LIMIT 50
        """

        cursor.execute(select_sql)
        tweets = cursor.fetchall()

        if not tweets:
            print("✅ No hay tweets pendientes para entity resolver.", flush=True)

            return jsonify({
                "status": "completed",
                "tweets_processed": 0,
                "entities_detected": 0,
                "errors": 0
            }), 200

        print(
            f"📄 Procesando {len(tweets)} tweets...",
            flush=True
        )

        tweets_processed = 0
        entities_detected = 0
        errors = 0

        # =====================================================
        # 2. PROCESAR TWEETS
        # =====================================================

        for tweet in tweets:

            tweetid = tweet["tweetid"]
            text = tweet["text"]

            try:

                # ---------------------------------------------
                # Ejecutar spaCy UNA sola vez
                # ---------------------------------------------

                entidades = get_entities_detailed(text)

                # ---------------------------------------------
                # Limpiar relaciones anteriores de este tweet
                #
                # Esto hace que el procesamiento sea idempotente.
                # NO elimina entities ni entity_aliases.
                # ---------------------------------------------

                cursor.execute(
                    """
                    DELETE FROM tweet_entities
                    WHERE tweetid = %s
                    """,
                    (tweetid,)
                )

                # ---------------------------------------------
                # Resolver cada entidad
                # ---------------------------------------------

                for label, lista in entidades.items():

                    for entity in lista:

                        resultado = resolve_entity(
                            cursor,
                            entity
                        )

                        entity_id = resultado["entity_id"]

                        # -------------------------------------
                        # Guardar relación tweet -> entidad
                        # -------------------------------------

                        insert_sql = """
                            INSERT INTO tweet_entities (
                                tweetid,
                                entity_id,
                                mention,
                                entity_type,
                                start_char,
                                end_char,
                                detection_source,
                                resolution_source,
                                confidence
                            )
                            VALUES (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            )
                        """

                        cursor.execute(
                            insert_sql,
                            (
                                tweetid,
                                entity_id,
                                entity["text"],
                                entity["label"],
                                entity["start_char"],
                                entity["end_char"],
                                entity["detection_source"],
                                resultado["resolution_source"],
                                resultado["confidence"]
                            )
                        )

                        entities_detected += 1

                # ---------------------------------------------
                # COMMIT POR TWEET
                #
                # Para esta etapa de pruebas prefiero esto.
                # Si un tweet falla, los anteriores quedan
                # correctamente guardados.
                # ---------------------------------------------

                conexion.commit()

                tweets_processed += 1

                print(
                    f"✅ Tweet {tweetid} | "
                    f"entidades: "
                    f"{sum(len(v) for v in entidades.values())}",
                    flush=True
                )

            except Exception as tweet_error:

                conexion.rollback()

                errors += 1

                print(
                    f"❌ Error procesando tweet {tweetid}: "
                    f"{tweet_error}",
                    flush=True
                )

        # =====================================================
        # 3. RESULTADO
        # =====================================================

        print(
            f"\n✅ TERMINADO | "
            f"tweets={tweets_processed} | "
            f"entidades={entities_detected} | "
            f"errores={errors}",
            flush=True
        )

        return jsonify({
            "status": "completed",
            "tweets_processed": tweets_processed,
            "entities_detected": entities_detected,
            "errors": errors
        }), 200

    except Exception as e:

        if conexion:
            conexion.rollback()

        print(
            f"❌ Error general en spacy_entities_v2: {e}",
            flush=True
        )

        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

    finally:

        if cursor:
            try:
                cursor.close()
            except Exception as close_error:
                print(
                    f"⚠️ Error cerrando cursor: {close_error}",
                    flush=True
                )

        if conexion:
            try:
                if conexion.is_connected():
                    conexion.close()
            except Exception as close_error:
                print(
                    f"⚠️ Error cerrando conexión: {close_error}",
                    flush=True
                )

        print("🔒 Conexión cerrada.", flush=True)
if __name__ == "__main__":
    # Para desarrollo local (no producción)
    app.run(host="0.0.0.0", port=8080, debug=True)

import mysql.connector
from typing import List, Tuple
from mysql.connector import Error
from flask import Flask, jsonify
from spacyscript import get_entities
import os 
from spacyscript import get_entities_detailed
from entity_resolver import resolve_entity
from entity_resolver import resolve_entity,should_resolve_entity


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
        
@app.route("/prueba",methods=["GET"])
def prueba():
    from spacyscript import nlp

    texto = "La Confederación Agropecuaria Nacional anunció nuevas medidas."

    doc = nlp(texto)

    for ent in doc.ents:
        print(
            "TEXT:", ent.text,
            "| LABEL:", ent.label_,
            "| ENT_ID:", ent.ent_id_, flush=True)
    return "ok"
    
@app.route("/spacy_entities_v2", methods=["GET"])
def spacy_entities_v2():

    conexion = None
    cursor = None

    try:
        # =====================================================
        # 1. CONEXIÓN
        # =====================================================

        conexion = mysql.connector.connect(**db_config)
        cursor = conexion.cursor(dictionary=True)

        print("✅ Conexión exitosa a MySQL", flush=True)

        # =====================================================
        # 2. OBTENER TWEETS PENDIENTES
        # =====================================================
        #
        # entities_processed:
        #
        # 0 = pendiente
        # 1 = procesado correctamente
        #
        # Ya NO dependemos de tweet_entities para saber si
        # un tweet fue procesado.
        #
        # Esto permite marcar correctamente también los tweets
        # que no contienen ninguna entidad.
        # =====================================================

        select_sql = """
            SELECT
                t.tweetid,
                t.text,
                t.created
            FROM Tweets t
            WHERE t.entities_processed = 0
              AND t.text IS NOT NULL
              AND TRIM(t.text) <> ''
            ORDER BY t.created ASC, t.tweetid ASC
            LIMIT 20
        """

        cursor.execute(select_sql)
        tweets = cursor.fetchall()

        # =====================================================
        # 3. NO HAY PENDIENTES
        # =====================================================

        if not tweets:

            print(
                "✅ No hay tweets pendientes para entity resolver.",
                flush=True
            )

            return jsonify({
                "status": "completed",
                "tweets_processed": 0,
                "entities_detected": 0,
                "entities_saved": 0,
                "entities_discarded": 0,
                "errors": 0
            }), 200

        print(
            f"📄 Procesando {len(tweets)} tweets...",
            flush=True
        )

        # =====================================================
        # 4. CONTADORES GENERALES
        # =====================================================

        tweets_processed = 0
        entities_detected = 0
        entities_saved = 0
        entities_discarded = 0
        errors = 0

        # =====================================================
        # 5. PROCESAR TWEETS
        # =====================================================

        for tweet in tweets:

            tweetid = tweet["tweetid"]
            text = tweet["text"]

            try:

                print(
                    "\n" + "=" * 100,
                    flush=True
                )

                print(
                    f"📝 Tweet: {tweetid}",
                    flush=True
                )

                # =================================================
                # CONTADORES DEL TWEET ACTUAL
                # =================================================

                tweet_saved = 0
                tweet_discarded = 0

                # =================================================
                # 5.1 EJECUTAR SPACY
                # =================================================

                entidades = get_entities_detailed(text)

                tweet_entities_count = sum(
                    len(lista)
                    for lista in entidades.values()
                )

                entities_detected += tweet_entities_count

                print(
                    f"🔎 Tweet {tweetid} | "
                    f"Entidades detectadas: {tweet_entities_count} | "
                    f"PER={len(entidades.get('PER', []))} | "
                    f"ORG={len(entidades.get('ORG', []))} | "
                    f"LOC={len(entidades.get('LOC', []))} | "
                    f"MISC={len(entidades.get('MISC', []))}",
                    flush=True
                )

                # =================================================
                # 5.2 LIMPIAR RELACIONES ANTERIORES
                # =================================================
                #
                # Si por algún motivo este tweet fue procesado
                # anteriormente, reconstruimos sus relaciones.
                #
                # NO eliminamos entities ni entity_aliases.
                # =================================================

                cursor.execute(
                    """
                    DELETE FROM tweet_entities
                    WHERE tweetid = %s
                    """,
                    (tweetid,)
                )

                # =================================================
                # 5.3 RECORRER ENTIDADES
                # =================================================

                for label, lista in entidades.items():

                    for entity in lista:

                        # =========================================
                        # FILTRO DE CALIDAD
                        # =========================================

                        if not should_resolve_entity(entity):

                            entities_discarded += 1
                            tweet_discarded += 1

                            print(
                                f"⏭️ Tweet {tweetid} | "
                                f"DESCARTADA | "
                                f"{entity['text']} | "
                                f"{entity['label']}",
                                flush=True
                            )

                            continue

                        # =========================================
                        # RESOLVER ENTIDAD
                        # =========================================

                        resultado = resolve_entity(
                            cursor,
                            entity
                        )

                        entity_id = resultado["entity_id"]
                        resolution_source = resultado[
                            "resolution_source"
                        ]
                        confidence = resultado["confidence"]

                        # =========================================
                        # GUARDAR RELACIÓN TWEET -> ENTITY
                        # =========================================

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
                                resolution_source,
                                confidence
                            )
                        )

                        entities_saved += 1
                        tweet_saved += 1

                        print(
                            f"✅ Tweet {tweetid} | "
                            f"GUARDADA | "
                            f"{entity['text']} | "
                            f"{entity['label']} | "
                            f"entity_id={entity_id} | "
                            f"source={resolution_source}",
                            flush=True
                        )

                # =================================================
                # 5.4 MARCAR TWEET COMO PROCESADO
                # =================================================
                #
                # MUY IMPORTANTE:
                #
                # Llegamos aquí solamente si todo el procesamiento
                # del tweet terminó sin excepciones.
                #
                # Incluso si:
                #
                # entidades detectadas = 0
                #
                # el tweet queda procesado.
                # =================================================

                cursor.execute(
                    """
                    UPDATE Tweets
                    SET entities_processed = 1
                    WHERE tweetid = %s
                    """,
                    (tweetid,)
                )

                # =================================================
                # 5.5 COMMIT DEL TWEET
                # =================================================

                conexion.commit()

                tweets_processed += 1

                print(
                    f"✅ Tweet {tweetid} procesado | "
                    f"detectadas={tweet_entities_count} | "
                    f"guardadas={tweet_saved} | "
                    f"descartadas={tweet_discarded}",
                    flush=True
                )

            except Exception as tweet_error:

                # =================================================
                # ERROR EN ESTE TWEET
                # =================================================
                #
                # Como hacemos rollback ANTES de haber hecho
                # commit, entities_processed seguirá en 0.
                #
                # Por lo tanto podrá volver a intentarse.
                # =================================================

                try:
                    conexion.rollback()
                except Exception:
                    pass

                errors += 1

                print(
                    f"❌ ERROR tweet {tweetid}: "
                    f"{tweet_error}",
                    flush=True
                )

                continue

        # =====================================================
        # 6. RESULTADO FINAL
        # =====================================================

        print(
            "\n" + "=" * 100,
            flush=True
        )

        print(
            "✅ PROCESAMIENTO TERMINADO",
            flush=True
        )

        print(
            f"Tweets procesados: {tweets_processed}",
            flush=True
        )

        print(
            f"Entidades detectadas: {entities_detected}",
            flush=True
        )

        print(
            f"Entidades guardadas: {entities_saved}",
            flush=True
        )

        print(
            f"Entidades descartadas: {entities_discarded}",
            flush=True
        )

        print(
            f"Errores: {errors}",
            flush=True
        )

        # =====================================================
        # 7. RESPONSE
        # =====================================================

        return jsonify({
            "status": "completed",
            "tweets_processed": tweets_processed,
            "entities_detected": entities_detected,
            "entities_saved": entities_saved,
            "entities_discarded": entities_discarded,
            "errors": errors
        }), 200

    except Exception as e:

        # =====================================================
        # ERROR GENERAL
        # =====================================================

        if conexion:

            try:
                conexion.rollback()
            except Exception:
                pass

        print(
            f"❌ Error general en spacy_entities_v2: {e}",
            flush=True
        )

        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

    finally:

        # =====================================================
        # 8. CERRAR CURSOR
        # =====================================================

        if cursor:

            try:
                cursor.close()

            except Exception as close_error:

                print(
                    f"⚠️ Error cerrando cursor: "
                    f"{close_error}",
                    flush=True
                )

        # =====================================================
        # 9. CERRAR CONEXIÓN
        # =====================================================

        if conexion:

            try:

                if conexion.is_connected():
                    conexion.close()

            except Exception as close_error:

                print(
                    f"⚠️ Error cerrando conexión: "
                    f"{close_error}",
                    flush=True
                )

        print(
            "🔒 Conexión cerrada.",
            flush=True
        )
if __name__ == "__main__":
    # Para desarrollo local (no producción)
    app.run(host="0.0.0.0", port=8080, debug=True)
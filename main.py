
import mysql.connector
from typing import List, Tuple
from mysql.connector import Error
from flask import Flask, jsonify
from spacyscript import get_entities
import os 
from spacyscript import get_entities_detailed, get_entities_detailed_gliner
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


    conexion = mysql.connector.connect(**db_config)
    cursor = conexion.cursor(dictionary=True)

    try:

        entity = {
            "text": "CONFEAGRO",
            "label": "ORG",
            "canonical_id": None,
            "detection_source": "ner",
        }

        resultado = resolve_entity(
            cursor,
            entity
        )

        print("RESULTADO:")
        print(resultado)
        print("RESULTADO RAW:", repr(resultado))
        print("TIPO:", type(resultado))

    finally:

        # IMPORTANTE:
        # esta prueba no debe guardar ningún cambio accidental
        conexion.rollback()

        cursor.close()
        conexion.close()
    return jsonify({"status": "completed"}), 200


    
@app.route("/spacy_entities_v2", methods=["GET"])
def spacy_entities_v2():

    conexion = None
    cursor = None

    # =========================================================
    # CONFIGURACIÓN
    # =========================================================

    BATCH_SIZE = 20

    # =========================================================
    # CONTADORES
    # =========================================================

    tweets_found = 0
    tweets_processed = 0

    entities_detected = 0
    entities_saved = 0
    entities_discarded = 0

    errors = 0

    failed_tweets = []

    try:

        # =====================================================
        # 1. CONEXIÓN
        # =====================================================

        conexion = mysql.connector.connect(**db_config)

        if not conexion.is_connected():

            return jsonify({
                "status": "error",
                "error": "No se pudo establecer conexión con MySQL"
            }), 500

        cursor = conexion.cursor(
            dictionary=True
        )

        print(
            "✅ Conexión exitosa a MySQL",
            flush=True
        )

        # =====================================================
        # 2. OBTENER TWEETS PENDIENTES
        # =====================================================
        #
        # entities_processed:
        #
        # 0 = pendiente
        # 1 = procesado correctamente
        #
        # Se usa esta columna como fuente de verdad.
        #
        # Un tweet puede tener:
        #
        # 0 entidades
        #
        # y aun así considerarse correctamente procesado.
        #
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
            ORDER BY
                t.created ASC,
                t.tweetid ASC
            LIMIT %s
        """

        cursor.execute(
            select_sql,
            (BATCH_SIZE,)
        )

        tweets = cursor.fetchall()

        tweets_found = len(tweets)

        # =====================================================
        # 3. NO HAY TWEETS PENDIENTES
        # =====================================================

        if not tweets:

            print(
                "✅ No hay tweets pendientes para procesar.",
                flush=True
            )

            return jsonify({
                "status": "completed",
                "tweets_found": 0,
                "tweets_processed": 0,
                "entities_detected": 0,
                "entities_saved": 0,
                "entities_discarded": 0,
                "errors": 0,
                "failed_tweets": []
            }), 200

        print(
            f"📄 Procesando {tweets_found} tweets...",
            flush=True
        )

        # =====================================================
        # 4. PROCESAR TWEETS
        # =====================================================

        for tweet in tweets:

            tweetid = tweet["tweetid"]
            text = tweet["text"]

            tweet_saved = 0
            tweet_discarded = 0

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
                # 4.1 GLINER + SPACY + ENTITY RULER
                # =================================================
                #
                # GLiNER:
                #     NER principal
                #
                # spaCy:
                #     tokenización
                #     POS
                #     dependencias
                #     lemas
                #
                # EntityRuler:
                #     entidades conocidas
                #     países
                #     reglas estructurales
                #
                # =================================================

                entidades = (
                    get_entities_detailed_gliner(
                        text
                    )
                )

                # =================================================
                # CONTAR ENTIDADES DETECTADAS
                # =================================================

                tweet_entities_count = sum(
                    len(lista)
                    for lista
                    in entidades.values()
                )

                entities_detected += (
                    tweet_entities_count
                )

                print(
                    f"🔎 Tweet {tweetid} | "
                    f"Detectadas={tweet_entities_count} | "
                    f"PER={len(entidades.get('PER', []))} | "
                    f"ORG={len(entidades.get('ORG', []))} | "
                    f"LOC={len(entidades.get('LOC', []))} | "
                    f"MISC={len(entidades.get('MISC', []))}",
                    flush=True
                )

                # =================================================
                # 4.2 ELIMINAR RELACIONES ANTERIORES
                # =================================================
                #
                # Importante:
                #
                # NO eliminamos:
                #
                # entities
                # entity_aliases
                #
                # Solo reconstruimos las relaciones de este tweet.
                #
                # =================================================

                cursor.execute(
                    """
                    DELETE FROM tweet_entities
                    WHERE tweetid = %s
                    """,
                    (tweetid,)
                )

                # =================================================
                # 4.3 RECORRER ENTIDADES
                # =================================================

                for detected_label, lista in (
                    entidades.items()
                ):

                    for entity in lista:

                        mention = entity.get(
                            "text"
                        )

                        entity_label = entity.get(
                            "label",
                            detected_label
                        )

                        canonical_id = entity.get(
                            "canonical_id"
                        )

                        detection_source = (
                            entity.get(
                                "detection_source",
                                "ner"
                            )
                        )

                        model_confidence = (
                            entity.get(
                                "model_confidence"
                            )
                        )

                        # =========================================
                        # DEBUG
                        # =========================================

                        print(
                            f"   🔹 Detectada | "
                            f"text={mention} | "
                            f"label={entity_label} | "
                            f"canonical={canonical_id} | "
                            f"detection={detection_source} | "
                            f"model_confidence={model_confidence}",
                            flush=True
                        )

                        # =========================================
                        # VALIDACIÓN BÁSICA
                        # =========================================

                        if not mention:

                            entities_discarded += 1
                            tweet_discarded += 1

                            print(
                                f"⏭️ Tweet {tweetid} | "
                                f"DESCARTADA | "
                                f"mention vacía",
                                flush=True
                            )

                            continue

                        # =========================================
                        # FILTRO DE CALIDAD
                        # =========================================
                        #
                        # Aquí desaparecen casos como:
                        #
                        # border
                        # El presidente
                        # my friend
                        # términos genéricos
                        #
                        # =========================================

                        if not should_resolve_entity(
                            entity,
                            text=text
                        ):

                            entities_discarded += 1
                            tweet_discarded += 1

                            print(
                                f"⏭️ Tweet {tweetid} | "
                                f"DESCARTADA | "
                                f"{mention} | "
                                f"{entity_label} | "
                                f"source={detection_source}",
                                flush=True
                            )

                            continue

                        # =========================================
                        # RESOLVER ENTIDAD
                        # =========================================
                        #
                        # resolve_entity:
                        #
                        # 1. canonical_id
                        # 2. alias conocido
                        # 3. correcciones de tipo
                        # 4. entidad existente
                        # 5. nueva entidad
                        #
                        # =========================================

                        resultado = resolve_entity(
                            cursor,
                            entity,
                            text=text
                        )

                        # =========================================
                        # ENTIDAD NO RESUELTA
                        # =========================================

                        if resultado is None:

                            entities_discarded += 1
                            tweet_discarded += 1

                            print(
                                f"⚠️ Tweet {tweetid} | "
                                f"NO RESUELTA | "
                                f"{mention} | "
                                f"{entity_label}",
                                flush=True
                            )

                            continue

                        # =========================================
                        # RESULTADO DEL RESOLVER
                        # =========================================

                        entity_id = resultado[
                            "entity_id"
                        ]

                        resolution_source = (
                            resultado[
                                "resolution_source"
                            ]
                        )

                        confidence = resultado.get(
                            "confidence"
                        )

                        # =========================================
                        # OBTENER TIPO CANÓNICO FINAL
                        # =========================================
                        #
                        # IMPORTANTE:
                        #
                        # resolve_entity() puede corregir:
                        #
                        # LOC -> PER
                        # LOC -> ORG
                        # etc.
                        #
                        # Por eso NO guardamos directamente:
                        #
                        # entity["label"]
                        #
                        # Consultamos la entidad finalmente
                        # resuelta.
                        #
                        # Ejemplo:
                        #
                        # Dockweiler:
                        #
                        # GLiNER => LOC
                        # resolver => PER
                        #
                        # tweet_entities debe guardar PER.
                        #
                        # =========================================

                        cursor.execute(
                            """
                            SELECT entity_type
                            FROM entities
                            WHERE id = %s
                            LIMIT 1
                            """,
                            (entity_id,)
                        )

                        resolved_entity = (
                            cursor.fetchone()
                        )

                        if (
                            resolved_entity
                            and resolved_entity.get(
                                "entity_type"
                            )
                        ):

                            final_entity_type = (
                                resolved_entity[
                                    "entity_type"
                                ]
                            )

                        else:

                            final_entity_type = (
                                entity_label
                            )

                        # =========================================
                        # OFFSETS
                        # =========================================

                        start_char = entity.get(
                            "start_char"
                        )

                        end_char = entity.get(
                            "end_char"
                        )

                        # =========================================
                        # GUARDAR TWEET -> ENTITY
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
                                mention,
                                final_entity_type,
                                start_char,
                                end_char,
                                detection_source,
                                resolution_source,
                                confidence
                            )
                        )

                        entities_saved += 1
                        tweet_saved += 1

                        print(
                            f"✅ Tweet {tweetid} | "
                            f"GUARDADA | "
                            f"{mention} | "
                            f"{final_entity_type} | "
                            f"entity_id={entity_id} | "
                            f"detection={detection_source} | "
                            f"resolution={resolution_source} | "
                            f"confidence={confidence}",
                            flush=True
                        )

                # =================================================
                # 4.4 MARCAR TWEET COMO PROCESADO
                # =================================================
                #
                # Se marca como procesado incluso si:
                #
                # - no se detectó ninguna entidad
                # - todas fueron descartadas
                #
                # porque el pipeline terminó correctamente.
                #
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
                # 4.5 COMMIT POR TWEET
                # =================================================
                #
                # Esto evita que un error posterior
                # revierta tweets ya procesados.
                #
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
                # ERROR EN TWEET
                # =================================================
                #
                # Revierte únicamente el tweet actual:
                #
                # - entidades nuevas
                # - aliases nuevos
                # - tweet_entities
                # - entities_processed
                #
                # entities_processed queda en 0
                # y podrá reintentarse.
                #
                # =================================================

                try:

                    if conexion:
                        conexion.rollback()

                except Exception:

                    pass

                errors += 1

                failed_tweets.append({
                    "tweetid": str(tweetid),
                    "error_type": (
                        type(tweet_error).__name__
                    ),
                    "error": str(tweet_error)
                })

                print(
                    "\n" + "!" * 100,
                    flush=True
                )

                print(
                    f"❌ ERROR tweet {tweetid}",
                    flush=True
                )

                print(
                    f"❌ "
                    f"{type(tweet_error).__name__}: "
                    f"{tweet_error}",
                    flush=True
                )

                print(
                    "!" * 100,
                    flush=True
                )

                continue

        # =====================================================
        # 5. RESULTADO FINAL
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
            f"Tweets encontrados: {tweets_found}",
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
        # 6. RESPONSE
        # =====================================================

        if errors == 0:

            status = "completed"

        elif tweets_processed > 0:

            status = "completed_with_errors"

        else:

            status = "error"

        return jsonify({
            "status": status,

            "model": "gliner",

            "tweets_found": tweets_found,

            "tweets_processed": (
                tweets_processed
            ),

            "entities_detected": (
                entities_detected
            ),

            "entities_saved": (
                entities_saved
            ),

            "entities_discarded": (
                entities_discarded
            ),

            "errors": errors,

            "failed_tweets": (
                failed_tweets
            )
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
            f"❌ Error general en "
            f"spacy_entities_v2: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        return jsonify({
            "status": "error",

            "model": "gliner",

            "error_type": (
                type(e).__name__
            ),

            "error": str(e)
        }), 500

    finally:

        # =====================================================
        # CERRAR CURSOR
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
        # CERRAR CONEXIÓN
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
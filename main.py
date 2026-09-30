
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
        
@app.route("/pruebas", methods=["GET"])
def pruebas():
   

    textos = [
        "YPFB anunció nuevas inversiones.",
        "Yacimientos Petrolíferos Fiscales Bolivianos presentó su informe.",

        "El TSE presentó el calendario electoral.",
        "El Tribunal Supremo Electoral emitió una resolución.",

        "Luis Arce participó de una reunión.",
        "Luis Arce presentó un informe.",

        "La reunión se realizó en La Paz.",
        "El evento ocurrió en La Paz."
    ]


    conexion = None
    cursor = None

    try:

        conexion = mysql.connector.connect(**db_config)

        cursor = conexion.cursor(dictionary=True)

        for texto in textos:

            print("\n" + "=" * 100)
            print("TEXTO:", texto)

            entidades = get_entities_detailed(texto)

            for label, lista in entidades.items():

                for entity in lista:

                    resultado = resolve_entity(
                        cursor,
                        entity
                    )

                    print(
                        entity["text"],
                        "|",
                        label,
                        "| canonical:",
                        entity["canonical_id"],
                        "| entity_id:",
                        resultado["entity_id"],
                        "| source:",
                        resultado["resolution_source"]
                    )

        # IMPORTANTE:
        # En esta prueba sí guardamos para poder revisar las tablas.
        conexion.commit()

        print("\n✅ PRUEBA TERMINADA")

    except Exception as e:

        if conexion:
            conexion.rollback()

        print("\n❌ ERROR:", e)

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()
    return "ok", 200

if __name__ == "__main__":
    # Para desarrollo local (no producción)
    app.run(host="0.0.0.0", port=8080, debug=True)
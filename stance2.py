import stance



def ejecutar_stance_topics_handler():
    # Primero calcula los targets de topicos que aún no los tengan.
    # Después clasifica comentarios pendientes por topico, sin filtro de fecha.
    def tarea():
        targets = stance.ejecutar_targets_topicos(
            limit=2,
            tweets_por_topico=20
        )

        comentarios = stance.ejecutar_stance_por_topico(
            max_comentarios=10,
            tamano_lote=10,
            max_topicos=2,
            max_publicaciones=3
        )

        print(f"Se han procesado {len(targets)} targets y {len(comentarios)} comentarios.")

    return stance.ejecutar_job_stance(
        "netvora_stance_topics",
        tarea
    )
    
    
if __name__ == "__main__":
    a = ejecutar_stance_topics_handler()
    print(f"Se han procesado {a} comentarios y targets de topicos.")

import os

import stance


def ejecutar_stance_topics_handler():
    def tarea():
        targets = stance.ejecutar_targets_topicos(
            limit=int(os.getenv("STANCE_MAX_TARGETS", "2")),
            tweets_por_topico=int(os.getenv("STANCE_TWEETS_POR_TOPICO", "20")),
        )
        comentarios = stance.ejecutar_stance_por_topico(
            max_comentarios=int(os.getenv("STANCE_MAX_COMENTARIOS", "10")),
            tamano_lote=int(os.getenv("STANCE_TAMANO_LOTE", "10")),
            max_topicos=int(os.getenv("STANCE_MAX_TOPICOS", "2")),
            max_publicaciones=int(os.getenv("STANCE_MAX_PUBLICACIONES", "3")),
        )
        return {
            "targets": targets,
            "comentarios": comentarios,
            "fallidos": targets["fallidos"] + comentarios["fallidos"],
        }

    return stance.ejecutar_job_stance("netvora_stance_topics", tarea)


if __name__ == "__main__":
    ejecutar_stance_topics_handler()

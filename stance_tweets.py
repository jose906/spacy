import os

from stance import ejecutar_job_stance, ejecutar_stance_por_target


def ejecutar_stance_por_target_handler():
    return ejecutar_job_stance(
        "netvora_stance_posts",
        lambda: ejecutar_stance_por_target(
            max_comentarios=int(os.getenv("STANCE_MAX_COMENTARIOS", "10")),
            tamano_lote=int(os.getenv("STANCE_TAMANO_LOTE", "10")),
            max_publicaciones=int(os.getenv("STANCE_MAX_PUBLICACIONES", "3")),
        ),
    )


if __name__ == "__main__":
    ejecutar_stance_por_target_handler()

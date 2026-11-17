
from stance import ejecutar_job_stance, ejecutar_stance_por_target
import json

def ejecutar_stance_por_target_handler():
    print("[STANCE] Ejecutando trabajo...", flush=True)
    
    resultado = ejecutar_job_stance(
                "netvora_stance_posts",
                lambda: ejecutar_stance_por_target(
                    max_comentarios=10,
                    tamano_lote=10,
                    max_publicaciones=3
                )
            )
    
    print(json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
                default=str
            ), flush=True)
    
    print("[STANCE] Trabajo finalizado", flush=True)
    



if __name__ == "__main__":
    
    
    ejecutar_stance_por_target_handler()
        
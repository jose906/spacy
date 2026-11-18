# Jobs de postura en Cloud Run

| Job | Módulo | Trabajo |
| --- | --- | --- |
| `netvora-stance-posts` | `stance_tweets` | Detecta el objetivo de cada publicación pendiente y clasifica sus comentarios. |
| `netvora-stance-topics` | `stance2` | Detecta objetivos de tópicos pendientes y clasifica comentarios respecto al tópico. |

Flask y ambos jobs usan la misma imagen, construida con `Dockerfile` y `requirements.txt`. La imagen inicia Gunicorn por defecto. Cloud Run configura cada job para ejecutar su módulo de Python. Ambos jobs usan una tarea y tienen un reintento. Cada uno usa su propio bloqueo de MySQL para evitar ejecuciones simultáneas del mismo job. El proceso registra los contadores en Cloud Logging y termina con error si Gemini o MySQL fallan o si faltan resultados para comentarios enviados. Las clasificaciones válidas se guardan por lote.

## Despliegue

Usa un proyecto con Cloud Run, Cloud Build, Artifact Registry, Cloud SQL y Secret Manager habilitados. El repositorio de Artifact Registry debe ser Docker y estar en la región indicada. Cloud Build requiere acceso de escritura al repositorio. La cuenta de servicio de los jobs necesita `roles/cloudsql.client` y acceso a las versiones de los dos secretos. El usuario MySQL debe tener permiso de lectura y escritura en las tablas de los jobs. El script conecta por el socket de Cloud SQL. Si la instancia solo admite IP privada, configura también la conectividad VPC de los jobs.

```bash
gcloud auth login
export PROJECT_ID='tweets-455721'
export REGION='REGION'
export ARTIFACT_REPOSITORY='REPOSITORIO_DOCKER'
export JOB_SERVICE_ACCOUNT='CUENTA@PROYECTO.iam.gserviceaccount.com'
export INSTANCE_CONNECTION_NAME='PROYECTO:REGION:INSTANCIA'
export DB_USER='USUARIO_MYSQL'
export DB_NAME='BASE_MYSQL'
export DB_PASS_SECRET='SECRETO_MYSQL:VERSION'
export GEMINI_API_KEY_SECRET='SECRETO_GEMINI:VERSION'
./deploy-stance-jobs.sh
```

Si ya publicaste la imagen del servicio con estos cambios, pasa su referencia al script para reutilizarla sin volver a compilar:

```bash
IMAGE='REGION-docker.pkg.dev/PROYECTO/REPOSITORIO/IMAGEN@sha256:DIGEST' ./deploy-stance-jobs.sh
```

Si el script construye una imagen, imprime su referencia para que puedas usarla también al desplegar Flask.

Ejecuta y verifica cada job con:

```bash
gcloud run jobs execute netvora-stance-posts --project="$PROJECT_ID" --region="$REGION" --wait
gcloud run jobs execute netvora-stance-topics --project="$PROJECT_ID" --region="$REGION" --wait
```

Ambos procesan primero los registros recientes. Los valores iniciales son 10 comentarios, lotes de hasta 10 y hasta 3 publicaciones por ejecución. En tópicos se procesan hasta 2 objetivos nuevos con hasta 20 publicaciones representativas cada uno y se revisan hasta 2 tópicos para comentarios. Puedes ajustar estos valores con `STANCE_MAX_COMENTARIOS`, `STANCE_TAMANO_LOTE`, `STANCE_MAX_PUBLICACIONES`, `STANCE_MAX_TARGETS`, `STANCE_TWEETS_POR_TOPICO` y `STANCE_MAX_TOPICOS`.

## Base de datos

El repositorio no contiene el esquema MySQL. Comprueba que existen las tablas y columnas que consulta `stance.py` y que hay claves únicas para `post_targets(tweetid)`, `reply_target_stance(replyid, post_target_id)` y `topic_reply_stance(replyid, topic_id)`. Esas claves hacen que los reintentos puedan guardar resultados de forma idempotente. Comprueba también los índices de `topic_tweets(topic_id, tweetid)` y `replies(tweetid, created, id)` antes de subir los límites. Usa `EXPLAIN` en Cloud SQL para medir las consultas con el esquema y los datos reales.

[Documentación de Cloud Run Jobs](https://docs.cloud.google.com/sdk/gcloud/reference/run/jobs/deploy)

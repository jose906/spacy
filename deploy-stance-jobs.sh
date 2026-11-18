#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Indica el proyecto de Google Cloud}"
: "${REGION:?Indica la región de Cloud Run}"
: "${JOB_SERVICE_ACCOUNT:?Indica la cuenta de servicio de los jobs}"
: "${INSTANCE_CONNECTION_NAME:?Indica la instancia de Cloud SQL como proyecto:region:instancia}"
: "${DB_USER:?Indica el usuario de MySQL}"
: "${DB_NAME:?Indica la base de datos}"
: "${DB_PASS_SECRET:?Indica el secreto y su versión como nombre:version}"
: "${GEMINI_API_KEY_SECRET:?Indica el secreto y su versión como nombre:version}"

image="${IMAGE:-}"
if [[ -z "$image" ]]; then
    : "${ARTIFACT_REPOSITORY:?Indica el repositorio Docker de Artifact Registry}"
    repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    build_dir="$(mktemp -d)"
    trap 'rm -rf -- "$build_dir"' EXIT

    cp "$repo_dir"/{Dockerfile,requirements.txt,main.py,app.py,embeddings.py,entity_patterns.py,entity_resolver.py,ner_gliner.py,spacyscript.py,stance.py,stance_tweets.py,stance2.py} "$build_dir/"

    tag="$(date -u +%Y%m%d%H%M%S)-$(basename "$build_dir" | tr '[:upper:]' '[:lower:]')"
    image="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPOSITORY}/netvora:${tag}"
    gcloud builds submit "$build_dir" --project="$PROJECT_ID" --tag="$image" --quiet
fi

printf 'Imagen compartida: %s\n' "$image"

deploy_job() {
    local job="$1"
    local module="$2"
    gcloud run jobs deploy "$job" \
        --project="$PROJECT_ID" --region="$REGION" --image="$image" \
        --command=python --args="-m,$module" --tasks=1 --parallelism=1 --max-retries=1 \
        --cpu=1 --memory=512Mi --task-timeout=15m \
        --service-account="$JOB_SERVICE_ACCOUNT" \
        --set-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
        --update-env-vars="INSTANCE_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME,DB_USER=$DB_USER,DB_NAME=$DB_NAME,GEMINI_MODEL=${GEMINI_MODEL:-gemini-3.8-flash}" \
        --update-secrets="DB_PASS=$DB_PASS_SECRET,GEMINI_API_KEY=$GEMINI_API_KEY_SECRET" \
        --quiet
}

deploy_job netvora-stance-posts stance_tweets
deploy_job netvora-stance-topics stance2

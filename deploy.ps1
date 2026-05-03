# ElectoGuide AI — Cloud Run Deployment Script (PowerShell)
# ============================================================
# Prerequisites:
#   1. gcloud CLI installed and initialised  (gcloud init)
#   2. Docker installed and running
#   3. gcloud auth login + gcloud auth configure-docker
#
# Usage:  .\deploy.ps1

$ErrorActionPreference = "Stop"

# ── Configuration ──────────────────────────────────────────────────────────────
$PROJECT_ID   = "promptwars-495214"
$REGION       = "us-central1"
$SERVICE_NAME = "electoguide-ai"
$IMAGE        = "gcr.io/$PROJECT_ID/$SERVICE_NAME"
$GEMINI_KEY   = $env:GEMINI_API_KEY  # Set this env var before running

if (-not $GEMINI_KEY) {
    Write-Error "GEMINI_API_KEY environment variable is not set. Run: `$env:GEMINI_API_KEY='your-key'"
    exit 1
}

Write-Host "`n>> ElectoGuide AI — Cloud Run Deployment" -ForegroundColor Cyan
Write-Host "   Project : $PROJECT_ID"
Write-Host "   Region  : $REGION"
Write-Host "   Service : $SERVICE_NAME`n"

# ── Step 1: Set active project ────────────────────────────────────────────────
Write-Host "1. Setting GCP project..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID

# ── Step 2: Enable required APIs ─────────────────────────────────────────────
Write-Host "2. Enabling required Cloud APIs..." -ForegroundColor Yellow
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    containerregistry.googleapis.com `
    firestore.googleapis.com `
    translate.googleapis.com `
    language.googleapis.com `
    texttospeech.googleapis.com `
    logging.googleapis.com `
    --project $PROJECT_ID

# ── Step 3: Build image via Cloud Build ──────────────────────────────────────
Write-Host "3. Building Docker image with Cloud Build..." -ForegroundColor Yellow
gcloud builds submit . `
    --tag $IMAGE `
    --project $PROJECT_ID

# ── Step 4: Deploy to Cloud Run ──────────────────────────────────────────────
Write-Host "4. Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --port 8080 `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars "GEMINI_API_KEY=$GEMINI_KEY,GEMINI_MODEL=gemini-3-flash-preview,GCP_PROJECT_ID=$PROJECT_ID,ENVIRONMENT=production" `
    --project $PROJECT_ID

# ── Step 5: Get service URL ───────────────────────────────────────────────────
Write-Host "`n5. Fetching service URL..." -ForegroundColor Yellow
$URL = gcloud run services describe $SERVICE_NAME `
    --platform managed `
    --region $REGION `
    --format "value(status.url)" `
    --project $PROJECT_ID

Write-Host "`n[OK] Deployment complete!" -ForegroundColor Green
Write-Host "   URL: $URL" -ForegroundColor Cyan
Write-Host "   Submit this URL in your competition form`n"

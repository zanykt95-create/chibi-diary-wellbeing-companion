#!/bin/bash
set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-chibi-diary-2306}"
IMAGE="gcr.io/${PROJECT_ID}/chibi-diary:latest"

echo "🐳 Building Docker image..."
docker build -t "$IMAGE" .

echo "📤 Pushing to Container Registry..."
docker push "$IMAGE"

echo "🚀 Deploying to Cloud Run..."
# NOTE: --allow-unauthenticated is intentional for the Kaggle demo so judges
# can access the live deployment without credentials.
# For a real production diary app, remove this flag and use IAM-based access:
#   gcloud run services add-iam-policy-binding chibi-diary \
#     --member="user:YOUR_EMAIL" --role="roles/run.invoker" --region=us-central1
gcloud run deploy chibi-diary \
  --image="$IMAGE" \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=1Gi \
  --port=8080 \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=True,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=us-central1" \
  --project="$PROJECT_ID"

echo "✅ Deployed! Check: gcloud run services describe chibi-diary --region=us-central1"

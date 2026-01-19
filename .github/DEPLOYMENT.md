# GitHub Actions Deployment Pipeline

This directory contains the GitHub Actions workflow for automated CI/CD deployment to Google Cloud Run.

## Pipeline Overview

The workflow ([deploy.yml](deploy.yml)) implements a complete CI/CD pipeline with:

### CI Stage (Test Job)
- **Code Quality Checks**: black, isort, autoflake, pylint (10/10 score required)
- **Unit Tests**: pytest with 100% coverage requirement
- **Security Scanning**: Trivy vulnerability scanner for Docker images
- **Parallel Execution**: All checks run concurrently for faster feedback

### CD Stage (Deploy Job)
- **Docker Build**: Multi-stage build optimized for production
- **Image Push**: Push to Google Artifact Registry with layer caching
- **Cloud Run Deployment**: Automated deployment with zero-downtime
- **Cost Controls**: Enforces disabled vulnerability scanning on Artifact Registry

## Required GitHub Secrets

**⚠️ All configuration comes from GitHub Secrets - no `.env` file needed in production**

Configure these secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

### GCP Authentication (Required)
| Secret | Description | Example |
|--------|-------------|---------|
| `GCP_SA_KEY` | Service Account JSON key | `{"type": "service_account", ...}` |
| `GCP_PROJECT_ID` | Your Google Cloud Project ID | `my-project-12345` |

### Application Configuration (Required)
| Secret | Description | Example |
|--------|-------------|---------|
| `PORT` | Application port | `3000` |
| `API_KEY` | API key for X-API-Key authentication | `sk_live_abc123...` (min 32 chars recommended) |
| `ENDPOINTS` | JSON array of endpoints (supports ${VAR_NAME} templates) | See examples below |### Email Notifications (Optional)
| Secret | Description | Example |
|--------|-------------|---------||
| `EMAIL_ADDRESS` | Gmail address for SMTP (sender and recipient) | `your-email@gmail.com` |
| `SMTP_PASSWORD` | Gmail App Password (16 chars, no spaces) | `abcdefghijklmnop` |
| `SMTP_HOST` | SMTP server host (optional, default: smtp.gmail.com) | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port (optional, default: 587) | `587` |

**Email Setup** (if using `send_email: true` in requests):
1. Enable 2-Step Verification in your Google Account
2. Generate App Password at [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Configure `EMAIL_ADDRESS` and `SMTP_PASSWORD` secrets
4. Email notifications include HTML reports with JSON attachments for each endpoint result

### Template Variables (Optional)
| Secret | Description | Example |
|--------|-------------|---------|
| `ENDPOINT_API_KEY` | API token for external services | `sk_test_abc123...` |
| `EXTERNAL_SERVICE_TOKEN` | Token for external services | `bearer_xyz789...` |
| `DATABASE_PASSWORD` | Database credentials | `super_secret_pwd` |
| *(Add more as needed)* | Any secret referenced in ENDPOINTS | Use `${VAR_NAME}` syntax |

**ENDPOINTS Configuration Format**:

Supports three formats:
1. **Simple URLs**: `["https://api.example.com/task1", "https://api.example.com/task2"]`
2. **Full objects**: `{"url": "...", "method": "POST", "headers": {...}, "json": {...}, "timeout": 30}`
3. **Template variables** (RECOMMENDED): `{"url": "...", "headers": {"Authorization": "Bearer ${ENDPOINT_API_KEY}"}}`

<details>
<summary><b>📖 View ENDPOINTS examples</b></summary>

**🔐 With Template Variables (RECOMMENDED)**:
```json
[
  {
    "url": "https://api.domain.com/sync",
    "method": "POST",
    "headers": {"Authorization": "Bearer ${ENDPOINT_API_KEY}"}
  },
  {
    "url": "https://external-api.example.com/data",
    "method": "GET",
    "headers": {"X-API-Key": "${EXTERNAL_SERVICE_TOKEN}"}
  }
]
```

**Mixed format**:
```json
[
  "https://api.example.com/simple",
  {
    "url": "https://api.example.com/complex",
    "method": "POST",
    "headers": {"X-API-Key": "${EXTERNAL_SERVICE_TOKEN}"},
    "json": {"action": "process"}
  }
]
```
</details>

## Service Account Permissions

The Service Account used by `GCP_SA_KEY` must have the following IAM roles:

```bash
# Required roles
roles/run.admin                    # Deploy and manage Cloud Run services
roles/iam.serviceAccountUser       # Act as Cloud Run runtime service account
roles/artifactregistry.writer      # Push Docker images to Artifact Registry
```

### Creating the Service Account

```bash
# Set variables
export PROJECT_ID="your-project-id"
export SA_NAME="github-actions-deployer"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account
gcloud iam service-accounts create $SA_NAME \
  --display-name="GitHub Actions Deployer" \
  --project=$PROJECT_ID

# Grant required roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"

# Create and download JSON key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=$SA_EMAIL \
  --project=$PROJECT_ID

# Copy the contents of github-actions-key.json to GCP_SA_KEY secret
cat github-actions-key.json
```

## One-Time GCP Setup

Before the first deployment, run these commands in Google Cloud Shell:

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export REPO="gcp-scheduler-runner"

# Create Artifact Registry repository
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for gcp-scheduler-runner service" \
  --project=$PROJECT_ID

# Disable vulnerability scanning (cost control)
gcloud artifacts repositories update $REPO \
  --location=$REGION \
  --disable-vulnerability-scanning \
  --project=$PROJECT_ID

# Verify scanning is disabled
gcloud artifacts repositories describe $REPO \
  --location=$REGION \
  --format="value(vulnerabilityScanningConfig.enablementConfig)" \
  --project=$PROJECT_ID
```

## Local Testing

Test the Docker build locally before pushing:

```bash
# Build image
docker build -t gcp-scheduler-runner:local .

# Run container (without email)
docker run -p 3000:3000 \
  -e ENDPOINTS='["http://example.com/api"]' \
  -e API_KEY='your_api_key_here' \
  gcp-scheduler-runner:local

# Run container (with email notifications)
docker run -p 3000:3000 \
  -e ENDPOINTS='["http://example.com/api"]' \
  -e API_KEY='your_api_key_here' \
  -e EMAIL_ADDRESS='your-email@gmail.com' \
  -e SMTP_PASSWORD='your_app_password' \
  gcp-scheduler-runner:local

# Test endpoints
curl http://localhost:3000/health
curl -X POST http://localhost:3000/execute -H "X-API-Key: your_api_key_here"
```

## Deployment

### Workflow Triggers

The pipeline runs on:
- **Push to main branch**: Automatic deployment on every commit to `main`
- **Manual trigger**: Via GitHub Actions UI (`Actions > Deploy to Cloud Run > Run workflow`)

### Monitoring Deployment

**View Deployment Status**:
1. Go to `Actions` tab in GitHub repository
2. Click on the latest workflow run
3. Monitor both `test` and `deploy` jobs

**Access Deployed Service**:
After successful deployment, the service URL is printed in the deploy job output:
```
✅ Service deployed to: https://gcp-scheduler-runner-xxx-uc.a.run.app
```

**View Cloud Run Logs**:
```bash
gcloud run services logs read gcp-scheduler-runner \
  --region=us-central1 \
  --project=your-project-id \
  --limit=50
```

## Cloud Scheduler Integration

The service can be invoked by Google Cloud Scheduler for automated periodic execution.

### Scheduler-Specific Features

**Detection Header**: Cloud Scheduler jobs should include `X-Scheduler-Trigger: true` header:
- Enables automatic execution context detection
- Improves email notification formatting (shows "Scheduled Execution" context)
- Distinguishes scheduled runs from manual API calls in logs

**Example Cloud Scheduler Job** (with email notifications):
```bash
gcloud scheduler jobs create http gcp-scheduler-runner-daily \
  --location=us-central1 \
  --schedule="30 4 * * *" \
  --uri="https://YOUR-SERVICE-URL.run.app/execute" \
  --http-method=POST \
  --headers="Content-Type=application/json,X-API-Key=YOUR_API_KEY,X-Scheduler-Trigger=true" \
  --message-body='{
    "parallel": true,
    "max_workers": 10,
    "send_email": true
  }' \
  --attempt-deadline=300s \
  --max-retry-attempts=3 \
  --description="Daily execution with parallel mode and email notifications"
```

**Request Parameters**:
- `parallel` (boolean, default: `true`): Enable parallel endpoint execution
- `max_workers` (integer, default: 10): Maximum concurrent workers
- `send_email` (boolean, default: `false`): Send HTML email report with JSON attachments

**Notes**:
- Email notifications are **optional** - only sent if `send_email: true`
- If email secrets not configured, execution continues without email
- Cloud Scheduler uses **UTC timezone** - convert your local time accordingly
- The `X-Scheduler-Trigger` header is optional but recommended for better observability

## Troubleshooting

### Test Job Fails
- **Code quality issues**: Run `bash envtool.sh code-check` locally and fix reported issues
- **Test failures**: Run `bash envtool.sh test` locally to debug
- **Coverage issues**: Ensure all code paths are covered by tests

### Deploy Job Fails
- **Repository not found**: Run the one-time GCP setup commands above
- **Vulnerability scanning enabled**: Follow error message instructions to disable scanning
- **Permission denied**: Verify service account has required IAM roles
- **Invalid credentials**: Regenerate `GCP_SA_KEY` secret

### Service Not Responding
- Check Cloud Run logs for runtime errors
- Verify `ENDPOINTS` secret is correctly configured
- Test locally with `bash envtool.sh start`

### Email Notifications Not Working
- Verify `EMAIL_ADDRESS` and `SMTP_PASSWORD` secrets are configured
- Ensure you're using Gmail App Password (not regular password)
- Check that 2-Step Verification is enabled in Google Account
- Verify `send_email: true` is included in the request body
- Check Cloud Run logs for SMTP connection errors

## Advanced Topics

### Security Features

**Trivy Vulnerability Scanning**:
- Scans Docker images for vulnerabilities before deployment
- Generates multiple report formats: SARIF, JSON, Table
- Uploads results to GitHub Security tab
- Blocks deployment if critical vulnerabilities found
- Can be disabled by setting `TRIVY_ENABLED: "false"` in [deploy.yml](deploy.yml)

**Cost Controls**:
- **Artifact Registry scanning disabled**: Prevents ~$5/month scanning charges
- **Short SHA tags**: Reduces storage costs by using bounded image tags
- **Layer caching**: Reduces build time and bandwidth costs

**Non-root Container**:
- Application runs as unprivileged user `appuser` (UID 1000)
- Follows least-privilege security principle
- Reduces attack surface

### Performance Optimizations

- **Python dependency caching**: ~2-3 min saved per run
- **Docker layer caching**: ~1-2 min saved per build
- **Parallel job execution**: CI and CD stages run independently
- **BuildKit**: Modern Docker builder for faster builds
- **Minimal base image**: Alpine Linux (~50MB vs ~150MB Debian)

### Migration to Workload Identity Federation

Consider migrating from Service Account keys to Workload Identity Federation for improved security:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_NAME/providers/PROVIDER_NAME'
    service_account: 'SERVICE_ACCOUNT_EMAIL'
```

Benefits:
- No long-lived credentials stored in GitHub
- Automatic token rotation
- Better audit trail

## References

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Trivy Security Scanner](https://aquasecurity.github.io/trivy/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

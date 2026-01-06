# Google Cloud Scheduler Setup

This guide explains how to configure Google Cloud Scheduler to periodically trigger the deployed Flask service on Cloud Run.

## 🎯 What Cloud Scheduler Executes

**Endpoint**: `/execute` (POST or GET)
- **Full URL**: `https://gcp-scheduler-runner-xxx-uc.a.run.app/execute`
- **Method**: POST (recommended) or GET
- **Purpose**: Orchestrates execution of all configured endpoints in parallel or sequential mode

**⏰ Timezone**: **UTC (Coordinated Universal Time)**
- All Cloud Scheduler cron expressions use **UTC timezone** only
- You must convert your local time to UTC when configuring schedules
- This is a GCP limitation - Cloud Scheduler does not support other timezones
- Example: 9:00 AM EST (UTC-5) = 14:00 UTC (2:00 PM UTC)
- Example: 9:00 AM PDT (UTC-7) = 16:00 UTC (4:00 PM UTC)

## Overview

Once the service is deployed to Cloud Run via GitHub Actions, you can set up Cloud Scheduler to invoke the `/execute` endpoint at scheduled intervals (e.g., every hour, daily, weekly).

## Prerequisites

- Service successfully deployed to Cloud Run
- Cloud Scheduler API enabled in your GCP project
- `gcloud` CLI configured with your project
- `API_KEY` configured as GitHub Secret and deployed to Cloud Run

## Enable Cloud Scheduler API

```bash
gcloud services enable cloudscheduler.googleapis.com --project=YOUR_PROJECT_ID
```

## Create a Scheduler Job

**⚠️ Important**: All requests must include the `X-API-Key` header with your configured API key.

### Basic Configuration (POST Request with Authentication)

```bash
gcloud scheduler jobs create http gcp-scheduler-runner-job \
  --location=us-central1 \
  --schedule="0 */6 * * *" \
  --uri="https://gcp-scheduler-runner-xxx-uc.a.run.app/execute" \
  --http-method=POST \
  --headers="Content-Type=application/json,X-API-Key=YOUR_API_KEY_HERE,X-Scheduler-Trigger=true" \
  --attempt-deadline=300s \
  --description="Execute configured endpoints every 6 hours" \
  --project=YOUR_PROJECT_ID
```

### With Custom Endpoints (POST Request with Body)

```bash
gcloud scheduler jobs create http gcp-scheduler-runner-job \
  --location=us-central1 \
  --schedule="0 9 * * 1-5" \
  --uri="https://gcp-scheduler-runner-xxx-uc.a.run.app/execute" \
  --http-method=POST \
  --message-body='{"endpoints": ["http://example.com/api1", "http://example.com/api2"], "parallel": true, "max_workers": 5}' \
  --headers="Content-Type=application/json,X-API-Key=YOUR_API_KEY_HERE,X-Scheduler-Trigger=true" \
  --attempt-deadline=300s \
  --description="Execute custom endpoints weekdays at 9 AM" \
  --project=YOUR_PROJECT_ID
```

### With OIDC Authentication (Recommended for Production)

For services that require authentication:

```bash
# Create service account for Cloud Scheduler
gcloud iam service-accounts create cloud-scheduler-invoker \
  --display-name="Cloud Scheduler Service Invoker" \
  --project=YOUR_PROJECT_ID

# Grant permission to invoke Cloud Run service
gcloud run services add-iam-policy-binding gcp-scheduler-runner \
  --member="serviceAccount:cloud-scheduler-invoker@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=us-central1 \
  --project=YOUR_PROJECT_ID

# Create scheduler job with OIDC auth
gcloud scheduler jobs create http gcp-scheduler-runner-job \
  --location=us-central1 \
  --schedule="0 */6 * * *" \
  --uri="https://gcp-scheduler-runner-xxx-uc.a.run.app/execute" \
  --http-method=POST \
  --oidc-service-account-email="cloud-scheduler-invoker@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --oidc-token-audience="https://gcp-scheduler-runner-xxx-uc.a.run.app" \
  --attempt-deadline=300s \
  --description="Execute endpoints with authentication" \
  --project=YOUR_PROJECT_ID
```

## Schedule Format (Cron Expression)

**⚠️ IMPORTANT**: All schedules use **UTC timezone** (not your local timezone)

Cloud Scheduler uses Unix cron format:

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23) ⚠️ UTC HOURS
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6, Sunday = 0)
│ │ │ │ │
* * * * *
```

### Timezone Conversion Reference

| Your Local Time | Timezone | UTC Time | Cron Hour |
|----------------|----------|----------|------------|
| 9:00 AM | EST (UTC-5) | 2:00 PM | `14` |
| 9:00 AM | PST (UTC-8) | 5:00 PM | `17` |
| 9:00 AM | CST (UTC-6) | 3:00 PM | `15` |
| 9:00 AM | MST (UTC-7) | 4:00 PM | `16` |
| 6:00 PM | EST (UTC-5) | 11:00 PM | `23` |
| 6:00 PM | PST (UTC-8) | 2:00 AM (next day) | `2` |

**Conversion Formula**: UTC Hour = (Local Hour + UTC Offset) % 24

**Quick Converter**: Use [worldtimebuddy.com](https://www.worldtimebuddy.com/) or:
```bash
# Linux/macOS: Convert current time to UTC
date -u

# Linux: Convert specific time to UTC
TZ='America/New_York' date -d '9:00 AM' -u '+%H:%M UTC'
```

### Common Schedule Examples

**⚠️ All times are in UTC**

```bash
# Every 15 minutes
--schedule="*/15 * * * *"

# Every hour at minute 0
--schedule="0 * * * *"

# Every 6 hours (starting at UTC midnight: 00:00, 06:00, 12:00, 18:00)
--schedule="0 */6 * * *"

# Daily at 2:30 AM UTC
--schedule="30 2 * * *"

# Every weekday (Mon-Fri) at 9:00 AM UTC
--schedule="0 9 * * 1-5"

# Every weekday (Mon-Fri) at 9:00 AM EST (14:00 UTC)
--schedule="0 14 * * 1-5"

# Every weekday (Mon-Fri) at 9:00 AM PST (17:00 UTC)
--schedule="0 17 * * 1-5"

# First day of every month at midnight UTC
--schedule="0 0 1 * *"

# Every Sunday at 3:00 PM UTC
--schedule="0 15 * * 0"

# Every day at 6:00 PM EST (23:00 UTC same day)
--schedule="0 23 * * *"

# Every day at 6:00 PM PST (02:00 UTC next day)
--schedule="0 2 * * *"
```

## Managing Scheduler Jobs

### List all jobs
```bash
gcloud scheduler jobs list --location=us-central1 --project=YOUR_PROJECT_ID
```

### Describe a job
```bash
gcloud scheduler jobs describe gcp-scheduler-runner-job \
  --location=us-central1 \
  --project=YOUR_PROJECT_ID
```

### Update job schedule
```bash
gcloud scheduler jobs update http gcp-scheduler-runner-job \
  --location=us-central1 \
  --schedule="0 */12 * * *" \
  --project=YOUR_PROJECT_ID
```

### Update job URI (after redeployment)
```bash
gcloud scheduler jobs update http gcp-scheduler-runner-job \
  --location=us-central1 \
  --uri="https://NEW-SERVICE-URL.run.app/execute" \
  --project=YOUR_PROJECT_ID
```

### Pause a job
```bash
gcloud scheduler jobs pause gcp-scheduler-runner-job \
  --location=us-central1 \
  --project=YOUR_PROJECT_ID
```

### Resume a job
```bash
gcloud scheduler jobs resume gcp-scheduler-runner-job \
  --location=us-central1 \
  --project=YOUR_PROJECT_ID
```

### Delete a job
```bash
gcloud scheduler jobs delete gcp-scheduler-runner-job \
  --location=us-central1 \
  --project=YOUR_PROJECT_ID
```

### Manually trigger a job (for testing)
```bash
gcloud scheduler jobs run gcp-scheduler-runner-job \
  --location=us-central1 \
  --project=YOUR_PROJECT_ID
```

## Monitoring and Logs

### View job execution history
```bash
gcloud scheduler jobs describe gcp-scheduler-runner-job \
  --location=us-central1 \
  --format="table(status.lastAttemptTime, status.state)" \
  --project=YOUR_PROJECT_ID
```

### View Cloud Run service logs
```bash
gcloud run services logs read gcp-scheduler-runner \
  --region=us-central1 \
  --limit=50 \
  --project=YOUR_PROJECT_ID
```

### View Cloud Scheduler logs (in Cloud Console)
1. Go to: [Cloud Console > Logs Explorer](https://console.cloud.google.com/logs)
2. Filter by:
   ```
   resource.type="cloud_scheduler_job"
   resource.labels.job_id="gcp-scheduler-runner-job"
   ```

## Error Handling and Retries

Cloud Scheduler automatically retries failed jobs with exponential backoff:

```bash
# Configure retry settings
gcloud scheduler jobs update http gcp-scheduler-runner-job \
  --location=us-central1 \
  --max-retry-attempts=3 \
  --max-retry-duration=600s \
  --min=5s \
  --max=60s \
  --max-doublings=3 \
  --project=YOUR_PROJECT_ID
```

## Cost Estimation

Cloud Scheduler pricing (as of 2024):
- **First 3 jobs per month**: Free
- **Additional jobs**: $0.10 per job per month
- **Free tier**: 3 jobs/month at no charge

For this setup with 1 job:
- **Cost**: $0/month (within free tier)

Cloud Run pricing:
- **Request charges**: Based on number of executions
- **Compute time**: Based on execution duration
- **No charges when idle** (scales to zero)

Example: 4 executions per day (every 6 hours)
- ~120 requests/month
- Well within free tier (2M requests/month free)

## Security Best Practices

1. **Use OIDC authentication**: Prevents unauthorized invocations
2. **Restrict Cloud Run access**: Remove `--allow-unauthenticated` flag and use IAM
3. **Use Secret Manager**: Store sensitive endpoint configurations
4. **Enable Cloud Audit Logs**: Track all scheduler invocations
5. **Set attempt deadlines**: Prevent runaway executions

## Troubleshooting

### Job fails with "Permission Denied"
- Verify service account has `roles/run.invoker` on Cloud Run service
- Check OIDC audience matches the service URL

### Job times out
- Increase `--attempt-deadline` (max 1800s = 30 minutes)
- Optimize endpoint execution time
- Consider sequential execution for long-running tasks

### Job doesn't execute
- Verify job is not paused: `gcloud scheduler jobs describe ...`
- Check cron schedule syntax
- Manually trigger job to test: `gcloud scheduler jobs run ...`

### Endpoints fail to execute
- Check Cloud Run service logs for errors
- Verify `ENDPOINTS` environment variable is set correctly
- Test endpoints manually with curl

## Example: Complete Setup Script

```bash
#!/bin/bash

# Configuration
PROJECT_ID="your-project-id"
REGION="us-central1"
SERVICE_URL="https://gcp-scheduler-runner-xxx-uc.a.run.app"

# Enable API
echo "Enabling Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com --project=$PROJECT_ID

# Create service account
echo "Creating service account..."
gcloud iam service-accounts create cloud-scheduler-invoker \
  --display-name="Cloud Scheduler Service Invoker" \
  --project=$PROJECT_ID

# Grant permissions
echo "Granting permissions..."
gcloud run services add-iam-policy-binding gcp-scheduler-runner \
  --member="serviceAccount:cloud-scheduler-invoker@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=$REGION \
  --project=$PROJECT_ID

# Create scheduler job
echo "Creating scheduler job..."
gcloud scheduler jobs create http gcp-scheduler-runner-job \
  --location=$REGION \
  --schedule="0 */6 * * *" \
  --uri="${SERVICE_URL}/execute" \
  --http-method=POST \
  --oidc-service-account-email="cloud-scheduler-invoker@${PROJECT_ID}.iam.gserviceaccount.com" \
  --oidc-token-audience="${SERVICE_URL}" \
  --attempt-deadline=300s \
  --description="Execute endpoints every 6 hours" \
  --project=$PROJECT_ID

echo "✅ Setup complete!"
echo "Test the job with: gcloud scheduler jobs run gcp-scheduler-runner-job --location=$REGION --project=$PROJECT_ID"
```

## References

- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [Cron Expression Reference](https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules)
- [Cloud Run Authentication](https://cloud.google.com/run/docs/authenticating/overview)

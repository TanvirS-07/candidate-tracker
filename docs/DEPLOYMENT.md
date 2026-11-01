# Deployment design (AWS, one page)

Not deployed; this is how I would run it for a small team.

```
Browser ─► CloudFront ─┬─ /*      ─► S3 (React build)
                       └─ /api/*  ─► App Runner (FastAPI container, from ECR)
                                          │  VPC connector
                                          ├─► RDS PostgreSQL (private subnet)
                                          ├─► Secrets Manager (ANTHROPIC_API_KEY, DB password)
                                          └─► NAT gateway ─► Anthropic API (outbound HTTPS)
        CloudWatch Logs + alarms on 5xx and summary failures
```

| Component | Service | Why |
|---|---|---|
| Frontend | S3 + CloudFront | Static build, cheap, HTTPS and caching built in. A second CloudFront behaviour sends `/api/*` to App Runner, so the browser sees one origin, just like the Vite proxy in development, and no CORS change is needed |
| API | App Runner (ECR image) | Container with no cluster to manage; autoscaling and TLS included. It needs a **VPC connector** to reach the private RDS, and once connected, all its outbound traffic goes through the VPC, so calling the Anthropic API needs a **NAT gateway** |
| Database | RDS PostgreSQL `db.t4g.micro`, single-AZ | Replaces SQLite; automated backups. Multi-AZ once real data lives there |
| Secrets | Secrets Manager | API key never in the image or repo |
| CI/CD | GitHub Actions → ECR → App Runner | Runs the tests, builds the image, deploys on main |
| Observability | CloudWatch | Logs, 5xx alarm, alarm on repeated 502s from the AI service |

**Security notes:** the app has no auth yet, so it must sit behind SSO (CloudFront + Cognito or the company IdP) before real candidate data goes in. Resume text is personal data: encrypt RDS at rest, keep the AI provider's data-retention terms in view, and do not log resume text.

**Rough monthly cost (small team, light use; estimates, check the AWS pricing calculator):**

| Item | USD / month |
|---|---|
| App Runner (1 small instance, mostly idle) | 5 – 15 |
| RDS `db.t4g.micro` + 20 GB storage | 15 – 20 |
| NAT gateway (one AZ, hourly charge + light data) | 35 – 45 |
| S3 + CloudFront | 1 – 3 |
| Secrets Manager, CloudWatch, ECR | 3 – 8 |
| Anthropic API (a few thousand summaries on the small model tier) | 1 – 10 |
| **Total** | **~60 – 100** |

The NAT gateway is the biggest single item, and it exists only so the API can reach both a private database and the internet. If cost mattered more than the managed service, ECS Fargate in a public subnet (with a security group allowing only it to reach RDS) avoids the NAT. The other levers are RDS (a free-tier or stopped dev instance for staging) and AI usage (summaries are generated on click and stored, so each resume is summarised once unless regenerated).

# Render.com Quick Reference

## 🔑 Your Credentials

**API Key:** `rnd_1qYdkGuHRHGB13aorQUdxwaE9GE2`
**Dashboard:** https://dashboard.render.com/blueprint/exs-d3tq77ndiees73dp43p0
**Live Site:** https://rugdetector.ai

---

## 🚀 Quick Actions

### Open Dashboard
```bash
# Direct link
open https://dashboard.render.com/blueprint/exs-d3tq77ndiees73dp43p0

# Or use helper script
./render-helper.sh
```

### Check Deployment Status
```bash
curl -H "Authorization: Bearer rnd_1qYdkGuHRHGB13aorQUdxwaE9GE2" \
  https://api.render.com/v1/services | jq '.[] | select(.name=="rugdetector")'
```

### View Logs
```bash
# Install Render CLI (one time)
npm install -g render

# View logs
render logs -s rugdetector --tail 100
```

### Check Health
```bash
curl https://rugdetector.ai/health | jq '.'
```

---

## 📋 Deployment Workflow

### Automatic Deployment (Default)
1. Push to GitHub: `git push`
2. Render auto-detects changes
3. Builds Docker image
4. Runs health checks
5. Deploys new version
6. **Time:** 3-5 minutes

### Manual Deployment
1. Open dashboard: https://dashboard.render.com/blueprint/exs-d3tq77ndiees73dp43p0
2. Click "Manual Deploy" button
3. Select branch to deploy
4. Click "Deploy"

---

## 🔧 Render CLI Installation

```bash
# Install globally
npm install -g render

# Login with API key
render login --api-key rnd_1qYdkGuHRHGB13aorQUdxwaE9GE2

# Common commands
render services list                    # List all services
render logs -s rugdetector             # View logs
render deploy -s rugdetector           # Manual deploy
render open -s rugdetector             # Open in browser
render env -s rugdetector              # View env vars
```

---

## 📊 Monitoring

### Health Check Endpoint
```bash
curl https://rugdetector.ai/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-24T...",
  "uptime": 12345
}
```

### Service Discovery
```bash
curl https://rugdetector.ai/.well-known/ai-service.json | jq '.'
```

### Test X402 Compliance
```bash
curl -i https://rugdetector.ai/check \
  -H "Content-Type: application/json" \
  -d '{"contract_address":"0x1234567890123456789012345678901234567890"}'
```

**Should return:** HTTP 402 with `X-PAYMENT-RESPONSE` header

---

## 🛠️ Troubleshooting

### Build Fails
1. Check logs in dashboard
2. Verify Dockerfile is correct
3. Check if all dependencies are in requirements.txt and package.json

### Health Check Fails
1. Verify `/health` endpoint works locally
2. Check if port 3000 is exposed in Dockerfile
3. Review environment variables

### Deployment Stuck
1. Check build logs for errors
2. Verify Docker image size (should be < 2GB)
3. Check Render status page: https://status.render.com

### Site Not Updating
1. Verify commit was pushed to GitHub
2. Check auto-deploy is enabled in Render
3. Manually trigger deploy if needed

---

## 🔐 Environment Variables

To update environment variables:

1. Go to dashboard
2. Click "Environment" tab
3. Add/edit variables
4. Click "Save Changes"
5. Render will auto-redeploy

**Important variables:**
- `NODE_ENV=production`
- `PORT=3000`
- `PAYMENT_ADDRESS=0xYour...`
- `BASE_RPC_URL=https://mainnet.base.org`

---

## 📁 Project Structure

```
rugdetector/
├── Dockerfile              # Container definition
├── render.yaml            # Render blueprint
├── .render-config         # Your credentials (gitignored)
├── render-helper.sh       # Quick helper script
├── api/                   # Node.js backend
├── ui/                    # Frontend files
├── model/                 # Python ML model
└── public/.well-known/    # Service discovery
```

---

## 🚦 Deployment Checklist

Before deploying:
- [ ] Code changes committed to git
- [ ] Tests pass locally
- [ ] Environment variables configured
- [ ] Dockerfile builds successfully
- [ ] Health check endpoint works

After deploying:
- [ ] Check deployment status in dashboard
- [ ] Verify health check returns 200
- [ ] Test API endpoints
- [ ] Check logs for errors
- [ ] Verify X402 compliance

---

## 📞 Support

**Render Support:**
- Email: support@render.com
- Docs: https://render.com/docs
- Community: https://community.render.com

**Render Status:**
- https://status.render.com

---

## 💡 Pro Tips

1. **Use the helper script:** `./render-helper.sh` for quick access to common tasks
2. **Monitor logs:** Set up log drains for production monitoring
3. **Enable notifications:** Get Slack/email alerts for deployments
4. **Use preview environments:** Test changes before production
5. **Set up custom domain:** Already done! (rugdetector.ai)

---

## 📝 Quick Commands Cheat Sheet

```bash
# Helper script (easiest)
./render-helper.sh

# Direct dashboard access
open https://dashboard.render.com/blueprint/exs-d3tq77ndiees73dp43p0

# Check health
curl https://rugdetector.ai/health

# View service info
curl -H "Authorization: Bearer rnd_1qYdkGuHRHGB13aorQUdxwaE9GE2" \
  https://api.render.com/v1/services | jq '.'

# Test X402
curl -i https://rugdetector.ai/check \
  -H "Content-Type: application/json" \
  -d '{"contract_address":"0x1234567890123456789012345678901234567890"}'
```

---

**Last Updated:** 2025-10-24
**Service:** RugDetector
**Region:** Oregon
**Runtime:** Docker

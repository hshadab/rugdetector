# Railway Deployment Fix

## Issue

Railway detected Python instead of Node.js because of `requirements.txt` file.

## Solution

I've created **3 configuration files** to force Railway to use Node.js:

### 1. `Procfile` (Simplest - Recommended)
```
web: node api/server.js
```
This tells Railway explicitly what command to run.

### 2. `nixpacks.toml` (Advanced)
Forces Railway to install both Node.js and Python, then start with Node.js.

### 3. `Dockerfile` (Most Control)
Complete containerization - Railway will use this if it detects it.

---

## Quick Fix Steps

### Option A: Use Settings (Fastest)

1. Go to your Railway project
2. Click **Settings** tab
3. Find **Start Command** field
4. Enter: `node api/server.js`
5. Click **Deploy**

### Option B: Re-deploy with Procfile (Recommended)

1. Commit the new files:
   ```bash
   git add Procfile nixpacks.toml
   git commit -m "Fix Railway deployment - add Procfile"
   git push
   ```

2. Railway will auto-deploy and detect the Procfile
3. It should now start correctly!

### Option C: Force Docker Build

In Railway dashboard:
1. Settings → **Build**
2. Set **Builder** to **Dockerfile**
3. Click **Deploy**

---

## What Each File Does

- **Procfile**: Tells Railway the start command (like Heroku)
- **nixpacks.toml**: Configures Railway's Nixpacks builder to use Node.js + Python
- **Dockerfile**: Complete container build (most reliable)

---

## Recommended Approach

**Best**: Use the **Settings → Start Command** method (no code changes needed)

**Good**: Use **Procfile** (simple, works like Heroku)

**Advanced**: Use **Dockerfile** (most control, slightly slower builds)

---

## Verification

After deployment, check:
1. Build logs show Node.js installation
2. Start command is `node api/server.js`
3. Health check passes: `GET /health`
4. UI loads: `GET /`

---

## Alternative: Use Render.com Instead

If Railway continues to have issues, Render.com works great with the `render.yaml` I created:

1. Go to https://render.com
2. New → Blueprint
3. Connect GitHub repo
4. Render auto-detects `render.yaml`
5. Deploy!

Render explicitly uses Docker, so no auto-detection issues.

---

## Need Help?

If you're still stuck, here's what to send me:
1. Screenshot of Railway build logs
2. Which approach you tried (Settings/Procfile/Docker)
3. Any error messages

I'll help debug! 🚀

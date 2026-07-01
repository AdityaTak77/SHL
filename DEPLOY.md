# SHL Assessment Recommender - Deployment Guide

This guide provides the exact steps to deploy both the FastAPI backend and the React Vite frontend as a single unified Web Service on Render.

## Step 1: Save & Push to GitHub
Initialize Git (if not already done) and push this repository to GitHub. In your terminal:

```bash
git add .
git commit -m "feat: unified React frontend with FastAPI server and Groq integration"
git push origin main
```

## Step 2: Connect to Render
1. Create a free account at [https://render.com](https://render.com).
2. Click **New +** -> **Web Service**.
3. Link your GitHub account and select your `SHL` repository.

## Step 3: Setup Web Service Parameters
Configure the following options on the Render setup page:

- **Name:** `shl-assessment-recommender` (or any name you prefer)
- **Region:** Select the closest region to you.
- **Branch:** `main`
- **Runtime:** `Python 3`
- **Build Command:** `chmod +x build.sh && ./build.sh`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Plan:** Free

## Step 4: Configure Environment Variables
1. Scroll down and click **Advanced**, or click the **Environment** tab on the left-side menu.
2. Click **Add Environment Variable** and enter:
   - **Key:** `GROQ_API_KEY`
   - **Value:** `(your Groq API Key starting with gsk_)`
3. Click **Create Web Service** (or Save Changes). Render will start the deployment build automatically.

Your service will compile and go live in about 2 minutes. The public URL provided by Render (e.g., `https://shl-assessment-recommender.onrender.com/`) will host your beautiful SHL Corporate Theme UI at the root `/` and seamlessly serve the `/chat` and `/health` endpoints!

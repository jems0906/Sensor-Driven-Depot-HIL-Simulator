# 🚀 Render Deployment Guide

## HIL Depot Simulator - Cloud Deployment

### Prerequisites
- GitHub account with your HIL Depot Simulator repository
- Render account (free at [render.com](https://render.com))

### Deployment Steps

#### 1. Prepare Your Repository
✅ **Already Done:**
- `requirements.txt` - Python dependencies
- `Procfile` - Tells Render how to start your app  
- `render.yaml` - Infrastructure as code for Render
- Production-ready Flask configuration

#### 2. Deploy to Render

1. **Connect GitHub to Render:**
   - Go to [render.com](https://render.com) and sign up/login
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select your `Sensor-Driven-Depot-HIL-Simulator` repository

2. **Configure Service:**
   - **Name:** `hil-depot-simulator`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --chdir dashboard --bind 0.0.0.0:$PORT app:app`
   - **Plan:** Free (sufficient for development/demo)

3. **Set Environment Variables:**
   ```
   FLASK_ENV = production
   PYTHON_VERSION = 3.11.0
   ```

4. **Deploy:**
   - Click "Create Web Service"  
   - Render will automatically build and deploy your app
   - Your app will be live at: `https://hil-depot-simulator.onrender.com`

#### 3. Post-Deployment
- **Health Check:** Your dashboard will be accessible via the Render URL
- **Database:** SQLite database will be recreated on each deployment (perfect for demo)
- **Logs:** View application logs in Render dashboard
- **Auto-Deploy:** Any push to `master` branch will trigger automatic redeployment

### 🎯 Live Features After Deployment
- **Real-time HIL Simulation Dashboard**
- **Interactive Scenario Execution** 
- **Sensor Timeline Visualizations**
- **Fault Detection & Control Logic**
- **Performance Metrics & Analytics**

### Troubleshooting
- If build fails: Check requirements.txt formatting
- If app won't start: Verify Procfile command matches your directory structure
- Database issues: SQLite recreates automatically, no persistent data needed for demo

**Your HIL Depot Simulator will be live and accessible worldwide! 🌍**
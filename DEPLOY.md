# ☁️ Cloud Deployment Guide

This guide will help you run the **Autonomous Content Engine (ACE)** on a remote server so it runs 24/7 without needing your laptop.

## 1. Get a Server (VPS)
You need a cheap Linux server. We recommend:
*   **Hetzner Cloud**: CX32 (4 vCPU, 8GB RAM) - ~$8/month (Best for Local LLM)
*   **DigitalOcean**: Droplet (4GB RAM minimum) - ~$24/month
*   **AWS**: t3.medium or larger.

**OS Requirement**: Ubuntu 22.04 LTS

## 2. Connect to Server
Open your terminal (or Putty) and SSH into your new server:
```bash
ssh root@<your-server-ip>
```

## 3. One-Click Install
Run this single command to install everything (Docker, Git, App):

```bash
curl -sL https://raw.githubusercontent.com/aaasharma870-art/Content-automation-engine/main/deploy.sh | bash
```

*Note: The script will pause and ask you to enter your API Keys (OpenAI, Pexels) into the config file.*

## 4. Verify It's Running
After the script finishes, copy your server's IP address and open:
*   **API**: `http://<your-ip>:8000/docs`
*   **Dashboard**: `http://<your-ip>:3000`

## 5. Enable Local LLM (Optional)
If you leased a server with good CPU/RAM (8GB+):
1.  Enter the directory: `cd Content-automation-engine`
2.  Edit config: `nano .env`
3.  Set `USE_LOCAL_LLM=true`
4.  Restart: `docker compose up -d`

## 📊 Cost Estimate (Running 24/7)
*   **Server**: $8.00 / month
*   **OpenAI API**: ~$5.00 / month (with Hybrid Mode)
*   **Total**: **~$13.00 / month** (vs $150+ for manual tools)

---

## 🎬 Simple Mode (Local Batch Generation)

If you prefer to **manually review and upload** videos instead of auto-posting:

1.  **Configure**:
    Ensure your `.env` has:
    ```ini
    MANUAL_MODE=true
    ```

2.  **Run Daily Batch**:
    Run this single command to generate 3 videos:
    ```bash
    python run_daily_batch.py
    ```

3.  **Get Output**:
    Videos will be saved to a timestamped folder:
    `output/videos/YYYY-MM-DD_HH-MM-SS/`

    *   `cinematic_001.mp4`
    *   `cinematic_002.mp4`
    *   `cinematic_003.mp4`

4.  **Upload**:
    Review the videos and upload them to YouTube Shorts, TikTok, or Instagram Reels.


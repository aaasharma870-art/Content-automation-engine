# 🛠️ Setup & Channel Guide

This guide covers the **Business Setup** required to run your Autonomous Content Engine (ACE).

---

## 1. Required API Keys
You need these keys to power the "Brain" and "Eyes" of the system.

### A. OpenAI (The Brain)
*   **Purpose**: Script writing, poetry generation, hook optimization.
*   **Cost**: pay-as-you-go (approx $5/mo with Hybrid Mode).
*   **Get Key**: [platform.openai.com](https://platform.openai.com/api-keys)
*   **Action**: Create a new secret key. Copy it immediately.

### B. Pexels (The Visuals)
*   **Purpose**: High-quality stock video and imagery (Free).
*   **Cost**: Free (7000 requests/hour limit).
*   **Get Key**: [pexels.com/api](https://www.pexels.com/api/)
*   **Action**: Sign up, click "Your API Key".

### C. Pixabay (Secondary Visuals)
*   **Purpose**: Backup stock footage if Pexels misses.
*   **Cost**: Free.
*   **Get Key**: [pixabay.com/api/docs](https://pixabay.com/api/docs/)
*   **Action**: Scroll to "Parameters" section to see your key (must be logged in).

---

## 2. Channel Creation Strategy
You are building a **Media Brand**, not just a bot page. Consistency is key.

### A. Branding
*   **Name Ideas**:
    *   `@TheStoicMind`
    *   `@Discipline.Daily`
    *   `@Silent.Focus`
    *   `@Mental.Callus`
*   **Profile Picture**: Use a simple, high-contrast symbol or a black & white statue face. (You can use the `media__...png` artifacts generated earlier).

### B. The Bio (Copy-Paste)
Use this format for maximum authority:
> **[Brand Name]**
> 🧠 Daily Philosophy & Mindset
> ⚔️ Build your mental fortress
> 👇 Join the 1% (Link to product/newsletter)

### C. Account Setup (Important!)
1.  **TikTok**: Switch to **Business Account** immediately (Settings -> Account -> Switch to Business). This allows for analytics access later.
2.  **Instagram**: Switch to **Professional Account** (Creator or Business). Select category "Motivation" or "Media".
3.  **YouTube**: Create a new Channel. Verify your phone number to enable custom thumbnails (though Shorts don't always need them).

---

## 3. Connecting to ACE
Once you have your keys and channels ready:

1.  **On your Server** (or local machine):
    ```bash
    nano .env
    ```
2.  **Paste your keys**:
    ```ini
    OPENAI_API_KEY=sk-proj-...
    PEXELS_API_KEY=563492...
    PIXABAY_API_KEY=12345-...
    ```
3.  **Restart the Brain**:
    ```bash
    docker compose restart brain
    ```

## 4. The "Warm-Up" Phase
Don't post 10 videos on Day 1. Platforms will flag you as spam.
*   **Day 1-3**: 1 Video/day. Manually interact with other accounts in your niche.
*   **Day 4-7**: 2 Videos/day.
*   **Day 8+**: 3 Videos/day (Full Auto Mode).

## 5. Automating with n8n (Cloud)
Your system includes **n8n**, a visual automation tool running on your server.

### A. Login to n8n
1.  Open `http://<YOUR-SERVER-IP>:5678` in your browser.
2.  Set up your username/password (first time only).

### B. Import the Robot
1.  Download `n8n_automation.json` from the file list.
2.  In n8n, click **Workflows** -> **Import from File**.
3.  Select `n8n_automation.json`.

### C. Activate
1.  You will see a workflow: `Daily Schedule` -> `Generate` -> `Render` -> `Publish`.
2.  Click **Execute Workflow** to test it once.
3.  Toggle **Active** in the top right.

**Congratulations!** Your channels will now auto-post every morning at 8 AM. 🥂

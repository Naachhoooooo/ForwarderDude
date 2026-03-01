# ForwarderDude 🚀

**ForwarderDude** is a light-weight and intelligent Telegram bot designed to automate message forwarding between channels and groups. With a sleek dashboard, real-time statistics, and robust administration tools, it simplifies managing content flow across your Telegram communities.

## ✨ Features

- **Smart Forwarding**: Define rules to forward and filter messages from source to multiple destinations.
- **Persistent Message Queue**: Built-in SQLite-backed message queue with automatic retries and exponential backoff. No messages are lost during downtime or rate limits.
- **Automated Database Backups**: Daily hot-backups of the SQLite database to prevent data loss.
- **System Monitoring**: Built-in real-time dashboard tracking bot RAM usage, CPU load, and hardware temperatures, complete with generated 7-day performance charts.
- **Admin Control Panel**: Manage access control (approve/restrict users), generate unique invite links, and toggle global maintenance mode.
- **Robust Error Handling**: Handles Telegram `FloodWait` automatically.

> [!WARNING]
> **For Private Use Only**
> This bot is optimized for private or small group usage. Due to Telegram's strict API rate limits, using this bot for high-volume public forwarding may result in `FloodWait` errors or temporary bans. The bot includes adaptive rate limiting to mitigate this, but please use responsibly.

## 🐳 Docker Installation (Recommended)

1.  **Clone the repository and set up environment:**
    ```bash
    git clone https://github.com/Naachhoooooo/ForwarderDude.git
    cd ForwarderDude
    cp .env.example .env
    ```
2.  **Edit `.env`** with your `BOT_TOKEN` and `ADMIN_IDS`.
3.  **Deploy with Docker Compose:**
    ```bash
    docker-compose up -d
    ```

    *The bot will automatically create local `./data`, `./logs`, and `./backups` folders on your host machine to ensure your database and settings are never lost even if the container restarts.*

## 🛠 Manual Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Naachhoooooo/ForwarderDude.git
    cd ForwarderDude
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration:**
    - Copy the example environment file:
      ```bash
      cp .env.example .env
      ```
    - Open `.env` and fill in your details:
      ```env
      BOT_TOKEN=your_bot_token_here
      ADMIN_IDS=123456789,987654321
      ```
    - **Note**: You can find your Telegram User ID by messaging [@userinfobot](https://t.me/userinfobot).

5.  **Initialize Database:**
    The bot will automatically check and initialize the SQLite database on first run.

## 🚀 Usage

1.  **Start the bot:**
    ```bash
    python -m app.main
    ```

    *Alternatively, you can run the bot in the background using `nohup` or `systemd`.*

2.  **Open Telegram:**
    Start a chat with your bot and send `/start`.

3.  **Dashboard:**
    You will see the **Forwarder Dude** dashboard with your current statistics and control panel.
    - **Forward Messages**: Configure your forwarding rules.
    - **Settings**: Adjust bot preferences.
    - **Admin Panel**: (Admins only) Manage system settings and maintenance.

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to help improve ForwarderDude.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

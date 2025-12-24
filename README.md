# ForwarderDude 🚀

**ForwarderDude** is a powerful and intelligent Telegram bot designed to automate message forwarding between channels and groups. With a sleek dashboard, real-time statistics, and robust administration tools, it simplifies managing content flow across your Telegram communities.

## ✨ Features

- **Smart Forwarding**: Define rules to forward messages from source to multiple destinations.
- **Real-time Statistics**: View processed message counts and success rates directly from the dashboard with visual progress bars.
- **Admin Control Panel**: Manage the bot's settings, users, and maintenance mode.
- **Maintenance Mode**: Admins can enable maintenance mode to temporarily disable bot features for users, with custom notice messages.
- **Granular Control**: Pause and resume specific forwarding rules.
- **Robust Error Handling**: Automatic retry mechanisms and detailed error logging (disk I/O, network issues).
- **Secure**: User restriction and admin-only access for sensitive operations.

> [!WARNING]
> **For Private Use Only**
> This bot is optimized for private or small group usage. Due to Telegram's strict API rate limits, using this bot for high-volume public forwarding may result in `FloodWait` errors or temporary bans. The bot includes adaptive rate limiting to mitigate this, but please use responsibly.

## 🛠 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/StartTheBot/ForwarderDude.git
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
    python run.py
    ```

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

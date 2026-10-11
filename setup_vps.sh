#!/bin/bash
# ==============================================================================
# 12th Bihar Board Telegram Bot - 1-Click VPS Auto Setup Script (Ubuntu/Debian)
# ==============================================================================

set -e

echo "🚀 [1/5] सिस्टम अपडेट और आवश्यक पैकेज इंस्टॉल हो रहे हैं..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv git curl

APP_DIR="/opt/bihar_board_bot"
CURRENT_USER=$(whoami)

echo "📂 [2/5] प्रोजेक्ट डायरेक्टरी सेटअप ($APP_DIR)..."
sudo mkdir -p "$APP_DIR"
sudo chown -R "$CURRENT_USER:$CURRENT_USER" "$APP_DIR"

# फ़ाइलें कॉपी करें
cp -r ./* "$APP_DIR/" 2>/dev/null || true
cd "$APP_DIR"

echo "🐍 [3/5] Python Virtual Environment तैयार किया जा रहा है..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# चेक करें कि .env फ़ाइल में टोकन है या नहीं
if ! grep -q "BOT_TOKEN=" .env 2>/dev/null || grep -q "YOUR_TELEGRAM_BOT_TOKEN_HERE" .env 2>/dev/null; then
    echo "⚠️ ध्यान दें: .env फ़ाइल में अपना सही BOT_TOKEN ज़रूर डालें!"
fi

echo "⚙️ [4/5] 24x7 Systemd Background Service बनाई जा रही है..."
SERVICE_FILE="/etc/systemd/system/bihar_board_bot.service"

sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=12th Bihar Board Telegram Quiz Bot (24x7 Service)
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

echo "🔄 [5/5] सर्विस को इनेबल और स्टार्ट किया जा रहा है..."
sudo systemctl daemon-reload
sudo systemctl enable bihar_board_bot.service
sudo systemctl restart bihar_board_bot.service

echo "=================================================================="
echo "🎉 बधाई! आपका बॉट VPS पर 24x7 बैकग्राउंड में लाइव हो चुका है!"
echo "=================================================================="
echo "👉 बॉट का स्टेटस चेक करने के लिए कमांड: sudo systemctl status bihar_board_bot"
echo "👉 लाइव लॉग्स देखने के लिए कमांड: journalctl -u bihar_board_bot -f"
echo "👉 बॉट रिस्टार्ट करने के लिए कमांड: sudo systemctl restart bihar_board_bot"
echo "=================================================================="

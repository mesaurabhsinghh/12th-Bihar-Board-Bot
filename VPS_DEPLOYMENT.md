# 🚀 VPS Par 24x7 Bot Live Chalane Ka Guide

Is guide ki madad se aapka Telegram Bot VPS par **24 ghante, 365 din bina ruke** chalta rahega. Chahe aapka mobile ya personal laptop band ho, bot hamesha live rahega!

---

## 📌 Step 1: VPS Server Kahan Se Lein?

Aap inme se koi bhi sasta ya free Linux VPS (Ubuntu 22.04 / 24.04 LTS) le sakte hain:
1. **Hostinger VPS** (Lagbhag ₹150 - ₹200/month) — Sabse aasan aur sasta.
2. **Hetzner Cloud** (Lagbhag €3.5/month) — Bahut fast aur reliable.
3. **Oracle Cloud Always Free Tier** (₹0 Free Forever) — Agar aapke paas international credit/debit card hai to free me lifetime milta hai.
4. **DigitalOcean** ($4 - $6/month) — Student pack me free credits milte hain.

> **OS Selection:** Hamesha **Ubuntu 22.04 LTS** ya **Ubuntu 24.04 LTS** chunein.

---

## 📌 Step 2: VPS Se Connect Karein

Jab aap VPS kharidenge, to aapko ek **IP Address** aur **Password** milega.

Apne computer me PowerShell / Terminal kholein aur likhein:
```bash
ssh root@AAPKA_VPS_IP
```
(Fir password maangega, password type karke `Enter` dabayein).

---

## 📌 Step 3: Bot Files VPS Par Daalein

VPS se connect hone ke baad, files VPS par laane ke 2 sabse aasan tarike hain:

### Tarika A: GitHub Ke Zariye (Sabse Aasan)
1. Is folder ko apne GitHub repository me push karein.
2. VPS me likhein:
   ```bash
   git clone https://github.com/AAPKA_USERNAME/AAPKA_REPO.git bot
   cd bot
   ```
3. `.env` file banakar apna Bot Token daalein:
   ```bash
   nano .env
   ```
   Isme likhein:
   ```env
   BOT_TOKEN=Aapka_Telegram_Bot_Token
   ```
   Save karne ke liye: `Ctrl + O`, fir `Enter`, fir exit ke liye `Ctrl + X`.

---

## 📌 Step 4: 1-Click Auto Setup Script Run Karein

Humne aapke liye ek automated script [setup_vps.sh](file:///c:/12th%20Bihar%20Board%20bot/setup_vps.sh) bana di hai jo ek hi command me sab kuch configure kar degi:

VPS terminal me bas yeh chalayein:
```bash
chmod +x setup_vps.sh
./setup_vps.sh
```

Yeh script apne aap:
- Python 3, pip aur requirements install karegi.
- Background `systemd` service create karegi (`bihar_board_bot.service`).
- Auto-restart configure karegi (agar server kabhi restart ho ya internet fluctuate ho, to bot automatically 5 second me khud start ho jayega).

---

## 📌 Step 5: Bot Ko Manage Karne Ki Commands

| Kaam | Command |
|---|---|
| **Bot ka status dekhna** | `sudo systemctl status bihar_board_bot` |
| **Live logs dekhna** | `journalctl -u bihar_board_bot -f` |
| **Bot ko restart karna** | `sudo systemctl restart bihar_board_bot` |
| **Bot ko stop karna** | `sudo systemctl stop bihar_board_bot` |

---

## 🐳 Vikalp 2: Docker Ke Saath Run Karna (Optional)

Agar aap Docker use karna chahte hain:
```bash
docker compose up -d --build
```
Bas! Bot background container me hamesha chalta rahega!

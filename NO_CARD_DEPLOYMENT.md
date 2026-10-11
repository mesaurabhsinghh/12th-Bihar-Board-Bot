# 🆓 Bina Credit/Debit Card Ke 24x7 Bot Live Chalane Ka Tarika

Agar aapke paas koi Credit Card ya International Debit Card nahi hai, to **Render.com + UptimeRobot** ka combination sabse best hai:
- ✅ **100% FREE (Hamesha ke liye)**
- ✅ **Kisi bhi Credit Card / Debit Card ki zaroorat NAHI hai**
- ✅ **Google / GitHub se direct 1-minute me account ban jata hai**
- ✅ **24 Ghante, 365 Din bina ruke chalta hai**

---

## 🛠️ Step-by-Step Setup Guide

### 📌 Step 1: Is Project Ko GitHub Par Daalein (Upload Karein)
1. [GitHub.com](https://github.com) par free account banayein (agar pehle se nahi hai).
2. Ek nayi repository banayein (jaise: `bihar-quiz-bot`).
3. Is folder ki sabhi files us repository me upload kar dein (ya Git se push karein).
   > *Note: `.env` file ko GitHub par public mat kijiyega.*

---

### 📌 Step 2: Render.com Par Free Account Banayein & Deploy Karein
1. Apne browser me **[https://render.com](https://render.com)** par jayein.
2. **Sign Up with GitHub** ya **Sign Up with Google** par click karein *(Yahan koi card nahi maangta)*.
3. Dashboard me aane ke baad **"New +"** par click karein aur **"Web Service"** chunein.
4. Apni GitHub repository select karein (`bihar-quiz-bot`).
5. Details bharein:
   - **Name:** `bihar-12th-quiz-bot`
   - **Region:** Singapore / Frankfurt / Oregon (koi bhi)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
   - **Instance Type:** `Free` (0$ / month)
6. Thoda niche scroll karein aur **"Environment Variables"** me jayein:
   - **Key:** `BOT_TOKEN`
   - **Value:** `Aapka_Telegram_Bot_Token_Yahan_Paste_Karein`
7. Niche **"Create Web Service"** par click kar dein!

Kuch hi second me aapka bot build hokar live ho jayega aur Render aapko ek **Free URL** de dega:
👉 Jaise: `https://bihar-12th-quiz-bot.onrender.com`

---

### 📌 Step 3: UptimeRobot Se Bot Ko 24x7 Zinda Rakhein (Never Sleep)
*Render ka free tier 15 minute baad so jata hai agar koi user web page na khole. Lekin humne bot ke andar ek keep-alive server jod diya hai.*

1. **[https://uptimerobot.com](https://uptimerobot.com)** par jayein aur Free Account banayein *(Yahan bhi koi card nahi chahiye)*.
2. **"+ Add New Monitor"** par click karein.
3. Details bharein:
   - **Monitor Type:** `HTTP(s)`
   - **Friendly Name:** `Bihar Board Bot`
   - **URL (or IP):** Render se mila hua URL (jaise `https://bihar-12th-quiz-bot.onrender.com`)
   - **Monitoring Interval:** `Every 5 minutes`
4. **"Create Monitor"** par click kar dein!

---

### 🎉 Bas Ho Gaya!
UptimeRobot har 5 minute me aapke Render server ko ping karta rahega, jisse **Render kabhi sleep mode me nahi jayega** aur aapka Telegram bot **24x7 lagatar live** rahega!

# 🎓 12th Bihar Board (BSEB) Telegram Quiz Bot

यह एक शक्तिशाली और इंटरैक्टिव Telegram Quiz Bot है जो **बिहार बोर्ड कक्षा 12वीं (BSEB 12th)** के छात्रों के लिए ऑब्जेक्टिव (MCQ) प्रश्नों की तैयारी करवाता है।

---

## 🌟 मुख्य विशेषताएँ (Features)

1. **विषय-वार क्विज़ (Subject-Wise Quiz):**
   - 🔬 भौतिक विज्ञान (Physics)
   - 🧪 रसायन विज्ञान (Chemistry)
   - 🧬 जीव विज्ञान (Biology)
   - 📐 गणित (Mathematics)
   - 📖 हिंदी 100 अंक (Hindi 100 Marks)
   - 🇬🇧 English 100 Marks
2. **इनलाइन बटन इंटरफ़ेस (Interactive Inline Buttons):**
   - प्रत्येक प्रश्न के लिए 4 विकल्प (A, B, C, D) इनलाइन बटनों के रूप में।
   - छात्र सीधे बटन पर टैप करके उत्तर दे सकते हैं।
3. **तुरंत परिणाम एवं व्याख्या (Instant Feedback & Explanation):**
   - सही या गलत उत्तर का तुरंत परिणाम।
   - प्रत्येक प्रश्न की विस्तृत व्याख्या (Explanation) ताकि छात्र संकल्पना (Concept) समझ सकें।
   - लाइव स्कोर ट्रैकिंग (जैसे: `📊 आपका स्कोर: 1/1`).
4. **ऑटोमैटिक अगला प्रश्न (Automatic Next Question):**
   - उत्तर देने के 3 सेकंड बाद स्वतः अगला प्रश्न आ जाता है।
   - छात्र यदि तुरंत आगे बढ़ना चाहें तो `➡️ अगला प्रश्न` बटन दबा सकते हैं।
5. **स्कोरबोर्ड और लीडरबोर्ड (Stats & Leaderboard):**
   - SQLite डेटाबेस में प्रत्येक छात्र का व्यक्तिगत स्कोर और सटीकता प्रतिशत सुरक्षित रहता है।
   - टॉप 10 मेधावी छात्रों की लीडरबोर्ड सूची (`/leaderboard`).
6. **आसान प्रश्न जोड़ना (Easy to Add Questions):**
   - सभी प्रश्न `data/` फ़ोल्डर में साफ़-सुथरे JSON फॉर्मेट में हैं। आप जितने चाहें नए प्रश्न जोड़ सकते हैं।

---

## 📁 फ़ाइल संरचना (Project Structure)

```text
12th Bihar Board bot/
├── data/
│   ├── physics.json          # 12th भौतिक विज्ञान प्रश्न बैंक
│   ├── chemistry.json        # 12th रसायन विज्ञान प्रश्न बैंक
│   ├── biology.json          # 12th जीव विज्ञान प्रश्न बैंक
│   ├── mathematics.json      # 12th गणित प्रश्न बैंक
│   ├── hindi.json            # 12th हिंदी (दिगंत भाग 2 व व्याकरण)
│   └── english.json          # 12th English (Rainbow & Grammar)
├── bot.py                    # मुख्य टेलीग्राम बॉट इंजन
├── config.py                 # सेटिंग्स और विषय सूची
├── database.py               # SQLite3 डेटाबेस ऑपरेशन्स
├── questions.py              # प्रश्न लोडर और रैंडमाइज़र
├── validate_questions.py     # प्रश्न बैंक जाँचने का टूल
├── requirements.txt          # आवश्यक Python लाइब्रेरीज़
├── .env                      # बॉट टोकन कॉन्फ़िगरेशन
└── README.md                 # यह गाइड
```

---

## 🚀 बॉट कैसे शुरू करें (Step-by-Step Setup Guide)

### 1️⃣ Telegram पर Bot Token प्राप्त करें:
1. अपने Telegram ऐप में **[@BotFather](https://t.me/BotFather)** सर्च करें।
2. चैट में `/newbot` भेजें।
3. अपने बॉट का एक नाम रखें (उदा: `Bihar Board 12th Quiz Bot`).
4. एक यूज़रनेम चुनें जो `bot` पर ख़त्म हो (उदा: `bseb12_quiz_bot`).
5. BotFather आपको एक **HTTP API Token** देगा (उदा: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### 2️⃣ Token को `.env` में सेव करें:
प्रोजेक्ट की `.env` फ़ाइल खोलें और अपना टोकन पेस्ट करें:
```env
BOT_TOKEN=YOUR_ACTUAL_TELEGRAM_BOT_TOKEN_HERE
DEFAULT_QUESTIONS_PER_QUIZ=10
AUTO_NEXT_DELAY_SECONDS=3
```

### 3️⃣ बॉट चलाएँ:
टर्मिनल / PowerShell में यह कमांड चलाएँ:
```bash
python bot.py
```
जब टर्मिनल में `Listening for messages...` दिखे, इसका मतलब बॉट लाइव हो चुका है!

---

## 📱 बॉट के Telegram कमांड्स

| कमांड | कार्य |
|---|---|
| `/start` या `/menu` | मुख्य विषय मेन्यू खोलें और क्विज़ शुरू करें |
| `/stats` | अपना कुल स्कोर, सटीकता (Accuracy %) देखें |
| `/leaderboard` | टॉप 10 छात्रों की रैंकिंग देखें |
| `/stop` | चालू क्विज़ को रोकें |
| `/help` | सहायता निर्देश पढ़ें |

---

## ✍️ नए प्रश्न कैसे जोड़ें? (How to Add More Questions)

`data/` फ़ोल्डर में जाकर संबंधित विषय की JSON फ़ाइल (जैसे `physics.json`) खोलें और नए प्रश्न जोड़ें:

```json
{
  "id": 16,
  "chapter": "विद्युत धारा (Current Electricity)",
  "question": "विद्युत परिपथ की शक्ति (Power) होती है:",
  "options": {
    "A": "V · R",
    "B": "V² · R",
    "C": "V² / R",
    "D": "V² · R · I"
  },
  "correct": "C",
  "explanation": "विद्युत शक्ति P = V² / R या P = V × I या P = I² × R होती है।"
}
```

प्रश्न जोड़ने के बाद यह कमांड चलाकर सुनिश्चित करें कि फ़ाइल में कोई टाइपिंग या सिंटेक्स मिस्टेक नहीं है:
```bash
python validate_questions.py
```

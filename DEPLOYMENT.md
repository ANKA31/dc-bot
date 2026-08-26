# Render Deploy Dosyası

Tüm dosyalara bu klasör içinde bulunmalıdır:

```
dc bot/
├── main.py                (Bot)
├── app.py                 (Web Dashboard)
├── config.py
├── cogs/
│   ├── __init__.py
│   └── ... (tüm cog modülleri)
├── templates/
│   └── dashboard.html
├── requirements.txt
├── Procfile
├── render.yaml
├── runtime.txt
├── .env.example
├── .gitignore
└── modlogs.json          (Otomatik oluşturulur)
```

## Render Kurulum Adımları

### 1. GitHub'a Push Et
```bash
git add .
git commit -m "rootv1 Discord Bot + Admin Dashboard"
git push origin main
```

### 2. Render'a Git
https://render.com → "New" → "Blueprint"

### 3. Repository Seç
Botunun olduğu repository'i seç

### 4. Environment Variables Ekle
Render Dashboard → "Environment" bölümüne ekle:
```
DISCORD_TOKEN=YENİ_TOKEN_BURAYA_GEL
```

### 5. Deploy!
Render otomatik deploy eder → 2-3 dakika

## URL'ler
- **Web Dashboard:** `https://your-app.onrender.com`
- **Bot:** Arka planda 24/7 çalışıyor

## Local Test (Railway'den Önce)
```bash
# Terminal 1
python main.py

# Terminal 2
python app.py

# Tarayıcı
http://localhost:5000
```

Sorular? Sor!

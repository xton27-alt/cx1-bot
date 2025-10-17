
# Telegram Stars Payments Bot (Arabic)

بوت جاهز لقبول مدفوعات **Telegram Stars (XTR)** للسلع الرقمية (اشتراكات/ملفات) داخل تيليجرام.

## خطوات التشغيل محليًا
```bash
pip install -r requirements.txt
export BOT_TOKEN=ضع_التوكن_من_BotFather
export ADMIN_ID=123456789   # اختياري
python bot.py
```

## أو على Render/Heroku
- ارفع الملفات كريبو GitHub
- أنشئ Worker
- أضف متغيرات البيئة:
  - `BOT_TOKEN`
  - `ADMIN_ID` (اختياري)

## أوامر البوت المقترحة
```
start - ابدأ
buy - شراء/الاشتراك
plans - الباقات
terms - الشروط
support - الدعم
status - حالتي
```

> العملة: XTR (Stars). اترك `provider_token` فارغًا لأن المنتج رقمي.

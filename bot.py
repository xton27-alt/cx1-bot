# -- coding: utf-8 --
# متجر روبوتات بدون نجوم + دفع يدوي بإثبات + موافقة أدمن + إرسال تلقائي
# لوحة تحكم كاملة (تظهر للأدمن فقط): منتجات / صور / أسعار / طرق دفع / إعدادات / أدمنز / طلبات
# Python 3.11+ | aiogram 3.13.1

import asyncio, os, json, uuid, datetime as dt
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ============== إعدادات ثابتة ==============
BOT_TOKEN = "8263685190:AAEwPfXILnWEv25F1U734W0lfyr38M2ZOIs"
OWNER_ID  = 1020361419  # المالك الأساسي (لا يُحذف)
FILES_DIR = "files"

DATA_PRODUCTS = "products.json"   # المنتجات
DATA_SETTINGS = "settings.json"   # الإعدادات العامة + طرق الدفع + الأدمنز
DATA_ORDERS   = "orders.json"     # الطلبات

os.makedirs(FILES_DIR, exist_ok=True)

# ============== بيانات افتراضية ==============
DEFAULT_PRODUCTS: Dict[str, dict] = {
    "gold_scalp": {
        "title": "بوت الذهب — المضاربة",
        "price": 10000,
        "description": "شراء بوت الذهب — المضاربة. التسليم بعد تأكيد الدفع.",
        "file_path": "files/gold_scalp.zip",
        "photo_id": "",
        "enabled": True
    },
    "gold_invest": {
        "title": "بوت الذهب — الاستثمار",
        "price": 15000,
        "description": "شراء بوت الذهب — الاستثمار. التسليم بعد تأكيد الدفع.",
        "file_path": "files/gold_invest.zip",
        "photo_id": "",
        "enabled": True
    },
    "btc_scalp": {
        "title": "بوت العملات الرقمية BTC — المضاربة",
        "price": 12000,
        "description": "شراء بوت BTC — المضاربة. التسليم بعد تأكيد الدفع.",
        "file_path": "files/btc_scalp.zip",
        "photo_id": "",
        "enabled": True
    },
}

DEFAULT_SETTINGS = {
    "support_url": "https://t.me/AE313AM",
    # طرق الدفع: قائمة عناصر {id, name, details}
    "payments": [
        {"id": "usdt_trc20", "name": "USDT (TRC20)", "details": "أرسل إلى: TXxxxxxxxxxxxxxxxxxxxx"},
        {"id": "binance_pay", "name": "Binance Pay", "details": "@YourBinanceHandle"},
    ],
    # الأدمنز (يتضمن المالك)
    "admins": [OWNER_ID]
}

# ============== تحميل/حفظ JSON ==============
def load_json(path: str, fallback):
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return fallback

def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

PRODUCTS: Dict[str, dict] = load_json(DATA_PRODUCTS, DEFAULT_PRODUCTS.copy())
SETTINGS: Dict[str, dict] = load_json(DATA_SETTINGS, DEFAULT_SETTINGS.copy())
ORDERS: Dict[str, dict]   = load_json(DATA_ORDERS,   {})

def save_settings():
    admins = [OWNER_ID] + [a for a in SETTINGS.get("admins", []) if a != OWNER_ID]
    # إزالة التكرار مع الحفاظ على الترتيب
    seen = set(); dedup = []
    for a in admins:
        if a not in seen:
            seen.add(a); dedup.append(a)
    SETTINGS["admins"] = dedup
    save_json(DATA_SETTINGS, SETTINGS)

def save_products(): save_json(DATA_PRODUCTS, PRODUCTS)
def save_orders():   save_json(DATA_ORDERS,   ORDERS)

# ============== بوت ==============
bot = Bot(BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ============== أدوات مساعدة ==============
def is_admin(uid: int) -> bool:
    return uid in SETTINGS.get("admins", []) or uid == OWNER_ID

def main_menu_kb(user_id: int) -> InlineKeyboardMarkup:
    """القائمة الرئيسية: زر لوحة التحكم يظهر للأدمن فقط"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍️ عرض الروبوتات", callback_data="show_bots")
    kb.button(text="🆘 الدعم", url=SETTINGS.get("support_url",""))
    if is_admin(user_id):
        kb.button(text="⚙️ لوحة التحكم", callback_data="admin")
    kb.adjust(1)
    return kb.as_markup()

def products_list_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, p in PRODUCTS.items():
        if not p.get("enabled", True): continue
        kb.button(text=f"⭐ {p['title']} — {p['price']}", callback_data=f"p:{code}")
    kb.button(text="⬅️ رجوع", callback_data="back_home")
    kb.adjust(1)
    return kb.as_markup()

def product_card_kb(code: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 شراء الآن", callback_data=f"buy:{code}")
    kb.button(text="⬅️ قائمة المنتجات", callback_data="show_bots")
    kb.adjust(1)
    return kb.as_markup()

def admin_home_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 المنتجات", callback_data="admin:products")
    kb.button(text="💳 طرق الدفع", callback_data="admin:payments")
    kb.button(text="👥 إدارة الأدمنز", callback_data="admin:admins")
    kb.button(text="⚙️ إعدادات عامة", callback_data="admin:settings")
    kb.button(text="🧾 الطلبات", callback_data="admin:orders")
    kb.button(text="⬅️ رجوع", callback_data="back_home")
    kb.adjust(2,2,2)
    return kb.as_markup()

# ===== منتجات: قوائم ولوحات =====
def admin_products_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📃 عرض المنتجات", callback_data="admin:prod:list")
    kb.button(text="➕ إضافة منتج", callback_data="admin:prod:add")
    kb.button(text="✏️ تعديل منتج", callback_data="admin:prod:edit")
    kb.button(text="🖼️ تعديل صورة", callback_data="admin:prod:photo")
    kb.button(text="🔛 تفعيل/تعطيل", callback_data="admin:prod:toggle")
    kb.button(text="🗑️ حذف منتج", callback_data="admin:prod:delete")
    kb.button(text="⬅️ رجوع", callback_data="admin")
    kb.adjust(2,2,2,1)
    return kb.as_markup()

def admin_select_product_kb(prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, p in PRODUCTS.items():
        mark = "✅" if p.get("enabled", True) else "⛔"
        kb.button(text=f"{mark} {p['title']} ({code})", callback_data=f"{prefix}:{code}")
    kb.button(text="⬅️ رجوع", callback_data="admin:products")
    kb.adjust(1)
    return kb.as_markup()

def admin_edit_product_kb(code: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ الاسم", callback_data=f"admin:prod:edit:title:{code}")
    kb.button(text="💲 السعر", callback_data=f"admin:prod:edit:price:{code}")
    kb.button(text="📝 الوصف", callback_data=f"admin:prod:edit:desc:{code}")
    kb.button(text="📦 الملف", callback_data=f"admin:prod:edit:file:{code}")
    kb.button(text="⬅️ رجوع", callback_data="admin:products")
    kb.adjust(2,2,1)
    return kb.as_markup()

# ===== طرق الدفع: قوائم ولوحات =====
def payments_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📃 قائمة الطرق", callback_data="admin:pay:list")
    kb.button(text="➕ إضافة طريقة", callback_data="admin:pay:add")
    kb.button(text="✏️ تعديل طريقة", callback_data="admin:pay:edit")
    kb.button(text="🗑️ حذف طريقة", callback_data="admin:pay:del")
    kb.button(text="⬅️ رجوع", callback_data="admin")
    kb.adjust(2,2,1)
    return kb.as_markup()

def payments_select_kb(prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for pm in SETTINGS.get("payments", []):
        kb.button(text=f"{pm['name']}", callback_data=f"{prefix}:{pm['id']}")
    kb.button(text="⬅️ رجوع", callback_data="admin:payments")
    kb.adjust(1)
    return kb.as_markup()

# ===== الأدمنز: قوائم ولوحات =====
def admins_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗒️ القائمة", callback_data="admin:admins:list")
    kb.button(text="➕ إضافة أدمن", callback_data="admin:admins:add")
    kb.button(text="➖ حذف أدمن", callback_data="admin:admins:remove")
    kb.button(text="⬅️ رجوع", callback_data="admin")
    kb.adjust(2,2)
    return kb.as_markup()

# ===== الطلبات: لوحة موافقة/رفض =====
def review_kb(order_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ قبول", callback_data=f"order:approve:{order_id}")
    kb.button(text="❌ رفض", callback_data=f"order:reject:{order_id}")
    kb.adjust(2)
    return kb.as_markup()

# ===== حالات FSM =====
class ProdStates(StatesGroup):
    new_code = State()
    new_title = State()
    new_price = State()
    new_desc  = State()
    new_file  = State()
    photo_pick_code = State()
    wait_photo = State()

    edit_pick_code = State()
    edit_set_title = State()
    edit_set_price = State()
    edit_set_desc  = State()
    edit_set_file  = State()

class PayStates(StatesGroup):
    add_name   = State()
    add_details= State()
    edit_pick  = State()
    edit_name  = State()
    edit_details = State()
    del_pick   = State()

class AdminsStates(StatesGroup):
    add_admin = State()
    del_pick  = State()

class SettingsStates(StatesGroup):
    support_url = State()

class OrderStates(StatesGroup):
    waiting_proof = State()
    waiting_delivery = State()

# مؤشر الطلب النشط لكل مستخدم (لجمع الإثبات والبيانات)
USER_ACTIVE_ORDER: Dict[int, str] = {}

# ============== أوامر المستخدم ==============
@dp.message(Command("start"))
async def start_cmd(m: Message):
    await m.answer(
        "أهلًا بك في متجر روبوتات التداول 👋\n"
        "• تصفح المنتجات: /bots\n"
        "• الدعم: /support",
        reply_markup=main_menu_kb(m.from_user.id)
    )

@dp.message(Command("support"))
async def support_cmd(m: Message):
    await m.answer(f"للدعم: {SETTINGS.get('support_url','')}")

@dp.message(Command("bots"))
async def bots_cmd(m: Message):
    await m.answer("🛍️ اختر منتجًا:", reply_markup=products_list_kb())

# عرض بطاقة المنتج
@dp.callback_query(F.data.startswith("p:"))
async def product_card(cq: CallbackQuery):
    code = cq.data.split(":",1)[1]
    p = PRODUCTS.get(code)
    if not p or not p.get("enabled", True):
        return await cq.answer("المنتج غير متاح.", show_alert=True)
    caption = f"🛒 {p['title']}\nالسعر: {p['price']}\n\n{p['description']}"
    pid = (p.get("photo_id") or "").strip()
    if pid:
        await cq.message.answer_photo(pid, caption=caption, reply_markup=product_card_kb(code))
    else:
        await cq.message.answer(caption, reply_markup=product_card_kb(code))
    await cq.answer()

@dp.callback_query(F.data == "show_bots")
async def cb_show_bots(cq: CallbackQuery):
    await cq.message.answer("🛍️ اختر منتجًا:", reply_markup=products_list_kb())
    await cq.answer()

@dp.callback_query(F.data == "back_home")
async def cb_back_home(cq: CallbackQuery):
    await cq.message.answer("القائمة الرئيسية:", reply_markup=main_menu_kb(cq.from_user.id))
    await cq.answer()

# ============== عملية شراء (دفع يدوي) ==============
def choose_payment_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    pays = SETTINGS.get("payments", [])
    for pm in pays:
        kb.button(text=f"💳 {pm['name']}", callback_data=f"buy:method:{pm['id']}")
    if not pays:
        kb.button(text="لا توجد طرق دفع مفعلة", callback_data="noop")
    kb.button(text="⬅️ رجوع", callback_data="show_bots")
    kb.adjust(1)
    return kb.as_markup()

@dp.callback_query(F.data.startswith("buy:"))
async def buy_flow(cq: CallbackQuery, state: FSMContext):
    parts = cq.data.split(":")
    if parts[1] == "method":
        # اختيار طريقة دفع لاحقًا يُعالَج في كولباك آخر
        return await cq.answer()

    # بدء شراء منتج
    code = cq.data.split(":",1)[1]
    p = PRODUCTS.get(code)
    if not p or not p.get("enabled", True):
        return await cq.answer("المنتج غير متاح.", show_alert=True)

    await cq.message.answer(
        f"اختر طريقة الدفع لشراء: {p['title']} — السعر: {p['price']}",
        reply_markup=choose_payment_kb()
    )
    # خزّن المنتج مؤقتًا في FSM
    await state.update_data(pending_product=code)
    await cq.answer()

@dp.callback_query(F.data.startswith("buy:method:"))
async def choose_method(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    code = data.get("pending_product")
    if not code:
        return await cq.answer("يرجى اختيار المنتج أولًا.", show_alert=True)
    p = PRODUCTS.get(code)
    if not p:
        return await cq.answer("المنتج غير موجود.", show_alert=True)

    pay_id = cq.data.split(":",2)[2]
    pay = next((x for x in SETTINGS.get("payments",[]) if x["id"]==pay_id), None)
    if not pay:
        return await cq.answer("طريقة الدفع غير متاحة.", show_alert=True)

    # إنشاء طلب
    order_id = uuid.uuid4().hex[:10]
    ORDERS[order_id] = {
        "status": "awaiting_proof",
        "created_at": dt.datetime.utcnow().isoformat(),
        "buyer_id": cq.from_user.id,
        "product_code": code,
        "product_title": p["title"],
        "price": p["price"],
        "payment_method_id": pay["id"],
        "payment_method_name": pay["name"],
        "payment_details": pay["details"],
        "proof_files": [],   # file_ids
        "delivery_note": ""  # بيانات التسليم/التواصل
    }
    save_orders()
    USER_ACTIVE_ORDER[cq.from_user.id] = order_id

    text = (
        f"🧾 *طلب جديد*\n"
        f"المنتج: {p['title']}\n"
        f"السعر: {p['price']}\n"
        f"طريقة الدفع: {pay['name']}\n"
        f"🔹 أرسل المبلغ إلى:\n`{pay['details']}`\n\n"
        f"بعد التحويل:\n1) أرسل *إثبات الدفع* (صورة/ملف).\n"
        f"2) أرسل *عنوان التسليم* أو وسيلة تواصل (تيليجرام/إيميل/واتساب).\n"
        f"ثم اكتب: *تم* أو *خلصت*."
    )
    await cq.message.answer(text, parse_mode="Markdown")
    await state.set_state(OrderStates.waiting_proof)
    await cq.answer()

# استقبال إثبات الدفع (صور/ملفات/رسائل) وبيانات التسليم
@dp.message(OrderStates.waiting_proof, F.photo | F.document | F.text)
async def capture_proof(m: Message, state: FSMContext):
    order_id = USER_ACTIVE_ORDER.get(m.from_user.id)
    if not order_id or order_id not in ORDERS:
        await state.clear()
        return await m.answer("لا يوجد طلب نشط. ابدأ من جديد عبر /bots")

    order = ORDERS[order_id]
    updated = False

    if m.photo:
        fid = m.photo[-1].file_id
        order["proof_files"].append(fid); updated = True
        await m.answer("📎 تم حفظ صورة الإثبات.")
    elif m.document:
        fid = m.document.file_id
        order["proof_files"].append(fid); updated = True
        await m.answer("📎 تم حفظ ملف الإثبات.")
    elif m.text:
        txt = (m.text or "").strip().lower()
        if txt in ("تم", "خلصت", "done", "paid"):
            await push_order_to_admin(order_id)
            await state.set_state(OrderStates.waiting_delivery)
            return
        else:
            order["delivery_note"] += (("\n" if order["delivery_note"] else "") + m.text)
            updated = True
            await m.answer("✍️ تم حفظ بيانات التسليم.")

    if updated:
        save_orders()

async def push_order_to_admin(order_id: str):
    o = ORDERS[order_id]
    p = PRODUCTS.get(o["product_code"], {})
    proof_count = len(o.get("proof_files", []))
    txt = (
        f"🆕 *طلب بانتظار المراجعة*\n"
        f"Order: {order_id}\n"
        f"عميل: {o['buyer_id']}\n"
        f"منتج: {p.get('title','')}\n"
        f"سعر: {o.get('price','')}\n"
        f"طريقة الدفع: {o.get('payment_method_name','')}\n"
        f"تفاصيل الدفع: {o.get('payment_details','')}\n"
        f"إثباتات: {proof_count}\n"
        f"بيانات التسليم:\n{o.get('delivery_note','(لا يوجد)')}"
    )
    # أرسل لكل الأدمنز
    for uid in SETTINGS.get("admins", []):
        try:
            await bot.send_message(uid, txt, reply_markup=review_kb(order_id), parse_mode="Markdown")
        except Exception:
            pass

    await bot.send_message(o["buyer_id"], "✅ تم إرسال طلبك للمراجعة. سنقوم بالتأكيد بأقرب وقت.")

# موافقة/رفض الأدمن
async def send_product_to_user(user_id: int, product_code: str, title: str):
    p = PRODUCTS.get(product_code)
    if not p:
        return await bot.send_message(user_id, "تم القبول ✅ لكن المنتج غير موجود حالياً.")
    path = p.get("file_path")
    if not path or not os.path.isfile(path):
        return await bot.send_message(user_id, "تم القبول ✅ لكن الملف غير متوفر على الخادم.")
    try:
        await bot.send_document(user_id, InputFile(path), caption=f"تم الشراء ✅\nالمنتج: {title}")
    except Exception as e:
        await bot.send_message(user_id, f"حصل خطأ أثناء الإرسال: {e}")

@dp.callback_query(F.data.startswith("order:approve:"))
async def approve_order(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        return await cq.answer("للمشرفين فقط.", show_alert=True)
    oid = cq.data.split(":",2)[2]
    o = ORDERS.get(oid)
    if not o: return await cq.answer("الطلب غير موجود.", show_alert=True)
    if o["status"] != "awaiting_proof":
        return await cq.answer("تمت معالجته مسبقًا.")

    o["status"] = "approved"; o["approved_at"] = dt.datetime.utcnow().isoformat()
    save_orders()
    await send_product_to_user(o["buyer_id"], o["product_code"], o["product_title"])
    await cq.message.edit_text(f"✅ تم قبول الطلب {oid} وإرسال الملف.", parse_mode="Markdown")
    await cq.answer("تم القبول.")

@dp.callback_query(F.data.startswith("order:reject:"))
async def reject_order(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        return await cq.answer("للمشرفين فقط.", show_alert=True)
    oid = cq.data.split(":",2)[2]
    o = ORDERS.get(oid)
    if not o: return await cq.answer("الطلب غير موجود.", show_alert=True)
    if o["status"] != "awaiting_proof":
        return await cq.answer("تمت معالجته مسبقًا.")

    o["status"] = "rejected"; o["rejected_at"] = dt.datetime.utcnow().isoformat()
    save_orders()
    try:
        await bot.send_message(o["buyer_id"], "❌ تم رفض الطلب. إن كان هناك خطأ، راسل الدعم.")
    except Exception:
        pass
    await cq.message.edit_text(f"❌ تم رفض الطلب {oid}.", parse_mode="Markdown")
    await cq.answer("تم الرفض.")

# ============== لوحة التحكم (أدمن فقط) ==============
@dp.callback_query(F.data == "admin")
async def admin_home(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        return await cq.answer("لوحة الإدارة للمشرفين فقط.", show_alert=True)
    await cq.message.answer("⚙️ لوحة التحكم", reply_markup=admin_home_kb())
    await cq.answer()

# --- المنتجات
@dp.callback_query(F.data == "admin:products")
async def admin_products(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await cq.message.answer("📦 إدارة المنتجات", reply_markup=admin_products_menu_kb())
    await cq.answer()

@dp.callback_query(F.data == "admin:prod:list")
async def prod_list(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    if not PRODUCTS: return await cq.message.answer("لا توجد منتجات.")
    lines = ["📃 قائمة المنتجات:"]
    for code, p in PRODUCTS.items():
        mark = "✅" if p.get("enabled", True) else "⛔"
        photo = "🖼️" if p.get("photo_id") else "—"
        lines.append(f"{mark} {p['title']} — {p['price']}  {photo}\ncode:{code} | ملف:{p['file_path']}")
    await cq.message.answer("\n\n".join(lines)); await cq.answer()

class ProdStates(StatesGroup):
    new_code = State(); new_title = State(); new_price = State(); new_desc = State(); new_file = State()
    photo_pick_code = State(); wait_photo = State()
    edit_pick_code = State(); edit_set_title = State(); edit_set_price = State(); edit_set_desc = State(); edit_set_file = State()

@dp.callback_query(F.data == "admin:prod:add")
async def prod_add(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await state.clear(); await state.set_state(ProdStates.new_code)
    await cq.message.answer("أرسل كود المنتج (بدون مسافات)."); await cq.answer()

@dp.message(ProdStates.new_code)
async def prod_add_code(m: Message, state: FSMContext):
    code = (m.text or "").strip()
    if not code or " " in code or ":" in code or code in PRODUCTS:
        return await m.answer("كود غير صالح/مكرر.")
    await state.update_data(code=code); await state.set_state(ProdStates.new_title)
    await m.answer("أرسل اسم المنتج:")

@dp.message(ProdStates.new_title)
async def prod_add_title(m: Message, state: FSMContext):
    await state.update_data(title=(m.text or "").strip())
    await state.set_state(ProdStates.new_price)
    await m.answer("أرسل السعر (رقم):")

@dp.message(ProdStates.new_price)
async def prod_add_price(m: Message, state: FSMContext):
    try:
        price = int((m.text or "").strip()); assert price>0
    except Exception: return await m.answer("أدخل رقم صحيح > 0.")
    await state.update_data(price=price); await state.set_state(ProdStates.new_desc)
    await m.answer("أرسل الوصف:")

@dp.message(ProdStates.new_desc)
async def prod_add_desc(m: Message, state: FSMContext):
    await state.update_data(description=(m.text or "").strip())
    await state.set_state(ProdStates.new_file)
    await m.answer("أرسل الملف كمستند (zip/rar/pdf…).")

@dp.message(ProdStates.new_file, F.document)
async def prod_add_file(m: Message, state: FSMContext):
    dtata = await state.get_data()
    code = dtata["code"]; title = dtata["title"]; price = dtata["price"]; desc = dtata["description"]
    filename = f"{code}_{m.document.file_name or 'file.bin'}"
    path = os.path.join(FILES_DIR, filename)
    await bot.download(m.document.file_id, destination=path)
    PRODUCTS[code] = {"title": title, "price": price, "description": desc,
                      "file_path": path, "photo_id": "", "enabled": True}
    save_products(); await state.clear()
    await m.answer(f"✅ تمت الإضافة: {title} — {price}\nملف: {path}\n(لتعيين صورة: لوحة التحكم → 🖼️ تعديل صورة)")

@dp.message(ProdStates.new_file)
async def prod_add_file_invalid(m: Message):
    await m.answer("أرسل الملف كمستند.")

@dp.callback_query(F.data == "admin:prod:edit")
async def prod_edit_pick(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    if not PRODUCTS: return await cq.message.answer("لا توجد منتجات.")
    await state.set_state(ProdStates.edit_pick_code)
    await cq.message.answer("اختر منتجًا للتعديل:", reply_markup=admin_select_product_kb("admin:prod:open"))
    await cq.answer()

@dp.callback_query(F.data.startswith("admin:prod:open:"))
async def prod_open_edit(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    code = cq.data.split(":",3)[3]
    p = PRODUCTS.get(code)
    if not p: return await cq.answer("غير موجود.", show_alert=True)
    await state.update_data(code=code)
    await cq.message.answer(
        f"تعديل: {p['title']} (code:{code})\nالسعر: {p['price']}\n"
        f"ملف: {p['file_path']}\nالوصف: {p['description']}",
        reply_markup=admin_edit_product_kb(code)
    ); await cq.answer()

@dp.callback_query(F.data.startswith("admin:prod:edit:title:"))
async def prod_edit_title(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await state.update_data(code=cq.data.split(":",3)[3]); await state.set_state(ProdStates.edit_set_title)
    await cq.message.answer("أرسل الاسم الجديد:"); await cq.answer()

@dp.message(ProdStates.edit_set_title)
async def _prod_set_title(m: Message, state: FSMContext):
    d = await state.get_data(); code = d["code"]
    if code not in PRODUCTS: await state.clear(); return await m.answer("غير موجود.")
    PRODUCTS[code]["title"] = (m.text or "").strip(); save_products()
    await state.clear(); await m.answer("تم تحديث الاسم ✅")

@dp.callback_query(F.data.startswith("admin:prod:edit:price:"))
async def prod_edit_price(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await state.update_data(code=cq.data.split(":",3)[3]); await state.set_state(ProdStates.edit_set_price)
    await cq.message.answer("أرسل السعر الجديد (رقم):"); await cq.answer()

@dp.message(ProdStates.edit_set_price)
async def _prod_set_price(m: Message, state: FSMContext):
    try:
        price = int((m.text or "").strip()); assert price>0
    except Exception: return await m.answer("أدخل رقم صحيح > 0.")
    d = await state.get_data(); code = d["code"]
    if code not in PRODUCTS: await state.clear(); return await m.answer("غير موجود.")
    PRODUCTS[code]["price"] = price; save_products()
    await state.clear(); await m.answer("تم تحديث السعر ✅")

@dp.callback_query(F.data.startswith("admin:prod:edit:desc:"))
async def prod_edit_desc(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await state.update_data(code=cq.data.split(":",3)[3]); await state.set_state(ProdStates.edit_set_desc)
    await cq.message.answer("أرسل الوصف الجديد:"); await cq.answer()

@dp.message(ProdStates.edit_set_desc)
async def _prod_set_desc(m: Message, state: FSMContext):
    d = await state.get_data(); code = d["code"]
    if code not in PRODUCTS: await state.clear(); return await m.answer("غير موجود.")
    PRODUCTS[code]["description"] = (m.text or "").strip(); save_products()
    await state.clear(); await m.answer("تم تحديث الوصف ✅")

@dp.callback_query(F.data.startswith("admin:prod:edit:file:"))
async def prod_edit_file(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await state.update_data(code=cq.data.split(":",3)[3]); await state.set_state(ProdStates.edit_set_file)
    await cq.message.answer("أرسل الملف الجديد كمستند:"); await cq.answer()

@dp.message(ProdStates.edit_set_file, F.document)
async def _prod_set_file(m: Message, state: FSMContext):
    d = await state.get_data(); code = d["code"]
    if code not in PRODUCTS: await state.clear(); return await m.answer("غير موجود.")
    filename = f"{code}_{m.document.file_name or 'file.bin'}"
    path = os.path.join(FILES_DIR, filename)
    await bot.download(m.document.file_id, destination=path)
    PRODUCTS[code]["file_path"] = path; save_products()
    await state.clear(); await m.answer(f"تم تحديث الملف ✅\n{path}")

@dp.message(ProdStates.edit_set_file)
async def _prod_set_file_invalid(m: Message):
    await m.answer("أرسل الملف كمستند.")

# ---- صور المنتجات
@dp.callback_query(F.data == "admin:prod:photo")
async def prod_photo_pick(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await state.set_state(ProdStates.photo_pick_code)
    await cq.message.answer("اختر المنتج لضبط صورته:", reply_markup=admin_select_product_kb("admin:prod:photo:set"))
    await cq.answer()

@dp.callback_query(F.data.startswith("admin:prod:photo:set:"))
async def prod_photo_wait(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    code = cq.data.split(":",3)[3]
    await state.update_data(code=code); await state.set_state(ProdStates.wait_photo)
    await cq.message.answer("أرسل الصورة الآن (ليست مستند)."); await cq.answer()

@dp.message(ProdStates.wait_photo, F.photo)
async def prod_photo_save(m: Message, state: FSMContext):
    d = await state.get_data(); code = d["code"]
    if code not in PRODUCTS: await state.clear(); return await m.answer("غير موجود.")
    PRODUCTS[code]["photo_id"] = m.photo[-1].file_id; save_products()
    await state.clear(); await m.answer("تم ضبط الصورة ✅")

@dp.message(ProdStates.wait_photo)
async def prod_photo_invalid(m: Message):
    await m.answer("أرسل صورة عادية (وليس ملف).")

# ---- تفعيل/تعطيل/حذف
@dp.callback_query(F.data == "admin:prod:toggle")
async def prod_toggle_menu(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await cq.message.answer("اختر منتجًا للتفعيل/التعطيل:", reply_markup=admin_select_product_kb("admin:prod:toggle:do"))
    await cq.answer()

@dp.callback_query(F.data.startswith("admin:prod:toggle:do:"))
async def prod_toggle_do(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    code = cq.data.split(":",3)[3]
    p = PRODUCTS.get(code)
    if not p: return await cq.answer("غير موجود.", show_alert=True)
    p["enabled"] = not p.get("enabled", True); save_products()
    await cq.message.answer(f"{p['title']} ➜ {'✅ مفعل' if p['enabled'] else '⛔ معطل'}"); await cq.answer()

@dp.callback_query(F.data == "admin:prod:delete")
async def prod_delete_menu(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await cq.message.answer("اختر منتجًا للحذف:", reply_markup=admin_select_product_kb("admin:prod:delete:do"))
    await cq.answer()

@dp.callback_query(F.data.startswith("admin:prod:delete:do:"))
async def prod_delete_do(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    code = cq.data.split(":",3)[3]
    if code in PRODUCTS:
        title = PRODUCTS[code]["title"]; del PRODUCTS[code]; save_products()
        await cq.message.answer(f"🗑️ تم حذف: {title}")
    else:
        await cq.message.answer("غير موجود.")
    await cq.answer()

# --- طرق الدفع
@dp.callback_query(F.data == "admin:payments")
async def payments_home(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await cq.message.answer("💳 إدارة طرق الدفع", reply_markup=payments_menu_kb()); await cq.answer()

@dp.callback_query(F.data == "admin:pay:list")
async def payments_list(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    pays = SETTINGS.get("payments", [])
    if not pays: return await cq.message.answer("لا توجد طرق دفع.")
    lines = ["📃 الطرق المتاحة:"]
    for pm in pays:
        lines.append(f"- {pm['name']}\n  التفاصيل: {pm['details']}\n  id:{pm['id']}")
    await cq.message.answer("\n\n".join(lines)); await cq.answer()

class PayStates(StatesGroup):
    add_name   = State(); add_details= State()
    edit_pick  = State(); edit_name  = State(); edit_details = State()
    del_pick   = State()

@dp.callback_query(F.data == "admin:pay:add")
async def pay_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await state.set_state(PayStates.add_name)
    await cq.message.answer("✏️ أرسل اسم الطريقة (مثال: USDT TRC20):"); await cq.answer()

@dp.message(PayStates.add_name)
async def pay_add_name(m: Message, state: FSMContext):
    name = (m.text or "").strip()
    if not name: return await m.answer("أرسل اسمًا صحيحًا.")
    await state.update_data(name=name)
    await state.set_state(PayStates.add_details)
    await m.answer("✏️ أرسل تفاصيل/عنوان الدفع (رقم/محفظة/رابط):")

@dp.message(PayStates.add_details)
async def pay_add_details(m: Message, state: FSMContext):
    details = (m.text or "").strip()
    if not details: return await m.answer("أرسل تفاصيل صحيحة.")
    data = await state.get_data()
    name = data["name"]
    pay_id = uuid.uuid4().hex[:6]
    SETTINGS.setdefault("payments", []).append({"id": pay_id, "name": name, "details": details})
    save_settings(); await state.clear()
    await m.answer(f"✅ تمت إضافة طريقة الدفع: {name}")

@dp.callback_query(F.data == "admin:pay:edit")
async def pay_edit_pick(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    if not SETTINGS.get("payments"): return await cq.message.answer("لا توجد طرق دفع.")
    await state.set_state(PayStates.edit_pick)
    await cq.message.answer("اختر طريقة لتعديلها:", reply_markup=payments_select_kb("admin:pay:open"))
    await cq.answer()

@dp.callback_query(F.data.startswith("admin:pay:open:"))
async def pay_edit_open(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    pid = cq.data.split(":",3)[3]
    pm = next((x for x in SETTINGS.get("payments",[]) if x["id"]==pid), None)
    if not pm: return await cq.answer("غير موجود.", show_alert=True)
    await state.update_data(pid=pid)
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ الاسم", callback_data="admin:pay:edit:name")
    kb.button(text="✏️ التفاصيل", callback_data="admin:pay:edit:details")
    kb.button(text="⬅️ رجوع", callback_data="admin:payments")
    kb.adjust(2,1)
    await cq.message.answer(f"تعديل طريقة الدفع:\nالاسم: {pm['name']}\nالتفاصيل: {pm['details']}", reply_markup=kb.as_markup())
    await cq.answer()

@dp.callback_query(F.data == "admin:pay:edit:name")
async def pay_edit_name(cq: CallbackQuery, state: FSMContext):
    await cq.message.answer("أرسل الاسم الجديد:"); await state.set_state(PayStates.edit_name); await cq.answer()

@dp.message(PayStates.edit_name)
async def pay_edit_name_set(m: Message, state: FSMContext):
    d = await state.get_data(); pid = d.get("pid")
    pm = next((x for x in SETTINGS.get("payments",[]) if x["id"]==pid), None)
    if not pm: await state.clear(); return await m.answer("غير موجود.")
    pm["name"] = (m.text or "").strip(); save_settings()
    await state.clear(); await m.answer("تم تحديث الاسم ✅")

@dp.callback_query(F.data == "admin:pay:edit:details")
async def pay_edit_details(cq: CallbackQuery, state: FSMContext):
    await cq.message.answer("أرسل التفاصيل/العنوان الجديد:"); await state.set_state(PayStates.edit_details); await cq.answer()

@dp.message(PayStates.edit_details)
async def pay_edit_details_set(m: Message, state: FSMContext):
    d = await state.get_data(); pid = d.get("pid")
    pm = next((x for x in SETTINGS.get("payments",[]) if x["id"]==pid), None)
    if not pm: await state.clear(); return await m.answer("غير موجود.")
    pm["details"] = (m.text or "").strip(); save_settings()
    await state.clear(); await m.answer("تم تحديث التفاصيل ✅")

@dp.callback_query(F.data == "admin:pay:del")
async def pay_del_pick(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    pays = SETTINGS.get("payments", [])
    if not pays: return await cq.message.answer("لا توجد طرق دفع.")
    await state.set_state(PayStates.del_pick)
    kb = payments_select_kb("admin:pay:del:do")
    await cq.message.answer("اختر طريقة لحذفها:", reply_markup=kb); await cq.answer()

@dp.callback_query(F.data.startswith("admin:pay:del:do:"))
async def pay_del_do(cq: CallbackQuery, state: FSMContext):
    pid = cq.data.split(":",4)[4]
    pays = SETTINGS.get("payments", [])
    idx = next((i for i,x in enumerate(pays) if x["id"]==pid), -1)
    if idx >= 0:
        name = pays[idx]["name"]; pays.pop(idx); save_settings()
        await cq.message.answer(f"🗑️ تم حذف طريقة الدفع: {name}")
    else:
        await cq.message.answer("غير موجود.")
    await cq.answer()

# --- الأدمنز
@dp.callback_query(F.data == "admin:admins")
async def admins_home(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await cq.message.answer("👥 إدارة الأدمنز", reply_markup=admins_menu_kb()); await cq.answer()

@dp.callback_query(F.data == "admin:admins:list")
async def admins_list(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    lines = ["قائمة الأدمنز:"]
    for uid in SETTINGS.get("admins", []):
        tag = "👑 مالك" if uid == OWNER_ID else "مشرف"
        lines.append(f"- {uid} ({tag})")
    await cq.message.answer("\n".join(lines)); await cq.answer()

@dp.callback_query(F.data == "admin:admins:add")
async def admins_add(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await state.set_state(AdminsStates.add_admin)
    await cq.message.answer("أرسل ID المستخدم (أرقام) أو مرّر رسالة منه (Forward).")
    await cq.answer()

@dp.message(AdminsStates.add_admin)
async def admins_add_handle(m: Message, state: FSMContext):
    uid = None
    if m.forward_from: uid = m.forward_from.id
    else:
        try: uid = int((m.text or "").strip())
        except Exception: pass
    if not uid: return await m.answer("تعذّر التعرف على الـID. أرسل رقم صحيح أو مرّر رسالة.")
    if uid in SETTINGS.get("admins", []):
        await state.clear(); return await m.answer("موجود مسبقًا كمشرف ✅")
    SETTINGS.setdefault("admins", []).append(uid); save_settings()
    await state.clear(); await m.answer(f"تمت إضافة {uid} كمشرف ✅")

@dp.callback_query(F.data == "admin:admins:remove")
async def admins_remove(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    admins = [a for a in SETTINGS.get("admins", []) if a != OWNER_ID]
    if not admins: return await cq.message.answer("لا يوجد مشرفون (غير المالك) لحذفهم.")
    kb = InlineKeyboardBuilder()
    for uid in admins:
        kb.button(text=f"حذف {uid}", callback_data=f"admin:admins:remove:{uid}")
    kb.button(text="⬅️ رجوع", callback_data="admin")
    kb.adjust(1)
    await cq.message.answer("اختر مشرفًا لحذفه:", reply_markup=kb.as_markup())
    await cq.answer()

@dp.callback_query(F.data.startswith("admin:admins:remove:"))
async def admins_remove_do(cq: CallbackQuery):
    uid = int(cq.data.split(":")[-1])
    if uid == OWNER_ID: return await cq.answer("لا يمكن حذف المالك.", show_alert=True)
    if uid in SETTINGS.get("admins", []):
        SETTINGS["admins"].remove(uid); save_settings()
        await cq.message.answer(f"تم حذف المشرف {uid} ✅")
    else:
        await cq.message.answer("غير موجود.")
    await cq.answer()

# --- الإعدادات العامة
@dp.callback_query(F.data == "admin:settings")
async def settings_home(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ رابط الدعم", callback_data="admin:settings:support")
    kb.button(text="⬅️ رجوع", callback_data="admin")
    kb.adjust(1)
    await cq.message.answer(f"الإعدادات:\n- رابط الدعم: {SETTINGS.get('support_url','')}", reply_markup=kb.as_markup())
    await cq.answer()

@dp.callback_query(F.data == "admin:settings:support")
async def settings_support(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    await state.set_state(SettingsStates.support_url)
    await cq.message.answer("أرسل رابط الدعم الجديد (يبدأ بـ http/https):"); await cq.answer()

@dp.message(SettingsStates.support_url)
async def settings_support_set(m: Message, state: FSMContext):
    url = (m.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return await m.answer("أرسل رابطًا صالحًا.")
    SETTINGS["support_url"] = url; save_settings()
    await state.clear(); await m.answer("تم تحديث رابط الدعم ✅")

# --- الطلبات
@dp.callback_query(F.data == "admin:orders")
async def orders_list(cq: CallbackQuery):
    if not is_admin(cq.from_user.id): return await cq.answer("غير مصرح.", show_alert=True)
    pending = [(k,v) for k,v in ORDERS.items() if v.get("status")=="awaiting_proof"]
    if not pending: return await cq.message.answer("لا توجد طلبات قيد المراجعة.")
    for oid, o in pending:
        await cq.message.answer(
            f"🧾 طلب\nOrder:{oid}\nعميل:{o['buyer_id']}\nمنتج:{o['product_title']}\nسعر:{o['price']}\nطريقة:{o['payment_method_name']}",
            reply_markup=review_kb(oid), parse_mode="Markdown"
        )
    await cq.answer()

# ============== Runner ==============
async def main():
    print("Store bot (manual payments) running...")
    save_settings()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
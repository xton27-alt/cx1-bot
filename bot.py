# -- coding: utf-8 --
# متجر روبوتات بدون نجوم + دفع يدوي بإثبات + موافقة أدمن + إرسال تلقائي
# لوحة تحكم كاملة (تظهر للأدمن فقط): منتجات / صور / أسعار / طرق دفع / إعدادات / أدمنز / طلبات
# Python 3.11+ | aiogram 3.13.1
# -- coding: utf-8 --
"""
بوت متجر بسيط — aiogram v3
يوفّر:
- عرض المنتجات و"شراء الآن"
- عند اختيار USDT(TRC20) يظهر عنوان الدفع فورًا (حل المشكلة)
- تسجيل المشتركين تلقائيًا عند /start
- تسجيل الطلبات وتعدادها
- لوحة تحكم للآدمن تعرض عدد المشتركين + عدد الطلبات
"""

import os, json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

#---------- الإعدادات ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT-YOUR-BOT-TOKEN")
ADMIN_ID  = int(os.getenv("ADMIN_ID", "123456789"))
USDT_ADDRESS = os.getenv("USDT_ADDRESS", "TUxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")  # TRC20

DATA_DIR = Path("files"); DATA_DIR.mkdir(exist_ok=True)
USERS_FILE  = DATA_DIR / "users.json"
ORDERS_FILE = DATA_DIR / "orders.json"

def _ensure_file(p: Path, default):
    if not p.exists(): p.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
def _load(p: Path):
    _ensure_file(p, []);  return json.loads(p.read_text(encoding="utf-8"))
def _save(p: Path, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def add_user(uid: int):
    users = _load(USERS_FILE)
    if uid not in users: users.append(uid); _save(USERS_FILE, users)
def users_count() -> int: return len(_load(USERS_FILE))

def add_order(uid: int, code: str, price: int) -> int:
    orders = _load(ORDERS_FILE)
    order_id = (orders[-1]["order_id"] + 1) if orders else 1
    orders.append({
        "order_id": order_id, "user_id": uid, "product_code": code, "price": price,
        "status": "pending", "payment_method": None, "created_at": datetime.utcnow().isoformat()
    })
    _save(ORDERS_FILE, orders);  return order_id
def set_order_payment(order_id: int, method: str, status="awaiting_payment"):
    orders = _load(ORDERS_FILE)
    for o in orders:
        if o["order_id"] == order_id:
            o["payment_method"] = method; o["status"] = status; break
    _save(ORDERS_FILE, orders)
def orders_count() -> int: return len(_load(ORDERS_FILE))

_ensure_file(USERS_FILE, []); _ensure_file(ORDERS_FILE, [])

# منتجات مثال
PRODUCTS: Dict[str, Dict[str, Any]] = {
    "gold_scalp":  {"title": "بوت الذهب — المضاربة",      "price": 10000},
    "gold_invest": {"title": "بوت الذهب — الاستثمار",      "price": 15000},
    "btc_scalp":   {"title": "بوت العملات الرقمية BTC — المضاربة", "price": 12000},
}

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp  = Dispatcher(storage=MemoryStorage())

#---------- لوحات ----------
def main_menu(is_admin=False):
    kb = [
        [InlineKeyboardButton(text="عرض الروبوتات 🛍️", callback_data="show_bots")],
        [InlineKeyboardButton(text="🆘 الدعم", url="https://t.me/")],
    ]
    if is_admin: kb.append([InlineKeyboardButton(text="لوحة التحكم ⚙️", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def products_menu():
    rows = [[InlineKeyboardButton(text=f"⭐ {p['title']} — {p['price']}", callback_data=f"prod:{code}")]
            for code, p in PRODUCTS.items()]
    rows.append([InlineKeyboardButton(text="رجوع ⬅️", callback_data="back_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def product_actions(code: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 شراء الآن", callback_data=f"buy:{code}")],
        [InlineKeyboardButton(text="قائمة المنتجات ⬅️", callback_data="show_bots")]
    ])

def payment_methods(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 USDT (TRC20)", callback_data=f"pay_usdt:{order_id}")],
        [InlineKeyboardButton(text="رجوع ⬅️", callback_data="show_bots")]
    ])

#---------- أوامر ----------
@dp.message(Command("start"))
async def start(m: Message):
    add_user(m.from_user.id)
    await m.answer(
        "أهلًا بك في متجر روبوتات التداول 👋\n• تصفح المنتجات: /bots\n• الدعم: /support",
        reply_markup=main_menu(is_admin=(m.from_user.id == ADMIN_ID))
    )

@dp.message(Command("bots"))
async def bots_cmd(m: Message):
    await m.answer("اختر منتجًا: 🛍️", reply_markup=products_menu())

@dp.message(Command("support"))
async def support_cmd(m: Message):
    await m.answer("راسلنا على الدعم: @your_support_username")

# لوحة تحكم
async def send_admin(chat_id: int):
    await bot.send_message(
        chat_id,
        f"لوحة التحكم ⚙️\n"
        f"• عدد المشتركين: <b>{users_count()}</b>\n"
        f"• عدد الطلبات: <b>{orders_count()}</b>\n\n"
        f"/bots — عرض المنتجات",
        reply_markup=main_menu(is_admin=True)
    )

@dp.message(Command("admin"))
async def admin_cmd(m: Message):
    if m.from_user.id == ADMIN_ID: await send_admin(m.chat.id)

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID: return await c.answer("غير مصرح", show_alert=True)
    await c.message.delete(); await send_admin(c.message.chat.id); await c.answer()

# تنقل
@dp.callback_query(F.data == "show_bots")
async def cb_show_bots(c: CallbackQuery):
    await c.message.edit_text("اختر منتجًا: 🛍️", reply_markup=products_menu()); await c.answer()

@dp.callback_query(F.data == "back_home")
async def cb_back_home(c: CallbackQuery):
    await c.message.edit_text("أهلًا بك في متجر روبوتات التداول 👋",
                              reply_markup=main_menu(is_admin=(c.from_user.id == ADMIN_ID)))
    await c.answer()

# عرض منتج
@dp.callback_query(F.data.startswith("prod:"))
async def cb_product(c: CallbackQuery):
    code = c.data.split(":", 1)[1]
    p = PRODUCTS.get(code)
    if not p: return await c.answer("المنتج غير موجود", show_alert=True)
    await c.message.edit_text(
        f"🛒 {p['title']}\nالسعر: <b>{p['price']}</b>\n\n"
        f"شراء {p['title']} — التسليم بعد تأكيد الدفع.",
        reply_markup=product_actions(code)
    ); await c.answer()

# شراء -> إنشاء طلب + طرق الدفع
@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(c: CallbackQuery):
    code = c.data.split(":", 1)[1]
    p = PRODUCTS.get(code)
    if not p: return await c.answer("المنتج غير موجود", show_alert=True)
    order_id = add_order(c.from_user.id, code, p["price"])
    await c.message.edit_text(
        f"اختر طريقة الدفع لشراء: {p['title']}\nالسعر: <b>{p['price']}</b>\n\nرقم الطلب: <code>{order_id}</code>",
        reply_markup=payment_methods(order_id)
    ); await c.answer()

# حل مشكلة زر USDT — إظهار العنوان مباشرة وتسجيل الطريقة
@dp.callback_query(F.data.startswith("pay_usdt:"))
async def cb_pay_usdt(c: CallbackQuery):
    order_id = int(c.data.split(":", 1)[1])
    set_order_payment(order_id, "USDT (TRC20)")
    await c.message.answer(
        "💰 عنوان الدفع عبر شبكة <b>TRC20</b>:\n"
        f"<code>{USDT_ADDRESS}</code>\n\n"
        "📩 بعد التحويل، أرسل إيصال الدفع للدعم.\n"
        f"🔎 رقم الطلب: <code>{order_id}</code>"
    )
    await c.answer("تم إظهار عنوان الدفع")

# تشغيل
async def on_startup(): print("Bot started.")
def main():
    from aiogram import asyncio
    dp.startup.register(on_startup)
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    main()

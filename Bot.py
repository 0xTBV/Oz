import sqlite3
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "-1002531653097"

# قاعدة البيانات
db_path = os.path.join(os.getcwd(), "referrals.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    referrals INTEGER DEFAULT 0,
    language TEXT DEFAULT 'ar'
)''')
conn.commit()

def get_user(user_id):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return c.fetchone()

def add_user(user_id, name, language='ar'):
    if not get_user(user_id):
        c.execute("INSERT INTO users (user_id, name, language) VALUES (?, ?, ?)", (user_id, name, language))
        conn.commit()

def increment_referral(referrer_id):
    c.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
    conn.commit()

def set_language(user_id, lang):
    c.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()

def get_language(user_id):
    c.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 'ar'

def get_referrals(user_id):
    c.execute("SELECT referrals FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 0

async def is_user_member(context: CallbackContext, user_id: int):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

messages = {
    'ar': {
        'welcome': "🎉 مرحبًا {name} 👋\n\nعليك الإشتراك في القناة للإستمتاع بمزايا البوت! ✅",
        'referral': "👥 عدد الأشخاص الذين قمت بإحالتهم: {count} 🔥",
        'link': "📌 شارك الرابط التالي مع أصدقائك:\nhttps://t.me/OzUSDTT_Bot?start={user_id}",
        'language_button': "تغيير اللغة",
        'language_changed': "تم تغيير اللغة إلى العربية.",
        'join_prompt': "⚠️ يجب الاشتراك في القناة لتفعيل البوت"
    },
    'en': {
        'welcome': "🎉 Welcome {name} 👋\n\nPlease join the channel to enjoy the bot features!",
        'referral': "👥 Number of people you referred: {count}",
        'link': "📌 Share this link with your friends:\nhttps://t.me/OzUSDTT_Bot?start={user_id}",
        'language_button': "Change language",
        'language_changed': "Language changed to English.",
        'join_prompt': "⚠️ You must join the channel to activate the bot."
    }
}

async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = user.id
    name = user.first_name

    lang = get_language(user_id)

    if not await is_user_member(context, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("اضغط هنا للإنضمام 📌", url="https://t.me/OzUSDTT")],
            [InlineKeyboardButton("تحقّق من الإشتراك", callback_data="check_join")]
        ])
        await update.message.reply_text(messages[lang]['join_prompt'], reply_markup=keyboard)
        return

    args = context.args
    referrer_id = int(args[0]) if args and args[0].isdigit() and int(args[0]) != user_id else None

    add_user(user_id, name)

    if referrer_id and get_user(referrer_id):
        increment_referral(referrer_id)

    text = messages[lang]['welcome'].format(name=name) + "\n\n"
    text += messages[lang]['referral'].format(count=get_referrals(user_id)) + "\n\n"
    text += messages[lang]['link'].format(user_id=user_id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(messages[lang]['language_button'], callback_data="toggle_lang")]
    ])

    await update.message.reply_text(text, reply_markup=keyboard)

async def toggle_language(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_language(user_id)
    new_lang = 'en' if lang == 'ar' else 'ar'
    set_language(user_id, new_lang)
    await query.answer()
    await query.edit_message_text(messages[new_lang]['language_changed'])

async def check_join_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    is_member = await is_user_member(context, user_id)

    if is_member:
        await query.message.delete()
        await start(update, context)
    else:
        await query.answer("⚠️ ما زلت غير مشترك بالقناة!", show_alert=True)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(toggle_language, pattern="toggle_lang"))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="check_join"))
    app.run_polling()

if __name__ == "__main__":
    main()

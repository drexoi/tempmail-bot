import os
import random
import string
import html
import sqlite3
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# ================= DUMMY WEB SERVER (RENDER KEEP-ALIVE) =================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Temp Mail Bot is active!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ================= CONFIGURATION =================
BOT_TOKEN = "8724616175:AAGwMfZ8EDCPwPnY4gF5xTVPrcfXWGBWi8A"
ADMIN_ID = 8671410379
UPI_ID = "Oxrehan11@oksbi"

CHANNELS = [
    {"chat_id": -1004447562202, "link": "https://t.me/+cJt33a-UDCw5YmVl"},
    {"chat_id": -1004374951317, "link": "https://t.me/+HkOcx5kbh01iZTE1"},
    {"chat_id": -1004291249317, "link": "https://t.me/OxRehanCyber"},
    {"chat_id": -1003782903063, "link": "https://t.me/+852hkOgj0UNlZGU9"}
]

FOOTER_TEXT = "\n\nany issues / feedback @OxRehann"
API_BASE = "https://www.1secmail.com/api/v1/"

bot = telebot.TeleBot(BOT_TOKEN)

# ================= DATABASE SETUP =================
conn = sqlite3.connect("tempmail_database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    credits INTEGER DEFAULT 1,
    is_permanent INTEGER DEFAULT 0,
    current_email TEXT DEFAULT NULL,
    referred_by INTEGER DEFAULT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS vouchers (
    code TEXT PRIMARY KEY,
    credits INTEGER,
    is_permanent INTEGER DEFAULT 0,
    max_uses INTEGER,
    used_count INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS voucher_redemptions (
    user_id INTEGER,
    code TEXT,
    PRIMARY KEY (user_id, code)
)
""")
conn.commit()

# ================= HELPER FUNCTIONS =================
def register_user(user_id, referrer_id=None):
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        ref_id = referrer_id if referrer_id and referrer_id != user_id else None
        cursor.execute(
            "INSERT INTO users (user_id, credits, is_permanent, referred_by) VALUES (?, 1, 0, ?)",
            (user_id, ref_id)
        )
        conn.commit()
        if ref_id:
            cursor.execute("UPDATE users SET credits = credits + 2 WHERE user_id = ?", (ref_id,))
            conn.commit()
            try:
                bot.send_message(
                    ref_id,
                    f"🎉 **Referral Success!**\nA user joined using your link. You received **+2 Credits**!{FOOTER_TEXT}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

def is_subscribed(user_id):
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch["chat_id"], user_id)
            if member.status not in ["member", "administrator", "creator", "restricted"]:
                return False
        except Exception:
            return False
    return True

def get_force_sub_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("🔹 Join 1", url=CHANNELS[0]["link"])
    b2 = types.InlineKeyboardButton("🔸 Join 2", url=CHANNELS[1]["link"])
    b3 = types.InlineKeyboardButton("⚡ Join 3", url=CHANNELS[2]["link"])
    b4 = types.InlineKeyboardButton("👑 Join 4", url=CHANNELS[3]["link"])
    markup.add(b1, b2)
    markup.add(b3, b4)
    markup.add(types.InlineKeyboardButton("✅ Verify Channels", callback_data="check_channels"))
    return markup

def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = types.KeyboardButton("📧 Generate Email")
    b2 = types.KeyboardButton("📬 Check Inbox")
    b3 = types.KeyboardButton("ℹ️ Current Mail")
    b4 = types.KeyboardButton("💰 Buy Credits")
    b5 = types.KeyboardButton("👥 Refer & Earn")
    b6 = types.KeyboardButton("🎁 Redeem Code")
    markup.add(b1, b2)
    markup.add(b3, b4)
    markup.add(b5, b6)
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("👑 Admin Panel"))
    return markup

def get_domains():
    try:
        res = requests.get(f"{API_BASE}?action=getDomainList", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return ["1secmail.com", "1secmail.net", "1secmail.org"]

def generate_temp_email():
    domains = get_domains()
    login = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domain = random.choice(domains)
    return login, domain

# ================= START COMMAND =================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        
    register_user(user_id, referrer_id)

    if not is_subscribed(user_id):
        bot.send_message(
            user_id,
            "🔒 **Access Locked!**\n\nPlease join our 4 official channels to use this bot:",
            reply_markup=get_force_sub_markup(),
            parse_mode="Markdown"
        )
        return

    cursor.execute("SELECT credits, is_permanent, current_email FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    credits, is_perm, active_email = data if data else (0, 0, None)
    status_str = "🌟 Permanent Access" if is_perm else f"⚡ {credits} Credits"

    welcome_text = (
        "👋 **Temp Mail Bot me aapka swagat hai!**\n\n"
        f"💎 **Account Plan:** {status_str}\n"
        f"📧 **Active Email:** `{active_email or 'None'}`\n\n"
        "Bina registration ke temporary emails create karein aur instant verification OTP receive karein."
        f"{FOOTER_TEXT}"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))

@bot.callback_query_handler(func=lambda call: call.data == "check_channels")
def verify_channels_callback(call):
    user_id = call.from_user.id
    if is_subscribed(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(user_id, "✅ Channels verified successfully!", reply_markup=get_main_keyboard(user_id))
    else:
        bot.answer_callback_query(call.id, "⚠️ Please join all 4 channels first!", show_alert=True)

# ================= MAIN BUTTON HANDLER =================
@bot.message_handler(content_types=['text'])
def handle_text_buttons(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip()

    if not is_subscribed(user_id):
        bot.send_message(chat_id, "🔒 Join channels first to unlock:", reply_markup=get_force_sub_markup())
        return

    # 1. Generate Email
    if text == "📧 Generate Email":
        cursor.execute("SELECT credits, is_permanent FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        credits, is_perm = row if row else (0, 0)

        if not is_perm and credits < 1:
            bot.send_message(chat_id, f"❌ **Insufficient Credits!**\n\nYou need 1 Credit to generate an email. Refer friends or buy credits.{FOOTER_TEXT}", parse_mode="Markdown")
            return

        login, domain = generate_temp_email()
        full_email = f"{login}@{domain}"

        if not is_perm:
            cursor.execute("UPDATE users SET credits = credits - 1, current_email = ? WHERE user_id = ?", (full_email, user_id))
        else:
            cursor.execute("UPDATE users SET current_email = ? WHERE user_id = ?", (full_email, user_id))
        conn.commit()

        resp = (
            f"🎉 **Aapka Temporary Email ready hai:**\n\n"
            f"`{full_email}`\n\n"
            f"_(Click karke copy karein. Verification mail aane par '📬 Check Inbox' dabayein.)_"
            f"{FOOTER_TEXT}"
        )
        bot.send_message(chat_id, resp, parse_mode="Markdown")

    # 2. Check Inbox
    elif text == "📬 Check Inbox":
        cursor.execute("SELECT current_email FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            bot.send_message(chat_id, f"❌ Pehle **📧 Generate Email** par click karke ek email create karein.{FOOTER_TEXT}")
            return

        full_email = row[0]
        login, domain = full_email.split("@")
        inbox_url = f"{API_BASE}?action=getMessages&login={login}&domain={domain}"

        try:
            res = requests.get(inbox_url, timeout=10).json()
            if not res:
                bot.send_message(
                    chat_id, 
                    f"📭 **Inbox Khali Hai!**\n\nEmail: `{full_email}`\nAbhi tak koi naya message nahi aaya."
                    f"{FOOTER_TEXT}", 
                    parse_mode="Markdown"
                )
                return

            markup = types.InlineKeyboardMarkup()
            summary = f"📬 **Inbox Messages ({len(res)}):**\n\n"
            
            for item in res[:10]:
                mail_id = item.get("id")
                from_user = item.get("from", "Unknown")
                subject = item.get("subject", "No Subject")
                date = item.get("date", "")

                summary += f"🔹 **From:** `{from_user}`\n**Subject:** {html.escape(subject)}\n**Date:** {date}\n\n"
                btn = types.InlineKeyboardButton(f"📖 Read: {subject[:20]}...", callback_data=f"read_{mail_id}")
                markup.add(btn)

            bot.send_message(chat_id, summary, parse_mode="Markdown", reply_markup=markup)

        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Inbox check karne me error aaya: {str(e)}{FOOTER_TEXT}")

    # 3. Current Mail
    elif text == "ℹ️ Current Mail":
        cursor.execute("SELECT current_email, credits, is_permanent FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        email = row[0] if row and row[0] else "None (Tap '📧 Generate Email')"
        creds = "Permanent" if row and row[2] else f"{row[1]} Credits"
        bot.send_message(chat_id, f"📧 **Active Email:** `{email}`\n💎 **Balance:** {creds}{FOOTER_TEXT}", parse_mode="Markdown")

    # 4. Buy Credits
    elif text == "💰 Buy Credits":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("⚡ ₹9 Plan (99 Credits)", callback_data="buy_9"),
            types.InlineKeyboardButton("👑 ₹29 Plan (Permanent Access)", callback_data="buy_29")
        )
        bot.send_message(
            chat_id,
            f"💰 **Choose Your Plan:**\n\n• **₹9** = 99 Credits\n• **₹29** = Permanent Lifetime Access{FOOTER_TEXT}",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    # 5. Refer & Earn
    elif text == "👥 Refer & Earn":
        bot_uname = bot.get_me().username
        link = f"https://t.me/{bot_uname}?start={user_id}"
        bot.send_message(
            chat_id,
            f"👥 **Refer & Earn Program!**\n\nInvite friends and receive **+2 Credits** per successful join!\n\n🔗 **Link:**\n`{link}`{FOOTER_TEXT}",
            parse_mode="Markdown"
        )

    # 6. Redeem Code
    elif text == "🎁 Redeem Code":
        msg = bot.send_message(chat_id, f"🎁 Please enter your voucher code below:{FOOTER_TEXT}")
        bot.register_next_step_handler(msg, process_code_redemption)

    # 7. Admin Panel
    elif text == "👑 Admin Panel" and user_id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📢 Broadcast to All Users", callback_data="btn_admin_bc"),
            types.InlineKeyboardButton("🎟️ Voucher Guide (/gen)", callback_data="btn_admin_gen_info")
        )
        bot.send_message(ADMIN_ID, f"👑 **Admin Panel**\n\nTotal Users: `{total}`\nUPI: `{UPI_ID}`", reply_markup=markup, parse_mode="Markdown")

# ================= READ EMAIL CONTENT =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("read_"))
def read_single_mail(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    mail_id = call.data.split("_")[1]

    cursor.execute("SELECT current_email FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        bot.answer_callback_query(call.id, "Session expired, please regenerate mail.")
        return

    login, domain = row[0].split("@")
    read_url = f"{API_BASE}?action=readMessage&login={login}&domain={domain}&id={mail_id}"

    try:
        data = requests.get(read_url, timeout=10).json()
        subject = data.get("subject", "No Subject")
        sender = data.get("from", "Unknown")
        date = data.get("date", "")
        text_body = data.get("textBody", "").strip() or data.get("body", "No Text Content")

        if len(text_body) > 3500:
            text_body = text_body[:3500] + "\n\n...[Truncated]"

        full_msg = (
            f"📨 **Subject:** {subject}\n"
            f"👤 **From:** `{sender}`\n"
            f"🕒 **Date:** {date}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{text_body}"
            f"{FOOTER_TEXT}"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, full_msg)

    except Exception as e:
        bot.answer_callback_query(call.id, "Mail open nahi ho paya!")
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# ================= BUY WORKFLOW & APPROVALS =================
@bot.callback_query_handler(func=lambda call: call.data in ["buy_9", "buy_29"])
def initiate_payment(call):
    user_id = call.from_user.id
    plan_name = "₹9 (99 Credits)" if call.data == "buy_9" else "₹29 (Permanent Access)"
    
    text = (
        f"💳 **Payment Request: {plan_name}**\n\n"
        f"Send payment to UPI ID:\n👉 `{UPI_ID}`\n\n"
        "After paying, reply directly with your **Payment Screenshot or UTR Number**."
        f"{FOOTER_TEXT}"
    )
    msg = bot.send_message(user_id, text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_payment_proof, plan_name)

def process_payment_proof(message, plan_name):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    approve_code = "app_9" if "₹9" in plan_name else "app_29"
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"{approve_code}_{user_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}")
    )

    admin_note = (
        f"🔔 **New Payment Submission!**\n\n"
        f"👤 User: `{user_id}` (@{message.from_user.username or 'NoUser'})\n"
        f"📦 Requested Plan: **{plan_name}**"
    )
    
    bot.send_message(ADMIN_ID, admin_note, parse_mode="Markdown")
    bot.copy_message(ADMIN_ID, user_id, message.message_id, reply_markup=markup)
    bot.send_message(user_id, f"✅ **Payment Submitted!**\n\nYour proof is sent to admin for verification.{FOOTER_TEXT}", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("app_9_", "app_29_", "rej_")))
def handle_admin_decision(call):
    if call.from_user.id != ADMIN_ID:
        return

    action = call.data
    if action.startswith("app_9_"):
        target_uid = int(action.replace("app_9_", ""))
        cursor.execute("UPDATE users SET credits = credits + 99 WHERE user_id = ?", (target_uid,))
        conn.commit()
        bot.edit_message_caption("✅ Approved: ₹9 Plan (99 Credits added).", ADMIN_ID, call.message.message_id)
        bot.send_message(target_uid, f"🎉 **Payment Verified!**\n\n99 Credits added to your account.{FOOTER_TEXT}", parse_mode="Markdown")

    elif action.startswith("app_29_"):
        target_uid = int(action.replace("app_29_", ""))
        cursor.execute("UPDATE users SET is_permanent = 1 WHERE user_id = ?", (target_uid,))
        conn.commit()
        bot.edit_message_caption("🌟 Approved: ₹29 Permanent Access granted.", ADMIN_ID, call.message.message_id)
        bot.send_message(target_uid, f"👑 **Payment Verified!**\n\nPermanent Lifetime Access is active on your account!{FOOTER_TEXT}", parse_mode="Markdown")

    elif action.startswith("rej_"):
        target_uid = int(action.replace("rej_", ""))
        bot.edit_message_caption("❌ Rejected.", ADMIN_ID, call.message.message_id)
        bot.send_message(target_uid, f"❌ **Payment Rejected!**\n\nInvalid proof or transaction not found. Contact @OxRehann.{FOOTER_TEXT}", parse_mode="Markdown")

# ================= REDEEM & /GEN WORKFLOW =================
def process_code_redemption(message):
    user_id = message.from_user.id
    code = message.text.strip()
    
    cursor.execute("SELECT credits, is_permanent, max_uses, used_count FROM vouchers WHERE code = ?", (code,))
    voucher = cursor.fetchone()
    
    if not voucher:
        bot.send_message(user_id, f"❌ Invalid voucher code.{FOOTER_TEXT}")
        return

    credits, is_perm, max_uses, used_count = voucher

    cursor.execute("SELECT 1 FROM voucher_redemptions WHERE user_id = ? AND code = ?", (user_id, code))
    if cursor.fetchone():
        bot.send_message(user_id, f"⚠️ You have already redeemed this code!{FOOTER_TEXT}")
        return

    if used_count >= max_uses:
        bot.send_message(user_id, f"❌ Code expired (usage limit reached).{FOOTER_TEXT}")
        return

    cursor.execute("INSERT INTO voucher_redemptions (user_id, code) VALUES (?, ?)", (user_id, code))
    cursor.execute("UPDATE vouchers SET used_count = used_count + 1 WHERE code = ?", (code,))
    
    if is_perm:
        cursor.execute("UPDATE users SET is_permanent = 1 WHERE user_id = ?", (user_id,))
        reward = "Permanent Lifetime Access"
    else:
        cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (credits, user_id))
        reward = f"{credits} Credits"

    conn.commit()
    bot.send_message(user_id, f"🎉 **Code Redeemed!**\n\nYou received: **{reward}**!{FOOTER_TEXT}", parse_mode="Markdown")

@bot.message_handler(commands=['gen'])
def generate_voucher_command(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 4:
        bot.send_message(ADMIN_ID, "⚠️ Format: `/gen <code> <credits/perm> <max_users>`\nExample: `/gen FREE50 50 10`", parse_mode="Markdown")
        return

    code = parts[1]
    cred_type = parts[2].lower()
    try:
        max_uses = int(parts[3])
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ Max users must be numeric.")
        return

    is_perm = 1 if cred_type == "perm" else 0
    cred_amt = 0 if is_perm else int(cred_type)

    cursor.execute(
        "INSERT OR REPLACE INTO vouchers (code, credits, is_permanent, max_uses, used_count) VALUES (?, ?, ?, ?, 0)",
        (code, cred_amt, is_perm, max_uses)
    )
    conn.commit()
    reward_text = "Permanent VIP Access" if is_perm else f"{cred_amt} Credits"
    bot.send_message(ADMIN_ID, f"✅ Created: `{code}` | Reward: {reward_text} | Max Users: {max_uses}", parse_mode="Markdown")

# ================= BROADCAST =================
@bot.callback_query_handler(func=lambda call: call.data == "btn_admin_gen_info")
def admin_gen_info(call):
    if call.from_user.id != ADMIN_ID:
        return
    bot.send_message(ADMIN_ID, "🎟️ Guide:\n• `/gen CODE 50 10`\n• `/gen CODE perm 1`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "btn_admin_bc")
def admin_broadcast_prompt(call):
    if call.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "📢 Send any message to broadcast:")
    bot.register_next_step_handler(msg, send_broadcast_all)

def send_broadcast_all(message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
        except Exception:
            pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {sent} users.")

# ================= RUN BOT =================
if __name__ == "__main__":
    print("🤖 Temp Mail Bot successfully started...")
    bot.infinity_polling(skip_pending=True)

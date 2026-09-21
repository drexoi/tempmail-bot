import os
import time
import random
import string
import sqlite3
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types

# ================= DUMMY WEB SERVER (RENDER & UPTIMEROBOT) =================
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
BOT_TOKEN = "8724616175:AAF0cEQ8FoNZRPIb7FI0neOrpVZxlg1XFfg"
ADMIN_ID = 8671410379
UPI_ID = "Oxrehan11@oksbi"

CHANNELS = [
    {"chat_id": -1004447562202, "link": "https://t.me/+cJt33a-UDCw5YmVl", "name": "Join 1"},
    {"chat_id": -1004374951317, "link": "https://t.me/+HkOcx5kbh01iZTE1", "name": "Join 2"},
    {"chat_id": -1004291249317, "link": "https://t.me/OxRehanCyber", "name": "Join 3"},
    {"chat_id": -1003782903063, "link": "https://t.me/+852hkOgj0UNlZGU9", "name": "Join 4"}
]

FOOTER_TEXT = "\n\nany issues / feedback @OxRehann"

bot = TeleBot(BOT_TOKEN)

# ================= DATABASE SETUP =================
conn = sqlite3.connect("tempmail_database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    credits INTEGER DEFAULT 1,
    is_permanent INTEGER DEFAULT 0,
    current_email TEXT DEFAULT NULL,
    account_token TEXT DEFAULT NULL,
    referred_by INTEGER DEFAULT NULL
)
""")

# Migration helper for existing databases
try:
    cursor.execute("ALTER TABLE users ADD COLUMN account_token TEXT DEFAULT NULL")
    conn.commit()
except Exception:
    pass

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
def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

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
    btn_gen = types.KeyboardButton("🎲 Generate Mail")
    btn_inbox = types.KeyboardButton("📬 Check Inbox / OTP")
    btn_balance = types.KeyboardButton("💳 Balance & Info")
    btn_buy = types.KeyboardButton("💰 Buy Credits")
    btn_refer = types.KeyboardButton("👥 Refer & Earn")
    btn_redeem = types.KeyboardButton("🎁 Redeem Code")
    markup.add(btn_gen, btn_inbox)
    markup.add(btn_balance, btn_buy)
    markup.add(btn_refer, btn_redeem)
    
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("👑 Admin Panel"))
    return markup

def get_user_status(user_id):
    cursor.execute("SELECT credits, is_permanent, current_email, account_token FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

# ================= TEMP MAIL ENGINE (MAIL.GW) =================
def create_temp_mailbox():
    headers = {"Content-Type": "application/json"}
    try:
        d_res = requests.get("https://api.mail.gw/domains", headers=headers, timeout=10)
        if d_res.status_code != 200:
            return None, None
        domains_data = d_res.json().get("hydra:member", [])
        if not domains_data:
            return None, None
        domain = domains_data[0]["domain"]
        
        username = f"user_{random_string(8)}"
        email_address = f"{username}@{domain}"
        password = f"P@{random_string(10)}"

        reg_payload = {"address": email_address, "password": password}
        reg_res = requests.post("https://api.mail.gw/accounts", json=reg_payload, headers=headers, timeout=10)
        if reg_res.status_code not in [200, 201]:
            return None, None

        token_res = requests.post("https://api.mail.gw/token", json=reg_payload, headers=headers, timeout=10)
        if token_res.status_code != 200:
            return None, None
        
        token = token_res.json().get("token")
        return email_address, token
    except Exception:
        return None, None

# ================= START & VERIFICATION =================
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        
    register_user(user_id, referrer_id)

    if not is_subscribed(user_id):
        bot.send_message(
            user_id,
            "🔒 **Access Locked!**\n\n"
            "Please join our 4 official channels below to unlock the bot and claim your free trial credit:",
            reply_markup=get_force_sub_markup()
        )
        return

    send_dashboard(user_id)

def send_dashboard(user_id):
    status = get_user_status(user_id)
    credits = status[0] if status else 0
    is_perm = status[1] if status else 0
    mail = status[2] if status and status[2] else "None (Tap 'Generate Mail')"
    perm_status = "🌟 Permanent Access Active" if is_perm else f"⚡ {credits} Credits Available"

    text = (
        "🚀 **Welcome to Professional Temp Mail Bot!**\n\n"
        f"📧 **Current Email:** `{mail}`\n"
        f"💎 **Account Plan:** {perm_status}\n\n"
        "Generate throwaway email addresses and fetch OTP/Verification codes instantly."
        f"{FOOTER_TEXT}"
    )
    bot.send_message(user_id, text, reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_channels")
def verify_channels_callback(call):
    user_id = call.from_user.id
    if is_subscribed(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_dashboard(user_id)
    else:
        bot.answer_callback_query(
            call.id,
            "⚠️ Access Denied! Please join all 4 required channels before verifying.",
            show_alert=True
        )

# ================= TEMP MAIL ACTIONS =================
@bot.message_handler(func=lambda msg: msg.text == "🎲 Generate Mail")
def generate_mail(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        bot.send_message(user_id, "⚠️ Join channels first!", reply_markup=get_force_sub_markup())
        return

    status = get_user_status(user_id)
    if not status:
        return
    credits, is_perm, _, _ = status

    if not is_perm and credits < 1:
        bot.send_message(
            user_id,
            f"❌ **Insufficient Credits!**\n\nYou need 1 Credit to generate an email. Refer friends or buy credits.{FOOTER_TEXT}",
            parse_mode="Markdown"
        )
        return

    wait_msg = bot.send_message(user_id, "⏳ Generating temporary mailbox...")
    new_mail, token = create_temp_mailbox()

    if not new_mail:
        bot.edit_message_text(f"⚠️ Mail service is temporarily busy. Please tap again in a moment.{FOOTER_TEXT}", user_id, wait_msg.message_id)
        return

    if not is_perm:
        cursor.execute(
            "UPDATE users SET credits = credits - 1, current_email = ?, account_token = ? WHERE user_id = ?",
            (new_mail, token, user_id)
        )
    else:
        cursor.execute(
            "UPDATE users SET current_email = ?, account_token = ? WHERE user_id = ?",
            (new_mail, token, user_id)
        )
    conn.commit()

    bot.delete_message(user_id, wait_msg.message_id)
    bot.send_message(
        user_id,
        f"✅ **New Temporary Email Ready!**\n\n"
        f"📧 `{new_mail}`\n\n"
        "*(Tap the email address above to copy it)*\n\n"
        "Send your OTP or confirmation to this address, then click **📬 Check Inbox / OTP**."
        f"{FOOTER_TEXT}",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "📬 Check Inbox / OTP")
def check_inbox(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        bot.send_message(user_id, "⚠️ Join channels first!", reply_markup=get_force_sub_markup())
        return

    status = get_user_status(user_id)
    if not status or not status[2] or not status[3]:
        bot.send_message(user_id, f"⚠️ You haven't generated an email yet! Tap '🎲 Generate Mail'.{FOOTER_TEXT}")
        return

    mail, token = status[2], status[3]
    headers = {"Authorization": f"Bearer {token}"}

    try:
        res = requests.get("https://api.mail.gw/messages", headers=headers, timeout=10)
        msgs_data = res.json().get("hydra:member", [])
    except Exception:
        bot.send_message(user_id, f"⚠️ Error fetching inbox. Please try again.{FOOTER_TEXT}")
        return

    if not msgs_data:
        bot.send_message(
            user_id,
            f"📭 **Inbox is Empty**\n\nTarget Email: `{mail}`\nNo incoming messages yet. Send OTP and check again."
            f"{FOOTER_TEXT}",
            parse_mode="Markdown"
        )
        return

    for item in msgs_data[:3]:
        m_id = item["id"]
        detail_res = requests.get(f"https://api.mail.gw/messages/{m_id}", headers=headers, timeout=10)
        detail = detail_res.json()
        
        sender = detail.get("from", {}).get("address", "Unknown Sender")
        subject = detail.get("subject", "No Subject")
        text_body = detail.get("text", detail.get("intro", "No Body Text")).strip()

        content = (
            f"📩 **New Message / OTP Received!**\n\n"
            f"👤 **From:** `{sender}`\n"
            f"📝 **Subject:** `{subject}`\n\n"
            f"📄 **Message:**\n`{text_body[:800]}`"
            f"{FOOTER_TEXT}"
        )
        bot.send_message(user_id, content, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "💳 Balance & Info")
def balance_info(message):
    user_id = message.from_user.id
    status = get_user_status(user_id)
    credits, is_perm, mail, _ = status
    perm = "Yes (Lifetime Unlimited)" if is_perm else "No"
    bot_info = bot.get_me().username
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
    total_refs = cursor.fetchone()[0]

    text = (
        f"📊 **Your Account Summary:**\n\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"💎 **Credits Balance:** `{credits}`\n"
        f"🌟 **Permanent Access:** `{perm}`\n"
        f"👥 **Total Referrals:** `{total_refs}`\n"
        f"📧 **Active Mail:** `{mail or 'None'}`\n\n"
        f"🔗 **Your Referral Link:**\n`https://t.me/{bot_info}?start={user_id}`"
        f"{FOOTER_TEXT}"
    )
    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "👥 Refer & Earn")
def refer_earn(message):
    user_id = message.from_user.id
    bot_info = bot.get_me().username
    link = f"https://t.me/{bot_info}?start={user_id}"
    bot.send_message(
        user_id,
        f"👥 **Refer & Earn Program!**\n\n"
        "Invite your friends to use this bot and receive **+2 Credits** per successful invite!\n\n"
        f"🔗 **Your Referral Link:**\n`{link}`"
        f"{FOOTER_TEXT}",
        parse_mode="Markdown"
    )

# ================= BUY & PAYMENT WORKFLOW =================
@bot.message_handler(func=lambda msg: msg.text == "💰 Buy Credits")
def buy_credits_menu(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⚡ ₹9 Plan (99 Credits)", callback_data="buy_9"),
        types.InlineKeyboardButton("👑 ₹29 Plan (Permanent Access)", callback_data="buy_29")
    )
    bot.send_message(
        user_id,
        "💰 **Choose Your Plan:**\n\n"
        "• **Starter:** ₹9 for 99 Credits\n"
        "• **VIP:** ₹29 for Permanent Lifetime Access (Unlimited)"
        f"{FOOTER_TEXT}",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data in ["buy_9", "buy_29"])
def initiate_payment(call):
    user_id = call.from_user.id
    plan_name = "₹9 (99 Credits)" if call.data == "buy_9" else "₹29 (Permanent Access)"
    
    text = (
        f"💳 **Payment Request: {plan_name}**\n\n"
        f"Send the payment to UPI ID:\n👉 `{UPI_ID}`\n\n"
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
    
    bot.send_message(
        user_id,
        f"✅ **Payment Submitted!**\n\nYour proof has been forwarded to the admin. Your plan will activate within minutes upon verification.{FOOTER_TEXT}",
        parse_mode="Markdown"
    )

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
        bot.send_message(target_uid, f"🎉 **Payment Verified!**\n\n99 Credits have been credited to your balance.{FOOTER_TEXT}", parse_mode="Markdown")

    elif action.startswith("app_29_"):
        target_uid = int(action.replace("app_29_", ""))
        cursor.execute("UPDATE users SET is_permanent = 1 WHERE user_id = ?", (target_uid,))
        conn.commit()
        bot.edit_message_caption("🌟 Approved: ₹29 Permanent VIP Access granted.", ADMIN_ID, call.message.message_id)
        bot.send_message(target_uid, f"👑 **Payment Verified!**\n\nPermanent Lifetime Access is now active on your account!{FOOTER_TEXT}", parse_mode="Markdown")

    elif action.startswith("rej_"):
        target_uid = int(action.replace("rej_", ""))
        bot.edit_message_caption("❌ Rejected.", ADMIN_ID, call.message.message_id)
        bot.send_message(target_uid, f"❌ **Payment Rejected!**\n\nThe submitted proof was invalid or could not be verified. Contact @OxRehann.{FOOTER_TEXT}", parse_mode="Markdown")

# ================= REDEEM & /GEN WORKFLOW =================
@bot.message_handler(func=lambda msg: msg.text == "🎁 Redeem Code")
def redeem_prompt(message):
    user_id = message.from_user.id
    msg = bot.send_message(user_id, f"🎁 Please send your redeem code below:{FOOTER_TEXT}")
    bot.register_next_step_handler(msg, process_code_redemption)

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
        bot.send_message(user_id, f"❌ This voucher code has expired (usage limit reached).{FOOTER_TEXT}")
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
    bot.send_message(user_id, f"🎉 **Code Redeemed Successfully!**\n\nYou received: **{reward}**!{FOOTER_TEXT}", parse_mode="Markdown")

# Admin /gen command: /gen <code> <credits/perm> <max_devices>
@bot.message_handler(commands=['gen'])
def generate_voucher_command(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 4:
        bot.send_message(
            ADMIN_ID,
            "⚠️ **Format:** `/gen <code> <credits/perm> <max_users>`\n\n"
            "Example 1: `/gen Ox1Rt5 100 5` (100 credits for 5 users)\n"
            "Example 2: `/gen VIPPERM perm 1` (Permanent for 1 user)",
            parse_mode="Markdown"
        )
        return

    code = parts[1]
    cred_type = parts[2].lower()
    try:
        max_uses = int(parts[3])
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ Max users must be a numeric integer.")
        return

    is_perm = 1 if cred_type == "perm" else 0
    cred_amt = 0 if is_perm else int(cred_type)

    cursor.execute(
        "INSERT OR REPLACE INTO vouchers (code, credits, is_permanent, max_uses, used_count) VALUES (?, ?, ?, ?, 0)",
     (code, cred_amt, is_perm, max_uses)
    )
    conn.commit()

    reward_text = "Permanent VIP Access" if is_perm else f"{cred_amt} Credits"
    bot.send_message(
        ADMIN_ID,
        f"✅ **Voucher Created!**\n\n"
        f"🔑 Code: `{code}`\n"
        f"🎁 Reward: **{reward_text}**\n"
        f"👥 Max Usable Users: **{max_uses}**",
        parse_mode="Markdown"
    )

# ================= ADMIN DASHBOARD & BROADCAST =================
@bot.message_handler(func=lambda msg: msg.text in ["👑 Admin Panel", "/admin"])
def admin_menu(message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Broadcast to All Users", callback_data="btn_admin_bc"),
        types.InlineKeyboardButton("🎟️ Create Code Guide (/gen)", callback_data="btn_admin_gen_info")
    )
    bot.send_message(
        ADMIN_ID,
        f"👑 **Admin Control Center**\n\n"
        f"👥 Registered Users: `{total_users}`\n"
        f"💳 Primary UPI: `{UPI_ID}`",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "btn_admin_gen_info")
def admin_gen_info(call):
    if call.from_user.id != ADMIN_ID:
        return
    bot.send_message(
        ADMIN_ID,
        "🎟️ **Voucher Generator Command Guide:**\n\n"
        "• `/gen <code> <credits> <max_users>`\n"
        "• Example: `/gen FREE50 50 10`\n"
        "• Example Permanent: `/gen OXLIFETIME perm 1`",
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "btn_admin_bc")
def admin_broadcast_prompt(call):
    if call.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "📢 Send any Text, Photo, Video, or Document to broadcast to all users:")
    bot.register_next_step_handler(msg, send_broadcast_all)

def send_broadcast_all(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent, failed = 0, 0
    bot.send_message(ADMIN_ID, f"⏳ Broadcasting message to {len(users)} users...")

    for (uid,) in users:
        try:
            bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
        except Exception:
            failed += 1

    bot.send_message(ADMIN_ID, f"✅ **Broadcast Finished!**\n\nSent: {sent}\nFailed: {failed}")

# ================= RUN BOT =================
if __name__ == "__main__":
    print("Temp Mail Bot is online...")
    bot.infinity_polling(skip_pending=True)

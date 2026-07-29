import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import json
import os
import time
import asyncio
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread

# ==============================================================================
# --- 0. CẤU HÌNH ROLE TOP TUẦN ---
# ==============================================================================
ROLE_TOP1_ID = 123456789012345678  # Thay ID Role Top 1 của bạn
ROLE_TOP2_ID = 123456789012345678  # Thay ID Role Top 2 của bạn
ROLE_TOP3_ID = 123456789012345678  # Thay ID Role Top 3 của bạn

# --- 1. WEB SERVER GIỮ BOT ONLINE 24/7 ---
app = Flask('')

@app.route('/')
def home():
    return "Bot System is Online & Running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. QUẢN LÝ CƠ SỞ DỮ LIỆU (JSON) ---
DATA_FILE = "user_points.json"
TITLES_FILE = "titles_config.json"
PETS_FILE = "user_pets.json"
CONFIG_FILE = "config.json"
SHOP_FILE = "fishing_shop.json"
TRIVIA_FILE = "trivia_questions.json"

def safe_load_json(file_path, default_data):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Lỗi đọc file {file_path}: {e}")
            return default_data
    return default_data

def safe_save_json(file_path, data):
    temp_file = f"{file_path}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(temp_file, file_path)
    except Exception as e:
        print(f"[ERROR] Lỗi ghi file {file_path}: {e}")

def load_data(): return safe_load_json(DATA_FILE, {})
def save_data(data): safe_save_json(DATA_FILE, data)

def load_pets(): return safe_load_json(PETS_FILE, {})
def save_pets(data): safe_save_json(PETS_FILE, data)

def load_config(): return safe_load_json(CONFIG_FILE, {"game_channel_id": None})
def save_config(cfg): safe_save_json(CONFIG_FILE, cfg)

def load_titles():
    default_titles = {
        "1": {"icon": "👑", "name": "Đoàn Trưởng"},
        "2": {"icon": "⚔️", "name": "Thần Thương"},
        "3": {"icon": "🐎", "name": "Kị Vương"}
    }
    return safe_load_json(TITLES_FILE, default_titles)

def save_titles(titles): safe_save_json(TITLES_FILE, titles)

def load_trivia():
    default_trivia = [
        {"q": "Trong một cuộc thi chạy, nếu bạn vượt qua người đang đứng thứ hai, bạn sẽ đứng thứ mấy?", "a": ["thứ hai", "thứ 2", "2", "thu hai"]},
        {"q": "Bố của Mary có 5 cô con gái: Nana, Nene, Nini, Nono. Hỏi cô con gái thứ 5 tên là gì?", "a": ["mary", "tên là mary", "cô con gái thứ 5 tên là mary"]},
        {"q": "Có một chiếc xe tải đi vào đường cấm, dù đi qua trước mặt rất nhiều cảnh sát giao thông nhưng không ai phạt. Hỏi tại sao?", "a": ["đi bộ", "bác tài đi bộ", "tài xế đi bộ"]},
        {"q": "Lớp học có 30 học sinh, cô giáo chia đều thành 5 tổ. Hỏi có tổng cộng bao nhiêu cái chân bước vào lớp nếu tất cả đều có mặt?", "a": ["2", "2 chân", "hai chân"]},
        {"q": "Có 3 quả táo trên bàn, bạn lấy đi 2 quả. Hỏi bạn còn bao nhiêu quả táo?", "a": ["2", "2 quả", "hai quả"]},
        {"q": "Cái gì người nghèo có, người giàu muốn có, nhưng nếu bạn ăn vô sẽ chết?", "a": ["không có gì", "khong co gi"]},
        {"q": "Càng thâu lại càng to là cái gì?", "a": ["cái lỗ", "lỗ"]},
        {"q": "Con gì đập thì sống, không đập thì chết?", "a": ["con tim", "trái tim", "tim"]},
        {"q": "Lịch nào dài nhất?", "a": ["lịch sử"]}
    ]
    return safe_load_json(TRIVIA_FILE, default_trivia)

def save_trivia(data): safe_save_json(TRIVIA_FILE, data)

def add_points(user_id: str, amount: int):
    data = load_data()
    if user_id not in data:
        data[user_id] = {"weekly": 0, "total": 0, "titles": []}
    
    data[user_id]["weekly"] = max(0, data[user_id].get("weekly", 0) + amount)
    if amount > 0:
        data[user_id]["total"] = data[user_id].get("total", 0) + amount
    
    save_data(data)
    return data[user_id]["weekly"]

def add_custom_title(user_id: str, title_str: str):
    data = load_data()
    if user_id not in data:
        data[user_id] = {"weekly": 0, "total": 0, "titles": []}
    if "titles" not in data[user_id]:
        data[user_id]["titles"] = []
    if title_str not in data[user_id]["titles"]:
        data[user_id]["titles"].append(title_str)
        save_data(data)

chat_cooldowns = {}

# --- 3. CẤU HÌNH BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def process_weekly_rewards():
    data = load_data()
    if not data:
        return "❌ Không có dữ liệu điểm tuần để chốt."

    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:3]
    summary_lines = []
    
    for guild in bot.guilds:
        roles = [
            guild.get_role(ROLE_TOP1_ID),
            guild.get_role(ROLE_TOP2_ID),
            guild.get_role(ROLE_TOP3_ID)
        ]
        
        for role in roles:
            if role:
                for member in role.members:
                    try:
                        await member.remove_roles(role)
                    except Exception as e:
                        print(f"[WARN] Không thể gỡ role {role.name}: {e}")

        for index, (u_id, score) in enumerate(sorted_users):
            member = guild.get_member(int(u_id))
            target_role = roles[index] if index < len(roles) else None
            
            if member:
                if target_role:
                    try:
                        await member.add_roles(target_role)
                    except Exception as e:
                        print(f"[WARN] Không thể trao role: {e}")
                summary_lines.append(f"🥇 **Top {index+1}:** {member.mention} — `{score.get('weekly', 0)} điểm`")

    for u_id in data:
        data[u_id]["weekly"] = 0
    save_data(data)
    
    return "\n".join(summary_lines) if summary_lines else "Không tìm thấy thành viên Top trong Server."

# --- 4. TASK TỰ ĐỘNG CHẠY NGẦM ---

@tasks.loop(minutes=1)
async def auto_daily_leaderboard():
    vietnam_tz = timezone(timedelta(hours=7))
    now = datetime.now(vietnam_tz)
    
    if now.hour == 8 and now.minute == 0:
        cfg = load_config()
        channel_id = cfg.get("game_channel_id")
        if not channel_id: return
            
        channel = bot.get_channel(channel_id)
        if not channel: return
            
        data = load_data()
        titles = load_titles()
        sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:10]
        
        embed = discord.Embed(
            title="☀️ BẢNG XẾP HẠNG ĐIỂM TUẦN HÀNG NGÀY ☀️",
            description="Được tự động cập nhật lúc 08:00 sáng mỗi ngày.",
            color=discord.Color.gold(),
            timestamp=now
        )
        
        desc = ""
        for index, (u_id, score) in enumerate(sorted_users, 1):
            user = bot.get_user(int(u_id))
            name = user.mention if user else f"User <@{u_id}>"
            
            icon = "🔹"
            if str(index) in titles:
                t_icon = titles[str(index)]["icon"]
                t_name = titles[str(index)]["name"]
                icon = f"{t_icon} **[{t_name}]**"
            
            desc += f"`#{index}` {icon} {name} — **{score.get('weekly', 0)}** điểm\n"
            
        embed.add_field(name="🏆 Top Cống Hiến", value=desc if desc else "Chưa có dữ liệu.", inline=False)
        embed.set_footer(text="Hệ thống tích điểm tự động")
        await channel.send(embed=embed)

@tasks.loop(minutes=1)
async def auto_reset_weekly_top():
    vietnam_tz = timezone(timedelta(hours=7))
    now = datetime.now(vietnam_tz)
    
    if now.weekday() == 0 and now.hour == 0 and now.minute == 0:
        msg = await process_weekly_rewards()
        cfg = load_config()
        channel_id = cfg.get("game_channel_id")
        if channel_id:
            channel = bot.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="🎉 KẾT QUẢ ĐUA TOP TUẦN & RESET ĐIỂM 🎉",
                    description=f"Chúc mừng các thành viên xuất sắc nhất tuần qua!\n\n{msg}",
                    color=discord.Color.green(),
                    timestamp=now
                )
                await channel.send(embed=embed)

@tasks.loop(minutes=5)
async def check_voice_points():
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            members = [m for m in vc.members if not m.bot and not m.voice.deaf and not m.voice.self_deaf]
            for member in members:
                add_points(str(member.id), 5)

@tasks.loop(hours=1)
async def auto_minigame_task():
    try:
        cfg = load_config()
        channel_id = cfg.get("game_channel_id")
        if not channel_id: 
            return
        
        channel = bot.get_channel(channel_id)
        if not channel: 
            return
        
        trivia_list = load_trivia()
        if not trivia_list: 
            return
        
        item = random.choice(trivia_list)
        valid_ans = item["a"]
        
        embed = discord.Embed(
            title="🎯 MINI-GAME HÀNG GIỜ: ĐỐ VUI MẸO",
            description=f"❓ **Câu hỏi:** {item['q']}\n\n⚡ *Gõ câu trả lời vào chat trong 45s để nhận ngay **+30 điểm**!*",
            color=discord.Color.blue()
        )

        await channel.send(embed=embed)

        def check(m):
            return (
                m.channel == channel 
                and not m.bot 
                and m.content.strip().lower() in [ans.lower() for ans in valid_ans]
            )

        try:
            msg = await bot.wait_for('message', timeout=45.0, check=check)
            new_score = add_points(str(msg.author.id), 30)
            await channel.send(f"🎉 Chúc mừng {msg.author.mention} trả lời đúng đầu tiên! Bạn nhận được **+30 điểm** (Điểm tuần: `{new_score}`).")
        except asyncio.TimeoutError:
            first_ans = valid_ans[0]
            await channel.send(f"⏰ Đã hết 45 giây mà chưa có ai trả lời đúng! Đáp án chính xác là: **{first_ans}**")

    except Exception as e:
        print(f"[WARN] Lỗi xảy ra trong auto_minigame_task: {e}")

@auto_minigame_task.before_loop
async def before_minigame():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f"[SYSTEM] Bot đã đăng nhập thành công: {bot.user}")
    
    if not check_voice_points.is_running(): check_voice_points.start()
    if not auto_minigame_task.is_running(): auto_minigame_task.start()
    if not auto_reset_weekly_top.is_running(): auto_reset_weekly_top.start()
    if not auto_daily_leaderboard.is_running(): auto_daily_leaderboard.start()
        
    try:
        synced = await bot.tree.sync()
        print(f"[SYSTEM] Đã đồng bộ thành công {len(synced)} lệnh Slash (/)...")
    except Exception as e:
        print(f"[ERROR] Lỗi đồng bộ lệnh Slash: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    
    user_id = str(message.author.id)
    current_time = time.time()
    
    if user_id not in chat_cooldowns or (current_time - chat_cooldowns[user_id]) >= 60:
        pts = random.randint(1, 3)
        add_points(user_id, pts)
        chat_cooldowns[user_id] = current_time
        
    await bot.process_commands(message)

# ==============================================================================
# --- 5. HỆ THỐNG /CAUSONG & SHOP CẦN/MỒI CÂU ---
# ==============================================================================

FISHING_ITEMS = {
    "moi_canh_gio": {"name": "🪽 Mồi cánh gió", "type": "moi", "rarity": "thuong", "price": 100, "succ_bonus": 0.01, "rare_bonus": 0},
    "moi_sao": {"name": "✨ Mồi sao", "type": "moi", "rarity": "hiem", "price": 200, "succ_bonus": 0.10, "rare_bonus": 0.10},
    "moi_sumo": {"name": "🥞 Mồi sumo", "type": "moi", "rarity": "su_thi", "price": 10000, "succ_bonus": 0.12, "epic_bonus": 0.11},
    "moi_tien_ca": {"name": "🧜 Mồi nàng tiên cá", "type": "moi", "rarity": "than_thoai", "price": 25000, "succ_bonus": 0.16, "mythic_bonus": 0.05},
    
    "can_banh_mi": {"name": "🥖 Cần bánh mì", "type": "can", "rarity": "thuong", "price": 10, "succ_bonus": 0},
    "can_set": {"name": "⚡ Cần sét", "type": "can", "rarity": "hiem", "price": 100, "succ_bonus": 0.01},
    "can_lua": {"name": "🔥 Cần lửa", "type": "can", "rarity": "hiem", "price": 1000, "succ_bonus": 0.03}
}

FISH_TABLE = [
    {"id": "ro_dong", "name": "🐟 Cá Rô Đồng", "type": "thuong", "pts": 10, "weight": 50},
    {"id": "chep_vang", "name": "🐠 Cá Chép Vàng", "type": "thuong", "pts": 10, "weight": 50},
    {"id": "ca_tam", "name": "🦈 Cá Tầm", "type": "thuong", "pts": 10, "weight": 50},
    {"id": "chim_cut", "name": "🐧 Chim Cút", "type": "thuong", "pts": 20, "weight": 50},
    
    {"id": "giay_rach", "name": "👞 Giày Cũ Bị Rách", "type": "xui", "pts": -100, "weight": 40},
    {"id": "ruong_bau", "name": "👑 Rương Báu Dưới Sông", "type": "hiem", "pts": 100, "weight": 40},
    {"id": "bach_tuoc", "name": "🐙 Bạch tuộc", "type": "hiem", "pts": 60, "weight": 40},
    {"id": "rua_con", "name": "🐢 Rùa con", "type": "hiem", "pts": 70, "weight": 40},
    
    {"id": "tieu_long_cau", "name": "🦭 Tiểu long cẩu", "type": "su_thi", "pts": 200, "weight": 20},
    {"id": "tom_suki", "name": "🦞 Tôm suki", "type": "su_thi", "pts": 210, "weight": 19},
    {"id": "light_suki", "name": "⭐ Light suki", "type": "su_thi", "pts": 220, "weight": 15},
    
    {"id": "voi_sat_than", "name": "🫍 Cá voi sát thần", "type": "than_thoai", "pts": 500, "title": "🛡️ Sát Long", "weight": 1.0},
    {"id": "virus_tu_than", "name": "🦠 Virut tử thần", "type": "than_thoai", "pts": 1000, "title": "👑 Virut Vương", "weight": 0.5},
    {"id": "leviathan", "name": "🐉 Leviathan", "type": "than_thoai", "pts": 2000, "title": "🌊 Leviathan", "weight": 0.1}
]

@bot.tree.command(name="causong", description="Thư giãn đi câu cá bờ sông nhận điểm thưởng!")
@app_commands.checks.cooldown(1, 60)
async def causong(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_pets_data = load_pets()
    user_inventory = user_pets_data.get(user_id, {}).get("inventory", {})

    base_success_rate = 0.45
    
    active_moi = user_inventory.get("active_moi")
    active_can = user_inventory.get("active_can")
    
    if active_moi and active_moi in FISHING_ITEMS:
        base_success_rate += FISHING_ITEMS[active_moi].get("succ_bonus", 0)
    if active_can and active_can in FISHING_ITEMS:
        base_success_rate += FISHING_ITEMS[active_can].get("succ_bonus", 0)

    if random.random() > base_success_rate:
        await interaction.response.send_message("🎣 **Rất tiếc!** Bạn đã quăng cần nhưng cá cắn hụt, câu thất bại rồi!")
        return

    weights = []
    for fish in FISH_TABLE:
        w = fish["weight"]
        if fish["type"] == "hiem" and active_moi and active_moi == "moi_sao":
            w *= 1.5
        elif fish["type"] == "su_thi" and active_moi and active_moi == "moi_sumo":
            w *= 1.8
        elif fish["type"] == "than_thoai" and active_moi and active_moi == "moi_tien_ca":
            w *= 2.0
        weights.append(w)

    caught = random.choices(FISH_TABLE, weights=weights)[0]
    pts = caught["pts"]
    new_score = add_points(user_id, pts)

    msg = f"🎣 Bạn vung cần và trúng lớn! Bắt được **{caught['name']}**!\n"
    if pts >= 0:
        msg += f"📈 Bạn nhận được **+{pts} điểm** (Điểm tuần mới: `{new_score}`)."
    else:
        msg += f"📉 Xui xẻo! Bạn bị phạt **{pts} điểm** (Điểm tuần còn: `{new_score}`)."

    if "title" in caught:
        add_custom_title(user_id, caught["title"])
        msg += f"\n🎉 **ĐẶC BIỆT!** Bạn khai quật được Danh hiệu Thần thoại: **[{caught['title']}]**!"

    await interaction.response.send_message(msg)

@bot.tree.command(name="buy_fishing", description="Mua Cần câu hoặc Mồi câu từ cửa hàng")
@app_commands.choices(item_id=[
    app_commands.Choice(name="🪽 Mồi cánh gió (100d)", value="moi_canh_gio"),
    app_commands.Choice(name="✨ Mồi sao (200d)", value="moi_sao"),
    app_commands.Choice(name="🥞 Mồi sumo (10,000d)", value="moi_sumo"),
    app_commands.Choice(name="🧜 Mồi nàng tiên cá (25,000d)", value="moi_tien_ca"),
    app_commands.Choice(name="🥖 Cần bánh mì (10d)", value="can_banh_mi"),
    app_commands.Choice(name="⚡ Cần sét (100d)", value="can_set"),
    app_commands.Choice(name="🔥 Cần lửa (1,000d)", value="can_lua")
])
async def buy_fishing(interaction: discord.Interaction, item_id: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    item = FISHING_ITEMS.get(item_id.value)
    if not item:
        await interaction.response.send_message("❌ Vật phẩm không tồn tại!", ephemeral=True)
        return

    data = load_data()
    pts = data.get(user_id, {}).get("weekly", 0)
    if pts < item["price"]:
        await interaction.response.send_message(f"❌ Bạn không đủ điểm để mua! Cần `{item['price']}` điểm.", ephemeral=True)
        return

    add_points(user_id, -item["price"])
    pets = load_pets()
    if user_id not in pets:
        pets[user_id] = {"pet": None, "inventory": {}}
    if "inventory" not in pets[user_id]:
        pets[user_id]["inventory"] = {}

    if item["type"] == "moi":
        pets[user_id]["inventory"]["active_moi"] = item_id.value
    else:
        pets[user_id]["inventory"]["active_can"] = item_id.value

    save_pets(pets)
    await interaction.response.send_message(f"✅ Bạn đã mua thành công **{item['name']}** và tự động trang bị!")

# ==============================================================================
# --- 6. HỆ THỐNG NUÔI THÚ ẢO (/nuoithu) & TÍNH NĂNG SHOP PET MỚI ---
# ==============================================================================

PET_DATABASE = {
    "sutu": {
        "name": "Sư tử con", "rarity": "thuong", "rate": 70,
        "forms": {1: "🦁 sư tử con", 2: "🐅 vương sư", 3: "⚡🐅 thần hổ sét"},
        "exp_caps": {1: 100, 2: 1100, 3: 2000}, "next_exp": 1000,
        "base_pwr_per_lvl": 10, "high_pwr_per_lvl": 100
    },
    "gau": {
        "name": "Gấu con", "rarity": "thuong", "rate": 70,
        "forms": {1: "🐻 gấu con", 2: "🦍&🐈‍⬛ gấu mèo", 3: "👺 quỷ gấu"},
        "exp_caps": {1: 100, 2: 1200, 3: 1200}, "next_exp": 1000,
        "base_pwr_per_lvl": 10, "high_pwr_per_lvl": 100
    },
    "gautruc": {
        "name": "Gấu trúc", "rarity": "hiem", "rate": 50,
        "forms": {1: "🐼 gấu trúc con", 2: "🐼&🦕 gấu long", 3: "🦹🐼 gấu ma rồng"},
        "exp_caps": {1: 200, 2: 1500, 3: 3000}, "next_exp": 2000,
        "base_pwr_per_lvl": 30, "high_pwr_per_lvl": 200
    },
    "phuonghoang": {
        "name": "Phượng hoàng con", "rarity": "su_thi", "rate": 20,
        "forms": {1: "🦅 phượng hoàng con", 2: "🦅&🌎 thần phượng", 3: "🌅🦅 phượng ngưu"},
        "exp_caps": {1: 1000, 2: 3000, 3: 4000}, "next_exp": 5000,
        "base_pwr_per_lvl": 50, "high_pwr_per_lvl": 500
    },
    "rong": {
        "name": "Rồng con", "rarity": "than_thoai", "rate": 10,
        "forms": {1: "🐉 rồng con", 2: "🐉&🐦‍🔥 thần tử chi long", 3: "🐲👑 phong long chính thất"},
        "exp_caps": {1: 2000, 2: 3000, 3: 4000}, "next_exp": 10000,
        "base_pwr_per_lvl": 1000, "high_pwr_per_lvl": 5000
    }
}

# BỔ SUNG CÁC MÓN ĂN TĂNG EXP VÀO DANH SÁCH ITEM PET
PET_ITEMS = {
    # Tăng sức mạnh
    "cam_duong": {"name": "🍎 Cam dương", "price": 300, "type": "power", "buff_power": 20, "duration": 600, "perm": False},
    "nam_ky_lung": {"name": "🍄 Nấm kỳ lung", "price": 1000, "type": "power", "buff_power": 100, "duration": 600, "perm": False},
    "tinh_cau": {"name": "🪐 Tinh cầu", "price": 10000, "type": "power", "buff_power": 10, "duration": 0, "perm": True},
    
    # Tăng EXP trực tiếp (Đã bổ sung theo yêu cầu)
    "kiquy": {"name": "🧡 Kí quỷ", "price": 10, "type": "exp", "add_exp": 10},
    "ngao_thi": {"name": "🪲 Ngao thị", "price": 1000, "type": "exp", "add_exp": 200},
    "thit_long_thu": {"name": "🥩 Thịt long thú", "price": 10000, "type": "exp", "add_exp": 10000}
}

# DANH SÁCH THÁP BOSS
BOSS_TOWER = {
    1: {"name": "👾 Quái nhỏ", "power": 20, "reward": 100},
    2: {"name": "👨🏻‍🐰‍👨🏼 Ma zumbi", "power": 40, "reward": 120},
    3: {"name": "👺 Chúa quỷ orozon", "power": 100, "reward": 200},
    4: {"name": "🤖 Romaku", "power": 150, "reward": 300},
    5: {"name": "🫀 Ma ma thần khu", "power": 300, "reward": 320},
    6: {"name": "🐲 Leviathan", "power": 1000, "reward": 1200},
    7: {"name": "🐙 Kraken vua biển cả", "power": 2000, "reward": 3000},
    8: {"name": "🦣 Behemonth", "power": 3000, "reward": 4000},
    9: {"name": "😈 Quỷ thần Satan", "power": 10000, "reward": 6000},
    10: {"name": "💀 Adim", "power": 900000000, "reward": 1}
}

def calculate_pet_power(pet_data):
    if not pet_data or "type" not in pet_data:
        return 0
    p_type = pet_data["type"]
    cfg = PET_DATABASE[p_type]
    lvl = pet_data["level"]
    
    base_power = 0
    for l in range(1, lvl + 1):
        if l < 20:
            base_power += cfg["base_pwr_per_lvl"]
        else:
            base_power += cfg["high_pwr_per_lvl"]
            
    base_power += pet_data.get("perm_power", 0)
    
    now = time.time()
    if pet_data.get("buff_until", 0) > now:
        base_power += pet_data.get("temp_power", 0)
        
    return base_power

def get_pet_name(pet_data):
    if not pet_data or "type" not in pet_data:
        return "Không có Pet"
    p_cfg = PET_DATABASE[pet_data["type"]]
    lvl = pet_data["level"]
    return p_cfg["forms"].get(lvl, p_cfg["forms"][3])

def add_exp_to_pet(pet_data, exp_amount):
    pet_data["exp"] += exp_amount
    p_cfg = PET_DATABASE[pet_data["type"]]
    
    leveled_up = False
    while True:
        lvl = pet_data["level"]
        max_exp = p_cfg["exp_caps"].get(lvl, p_cfg["next_exp"])
        if pet_data["exp"] >= max_exp:
            pet_data["level"] += 1
            pet_data["exp"] -= max_exp
            leveled_up = True
        else:
            break
    return leveled_up

class PetView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = str(user_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Bảng điều khiển này không thuộc về bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Mở Trứng Pet (100đ)", style=discord.ButtonStyle.success, emoji="🥚")
    async def open_egg(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        current_pts = data.get(self.user_id, {}).get("weekly", 0)
        if current_pts < 100:
            await interaction.response.send_message("❌ Bạn không đủ 100 điểm để mở trứng Pet!", ephemeral=True)
            return

        add_points(self.user_id, -100)
        
        pet_choice = random.choices(
            ["sutu", "gau", "gautruc", "phuonghoang", "rong"],
            weights=[70, 70, 50, 20, 10]
        )[0]

        pets = load_pets()
        p_info = PET_DATABASE[pet_choice]
        pets[self.user_id] = {
            "type": pet_choice,
            "level": 1,
            "exp": 0,
            "perm_power": 0,
            "temp_power": 0,
            "buff_until": 0
        }
        save_pets(pets)

        embed = discord.Embed(
            title="🎉 BẠN ĐÃ MỞ TRỨNG THÀNH CÔNG!",
            description=f"Chúc mừng bạn nhận được Pet: **{p_info['forms'][1]}** ({p_info['rarity'].upper()})!",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cho Pet Ăn (+100 EXP)", style=discord.ButtonStyle.primary, emoji="🍖")
    async def feed_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_pets()
        p = pets.get(self.user_id)
        if not p or "type" not in p:
            await interaction.response.send_message("❌ Bạn chưa sở hữu Pet nào! Hãy mở trứng trước.", ephemeral=True)
            return

        data = load_data()
        pts = data.get(self.user_id, {}).get("weekly", 0)
        if pts < 20:
            await interaction.response.send_message("❌ Bạn không đủ 20 điểm để cho Pet ăn!", ephemeral=True)
            return

        add_points(self.user_id, -20)
        add_exp_to_pet(p, 100)
        save_pets(pets)
        
        p_cfg = PET_DATABASE[p["type"]]
        form_name = get_pet_name(p)
        power = calculate_pet_power(p)
        max_exp = p_cfg["exp_caps"].get(p["level"], p_cfg["next_exp"])

        embed = discord.Embed(
            title=f"🐾 BẢNG THÔNG TIN PET: {form_name}",
            description=f"⭐ Cấp độ: `{p['level']}`\n⚡ Lực chiến: `{power}`\n📈 EXP: `{p['exp']}/{max_exp}`",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name="nuoithu", description="Mở bảng điều khiển Thú Cưng Ảo")
async def nuoithu(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pets = load_pets()
    p = pets.get(user_id)

    if not p or "type" not in p:
        embed = discord.Embed(
            title="🥚 BẠN CHƯA CÓ THÚ CƯNG",
            description="Hãy nhấn nút **Mở Trứng Pet (100đ)** bên dưới để thử vận may sở hữu Thần Thú!",
            color=discord.Color.gold()
        )
    else:
        p_cfg = PET_DATABASE[p["type"]]
        lvl = p["level"]
        form_name = get_pet_name(p)
        max_exp = p_cfg["exp_caps"].get(lvl, p_cfg["next_exp"])
        power = calculate_pet_power(p)

        embed = discord.Embed(
            title=f"🐾 THÚ CƯNG CỦA BẠN: {form_name}",
            description=f"⭐ **Cấp độ:** `{lvl}`\n⚡ **Lực chiến:** `{power}`\n📈 **Kinh nghiệm:** `{p['exp']}/{max_exp}`",
            color=discord.Color.purple()
        )

    view = PetView(user_id)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="buy_pet_item", description="Mua đồ ăn & vật phẩm tăng Lực chiến/EXP cho Pet")
@app_commands.choices(item_id=[
    app_commands.Choice(name="🧡 Kí quỷ (+10 EXP) - 10d", value="kiquy"),
    app_commands.Choice(name="🪲 Ngao thị (+200 EXP) - 1,000d", value="ngao_thi"),
    app_commands.Choice(name="🥩 Thịt long thú (+10,000 EXP) - 10,000d", value="thit_long_thu"),
    app_commands.Choice(name="🍎 Cam dương (+20 Pwr/10p) - 300d", value="cam_duong"),
    app_commands.Choice(name="🍄 Nấm kỳ lung (+100 Pwr/10p) - 1,000d", value="nam_ky_lung"),
    app_commands.Choice(name="🪐 Tinh cầu (+10 Pwr vĩnh viễn) - 10,000d", value="tinh_cau")
])
async def buy_pet_item(interaction: discord.Interaction, item_id: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    pets = load_pets()
    p = pets.get(user_id)
    if not p or "type" not in p:
        await interaction.response.send_message("❌ Bạn chưa có Pet để sử dụng vật phẩm!", ephemeral=True)
        return

    item = PET_ITEMS[item_id.value]
    data = load_data()
    pts = data.get(user_id, {}).get("weekly", 0)

    if pts < item["price"]:
        await interaction.response.send_message(f"❌ Bạn không đủ điểm! Cần `{item['price']}` điểm.", ephemeral=True)
        return

    add_points(user_id, -item["price"])

    if item["type"] == "exp":
        exp_gained = item["add_exp"]
        old_lvl = p["level"]
        add_exp_to_pet(p, exp_gained)
        new_lvl = p["level"]
        
        msg = f"🎉 Bạn đã cho Pet ăn **{item['name']}**, nhận được **+{exp_gained} EXP**!"
        if new_lvl > old_lvl:
            msg += f"\n🎊 **CHÚC MỪNG!** Pet của bạn đã thăng cấp thành công lên **Level {new_lvl}**!"
            
    elif item["type"] == "power":
        if item["perm"]:
            p["perm_power"] = p.get("perm_power", 0) + item["buff_power"]
            msg = f"🎉 Bạn đã cho Pet dùng **{item['name']}**, tăng vĩnh viễn **+{item['buff_power']} Lực chiến**!"
        else:
            p["temp_power"] = item["buff_power"]
            p["buff_until"] = time.time() + item["duration"]
            msg = f"⚡ Bạn đã dùng **{item['name']}**, tăng **+{item['buff_power']} Lực chiến** trong 10 phút!"

    save_pets(pets)
    await interaction.response.send_message(msg)

# ==============================================================================
# --- 7. TÍNH NĂNG MỚI: PVP PET & ĐÁNH BOSS TẦNG ---
# ==============================================================================

@bot.tree.command(name="pvp_pet", description="Thách đấu PvP Thú cưng với người chơi khác!")
async def pvp_pet(interaction: discord.Interaction, target: discord.User):
    user_id = str(interaction.user.id)
    target_id = str(target.id)

    if target_id == user_id:
        await interaction.response.send_message("❌ Bạn không thể tự PvP với chính mình!", ephemeral=True)
        return

    if target.bot:
        await interaction.response.send_message("❌ Bạn không thể thách đấu với Bot!", ephemeral=True)
        return

    pets = load_pets()
    p1 = pets.get(user_id)
    p2 = pets.get(target_id)

    if not p1 or "type" not in p1:
        await interaction.response.send_message("❌ Bạn chưa có Pet để tham gia PvP!", ephemeral=True)
        return

    if not p2 or "type" not in p2:
        await interaction.response.send_message(f"❌ {target.mention} hiện chưa sở hữu Pet nào!", ephemeral=True)
        return

    p1_pwr = calculate_pet_power(p1)
    p2_pwr = calculate_pet_power(p2)
    p1_name = get_pet_name(p1)
    p2_name = get_pet_name(p2)

    embed = discord.Embed(
        title="⚔️ TRẬN ĐẤU PVP PET NẢY LỬA ⚔️",
        description=f"🔴 **{interaction.user.mention}** với Pet **{p1_name}** (Lực chiến: `{p1_pwr}`)\n⚡ **VS** ⚡\n🔵 **{target.mention}** với Pet **{p2_name}** (Lực chiến: `{p2_pwr}`)",
        color=discord.Color.red()
    )

    reward = random.randint(50, 150)

    if p1_pwr > p2_pwr:
        add_points(user_id, reward)
        embed.add_field(name="🏆 KẾT QUẢ", value=f"🎉 **{interaction.user.mention}** chiến thắng và nhận **+{reward} điểm**!", inline=False)
    elif p2_pwr > p1_pwr:
        add_points(target_id, reward)
        embed.add_field(name="🏆 KẾT QUẢ", value=f"🎉 **{target.mention}** chiến thắng và nhận **+{reward} điểm**!", inline=False)
    else:
        embed.add_field(name="🏆 KẾT QUẢ", value="🤝 **HÒA CỜ!** Cả 2 Pet có lực chiến bằng nhau, không ai mất điểm!", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="danhboss", description="Đưa Pet đi khiêu chiến Boss các tầng để cày điểm!")
@app_commands.choices(tang=[
    app_commands.Choice(name="Tầng 1: 👾 Quái nhỏ (Pwr: 20 -> Thưởng: 100d)", value=1),
    app_commands.Choice(name="Tầng 2: 👨🏻‍🐰‍👨🏼 Ma zumbi (Pwr: 40 -> Thưởng: 120d)", value=2),
    app_commands.Choice(name="Tầng 3: 👺 Chúa quỷ orozon (Pwr: 100 -> Thưởng: 200d)", value=3),
    app_commands.Choice(name="Tầng 4: 🤖 Romaku (Pwr: 150 -> Thưởng: 300d)", value=4),
    app_commands.Choice(name="Tầng 5: 🫀 Ma ma thần khu (Pwr: 300 -> Thưởng: 320d)", value=5),
    app_commands.Choice(name="Tầng 6: 🐲 Leviathan (Pwr: 1,000 -> Thưởng: 1,200d)", value=6),
    app_commands.Choice(name="Tầng 7: 🐙 Kraken vua biển cả (Pwr: 2,000 -> Thưởng: 3,000d)", value=7),
    app_commands.Choice(name="Tầng 8: 🦣 Behemonth (Pwr: 3,000 -> Thưởng: 4,000d)", value=8),
    app_commands.Choice(name="Tầng 9: 😈 Quỷ thần Satan (Pwr: 10,000 -> Thưởng: 6,000d)", value=9),
    app_commands.Choice(name="Tầng 10: 💀 Adim (Pwr: 900,000,000 -> Thưởng: 1d)", value=10)
])
@app_commands.checks.cooldown(1, 30)
async def danhboss(interaction: discord.Interaction, tang: app_commands.Choice[int]):
    user_id = str(interaction.user.id)
    pets = load_pets()
    p = pets.get(user_id)

    if not p or "type" not in p:
        await interaction.response.send_message("❌ Bạn chưa có Pet để tham gia đánh Boss! Hãy gõ `/nuoithu` để nhận Pet.", ephemeral=True)
        danhboss.reset_cooldown(interaction)
        return

    boss_info = BOSS_TOWER[tang.value]
    pet_pwr = calculate_pet_power(p)
    pet_name = get_pet_name(p)

    embed = discord.Embed(title=f"🏰 THÁP MA THẦN - TẦNG {tang.value}")
    embed.add_field(name="🐾 Thần thú chiến đấu", value=f"**{pet_name}** (Lực chiến: `{pet_pwr}`)", inline=False)
    embed.add_field(name="👹 Thủ vệ Tầng", value=f"**{boss_info['name']}** (Lực chiến: `{boss_info['power']:,}`)", inline=False)

    if pet_pwr >= boss_info["power"]:
        new_score = add_points(user_id, boss_info["reward"])
        embed.color = discord.Color.green()
        embed.add_field(
            name="⚔️ TRẬN ĐẤU KẾT THÚC", 
            value=f"🎉 **CHIẾN THẮNG!** Pet của bạn đã tiêu diệt **{boss_info['name']}**!\n📈 Nhận được **+{boss_info['reward']:,} điểm** (Tổng điểm tuần: `{new_score}`).", 
            inline=False
        )
    else:
        embed.color = discord.Color.red()
        embed.add_field(
            name="⚔️ TRẬN ĐẤU KẾT THÚC", 
            value=f"💀 **THẤT BẠI!** Lực chiến của Pet (`{pet_pwr}`) chưa đủ để đánh bại **{boss_info['name']}** (`{boss_info['power']:,}`). Hãy cho Pet ăn để thăng cấp nhé!", 
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# ==============================================================================
# --- 8. CÁC LỆNH CHÍNH KHÁC (/cuop, /taixiu, /bangxephang) ---
# ==============================================================================

@bot.tree.command(name="cuop", description="Thử vận may đi cướp điểm từ một người chơi khác!")
@app_commands.checks.cooldown(1, 60)
async def cuop(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    
    possible_targets = [uid for uid, score in data.items() if uid != user_id and score.get("weekly", 0) > 0]
    
    if not possible_targets:
        await interaction.response.send_message("❌ Chưa có người chơi nào khác có điểm tuần để bạn cướp!", ephemeral=True)
        cuop.reset_cooldown(interaction)
        return

    target_id = random.choice(possible_targets)
    target_user = bot.get_user(int(target_id))
    target_name = target_user.mention if target_user else f"<@{target_id}>"
    target_score = data[target_id]["weekly"]
    
    is_success = random.random() <= 0.45

    if is_success:
        if random.random() <= 0.05:
            stolen_pts = target_score
            jackpot_msg = "🔥 **JACKPOT! BẠN ĐÃ CƯỚP TRẮNG TAY 100% ĐIỂM CỦA NẠN NHÂN!** 🔥\n"
        else:
            stolen_pts = random.randint(10, min(1000, target_score))
            jackpot_msg = ""
            
        my_new_score = add_points(user_id, stolen_pts)
        add_points(target_id, -stolen_pts)
        
        embed = discord.Embed(
            title="🥷 CƯỚP ĐIỂM THÀNH CÔNG!",
            description=f"{jackpot_msg}Bạn đột nhập thành công và cướp **+{stolen_pts} điểm** từ {target_name}!\n📈 Điểm tuần mới của bạn: `{my_new_score}`",
            color=discord.Color.green()
        )
    else:
        penalty_pts = random.randint(10, 1000)
        my_score = data.get(user_id, {}).get("weekly", 0)
        actual_penalty = min(my_score, penalty_pts)
        
        if actual_penalty > 0:
            my_new_score = add_points(user_id, -actual_penalty)
            add_points(target_id, actual_penalty)
            
            embed = discord.Embed(
                title="🚨 BỊ BẮT QUẢ TANG!",
                description=f"Bạn định cướp điểm của {target_name} nhưng bị cảnh sát tóm!\n⚖️ Bạn bị phạt **-{actual_penalty} điểm** (chuyển bồi thường cho {target_name}).\n📉 Điểm tuần còn lại: `{my_new_score}`",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="🚨 BỊ BẮT QUẢ TANG!",
                description=f"Bạn định cướp điểm của {target_name} nhưng bị tóm! May mắn do bạn đang có `0 điểm` nên không bị trừ điểm.",
                color=discord.Color.red()
            )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="taixiu", description="Đặt cược điểm tuần vào Tài hoặc Xỉu!")
@app_commands.choices(luachon=[
    app_commands.Choice(name="Tài (11 - 18)", value="tai"),
    app_commands.Choice(name="Xỉu (3 - 10)", value="xiu")
])
async def taixiu(interaction: discord.Interaction, sodiem_cuoc: int, luachon: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    data = load_data()
    current_pts = data.get(user_id, {}).get("weekly", 0)
    
    if sodiem_cuoc <= 0 or current_pts < sodiem_cuoc:
        await interaction.response.send_message(f"❌ Điểm cược không hợp lệ hoặc bạn không đủ điểm! (Điểm hiện có: `{current_pts}`)", ephemeral=True)
        return
        
    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    result = "tai" if total >= 11 else "xiu"
    
    embed = discord.Embed(title="🎲 KẾT QUẢ TÀI XỈU")
    embed.add_field(name="Xúc xắc", value=f"🎲 **{d1}** — 🎲 **{d2}** — 🎲 **{d3}**", inline=False)
    embed.add_field(name="Tổng điểm", value=f"**{total}** ({'TÀI' if result == 'tai' else 'XỈU'})", inline=False)

    if luachon.value == result:
        new_score = add_points(user_id, sodiem_cuoc)
        embed.color = discord.Color.green()
        embed.add_field(name="Kết quả", value=f"🎉 **THẮNG!** Nhận thêm **+{sodiem_cuoc} điểm** (Tổng: `{new_score}`)")
    else:
        new_score = add_points(user_id, -sodiem_cuoc)
        embed.color = discord.Color.red()
        embed.add_field(name="Kết quả", value=f"😢 **THUA!** Bị trừ **-{sodiem_cuoc} điểm** (Còn lại: `{new_score}`)")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bangxephang", description="Xem Bảng Xếp Hạng điểm tuần hiện tại!")
async def bangxephang(interaction: discord.Interaction):
    data = load_data()
    titles = load_titles()
    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:10]
    
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG ĐIỂM TUẦN 🏆", color=discord.Color.gold())
    
    desc = ""
    for index, (u_id, score) in enumerate(sorted_users, 1):
        user = bot.get_user(int(u_id))
        name = user.mention if user else f"<@{u_id}>"
        
        icon = "🔹"
        if str(index) in titles:
            t_icon = titles[str(index)]["icon"]
            t_name = titles[str(index)]["name"]
            icon = f"{t_icon} **[{t_name}]**"
        
        user_titles = score.get("titles", [])
        title_str = f" `[{', '.join(user_titles)}]`" if user_titles else ""
        
        desc += f"`#{index}` {icon} {name}{title_str} — **{score.get('weekly', 0)}** điểm\n"
        
    embed.description = desc if desc else "Chưa có dữ liệu tích điểm tuần này."
    await interaction.response.send_message(embed=embed)

# ==============================================================================
# --- 9. CÁC LỆNH ADMIN ---
# ==============================================================================

@bot.tree.command(name="add_question", description="[ADMIN] Thêm câu hỏi đố vui mẹo mới vào hệ thống")
@app_commands.checks.has_permissions(administrator=True)
async def add_question(interaction: discord.Interaction, question: str, answer: str):
    trivia = load_trivia()
    answers = [a.strip().lower() for a in answer.split(",")]
    trivia.append({"q": question, "a": answers})
    save_trivia(trivia)
    await interaction.response.send_message(f"✅ Đã thêm câu hỏi thành công!\n❓ **Câu hỏi:** {question}\n🎯 **Đáp án:** {answers}")

@bot.tree.command(name="reset_week_manual", description="[ADMIN] Ép chốt Top tuần, trao Role và Reset điểm ngay")
@app_commands.checks.has_permissions(administrator=True)
async def reset_week_manual(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = await process_weekly_rewards()
    await interaction.followup.send(f"✅ **ĐÃ CHỐT VÀ RESET ĐIỂM TUẦN THỦ CÔNG:**\n{msg}")

@bot.tree.command(name="set_top_title", description="[ADMIN] Đổi danh hiệu hiển thị cho Top 1, Top 2 hoặc Top 3")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(top=[
    app_commands.Choice(name="Top 1", value=1),
    app_commands.Choice(name="Top 2", value=2),
    app_commands.Choice(name="Top 3", value=3)
])
async def set_top_title(interaction: discord.Interaction, top: app_commands.Choice[int], icon: str, title_name: str):
    titles = load_titles()
    titles[str(top.value)] = {"icon": icon, "name": title_name}
    save_titles(titles)
    await interaction.response.send_message(f"✅ Đã đổi danh hiệu **Top {top.value}** thành: {icon} **[{title_name}]**!")

@bot.tree.command(name="set_game_channel", description="[ADMIN] Đặt kênh nhận thông báo tự động và phát Mini-game (1 tiếng/lần)")
@app_commands.checks.has_permissions(administrator=True)
async def set_game_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    cfg = load_config()
    cfg["game_channel_id"] = channel.id
    save_config(cfg)
    await interaction.response.send_message(f"✅ Đã lưu cài đặt kênh **{channel.mention}** làm nơi phát Mini-game đố vui tự động (1 tiếng/lần)!")

@bot.tree.command(name="point_edit", description="[ADMIN] Cộng hoặc trừ điểm tuần trực tiếp của thành viên")
@app_commands.checks.has_permissions(administrator=True)
async def point_edit(interaction: discord.Interaction, user: discord.User, amount: int):
    new_score = add_points(str(user.id), amount)
    await interaction.response.send_message(f"✅ Đã cập nhật điểm cho {user.mention}. Điểm tuần mới: `{new_score}`.")

# --- HANDLER BẮT LỖI COOLDOWN TOÀN CỤC ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Vui lòng chờ `{int(error.retry_after)}s` nữa để tiếp tục sử dụng lệnh này!", ephemeral=True)
    else:
        print(f"[ERROR] App Command Error: {error}")

# --- 10. KÍCH HOẠT BOT ---
keep_alive()
TOKEN = os.getenv('TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("[ERROR] Không tìm thấy 'TOKEN' trong Environment Variables!")

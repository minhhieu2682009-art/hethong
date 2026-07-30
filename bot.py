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
# --- 0. KHỞI TẠO WEB SERVER KEEP ALIVE 24/7 ---
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "📜 Hệ Thống Bot Thượng Cổ Online 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==============================================================================
# --- 1. QUẢN LÝ DỮ LIỆU JSON AN TOÀN ---
# ==============================================================================
DATA_FILE = "user_points.json"
PETS_FILE = "user_pets.json"
CONFIG_FILE = "config.json"
TITLES_FILE = "titles_config.json"
TRIVIA_FILE = "trivia_questions.json"
FISHING_ITEMS_FILE = "fishing_items.json"
FISH_TABLE_FILE = "fish_table.json"
PET_ITEMS_FILE = "pet_items.json"
PET_DATABASE_FILE = "pet_database.json"

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

# Load / Save Helpers
def load_data(): return safe_load_json(DATA_FILE, {})
def save_data(d): safe_save_json(DATA_FILE, d)

def load_pets(): return safe_load_json(PETS_FILE, {})
def save_pets(d): safe_save_json(PETS_FILE, d)

def load_config(): return safe_load_json(CONFIG_FILE, {"game_channel_id": None})
def save_config(c): safe_save_json(CONFIG_FILE, c)

def load_titles():
    default = {
        "1": {"icon": "👑", "name": "Khư Quỷ", "role_id": None},
        "2": {"icon": "⚔️", "name": "Khư La", "role_id": None},
        "3": {"icon": "🛡️", "name": "Thế Thần", "role_id": None}
    }
    return safe_load_json(TITLES_FILE, default)
def save_titles(t): safe_save_json(TITLES_FILE, t)

def load_trivia():
    default = [
        {"q": "Trong một cuộc thi chạy, nếu bạn vượt qua người đang đứng thứ hai, bạn sẽ đứng thứ mấy?", "a": ["thứ hai", "thứ 2", "2"]},
        {"q": "Bố của Mary có 5 cô con gái: Nana, Nene, Nini, Nono. Hỏi cô con gái thứ 5 tên là gì?", "a": ["mary"]},
        {"q": "Có 3 quả táo trên bàn, bạn lấy đi 2 quả. Hỏi bạn còn bao nhiêu quả táo?", "a": ["2", "2 quả", "hai quả"]},
        {"q": "Lịch nào dài nhất?", "a": ["lịch sử"]}
    ]
    return safe_load_json(TRIVIA_FILE, default)
def save_trivia(t): safe_save_json(TRIVIA_FILE, t)

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

# ==============================================================================
# --- 2. CƠ SỞ DỮ LIỆU BAN ĐẦU ---
# ==============================================================================
FISHING_ITEMS = safe_load_json(FISHING_ITEMS_FILE, {
    "moi_canh_gio": {"name": "🪽 Mồi cánh gió", "type": "moi", "rarity": "Thường", "price": 100, "succ_bonus": 0.01, "rare_bonus": 0.0, "desc": "Tăng 1% tỷ lệ câu thành công cá thường"},
    "moi_sao": {"name": "✨ Mồi sao", "type": "moi", "rarity": "Hiếm", "price": 200, "succ_bonus": 0.10, "rare_bonus": 0.10, "desc": "Tăng 10% câu thành công, +10% cá hiếm"},
    "moi_sumo": {"name": "🥞 Mồi sumo", "type": "moi", "rarity": "Sử Thi", "price": 10000, "succ_bonus": 0.12, "epic_bonus": 0.11, "desc": "Tăng 12% câu thành công, +11% cá sử thi"},
    "moi_tienca": {"name": "🧜 Mồi nàng tiên cá", "type": "moi", "rarity": "Thần Thoại", "price": 25000, "succ_bonus": 0.16, "myth_bonus": 0.05, "desc": "Tăng 16% câu thành công, +5% cá thần thoại"},
    "can_banh_mi": {"name": "🥖 Cần bánh mì", "type": "can", "rarity": "Thường", "price": 10, "succ_bonus": 0.0, "desc": "Cần câu tân thủ"},
    "can_set": {"name": "⚡ Cần sét", "type": "can", "rarity": "Hiếm", "price": 100, "succ_bonus": 0.01, "desc": "Cần câu nguyên tố sét"},
    "can_lua": {"name": "🔥 Cần lửa", "type": "can", "rarity": "Hiếm", "price": 1000, "succ_bonus": 0.03, "desc": "Tăng 3% tỷ lệ câu thành công"}
})

FISH_TABLE = safe_load_json(FISH_TABLE_FILE, [
    {"id": "ro_dong", "name": "🐟 Cá Rô Đồng", "type": "Thường", "pts": 10, "weight": 50.0},
    {"id": "chep_vang", "name": "🐠 Cá Chép Vàng", "type": "Thường", "pts": 10, "weight": 50.0},
    {"id": "ca_tam", "name": "🦈 Cá Tầm", "type": "Thường", "pts": 10, "weight": 50.0},
    {"id": "chim_cut", "name": "🐧 Chim Cút", "type": "Thường", "pts": 20, "weight": 50.0},
    {"id": "giay_rach", "name": "👞 Giày Cũ Bị Rách", "type": "Rác", "pts": -100, "weight": 40.0},
    {"id": "ruong_bau", "name": "👑 Rương Báu Dưới Sông", "type": "Hiếm", "pts": 100, "weight": 40.0},
    {"id": "bach_tuoc", "name": "🐙 Bạch Tuộc", "type": "Hiếm", "pts": 60, "weight": 40.0},
    {"id": "rua_con", "name": "🐢 Rùa Con", "type": "Hiếm", "pts": 70, "weight": 40.0},
    {"id": "tieu_long_cau", "name": "🦭 Tiểu Long Cẩu", "type": "Sử Thi", "pts": 200, "weight": 20.0},
    {"id": "tom_suki", "name": "🦞 Tôm Suki", "type": "Sử Thi", "pts": 210, "weight": 19.0},
    {"id": "light_suki", "name": "⭐ Light Suki", "type": "Sử Thi", "pts": 220, "weight": 15.0},
    {"id": "ca_voi_sat_than", "name": "🫍 Cá Voi Sát Thần", "type": "Thần Thoại", "pts": 500, "title": "Sát Long", "weight": 1.0},
    {"id": "virut_tu_than", "name": "🦠 Virut Tử Thần", "type": "Thần Thoại", "pts": 1000, "title": "Virut Vương", "weight": 0.5},
    {"id": "leviathan", "name": "🐉 Leviathan", "type": "Thần Thoại", "pts": 2000, "title": "Leviathan", "weight": 0.1}
])

PET_ITEMS = safe_load_json(PET_ITEMS_FILE, {
    "cam_duong": {"name": "🍎 Cam Dương", "price": 300, "buff_pwr": 20, "duration": 600, "add_exp": 0, "desc": "Tăng 20 lực chiến trong 10 phút"},
    "nam_ki_lung": {"name": "🍄 Nấm Kì Lung", "price": 1000, "buff_pwr": 100, "duration": 600, "add_exp": 0, "desc": "Tăng 100 lực chiến trong 10 phút"},
    "tinh_cau": {"name": "🪐 Tinh Cầu", "price": 10000, "buff_pwr": 10, "duration": 0, "add_exp": 0, "desc": "Tăng 10 lực chiến vĩnh viễn"},
    "kiquy": {"name": "🧡 Kí Quỷ", "price": 10, "buff_pwr": 0, "duration": 0, "add_exp": 10, "desc": "Tăng 10 EXP"},
    "ngao_thi": {"name": "🪲 Ngao Thị", "price": 1000, "buff_pwr": 0, "duration": 0, "add_exp": 200, "desc": "Tăng 200 EXP / miếng"},
    "thit_long_thu": {"name": "🥩 Thịt Long Thú", "price": 10000, "buff_pwr": 0, "duration": 0, "add_exp": 10000, "desc": "Tăng 10000 EXP / miếng"}
})

PET_DATABASE = safe_load_json(PET_DATABASE_FILE, {
    "sutu": {
        "name": "Sư tử con", "rarity": "Thường", "rate": 70,
        "forms": {"1": "🦁 Sư tử con", "2": "🐅 Vương sư", "3": "⚡🐅 Thần hổ sét"},
        "exp_caps": {"1": 100, "2": 1100, "3": 2000}, "step_exp": 1000,
        "base_pwr": 10, "high_pwr": 100
    },
    "gaucon": {
        "name": "Gấu con", "rarity": "Thường", "rate": 70,
        "forms": {"1": "🐻 Gấu con", "2": "🦍🐈‍⬛ Gấu mèo", "3": "👺 Quỷ gấu"},
        "exp_caps": {"1": 100, "2": 1200, "3": 1200}, "step_exp": 1000,
        "base_pwr": 10, "high_pwr": 100
    },
    "gautruc": {
        "name": "Gấu trúc", "rarity": "Hiếm", "rate": 50,
        "forms": {"1": "🐼 Gấu trúc con", "2": "🐼🦕 Gấu long", "3": "🦹🐼 Gấu ma rồng"},
        "exp_caps": {"1": 200, "2": 1500, "3": 3000}, "step_exp": 2000,
        "base_pwr": 30, "high_pwr": 200
    },
    "phuonghoang": {
        "name": "Phượng hoàng con", "rarity": "Sử Thi", "rate": 20,
        "forms": {"1": "🦅 Phượng hoàng con", "2": "🦅🌎 Thần phượng", "3": "🌅🦅 Phượng ngưu"},
        "exp_caps": {"1": 1000, "2": 3000, "3": 4000}, "step_exp": 5000,
        "base_pwr": 50, "high_pwr": 500
    },
    "rong": {
        "name": "Rồng con", "rarity": "Thần Thoại", "rate": 10,
        "forms": {"1": "🐉 Rồng con", "2": "🐉🐦‍🔥 Thần tử chi long", "3": "🐲👑 Phong long chính thất"},
        "exp_caps": {"1": 2000, "2": 3000, "3": 4000}, "step_exp": 10000,
        "base_pwr": 1000, "high_pwr": 5000
    }
})

# ==============================================================================
# --- 3. HELPER FUNCTIONS TÍNH TOÁN LINH THÚ ---
# ==============================================================================
def calculate_pet_power(pet_data):
    if not pet_data or "type" not in pet_data or pet_data["type"] not in PET_DATABASE:
        return 0
    p_cfg = PET_DATABASE[pet_data["type"]]
    lvl = pet_data.get("level", 1)
    base_pwr = 0
    for l in range(1, lvl + 1):
        if l < 20:
            base_pwr += p_cfg.get("base_pwr", 10)
        else:
            base_pwr += p_cfg.get("high_pwr", 100)
    base_pwr += pet_data.get("perm_power", 0)
    if pet_data.get("buff_until", 0) > time.time():
        base_pwr += pet_data.get("temp_power", 0)
    return base_pwr

def get_pet_display_name(pet_data):
    if not pet_data or "type" not in pet_data or pet_data["type"] not in PET_DATABASE:
        return "Chưa Có Pet"
    p_cfg = PET_DATABASE[pet_data["type"]]
    lvl = pet_data.get("level", 1)
    forms = p_cfg.get("forms", {})
    if lvl == 1: return forms.get("1", p_cfg["name"])
    elif lvl == 2: return forms.get("2", p_cfg["name"])
    else: return forms.get("3", p_cfg["name"])

def add_exp_to_pet(pet_data, exp_amount):
    pet_data["exp"] = pet_data.get("exp", 0) + exp_amount
    p_cfg = PET_DATABASE[pet_data["type"]]
    leveled_up = False
    while True:
        lvl = pet_data.get("level", 1)
        caps = p_cfg.get("exp_caps", {})
        step = p_cfg.get("step_exp", 1000)
        max_exp = caps.get(str(lvl), step)
        if pet_data["exp"] >= max_exp:
            pet_data["level"] = lvl + 1
            pet_data["exp"] -= max_exp
            leveled_up = True
        else:
            break
    return leveled_up

# ==============================================================================
# --- 4. CẤU HÌNH BOT DISCORD ---
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
chat_cooldowns = {}
fishing_cooldowns = {}

# Process Weekly Top
async def process_weekly_rewards():
    data = load_data()
    if not data: return "📜 Không có dữ liệu điểm để chốt tuần."
    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:3]
    titles_cfg = load_titles()
    summary = []
    
    for guild in bot.guilds:
        for idx, (u_id, score) in enumerate(sorted_users, 1):
            t_info = titles_cfg.get(str(idx), {})
            role_id = t_info.get("role_id")
            member = guild.get_member(int(u_id))
            if role_id and member:
                role = guild.get_role(role_id)
                if role:
                    try: await member.add_roles(role)
                    except: pass
            t_name = f"{t_info.get('icon','🏆')} **[{t_info.get('name','Top')}]**"
            summary.append(f"{t_name} <@{u_id}> — `{score.get('weekly',0)} điểm`")
            add_custom_title(u_id, f"{t_info.get('icon','')} {t_info.get('name','')}")

    for u in data: data[u]["weekly"] = 0
    save_data(data)
    return "\n".join(summary) if summary else "Đã reset điểm tuần."

# TASKS NGẦM
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
            title="📜 ─── BẢNG VÀNG CỐNG HIẾN HÀNG NGÀY ─── 📜",
            description="🏛️ *Tự động cập nhật 08:00 sáng hàng ngày*",
            color=discord.Color.gold(), timestamp=now
        )
        desc = ""
        for idx, (u_id, score) in enumerate(sorted_users, 1):
            icon = "🔹"
            if str(idx) in titles:
                icon = f"{titles[str(idx)]['icon']} **[{titles[str(idx)]['name']}]**"
            desc += f"`#{idx}` {icon} <@{u_id}> — 🪙 **{score.get('weekly',0)}** điểm\n"
        embed.add_field(name="🏆 Top Cao Thủ", value=desc if desc else "Chưa có dữ liệu.", inline=False)
        await channel.send(embed=embed)

@tasks.loop(hours=1)
async def auto_hourly_trivia():
    try:
        cfg = load_config()
        channel_id = cfg.get("game_channel_id")
        if not channel_id: return
        channel = bot.get_channel(channel_id)
        if not channel: return
        
        trivia = load_trivia()
        if not trivia: return
        item = random.choice(trivia)
        valid_ans = item["a"]
        
        embed = discord.Embed(
            title="🏮 ─── THỬ THÁCH ĐỐ VUI MẸO (MỖI GIỜ) ─── 🏮",
            description=f"❓ **Câu hỏi:** {item['q']}\n\n⚡ *Trả lời đúng trong 45s để nhận **+30 điểm**!*",
            color=discord.Color.orange()
        )
        await channel.send(embed=embed)

        def check(m):
            if m.channel != channel or m.bot: return False
            content = m.content.strip().lower()
            return any(ans.lower() in content for ans in valid_ans)

        try:
            msg = await bot.wait_for('message', timeout=45.0, check=check)
            new_pts = add_points(str(msg.author.id), 30)
            await channel.send(f"🎉 Chúc mừng {msg.author.mention} đã trả lời đúng! Nhận **+30 điểm** (Điểm tuần: `{new_pts}`).")
        except asyncio.TimeoutError:
            await channel.send(f"⏰ Hết thời gian! Đáp án chính xác là: **{valid_ans[0]}**")
    except Exception as e:
        print(f"[WARN] Lỗi trivia: {e}")

@bot.event
async def on_ready():
    print(f"[SYSTEM] Bot đã sẵn sàng kết nối: {bot.user}")
    if not auto_daily_leaderboard.is_running(): auto_daily_leaderboard.start()
    if not auto_hourly_trivia.is_running(): auto_hourly_trivia.start()

    # Dynamic Register Persistent Views (timeout=None)
    bot.add_view(GlobalShopView())
    bot.add_view(CauSongView())
    bot.add_view(NuoiThuView())

    try:
        synced = await bot.tree.sync()
        print(f"[SYSTEM] Đã đồng bộ thành công {len(synced)} Slash Commands.")
    except Exception as e:
        print(f"[ERROR] Sync error: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    user_id = str(message.author.id)
    now = time.time()
    if user_id not in chat_cooldowns or (now - chat_cooldowns[user_id]) >= 60:
        add_points(user_id, random.randint(1, 3))
        chat_cooldowns[user_id] = now
    await bot.process_commands(message)

# ==============================================================================
# --- 5. /PVP_PET (THÁCH ĐẤU PET LINH THÚ) ---
# ==============================================================================
class PvPChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="⚔️ Đồng Ý Thách Đấu", style=discord.ButtonStyle.danger)
    async def accept_pvp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Bạn không phải người được thách đấu!", ephemeral=True)
            return

        pets = load_pets()
        p1_data = pets.get(str(self.challenger.id), {}).get("pet")
        p2_data = pets.get(str(self.opponent.id), {}).get("pet")

        if not p1_data or not p2_data:
            await interaction.response.send_message("❌ Một trong hai người chơi không còn sở hữu Linh Thú!", ephemeral=True)
            return

        p1_pwr = calculate_pet_power(p1_data)
        p2_pwr = calculate_pet_power(p2_data)

        # Tính tỷ lệ thắng
        diff = abs(p1_pwr - p2_pwr)
        if diff == 0:
            p1_win_rate = 0.50
        elif 10 <= diff <= 1000:
            p1_win_rate = 0.60 if p1_pwr > p2_pwr else 0.40
        elif 1000 < diff <= 2000:
            p1_win_rate = 0.70 if p1_pwr > p2_pwr else 0.30
        else: # > 2000
            p1_win_rate = 1.00 if p1_pwr > p2_pwr else 0.00

        p1_name = get_pet_display_name(p1_data)
        p2_name = get_pet_display_name(p2_data)

        # Quyết định thắng thua
        p1_win = random.random() < p1_win_rate
        winner = self.challenger if p1_win else self.opponent
        loser = self.opponent if p1_win else self.challenger

        # Thưởng / Phạt điểm
        win_pts = random.randint(50, 150)
        add_points(str(winner.id), win_pts)
        add_points(str(loser.id), -win_pts)

        embed = discord.Embed(
            title="⚔️ ─── KẾT QUẢ QUYẾT ĐẤU LINH THÚ ─── ⚔️",
            description=f"🔴 **{self.challenger.mention}** ({p1_name} - `{p1_pwr} PWR`)\n⚡ **VS** ⚡\n🔵 **{self.opponent.mention}** ({p2_name} - `{p2_pwr} PWR`)",
            color=discord.Color.red()
        )
        embed.add_field(name="🏆 Đơn Vị Chiến Thắng", value=f"🎉 **{winner.mention}** đã chiến thắng!\n📈 Thưởng: **+{win_pts} điểm** (Đối phương bị trừ **-{win_pts} điểm**).", inline=False)
        
        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🏳️ Từ Chối", style=discord.ButtonStyle.secondary)
    async def decline_pvp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Bạn không có quyền bấm nút này!", ephemeral=True)
            return
        await interaction.response.edit_message(content=f"❌ {self.opponent.mention} đã từ chối lời thách đấu!", embed=None, view=None)

@bot.tree.command(name="pvp_pet", description="Thách đấu Linh Thú với thành viên khác!")
async def pvp_pet(interaction: discord.Interaction, opponent: discord.Member):
    if opponent.id == interaction.user.id or opponent.bot:
        await interaction.response.send_message("❌ Bạn không thể thách đấu chính mình hoặc Bot!", ephemeral=True)
        return

    pets = load_pets()
    p1 = pets.get(str(interaction.user.id), {}).get("pet")
    p2 = pets.get(str(opponent.id), {}).get("pet")

    if not p1:
        await interaction.response.send_message("❌ Bạn chưa có Linh Thú! Hãy dùng `/nuoithu` để mở trứng.", ephemeral=True)
        return
    if not p2:
        await interaction.response.send_message(f"❌ {opponent.mention} chưa có Linh Thú để tham gia PvP!", ephemeral=True)
        return

    p1_pwr = calculate_pet_power(p1)
    p2_pwr = calculate_pet_power(p2)

    embed = discord.Embed(
        title="⚔️ ─── THÁCH ĐẤU LINH THÚ THƯỢNG CỔ ─── ⚔️",
        description=f"⚔️ **{interaction.user.mention}** (`{p1_pwr} PWR`) muốn thách đấu Linh Thú với **{opponent.mention}** (`{p2_pwr} PWR`)!\n\nNhấn nút bên dưới trong **60s** để chấp nhận!",
        color=discord.Color.gold()
    )
    view = PvPChallengeView(interaction.user, opponent)
    await interaction.response.send_message(content=opponent.mention, embed=embed, view=view)

# ==============================================================================
# --- 6. /SHOP (TIMEOUT=NONE) & MODAL ADD ITEM ADMIN ---
# ==============================================================================
class AddShopItemModal(discord.ui.Modal, title="➕ Thêm Vật Phẩm Shop (Admin)"):
    shop_target = discord.ui.TextInput(label="Chọn Shop (fishing / pet)", placeholder="fishing hoặc pet", required=True)
    item_id = discord.ui.TextInput(label="ID Vật Phẩm", placeholder="can_kc", required=True)
    item_name = discord.ui.TextInput(label="Tên & Icon Vật Phẩm", placeholder="💎 Cần Kim Cương", required=True)
    item_price = discord.ui.TextInput(label="Giá Điểm", placeholder="1000", required=True)
    item_buff1 = discord.ui.TextInput(label="Buff 1 (% Câu/Cá Hiếm/EXP/PWR)", placeholder="0.15", required=False)
    item_buff2 = discord.ui.TextInput(label="Buff 2 (Thời hạn min / 0=vĩnh viễn)", placeholder="600", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
            return

        target = self.shop_target.value.strip().lower()
        i_id = self.item_id.value.strip()
        name = self.item_name.value.strip()
        try:
            price = int(self.item_price.value)
            b1 = float(self.item_buff1.value) if self.item_buff1.value else 0.0
            b2 = int(self.item_buff2.value) if self.item_buff2.value else 0
        except:
            await interaction.response.send_message("❌ Giá hoặc chỉ số buff không hợp lệ!", ephemeral=True)
            return

        if target == "fishing":
            FISHING_ITEMS[i_id] = {
                "name": name, "type": "can", "rarity": "Đặc Biệt",
                "price": price, "succ_bonus": b1, "desc": f"Vật phẩm câu cá đặc biệt (Buff: {b1})"
            }
            safe_save_json(FISHING_ITEMS_FILE, FISHING_ITEMS)
        else:
            PET_ITEMS[i_id] = {
                "name": name, "price": price, "buff_pwr": int(b1),
                "duration": b2, "add_exp": int(b1), "desc": f"Đồ pet đặc biệt (Buff: {b1})"
            }
            safe_save_json(PET_ITEMS_FILE, PET_ITEMS)

        await interaction.response.send_message(f"✅ Đã thêm thành công vật phẩm **{name}** vào Shop `{target}`!", ephemeral=True)

class ShopBuyDropdown(discord.ui.Select):
    def __init__(self, items_dict, prefix):
        options = []
        for key, val in list(items_dict.items())[:25]:
            options.append(discord.SelectOption(
                label=f"{val['name']} ({val['price']} điểm)",
                value=f"{prefix}_{key}",
                description=val.get("desc", "Trang bị thượng cổ")[:100]
            ))
        super().__init__(placeholder="🛒 Chọn vật phẩm muốn mua...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        selected = self.values[0]
        prefix, key = selected.split("_", 1)

        data = load_data()
        user_pts = data.get(user_id, {}).get("weekly", 0)
        item_data = FISHING_ITEMS.get(key) if prefix == "fish" else PET_ITEMS.get(key)

        if not item_data:
            await interaction.response.send_message("❌ Vật phẩm không tồn tại!", ephemeral=True)
            return

        price = item_data["price"]
        if user_pts < price:
            await interaction.response.send_message(f"❌ Bạn không đủ điểm! Cần `{price}` điểm (Hiện có: `{user_pts}`).", ephemeral=True)
            return

        add_points(user_id, -price)
        pets = load_pets()
        if user_id not in pets:
            pets[user_id] = {"pet": None, "inventory": {}}
        
        inv = pets[user_id].get("inventory", {})
        inv[key] = inv.get(key, 0) + 1
        pets[user_id]["inventory"] = inv
        save_pets(pets)

        await interaction.response.send_message(f"🎉 Bạn đã mua thành công **{item_data['name']}**! Đã chuyển vào tủ đồ.", ephemeral=True)

class GlobalShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎣 Shop Cần & Mồi", style=discord.ButtonStyle.primary, custom_id="shop_fishing_btn")
    async def shop_fishing(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopBuyDropdown(FISHING_ITEMS, "fish"))
        embed = discord.Embed(title="🎣 ─── SHOP CẦN CÂU & MỒI CÂU ─── 🎣", color=discord.Color.teal())
        for k, v in FISHING_ITEMS.items():
            embed.add_field(name=f"{v['name']} — `{v['price']}đ`", value=f"ℹ️ {v.get('desc','N/A')}", inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🥩 Shop Đồ Ăn & Trang Bị Pet", style=discord.ButtonStyle.success, custom_id="shop_pet_btn")
    async def shop_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopBuyDropdown(PET_ITEMS, "pet"))
        embed = discord.Embed(title="🥩 ─── SHOP ĐỒ ĂN & TRANG BỊ PET ─── 🥩", color=discord.Color.green())
        for k, v in PET_ITEMS.items():
            embed.add_field(name=f"{v['name']} — `{v['price']}đ`", value=f"ℹ️ {v.get('desc','N/A')}", inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="➕ Update Vật Phẩm (Admin)", style=discord.ButtonStyle.secondary, custom_id="shop_update_btn")
    async def shop_update(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
            return
        await interaction.response.send_modal(AddShopItemModal())

@bot.tree.command(name="shop", description="Mở cửa hàng Thượng Cổ mua trang bị và đồ ăn!")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏪 ─── CỬA HÀNG THƯỢNG CỔ TỔNG HỢP ─── 🏪",
        description="Chào mừng bạn đến với Cửa Hàng Thượng Cổ! Vui lòng chọn danh mục bên dưới để mua sắm.",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=GlobalShopView())

# ==============================================================================
# --- 7. /CAUSONG (TIMEOUT=NONE) & ADMIN ADD FISH ---
# ==============================================================================
class AddFishModal(discord.ui.Modal, title="➕ Thêm Cá / Vật Phẩm Câu Mới"):
    f_id = discord.ui.TextInput(label="ID Cá", placeholder="ca_than", required=True)
    f_name = discord.ui.TextInput(label="Tên & Icon Cá", placeholder="🐉 Cá Thần Long", required=True)
    f_type = discord.ui.TextInput(label="Cấp Độ / Độ Hiếm", placeholder="Hiếm / Sử Thi / Thần Thoại", required=True)
    f_pts = discord.ui.TextInput(label="Điểm Cộng/Trừ", placeholder="500", required=True)
    f_rate = discord.ui.TextInput(label="Tỷ Lệ Tỷ Trọng (Weight)", placeholder="5.0", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
            return
        try:
            pts = int(self.f_pts.value)
            weight = float(self.f_rate.value)
        except:
            await interaction.response.send_message("❌ Điểm hoặc Weight phải là số!", ephemeral=True)
            return

        new_fish = {
            "id": self.f_id.value.strip(),
            "name": self.f_name.value.strip(),
            "type": self.f_type.value.strip(),
            "pts": pts,
            "weight": weight
        }
        FISH_TABLE.append(new_fish)
        safe_save_json(FISH_TABLE_FILE, FISH_TABLE)
        await interaction.response.send_message(f"✅ Đã thêm **{new_fish['name']}** vào Bờ Sông thành công!", ephemeral=True)

class CauSongView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎣 Vung Cần Câu Cá", style=discord.ButtonStyle.success, custom_id="causong_fish_btn")
    async def fish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        u_id = str(interaction.user.id)
        now = time.time()

        if u_id in fishing_cooldowns and (now - fishing_cooldowns[u_id]) < 5:
            wait = int(5 - (now - fishing_cooldowns[u_id]))
            await interaction.response.send_message(f"⏳ **Hãy chờ {wait}s** nữa mới quăng cần tiếp được!", ephemeral=True)
            return
        fishing_cooldowns[u_id] = now

        pets = load_pets()
        inv = pets.get(u_id, {}).get("inventory", {})

        # Tỷ lệ thành công cơ bản 45%
        success_rate = 0.45
        for item_k in inv:
            if item_k in FISHING_ITEMS:
                success_rate += FISHING_ITEMS[item_k].get("succ_bonus", 0)

        if random.random() > success_rate:
            await interaction.response.send_message("🌊 **Rất tiếc!** Cá đã đớp hụt mồi, câu thất bại rồi!")
            return

        weights = [f["weight"] for f in FISH_TABLE]
        caught = random.choices(FISH_TABLE, weights=weights)[0]
        pts = caught["pts"]
        new_score = add_points(u_id, pts)

        msg = f"🎉 Chúc mừng {interaction.user.mention} câu được **{caught['name']}** (`{caught['type']}`)!\n"
        msg += f"📈 Thưởng: **+{pts} điểm** (Tổng điểm tuần: `{new_score}`)." if pts >= 0 else f"📉 Rủi ro: Phạt **{pts} điểm** (Tổng điểm tuần: `{new_score}`)."

        if "title" in caught:
            add_custom_title(u_id, caught["title"])
            msg += f"\n🏆 **ĐẶC BIỆT!** Bạn nhận được danh hiệu: **[{caught['title']}]**!"

        await interaction.response.send_message(msg)

    @discord.ui.button(label="➕ Thêm Cá Mới (Admin)", style=discord.ButtonStyle.secondary, custom_id="causong_add_btn")
    async def add_fish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
            return
        await interaction.response.send_modal(AddFishModal())

@bot.tree.command(name="causong", description="Vung cần câu cá bên bờ sông Thượng Cổ!")
async def causong(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌊 ─── BỜ SÔNG THƯỢNG CỔ ─── 🌊",
        description="🌾 *Nơi quăng cần săn bảo vật thượng cổ.*\nTỷ lệ thành công mặc định là **45%**. Mua mồi & cần trong `/shop` để tăng tỷ lệ!",
        color=discord.Color.teal()
    )
    await interaction.response.send_message(embed=embed, view=CauSongView())
# ==============================================================================
# --- 9. /TUIDO (TÚI ĐỒ & SỬ DỤNG VẬT PHẨM) ---
# ==============================================================================
class UseItemSelect(discord.ui.Select):
    def __init__(self, inventory):
        options = []
        for item_key, quantity in inventory.items():
            if quantity <= 0:
                continue
            # Tìm tên vật phẩm từ FISHING_ITEMS hoặc PET_ITEMS
            item_info = FISHING_ITEMS.get(item_key) or PET_ITEMS.get(item_key)
            if item_info:
                name = item_info.get("name", item_key)
                item_type = "Mồi/Cần" if item_key in FISHING_ITEMS else "Đồ Pet"
                options.append(discord.SelectOption(
                    label=f"{name} (x{quantity})",
                    value=item_key,
                    description=f"Loại: {item_type} - {item_info.get('desc', '')[:90]}"
                ))
        
        if not options:
            options.append(discord.SelectOption(label="Túi đồ trống", value="empty", description="Hãy mua thêm vật phẩm tại /shop"))
            
        super().__init__(placeholder="🎒 Chọn vật phẩm muốn sử dụng / cho pet ăn...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "empty":
            await interaction.response.send_message("❌ Túi đồ của bạn đang trống!", ephemeral=True)
            return

        item_key = self.values[0]
        u_id = str(interaction.user.id)
        
        pets = load_pets()
        if u_id not in pets or "inventory" not in pets[u_id] or pets[u_id]["inventory"].get(item_key, 0) <= 0:
            await interaction.response.send_message("❌ Bạn không còn sở hữu vật phẩm này trong túi đồ!", ephemeral=True)
            return

        # Kiểm tra xem đây là vật phẩm cho Pet hay Vật phẩm câu cá
        if item_key in PET_ITEMS:
            # Kiểm tra xem người chơi đã có Pet chưa
            pet_data = pets[u_id].get("pet")
            if not pet_data:
                await interaction.response.send_message("❌ Bạn chưa có Linh Thú để sử dụng vật phẩm này! Hãy dùng `/nuoithu` để mở trứng.", ephemeral=True)
                return

            item_info = PET_ITEMS[item_key]
            add_exp = item_info.get("add_exp", 0)
            buff_pwr = item_info.get("buff_pwr", 0)
            duration = item_info.get("duration", 0)

            msg = f"🍖 Bạn đã cho Linh Thú ăn **{item_info['name']}** thành công!\n"

            # Xử lý tăng EXP hoặc Buff lực chiến
            if add_exp > 0:
                leveled_up = add_exp_to_pet(pet_data, add_exp)
                msg += f"✨ Nhận thêm **+{add_exp} EXP** cho Linh Thú!\n"
                if leveled_up:
                    new_name = get_pet_display_name(pet_data)
                    msg += f"🎉 **LINH THÚ ĐÃ LÊN CẤP!** Hình thái hiện tại: **{new_name}** (Lv.{pet_data.get('level')})"

            if buff_pwr > 0:
                if duration > 0:
                    pet_data["temp_power"] = buff_pwr
                    pet_data["buff_until"] = time.time() + duration
                    msg += f"⚡ Tăng tạm thời `+{buff_pwr} PWR` trong {duration // 60} phút!"
                else:
                    pet_data["perm_power"] = pet_data.get("perm_power", 0) + buff_pwr
                    msg += f"🌟 Tăng vĩnh viễn `+{buff_pwr} PWR` cho Linh Thú!"

            # Trừ số lượng item trong túi đồ
            pets[u_id]["inventory"][item_key] -= 1
            if pets[u_id]["inventory"][item_key] <= 0:
                del pets[u_id]["inventory"][item_key]
            save_pets(pets)

            await interaction.response.send_message(msg, ephemeral=True)

        elif item_key in FISHING_ITEMS:
            item_info = FISHING_ITEMS[item_key]
            await interaction.response.send_message(f"🎣 Vật phẩm **{item_info['name']}** thuộc loại trang bị câu cá. Nó sẽ **tự động kích hoạt** tỷ lệ khi bạn bấm quăng cần ở `/causong`!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Không xác định được loại vật phẩm này!", ephemeral=True)

class InventoryView(discord.ui.View):
    def __init__(self, inventory):
        super().__init__(timeout=60)
        self.add_item(UseItemSelect(inventory))

@bot.tree.command(name="tuido", description="Mở túi đồ cá nhân để xem trang bị, mồi câu và cho pet ăn!")
async def tuido(interaction: discord.Interaction):
    u_id = str(interaction.user.id)
    pets = load_pets()
    inv = pets.get(u_id, {}).get("inventory", {})

    embed = discord.Embed(
        title=f"🎒 ─── TÚI ĐỒ CỦA {interaction.user.display_name.upper()} ─── 🎒",
        description="Quản lý mồi câu, cần câu và đồ ăn cho Linh Thú của bạn.\n*Chọn vật phẩm bên dưới để sử dụng hoặc cho pet ăn.*",
        color=discord.Color.blurple()
    )

    if not inv:
        embed.add_field(name="Trạng thái", value="Túi đồ của bạn đang trống rỗng. Hãy ghé thăm `/shop` để mua sắm!", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    desc = ""
    for item_key, qty in inv.items():
        if qty <= 0:
            continue
        item_info = FISHING_ITEMS.get(item_key) or PET_ITEMS.get(item_key)
        if item_info:
            desc += f"• **{item_info['name']}** x`{qty}` — *{item_info.get('desc', '')}*\n"

    embed.add_field(name="📦 Danh Sách Vật Phẩm", value=desc if desc else "Không có vật phẩm nào.", inline=False)
    view = InventoryView(inv)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
# ==============================================================================
# --- 8. /NUOITHU (NUÔI THÚ ẢO & MỞ TRỨNG) ---
# ==============================================================================
class AddPetModal(discord.ui.Modal, title="➕ Thêm Pet Mới (Admin)"):
    p_id = discord.ui.TextInput(label="ID Pet", placeholder="rua_than", required=True)
    p_name = discord.ui.TextInput(label="Tên Hiển Thị", placeholder="Rùa Thần", required=True)
    p_rarity = discord.ui.TextInput(label="Độ Hiếm", placeholder="Hiếm", required=True)
    p_rate = discord.ui.TextInput(label="Tỷ Lệ Mở Ra (%)", placeholder="30", required=True)
    p_icon1 = discord.ui.TextInput(label="Tên & Icon Cấp 1", placeholder="🐢 Rùa Thần Con", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
            return
        try: rate = int(self.p_rate.value)
        except: rate = 10

        PET_DATABASE[self.p_id.value.strip()] = {
            "name": self.p_name.value.strip(), "rarity": self.p_rarity.value.strip(), "rate": rate,
            "forms": {"1": self.p_icon1.value.strip()}, "exp_caps": {"1": 500}, "step_exp": 1000,
            "base_pwr": 20, "high_pwr": 150
        }
        safe_save_json(PET_DATABASE_FILE, PET_DATABASE)
        await interaction.response.send_message(f"✅ Đã thêm Pet **{self.p_name.value}** vào Trứng!", ephemeral=True)

class NuoiThuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🥚 Mở Trứng Linh Thú (100đ)", style=discord.ButtonStyle.primary, custom_id="pet_open_egg_btn")
    async def open_egg(self, interaction: discord.Interaction, button: discord.ui.Button):
        u_id = str(interaction.user.id)
        data = load_data()
        pts = data.get(u_id, {}).get("weekly", 0)

        if pts < 100:
            await interaction.response.send_message("❌ Bạn cần **100 điểm** để mở Trứng Linh Thú!", ephemeral=True)
            return

        add_points(u_id, -100)
        
        # Chọn Pet ngẫu nhiên theo Tỷ lệ
        keys = list(PET_DATABASE.keys())
        weights = [PET_DATABASE[k]["rate"] for k in keys]
        chosen_key = random.choices(keys, weights=weights)[0]
        chosen_pet = PET_DATABASE[chosen_key]

        pets = load_pets()
        if u_id not in pets: pets[u_id] = {"pet": None, "inventory": {}}

        pets[u_id]["pet"] = {
            "type": chosen_key,
            "level": 1, "exp": 0, "perm_power": 0
        }
        save_pets(pets)

        embed = discord.Embed(
            title="🥚 ─── MỞ TRỨNG LINH THÚ THÀNH CÔNG ─── 🥚",
            description=f"🎉 Chúc mừng {interaction.user.mention} đã ấp nở thành công Linh Thú:\n\n✨ **{chosen_pet['forms'].get('1', chosen_pet['name'])}** (`{chosen_pet['rarity']}`)",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="🐾 Xem Linh Thú Của Tôi", style=discord.ButtonStyle.success, custom_id="pet_view_my_btn")
    async def view_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        u_id = str(interaction.user.id)
        pets = load_pets()
        pet = pets.get(u_id, {}).get("pet")

        if not pet:
            await interaction.response.send_message("❌ Bạn chưa có Linh Thú! Bấm nút **Mở Trứng** để nhận.", ephemeral=True)
            return

        p_name = get_pet_display_name(pet)
        p_pwr = calculate_pet_power(pet)
        p_cfg = PET_DATABASE[pet["type"]]

        embed = discord.Embed(title=f"🐾 LINH THÚ CỦA BẠN: {p_name}", color=discord.Color.gold())
        embed.add_field(name="📊 Cấp Độ", value=f"`Lv.{pet.get('level',1)}` (EXP: `{pet.get('exp',0)}`)", inline=True)
        embed.add_field(name="⚔️ Sức Mạnh", value=f"`{p_pwr} PWR`", inline=True)
        embed.add_field(name="✨ Độ Hiếm", value=f"`{p_cfg.get('rarity','Thường')}`", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="➕ Thêm Pet Mới (Admin)", style=discord.ButtonStyle.secondary, custom_id="pet_add_btn")
    async def add_pet_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
            return
        await interaction.response.send_modal(AddPetModal())

@bot.tree.command(name="nuoithu", description="Mở trứng ấp nở và chăm sóc Linh Thú!")
async def nuoithu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🐣 ─── TRANG TRẠI NUÔI THÚ THƯỢNG CỔ ─── 🐣",
        description="Mở trứng ngẫu nhiên nhận Linh Thú Thượng Cổ với giá **100 điểm**!",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=NuoiThuView())

# ==============================================================================
# --- 9. CÁC LỆNH BỔ SUNG: /CUOP, /TAIXIU, /BANGXEPHANG, ADMIN COMMANDS ---
# ==============================================================================
@bot.tree.command(name="cuop", description="Thử vận may cướp điểm thành viên khác!")
async def cuop(interaction: discord.Interaction, victim: discord.Member):
    if victim.id == interaction.user.id or victim.bot:
        await interaction.response.send_message("❌ Bạn không thể cướp của chính mình hoặc Bot!", ephemeral=True)
        return

    u1 = str(interaction.user.id)
    u2 = str(victim.id)
    data = load_data()
    v_pts = data.get(u2, {}).get("weekly", 0)

    if v_pts <= 0:
        await interaction.response.send_message(f"❌ {victim.mention} không có điểm nào để cướp!", ephemeral=True)
        return

    if random.random() < 0.45: # Thành công 45%
        if random.random() < 0.05: # 5% Cướp sạch
            stolen = v_pts
            msg_extra = "🔥 **ĐẶC BIỆT:** Bạn đã cướp sạch toàn bộ số điểm của nạn nhân!"
        else:
            stolen = random.randint(10, min(1000, v_pts))
            msg_extra = ""
        add_points(u1, stolen)
        add_points(u2, -stolen)
        await interaction.response.send_message(f"🥷 {interaction.user.mention} đã cướp thành công **{stolen} điểm** từ {victim.mention}! {msg_extra}")
    else: # Thất bại / Bị phạt 55%
        penalty = random.randint(10, 1000)
        add_points(u1, -penalty)
        add_points(u2, penalty)
        await interaction.response.send_message(f"🚔 {interaction.user.mention} đã cướp thất bại và bị phạt **{penalty} điểm** bồi thường trực tiếp cho {victim.mention}!")

@bot.tree.command(name="taixiu", description="Minigame Tài Xỉu đặt cược điểm!")
async def taixiu(interaction: discord.Interaction, luachon: str, tiencuoc: int):
    u_id = str(interaction.user.id)
    data = load_data()
    pts = data.get(u_id, {}).get("weekly", 0)

    if tiencuoc <= 0 or pts < tiencuoc:
        await interaction.response.send_message("❌ Điểm cược không hợp lệ hoặc bạn không đủ điểm!", ephemeral=True)
        return

    choice = luachon.strip().lower()
    if choice not in ["tài", "tai", "xỉu", "xiu"]:
        await interaction.response.send_message("❌ Vui lòng chọn 'Tài' hoặc 'Xỉu'!", ephemeral=True)
        return

    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    result = "Tài" if total >= 11 else "Xỉu"

    win = (choice in ["tài", "tai"] and result == "Tài") or (choice in ["xỉu", "xiu"] and result == "Xỉu")

    if win:
        # Thắng nhận gấp đôi tiền cược (+ tiencuoc * 2)
        new_pts = add_points(u_id, tiencuoc * 2)
        await interaction.response.send_message(f"🎲 Xúc xắc: `{d1}` - `{d2}` - `{d3}` => **{total} ({result})**\n🎉 Chúc mừng bạn đã THẮNG gấp đôi **+{tiencuoc * 2} điểm** (Tổng: `{new_pts}`).")
    else:
        # Thua trừ gấp đôi tiền cược (- tiencuoc * 2)
        new_pts = add_points(u_id, -(tiencuoc * 2))
        await interaction.response.send_message(f"🎲 Xúc xắc: `{d1}` - `{d2}` - `{d3}` => **{total} ({result})**\n😭 Bạn đã THUA gấp đôi **-{tiencuoc * 2} điểm** (Tổng: `{new_pts}`).")
@bot.tree.command(name="bangxephang", description="Xem Bảng Xếp Hạng Điểm Cống Hiến!")
async def bangxephang(interaction: discord.Interaction):
    data = load_data()
    titles = load_titles()
    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:10]

    embed = discord.Embed(title="🏆 ─── BẢNG XẾP HẠNG THƯỢNG CỔ ─── 🏆", color=discord.Color.gold())
    desc = ""
    for idx, (u_id, score) in enumerate(sorted_users, 1):
        icon = "🔹"
        if str(idx) in titles:
            icon = f"{titles[str(idx)]['icon']} **[{titles[str(idx)]['name']}]**"
        desc += f"`#{idx}` {icon} <@{u_id}> — **{score.get('weekly',0)}** điểm\n"

    embed.description = desc if desc else "Chưa có dữ liệu."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add_question", description="Thêm câu hỏi đố vui mẹo mới (Admin)")
async def add_question(interaction: discord.Interaction, question: str, answer: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
        return
    trivia = load_trivia()
    trivia.append({"q": question, "a": [ans.strip().lower() for ans in answer.split(",")]})
    save_trivia(trivia)
    await interaction.response.send_message(f"✅ Đã thêm câu hỏi đố vui mới!", ephemeral=True)

@bot.tree.command(name="reset_week_manual", description="Reset điểm tuần & chốt Top thủ công (Admin)")
async def reset_week_manual(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
        return
    msg = await process_weekly_rewards()
    await interaction.response.send_message(f"✅ Đã chốt Top tuần và reset điểm thành công!\n\n{msg}")

@bot.tree.command(name="set_top_title", description="Cấu hình danh hiệu Top 1, 2, 3 (Admin)")
async def set_top_title(interaction: discord.Interaction, top: int, icon: str, name: str, role: discord.Role = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
        return
    if top not in [1, 2, 3]:
        await interaction.response.send_message("❌ Chỉ chọn Top 1, 2 hoặc 3!", ephemeral=True)
        return
    titles = load_titles()
    titles[str(top)] = {"icon": icon, "name": name, "role_id": role.id if role else None}
    save_titles(titles)
    await interaction.response.send_message(f"✅ Đã đổi danh hiệu Top {top} thành: {icon} **[{name}]**", ephemeral=True)

@bot.tree.command(name="set_game_channel", description="Cấu hình kênh gửi Minigame & Thông báo (Admin)")
async def set_game_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)
        return
    cfg = load_config()
    cfg["game_channel_id"] = channel.id
    save_config(cfg)
    await interaction.response.send_message(f"✅ Đã cài đặt kênh Game tại {channel.mention}", ephemeral=True)
# ==============================================================================
# --- 9.5. HỆ THỐNG /LEOTHAP (ĐÁNH BOSS VƯỢT THÁP) ---
# ==============================================================================
TOWER_BOSS_FILE = "tower_bosses.json"

DEFAULT_TOWER_BOSSES = {
    "1": {"name": "👾 Quái nhỏ", "pwr": 20, "reward": 100, "title": "Dũng Sĩ Tầng 1", "effect": ""},
    "2": {"name": "👨🏻‍🐰‍👨🏼 Ma zumbi", "pwr": 40, "reward": 120, "title": "Săn Xác Sống", "effect": ""},
    "3": {"name": "👺 Chúa quỷ orozon", "pwr": 100, "reward": 200, "title": "Khắc Tinh Orozon", "effect": ""},
    "4": {"name": "🤖 Romaku", "pwr": 150, "reward": 300, "title": "Kẻ Hủy Diệt Romaku", "effect": ""},
    "5": {"name": "🫀 Ma ma thần khu", "pwr": 300, "reward": 320, "title": "Trấn Áp Thần Khu", "effect": ""},
    "6": {"name": "🐲 Leviathan", "pwr": 1000, "reward": 1200, "title": "Sát Long Leviathan", "effect": ""},
    "7": {"name": "🐙 Kraken vua biển cả", "pwr": 2000, "reward": 3000, "title": "Bá Chủ Đại Dương", "effect": ""},
    "8": {"name": "🦣 behemonth", "pwr": 3000, "reward": 4000, "title": "Hủy Diệt Behemoth", "effect": ""},
    "9": {"name": "😈 Quỷ thần Satan", "pwr": 10000, "reward": 6000, "title": "Khất Thực Satan", "effect": ""},
    "10": {"name": "💀 Adim", "pwr": 900000000, "reward": 1, "title": "Kẻ Thách Thức Thần Linh", "effect": ""}
}

def load_tower_bosses():
    return safe_load_json(TOWER_BOSS_FILE, DEFAULT_TOWER_BOSSES)

def save_tower_bosses(data):
    safe_save_json(TOWER_BOSS_FILE, data)

class AddOrUpdateTowerBossModal(discord.ui.Modal, title="⚙️ Quản Lý Boss Tháp (Admin)"):
    floor_num = discord.ui.TextInput(label="Số Tầng (1-10 hoặc số mới)", placeholder="Ví dụ: 1", required=True)
    boss_name = discord.ui.TextInput(label="Tên Boss", placeholder="👾 Chúa Tể Hắc Ám", required=True)
    boss_pwr = discord.ui.TextInput(label="Lực Chiến Boss (PWR)", placeholder="5000", required=True)
    boss_reward = discord.ui.TextInput(label="Điểm Thưởng Khi Thắng", placeholder="1500", required=True)
    boss_effect = discord.ui.TextInput(label="Hiệu Ứng Gây Ra (Không bắt buộc)", placeholder="Gây tê liệt, mất lượt...", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền cấu hình Boss!", ephemeral=True)
            return

        f_key = self.floor_num.value.strip()
        name = self.boss_name.value.strip()
        effect = self.boss_effect.value.strip()

        try:
            pwr = int(self.boss_pwr.value)
            reward = int(self.boss_reward.value)
        except ValueError:
            await interaction.response.send_message("❌ Lực chiến và Điểm thưởng phải là số nguyên!", ephemeral=True)
            return

        bosses = load_tower_bosses()
        
        # Cơ chế ghi đè / thêm mới
        bosses[f_key] = {
            "name": name,
            "pwr": pwr,
            "reward": reward,
            "title": f"Chinh Phục Tầng {f_key}",
            "effect": effect
        }
        save_tower_bosses(bosses)

        await interaction.response.send_message(f"✅ Đã cập nhật thành công Boss cho **Tầng {f_key}** (`{name}` - Lực chiến: `{pwr}`)!", ephemeral=True)

class DeleteTowerBossModal(discord.ui.Modal, title="🗑️ Xóa Boss Tháp (Admin)"):
    floor_num = discord.ui.TextInput(label="Nhập Tầng Cần Xóa Boss", placeholder="Ví dụ: 10", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền xóa!", ephemeral=True)
            return
        
        f_key = self.floor_num.value.strip()
        bosses = load_tower_bosses()
        if f_key in bosses:
            del bosses[f_key]
            save_tower_bosses(bosses)
            await interaction.response.send_message(f"✅ Đã xóa Boss tại Tầng {f_key} thành công!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Không tìm thấy Boss ở Tầng {f_key}!", ephemeral=True)

class TowerFloorSelect(discord.ui.Select):
    def __init__(self):
        bosses = load_tower_bosses()
        options = []
        for floor, b in sorted(bosses.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            options.append(discord.SelectOption(
                label=f"Tầng {floor}: {b['name']}",
                value=str(floor),
                description=f"Lực chiến yêu cầu: {b['pwr']} | Thưởng: {b['reward']} điểm"
            ))
        super().__init__(placeholder="🏰 Chọn tầng tháp muốn khiêu chiến...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        u_id = str(interaction.user.id)
        pets = load_pets()
        user_pet_info = pets.get(u_id, {})
        p_data = user_pet_info.get("pet")

        if not p_data:
            await interaction.response.send_message("❌ Bạn chưa sở hữu Linh Thú! Hãy dùng `/nuoithu` để mở trứng tham gia chiến đấu.", ephemeral=True)
            return

        floor_chosen = self.values[0]
        bosses = load_tower_bosses()
        boss = bosses.get(floor_chosen)

        if not boss:
            await interaction.response.send_message("❌ Tầng tháp này không tồn tại hoặc đã bị xóa!", ephemeral=True)
            return

        pet_pwr = calculate_pet_power(p_data)
        boss_pwr = boss["pwr"]
        p_name = get_pet_display_name(p_data)

        embed = discord.Embed(
            title=f"⚔️ ─── KẾT QUẢ KHIÊU CHIẾN TẦNG {floor_chosen} ─── ⚔️",
            color=discord.Color.dark_red()
        )

        embed.add_field(name="🐾 Linh Thú Của Bạn", value=f"{p_name}\nLực chiến: `{pet_pwr} PWR`", inline=True)
        embed.add_field(name=f"👹 Boss: {boss['name']}", value=f"Lực chiến: `{boss_pwr} PWR`\nHiệu ứng: `{boss['effect'] if boss['effect'] else 'Không có'}`", inline=True)

        # Kiểm tra thắng thua dựa trên lực chiến
        if pet_pwr >= boss_pwr:
            reward = boss["reward"]
            new_score = add_points(u_id, reward)
            title_to_give = boss.get("title")
            if title_to_give:
                add_custom_title(u_id, title_to_give)

            embed.description = f"🎉 **CHIẾN THẮNG VẺ VANG!**\nLinh Thú của bạn đã áp đảo và đánh bại **{boss['name']}** tại Tầng {floor_chosen}!"
            embed.add_field(name="🎁 Phần Thưởng", value=f"🪙 Nhận được **+{reward} điểm** (Điểm tuần: `{new_score}`)\n👑 Mở khóa danh hiệu: **[{title_to_give}]**", inline=False)
            embed.color = discord.Color.green()
        else:
            embed.description = f"💀 **THẤT BẠI!**\nLực chiến Linh Thú của bạn quá yếu so với **{boss['name']}**. Cần rèn luyện thêm lực chiến qua `/shop` hoặc `/nuoithu`!"
            embed.color = discord.Color.red()

        await interaction.response.send_message(embed=embed, ephemeral=False)

class TowerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TowerFloorSelect())

    @discord.ui.button(label="➕ Update Boss (Admin)", style=discord.ButtonStyle.secondary, custom_id="tower_update_admin_btn", row=1)
    async def update_boss_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền cập nhật Boss!", ephemeral=True)
            return
        await interaction.response.send_modal(AddOrUpdateTowerBossModal())

    @discord.ui.button(label="🗑️ Xóa Boss (Admin)", style=discord.ButtonStyle.danger, custom_id="tower_delete_admin_btn", row=1)
    async def delete_boss_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền xóa Boss!", ephemeral=True)
            return
        await interaction.response.send_modal(DeleteTowerBossModal())

@bot.tree.command(name="leothap", description="Mở cổng không gian Tháp Thượng Cổ để khiêu chiến các Boss cực mạnh!")
async def leothap(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🗼 ─── THÁP THƯỢNG CỔ - ĐÁNH BOSS ─── 🗼",
        description="Chào mừng các chiến thần đến với Tháp Thượng Cổ.\nHãy chọn tầng bên dưới để đưa Linh Thú vào giao tranh.\n*Lưu ý: Lực chiến Linh Thú của bạn phải lớn hơn hoặc bằng lực chiến của Boss mới có thể chiến thắng!*",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Quản trị viên có thể bấm nút bên dưới để thêm/sửa/xóa Boss theo ý muốn.")
    await interaction.response.send_message(embed=embed, view=TowerView())
    # ==============================================================================
# --- 11. /POINT_EDIT (QUẢN TRỊ VIÊN CỘNG/TRỪ ĐIỂM THÀNH VIÊN) ---
# ==============================================================================
@bot.tree.command(name="point_edit", description="[Admin] Cộng hoặc trừ điểm của một thành viên trong server.")
@app_commands.default_permissions(administrator=True)
async def point_edit(interaction: discord.Interaction, user: discord.Member, amount: int):
    # Kiểm tra lại quyền Admin chắc chắn
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bạn không có quyền quản trị viên để sử dụng lệnh này!", ephemeral=True)
        return

    u_id = str(user.id)
    
    # Thực hiện cộng hoặc trừ điểm (hàm add_points đã tự xử lý logic giới hạn không âm hoặc cộng trừ)
    new_score = add_points(u_id, amount)
    
    # Tạo thông báo phản hồi phù hợp
    if amount >= 0:
        msg = f"✅ Đã **cộng thêm `+{amount}` điểm** cho {user.mention}. Tổng điểm tuần hiện tại: `{new_score}`."
    else:
        msg = f"⚠️ Đã **trừ `{amount}` điểm** của {user.mention}. Tổng điểm tuần hiện tại: `{new_score}`."

    embed = discord.Embed(
        title="🛠️ ─── QUẢN LÝ ĐIỂM THÀNH VIÊN (ADMIN) ─── 🛠️",
        description=msg,
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Thực hiện bởi Admin: {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=False)
# ==============================================================================
# --- 10. CHẠY BOT ---
# ==============================================================================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("BOT_TOKEN") # Đảm bảo cài đặt BOT_TOKEN trong biến môi trường
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("[ERROR] Chưa có BOT_TOKEN trong Environment Variable!")

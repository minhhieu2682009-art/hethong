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
# --- 0. CẤU HÌNH ROLE TOP TUẦN & ADMIN ---
# ==============================================================================
ROLE_TOP1_ID = 123456789012345678
ROLE_TOP2_ID = 123456789012345678
ROLE_TOP3_ID = 123456789012345678

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
PET_DB_FILE = "pet_database.json"
PET_ITEMS_FILE = "pet_items.json"
BOSS_FILE = "boss_tower.json"
FISH_FILE = "fish_table.json"

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
        {"q": "Có một chiếc xe tải đi vào đường cấm, dù đi qua trước mặt rất nhiều cảnh sát giao thông nhưng không ai phạt. Hỏi tại sao?", "a": ["đi bộ", "bác tài đi bộ", "tài xế đi bộ"]}
    ]
    return safe_load_json(TRIVIA_FILE, default_trivia)

def save_trivia(data): safe_save_json(TRIVIA_FILE, data)

# --- KHỞI TẠO DỮ LIỆU ĐỘNG CHO SHOP, PET, BOSS, CÁ ---
DEFAULT_FISHING_ITEMS = {
    "moi_canh_gio": {"name": "🪽 Mồi cánh gió", "type": "moi", "rarity": "Thường ⚪", "price": 100, "succ_bonus": 0.01},
    "moi_sao": {"name": "✨ Mồi sao", "type": "moi", "rarity": "Hiếm 🟢", "price": 200, "succ_bonus": 0.10},
    "moi_sumo": {"name": "🥞 Mồi sumo", "type": "moi", "rarity": "Sử Thi 🟣", "price": 10000, "succ_bonus": 0.12},
    "moi_tien_ca": {"name": "🧜 Mồi nàng tiên cá", "type": "moi", "rarity": "Thần Thoại 🟡", "price": 25000, "succ_bonus": 0.16},
    "can_banh_mi": {"name": "🥖 Cần bánh mì", "type": "can", "rarity": "Thường ⚪", "price": 10, "succ_bonus": 0},
    "can_set": {"name": "⚡ Cần sét", "type": "can", "rarity": "Hiếm 🟢", "price": 100, "succ_bonus": 0.01},
    "can_lua": {"name": "🔥 Cần lửa", "type": "can", "rarity": "Hiếm 🟢", "price": 1000, "succ_bonus": 0.03}
}

DEFAULT_PET_DATABASE = {
    "sutu": {
        "name": "Sư tử con", "rarity": "Thường ⚪",
        "forms": {"1": "🦁 Sư tử con", "2": "🐅 Vương sư", "3": "⚡🐅 Thần hổ sét"},
        "exp_caps": {"1": 100, "2": 1100, "3": 2000}, "next_exp": 1000,
        "base_pwr_per_lvl": 10, "high_pwr_per_lvl": 100
    },
    "gau": {
        "name": "Gấu con", "rarity": "Thường ⚪",
        "forms": {"1": "🐻 Gấu con", "2": "🦝 Gấu mèo", "3": "👺 Quỷ gấu"},
        "exp_caps": {"1": 100, "2": 1200, "3": 1200}, "next_exp": 1000,
        "base_pwr_per_lvl": 10, "high_pwr_per_lvl": 100
    },
    "gautruc": {
        "name": "Gấu trúc", "rarity": "Hiếm 🟢",
        "forms": {"1": "🐼 Gấu trúc con", "2": "🐼🐉 Gấu long", "3": "🦹🐼 Gấu ma rồng"},
        "exp_caps": {"1": 200, "2": 1500, "3": 3000}, "next_exp": 2000,
        "base_pwr_per_lvl": 30, "high_pwr_per_lvl": 200
    },
    "phuonghoang": {
        "name": "Phượng hoàng con", "rarity": "Sử Thi 🟣",
        "forms": {"1": "🦅 Phượng hoàng con", "2": "🦅✨ Thần phượng", "3": "🌅🦅 Phượng ngưu"},
        "exp_caps": {"1": 1000, "2": 3000, "3": 4000}, "next_exp": 5000,
        "base_pwr_per_lvl": 50, "high_pwr_per_lvl": 500
    },
    "rong": {
        "name": "Rồng con", "rarity": "Thần Thoại 🟡",
        "forms": {"1": "🐉 Rồng con", "2": "🐉🔥 Thần tử chi long", "3": "🐲👑 Phong long chính thất"},
        "exp_caps": {"1": 2000, "2": 3000, "3": 4000}, "next_exp": 10000,
        "base_pwr_per_lvl": 1000, "high_pwr_per_lvl": 5000
    }
}

DEFAULT_PET_ITEMS = {
    "cam_duong": {"name": "🍎 Cam dương", "price": 300, "type": "power", "buff_power": 20, "duration": 600, "perm": False},
    "nam_ky_lung": {"name": "🍄 Nấm kỳ lung", "price": 1000, "type": "power", "buff_power": 100, "duration": 600, "perm": False},
    "tinh_cau": {"name": "🪐 Tinh cầu", "price": 10000, "type": "power", "buff_power": 10, "duration": 0, "perm": True},
    "kiquy": {"name": "🧡 Kí quỷ", "price": 10, "type": "exp", "add_exp": 10},
    "ngao_thi": {"name": "🪲 Ngao thị", "price": 1000, "type": "exp", "add_exp": 200},
    "thit_long_thu": {"name": "🥩 Thịt long thú", "price": 10000, "type": "exp", "add_exp": 10000}
}

DEFAULT_BOSS_TOWER = {
    "1": {"name": "👾 Quái nhỏ", "power": 20, "reward": 100},
    "2": {"name": "👨🏻‍🐰‍👨🏼 Ma zumbi", "power": 40, "reward": 120},
    "3": {"name": "👺 Chúa quỷ orozon", "power": 100, "reward": 200},
    "4": {"name": "🤖 Romaku", "power": 150, "reward": 300},
    "5": {"name": "🫀 Ma ma thần khu", "power": 300, "reward": 320},
    "6": {"name": "🐲 Leviathan", "power": 1000, "reward": 1200},
    "7": {"name": "🐙 Kraken vua biển cả", "power": 2000, "reward": 3000},
    "8": {"name": "🦣 Behemonth", "power": 3000, "reward": 4000},
    "9": {"name": "😈 Quỷ thần Satan", "power": 10000, "reward": 6000},
    "10": {"name": "💀 Adim", "power": 900000000, "reward": 1}
}

DEFAULT_FISH_TABLE = [
    {"id": "ro_dong", "name": "🐟 Cá Rô Đồng", "type": "thuong", "pts": 10, "weight": 50},
    {"id": "chep_vang", "name": "🐠 Cá Chép Vàng", "type": "thuong", "pts": 10, "weight": 50},
    {"id": "giay_rach", "name": "👞 Giày Cũ Bị Rách", "type": "xui", "pts": -100, "weight": 40},
    {"id": "ruong_bau", "name": "👑 Rương Báu Dưới Sông", "type": "hiem", "pts": 100, "weight": 40},
    {"id": "voi_sat_than", "name": "🫍 Cá voi sát thần", "type": "than_thoai", "pts": 500, "title": "🛡️ Sát Long", "weight": 1.0}
]

def load_fishing_shop(): return safe_load_json(SHOP_FILE, DEFAULT_FISHING_ITEMS)
def save_fishing_shop(d): safe_save_json(SHOP_FILE, d)

def load_pet_db(): return safe_load_json(PET_DB_FILE, DEFAULT_PET_DATABASE)
def save_pet_db(d): safe_save_json(PET_DB_FILE, d)

def load_pet_items(): return safe_load_json(PET_ITEMS_FILE, DEFAULT_PET_ITEMS)
def save_pet_items(d): safe_save_json(PET_ITEMS_FILE, d)

def load_boss_tower(): return safe_load_json(BOSS_FILE, DEFAULT_BOSS_TOWER)
def save_boss_tower(d): safe_save_json(BOSS_FILE, d)

def load_fish_table(): return safe_load_json(FISH_FILE, DEFAULT_FISH_TABLE)
def save_fish_table(d): safe_save_json(FISH_FILE, d)

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

# --- 4. TASKS TỰ ĐỘNG CHẠY NGẦM ---
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
        if not channel_id: return
        
        channel = bot.get_channel(channel_id)
        if not channel: return
        
        trivia_list = load_trivia()
        if not trivia_list: return
        
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
# --- 5. CÂU CÁ & LỆNH /causong CÓ NÚT BẤM CÂU CÁ + THÊM CÁ (ADMIN) ---
# ==============================================================================

class AddFishModal(discord.ui.Modal, title="🎣 [ADMIN] Thêm Cá / Vật Phẩm Mới"):
    f_id = discord.ui.TextInput(label="ID Cá (viết liền không dấu)", placeholder="vd: ca_rong", required=True)
    f_name = discord.ui.TextInput(label="Tên Cá (có Icon)", placeholder="vd: 🐉 Cá Rồng Đỏ", required=True)
    f_type = discord.ui.TextInput(label="Loại (thuong, hiem, su_thi, than_thoai, xui)", default="thuong", required=True)
    f_pts = discord.ui.TextInput(label="Điểm thưởng/trừ", default="50", required=True)
    f_weight = discord.ui.TextInput(label="Tỉ lệ xuất hiện (Weight)", default="30.0", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền thêm cá!", ephemeral=True)
            return
        
        fish_table = load_fish_table()
        try:
            pts = int(self.f_pts.value)
            weight = float(self.f_weight.value)
        except ValueError:
            await interaction.response.send_message("❌ Điểm và Tỉ lệ phải là chữ số!", ephemeral=True)
            return

        new_fish = {
            "id": self.f_id.value.strip(),
            "name": self.f_name.value.strip(),
            "type": self.f_type.value.strip(),
            "pts": pts,
            "weight": weight
        }
        fish_table.append(new_fish)
        save_fish_table(fish_table)

        embed = discord.Embed(
            title="✅ ĐÃ THÊM CÁ MỚI VÀO SÔNG!",
            description=f"🐟 **Tên:** {new_fish['name']}\n🏷️ **Loại:** `{new_fish['type']}` | 🎁 **Điểm:** `{new_fish['pts']}` | 📊 **Tỉ lệ:** `{new_fish['weight']}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CauSongView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Thả Cần Câu Cá 🎣", style=discord.ButtonStyle.success)
    async def fish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        user_pets_data = load_pets()
        user_inventory = user_pets_data.get(user_id, {}).get("inventory", {})

        fishing_items = load_fishing_shop()
        base_success_rate = 0.45
        
        active_moi = user_inventory.get("active_moi")
        active_can = user_inventory.get("active_can")
        
        if active_moi and active_moi in fishing_items:
            base_success_rate += fishing_items[active_moi].get("succ_bonus", 0)
        if active_can and active_can in fishing_items:
            base_success_rate += fishing_items[active_can].get("succ_bonus", 0)

        if random.random() > base_success_rate:
            await interaction.response.send_message("🎣 **Rất tiếc!** Bạn đã quăng cần nhưng cá cắn hụt, câu thất bại rồi!", ephemeral=True)
            return

        fish_table = load_fish_table()
        weights = []
        for fish in fish_table:
            w = fish["weight"]
            if fish["type"] == "hiem" and active_moi == "moi_sao":
                w *= 1.5
            elif fish["type"] == "su_thi" and active_moi == "moi_sumo":
                w *= 1.8
            elif fish["type"] == "than_thoai" and active_moi == "moi_tien_ca":
                w *= 2.0
            weights.append(w)

        caught = random.choices(fish_table, weights=weights)[0]
        pts = caught["pts"]
        new_score = add_points(user_id, pts)

        embed = discord.Embed(
            title="🎣 BẬT CẦN TRÚNG LỚN!",
            description=f"Bạn đã giật cần thành công và bắt được **{caught['name']}**!",
            color=discord.Color.blue()
        )
        if pts >= 0:
            embed.add_field(name="🎁 Phần Thưởng", value=f"**+{pts} điểm** (Tổng điểm tuần: `{new_score}`)", inline=False)
        else:
            embed.add_field(name="📉 Xui Xẻo", value=f"**{pts} điểm** (Điểm tuần còn lại: `{new_score}`)", inline=False)

        if "title" in caught:
            add_custom_title(user_id, caught["title"])
            embed.add_field(name="🎉 DANH HIỆU KHAI QUẬT", value=f"🏆 **[{caught['title']}]**", inline=False)

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Thêm Cá Mới (Admin) ➕", style=discord.ButtonStyle.danger)
    async def add_fish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Administrator mới được sử dụng nút này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddFishModal())

@bot.tree.command(name="causong", description="Thư giãn đi câu cá bờ sông nhận điểm thưởng!")
async def causong(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌊 BỜ SÔNG CÂU CÁ GIẢI TRÍ 🌊",
        description="Hãy bấm nút **Thả Cần Câu Cá 🎣** bên dưới để trải nghiệm vận may của bạn!\n*Trang bị Cần & Mồi xịn tại `/shop` để tăng tỉ lệ thắng cá khủng.*",
        color=discord.Color.teal()
    )
    view = CauSongView()
    await interaction.response.send_message(embed=embed, view=view)

# ==============================================================================
# --- 6. HỆ THỐNG NUÔI THÚ ẢO (/nuoithu) CÓ NÚT THÊM PET DÀNH CHO ADMIN ---
# ==============================================================================

def calculate_pet_power(pet_data):
    if not pet_data or "type" not in pet_data:
        return 0
    p_type = pet_data["type"]
    pet_db = load_pet_db()
    if p_type not in pet_db:
        return 0
    cfg = pet_db[p_type]
    lvl = pet_data["level"]
    
    base_power = 0
    for l in range(1, lvl + 1):
        if l < 20:
            base_power += cfg.get("base_pwr_per_lvl", 10)
        else:
            base_power += cfg.get("high_pwr_per_lvl", 100)
            
    base_power += pet_data.get("perm_power", 0)
    
    now = time.time()
    if pet_data.get("buff_until", 0) > now:
        base_power += pet_data.get("temp_power", 0)
        
    return base_power

def get_pet_name(pet_data):
    if not pet_data or "type" not in pet_data:
        return "Chưa sở hữu Pet"
    pet_db = load_pet_db()
    if pet_data["type"] not in pet_db:
        return "Pet Không Xác Định"
    p_cfg = pet_db[pet_data["type"]]
    lvl = str(pet_data["level"])
    forms = p_cfg.get("forms", {})
    return forms.get(lvl, forms.get("3", p_cfg.get("name", "Thần Thú")))

def add_exp_to_pet(pet_data, exp_amount):
    pet_data["exp"] += exp_amount
    pet_db = load_pet_db()
    p_cfg = pet_db.get(pet_data["type"], {})
    
    leveled_up = False
    while True:
        lvl = str(pet_data["level"])
        exp_caps = p_cfg.get("exp_caps", {})
        max_exp = exp_caps.get(lvl, p_cfg.get("next_exp", 1000))
        if pet_data["exp"] >= max_exp:
            pet_data["level"] += 1
            pet_data["exp"] -= max_exp
            leveled_up = True
        else:
            break
    return leveled_up

def make_progress_bar(current, total, length=10):
    percent = min(1.0, max(0.0, current / total)) if total > 0 else 0
    filled = int(round(length * percent))
    return "🟩" * filled + "⬛" * (length - filled)

def create_pet_embed(user_name, pet_data, user_points):
    pet_db = load_pet_db()
    p_cfg = pet_db.get(pet_data["type"], {})
    lvl = pet_data["level"]
    form_name = get_pet_name(pet_data)
    exp_caps = p_cfg.get("exp_caps", {})
    max_exp = exp_caps.get(str(lvl), p_cfg.get("next_exp", 1000))
    power = calculate_pet_power(pet_data)
    
    progress_bar = make_progress_bar(pet_data["exp"], max_exp)
    percent_str = f"{(pet_data['exp'] / max_exp * 100):.1f}%" if max_exp > 0 else "100%"

    embed = discord.Embed(
        title=f"✨ TRANG TRẠI THÚ CƯNG CỦA {user_name.upper()} ✨",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="🐾 Thần Thú Hiện Tại",
        value=f"> **{form_name}**\n> 🔖 Phẩm cấp: `{p_cfg.get('rarity', 'Thường ⚪')}`",
        inline=False
    )
    embed.add_field(
        name="📊 Chỉ Số Chiến Đấu",
        value=f"⭐ **Cấp độ:** `Lv.{lvl}`\n⚔️ **Lực chiến:** `{power:,} Pwr`",
        inline=True
    )
    embed.add_field(
        name="💰 Điểm Hiện Có",
        value=f"🪙 **Số dư:** `{user_points:,}` điểm",
        inline=True
    )
    embed.add_field(
        name=f"📈 Tiến Trình Kinh Nghiệm [{percent_str}]",
        value=f"`{progress_bar}`\n`{pet_data['exp']:,} / {max_exp:,} EXP`",
        inline=False
    )
    embed.set_footer(text="Cho Pet ăn hằng ngày để sẵn sàng tham gia Đánh Boss & PvP!")
    return embed

class AddPetModal(discord.ui.Modal, title="🐉 [ADMIN] Thêm Loại Pet Mới"):
    pet_id = discord.ui.TextInput(label="ID Pet (viết liền không dấu)", placeholder="vd: phuong_hoang", required=True)
    pet_name = discord.ui.TextInput(label="Tên Pet (Form 1 có Icon)", placeholder="vd: 🦅 Phượng hoàng con", required=True)
    pet_rarity = discord.ui.TextInput(label="Phẩm cấp", default="Thần Thoại 🟡", required=True)
    pwr_lvl = discord.ui.TextInput(label="Lực chiến tăng mỗi cấp", default="50", required=True)
    form23 = discord.ui.TextInput(label="Tên Form 2 và Form 3 (phân cách bằng dấu ,)", placeholder="vd: 🦅✨ Thần Phượng, 🌅🦅 Phượng Ngưu", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền thêm Pet!", ephemeral=True)
            return

        pet_db = load_pet_db()
        forms_split = [f.strip() for f in self.form23.value.split(",")]
        f2 = forms_split[0] if len(forms_split) > 0 else self.pet_name.value
        f3 = forms_split[1] if len(forms_split) > 1 else f2

        new_pet = {
            "name": self.pet_name.value.strip(),
            "rarity": self.pet_rarity.value.strip(),
            "forms": {"1": self.pet_name.value.strip(), "2": f2, "3": f3},
            "exp_caps": {"1": 500, "2": 2000, "3": 5000},
            "next_exp": 5000,
            "base_pwr_per_lvl": int(self.pwr_lvl.value),
            "high_pwr_per_lvl": int(self.pwr_lvl.value) * 5
        }

        pet_db[self.pet_id.value.strip()] = new_pet
        save_pet_db(pet_db)

        embed = discord.Embed(
            title="✅ THÊM PET MỚI THÀNH CÔNG!",
            description=f"🐾 **ID:** `{self.pet_id.value}`\n✨ **Tên Form 1:** {new_pet['forms']['1']}\n🔮 **Phẩm cấp:** {new_pet['rarity']}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PetView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=120)
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
            await interaction.response.send_message("❌ Bạn không đủ **100 điểm** để mở trứng Pet!", ephemeral=True)
            return

        add_points(self.user_id, -100)
        pet_db = load_pet_db()
        pet_keys = list(pet_db.keys())
        pet_choice = random.choice(pet_keys) if pet_keys else "sutu"

        pets = load_pets()
        p_info = pet_db.get(pet_choice, DEFAULT_PET_DATABASE["sutu"])
        pets[self.user_id] = {
            "type": pet_choice,
            "level": 1,
            "exp": 0,
            "perm_power": 0,
            "temp_power": 0,
            "buff_until": 0
        }
        save_pets(pets)

        updated_pts = load_data().get(self.user_id, {}).get("weekly", 0)
        embed = create_pet_embed(interaction.user.display_name, pets[self.user_id], updated_pts)
        await interaction.response.edit_message(content=f"🎉 **Chúc mừng!** Bạn đã ấp thành công trứng và nhận được **{p_info['forms']['1']}**!", embed=embed, view=self)

    @discord.ui.button(label="Cho Pet Ăn (+100 EXP) - 500đ", style=discord.ButtonStyle.primary, emoji="🍖")
    async def feed_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_pets()
        p = pets.get(self.user_id)
        if not p or "type" not in p:
            await interaction.response.send_message("❌ Bạn chưa sở hữu Pet nào! Hãy mở trứng trước.", ephemeral=True)
            return

        data = load_data()
        pts = data.get(self.user_id, {}).get("weekly", 0)
        if pts < 500:
            await interaction.response.send_message(f"❌ Bạn không đủ điểm! Cần **500 điểm** để cho Pet ăn (Hiện có: `{pts}` điểm).", ephemeral=True)
            return

        add_points(self.user_id, -500)
        leveled_up = add_exp_to_pet(p, 100)
        save_pets(pets)
        
        updated_pts = load_data().get(self.user_id, {}).get("weekly", 0)
        embed = create_pet_embed(interaction.user.display_name, p, updated_pts)

        msg_content = "🍖 Bạn đã tốn **500 điểm** cho Pet ăn và nhận **+100 EXP**!"
        if leveled_up:
            msg_content += f"\n🎊 **THẮNG CẤP!** Pet của bạn đã thăng cấp lên **Lv.{p['level']}**!"

        await interaction.response.edit_message(content=msg_content, embed=embed, view=self)

    @discord.ui.button(label="Thêm Pet Mới (Admin) ➕", style=discord.ButtonStyle.danger)
    async def add_pet_admin_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Administrator mới được dùng tính năng này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddPetModal())

@bot.tree.command(name="nuoithu", description="Mở bảng điều khiển Thú Cưng Ảo")
async def nuoithu(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pets = load_pets()
    p = pets.get(user_id)
    data = load_data()
    user_pts = data.get(user_id, {}).get("weekly", 0)

    if not p or "type" not in p:
        embed = discord.Embed(
            title="🥚 BẠN CHƯA CÓ THÚ CƯNG",
            description="Hãy nhấn nút **Mở Trứng Pet (100đ)** bên dưới để thử vận may nhận Thần Thú!",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Số dư hiện tại", value=f"`{user_pts:,}` điểm")
    else:
        embed = create_pet_embed(interaction.user.display_name, p, user_pts)

    view = PetView(user_id)
    await interaction.response.send_message(embed=embed, view=view)

# ==============================================================================
# --- 7. HỆ THỐNG CỬA HÀNG (/shop) VỚI NÚT THÊM VẬT PHẨM DÀNH CHO ADMIN ---
# ==============================================================================

class AddShopItemModal(discord.ui.Modal, title="🛒 [ADMIN] Thêm Vật Phẩm Vào Shop"):
    shop_target = discord.ui.TextInput(label="Shop (fishing hoặc pet)", placeholder="Nhập: fishing hoặc pet", default="pet", required=True)
    item_id = discord.ui.TextInput(label="ID Vật phẩm (không dấu)", placeholder="vd: qua_tao_vang", required=True)
    item_name = discord.ui.TextInput(label="Tên Vật phẩm (kèm Icon)", placeholder="vd: 🍎 Táo Vàng Thần Kỳ", required=True)
    item_price = discord.ui.TextInput(label="Giá bán (điểm)", default="500", required=True)
    item_effect = discord.ui.TextInput(label="Tác dụng (EXP/Pwr/Bonus)", placeholder="vd: exp:500 hoặc pwr:50 hoặc succ:0.05", default="exp:500", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền thêm vật phẩm!", ephemeral=True)
            return

        target = self.shop_target.value.strip().lower()
        try:
            price = int(self.item_price.value)
        except ValueError:
            await interaction.response.send_message("❌ Giá bán phải là con số!", ephemeral=True)
            return

        eff = self.item_effect.value.strip().split(":")
        eff_type = eff[0].lower()
        eff_val = float(eff[1]) if len(eff) > 1 else 0

        if target == "fishing":
            shop_data = load_fishing_shop()
            shop_data[self.item_id.value] = {
                "name": self.item_name.value,
                "type": "moi" if "mồi" in self.item_name.value.lower() else "can",
                "rarity": "Đặc Biệt ✨",
                "price": price,
                "succ_bonus": eff_val
            }
            save_fishing_shop(shop_data)
        else:
            pet_items = load_pet_items()
            if eff_type == "exp":
                pet_items[self.item_id.value] = {"name": self.item_name.value, "price": price, "type": "exp", "add_exp": int(eff_val)}
            else:
                pet_items[self.item_id.value] = {"name": self.item_name.value, "price": price, "type": "power", "buff_power": int(eff_val), "duration": 600, "perm": True}
            save_pet_items(pet_items)

        embed = discord.Embed(
            title="✅ ĐÃ THÊM VẬT PHẨM MỚI VÀO SHOP!",
            description=f"🛍️ **Shop:** `{target.upper()}`\n📦 **Item:** {self.item_name.value}\n💰 **Giá:** `{price:,} điểm`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SelectFishingItemDropdown(discord.ui.Select):
    def __init__(self):
        items = load_fishing_shop()
        options = []
        for key, info in list(items.items())[:25]:
            options.append(discord.SelectOption(
                label=info['name'],
                value=key,
                description=f"Giá: {info['price']:,} điểm | Rarity: {info.get('rarity', 'Thuường')}"
            ))
        super().__init__(placeholder="🛒 Chọn Cần hoặc Mồi câu để mua...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        item_id = self.values[0]
        shop_data = load_fishing_shop()
        item = shop_data.get(item_id)
        
        data = load_data()
        pts = data.get(user_id, {}).get("weekly", 0)

        if pts < item["price"]:
            await interaction.response.send_message(f"❌ Bạn không đủ điểm! Cần `{item['price']:,}` điểm.", ephemeral=True)
            return

        add_points(user_id, -item["price"])
        pets = load_pets()
        if user_id not in pets:
            pets[user_id] = {"pet": None, "inventory": {}}
        if "inventory" not in pets[user_id]:
            pets[user_id]["inventory"] = {}

        if item["type"] == "moi":
            pets[user_id]["inventory"]["active_moi"] = item_id
        else:
            pets[user_id]["inventory"]["active_can"] = item_id

        save_pets(pets)
        await interaction.response.send_message(f"✅ Bạn đã mua thành công **{item['name']}** và tự động trang bị!", ephemeral=True)

class SelectPetItemDropdown(discord.ui.Select):
    def __init__(self):
        items = load_pet_items()
        options = []
        for key, info in list(items.items())[:25]:
            options.append(discord.SelectOption(
                label=info['name'],
                value=key,
                description=f"Giá: {info['price']:,} điểm"
            ))
        super().__init__(placeholder="🍖 Chọn thức ăn / vật phẩm cho Pet...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        item_id = self.values[0]
        items = load_pet_items()
        item = items.get(item_id)

        pets = load_pets()
        p = pets.get(user_id)
        if not p or "type" not in p:
            await interaction.response.send_message("❌ Bạn chưa có Pet để dùng vật phẩm!", ephemeral=True)
            return

        data = load_data()
        pts = data.get(user_id, {}).get("weekly", 0)
        if pts < item["price"]:
            await interaction.response.send_message(f"❌ Bạn không đủ điểm! Cần `{item['price']:,}` điểm.", ephemeral=True)
            return

        add_points(user_id, -item["price"])

        if item["type"] == "exp":
            exp_gained = item["add_exp"]
            old_lvl = p["level"]
            add_exp_to_pet(p, exp_gained)
            new_lvl = p["level"]
            msg = f"🎉 Bạn cho Pet ăn **{item['name']}**, nhận được **+{exp_gained} EXP**!"
            if new_lvl > old_lvl:
                msg += f"\n🎊 **CHÚC MỪNG!** Pet thăng cấp lên **Lv.{new_lvl}**!"
        else:
            if item.get("perm", False):
                p["perm_power"] = p.get("perm_power", 0) + item["buff_power"]
                msg = f"🎉 Đã dùng **{item['name']}**, tăng vĩnh viễn **+{item['buff_power']} Lực chiến**!"
            else:
                p["temp_power"] = item["buff_power"]
                p["buff_until"] = time.time() + item.get("duration", 600)
                msg = f"⚡ Đã dùng **{item['name']}**, tăng **+{item['buff_power']} Lực chiến** trong 10 phút!"

        save_pets(pets)
        await interaction.response.send_message(msg, ephemeral=True)

class MainShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Cửa Hàng Câu Cá 🎣", style=discord.ButtonStyle.primary)
    async def fishing_shop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        v = discord.ui.View()
        v.add_item(SelectFishingItemDropdown())
        embed = discord.Embed(
            title="🎣 CỬA HÀNG CẦN & MỒI CÂU",
            description="Hãy chọn vật phẩm bạn muốn mua từ danh sách bên dưới:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=v, ephemeral=True)

    @discord.ui.button(label="Cửa Hàng Thức Ăn Pet 🍖", style=discord.ButtonStyle.success)
    async def pet_shop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        v = discord.ui.View()
        v.add_item(SelectPetItemDropdown())
        embed = discord.Embed(
            title="🍖 CỬA HÀNG THỨC ĂN & VẬT PHẨM PET",
            description="Hãy chọn vật phẩm tăng EXP hoặc Lực chiến cho Pet:",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=v, ephemeral=True)

    @discord.ui.button(label="Thêm Đồ Shop (Admin) ➕", style=discord.ButtonStyle.danger)
    async def add_item_admin_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Administrator mới được dùng tính năng này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddShopItemModal())

@bot.tree.command(name="shop", description="Mở Cửa Hàng Tổng Hợp (Thức Ăn Pet & Cần/Mồi Câu Cá)")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛒 CỬA HÀNG TRỰC TUYẾN 🛒",
        description="Chào mừng bạn đến với Cửa Hàng Trung Tâm!\nNhấn vào các nút bên dưới để chọn mua vật phẩm mong muốn.",
        color=discord.Color.magenta()
    )
    view = MainShopView()
    await interaction.response.send_message(embed=embed, view=view)

# ==============================================================================
# --- 8. SỬA LẠI /pvp_pet CÓ ĐỒNG Ý / TỪ CHỐI & TÍNH TỈ LỆ THẮNG THUA CHUẨN ---
# ==============================================================================

class PvPChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.User, target: discord.User):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.target = target

    @discord.ui.button(label="Chấp Nhận ⚔️", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Lời thách đấu này không dành cho bạn!", ephemeral=True)
            return

        pets = load_pets()
        p1 = pets.get(str(self.challenger.id))
        p2 = pets.get(str(self.target.id))

        if not p1 or "type" not in p1 or not p2 or "type" not in p2:
            await interaction.response.send_message("❌ Một trong hai người chơi đã bị mất dữ liệu Pet!", ephemeral=True)
            return

        p1_pwr = calculate_pet_power(p1)
        p2_pwr = calculate_pet_power(p2)
        p1_name = get_pet_name(p1)
        p2_name = get_pet_name(p2)

        # CƠ CHẾ TÍNH TỈ LỆ THẮNG MỚI THEO YÊU CẦU:
        # Nếu bằng Lực chiến: 50% - 50%
        # Nếu P1 > P2: P1 có 60% thắng, P2 có 40% thắng
        # Nếu P2 > P1: P2 có 60% thắng, P1 có 40% thắng
        if p1_pwr == p2_pwr:
            p1_win_rate = 0.50
        elif p1_pwr > p2_pwr:
            p1_win_rate = 0.60
        else:
            p1_win_rate = 0.40

        reward = random.randint(100, 250)
        p1_wins = random.random() < p1_win_rate

        embed = discord.Embed(
            title="⚔️ TRẬN ĐẤU PVP PET KỊCH TÍNH ⚔️",
            description=f"🔴 **{self.challenger.mention}** - **{p1_name}** (`{p1_pwr} Pwr`)\n⚡ **VS** ⚡\n🔵 **{self.target.mention}** - **{p2_name}** (`{p2_pwr} Pwr`)",
            color=discord.Color.red()
        )

        if p1_wins:
            add_points(str(self.challenger.id), reward)
            embed.add_field(
                name="🏆 KẾT QUẢ TỶ THẮNG",
                value=f"🎉 **{self.challenger.mention}** đã giành chiến thắng (Tỉ lệ thắng: `{int(p1_win_rate*100)}%`) và nhận ngay **+{reward} điểm**!",
                inline=False
            )
        else:
            add_points(str(self.target.id), reward)
            embed.add_field(
                name="🏆 KẾT QUẢ TỶ THẮNG",
                value=f"🎉 **{self.target.mention}** đã lội ngược dòng chiến thắng (Tỉ lệ thắng: `{int((1-p1_win_rate)*100)}%`) và nhận ngay **+{reward} điểm**!",
                inline=False
            )

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(content="⚔️ **Trận đấu đã diễn ra thành công!**", embed=embed, view=self)

    @discord.ui.button(label="Từ Chối 🛡️", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Lời thách đấu này không dành cho bạn!", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(content=f"🛡️ **{self.target.mention} đã từ chối lời thách đấu PvP của {self.challenger.mention}!**", embed=None, view=self)

@bot.tree.command(name="pvp_pet", description="Thách đấu PvP Thú cưng với người chơi khác!")
async def pvp_pet(interaction: discord.Interaction, target: discord.User):
    challenger_id = str(interaction.user.id)
    target_id = str(target.id)

    if target_id == challenger_id:
        await interaction.response.send_message("❌ Bạn không thể tự PvP với chính mình!", ephemeral=True)
        return

    if target.bot:
        await interaction.response.send_message("❌ Bạn không thể thách đấu với Bot!", ephemeral=True)
        return

    pets = load_pets()
    p1 = pets.get(challenger_id)
    p2 = pets.get(target_id)

    if not p1 or "type" not in p1:
        await interaction.response.send_message("❌ Bạn chưa có Pet để tham gia PvP!", ephemeral=True)
        return

    if not p2 or "type" not in p2:
        await interaction.response.send_message(f"❌ {target.mention} hiện chưa sở hữu Pet nào!", ephemeral=True)
        return

    view = PvPChallengeView(interaction.user, target)
    embed = discord.Embed(
        title="⚔️ LỜI THÁCH ĐẤU PVP PET!",
        description=f"🔥 **{interaction.user.mention}** đã gửi lời thách đấu PvP Pet đến **{target.mention}**!\n\n*Vui lòng bấm **Chấp Nhận ⚔️** trong 60s để bắt đầu trận đấu.*",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(content=target.mention, embed=embed, view=view)

# ==============================================================================
# --- 9. HỆ THỐNG /danhboss CÓ NÚT THÊM BOSS DÀNH CHO ADMIN ---
# ==============================================================================

class AddBossModal(discord.ui.Modal, title="👹 [ADMIN] Thêm Tầng Boss Mới"):
    boss_floor = discord.ui.TextInput(label="Số Tầng", placeholder="vd: 11", required=True)
    boss_name = discord.ui.TextInput(label="Tên Boss (có Icon)", placeholder="vd: 🐉 Rồng Hắc Ám", required=True)
    boss_power = discord.ui.TextInput(label="Lực chiến Boss", placeholder="vd: 50000", required=True)
    boss_reward = discord.ui.TextInput(label="Phần thưởng (điểm)", placeholder="vd: 10000", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền thêm Boss!", ephemeral=True)
            return

        boss_tower = load_boss_tower()
        floor = self.boss_floor.value.strip()

        try:
            pwr = int(self.boss_power.value)
            rew = int(self.boss_reward.value)
        except ValueError:
            await interaction.response.send_message("❌ Lực chiến và Thưởng phải là số!", ephemeral=True)
            return

        boss_tower[floor] = {
            "name": self.boss_name.value.strip(),
            "power": pwr,
            "reward": rew
        }
        save_boss_tower(boss_tower)

        embed = discord.Embed(
            title="✅ ĐÃ THÊM BOSS MỚI VÀO THÁP!",
            description=f"🏰 **Tầng:** `{floor}` | 👺 **Boss:** {self.boss_name.value}\n⚔️ **Lực chiến:** `{pwr:,}` | 🎁 **Thưởng:** `{rew:,} điểm`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SelectBossFloorDropdown(discord.ui.Select):
    def __init__(self):
        boss_tower = load_boss_tower()
        options = []
        for floor, info in sorted(boss_tower.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
            options.append(discord.SelectOption(
                label=f"Tầng {floor}: {info['name']}",
                value=str(floor),
                description=f"Lực chiến: {info['power']:,} | Thưởng: {info['reward']:,}d"
            ))
        super().__init__(placeholder="🏰 Chọn Tầng Boss muốn khiêu chiến...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        pets = load_pets()
        p = pets.get(user_id)

        if not p or "type" not in p:
            await interaction.response.send_message("❌ Bạn chưa có Pet để tham gia đánh Boss! Hãy gõ `/nuoithu` để nhận Pet.", ephemeral=True)
            return

        boss_tower = load_boss_tower()
        floor = self.values[0]
        boss_info = boss_tower.get(floor)

        pet_pwr = calculate_pet_power(p)
        pet_name = get_pet_name(p)

        embed = discord.Embed(title=f"🏰 THÁP MA THẦN - TẦNG {floor}")
        embed.add_field(name="🐾 Thần thú chiến đấu", value=f"**{pet_name}** (Lực chiến: `{pet_pwr:,}`)", inline=False)
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
                value=f"💀 **THẤT BẠI!** Lực chiến của Pet (`{pet_pwr:,}`) chưa đủ để đánh bại **{boss_info['name']}** (`{boss_info['power']:,}`). Hãy cho Pet ăn để thăng cấp nhé!", 
                inline=False
            )

        await interaction.response.send_message(embed=embed)

class BossTowerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Khiêu Chiến Boss ⚔️", style=discord.ButtonStyle.primary)
    async def fight_boss_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        v = discord.ui.View()
        v.add_item(SelectBossFloorDropdown())
        embed = discord.Embed(
            title="👹 LỰA CHỌN TẦNG BOSS KHIÊU CHIẾN",
            description="Hãy chọn tầng Boss vừa sức để giành chiến thắng và mang về điểm số lớn:",
            color=discord.Color.dark_red()
        )
        await interaction.response.send_message(embed=embed, view=v, ephemeral=True)

    @discord.ui.button(label="Thêm Boss Mới (Admin) ➕", style=discord.ButtonStyle.danger)
    async def add_boss_admin_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Administrator mới được dùng tính năng này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddBossModal())

@bot.tree.command(name="danhboss", description="Đưa Pet đi khiêu chiến Boss các tầng để cày điểm!")
async def danhboss(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏰 KHUYÊN CHIẾN THÁP MA THẦN 🏰",
        description="Đưa Thần thú của bạn vượt tháp tiêu diệt Ma Vương để thu về hàng ngàn điểm cống hiến!\nBấm nút **Khiêu Chiến Boss ⚔️** bên dưới để chọn Tầng.",
        color=discord.Color.dark_purple()
    )
    view = BossTowerView()
    await interaction.response.send_message(embed=embed, view=view)

# ==============================================================================
# --- 10. CÁC LỆNH KHÁC (/cuop, /taixiu, /bangxephang, ADMIN) GIỮ NGUYÊN ---
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

# --- CÁC LỆNH ADMIN KHÁC ---
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

# --- 11. KÍCH HOẠT BOT ---
keep_alive()
TOKEN = os.getenv('TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("[ERROR] Không tìm thấy 'TOKEN' trong Environment Variables!")

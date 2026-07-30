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
ROLE_TOP1_ID = 123456789012345678 
ROLE_TOP2_ID = 123456789012345678 
ROLE_TOP3_ID = 123456789012345678 

# --- 1. WEB SERVER GIỮ BOT ONLINE 24/7 ---
app = Flask('')

@app.route('/')
def home():
    return "📜 Hệ Thống Thượng Cổ Bot Online 24/7!"

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
        "1": {"icon": "👑", "name": "Hư Quỷ"},
        "2": {"icon": "⚔️", "name": "khu la thần"},
        "3": {"icon": "🐎", "name": "thế thần"}
    }
    return safe_load_json(TITLES_FILE, default_titles)

def save_titles(titles): safe_save_json(TITLES_FILE, titles)

def load_trivia():
    default_trivia = [
        {"q": "Trong một cuộc thi chạy, nếu bạn vượt qua người đang đứng thứ hai, bạn sẽ đứng thứ mấy?", "a": ["thứ hai", "thứ 2", "2", "thu hai"]},
        {"q": "Bố của Mary có 5 cô con gái: Nana, Nene, Nini, Nono. Hỏi cô con gái thứ 5 tên là gì?", "a": ["mary", "tên là mary", "cô con gái thứ 5 tên là mary"]},
        {"q": "Có 3 quả táo trên bàn, bạn lấy đi 2 quả. Hỏi bạn còn bao nhiêu quả táo?", "a": ["2", "2 quả", "hai quả"]},
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

# DỮ LIỆU ĐỘNG BAN ĐẦU
FISHING_ITEMS = safe_load_json("fishing_items.json", {
    "moi_canh_gio": {"name": "🪽 Mồi Cánh Gió", "type": "moi", "rarity": "Thường", "price": 100, "succ_bonus": 0.01},
    "moi_sao": {"name": "✨ Mồi Sao", "type": "moi", "rarity": "Hiếm", "price": 200, "succ_bonus": 0.10},
    "can_banh_mi": {"name": "🥖 Cần Bánh Mì", "type": "can", "rarity": "Thường", "price": 10, "succ_bonus": 0},
    "can_lua": {"name": "🔥 Cần Lửa Tinh Anh", "type": "can", "rarity": "Thường", "price": 1000, "succ_bonus": 0.03}
})

FISH_TABLE = safe_load_json("fish_table.json", [
    {"id": "ro_dong", "name": "🐟 Cá Rô Đồng", "type": "Thường", "pts": 10, "weight": 50},
    {"id": "chep_vang", "name": "🐠 Cá Chép Vàng", "type": "Thường", "pts": 10, "weight": 50},
    {"id": "ruong_bau", "name": "👑 Rương Báu Cổ", "type": "Hiếm", "pts": 100, "weight": 40},
    {"id": "leviathan", "name": "🐉 Thượng Cổ Leviathan", "type": "Thần Thoại", "pts": 2000, "title": "🌊 Leviathan", "weight": 0.1}
])

PET_DATABASE = safe_load_json("pet_database.json", {
    "sutu": {
        "name": "Sư tử con", "rarity": "Thường",
        "forms": {1: "🦁 Sư Tử Con", 2: "🐅 Vương Sư", 3: "⚡🐅 Thần Hổ Sét"},
        "exp_caps": {1: 100, 2: 1100, 3: 2000}, "next_exp": 1000,
        "base_pwr_per_lvl": 10, "high_pwr_per_lvl": 100
    },
    "rong": {
        "name": "Rồng con", "rarity": "Thần Thoại",
        "forms": {1: "🐉 Rồng Con Thượng Cổ", 2: "🐉 Thần Tử Chi Long", 3: "🐲 Phong Long Chính Thất"},
        "exp_caps": {1: 2000, 2: 3000, 3: 4000}, "next_exp": 10000,
        "base_pwr_per_lvl": 1000, "high_pwr_per_lvl": 5000
    }
})

PET_ITEMS = safe_load_json("pet_items.json", {
    "kiquy": {"name": "🧡 Kí Quỷ", "price": 10, "type": "exp", "add_exp": 10, "rarity": "Thường"},
    "ngao_thi": {"name": "🪲 Ngao Thị", "price": 1000, "type": "exp", "add_exp": 200, "rarity": "Hiếm"},
    "thit_long_thu": {"name": "🥩 Thịt Long Thú", "price": 10000, "type": "exp", "add_exp": 10000, "rarity": "Thần Thoại"},
    "cam_duong": {"name": "🍎 Cam Dương", "price": 300, "type": "power", "buff_power": 20, "duration": 600, "perm": False, "rarity": "Thường"},
    "tinh_cau": {"name": "🪐 Tinh Cầu Thượng Cổ", "price": 10000, "type": "power", "buff_power": 10, "duration": 0, "perm": True, "rarity": "Thần Thoại"}
})

BOSS_TOWER = safe_load_json("boss_tower.json", {
    "1": {"name": "👾 Quái Nhỏ Thượng Cổ", "power": 20, "reward": 100},
    "2": {"name": "👨🏻‍🐰 Ma Zumbi Trăm Năm", "power": 40, "reward": 120},
    "3": {"name": "👺 Chúa Quỷ OROZON", "power": 100, "reward": 200},
    "10": {"name": "💀 ADIM Tối Cao", "power": 900000000, "reward": 1}
})

# --- 3. CẤU HÌNH BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- HELPER FUNCTIONS FOR PET ---
def calculate_pet_power(pet_data):
    if not pet_data or "type" not in pet_data or pet_data["type"] not in PET_DATABASE:
        return 0
    p_type = pet_data["type"]
    cfg = PET_DATABASE[p_type]
    lvl = pet_data["level"]
    base_power = 0
    for l in range(1, lvl + 1):
        if l < 20:
            base_power += cfg.get("base_pwr_per_lvl", 10)
        else:
            base_power += cfg.get("high_pwr_per_lvl", 100)
    base_power += pet_data.get("perm_power", 0)
    if pet_data.get("buff_until", 0) > time.time():
        base_power += pet_data.get("temp_power", 0)
    return base_power

def get_pet_name(pet_data):
    if not pet_data or "type" not in pet_data or pet_data["type"] not in PET_DATABASE:
        return "Không Có Pet"
    p_cfg = PET_DATABASE[pet_data["type"]]
    lvl = pet_data["level"]
    forms = p_cfg.get("forms", {})
    return forms.get(str(lvl), forms.get(1, p_cfg.get("name", "Pet")))

def add_exp_to_pet(pet_data, exp_amount):
    pet_data["exp"] += exp_amount
    p_cfg = PET_DATABASE[pet_data["type"]]
    leveled_up = False
    while True:
        lvl = pet_data["level"]
        caps = p_cfg.get("exp_caps", {})
        max_exp = caps.get(str(lvl), p_cfg.get("next_exp", 1000))
        if pet_data["exp"] >= max_exp:
            pet_data["level"] += 1
            pet_data["exp"] -= max_exp
            leveled_up = True
        else:
            break
    return leveled_up

async def process_weekly_rewards():
    data = load_data()
    if not data:
        return "📜 Không có dữ liệu điểm tuần để chốt."

    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:3]
    summary_lines = []
    for guild in bot.guilds:
        roles = [guild.get_role(ROLE_TOP1_ID), guild.get_role(ROLE_TOP2_ID), guild.get_role(ROLE_TOP3_ID)]
        for role in roles:
            if role:
                for member in role.members:
                    try: await member.remove_roles(role)
                    except: pass

        for index, (u_id, score) in enumerate(sorted_users):
            member = guild.get_member(int(u_id))
            target_role = roles[index] if index < len(roles) else None
            if member and target_role:
                try: await member.add_roles(target_role)
                except: pass
                summary_lines.append(f"👑 **Top {index+1}:** {member.mention} — `{score.get('weekly', 0)} điểm`")

    for u_id in data:
        data[u_id]["weekly"] = 0
    save_data(data)
    return "\n".join(summary_lines) if summary_lines else "Không tìm thấy thành viên Top trong Server."

# --- 4. TASKS NGẦM ---
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
            description="🏛️ *Tự động cập nhật vào lúc 08:00 sáng mỗi ngày*",
            color=discord.Color.from_rgb(212, 175, 55),
            timestamp=now
        )
        desc = ""
        for index, (u_id, score) in enumerate(sorted_users, 1):
            user = bot.get_user(int(u_id))
            name = user.mention if user else f"Anh Hùng <@{u_id}>"
            icon = "🔹"
            if str(index) in titles:
                t_icon = titles[str(index)]["icon"]
                t_name = titles[str(index)]["name"]
                icon = f"{t_icon} **[{t_name}]**"
            desc += f"`#{index}` {icon} {name} — 🪙 **{score.get('weekly', 0)}** điểm\n"
        embed.add_field(name="🏆 Danh Sách Cao Thủ", value=desc if desc else "Chưa có dữ liệu.", inline=False)
        embed.set_footer(text="⚔️ Thượng Cổ Phong Thần Bang")
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
                    title="🏛️ ─── KẾT QUẢ ĐUA TOP TUẦN & RESET DÂN VỌNG ─── 🏛️",
                    description=f"🎉 *Vinh danh những bậc cao thủ xuất sắc nhất tuần qua!*\n\n{msg}",
                    color=discord.Color.gold(),
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
            title="🏮 ─── THỬ THÁCH ĐỐ VUI MẸO ─── 🏮",
            description=f"❓ **Câu hỏi:** {item['q']}\n\n⚡ *Gõ câu trả lời vào chat trong 45s để nhận **+30 điểm**!*",
            color=discord.Color.dark_gold()
        )
        await channel.send(embed=embed)

        def check(m):
            return m.channel == channel and not m.bot and m.content.strip().lower() in [ans.lower() for ans in valid_ans]

        try:
            msg = await bot.wait_for('message', timeout=45.0, check=check)
            new_score = add_points(str(msg.author.id), 30)
            await channel.send(f"🎉 Chức mừng {msg.author.mention} trả lời đúng! Bạn nhận được **+30 điểm** (Điểm tuần: `{new_score}`).")
        except asyncio.TimeoutError:
            await channel.send(f"⏰ Hết thời gian! Đáp án chính xác là: **{valid_ans[0]}**")
    except Exception as e:
        print(f"[WARN] Lỗi minigame: {e}")

@auto_minigame_task.before_loop
async def before_minigame():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f"[SYSTEM] Bot Cổ Đại Đã Sẵn Sàng: {bot.user}")
    if not check_voice_points.is_running(): check_voice_points.start()
    if not auto_minigame_task.is_running(): auto_minigame_task.start()
    if not auto_reset_weekly_top.is_running(): auto_reset_weekly_top.start()
    if not auto_daily_leaderboard.is_running(): auto_daily_leaderboard.start()

    # Register Persistent Views (Timeout=None)
    bot.add_view(GlobalShopView())

    try:
        synced = await bot.tree.sync()
        print(f"[SYSTEM] Đã đồng bộ thành công {len(synced)} lệnh Slash (/)...")
    except Exception as e:
        print(f"[ERROR] Lỗi đồng bộ lệnh Slash: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    user_id = str(message.author.id)
    current_time = time.time()
    if user_id not in chat_cooldowns or (current_time - chat_cooldowns[user_id]) >= 60:
        pts = random.randint(1, 3)
        add_points(user_id, pts)
        chat_cooldowns[user_id] = current_time
    await bot.process_commands(message)

# ==============================================================================
# --- 5. LỆNH /CAUSONG VÀ MODAL THÊM CÁ (ADMIN) ---
# ==============================================================================
class AddFishModal(discord.ui.Modal, title="➕ Thêm Cá / Vật Phẩm Câu Mới"):
    f_id = discord.ui.TextInput(label="ID Cá (VD: ca_rong)", placeholder="ca_rong", required=True)
    f_name = discord.ui.TextInput(label="Tên Hiển Thị", placeholder="🐉 Cá Rồng Thần", required=True)
    f_type = discord.ui.TextInput(label="Loại / Độ Hiếm", placeholder="Thường / Hiếm / Thần Thoại", required=True)
    f_pts = discord.ui.TextInput(label="Điểm Cộng/Trừ", placeholder="100", required=True)
    f_weight = discord.ui.TextInput(label="Tỷ Lệ Tỷ Trọng (Weight)", placeholder="10.0", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Bạn không có quyền Admin!", ephemeral=True)
            return
        try:
            pts = int(self.f_pts.value)
            weight = float(self.f_weight.value)
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
        safe_save_json("fish_table.json", FISH_TABLE)
        await interaction.response.send_message(f"✅ Đã thêm cá **{new_fish['name']}** thành công vào Bờ Sông!", ephemeral=True)

class CauSongView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=120)
        self.user_id = str(user_id)
        self.last_fish_time = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Bảng câu cá này không thuộc về bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🎣 Bắt Đầu Câu Cá", style=discord.ButtonStyle.success)
    async def fish_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        now = time.time()
        if now - self.last_fish_time < 5:
            wait_t = int(5 - (now - self.last_fish_time))
            await interaction.response.send_message(f"⏳ **Chờ chút!** Bạn cần nghỉ ngơi **{wait_t}s** nữa mới quăng cần tiếp được!", ephemeral=True)
            return
        self.last_fish_time = now

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
            await interaction.response.send_message("🎣 **Rất tiếc!** Cá quẫy đuôi cắn hụt mồi, câu thất bại rồi!")
            return

        weights = [f.get("weight", 10) for f in FISH_TABLE]
        caught = random.choices(FISH_TABLE, weights=weights)[0]
        pts = caught["pts"]
        new_score = add_points(user_id, pts)

        msg = f"🌊 **[BỜ SÔNG THƯỢNG CỔ]**\n🎣 Bạn vung cần trúng lớn! Bắt được **{caught['name']}** (`{caught['type']}`)!\n"
        if pts >= 0:
            msg += f"📈 Thưởng: **+{pts} điểm** (Điểm tuần: `{new_score}`)."
        else:
            msg += f"📉 Xui xẻo: Phạt **{pts} điểm** (Điểm tuần: `{new_score}`)."

        if "title" in caught:
            add_custom_title(user_id, caught["title"])
            msg += f"\n🎉 **ĐẶC BIỆT!** Nhận danh hiệu Thần Thoại: **[{caught['title']}]**!"

        await interaction.response.send_message(msg)

    @discord.ui.button(label="➕ Thêm Cá Mới (Admin)", style=discord.ButtonStyle.secondary)
    async def add_fish_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được nút này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddFishModal())

@bot.tree.command(name="causong", description="Thư giãn đi câu cá bờ sông nhận điểm thưởng!")
async def causong(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌊 ─── BỜ SÔNG THƯỢNG CỔ ─── 🌊",
        description="🌾 *Nơi hội tụ các cần thủ quăng cần săn bảo vật thượng cổ.*\nNhấn nút bên dưới để bắt đầu quăng cần!",
        color=discord.Color.teal()
    )
    view = CauSongView(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)

# ==============================================================================
# --- 6. HỆ THỐNG /SHOP HOÀN CHỈNH (Timeout=None) & ADD ITEM ADMIN ---
# ==============================================================================
class AddShopItemModal(discord.ui.Modal, title="➕ Thêm Vật Phẩm Vào Shop"):
    shop_type = discord.ui.TextInput(label="Shop (Nhập 'ca' hoặc 'pet')", placeholder="ca", required=True)
    item_id = discord.ui.TextInput(label="ID Vật Phẩm", placeholder="can_huyen_thoai", required=True)
    item_name = discord.ui.TextInput(label="Tên Vật Phẩm", placeholder="⚡ Cần Huyền Thoại", required=True)
    price = discord.ui.TextInput(label="Giá Mua (Điểm)", placeholder="5000", required=True)
    rarity = discord.ui.TextInput(label="Độ Hiếm", placeholder="Thường / Hiếm / Thần Thoại", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Bạn không có quyền Admin!", ephemeral=True)
            return
        try:
            p_val = int(self.price.value)
        except:
            await interaction.response.send_message("❌ Giá phải là số nguyên!", ephemeral=True)
            return

        s_type = self.shop_type.value.strip().lower()
        if s_type == "ca":
            FISHING_ITEMS[self.item_id.value.strip()] = {
                "name": self.item_name.value.strip(),
                "price": p_val,
                "rarity": self.rarity.value.strip(),
                "type": "can",
                "succ_bonus": 0.05
            }
            safe_save_json("fishing_items.json", FISHING_ITEMS)
            await interaction.response.send_message(f"✅ Đã thêm **{self.item_name.value}** vào Cửa Hàng Cá!", ephemeral=True)
        elif s_type == "pet":
            PET_ITEMS[self.item_id.value.strip()] = {
                "name": self.item_name.value.strip(),
                "price": p_val,
                "rarity": self.rarity.value.strip(),
                "type": "exp",
                "add_exp": 500
            }
            safe_save_json("pet_items.json", PET_ITEMS)
            await interaction.response.send_message(f"✅ Đã thêm **{self.item_name.value}** vào Cửa Hàng Pet!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Shop type chỉ được nhập 'ca' hoặc 'pet'!", ephemeral=True)

class ShopSelectMenu(discord.ui.Select):
    def __init__(self, items_dict, shop_cat):
        self.shop_cat = shop_cat
        options = []
        for key, item in items_dict.items():
            options.append(discord.SelectOption(
                label=f"{item['name']} ({item.get('rarity', 'Thường')})",
                value=key,
                description=f"Giá: {item['price']:,} điểm"
            ))
        if not options:
            options.append(discord.SelectOption(label="Trống", value="none"))
        super().__init__(placeholder="🛒 Chọn vật phẩm cần mua...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

class GlobalShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎣 Cửa Hàng Câu Cá", style=discord.ButtonStyle.primary, custom_id="btn_shop_fish")
    async def shop_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        select = ShopSelectMenu(FISHING_ITEMS, "ca")
        view.add_item(select)

        async def buy_cb(inter: discord.Interaction):
            val = select.values[0]
            if val not in FISHING_ITEMS:
                await inter.response.send_message("❌ Vật phẩm không hợp lệ!", ephemeral=True)
                return
            item = FISHING_ITEMS[val]
            u_id = str(inter.user.id)
            data = load_data()
            pts = data.get(u_id, {}).get("weekly", 0)
            if pts < item["price"]:
                await inter.response.send_message(f"❌ Bạn cần `{item['price']:,}` điểm để mua!", ephemeral=True)
                return

            add_points(u_id, -item["price"])
            pets = load_pets()
            if u_id not in pets: pets[u_id] = {"inventory": {}}
            if "inventory" not in pets[u_id]: pets[u_id]["inventory"] = {}
            if item.get("type") == "moi": pets[u_id]["inventory"]["active_moi"] = val
            else: pets[u_id]["inventory"]["active_can"] = val
            save_pets(pets)
            await inter.response.send_message(f"🎉 Mua thành công **{item['name']}**!", ephemeral=True)

        buy_btn = discord.ui.Button(label="🛒 Mua Vật Phẩm", style=discord.ButtonStyle.success)
        buy_btn.callback = buy_cb
        view.add_item(buy_btn)

        embed = discord.Embed(title="🎣 ─── CỬA HÀNG CẦN & MỒI CÂU ─── 🎣", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🐾 Cửa Hàng Vật Phẩm Pet", style=discord.ButtonStyle.primary, custom_id="btn_shop_pet")
    async def shop_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        select = ShopSelectMenu(PET_ITEMS, "pet")
        view.add_item(select)

        async def buy_cb(inter: discord.Interaction):
            val = select.values[0]
            if val not in PET_ITEMS:
                await inter.response.send_message("❌ Vật phẩm không hợp lệ!", ephemeral=True)
                return
            item = PET_ITEMS[val]
            u_id = str(inter.user.id)
            pets = load_pets()
            p = pets.get(u_id)
            if not p or "type" not in p:
                await inter.response.send_message("❌ Bạn chưa sở hữu Pet!", ephemeral=True)
                return

            data = load_data()
            pts = data.get(u_id, {}).get("weekly", 0)
            if pts < item["price"]:
                await inter.response.send_message(f"❌ Bạn cần `{item['price']:,}` điểm!", ephemeral=True)
                return

            add_points(u_id, -item["price"])
            if item["type"] == "exp":
                add_exp_to_pet(p, item["add_exp"])
                msg = f"🎉 Cho Pet dùng **{item['name']}**, nhận **+{item['add_exp']} EXP**!"
            elif item["type"] == "power":
                if item.get("perm"):
                    p["perm_power"] = p.get("perm_power", 0) + item["buff_power"]
                    msg = f"🎉 Cho Pet dùng **{item['name']}**, vĩnh viễn **+{item['buff_power']} Lực chiến**!"
                else:
                    p["temp_power"] = item["buff_power"]
                    p["buff_until"] = time.time() + item.get("duration", 600)
                    msg = f"⚡ Cho Pet dùng **{item['name']}**, tăng **+{item['buff_power']} Lực chiến** trong 10p!"

            save_pets(pets)
            await inter.response.send_message(msg, ephemeral=True)

        buy_btn = discord.ui.Button(label="🛒 Mua Vật Phẩm", style=discord.ButtonStyle.success)
        buy_btn.callback = buy_cb
        view.add_item(buy_btn)

        embed = discord.Embed(title="🐾 ─── CỬA HÀNG VẬT PHẨM PET ─── 🐾", color=discord.Color.purple())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="➕ Thêm Vật Phẩm (Admin)", style=discord.ButtonStyle.secondary, custom_id="btn_shop_add")
    async def shop_add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được tính năng này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddShopItemModal())

@bot.tree.command(name="shop", description="Mở Trân Bảo Cắc - Cửa hàng mua sắm thượng cổ")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏛️ ─── TRÂN BẢO CÁC THƯỢNG CỔ ─── 🏛️",
        description="📜 *Chào mừng quý tiên hữu đến với Cửa Hàng. Hãy chọn phân mục bên dưới để mua sắm!*",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=GlobalShopView())

# ==============================================================================
# --- 7. HỆ THỐNG /NUOITHU & MODAL THÊM PET ADMIN ---
# ==============================================================================
class AddPetModal(discord.ui.Modal, title="➕ Thêm Loài Pet Mới"):
    p_id = discord.ui.TextInput(label="ID Pet", placeholder="phuonghoang", required=True)
    p_name = discord.ui.TextInput(label="Tên Trứng/Pet Initial", placeholder="Phượng Hoàng Con", required=True)
    p_rarity = discord.ui.TextInput(label="Độ Hiếm", placeholder="Thường / Hiếm / Thần Thoại", required=True)
    p_form1 = discord.ui.TextInput(label="Cấp 1 Form Name", placeholder="🦅 Phượng Hoàng Con", required=True)
    p_form2 = discord.ui.TextInput(label="Cấp 2 Form Name", placeholder="🔥 Thần Phượng Thượng Cổ", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Bạn không có quyền Admin!", ephemeral=True)
            return
        PET_DATABASE[self.p_id.value.strip()] = {
            "name": self.p_name.value.strip(),
            "rarity": self.p_rarity.value.strip(),
            "forms": {"1": self.p_form1.value.strip(), "2": self.p_form2.value.strip(), "3": self.p_form2.value.strip()},
            "exp_caps": {"1": 200, "2": 1000, "3": 2000},
            "base_pwr_per_lvl": 20,
            "high_pwr_per_lvl": 200
        }
        safe_save_json("pet_database.json", PET_DATABASE)
        await interaction.response.send_message(f"✅ Đã thêm Pet **{self.p_name.value}** thành công!", ephemeral=True)

class PetControlView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = str(user_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Bảng điều khiển này không thuộc về bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🥚 Mở Trứng Pet (100đ)", style=discord.ButtonStyle.success)
    async def open_egg(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        current_pts = data.get(self.user_id, {}).get("weekly", 0)
        if current_pts < 100:
            await interaction.response.send_message("❌ Bạn không đủ 100 điểm để mở trứng Pet!", ephemeral=True)
            return

        add_points(self.user_id, -100)
        keys = list(PET_DATABASE.keys())
        pet_choice = random.choice(keys) if keys else "sutu"

        pets = load_pets()
        p_info = PET_DATABASE[pet_choice]
        pets[self.user_id] = {
            "type": pet_choice, "level": 1, "exp": 0,
            "perm_power": 0, "temp_power": 0, "buff_until": 0
        }
        save_pets(pets)

        embed = discord.Embed(
            title="🎉 ─── KHAI MỞ THẦN TRỨNG ─── 🎉",
            description=f"✨ Chúc mừng bạn nhận được Linh Thú: **{p_info['forms'].get('1', p_info['name'])}** (`{p_info.get('rarity','Thường')}`)!",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🍖 Cho Pet Ăn (+100 EXP) - 500đ", style=discord.ButtonStyle.primary)
    async def feed_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_pets()
        p = pets.get(self.user_id)
        if not p or "type" not in p:
            await interaction.response.send_message("❌ Bạn chưa sở hữu Pet nào!", ephemeral=True)
            return

        data = load_data()
        pts = data.get(self.user_id, {}).get("weekly", 0)
        if pts < 500:
            await interaction.response.send_message("❌ Bạn không đủ 500 điểm để cho Pet ăn!", ephemeral=True)
            return

        add_points(self.user_id, -500)
        add_exp_to_pet(p, 100)
        save_pets(pets)

        form_name = get_pet_name(p)
        power = calculate_pet_power(p)
        p_cfg = PET_DATABASE.get(p["type"], {})
        max_exp = p_cfg.get("exp_caps", {}).get(str(p["level"]), 1000)

        embed = discord.Embed(
            title=f"🐾 ─── LINH THÚ: {form_name} ─── 🐾",
            description=f"⭐ **Cấp độ:** `{p['level']}`\n⚡ **Lực chiến:** `{power}`\n📈 **Kinh nghiệm:** `{p['exp']}/{max_exp}`\n💰 *Đã tốn 500 điểm cho ăn.*",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="➕ Thêm Pet (Admin)", style=discord.ButtonStyle.secondary)
    async def add_pet_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được nút này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddPetModal())

@bot.tree.command(name="nuoithu", description="Mở Bảng Điều Khiển Nuôi Thú Thượng Cổ")
async def nuoithu(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pets = load_pets()
    p = pets.get(user_id)

    if not p or "type" not in p:
        embed = discord.Embed(
            title="🥚 ─── CHƯA CÓ LINH THÚ ─── 🥚",
            description="Hãy nhấn nút **Mở Trứng Pet (100đ)** bên dưới để nhận Linh Thú!",
            color=discord.Color.gold()
        )
    else:
        lvl = p["level"]
        form_name = get_pet_name(p)
        p_cfg = PET_DATABASE.get(p["type"], {})
        max_exp = p_cfg.get("exp_caps", {}).get(str(lvl), 1000)
        power = calculate_pet_power(p)

        embed = discord.Embed(
            title=f"🐾 ─── LINH THÚ: {form_name} ─── 🐾",
            description=f"⭐ **Cấp độ:** `{lvl}`\n⚡ **Lực chiến:** `{power}`\n📈 **Kinh nghiệm:** `{p['exp']}/{max_exp}`",
            color=discord.Color.purple()
        )

    view = PetControlView(user_id)
    await interaction.response.send_message(embed=embed, view=view)

# ==============================================================================
# --- 8. NÂNG CẤP /PVP_PET (XÁC NHẬN & TỶ LỆ CHÍNH XÁC) ---
# ==============================================================================
class PvPInviteView(discord.ui.View):
    def __init__(self, challenger: discord.User, target: discord.User):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.target = target

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Bạn không phải là người được thách đấu!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⚔️ Chấp Nhận Tuyên Chiến", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_pets()
        p1 = pets.get(str(self.challenger.id))
        p2 = pets.get(str(self.target.id))

        p1_pwr = calculate_pet_power(p1)
        p2_pwr = calculate_pet_power(p2)
        p1_name = get_pet_name(p1)
        p2_name = get_pet_name(p2)

        diff = abs(p1_pwr - p2_pwr)
        if p1_pwr == p2_pwr:
            p1_win_rate = 0.50
        elif p1_pwr > p2_pwr:
            if 10 <= diff <= 1000: p1_win_rate = 0.60
            elif 1000 < diff <= 2000: p1_win_rate = 0.70
            elif diff > 2000: p1_win_rate = 1.00
            else: p1_win_rate = 0.50
        else:
            if 10 <= diff <= 1000: p1_win_rate = 0.40
            elif 1000 < diff <= 2000: p1_win_rate = 0.30
            elif diff > 2000: p1_win_rate = 0.00
            else: p1_win_rate = 0.50

        p1_wins = random.random() < p1_win_rate
        reward = random.randint(50, 150)

        embed = discord.Embed(
            title="⚔️ ─── KẾT QUẢ QUYẾT CHIẾN LINH THÚ ─── ⚔️",
            description=f"🔴 **{self.challenger.mention}** [{p1_name}] (Lực chiến: `{p1_pwr}`)\n⚡ **VS** ⚡\n🔵 **{self.target.mention}** [{p2_name}] (Lực chiến: `{p2_pwr}`)",
            color=discord.Color.red()
        )

        if p1_wins:
            add_points(str(self.challenger.id), reward)
            embed.add_field(name="🏆 VIỆT VỊ BẠO CHÚA", value=f"🎉 **{self.challenger.mention}** chiến thắng và nhận **+{reward} điểm**!", inline=False)
        else:
            add_points(str(self.target.id), reward)
            embed.add_field(name="🏆 VIỆT VỊ BẠO CHÚA", value=f"🎉 **{self.target.mention}** chiến thắng và nhận **+{reward} điểm**!", inline=False)

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🏳️ Từ Chối", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"🏳️ {self.target.mention} đã từ chối lời thách đấu!", embed=None, view=None)

@bot.tree.command(name="pvp_pet", description="Thách đấu PvP Linh Thú với người chơi khác!")
async def pvp_pet(interaction: discord.Interaction, target: discord.User):
    if target.id == interaction.user.id:
        await interaction.response.send_message("❌ Bạn không thể tự đấu với chính mình!", ephemeral=True)
        return
    if target.bot:
        await interaction.response.send_message("❌ Không thể thách đấu Bot!", ephemeral=True)
        return

    pets = load_pets()
    if not pets.get(str(interaction.user.id)):
        await interaction.response.send_message("❌ Bạn chưa có Linh Thú!", ephemeral=True)
        return
    if not pets.get(str(target.id)):
        await interaction.response.send_message(f"❌ {target.mention} chưa sở hữu Linh Thú nào!", ephemeral=True)
        return

    embed = discord.Embed(
        title="📜 ─── THƯ THÁCH ĐẤU THẦN THÚ ─── 📜",
        description=f"⚔️ **{interaction.user.mention}** đã gửi lời thách đấu PvP Linh Thú tới **{target.mention}**!\n\n*Nhấn nút bên dưới trong 60s để đồng ý chiến đấu!*",
        color=discord.Color.orange()
    )
    view = PvPInviteView(interaction.user, target)
    await interaction.response.send_message(content=target.mention, embed=embed, view=view)

# ==============================================================================
# --- 9. HỆ THỐNG /DANHBOSS & MODAL THÊM BOSS (ADMIN) ---
# ==============================================================================
class AddBossModal(discord.ui.Modal, title="➕ Thêm Boss Tháp Ma Thần"):
    tang_num = discord.ui.TextInput(label="Tầng Số", placeholder="11", required=True)
    b_name = discord.ui.TextInput(label="Tên Boss", placeholder="🐲 Ma Rồng Đen Thượng Cổ", required=True)
    b_power = discord.ui.TextInput(label="Lực Chiến Boss", placeholder="50000", required=True)
    b_reward = discord.ui.TextInput(label="Điểm Thưởng", placeholder="10000", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Bạn không có quyền Admin!", ephemeral=True)
            return
        try:
            pwr = int(self.b_power.value)
            rew = int(self.b_reward.value)
        except:
            await interaction.response.send_message("❌ Lực chiến và Thưởng phải là số!", ephemeral=True)
            return

        BOSS_TOWER[self.tang_num.value.strip()] = {
            "name": self.b_name.value.strip(),
            "power": pwr,
            "reward": rew
        }
        safe_save_json("boss_tower.json", BOSS_TOWER)
        await interaction.response.send_message(f"✅ Đã thêm Boss **{self.b_name.value}** vào Tầng {self.tang_num.value}!", ephemeral=True)

class BossChallengeView(discord.ui.View):
    def __init__(self, user_id, tang_num):
        super().__init__(timeout=60)
        self.user_id = str(user_id)
        self.tang_num = str(tang_num)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Bảng này không thuộc về bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⚔️ Khiêu Chiến Boss", style=discord.ButtonStyle.danger)
    async def challenge_boss(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_pets()
        p = pets.get(self.user_id)
        if not p or "type" not in p:
            await interaction.response.send_message("❌ Bạn chưa có Pet!", ephemeral=True)
            return

        boss_info = BOSS_TOWER.get(self.tang_num)
        if not boss_info:
            await interaction.response.send_message("❌ Tầng Boss không tồn tại!", ephemeral=True)
            return

        pet_pwr = calculate_pet_power(p)
        pet_name = get_pet_name(p)

        embed = discord.Embed(title=f"🏰 ─── THÁP MA THẦN - TẦNG {self.tang_num} ─── 🏰")
        embed.add_field(name="🐾 Thần Thú", value=f"**{pet_name}** (Lực chiến: `{pet_pwr}`)", inline=False)
        embed.add_field(name="👹 Thủ Vệ", value=f"**{boss_info['name']}** (Lực chiến: `{boss_info['power']:,}`)", inline=False)

        if pet_pwr >= boss_info["power"]:
            new_score = add_points(self.user_id, boss_info["reward"])
            embed.color = discord.Color.green()
            embed.add_field(name="⚔️ CHIẾN TRƯỜNG", value=f"🎉 **CHIẾN THẮNG!** Diệt **{boss_info['name']}**!\n📈 Thưởng: **+{boss_info['reward']:,} điểm** (Tổng: `{new_score}`).", inline=False)
        else:
            embed.color = discord.Color.red()
            embed.add_field(name="⚔️ CHIẾN TRƯỜNG", value=f"💀 **THẤT BẠI!** Lực chiến Linh Thú không đủ đánh bại Boss!", inline=False)

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="➕ Thêm Boss (Admin)", style=discord.ButtonStyle.secondary)
    async def add_boss_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới dùng được nút này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddBossModal())

@bot.tree.command(name="danhboss", description="Đưa Pet đi khiêu chiến Boss Tháp Ma Thần!")
async def danhboss(interaction: discord.Interaction, tang: int):
    view = BossChallengeView(interaction.user.id, tang)
    boss_info = BOSS_TOWER.get(str(tang), {"name": "Boss Bí Uẩn", "power": 1000, "reward": 500})
    embed = discord.Embed(
        title=f"🏰 ─── KHIÊU CHIẾN TẦNG {tang} ─── 🏰",
        description=f"👹 **Thủ Vệ:** {boss_info['name']}\n⚡ **Lực chiến yêu cầu:** `{boss_info['power']:,}`\n🎁 **Phần thưởng:** `{boss_info['reward']:,} điểm`",
        color=discord.Color.dark_red()
    )
    await interaction.response.send_message(embed=embed, view=view)

# ==============================================================================
# --- 10. CÁC LỆNH ĐIỂM, BẢNG XẾP HẠNG & ADMIN QUẢN LÝ MỚI ---
# ==============================================================================
@bot.tree.command(name="cuop", description="Thử vận may đi cướp điểm từ người chơi khác!")
@app_commands.checks.cooldown(1, 60)
async def cuop(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    possible_targets = [uid for uid, score in data.items() if uid != user_id and score.get("weekly", 0) > 0]
    if not possible_targets:
        await interaction.response.send_message("❌ Chưa có nạn nhân phù hợp!", ephemeral=True)
        return

    target_id = random.choice(possible_targets)
    target_user = bot.get_user(int(target_id))
    target_name = target_user.mention if target_user else f"<@{target_id}>"
    target_score = data[target_id]["weekly"]

    if random.random() <= 0.45:
        stolen_pts = random.randint(1, min(1000, target_score))
        my_new_score = add_points(user_id, stolen_pts)
        add_points(target_id, -stolen_pts)
        embed = discord.Embed(
            title="🥷 ─── CƯỚP ĐIỂM THÀNH CÔNG ─── 🥷",
            description=f"Âm thầm đột nhập cướp thành công **+{stolen_pts} điểm** từ {target_name}!\n📈 Điểm mới: `{my_new_score}`",
            color=discord.Color.green()
        )
    else:
        penalty = min(data.get(user_id, {}).get("weekly", 0), random.randint(10, 500))
        if penalty > 0:
            add_points(user_id, -penalty)
            add_points(target_id, penalty)
        embed = discord.Embed(
            title="🚨 ─── BỊ BẮT QUẢ TANG ─── 🚨",
            description=f"Bị quan quân tóm gọn khi định cướp {target_name}! Bị phạt **-{penalty} điểm** bồi thường.",
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="taixiu", description="Đặt cược điểm vào Tài hoặc Xỉu!")
@app_commands.choices(luachon=[app_commands.Choice(name="Tài (11 - 18)", value="tai"), app_commands.Choice(name="Xỉu (3 - 10)", value="xiu")])
async def taixiu(interaction: discord.Interaction, sodiem_cuoc: int, luachon: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    if sodiem_cuoc <= 0:
        await interaction.response.send_message("❌ Số điểm cược phải lớn hơn 0!", ephemeral=True)
        return

    data = load_data()
    current_pts = data.get(user_id, {}).get("weekly", 0)
    if current_pts < sodiem_cuoc:
        await interaction.response.send_message(f"❌ Bạn không đủ điểm cược!", ephemeral=True)
        return

    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    res = "tai" if total >= 11 else "xiu"

    embed = discord.Embed(title="🎲 ─── ĐẮC THẮNG TÀI XỈU ─── 🎲", description=f"🎲 Xúc xắc: **[{d1}] [{d2}] [{d3}]** ➔ Tổng: **{total}** ({res.upper()})")
    if luachon.value == res:
        new_pts = add_points(user_id, sodiem_cuoc)
        embed.color = discord.Color.green()
        embed.add_field(name="🏆 TRẮNG TAY HOẶC ĐẠI PHÚ", value=f"🎉 **THẮNG!** Nhận **+{sodiem_cuoc} điểm** (Tổng: `{new_pts}`).", inline=False)
    else:
        new_pts = add_points(user_id, -sodiem_cuoc)
        embed.color = discord.Color.red()
        embed.add_field(name="🏆 TRẮNG TAY HOẶC ĐẠI PHÚ", value=f"💀 **THUA!** Mất **-{sodiem_cuoc} điểm** (Còn lại: `{new_pts}`).", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bangxephang", description="Xem Bảng xếp hạng Top điểm")
async def bangxephang(interaction: discord.Interaction):
    data = load_data()
    titles = load_titles()
    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:10]

    embed = discord.Embed(
        title="📜 ─── BẢNG PHONG THẦN ĐIỂM TUẦN ─── 📜",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    desc = ""
    for index, (u_id, score) in enumerate(sorted_users, 1):
        user = bot.get_user(int(u_id))
        name = user.mention if user else f"<@{u_id}>"
        icon = "🔹"
        if str(index) in titles:
            icon = f"{titles[str(index)]['icon']} **[{titles[str(index)]['name']}]**"
        desc += f"`#{index}` {icon} {name} — **{score.get('weekly', 0)}** điểm\n"

    embed.description = desc if desc else "Chưa có dữ liệu."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="diem", description="Kiểm tra điểm số và danh hiệu")
async def diem(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    data = load_data()
    u_info = data.get(str(target.id), {"weekly": 0, "total": 0, "titles": []})

    embed = discord.Embed(title=f"📜 ─── HỒ SƠ ANH HÙNG: {target.name.upper()} ─── 📜", color=discord.Color.blue())
    embed.add_field(name="📅 Điểm Tuần", value=f"`{u_info.get('weekly', 0)}` điểm", inline=True)
    embed.add_field(name="🏆 Tích Lũy", value=f"`{u_info.get('total', 0)}` điểm", inline=True)
    titles_list = u_info.get("titles", [])
    embed.add_field(name="🏅 Danh Hiệu", value="\n".join([f"• **[{t}]**" for t in titles_list]) if titles_list else "Chưa có", inline=False)
    await interaction.response.send_message(embed=embed)

# --- ADMIN COMMANDS MỚI BỔ SUNG ---
@bot.tree.command(name="set_top_title", description="Thay đổi Icon và Tên danh hiệu Top trên Bảng Xếp Hạng")
@app_commands.checks.has_permissions(administrator=True)
async def set_top_title(interaction: discord.Interaction, top: int, icon: str, title_name: str):
    titles = load_titles()
    titles[str(top)] = {"icon": icon, "name": title_name}
    save_titles(titles)
    await interaction.response.send_message(f"✅ Đã đổi Top `{top}` thành: {icon} **[{title_name}]**!")

@bot.tree.command(name="point_edit", description="Cộng hoặc trừ điểm tuần của thành viên")
@app_commands.checks.has_permissions(administrator=True)
async def point_edit(interaction: discord.Interaction, user: discord.User, amount: int):
    new_score = add_points(str(user.id), amount)
    await interaction.response.send_message(f"✅ Đã điều chỉnh **{amount} điểm** cho {user.mention}. Điểm tuần mới: `{new_score}`!")

@bot.tree.command(name="add_question", description="Thêm câu hỏi đố vui mẹo mới")
@app_commands.checks.has_permissions(administrator=True)
async def add_question(interaction: discord.Interaction, question: str, answer: str):
    trivia_list = load_trivia()
    ans_list = [a.strip() for a in answer.split(",")]
    trivia_list.append({"q": question, "a": ans_list})
    save_trivia(trivia_list)
    await interaction.response.send_message(f"✅ Đã thêm câu hỏi đố vui mới thành công!")

@bot.tree.command(name="setup_game_channel", description="Cài đặt kênh chính phát Game & Bảng Xếp Hạng")
@app_commands.checks.has_permissions(administrator=True)
async def setup_game_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    cfg = load_config()
    cfg["game_channel_id"] = channel.id
    save_config(cfg)
    await interaction.response.send_message(f"✅ Đã thiết lập kênh {channel.mention}!")

# ==============================================================================
# --- 11. KÍCH HOẠT VÀ CHẠY BOT ---
# ==============================================================================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("[ERROR] Chưa cấu hình DISCORD_TOKEN!")

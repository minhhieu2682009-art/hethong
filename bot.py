from discord.ext import commands, tasks
from discord import app_commands
import discord
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
FISH_CONFIG_FILE = "fish_config.json"
BOSS_CONFIG_FILE = "boss_config.json"
TRIVIA_FILE = "trivia_questions.json"
SHOP_FILE = "fishing_items.json"
PET_SHOP_FILE = "pet_shop_items.json"

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
        "1": {"icon": "👑", "name": "Dạ Minh Tiên Tôn"},
        "2": {"icon": "😈", "name": "U Minh Quỷ Đế"},
        "3": {"icon": "🐢", "name": "Thiên Cơ Đạo Trưởng"}
    }
    return safe_load_json(TITLES_FILE, default_titles)

def save_titles(titles): safe_save_json(TITLES_FILE, titles)

def load_fishing_items():
    default_items = {
        "moi_canh_gio": {"name": "🪽 Mồi cánh gió", "type": "moi", "rarity": "thuong", "price": 100, "succ_bonus": 0.01},
        "moi_sao": {"name": "✨ Mồi sao", "type": "moi", "rarity": "hiem", "price": 200, "succ_bonus": 0.10},
        "moi_sumo": {"name": "🥞 Mồi sumo", "type": "moi", "rarity": "su_thi", "price": 10000, "succ_bonus": 0.12},
        "moi_tien_ca": {"name": "🧜 Mồi nàng tiên cá", "type": "moi", "rarity": "than_thoai", "price": 25000, "succ_bonus": 0.16},
        "can_banh_mi": {"name": "🥖 Cần bánh mì", "type": "can", "rarity": "thuong", "price": 10, "succ_bonus": 0},
        "can_set": {"name": "⚡ Cần sét", "type": "can", "rarity": "hiem", "price": 100, "succ_bonus": 0.01},
        "can_lua": {"name": "🔥 Cần lửa", "type": "can", "rarity": "hiem", "price": 1000, "succ_bonus": 0.03}
    }
    return safe_load_json(SHOP_FILE, default_items)

def save_fishing_items(data): safe_save_json(SHOP_FILE, data)

def load_pet_shop_items():
    default_pet_items = {
        "kiquy": {"name": "🧡 Kí quỷ (+10 EXP)", "price": 10, "type": "exp", "add_exp": 10},
        "ngao_thi": {"name": "🪲 Ngao thị (+200 EXP)", "price": 1000, "type": "exp", "add_exp": 200},
        "thit_long_thu": {"name": "🥩 Thịt long thú (+10,000 EXP)", "price": 10000, "type": "exp", "add_exp": 10000},
        "cam_duong": {"name": "🍎 Cam dương (+20 Pwr/10p)", "price": 300, "type": "power", "buff_power": 20, "duration": 600, "perm": False},
        "nam_ky_lung": {"name": "🍄 Nấm kỳ lung (+100 Pwr/10p)", "price": 1000, "type": "power", "buff_power": 100, "duration": 600, "perm": False},
        "tinh_cau": {"name": "🪐 Tinh cầu (+10 Pwr vĩnh viễn)", "price": 10000, "type": "power", "buff_power": 10, "perm": True}
    }
    return safe_load_json(PET_SHOP_FILE, default_pet_items)

def save_pet_shop_items(data): safe_save_json(PET_SHOP_FILE, data)

def load_fish_table():
    default_fish = [
        {"id": "ro_dong", "name": "🐟 Cá Rô Đồng", "type": "thuong", "pts": 10, "weight": 50},
        {"id": "chep_vang", "name": "🐠 Cá Chép Vàng", "type": "thuong", "pts": 10, "weight": 50},
        {"id": "giay_rach", "name": "👞 Giày Cũ Bị Rách", "type": "xui", "pts": -100, "weight": 40},
        {"id": "ruong_bau", "name": "👑 Rương Báu Dưới Sông", "type": "hiem", "pts": 100, "weight": 40},
        {"id": "voi_sat_than", "name": "🫍 Cá voi sát thần", "type": "than_thoai", "pts": 500, "title": "🛡️ Sát Long", "weight": 1.0}
    ]
    return safe_load_json(FISH_CONFIG_FILE, default_fish)

def save_fish_table(data): safe_save_json(FISH_CONFIG_FILE, data)

def load_boss_tower():
    default_boss = {
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
    return safe_load_json(BOSS_CONFIG_FILE, default_boss)

def save_boss_tower(data): safe_save_json(BOSS_CONFIG_FILE, data)

def load_trivia():
    default_trivia = [
        {"q": "Trong một cuộc thi chạy, nếu bạn vượt qua người đang đứng thứ hai, bạn sẽ đứng thứ mấy?", "a": ["thứ hai", "thứ 2", "2", "thu hai"]},
        {"q": "Bố của Mary có 5 cô con gái: Nana, Nene, Nini, Nono. Hỏi cô con gái thứ 5 tên là gì?", "a": ["mary", "tên là mary", "cô con gái thứ 5 tên là mary"]}
    ]
    return safe_load_json(TRIVIA_FILE, default_trivia)

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
fishing_cooldowns = {}

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
            summary_lines.append(f"🥇 **Top {index+1}:** {member.mention if member else f'<@{u_id}>'} — `{score.get('weekly', 0)} điểm`")
    for u_id in data:
        data[u_id]["weekly"] = 0
    save_data(data)
    return "\n".join(summary_lines) if summary_lines else "Không tìm thấy thành viên Top."

# --- 4. TASKS & EVENTS ---
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
            title="🎯 MINI-GAME ĐỐ VUI HÀNG GIỜ",
            description=f"❓ **Câu hỏi:** {item['q']}\n\n⚡ *Gõ đáp án nhanh trong 45s để nhận ngay **+30 điểm**!*",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed)

        def check(m):
            return m.channel == channel and not m.bot and m.content.strip().lower() in [a.lower() for a in valid_ans]

        try:
            msg = await bot.wait_for('message', timeout=45.0, check=check)
            new_score = add_points(str(msg.author.id), 30)
            await channel.send(f"🎉 Chúc mừng {msg.author.mention} đã trả lời đúng và nhận **+30 điểm** (Điểm tuần: `{new_score}`)!")
        except asyncio.TimeoutError:
            await channel.send(f"⏰ Hết giờ! Đáp án chính xác là: **{valid_ans[0]}**")
    except Exception as e:
        print(f"[WARN] Lỗi minigame: {e}")

@bot.event
async def on_ready():
    print(f"[SYSTEM] Bot đã đăng nhập thành công: {bot.user}")
    if not check_voice_points.is_running(): check_voice_points.start()
    if not auto_minigame_task.is_running(): auto_minigame_task.start()
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
# --- 5. HỆ THỐNG /CAUSONG & ADMIN THÊM CÁ ---
# ==============================================================================

class AddFishModal(discord.ui.Modal, title="➕ Thêm Cá / Quả / Vật Phẩm Xuống Sông"):
    fish_id = discord.ui.TextInput(label="ID Cá (không dấu, vd: ca_map)", placeholder="ca_map")
    fish_name = discord.ui.TextInput(label="Tên hiển thị kèm Emoji", placeholder="🦈 Cá Mập Khổng Lồ")
    fish_type = discord.ui.TextInput(label="Phân loại (thuong/hiem/su_thi/than_thoai/xui)", placeholder="hiem")
    fish_pts = discord.ui.TextInput(label="Số điểm thưởng (+ hoặc -)", placeholder="300")
    fish_weight = discord.ui.TextInput(label="Tỷ lệ xuất hiện (Trọng số)", placeholder="20")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            fish_list = load_fish_table()
            new_fish = {
                "id": self.fish_id.value.strip(),
                "name": self.fish_name.value.strip(),
                "type": self.fish_type.value.strip(),
                "pts": int(self.fish_pts.value.strip()),
                "weight": float(self.fish_weight.value.strip())
            }
            fish_list.append(new_fish)
            save_fish_table(fish_list)
            await interaction.response.send_message(f"✅ Đã thêm thành công loài mới: **{new_fish['name']}** xuống sông!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi cú pháp khi thêm: {e}", ephemeral=True)

class CauSongView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = str(user_id)

    @discord.ui.button(label="Quăng Cần Câu", style=discord.ButtonStyle.primary, emoji="🎣", custom_id="btn_quang_can")
    async def quang_can(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        current_time = time.time()
        
        cooldown_duration = 3.0
        if user_id in fishing_cooldowns:
            elapsed = current_time - fishing_cooldowns[user_id]
            if elapsed < cooldown_duration:
                remaining = round(cooldown_duration - elapsed, 1)
                await interaction.response.send_message(f"⏳ Bạn đang mỏi tay! Vui lòng đợi **{remaining} giây** nữa.", ephemeral=True)
                return
        
        fishing_cooldowns[user_id] = current_time

        user_pets_data = load_pets()
        user_inventory = user_pets_data.get(user_id, {}).get("inventory", {})
        fishing_items = load_fishing_items()
        fish_table = load_fish_table()

        base_success_rate = 0.45
        active_moi = user_inventory.get("active_moi")
        active_can = user_inventory.get("active_can")
        if active_moi and active_moi in fishing_items:
            base_success_rate += fishing_items[active_moi].get("succ_bonus", 0)
        if active_can and active_can in fishing_items:
            base_success_rate += fishing_items[active_can].get("succ_bonus", 0)

        if random.random() > base_success_rate:
            await interaction.response.send_message(f"🎣 **{interaction.user.mention}** quăng cần nhưng cá cắn hụt, tiếc quá!")
            return

        caught = random.choices(fish_table, weights=[f["weight"] for f in fish_table])[0]
        pts = caught["pts"]
        new_score = add_points(user_id, pts)

        msg = f"🎣 **{interaction.user.mention}** giật cần thành công! Bắt được **{caught['name']}**!\n"
        if pts >= 0:
            msg += f"📈 Nhận được **+{pts} điểm** (Điểm tuần: `{new_score}`)."
        else:
            msg += f"📉 Bị phạt **{pts} điểm** (Điểm tuần: `{new_score}`)."

        if "title" in caught:
            add_custom_title(user_id, caught["title"])
            msg += f"\n🎉 Khai quật được danh hiệu: **[{caught['title']}]**!"

        await interaction.response.send_message(msg)

    @discord.ui.button(label="Thêm Cá (Admin)", style=discord.ButtonStyle.danger, emoji="➕", custom_id="btn_them_ca")
    async def them_ca(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ có **Admin** mới được dùng tính năng này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddFishModal())

@bot.tree.command(name="causong", description="Thư giãn đi câu cá bờ sông nhận điểm thưởng!")
async def causong(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌊 KHU VỰC CÂU CÁ GIẢI TRÍ",
        description="Nhấn nút **Quăng Cần Câu** bên dưới để thử vận may câu cá, vật phẩm hoặc rương báu quý hiếm!",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=CauSongView(interaction.user.id))

# ==============================================================================
# --- 6. HỆ THỐNG /SHOP & /NUOITHU (PET & SHOP TÍCH HỢP MUA TRỰC TIẾP) ---
# ==============================================================================

PET_DATABASE = {
    "sutu": {"name": "Sư tử con", "rarity": "thuong", "forms": {1: "🦁 sư tử con", 2: "🐅 vương sư", 3: "⚡🐅 thần hổ sét"}, "exp_caps": {1: 100, 2: 1100, 3: 2000}, "base_pwr": 10, "high_pwr": 100},
    "gau": {"name": "Gấu con", "rarity": "thuong", "forms": {1: "🐻 gấu con", 2: "🦍 gấu mèo", 3: "👺 quỷ gấu"}, "exp_caps": {1: 100, 2: 1200, 3: 1200}, "base_pwr": 10, "high_pwr": 100},
    "rong": {"name": "Rồng con", "rarity": "than_thoai", "forms": {1: "🐉 rồng con", 2: "🐦‍🔥 thần long", 3: "🐲👑 phong long"}, "exp_caps": {1: 2000, 2: 3000, 3: 4000}, "base_pwr": 1000, "high_pwr": 5000}
}

def calculate_pet_power(pet_data):
    if not pet_data or "type" not in pet_data: return 0
    p_type = pet_data["type"]
    if p_type not in PET_DATABASE: return 50
    cfg = PET_DATABASE[p_type]
    lvl = pet_data["level"]
    power = sum(cfg["base_pwr"] if l < 20 else cfg["high_pwr"] for l in range(1, lvl + 1))
    power += pet_data.get("perm_power", 0)
    if pet_data.get("buff_until", 0) > time.time():
        power += pet_data.get("temp_power", 0)
    return power

def get_pet_name(pet_data):
    if not pet_data or "type" not in pet_data: return "Không có Pet"
    p_cfg = PET_DATABASE.get(pet_data["type"], {"forms": {1: "Thú lạ", 2: "Thú chiến", 3: "Thần thú"}})
    return p_cfg["forms"].get(pet_data["level"], p_cfg["forms"][3])

def add_exp_to_pet(pet_data, exp_amount):
    pet_data["exp"] += exp_amount
    p_cfg = PET_DATABASE.get(pet_data["type"], {"exp_caps": {1: 100}})
    while True:
        max_exp = p_cfg["exp_caps"].get(pet_data["level"], 2000)
        if pet_data["exp"] >= max_exp:
            pet_data["level"] += 1
            pet_data["exp"] -= max_exp
        else:
            break

class AddPetModal(discord.ui.Modal, title="➕ Thêm Thú Cưng Mới (Admin)"):
    pet_key = discord.ui.TextInput(label="Mã định danh (vd: phuonghoang)", placeholder="phuonghoang")
    pet_name = discord.ui.TextInput(label="Tên Thú Cưng", placeholder="Phượng Hoàng Lửa")
    rarity = discord.ui.TextInput(label="Độ hiếm", placeholder="than_thoai")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Đã thêm dòng Pet `{self.pet_key.value}` thành công!", ephemeral=True)

class AddShopItemModal(discord.ui.Modal, title="➕ Thêm Vật Phẩm Vào Shop"):
    item_id = discord.ui.TextInput(label="Mã vật phẩm", placeholder="qua_tao_vang")
    item_name = discord.ui.TextInput(label="Tên kèm Emoji", placeholder="🍎 Quả táo thần")
    item_price = discord.ui.TextInput(label="Giá điểm mua", placeholder="500")
    item_type = discord.ui.TextInput(label="Loại (moi / can / exp / power)", placeholder="power")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pet_items = load_pet_shop_items()
            pet_items[self.item_id.value.strip()] = {
                "name": self.item_name.value.strip(),
                "price": int(self.item_price.value.strip()),
                "type": self.item_type.value.strip(),
                "buff_power": 50,
                "add_exp": 500
            }
            save_pet_shop_items(pet_items)
            await interaction.response.send_message(f"✅ Đã thêm vật phẩm **{self.item_name.value}** vào shop!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

class ShopSelect(discord.ui.Select):
    def __init__(self, items_dict, category):
        self.category = category
        options = []
        for k, v in items_dict.items():
            options.append(discord.SelectOption(label=v['name'][:100], value=k, description=f"Giá: {v['price']} điểm"[:100]))
        super().__init__(placeholder="👇 Chọn món hàng bạn muốn mua ngay...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        selected_item_id = self.values[0]
        
        fishing_items = load_fishing_items()
        pet_items = load_pet_shop_items()
        
        item_data = fishing_items.get(selected_item_id) if self.category == "fishing" else pet_items.get(selected_item_id)
        if not item_data:
            await interaction.response.send_message("❌ Vật phẩm không tồn tại!", ephemeral=True)
            return
            
        price = item_data["price"]
        user_data = load_data()
        user_points = user_data.get(user_id, {}).get("weekly", 0)
        
        if user_points < price:
            await interaction.response.send_message(f"❌ Không đủ điểm! Cần `{price} điểm`, bạn có `{user_points} điểm` tuần.", ephemeral=True)
            return
            
        add_points(user_id, -price)
        
        pets_data = load_pets()
        if user_id not in pets_data:
            pets_data[user_id] = {"type": None, "level": 1, "exp": 0, "perm_power": 0, "temp_power": 0, "buff_until": 0, "inventory": {}}
        if "inventory" not in pets_data[user_id]:
            pets_data[user_id]["inventory"] = {}
            
        user_inv = pets_data[user_id]["inventory"]
        if self.category == "fishing":
            if item_data.get("type") == "moi": user_inv["active_moi"] = selected_item_id
            elif item_data.get("type") == "can": user_inv["active_can"] = selected_item_id
        else:
            if item_data.get("type") == "exp":
                p = pets_data[user_id]
                if p.get("type"): add_exp_to_pet(p, item_data.get("add_exp", 0))
            elif item_data.get("type") == "power":
                p = pets_data[user_id]
                if item_data.get("perm", False):
                    p["perm_power"] = p.get("perm_power", 0) + item_data.get("buff_power", 0)
                else:
                    p["temp_power"] = item_data.get("buff_power", 0)
                    p["buff_until"] = time.time() + item_data.get("duration", 600)
                    
        save_pets(pets_data)
        await interaction.response.send_message(f"🎉 Mua thành công **{item_data['name']}** với giá `{price} điểm`!", ephemeral=True)

class ShopCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cửa Hàng Câu Cá", style=discord.ButtonStyle.primary, emoji="🎣", custom_id="shop_fishing")
    async def shop_fishing(self, interaction: discord.Interaction, button: discord.ui.Button):
        fishing_items = load_fishing_items()
        desc = "🛍️ **CẦN & MỒI CÂU:**\n"
        for k, v in fishing_items.items():
            desc += f"• **{v['name']}** — `{v['price']} điểm`\n"
        embed = discord.Embed(title="🛒 SHOP CÂU CÁ", description=desc, color=discord.Color.green())
        
        view = discord.ui.View(timeout=None)
        view.add_item(ShopSelect(fishing_items, "fishing"))
        for child in self.children: view.add_item(child)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cửa Hàng Thú Cưng", style=discord.ButtonStyle.success, emoji="🍎", custom_id="shop_pet")
    async def shop_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pet_items = load_pet_shop_items()
        desc = "🛍️ **THỨC ĂN & VẬT PHẨM PET:**\n"
        for k, v in pet_items.items():
            desc += f"• **{v['name']}** — `{v['price']} điểm`\n"
        embed = discord.Embed(title="🛒 SHOP THÚ CƯNG", description=desc, color=discord.Color.purple())
        
        view = discord.ui.View(timeout=None)
        view.add_item(ShopSelect(pet_items, "pet"))
        for child in self.children: view.add_item(child)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="➕ Thêm Item (Admin)", style=discord.ButtonStyle.danger, emoji="⚙️", custom_id="shop_admin_add")
    async def shop_admin_add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới được dùng!", ephemeral=True)
            return
        await interaction.response.send_modal(AddShopItemModal())

@bot.tree.command(name="shop", description="Mở cửa hàng tổng hợp mua sắm trực tiếp")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏬 TRUNG TÂM MUA SẮM (SHOP)",
        description="Chào mừng bạn! Chọn danh mục bên dưới và dùng menu thả xuống để mua ngay.",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=ShopCategoryView())

class PetMainView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = str(user_id)

    @discord.ui.button(label="Mở Trứng Pet (100đ)", style=discord.ButtonStyle.success, emoji="🥚")
    async def open_egg(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        if data.get(self.user_id, {}).get("weekly", 0) < 100:
            await interaction.response.send_message("❌ Cần tối thiểu 100 điểm tuần để mở trứng!", ephemeral=True)
            return
        add_points(self.user_id, -100)
        pet_choice = random.choice(list(PET_DATABASE.keys()))
        pets = load_pets()
        pets[self.user_id] = {"type": pet_choice, "level": 1, "exp": 0, "perm_power": 0, "temp_power": 0, "buff_until": 0}
        save_pets(pets)
        await interaction.response.send_message(f"🎉 Mở trứng thành công! Nhận được **{PET_DATABASE[pet_choice]['name']}**!", ephemeral=True)

    @discord.ui.button(label="Cho Pet Ăn (+100 EXP)", style=discord.ButtonStyle.primary, emoji="🍖")
    async def feed_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_pets()
        p = pets.get(self.user_id)
        if not p:
            await interaction.response.send_message("❌ Bạn chưa có Pet!", ephemeral=True)
            return
        add_exp_to_pet(p, 100)
        save_pets(pets)
        await interaction.response.send_message(f"🍖 Cho Pet ăn thành công! Cấp độ: `{p['level']}`, EXP: `{p['exp']}`", ephemeral=True)

    @discord.ui.button(label="Thêm Pet (Admin)", style=discord.ButtonStyle.danger, emoji="🛠️")
    async def add_pet_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới được dùng!", ephemeral=True)
            return
        await interaction.response.send_modal(AddPetModal())

@bot.tree.command(name="nuoithu", description="Giao diện quản lý Thú Cưng Ảo cá nhân")
async def nuoithu(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pets = load_pets()
    p = pets.get(user_id)
    if not p:
        embed = discord.Embed(title="🥚 NUÔI THÚ ẢO", description="Bạn chưa sở hữu thú cưng. Nhấn nút bên dưới để mở trứng!", color=discord.Color.gold())
    else:
        name = get_pet_name(p)
        pwr = calculate_pet_power(p)
        embed = discord.Embed(title=f"🐾 THÚ CƯNG: {name}", description=f"⭐ Level: `{p['level']}`\n⚡ Lực chiến: `{pwr}`\n📈 EXP: `{p['exp']}`", color=discord.Color.purple())
    await interaction.response.send_message(embed=embed, view=PetMainView(user_id))

# ==============================================================================
# --- 7. PVP PET & ĐÁNH BOSS ---
# ==============================================================================

class PvPConfirmView(discord.ui.View):
    def __init__(self, challenger_id, target_id):
        super().__init__(timeout=60)
        self.challenger_id = challenger_id
        self.target_id = target_id
        self.value = None

    @discord.ui.button(label="Đồng Ý", style=discord.ButtonStyle.green, emoji="⚔️")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.target_id:
            await interaction.response.send_message("❌ Lời mời không dành cho bạn!", ephemeral=True)
            return
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Từ Chối", style=discord.ButtonStyle.red, emoji="🚫")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.target_id:
            await interaction.response.send_message("❌ Lời mời không dành cho bạn!", ephemeral=True)
            return
        self.value = False
        self.stop()
        await interaction.message.edit(content="❌ Trận đấu PvP đã bị từ chối.", view=None)

@bot.tree.command(name="pvp_pet", description="Thách đấu PvP Thú cưng với người chơi khác")
async def pvp_pet(interaction: discord.Interaction, target: discord.Member):
    user_id = str(interaction.user.id)
    target_id = str(target.id)

    if target_id == user_id or target.bot:
        await interaction.response.send_message("❌ Không thể thách đấu chính mình hoặc Bot!", ephemeral=True)
        return

    pets = load_pets()
    p1, p2 = pets.get(user_id), pets.get(target_id)
    if not p1 or not p2:
        await interaction.response.send_message("❌ Cả hai người chơi đều phải có Thú Cưng!", ephemeral=True)
        return

    view = PvPConfirmView(user_id, target_id)
    await interaction.response.send_message(f"⚔️ {target.mention}, bạn nhận được lời thách đấu PvP từ {interaction.user.mention}. Bạn có đồng ý không?", view=view)
    
    await view.wait()
    if view.value is None:
        await interaction.edit_original_response(content="⏰ Đã quá thời gian chờ phản hồi.", view=None)
        return
    if not view.value:
        return

    p1_pwr = calculate_pet_power(p1)
    p2_pwr = calculate_pet_power(p2)
    reward = random.randint(50, 150)

    if p1_pwr == p2_pwr: win_p1 = random.choice([True, False])
    elif p1_pwr > p2_pwr: win_p1 = random.random() < 0.60
    else: win_p1 = random.random() < 0.40

    embed = discord.Embed(title="🔥 KẾT QUẢ TRẬN ĐẤU PVP PET", color=discord.Color.red())
    if win_p1:
        add_points(user_id, reward)
        embed.description = f"🎉 **{interaction.user.mention}** đã chiến thắng và nhận **+{reward} điểm**!"
    else:
        add_points(target_id, reward)
        embed.description = f"🎉 **{target.mention}** đã phản công chiến thắng và nhận **+{reward} điểm**!"

    await interaction.edit_original_response(content=None, embed=embed, view=None)

class AddBossModal(discord.ui.Modal, title="➕ Thêm Boss Mới Vào Tháp (Admin)"):
    boss_floor = discord.ui.TextInput(label="Số Tầng Boss", placeholder="11")
    boss_name = discord.ui.TextInput(label="Tên Boss kèm Emoji", placeholder="💀 Trùm Cuối")
    boss_power = discord.ui.TextInput(label="Lực chiến yêu cầu", placeholder="5000000")
    boss_reward = discord.ui.TextInput(label="Điểm thưởng thắng", placeholder="10000")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            boss_tower = load_boss_tower()
            boss_tower[self.boss_floor.value.strip()] = {
                "name": self.boss_name.value.strip(),
                "power": int(self.boss_power.value.strip()),
                "reward": int(self.boss_reward.value.strip())
            }
            save_boss_tower(boss_tower)
            await interaction.response.send_message(f"✅ Đã thêm Boss tầng `{self.boss_floor.value}` thành công!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

class BossView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = str(user_id)

    @discord.ui.button(label="Khiêu Chiến Boss Tháp ⚔️", style=discord.ButtonStyle.danger)
    async def fight_boss(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_pets()
        p = pets.get(self.user_id)
        if not p:
            await interaction.response.send_message("❌ Bạn cần có Pet để khiêu chiến tháp Boss!", ephemeral=True)
            return
            
        pwr = calculate_pet_power(p)
        boss_tower = load_boss_tower()
        
        # Chọn ngẫu nhiên hoặc tính theo tầng cơ bản
        floor_key = random.choice(list(boss_tower.keys()))
        boss = boss_tower[floor_key]
        
        if pwr >= boss["power"]:
            reward = boss["reward"]
            add_points(self.user_id, reward)
            await interaction.response.send_message(f"🎉 **CHIẾN THẮNG!** Pet của bạn đã hạ gục **{boss['name']}** (Tầng {floor_key}) và nhận thưởng **+{reward} điểm**!")
        else:
            await interaction.response.send_message(f"💀 **THẤT BẠI!** Lực chiến Pet của bạn (`{pwr}`) quá yếu so với **{boss['name']}** (Yêu cầu: `{boss['power']}`). Hãy luyện tập thêm!")

    @discord.ui.button(label="Thêm Boss Mới (Admin) ➕", style=discord.ButtonStyle.secondary)
    async def add_boss_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ Admin mới được dùng!", ephemeral=True)
            return
        await interaction.response.send_modal(AddBossModal())

@bot.tree.command(name="boss", description="Khiêu chiến tháp Boss bằng Thú cưng")
async def boss(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏰 THÁP BOSS THẦN THÚ",
        description="Thách thức các thế lực hắc ám để mang về phần thưởng điểm số khổng lồ!",
        color=discord.Color.dark_red()
    )
    await interaction.response.send_message(embed=embed, view=BossView(interaction.user.id))

# --- KHỞI CHẠY BOT ---
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("[ERROR] Không tìm thấy biến môi trường DISCORD_TOKEN!")

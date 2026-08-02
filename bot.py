import os
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import random
import asyncio
from datetime import datetime, time, timedelta

# ==========================================
# 1. KHỞI TẠO BOT & DATABASE
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Bảng người dùng
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        points INTEGER DEFAULT 500,
        titles TEXT DEFAULT ''
    )''')
    
    # Bảng thú cưng người chơi
    c.execute('''CREATE TABLE IF NOT EXISTS user_pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pet_type TEXT,
        pet_name TEXT,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 0
    )''')

    # Bảng cấu hình Pet hệ thống (Admin có thể update)
    c.execute('''CREATE TABLE IF NOT EXISTS pet_config (
        pet_type TEXT PRIMARY KEY,
        display_name TEXT,
        rarity TEXT,
        rate REAL
    )''')

    # Bảng Boss Tháp
    c.execute('''CREATE TABLE IF NOT EXISTS tower_bosses (
        floor INTEGER PRIMARY KEY,
        name TEXT,
        cp INTEGER,
        reward_points INTEGER,
        reward_exp INTEGER,
        dmg_reduction REAL,
        req_rarity TEXT,
        title_reward TEXT
    )''')

    # Bảng Cá
    c.execute('''CREATE TABLE IF NOT EXISTS fishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        rarity TEXT,
        rate REAL,
        points INTEGER,
        title TEXT
    )''')

    # Bảng Cửa hàng (Shop)
    c.execute('''CREATE TABLE IF NOT EXISTS shop_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        name TEXT,
        price INTEGER,
        description TEXT,
        effect_type TEXT,
        effect_value REAL
    )''')

    # Bảng Túi đồ người chơi
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_name TEXT,
        quantity INTEGER DEFAULT 1,
        is_equipped INTEGER DEFAULT 0
    )''')

    # Bảng cấu hình Bảng xếp hạng
    c.execute('''CREATE TABLE IF NOT EXISTS lb_config (
        id INTEGER PRIMARY KEY,
        top1_title TEXT DEFAULT 'khư quỷ',
        top1_color TEXT DEFAULT '🥇',
        top2_title TEXT DEFAULT 'khu la',
        top2_color TEXT DEFAULT '🥈',
        top3_title TEXT DEFAULT 'thế thần',
        top3_color TEXT DEFAULT '🥉',
        target_channel_id INTEGER DEFAULT 0
    )''')
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. HÀM BỔ TRỢ DATABASE & TÍNH TOÁN PET
# ==========================================
def get_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT points, titles FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, points) VALUES (?, 500)", (user_id,))
        conn.commit()
        conn.close()
        return {"points": 500, "titles": ""}
    conn.close()
    return {"points": row[0], "titles": row[1]}

def update_points(user_id: int, amount: int):
    get_user(user_id)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# Cấu hình dữ liệu tiến hóa mặc định của 9 loại Pet
PET_EVOLUTION_DATA = {
    "sutu": {
        "base_name": "Sư tử con", "rarity": "thường", "base_rate": 70.0,
        "stages": [(1, 100, "🦁 Sư tử con"), (2, 1000, "🐯 Vua hổ"), (3, 2000, "⚡🐅 Sấm chị lâm")],
        "cp_base": 50, "cp_high": 100
    },
    "gau": {
        "base_name": "Gấu con", "rarity": "thường", "base_rate": 70.0,
        "stages": [(1, 100, "🐻 Gấu con"), (2, 1000, "🐻🙈 Gấu béo"), (3, 2000, "🐻⭐ Thần gấu phương nam")],
        "cp_base": 60, "cp_high": 110
    },
    "gautruc": {
        "base_name": "Gấu trúc con", "rarity": "hiếm", "base_rate": 50.0,
        "stages": [(1, 200, "🐼 Gấu trúc con"), (2, 2000, "🐼👑 Vua gấu"), (3, 3000, "🐼&🌛 Thái cực thiên tôn")],
        "cp_base": 100, "cp_high": 150
    },
    "camap": {
        "base_name": "Cá mập con", "rarity": "hiếm", "base_rate": 50.0,
        "stages": [(1, 300, "🦈 Cá mập con"), (2, 3000, "🦈😶 Thần tử"), (3, 4000, "🐋 Tinh kình")],
        "cp_base": 150, "cp_high": 200
    },
    "daibang": {
        "base_name": "Đại bàng trắng con", "rarity": "sử thi", "base_rate": 20.0,
        "stages": [(1, 500, "🦅 Đại bàng trắng con"), (2, 5000, "⚡🦅 Xấm đại cửu u"), (3, 10000, "🦅🔥 Tiểu thần quân")],
        "cp_base": 500, "cp_high": 1000
    },
    "kilan": {
        "base_name": "Kì lân con", "rarity": "sử thi", "base_rate": 10.0,
        "stages": [(1, 600, "🦄 Kì lân con"), (2, 6000, "🦄🙈 Bạch thú chi vương"), (3, 8000, "🦄🔥 Hoả Lâm Chân Nhân")],
        "cp_base": 600, "cp_high": 1500
    },
    "rong": {
        "base_name": "Rồng con", "rarity": "thần thoại", "base_rate": 1.0,
        "stages": [(1, 1000, "🐉 Pet rồng con"), (2, 5000, "🐉🦅 Ứng long chân nhân"), (3, 20000, "🐲 Chí tôn long hoàng")],
        "cp_base": 5000, "cp_high": 10000
    },
    "phuonghoang": {
        "base_name": "Phượng hoàng con", "rarity": "thần thoại", "base_rate": 1.0,
        "stages": [(1, 2000, "🐦‍🔥 Phượng hoàng con"), (2, 7000, "🐦‍🔥🌋 Niết bàn vĩnh hằng"), (3, 25000, "🐦‍🔥🩸 Thái dương thần điểu")],
        "cp_base": 7000, "cp_high": 12000
    },
    "diathien": {
        "base_name": "Địa thiên cực bắc đại đế", "rarity": "hư vọng", "base_rate": 0.1,
        "stages": [(1, 10000, "🌏 Địa thiên cực bắc đại đế"), (2, 40000, "🌌🌑 Tử vi tinh đại đế"), (3, 80000, "🌌🪐 Hư không cổ Hoàng")],
        "cp_base": 10000, "cp_high": 30000
    }
}

def get_next_exp_req(pet_type: str, level: int) -> int:
    data = PET_EVOLUTION_DATA.get(pet_type)
    if not data:
        return 1000
    if level == 1:
        return data["stages"][0][1]
    elif level == 2:
        return data["stages"][1][1]
    elif level == 3:
        return data["stages"][2][1]
    else:
        # Công thức: EXP cấp trước / 2 * cấp tiếp theo
        prev = get_next_exp_req(pet_type, level - 1)
        return int((prev / 2) * level)

def get_pet_info_display(pet_type: str, level: int):
    data = PET_EVOLUTION_DATA.get(pet_type)
    if not data:
        return "Linh Thú Khái Niệm", "thường"
    if level == 1:
        name = data["stages"][0][2]
    elif level == 2:
        name = data["stages"][1][2]
    elif level >= 3:
        name = data["stages"][2][2]
    return name, data["rarity"]

def calculate_pet_cp(pet_type: str, level: int) -> int:
    data = PET_EVOLUTION_DATA.get(pet_type)
    if not data:
        return level * 50
    cp = 0
    for l in range(1, level + 1):
        if l < 20:
            cp += data["cp_base"]
        else:
            cp += data["cp_high"]
    return cp

# ==========================================
# 3. HỆ THỐNG /nuoithu UI & LOGIC (MỞ RỘNG)
# ==========================================

class AdminUpdatePetModal(discord.ui.Modal, title="Cập Nhật Thông Tin Pet (Admin)"):
    pet_name = discord.ui.TextInput(label="Tên Pet (Bắt buộc)", placeholder="Ví dụ: Sư tử con", required=True)
    rarity = discord.ui.TextInput(label="Phẩm chất (Bắt buộc)", placeholder="thường/hiếm/sử thi/thần thoại/hư vọng", required=True)
    rate = discord.ui.TextInput(label="Tỉ lệ ra (%) (Bắt buộc)", placeholder="Ví dụ: 70.0", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Bạn không có quyền Admin!", ephemeral=True)
        try:
            r_val = float(self.rate.value)
        except ValueError:
            return await interaction.response.send_message("❌ Tỉ lệ phải là một số!", ephemeral=True)
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO pet_config (pet_type, display_name, rarity, rate) VALUES (?, ?, ?, ?)",
                  (self.pet_name.value.lower(), self.pet_name.value, self.rarity.value.lower(), r_val))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Cập Nhật Pet Thành Công!",
            description=f"**Tên:** {self.pet_name.value}\n**Phẩm chất:** {self.rarity.value}\n**Tỉ lệ mới:** {r_val}%",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Menu chọn Pet đồng hành
class SelectActivePetDropdown(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, pet_type, level FROM user_pets WHERE user_id = ?", (user_id,))
        pets = c.fetchall()
        conn.close()

        options = []
        for p in pets:
            p_id, p_type, p_lvl = p
            display_name, _ = get_pet_info_display(p_type, p_lvl)
            options.append(discord.SelectOption(label=f"{display_name} (Lv.{p_lvl})", value=str(p_id)))
        
        if not options:
            options.append(discord.SelectOption(label="Bạn chưa có thú nuôi nào", value="none"))

        super().__init__(placeholder="⚔️ Chọn linh thú xuất trận...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("❌ Bạn chưa có linh thú nào để chọn!", ephemeral=True)
        
        pet_id = int(self.values[0])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Đưa tất cả pet về 0, rồi set pet được chọn lên 1
        c.execute("UPDATE user_pets SET is_active = 0 WHERE user_id = ?", (self.user_id,))
        c.execute("UPDATE user_pets SET is_active = 1 WHERE id = ? AND user_id = ?", (pet_id, self.user_id))
        conn.commit()
        conn.close()

        await interaction.response.send_message("🛡️ Đã thay đổi linh thú đồng hành thành công! Sẵn sàng chinh phục tháp.", ephemeral=True)

class SelectActivePetView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.add_item(SelectActivePetDropdown(user_id))

# Menu chọn đồ ăn cho pet từ túi đồ
class FeedPetDropdown(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Lấy các vật phẩm là thức ăn/trang bị pet trong túi
        c.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ? AND (item_name LIKE '%Đào%' OR item_name LIKE '%Hoa%' OR item_name LIKE '%Thịt%' OR item_name LIKE '%Nấm%' OR item_name LIKE '%quả%' OR item_name LIKE '%kiếm%')", (user_id,))
        items = c.fetchall()
        conn.close()

        options = [discord.SelectOption(label=f"{i[0]} (x{i[1]})", value=i[0]) for i in items[:25]]
        if not options:
            options.append(discord.SelectOption(label="Túi không có thức ăn/đồ pet", value="none"))

        super().__init__(placeholder="🍖 Chọn thức ăn/bảo vật trong túi để bồi bổ...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("❌ Không tìm thấy thức ăn hoặc bảo vật cho pet trong túi đồ!", ephemeral=True)
        
        item_name = self.values[0]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Trừ 1 số lượng item trong túi
        c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (self.user_id, item_name))
        c.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ? AND quantity <= 0", (self.user_id, item_name))
        
        # Tìm pet đang đồng hành để cộng EXP
        c.execute("SELECT id, level FROM user_pets WHERE user_id = ? AND is_active = 1", (self.user_id,))
        active_pet = c.fetchone()
        
        if active_pet:
            pet_id = active_pet[0]
            c.execute("UPDATE user_pets SET exp = exp + 150 WHERE id = ?", (pet_id,))
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"✨ Đã sử dụng **{item_name}** cho linh thú đang xuất trận, nhận thêm `150 EXP`!", ephemeral=True)
        else:
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"⚠️ Bạn đã tiêu thụ **{item_name}**, nhưng chưa chọn linh thú xuất trận nên không nhận được EXP!", ephemeral=True)

class FeedPetView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.add_item(FeedPetDropdown(user_id))

class PetMainView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="🎲 Quay Pet (100 Điểm)", style=discord.ButtonStyle.primary, custom_id="btn_gacha_pet")
    async def spin_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Bảng này không phải của bạn!", ephemeral=True)
        
        u_data = get_user(self.user_id)
        if u_data["points"] < 100:
            return await interaction.response.send_message("❌ Bạn không đủ 100 điểm để quay Pet!", ephemeral=True)
        
        update_points(self.user_id, -100)

        rolled_pets = []
        for key, pdata in PET_EVOLUTION_DATA.items():
            chance = random.uniform(0, 100)
            if chance <= pdata["base_rate"]:
                rolled_pets.append(key)
        
        if not rolled_pets:
            rolled_pets = ["sutu", "gau"]

        chosen_key = random.choice(rolled_pets)
        pdata = PET_EVOLUTION_DATA[chosen_key]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO user_pets (user_id, pet_type, pet_name, level, exp, is_active) VALUES (?, ?, ?, 1, 0, 0)",
                  (self.user_id, chosen_key, pdata["base_name"]))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="🎉 TRÚNG LINH THÚ MỚI!",
            description=f"Bạn đã chi **100 Điểm** và chiêu mộ thành công:\n\n### {pdata['stages'][0][2]}\n* **Phẩm chất:** {pdata['rarity'].upper()}\n* **Lực chiến ban đầu:** +{pdata['cp_base']} CP",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚔️ Chọn Xuất Trận", style=discord.ButtonStyle.success, custom_id="btn_select_active_pet")
    async def select_active_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Bảng này không phải của bạn!", ephemeral=True)
        await interaction.response.send_message("👇 Chọn linh thú bạn muốn đưa ra chiến đấu:", view=SelectActivePetView(self.user_id), ephemeral=True)

    @discord.ui.button(label="🍖 Cho Pet Ăn", style=discord.ButtonStyle.secondary, custom_id="btn_feed_pet")
    async def feed_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Bảng này không phải của bạn!", ephemeral=True)
        await interaction.response.send_message("👇 Chọn thức ăn trong túi để bồi bổ cho linh thú xuất trận:", view=FeedPetView(self.user_id), ephemeral=True)

    @discord.ui.button(label="⚙️ Update Pet (Admin)", style=discord.ButtonStyle.danger, custom_id="btn_admin_update_pet")
    async def update_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Chỉ Quản trị viên mới dùng được nút này!", ephemeral=True)
        await interaction.response.send_modal(AdminUpdatePetModal())

@bot.tree.command(name="nuoithu", description="Mở Bảng Nuôi Thú Ảo & Chiêu Mộ Linh Thú")
async def nuoithu(interaction: discord.Interaction):
    user_id = interaction.user.id
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, pet_type, pet_name, level, exp, is_active FROM user_pets WHERE user_id = ?", (user_id,))
    user_pets = c.fetchall()
    conn.close()

    embed = discord.Embed(
        title="🐾 BẢNG QUẢN LÝ & NUÔI THÚ ẢO",
        description="Chào mừng bạn đến với Linh Thú Điện! Chiêu mộ linh thú, chọn pet xuất trận để tăng Lực Chiến (CP) chuẩn bị đi chinh phục Tháp Boss (`/leothap`).",
        color=discord.Color.purple()
    )

    if user_pets:
        pet_list_str = ""
        for p in user_pets:
            p_id, p_type, p_name, p_lvl, p_exp, is_act = p
            display_name, rarity = get_pet_info_display(p_type, p_lvl)
            next_exp = get_next_exp_req(p_type, p_lvl)
            cp = calculate_pet_cp(p_type, p_lvl)
            active_badge = " 🟢 [ĐANG XUẤT TRẬN]" if is_act == 1 else ""
            pet_list_str += f"• **{display_name}** (Lv.{p_lvl}){active_badge}\n  └ Phẩm chất: **{rarity.upper()}** | EXP: `{p_exp}/{next_exp}` | CP: **+{cp}**\n"
        embed.add_field(name="📜 Linh Thú Đang Sở Hữu:", value=pet_list_str[:1024], inline=False)
    else:
        embed.add_field(name="📜 Linh Thú Đang Sở Hữu:", value="*Bạn chưa sở hữu Linh thú nào. Hãy thử vận may bằng cách bấm Quay Pet!*", inline=False)

    view = PetMainView(user_id=user_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==========================================
# 4. TÍCH ĐIỂM CHAT & VOICE TỰ ĐỘNG
# ==========================================
voice_time_tracker = {}

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # Cộng 2 điểm ngẫu nhiên mỗi khi chat
    update_points(message.author.id, 2)
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return
    
    # Vào voice chat
    if before.channel is None and after.channel is not None:
        voice_time_tracker[member.id] = datetime.now()
    # Rời voice chat
    elif before.channel is not None and after.channel is None:
        join_time = voice_time_tracker.pop(member.id, None)
        if join_time:
            duration = (datetime.now() - join_time).total_seconds()
            # Mỗi 1 phút voice cộng 5 điểm
            earned_points = int((duration // 60) * 5)
            if earned_points > 0:
                update_points(member.id, earned_points)

# ==========================================
# 5. HỆ THỐNG /pvp_pet (THÁCH ĐẤU LINH THÚ)
# ==========================================

class PVPChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, challenger_pet: tuple, opponent_pet: tuple):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.challenger_pet = challenger_pet  # (id, pet_type, level, exp)
        self.opponent_pet = opponent_pet

    @discord.ui.button(label="⚔️ Chấp Nhận Thách Đấu", style=discord.ButtonStyle.success, custom_id="btn_accept_pvp")
    async def accept_pvp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            return await interaction.response.send_message("❌ Bạn không phải người được thách đấu!", ephemeral=True)

        # Tính Lực chiến (CP) của 2 bên
        cp1 = calculate_pet_cp(self.challenger_pet[1], self.challenger_pet[2])
        cp2 = calculate_pet_cp(self.opponent_pet[1], self.opponent_pet[2])

        # Kiểm tra buff từ trang bị trong túi đồ (Chi dục: +50% tỷ lệ thắng)
        def get_pvp_buff(user_id):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = 'Chi dục' AND is_equipped = 1", (user_id,))
            row = c.fetchone()
            conn.close()
            return 0.5 if row and row[0] > 0 else 0.0

        buff1 = get_pvp_buff(self.challenger.id)
        buff2 = get_pvp_buff(self.opponent.id)

        # Tính toán tỷ lệ thắng cơ bản dựa theo khoảng cách Lực chiến
        diff = abs(cp1 - cp2)
        if cp1 == cp2:
            win_rate1 = 0.50
        elif cp1 > cp2:
            if diff <= 3000:
                win_rate1 = 0.60
            elif diff <= 10000:
                win_rate1 = 0.70
            else:
                win_rate1 = 1.00
        else:
            if diff <= 3000:
                win_rate1 = 0.40
            elif diff <= 10000:
                win_rate1 = 0.30
            else:
                win_rate1 = 0.00

        # Áp dụng buff trang bị
        win_rate1 = min(1.00, max(0.00, win_rate1 + buff1 - buff2))

        # Quyết định kết quả
        roll = random.random()
        p1_name, _ = get_pet_info_display(self.challenger_pet[1], self.challenger_pet[2])
        p2_name, _ = get_pet_info_display(self.opponent_pet[1], self.opponent_pet[2])

        if roll <= win_rate1:
            winner = self.challenger
            loser = self.opponent
            win_pet_name = p1_name
            lose_pet_name = p2_name
        else:
            winner = self.opponent
            loser = self.challenger
            win_pet_name = p2_name
            lose_pet_name = p1_name

        # Thưởng 100 điểm cho người thắng
        update_points(winner.id, 100)

        embed = discord.Embed(
            title="⚔️ KẾT QUẢ QUYẾT ĐẤU LINH THÚ ⚔️",
            description=f"**{self.challenger.display_name}** ({p1_name} - {cp1} CP) \n🆚\n **{self.opponent.display_name}** ({p2_name} - {cp2} CP)",
            color=discord.Color.red()
        )
        embed.add_field(name="🏆 Đơn Vị Chiến Thắng", value=f"**{winner.mention}** cùng Linh Thú **{win_pet_name}** đã đánh bại **{lose_pet_name}** của {loser.mention}!", inline=False)
        embed.add_field(name="🎁 Phần Thưởng", value="+100 Điểm vào tài khoản người thắng!", inline=False)

        self.stop()
        await interaction.response.edit_message(content=None, embed=embed, view=None)

    @discord.ui.button(label="🏳️ Từ Chối", style=discord.ButtonStyle.danger, custom_id="btn_deny_pvp")
    async def deny_pvp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            return await interaction.response.send_message("❌ Bạn không phải người được thách đấu!", ephemeral=True)
        self.stop()
        await interaction.response.edit_message(content=f"❌ {self.opponent.mention} đã từ chối lời mời PvP!", embed=None, view=None)

@bot.tree.command(name="pvp_pet", description="Thách đấu Linh thú với người chơi khác")
@app_commands.describe(target="Người chơi bạn muốn thách đấu")
async def pvp_pet(interaction: discord.Interaction, target: discord.Member):
    if target.bot or target.id == interaction.user.id:
        return await interaction.response.send_message("❌ Đối thủ không hợp lệ!", ephemeral=True)

    def get_active_pet(uid):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, pet_type, level, exp FROM user_pets WHERE user_id = ? AND is_active = 1", (uid,))
        pet = c.fetchone()
        if not pet:
            # Nếu chưa chọn pet active thì tự lấy pet đầu tiên
            c.execute("SELECT id, pet_type, level, exp FROM user_pets WHERE user_id = ? LIMIT 1", (uid,))
            pet = c.fetchone()
        conn.close()
        return pet

    p1_pet = get_active_pet(interaction.user.id)
    p2_pet = get_active_pet(target.id)

    if not p1_pet:
        return await interaction.response.send_message("❌ Bạn chưa có Linh thú nào! Hãy dùng `/nuoithu` để quay Pet.", ephemeral=True)
    if not p2_pet:
        return await interaction.response.send_message(f"❌ {target.mention} chưa có Linh thú để tham gia PvP!", ephemeral=True)

    p1_name, _ = get_pet_info_display(p1_pet[1], p1_pet[2])
    p2_name, _ = get_pet_info_display(p2_pet[1], p2_pet[2])

    view = PVPChallengeView(interaction.user, target, p1_pet, p2_pet)
    await interaction.response.send_message(
        content=f"⚔️ {target.mention}, **{interaction.user.display_name}** xuất chiến với **{p1_name}** gửi lời thách đấu Linh thú **{p2_name}** của bạn!",
        view=view
    )

# ==========================================
# 6. HỆ THỐNG /leothap (LEO THÁP 11 TẦNG & BOSS)
# ==========================================

# Dữ liệu 11 tầng Tháp mặc định
DEFAULT_TOWER_BOSSES = [
    (1, "👾 Quái nhỏ", 500, 100, 20, 0.0, "ALL", ""),
    (2, "🧌 Zombie vua", 1000, 120, 40, 0.0, "ALL", ""),
    (3, "🧛 Ma cà rồng", 3000, 200, 100, 0.0, "ALL", ""),
    (4, "🩸 Lucifer", 5000, 300, 300, 0.0, "ALL", ""),
    (5, "🫀 Abaddon", 10000, 320, 310, 0.0, "ALL", ""),
    (6, "🐲 Leviathan", 15000, 1000, 500, 0.0, "ALL", ""),
    (7, "🪐 Bàn cổ", 30000, 3000, 1000, 0.60, "ALL", ""),
    (8, "🧿 Samyaza", 50000, 4000, 2000, 0.55, "sử thi,thần thoại,hư vọng", "Chân nhân"),
    (9, "🪬 Kokabiel", 80000, 6000, 3000, 0.70, "thần thoại,hư vọng", "Sáng thế nhân"),
    (10, "📿🪦🕧 ???", 100000, 100000, 100000, 1.00, "thần thoại,hư vọng", "???"),
    (11, "💀 Admin", 999999999999, 1, 1, 0.0, "ALL", "Tiểu Admin tối cao")
]

def init_tower_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tower_bosses")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO tower_bosses VALUES (?, ?, ?, ?, ?, ?, ?, ?)", DEFAULT_TOWER_BOSSES)
        conn.commit()
    conn.close()

init_tower_data()

class AddBossModal(discord.ui.Modal, title="Thêm Boss Tháp Mới (Admin)"):
    floor = discord.ui.TextInput(label="Số Tầng", placeholder="Ví dụ: 12", required=True)
    name = discord.ui.TextInput(label="Tên Boss", placeholder="Ví dụ: 👹 Tà Thần", required=True)
    cp = discord.ui.TextInput(label="Lực Chiến (CP)", placeholder="Ví dụ: 150000", required=True)
    rewards = discord.ui.TextInput(label="Thưởng Điểm - EXP", placeholder="Ví dụ: 5000 - 2000", required=True)
    effects = discord.ui.TextInput(label="Giảm ST (0.0-1.0) - Yêu Cầu Phẩm - Danh Hiệu", placeholder="Ví dụ: 0.5 - thần thoại,hư vọng - Độc Tôn", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Bạn không có quyền Admin!", ephemeral=True)
        try:
            fl = int(self.floor.value)
            boss_cp = int(self.cp.value)
            pts, exp = map(int, self.rewards.value.split("-"))
            eff_parts = [p.strip() for p in self.effects.value.split("-")]
            dmg_red = float(eff_parts[0])
            req_rarity = eff_parts[1] if len(eff_parts) > 1 else "ALL"
            title_rw = eff_parts[2] if len(eff_parts) > 2 else ""

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO tower_bosses VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (fl, self.name.value, boss_cp, pts, exp, dmg_red, req_rarity, title_rw))
            conn.commit()
            conn.close()

            await interaction.response.send_message(f"✅ Đã thêm Boss **{self.name.value}** vào Tầng **{fl}** thành công!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi định dạng nhập liệu: {str(e)}", ephemeral=True)

class DeleteBossModal(discord.ui.Modal, title="Xóa Boss Tháp (Admin)"):
    floor = discord.ui.TextInput(label="Số Tầng Cần Xóa", placeholder="Ví dụ: 12", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Bạn không có quyền Admin!", ephemeral=True)
        try:
            fl = int(self.floor.value)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("DELETE FROM tower_bosses WHERE floor = ?", (fl,))
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"✅ Đã xóa Boss Tầng **{fl}** khỏi hệ thống!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi: {str(e)}", ephemeral=True)

class TowerMainView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="➕ Thêm Boss (Admin)", style=discord.ButtonStyle.secondary, custom_id="btn_add_boss")
    async def add_boss_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được tính năng này!", ephemeral=True)
        await interaction.response.send_modal(AddBossModal())

    @discord.ui.button(label="➖ Xóa Boss (Admin)", style=discord.ButtonStyle.danger, custom_id="btn_del_boss")
    async def del_boss_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được tính năng này!", ephemeral=True)
        await interaction.response.send_modal(DeleteBossModal())

@bot.tree.command(name="leothap", description="Khiêu chiến Tháp Vô Tận để cày EXP Pet và Điểm")
@app_commands.describe(tang="Chọn số tầng tháp muốn khiêu chiến")
async def leothap(interaction: discord.Interaction, tang: int):
    user_id = interaction.user.id

    # Lấy thông tin Boss
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT floor, name, cp, reward_points, reward_exp, dmg_reduction, req_rarity, title_reward FROM tower_bosses WHERE floor = ?", (tang,))
    boss = c.fetchone()
    conn.close()

    if not boss:
        return await interaction.response.send_message(f"❌ Tầng **{tang}** hiện chưa có Boss dữ liệu!", ephemeral=True)

    fl, b_name, b_cp, b_pts, b_exp, b_red, b_rarity, b_title = boss

    # Lấy thông tin Pet đang kích hoạt
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, pet_type, level, exp FROM user_pets WHERE user_id = ? AND is_active = 1", (user_id,))
    pet = c.fetchone()
    if not pet:
        c.execute("SELECT id, pet_type, level, exp FROM user_pets WHERE user_id = ? LIMIT 1", (user_id,))
        pet = c.fetchone()
    conn.close()

    if not pet:
        return await interaction.response.send_message("❌ Bạn chưa có Linh thú nào! Hãy dùng `/nuoithu` để sở hữu Pet.", ephemeral=True)

    pet_id, p_type, p_lvl, p_exp = pet
    p_name, p_rarity = get_pet_info_display(p_type, p_lvl)
    p_cp = calculate_pet_cp(p_type, p_lvl)

    # Kiểm tra trang bị giảm hiệu ứng Boss "Bình tĩnh" (-30% khả năng giảm ST của Boss)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = 'Bình tĩnh' AND is_equipped = 1", (user_id,))
    has_calm = c.fetchone()
    conn.close()

    effective_reduction = b_red
    if has_calm and has_calm[0] > 0:
        effective_reduction = max(0.0, effective_reduction - 0.30)

    # 1. Kiểm tra yêu cầu phẩm cấp Linh thú
    if b_rarity != "ALL":
        allowed_rarities = [r.strip().lower() for r in b_rarity.split(",")]
        if p_rarity.lower() not in allowed_rarities:
            embed_fail = discord.Embed(
                title=f"💥 KHIÊU CHIẾN TẦNG {fl} THẤT BẠI!",
                description=f"**Boss {b_name}** sở hữu uy áp áp đảo!\n\n❌ Linh Thú **{p_name}** ({p_rarity.upper()}) không đủ điều kiện phẩm cấp để tham gia trận chiến này (Yêu cầu: **{b_rarity.upper()}**).",
                color=discord.Color.dark_red()
            )
            return await interaction.response.send_message(embed=embed_fail, view=TowerMainView(user_id))

    # 2. Tính toán Lực chiến thực tế sau khi chịu hiệu ứng giảm sát thương của Boss
    player_effective_cp = p_cp * (1.0 - effective_reduction)

    embed = discord.Embed(title=f"🏰 THÁP VÔ TẬN - TẦNG {fl}", color=discord.Color.gold())
    embed.add_field(name="👹 Thủ Vệ Boss", value=f"**{b_name}**\n• Lực chiến: `{b_cp}` CP\n• Kháng ST: `{int(effective_reduction * 100)}%`", inline=True)
    embed.add_field(name="🐾 Linh Thú Xuất Chiến", value=f"**{p_name}** (Lv.{p_lvl})\n• Lực chiến gốc: `{p_cp}` CP\n• Lực chiến thực tế: `{int(player_effective_cp)}` CP", inline=True)

    if player_effective_cp >= b_cp:
        # CHIẾN THẮNG
        update_points(user_id, b_pts)

        # Cộng EXP và kiểm tra Thăng cấp
        new_exp = p_exp + b_exp
        req_exp = get_next_exp_req(p_type, p_lvl)
        new_lvl = p_lvl
        if new_exp >= req_exp:
            new_lvl += 1
            new_exp -= req_exp

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE user_pets SET level = ?, exp = ? WHERE id = ?", (new_lvl, new_exp, pet_id))

        # Thưởng Danh hiệu nếu có
        title_msg = ""
        if b_title:
            c.execute("SELECT titles FROM users WHERE user_id = ?", (user_id,))
            curr_titles = c.fetchone()[0] or ""
            if b_title not in curr_titles:
                updated_titles = f"{curr_titles}, {b_title}".strip(", ")
                c.execute("UPDATE users SET titles = ? WHERE user_id = ?", (updated_titles, user_id))
                title_msg = f"\n🏆 **ĐÃ NHẬN DANH HIỆU MỚI:** `[{b_title}]`!"

        conn.commit()
        conn.close()

        embed.color = discord.Color.green()
        embed.add_field(name="🎉 KẾT QUẢ: CHIẾN THẮNG!", value=f"Bạn đã tiêu diệt **{b_name}**!\n\n**Phần thưởng:**\n• +**{b_pts}** Điểm\n• +**{b_exp}** EXP Linh Thú {title_msg}", inline=False)
        if new_lvl > p_lvl:
            new_display, _ = get_pet_info_display(p_type, new_lvl)
            embed.add_field(name="🎊 LINH THÚ THĂNG CẤP!", value=f"**{p_name}** đã tiến hóa/thăng cấp lên **{new_display}** (Level {new_lvl})!", inline=False)
    else:
        # THẤT BẠI
        embed.color = discord.Color.red()
        embed.add_field(name="💥 KẾT QUẢ: THẤT BẠI!", value=f"Lực chiến thực tế của Linh Thú (`{int(player_effective_cp)}` CP) không đủ để vượt qua Lực chiến của Boss (`{b_cp}` CP).\n\n💡 *Mẹo: Mua món 'Bình tĩnh' trong /shop hoặc nâng cấp Level Pet để vượt tầng này!*", inline=False)

    await interaction.response.send_message(embed=embed, view=TowerMainView(user_id))

# ==========================================
# HỆ THỐNG /causong (CHỌN CẦN & MỒI + TÍCH HỢP TÚI ĐỒ CHUẨN XÁC)
# ==========================================

DEFAULT_FISHES = [
    ("🐟 Cá Rô Đồng", "thường", 50.0, 10, ""),
    ("🐠 Cá Chép Vàng", "thường", 50.0, 10, ""),
    ("🦈 Cá Tầm", "thường", 50.0, 10, ""),
    ("🐧 Chim Cút", "thường", 50.0, 20, ""),
    ("👞 Giày Cũ Bị Rách", "thường", 40.0, -100, ""),
    ("👑 Rương Báu Dưới Sông", "hiếm", 40.0, 100, ""),
    ("🐙 Bạch tuộc", "hiếm", 40.0, 60, ""),
    ("🐢 Rùa con", "hiếm", 40.0, 70, ""),
    ("🦭 Tiểu long cẩu", "sử thi", 20.0, 200, ""),
    ("🦞 Tôm suki", "sử thi", 19.0, 210, ""),
    ("⭐ Light suki", "sử thi", 15.0, 220, ""),
    ("🫍 Cá voi sát thần", "thần thoại", 1.0, 500, "Sát long"),
    ("🦠 Virut tử thần", "thần thoại", 0.5, 1000, "Virut vương"),
    ("🐉 Leviathan", "thần thoại", 0.1, 2000, "Leviathan"),
    ("🌑 Chân thiên tôn", "hư vô", 0.001, 3000, "Thiên tôn")
]

def init_fish_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM fishes")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO fishes (name, rarity, rate, points, title) VALUES (?, ?, ?, ?, ?)", DEFAULT_FISHES)
        conn.commit()
    conn.close()

init_fish_data()

class AddFishModal(discord.ui.Modal, title="Thêm Cá Mới Vào Hệ Thống (Admin)"):
    name = discord.ui.TextInput(label="Tên Cá/Vật Phẩm (Bắt buộc)", placeholder="Ví dụ: 🐬 Cá Heo", required=True)
    rarity = discord.ui.TextInput(label="Phẩm cấp (Bắt buộc)", placeholder="thường/hiếm/sử thi/thần thoại/hư vô", required=True)
    rate = discord.ui.TextInput(label="Tỉ lệ ra (%) (Bắt buộc)", placeholder="Ví dụ: 10.0", required=True)
    points = discord.ui.TextInput(label="Điểm thưởng (Bắt buộc)", placeholder="Ví dụ: 150", required=True)
    title = discord.ui.TextInput(label="Danh hiệu (Tùy chọn)", placeholder="Để trống nếu không có", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Bạn không có quyền Admin!", ephemeral=True)
        try:
            r_rate = float(self.rate.value)
            r_pts = int(self.points.value)
            t_val = self.title.value.strip() if self.title.value else ""

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO fishes (name, rarity, rate, points, title) VALUES (?, ?, ?, ?, ?)",
                      (self.name.value, self.rarity.value.lower(), r_rate, r_pts, t_val))
            conn.commit()
            conn.close()

            await interaction.response.send_message(f"✅ Đã thêm cá **{self.name.value}** ({self.rarity.value}) thành công!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi định dạng: {str(e)}", ephemeral=True)

# Menu chọn Cần Câu từ túi đồ
class SelectRodDropdown(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT item_name, quantity, is_equipped FROM inventory WHERE user_id = ? AND (item_name LIKE '%Cần%' or item_name LIKE '%cần%')", (user_id,))
        rods = c.fetchall()
        conn.close()

        options = []
        for r in rods:
            name, qty, eq = r
            status = " [Đang trang bị]" if eq == 1 else ""
            options.append(discord.SelectOption(label=f"{name}{status}", value=name, emoji="🎣"))
        
        if not options:
            options.append(discord.SelectOption(label="Không có cần câu nào trong túi (Dùng tay không)", value="none", emoji="❌"))

        super().__init__(placeholder="🎣 Chọn Cần Câu muốn sử dụng...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        chosen_rod = self.values[0]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if chosen_rod != "none":
            c.execute("UPDATE inventory SET is_equipped = 0 WHERE user_id = ? AND (item_name LIKE '%Cần%' or item_name LIKE '%cần%')", (self.user_id,))
            c.execute("UPDATE inventory SET is_equipped = 1 WHERE user_id = ? AND item_name = ?", (self.user_id, chosen_rod))
            conn.commit()
            msg = f"🛡️ Đã chọn và trang bị thành công: **{chosen_rod}**!"
        else:
            c.execute("UPDATE inventory SET is_equipped = 0 WHERE user_id = ? AND (item_name LIKE '%Cần%' or item_name LIKE '%cần%')", (self.user_id,))
            conn.commit()
            msg = "⚠️ Bạn đang câu tay không (không dùng cần)."
        conn.close()
        await interaction.response.send_message(msg, ephemeral=True)

class SelectRodView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.add_item(SelectRodDropdown(user_id))

# Menu chọn Mồi Câu từ túi đồ (Dạng trang bị, không trừ điểm ngay khi chọn)
class SelectBaitDropdown(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT item_name, quantity, is_equipped FROM inventory WHERE user_id = ? AND (item_name LIKE '%Mồi%' or item_name LIKE '%mồi%')", (user_id,))
        baits = c.fetchall()
        conn.close()

        options = []
        for b in baits:
            name, qty, eq = b
            status = " [Đang dùng]" if eq == 1 else ""
            options.append(discord.SelectOption(label=f"{name} (x{qty}){status}", value=name, emoji="🪱"))
        
        if not options:
            options.append(discord.SelectOption(label="Không có mồi câu nào trong túi", value="none", emoji="❌"))

        super().__init__(placeholder="🪱 Chọn Mồi Câu muốn dùng...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        chosen_bait = self.values[0]
        if chosen_bait == "none":
            return await interaction.response.send_message("❌ Bạn không có mồi câu trong túi!", ephemeral=True)
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Set mồi này thành đang trang bị (is_equipped = 1), gỡ các mồi khác
        c.execute("UPDATE inventory SET is_equipped = 0 WHERE user_id = ? AND (item_name LIKE '%Mồi%' or item_name LIKE '%mồi%')", (self.user_id,))
        c.execute("UPDATE inventory SET is_equipped = 1 WHERE user_id = ? AND item_name = ?", (self.user_id, chosen_bait))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"🪱 Đã gắn mồi **{chosen_bait}}** vào lưỡi câu! Sẵn sàng thả mồi.", ephemeral=True)

class SelectBaitView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.add_item(SelectBaitDropdown(user_id))

class FishingView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="🎣 Thả Câu Ngay", style=discord.ButtonStyle.primary, custom_id="btn_fishing_action")
    async def fish_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Bảng này không phải của bạn!", ephemeral=True)

        base_success_rate = 0.45
        bonus_success = 0.0
        bonus_mythic_rate = 0.0

        # Lấy toàn bộ trang bị đang active (is_equipped = 1) và liên kết với shop_items để đọc hiệu ứng động
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            SELECT i.id, i.item_name, i.quantity, s.effect_type, s.effect_value 
            FROM inventory i 
            LEFT JOIN shop_items s ON i.item_name = s.name 
            WHERE i.user_id = ? AND i.is_equipped = 1
        """, (self.user_id,))
        equipped_items = c.fetchall()

        # Xử lý tính buff động từ Cần và Mồi đang trang bị
        equipped_bait_id = None
        for inv_id, item_name, qty, effect_type, effect_value in equipped_items:
            val = float(effect_value) if effect_value else 0.0
            lower_name = item_name.lower()

            # Nếu là Mồi câu -> tiêu hao 1 cái khi bấm thả câu
            if "mồi" in lower_name or effect_type == "bait":
                equipped_bait_id = inv_id
                # Áp dụng tỷ lệ buff linh hoạt dựa trên giá trị cấu hình trong shop hoặc tên
                if "cánh gió" in lower_name: bonus_success += 0.05
                elif "sao" in lower_name: bonus_success += 0.10
                elif "mặt trăng" in lower_name:
                    bonus_success -= 0.30
                    bonus_mythic_rate += 10.0 # Tăng % ra thần thoại
                elif "susanoo" in lower_name: bonus_success += 0.20
                elif "gorgon" in lower_name: bonus_success += 0.50
                elif "cá voi xanh" in lower_name: bonus_success += 0.02
                elif "tinh cầu" in lower_name: bonus_success += 0.50
                elif "nàng tiên cá" in lower_name: bonus_success += 0.40
                elif "may mắn" in lower_name:
                    if random.random() <= 0.5: bonus_success += 1.0
                    else: bonus_success -= 1.0
                else:
                    # Mồi tự do khác lấy trực tiếp từ effect_value của shop (chia 100 nếu tính theo %)
                    bonus_success += val / 100.0

            # Nếu là Cần câu
            elif "cần" in lower_name or effect_type == "rod":
                if "lửa" in lower_name: bonus_success += 0.03
                elif "băng" in lower_name: bonus_success += 0.05
                elif "quỷ" in lower_name: bonus_success += 0.09
                elif "vua" in lower_name: bonus_success += 0.15
                else:
                    bonus_success += val / 100.0

        # Tiến hành trừ 1 số lượng mồi đang dùng trong kho
        if equipped_bait_id:
            c.execute("SELECT quantity FROM inventory WHERE id = ?", (equipped_bait_id,))
            q_row = c.fetchone()
            if q_row:
                current_q = q_row[0]
                if current_q <= 1:
                    c.execute("DELETE FROM inventory WHERE id = ?", (equipped_bait_id,))
                else:
                    c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (equipped_bait_id,))

        conn.commit()

        final_success_rate = max(0.05, min(1.0, base_success_rate + bonus_success))

        # Kiểm tra đứt dây câu (Thất bại)
        if random.random() > final_success_rate:
            conn.close()
            embed_fail = discord.Embed(
                title="💔 RẤT TIẾC - ĐỨT DÂY CÂU!",
                description="Cá cắn câu quá mạnh làm đứt dây câu mất rồi! Mồi đã tiêu hao, hãy thử lại vận may lần sau nhé.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_fail)

        # Câu thành công -> Lấy danh sách cá từ Database và dùng thuật toán Weighted Random chuẩn xác
        c.execute("SELECT name, rarity, rate, points, title FROM fishes")
        all_fishes = c.fetchall()
        conn.close()

        weighted_fishes = []
        total_weight = 0
        for f in all_fishes:
            f_name, f_rarity, f_rate, f_pts, f_title = f
            calc_rate = f_rate
            if f_rarity == "thần thoại": 
                calc_rate += bonus_mythic_rate
            
            weighted_fishes.append((f, max(0.0001, calc_rate)))
            total_weight += max(0.0001, calc_rate)

        # Quay số ngẫu nhiên theo tổng trọng số tỷ lệ
        pick = random.uniform(0, total_weight)
        current = 0
        selected_fish = all_fishes[0]
        for f, rate in weighted_fishes:
            current += rate
            if pick <= current:
                selected_fish = f
                break

        f_name, f_rarity, f_rate, f_pts, f_title = selected_fish

        update_points(self.user_id, f_pts)

        title_msg = ""
        if f_title:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT titles FROM users WHERE user_id = ?", (self.user_id,))
            row_t = c.fetchone()
            curr_titles = row_t[0] if row_t and row_t[0] else ""
            if f_title not in curr_titles:
                updated_titles = f"{curr_titles}, {f_title}".strip(", ")
                c.execute("UPDATE users SET titles = ? WHERE user_id = ?", (updated_titles, self.user_id))
                title_msg = f"\n🏆 **ĐÃ NHẬN DANH HIỆU:** `[{f_title}]`!"
            conn.commit()
            conn.close()

        pts_str = f"+{f_pts}" if f_pts >= 0 else f"{f_pts}"
        embed_win = discord.Embed(
            title="🎣 CÂU CÁ THÀNH CÔNG!",
            description=f"Bạn đã giật cần và bắt được:\n\n### {f_name}\n* **Phẩm cấp:** {f_rarity.upper()}\n* **Phần thưởng:** `{pts_str}` Điểm {title_msg}",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed_win)

    @discord.ui.button(label="🎣 Chọn Cần Câu", style=discord.ButtonStyle.secondary, custom_id="btn_select_rod")
    async def select_rod_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Bảng này không phải của bạn!", ephemeral=True)
        await interaction.response.send_message("👇 Chọn cây cần câu bạn muốn trang bị từ túi đồ:", view=SelectRodView(self.user_id), ephemeral=True)

    @discord.ui.button(label="🪱 Chọn Mồi Câu", style=discord.ButtonStyle.secondary, custom_id="btn_select_bait")
    async def select_bait_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Bảng này không phải của bạn!", ephemeral=True)
        await interaction.response.send_message("👇 Chọn mồi câu bạn muốn sử dụng từ túi đồ:", view=SelectBaitView(self.user_id), ephemeral=True)

    @discord.ui.button(label="➕ Thêm Cá (Admin)", style=discord.ButtonStyle.danger, custom_id="btn_add_fish_admin")
    async def add_fish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được nút này!", ephemeral=True)
        await interaction.response.send_modal(AddFishModal())

@bot.tree.command(name="causong", description="Thả mồi câu cá bên bờ sông nhận Điểm & Danh hiệu")
async def causong(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌊 BỜ SÔNG CÂU CÁ THƯ GIÃN",
        description="Hãy chọn **Cần Câu** hoặc **Mồi Câu** từ túi đồ của bạn trước khi bấm **Thả Câu Ngay** để tăng tỷ lệ bắt cá quý hiếm!",
        color=discord.Color.teal()
    )
    view = FishingView(user_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==========================================
# 8. HỆ THỐNG /shop & TÚI ĐỒ /tuido
# ==========================================

DEFAULT_SHOP_ITEMS = [
    # Mồi
    ("candaumoi", "🪽 Mồi cánh gió", 100, "Tăng 5% tỷ lệ câu cá thường thành công", "buff_fish_success", 0.05),
    ("candaumoi", "✨ Mồi sao", 200, "Tăng 10% câu thành công & 10% cá hiếm", "buff_fish_success", 0.10),
    ("candaumoi", "🌛 Mồi mặt trăng", 10000, "-30% tỷ lệ thành công, +10% câu cá thần thoại", "buff_fish_mythic", 0.10),
    ("candaumoi", "🥞 Mồi susanoo", 11000, "Tăng 20% câu thành công & 20% cá sử thi", "buff_fish_success", 0.20),
    ("candaumoi", "👀 Mồi mắt Gorgon", 15000, "Tăng 50% câu thành công & +15% cá hiếm/sử thi", "buff_fish_success", 0.50),
    ("candaumoi", "🐋 Mồi cá voi xanh", 16000, "Tăng 2% tỷ lệ câu thành công vĩnh viễn", "buff_fish_perm", 0.02),
    ("candaumoi", "🌎 Mồi tinh cầu", 20000, "Tăng 50% tỷ lệ câu & +10% cá thần thoại", "buff_fish_success", 0.50),
    ("candaumoi", "🧜 Mồi nàng tiên cá", 25000, "Tăng 40% câu thành công & +5% cá thần thoại", "buff_fish_success", 0.40),
    ("candaumoi", "🎁 Mồi may mắn", 100000, "50% tăng 100% tỷ lệ câu, 50% -100% tỷ lệ câu", "buff_lucky", 1.0),

    # Cần câu
    ("candaumoi", "🥖 Cần bánh mì", 10, "Cần câu bình dân", "none", 0),
    ("candaumoi", "⚡ Cần sét", 100, "Cần câu nhanh nhẹn", "none", 0),
    ("candaumoi", "🫏 Cần mèo", 200, "Cần câu dễ thương", "none", 0),
    ("candaumoi", "🔥 Cần lửa", 1000, "Tăng 3% câu thành công", "buff_fish_success", 0.03),
    ("candaumoi", "🥶 Cần băng", 10000, "Tăng 5% câu thành công & 4% cá sử thi/hiếm", "buff_fish_success", 0.05),
    ("candaumoi", "👺 Cần quỷ", 20000, "Tăng 9% câu thành công & 10% cá thần thoại", "buff_fish_success", 0.09),
    ("candaumoi", "👑 Cần vua", 30000, "Tăng 15% câu thành công & 15% cá thần thoại", "buff_fish_success", 0.15),
    ("candaumoi", "🫯 Bom nguyên tử", 33000, "Tăng 1% câu được cá hư vô", "buff_void", 0.01),

    # Đồ ăn Pet
    ("doan_trangbi", "🍑 Đào lumi", 20, "Tăng 10 EXP cho Linh Thú", "add_exp", 10),
    ("doan_trangbi", "🌹 Hoa furina", 200, "Tăng 100 EXP cho Linh Thú", "add_exp", 100),
    ("doan_trangbi", "🍖 Thịt hổ", 600, "Tăng 300 EXP cho Linh Thú", "add_exp", 300),
    ("doan_trangbi", "🍄 Nấm chaac", 1500, "Tăng 600 EXP & 10 CP trong 10 phút", "add_exp", 600),
    ("doan_trangbi", "🥬 Ravena", 1450, "Tăng 500 EXP cho Linh Thú", "add_exp", 500),
    ("doan_trangbi", "🧅 Thái âm dương quả", 2000, "Tăng 1000 EXP cho Linh Thú", "add_exp", 1000),
    ("doan_trangbi", "🌕 Cửu diệp thảo quả", 2300, "Tăng 1100 EXP cho Linh Thú", "add_exp", 1100),
    ("doan_trangbi", "💀 Linh tủy quả", 5000, "Tăng 100 CP vĩnh viễn cho Linh Thú", "add_cp_perm", 100),
    ("doan_trangbi", "🌏 Hỗn độn thanh liên Quả", 20000, "Tăng 10000 EXP cho Linh Thú", "add_exp", 10000),
    ("doan_trangbi", "🐦‍🔥 Bất tử phượng hoàng quả", 30000, "Tăng 1000 CP vĩnh viễn & 1000 EXP", "add_cp_exp", 1000),

    # Trang bị Pet
    ("doan_trangbi", "🖕 Chi dục", 100000, "Tăng 50% tỷ lệ thắng trong /pvp_pet", "pvp_buff", 0.5),
    ("doan_trangbi", "🫸 Bình tĩnh", 100000, "Giảm 30% kháng sát thương của Boss Tháp", "tower_buff", 0.3),
    ("doan_trangbi", "🌀 Tịnh diệt kiếm ý", 50000, "Tăng 1000 Lực chiến CP", "add_cp_perm", 1000),
    ("doan_trangbi", "🌚 Cửu u minh kiếm", 55000, "Tăng 2000 Lực chiến CP", "add_cp_perm", 2000),
    ("doan_trangbi", "🔪 Pháp tắc chi nhân", 80000, "Tăng 5000 Lực chiến CP", "add_cp_perm", 5000),
    ("doan_trangbi", "🔫 Xúng xxx zzz", 150000, "50% cơ hội tăng 10000 Lực chiến CP khi sử dụng", "chance_cp", 10000)
]

def init_shop_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM shop_items")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO shop_items (category, name, price, description, effect_type, effect_value) VALUES (?, ?, ?, ?, ?, ?)", DEFAULT_SHOP_ITEMS)
        conn.commit()
    conn.close()

init_shop_data()

class AddShopItemModal(discord.ui.Modal, title="Update Đồ Cửa Hàng (Admin)"):
    cat = discord.ui.TextInput(label="Loại (candaumoi / doan_trangbi)", placeholder="candaumoi", required=True)
    name = discord.ui.TextInput(label="Tên Vật Phẩm", placeholder="Ví dụ: 🗡️ Kiếm Thần", required=True)
    price = discord.ui.TextInput(label="Giá Mua (Điểm)", placeholder="Ví dụ: 5000", required=True)
    desc = discord.ui.TextInput(label="Mô Tả & Hiệu Ứng", placeholder="Ví dụ: Tăng 500 CP cho Pet", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Bạn không có quyền Admin!", ephemeral=True)
        try:
            p_val = int(self.price.value)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO shop_items (category, name, price, description, effect_type, effect_value) VALUES (?, ?, ?, ?, 'custom', 0)",
                      (self.cat.value.lower(), self.name.value, p_val, self.desc.value))
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"✅ Đã thêm vật phẩm **{self.name.value}** vào Shop thành công!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi: {str(e)}", ephemeral=True)

class ShopCategorySelect(discord.ui.Select):
    def __init__(self, items, user_id):
        self.user_id = user_id
        options = [
            discord.SelectOption(label=f"{item[1]} - {item[2]} Điểm", description=item[3][:50], value=str(item[0]))
            for item in items[:25]
        ]
        super().__init__(placeholder="🛒 Chọn vật phẩm muốn mua...", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_id = int(self.values[0])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT name, price FROM shop_items WHERE id = ?", (item_id,))
        item = c.fetchone()
        conn.close()

        if not item:
            return await interaction.response.send_message("❌ Vật phẩm không tồn tại!", ephemeral=True)

        i_name, i_price = item
        u_data = get_user(interaction.user.id)
        if u_data["points"] < i_price:
            return await interaction.response.send_message(f"❌ Bạn không đủ điểm! Cần **{i_price}** Điểm.", ephemeral=True)

        update_points(interaction.user.id, -i_price)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_name = ?", (interaction.user.id, i_name))
        inv = c.fetchone()
        if inv:
            c.execute("UPDATE inventory SET quantity = quantity + 1 WHERE id = ?", (inv[0],))
        else:
            c.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (interaction.user.id, i_name))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"🎉 Mua thành công **{i_name}** với giá `{i_price}` Điểm! Món đồ đã được thêm vào `/tuido`.", ephemeral=True)

class ShopMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎣 Cần & Mồi", style=discord.ButtonStyle.primary, custom_id="btn_shop_rods")
    async def shop_rods(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, name, price, description FROM shop_items WHERE category = 'candaumoi'")
        items = c.fetchall()
        conn.close()

        embed = discord.Embed(title="🛒 SHOP CẦN CÂU & MỒI CÂU", color=discord.Color.blue())
        view = discord.ui.View(timeout=None)
        view.add_item(ShopCategorySelect(items, interaction.user.id))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🍖 Đồ Ăn & Trang Bị Pet", style=discord.ButtonStyle.success, custom_id="btn_shop_pet_items")
    async def shop_pet_items(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, name, price, description FROM shop_items WHERE category = 'doan_trangbi'")
        items = c.fetchall()
        conn.close()

        embed = discord.Embed(title="🛒 SHOP ĐỒ ĂN & TRANG BỊ PET", color=discord.Color.green())
        view = discord.ui.View(timeout=None)
        view.add_item(ShopCategorySelect(items, interaction.user.id))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="⚙️ Update Đồ Shop (Admin)", style=discord.ButtonStyle.danger, custom_id="btn_shop_admin_update")
    async def shop_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Chỉ Quản trị viên mới dùng được nút này!", ephemeral=True)
        await interaction.response.send_modal(AddShopItemModal())

@bot.tree.command(name="shop", description="Mở Cửa Hàng Mua Cần, Mồi, Đồ Ăn & Trang Bị")
async def shop(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Lệnh này chỉ dành cho Admin gọi menu Shop!", ephemeral=True)

    embed = discord.Embed(
        title="🏪 HỆ THỐNG CỬA HÀNG TRỰC TUYẾN",
        description="Bấm các nút bên dưới để chọn loại Cửa Hàng bạn muốn mua sắm!",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=ShopMainView())

# ==========================================
# PHẦN TÚI ĐỒ & SỬ DỤNG VẬT PHẨM (LIÊN KẾT SHOP)
# ==========================================

class InventorySelect(discord.ui.Select):
    def __init__(self, items):
        options = []
        for name, qty, eq in items[:25]:
            eq_text = " 🟢 [Đang trang bị]" if eq == 1 else ""
            options.append(discord.SelectOption(
                label=f"{name} (x{qty}){eq_text}",
                description="Bấm để trang bị hoặc sử dụng vật phẩm này",
                value=name,
                emoji="🍄"
            ))
        super().__init__(placeholder="🍄 Chọn vật phẩm muốn sử dụng...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        item_name = self.values[0]
        user_id = interaction.user.id

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # 1. Lấy thông tin từ shop_items để biết phân loại và hiệu ứng
        c.execute("SELECT category, effect_type, effect_value FROM shop_items WHERE name = ?", (item_name,))
        shop_info = c.fetchone()
        
        # 2. Kiểm tra kho đồ của người chơi
        c.execute("SELECT id, quantity, is_equipped FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        inv_row = c.fetchone()

        if not inv_row or inv_row[1] <= 0:
            conn.close()
            return await interaction.response.send_message("❌ Vật phẩm này không còn trong túi đồ của bạn!", ephemeral=True)

        inv_id, current_qty, is_eq = inv_row
        
        category = shop_info[0].lower() if shop_info and shop_info[0] else ""
        effect_type = shop_info[1].lower() if shop_info and shop_info[1] else "none"
        effect_value = shop_info[2] if shop_info and shop_info[2] else 0

        msg = ""

        # --- NHÓM 1: CẦN CÂU HOẶC TRANG BỊ (Mặc / Tháo đổi trạng thái is_equipped) ---
        is_equipment_item = (
            "cần" in item_name.lower() or 
            "kiếm" in item_name.lower() or 
            "giáp" in item_name.lower() or 
            "bảo vật" in item_name.lower() or 
            "trang bị" in item_name.lower() or 
            "bình tĩnh" in item_name.lower() or
            "chi dục" in item_name.lower() or
            category in ["rod", "equipment", "weapon", "armor"] or
            effect_type in ["rod", "equipment"]
        )

        if is_equipment_item:
            if is_eq == 1:
                c.execute("UPDATE inventory SET is_equipped = 0 WHERE id = ?", (inv_id,))
                msg = f"🔄 Bạn đã tháo thành công **{item_name}**!"
            else:
                if "cần" in item_name.lower() or effect_type == "rod":
                    c.execute("UPDATE inventory SET is_equipped = 0 WHERE user_id = ? AND (item_name LIKE '%Cần%' OR item_name LIKE '%cần%')", (user_id,))
                
                c.execute("UPDATE inventory SET is_equipped = 1 WHERE id = ?", (inv_id,))
                msg = f"🛡️ Bạn đã trang bị thành công **{item_name}**!"
            
            conn.commit()
            conn.close()
            return await interaction.response.send_message(msg, ephemeral=True)

        # --- NHÓM 2: THỨC ĂN / BỒI BỔ CHO PET (Tiêu thụ để tăng EXP & Tự động thăng cấp) ---
        is_food_item = (
            "đào" in item_name.lower() or 
            "thảo quả" in item_name.lower() or 
            "thịt" in item_name.lower() or 
            "nấm" in item_name.lower() or 
            "quả" in item_name.lower() or 
            category in ["food", "pet_food"] or
            effect_type == "add_exp"
        )

        if is_food_item:
            new_qty = current_qty - 1
            if new_qty <= 0:
                c.execute("DELETE FROM inventory WHERE id = ?", (inv_id,))
            else:
                c.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_qty, inv_id))
            
            # Lấy thêm pet_type để tính mốc exp tiến hóa chuẩn xác
            c.execute("SELECT id, pet_type, level, exp FROM user_pets WHERE user_id = ? AND is_active = 1", (user_id,))
            active_pet = c.fetchone()
            
            if active_pet:
                pet_id, pet_type, lvl, current_exp = active_pet
                
                # Lấy đúng số EXP thực tế từ shop (ví dụ 1100), nếu không có mới fallback về 150
                exp_gain = int(effect_value) if effect_value and effect_value > 0 else 150
                current_exp += exp_gain
                
                leveled_up = False
                max_exp = get_next_exp_req(pet_type, lvl)
                
                # Vòng lặp kiểm tra thăng cấp nếu EXP vượt ngưỡng
                while current_exp >= max_exp:
                    current_exp -= max_exp
                    lvl += 1
                    leveled_up = True
                    max_exp = get_next_exp_req(pet_type, lvl)

                c.execute("UPDATE user_pets SET level = ?, exp = ? WHERE id = ?", (lvl, current_exp, pet_id))
                new_pet_name, _ = get_pet_info_display(pet_type, lvl)
                
                if leveled_up:
                    msg = f"🎉 Tuyệt vời! Linh thú ăn **{item_name}** (`+{exp_gain} EXP`) và tiến hóa thành **{new_pet_name} (Level {lvl})** thành công!"
                else:
                    msg = f"✨ Bạn đã cho linh thú xuất trận ăn **{item_name}**, nhận thành công `+{exp_gain} EXP`!"
            else:
                msg = f"✨ Đã tiêu thụ **{item_name}**, nhưng bạn chưa chọn linh thú xuất trận (`/nuoithu`) nên pet không nhận được EXP!"
            
            conn.commit()
            conn.close()
            return await interaction.response.send_message(msg, ephemeral=True)

        # --- NHÓM 3: VẬT PHẨM TIÊU HAO KHÁC ---
        new_qty = current_qty - 1
        if new_qty <= 0:
            c.execute("DELETE FROM inventory WHERE id = ?", (inv_id,))
        else:
            c.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_qty, inv_id))

        if "mồi" in item_name.lower() or effect_type == "bait":
            msg = f"🪱 Đã kích hoạt mồi **{item_name}** thành công! Sẵn sàng mang ra bờ sông câu cá (`/causong`)."
        elif effect_type == "add_points":
            pts = int(effect_value) if effect_value else 100
            update_points(user_id, pts)
            msg = f"💰 Bạn đã sử dụng **{item_name}** và nhận được `{pts}` Điểm!"
        else:
            msg = f"✨ Bạn đã sử dụng thành công **{item_name}** từ túi đồ!"

        conn.commit()
        conn.close()

        await interaction.response.send_message(msg, ephemeral=True)

# ==========================================
# 9. CÁC LỆNH MINI-GAME & TƯƠNG TÁC (/cuop, /taixiu)
# ==========================================

@bot.tree.command(name="cuop", description="Thử thách cướp điểm của người chơi khác (Nguy hiểm!)")
@app_commands.describe(member="Người chơi bạn muốn cướp điểm")
async def cuop(interaction: discord.Interaction, member: discord.Member):
    if member.id == interaction.user.id:
        return await interaction.response.send_message("❌ Bạn không thể tự cướp chính mình!", ephemeral=True)
    if member.bot:
        return await interaction.response.send_message("❌ Không thể cướp bot!", ephemeral=True)

    thief_data = get_user(interaction.user.id)
    target_data = get_user(member.id)

    if thief_data["points"] < 50:
        return await interaction.response.send_message("❌ Bạn cần ít nhất **50 điểm** trong tài khoản mới dám đi cướp!", ephemeral=True)
    if target_data["points"] < 50:
        return await interaction.response.send_message(f"❌ Mục tiêu `{member.display_name}` nghèo quá, không có gì để cướp cả!", ephemeral=True)

    # Tỷ lệ cướp thành công 40%
    if random.random() <= 0.40:
        stolen_pts = random.randint(10, min(50, target_data["points"]))
        update_points(interaction.user.id, stolen_pts)
        update_points(member.id, -stolen_pts)
        
        embed = discord.Embed(
            title="🥷 CƯỚP ĐIỂM THÀNH CÔNG!",
            description=f"Bạn đã lẻn vào nhà và vơ vét được `{stolen_pts}` Điểm từ **{member.mention}**!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        fine_pts = random.randint(20, min(50, thief_data["points"]))
        update_points(interaction.user.id, -fine_pts)
        update_points(member.id, fine_pts)

        embed = discord.Embed(
            title="🚨 BỊ TÚM CỔ - CƯỚP THẤT BẠI!",
            description=f"Bạn đã bị **{member.mention}** tóm gọn! Phải đền bù danh dự và mất phạt `{fine_pts}` Điểm vào tay họ.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

class TaiXiuView(discord.ui.View):
    def __init__(self, user_id: int, bet_amount: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet_amount = bet_amount

    @discord.ui.button(label="🎲 ĐẶT TÀI (11-18)", style=discord.ButtonStyle.green, custom_id="btn_tx_tai")
    async def tai_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_taixiu(interaction, "Tài")

    @discord.ui.button(label="🎲 ĐẶT XỈU (3-10)", style=discord.ButtonStyle.red, custom_id="btn_tx_xiu")
    async def xiu_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_taixiu(interaction, "Xỉu")

    async def process_taixiu(self, interaction: discord.Interaction, choice: str):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Đây không phải bàn tài xỉu của bạn!", ephemeral=True)

        u_data = get_user(self.user_id)
        if u_data["points"] < self.bet_amount:
            return await interaction.response.send_message(f"❌ Bạn không đủ `{self.bet_amount}` Điểm để chơi tiếp!", ephemeral=True)

        # Tung 3 con xúc sắc (1-6)
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        d3 = random.randint(1, 6)
        total = d1 + d2 + d3

        result = "Tài" if total >= 11 else "Xỉu"
        is_win = (choice == result)

        if is_win:
            update_points(self.user_id, self.bet_amount)
            msg_status = f"🎉 **THẮNG CƯỢC!** Nhận về `+{self.bet_amount}` Điểm."
            color = discord.Color.green()
        else:
            update_points(self.user_id, -self.bet_amount)
            msg_status = f"😢 **THUA CƯỢC!** Mất `- {self.bet_amount}` Điểm."
            color = discord.Color.red()

        embed = discord.Embed(
            title="🎲 KẾT QUẢ TÀI XỈU",
            description=f"* **Lựa chọn của bạn:** {choice}\n* **Xúc xắc ra:** 🎲 `{d1}` - 🎲 `{d2}` - 🎲 `{d3}`\n* **Tổng điểm:** **{total} ({result})**\n\n{msg_status}",
            color=color
        )
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

@bot.tree.command(name="taixiu", description="Chơi minigame Tài Xỉu đặt cược Điểm")
@app_commands.describe(sodiem="Số điểm bạn muốn đặt cược")
async def taixiu(interaction: discord.Interaction, sodiem: int):
    if sodiem <= 0:
        return await interaction.response.send_message("❌ Số điểm cược phải lớn hơn 0!", ephemeral=True)
    
    u_data = get_user(interaction.user.id)
    if u_data["points"] < sodiem:
        return await interaction.response.send_message(f"❌ Bạn chỉ đang có `{u_data['points']}` Điểm, không đủ để cược `{sodiem}` Điểm!", ephemeral=True)

    embed = discord.Embed(
        title="🎲 BÀN CƯỢC TÀI XỈU",
        description=f"Mức cược hiện tại: **{sodiem} Điểm**\nHãy chọn **TÀI** (11-18) hoặc **XỈU** (3-10) bên dưới:",
        color=discord.Color.blurple()
    )
    view = TaiXiuView(user_id=interaction.user.id, bet_amount=sodiem)
    await interaction.response.send_message(embed=embed, view=view)

# ==========================================
# 10. HỆ THỐNG XẾP HẠNG & QUẢN TRỊ ADMIN (/bangxephang, /point_edit, /set_top1_title)
# ==========================================

@bot.tree.command(name="bangxephang", description="Xem Bảng Xếp Hạng Top 10 người chơi giàu điểm nhất Server")
async def bangxephang(interaction: discord.Interaction):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, points, titles FROM users ORDER BY points DESC LIMIT 10")
    top_users = c.fetchall()
    conn.close()

    embed = discord.Embed(
        title="🏆 BẢNG XẾP HẠNG ĐIỂM SỐ SERVER",
        description="Top 10 đại gia nắm giữ nhiều Điểm nhất:",
        color=discord.Color.gold()
    )

    medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    desc_str = ""
    for idx, (uid, pts, titles) in enumerate(top_users):
        user_obj = bot.get_user(uid)
        username = user_obj.name if user_obj else f"User ID: {uid}"
        medal = medal_emojis[idx] if idx < len(medal_emojis) else f"#{idx+1}"
        
        display_title = ""
        if titles:
            first_title = titles.split(",")[0].strip()
            display_title = f" `[{first_title}]`"

        desc_str += f"{medal} **{username}**{display_title} — `{pts}` Điểm\n"

    embed.add_field(name="", value=desc_str if desc_str else "*Chưa có dữ liệu xếp hạng.*", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="point_edit", description="[Admin] Cộng hoặc trừ điểm của một người chơi")
@app_commands.describe(member="Thành viên cần chỉnh sửa điểm", sodiem="Số điểm (Nhập số âm nếu muốn trừ)")
async def point_edit(interaction: discord.Interaction, member: discord.Member, sodiem: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này!", ephemeral=True)

    update_points(member.id, sodiem)
    action_text = f"cộng `+{sodiem}`" if sodiem >= 0 else f"trừ `{sodiem}`"
    
    await interaction.response.send_message(
        f"✅ Quản trị viên **{interaction.user.display_name}** đã {action_text} điểm của **{member.mention}** thành công!",
        ephemeral=True
    )

@bot.tree.command(name="set_top1_title", description="[Admin] Thay đổi danh hiệu thưởng cho Top 1 BXH")
@app_commands.describe(new_title="Nhận danh hiệu mới cho Top 1")
async def set_top1_title(interaction: discord.Interaction, new_title: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này!", ephemeral=True)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM lb_config WHERE id = 1")
    if c.fetchone():
        c.execute("UPDATE lb_config SET top1_title = ? WHERE id = 1", (new_title,))
    else:
        c.execute("INSERT INTO lb_config (id, top1_title) VALUES (1, ?)", (new_title,))
    conn.commit()
    conn.close()

    await interaction.response.send_message(f"✅ Đã cập nhật danh hiệu Top 1 thành công thành: **{new_title}**!", ephemeral=True)

# ==========================================
# 11. KHỞI CHẠY BOT
# ==========================================

import os

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ thành công {len(synced)} lệnh slash!")
    except Exception as e:
        print(f"Lỗi đồng bộ lệnh: {e}")
    
    print(f"Bot đã đăng nhập thành công với tên: {bot.user.name}")

# Ưu tiên lấy token từ biến môi trường trên Render, nếu không có sẽ nhận giá trị dự phòng bên dưới
BOT_TOKEN = os.getenv("BOT_TOKEN", "ĐIỀN_TOKEN_CỦA_BẠN_VÀO_ĐÂY_NẾU_KHÔNG_DÙNG_ENV")

if __name__ == "__main__":
    if BOT_TOKEN == "ĐIỀN_TOKEN_CỦA_BẠN_VÀO_ĐÂY_NẾU_KHÔNG_DÙNG_ENV" or not BOT_TOKEN:
        print("⚠️ Vui lòng cấu hình biến môi trường BOT_TOKEN hoặc điền token trực tiếp vào code!")
    else:
        bot.run(BOT_TOKEN)

import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import json
import random
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==========================================
# SYSTEM SETUP & INTENTS
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
DB_FILE = "bot_database.db"

# ==========================================
# DATABASE INIT & PERSISTENCE (SQLITE3)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Bảng người chơi
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        points INTEGER DEFAULT 1000,
        active_pet_idx INTEGER DEFAULT NULL,
        equipped_rod TEXT DEFAULT NULL,
        equipped_bait TEXT DEFAULT NULL,
        equipped_pet_item TEXT DEFAULT NULL,
        active_title TEXT DEFAULT NULL,
        titles TEXT DEFAULT '[]'
    )''')
    
    # Bảng cưng (Pets)
    c.execute('''CREATE TABLE IF NOT EXISTS pets (
        pet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        type TEXT,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        bonus_cp INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')

    # Bảng túi đồ (Inventory)
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        user_id TEXT,
        item_id TEXT,
        quantity INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, item_id)
    )''')

    # Bảng cài đặt hệ thống (Custom pets, fish, shop, config)
    c.execute('''CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def db_get_user(user_id: int):
    uid = str(user_id)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, points) VALUES (?, 1000)", (uid,))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
        row = c.fetchone()
    conn.close()
    return dict(row)

def db_update_user(user_id: int, **kwargs):
    uid = str(user_id)
    conn = get_db()
    c = conn.cursor()
    fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [uid]
    c.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

def db_get_user_pets(user_id: int):
    uid = str(user_id)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM pets WHERE user_id = ?", (uid,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_get_inventory(user_id: int):
    uid = str(user_id)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ? AND quantity > 0", (uid,))
    rows = c.fetchall()
    conn.close()
    return {r["item_id"]: r["quantity"] for r in rows}

def db_add_inventory(user_id: int, item_id: str, amount: int = 1):
    uid = str(user_id)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (uid, item_id))
    row = c.fetchone()
    if row:
        new_q = row["quantity"] + amount
        if new_q <= 0:
            c.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ?", (uid, item_id))
        else:
            c.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?", (new_q, uid, item_id))
    else:
        if amount > 0:
            c.execute("INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)", (uid, item_id, amount))
    conn.commit()
    conn.close()

# Config Json helpers
def get_config(key: str, default: Any):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM system_config WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return default

def set_config(key: str, value: Any):
    conn = get_db()
    c = conn.cursor()
    val_json = json.dumps(value, ensure_ascii=False)
    c.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", (key, val_json))
    conn.commit()
    conn.close()

# ==========================================
# BASE GAME DATA
# ==========================================
BASE_PETS = {
    "sutu": {
        "name": "Sư tử con", "rarity": "Thường", "rate": 0.70,
        "stages": [
            {"name": "🦁 Sư tử con", "max_exp": 100},
            {"name": "🐯 Vua hổ", "max_exp": 1000},
            {"name": "⚡🐅 Sấm chị lâm", "max_exp": 2000}
        ],
        "stat_base": 50, "stat_high": 100
    },
    "gau": {
        "name": "Gấu con", "rarity": "Thường", "rate": 0.70,
        "stages": [
            {"name": "🐻 Gấu con", "max_exp": 100},
            {"name": "🐻🙈 Gấu béo", "max_exp": 1000},
            {"name": "🐻⭐ Thần gấu phương nam", "max_exp": 2000}
        ],
        "stat_base": 60, "stat_high": 110
    },
    "gautruc": {
        "name": "Gấu trúc con", "rarity": "Hiếm", "rate": 0.50,
        "stages": [
            {"name": "🐼 Gấu trúc con", "max_exp": 200},
            {"name": "🐼👑 Vua gấu", "max_exp": 2000},
            {"name": "🐼&🌛 Thái cực thiên tôn", "max_exp": 3000}
        ],
        "stat_base": 100, "stat_high": 150
    },
    "camap": {
        "name": "Cá mập con", "rarity": "Hiếm", "rate": 0.50,
        "stages": [
            {"name": "🦈 Cá mập con", "max_exp": 300},
            {"name": "🦈😶 Thần tử", "max_exp": 3000},
            {"name": "🐋 Tinh kình", "max_exp": 4000}
        ],
        "stat_base": 150, "stat_high": 200
    },
    "daibang": {
        "name": "Đại bàng trắng con", "rarity": "Sử thi", "rate": 0.20,
        "stages": [
            {"name": "🦅 Đại bàng trắng con", "max_exp": 500},
            {"name": "⚡🦅 Sấm đại cửu u", "max_exp": 5000},
            {"name": "🦅🔥 Tiểu thần quân", "max_exp": 10000}
        ],
        "stat_base": 500, "stat_high": 1000
    },
    "kilan": {
        "name": "Kì lân con", "rarity": "Sử thi", "rate": 0.10,
        "stages": [
            {"name": "🦄 Kì lân con", "max_exp": 600},
            {"name": "🦄🙈 Bạch thú chi vương", "max_exp": 6000},
            {"name": "🦄🔥 Hoả Lâm Chân Nhân", "max_exp": 8000}
        ],
        "stat_base": 600, "stat_high": 1500
    },
    "rong": {
        "name": "Rồng con", "rarity": "Thần thoại", "rate": 0.01,
        "stages": [
            {"name": "🐉 Pet rồng con", "max_exp": 1000},
            {"name": "🐉🦅 Ứng long chân nhân", "max_exp": 5000},
            {"name": "🐲 Chí tôn long hoàng", "max_exp": 20000}
        ],
        "stat_base": 5000, "stat_high": 10000
    },
    "phuonghoang": {
        "name": "Phượng hoàng con", "rarity": "Thần thoại", "rate": 0.01,
        "stages": [
            {"name": "🐦‍🔥 Phượng hoàng con", "max_exp": 2000},
            {"name": "🐦‍🔥🌋 Niết bàn vĩnh hằng", "max_exp": 7000},
            {"name": "🐦‍🔥🩸 Thái dương thần điểu", "max_exp": 25000}
        ],
        "stat_base": 7000, "stat_high": 12000
    },
    "diathien": {
        "name": "Địa thiên cực bắc đại đế", "rarity": "Hư vọng", "rate": 0.001,
        "stages": [
            {"name": "🌏 Địa thiên cực bắc đại đế", "max_exp": 10000},
            {"name": "🌌🌑 Tử vi tinh đại đế", "max_exp": 40000},
            {"name": "🌌🪐 Hư không cổ Hoàng", "max_exp": 80000}
        ],
        "stat_base": 10000, "stat_high": 30000
    }
}

DEFAULT_SHOP = {
    "bait": [
        {"id": "b1", "name": "🪽 Mồi cánh gió", "type": "Thường", "price": 100, "desc": "Tăng 5% tỷ lệ câu cá thường"},
        {"id": "b2", "name": "✨ Mồi sao", "type": "Hiếm", "price": 200, "desc": "+10% câu thành công, +10% cá hiếm"},
        {"id": "b3", "name": "🌛 Mồi mặt trăng", "type": "Hiếm", "price": 10000, "desc": "-30% câu thành công, +10% cá thần thoại"},
        {"id": "b4", "name": "🥞 Mồi susanoo", "type": "Sử thi", "price": 11000, "desc": "+20% câu thành công, +20% cá sử thi"},
        {"id": "b5", "name": "👀 Mồi mắt Gorgon", "type": "Sử thi", "price": 15000, "desc": "+50% thành công, +15% cá hiếm & sử thi"},
        {"id": "b6", "name": "🐋 Mồi cá voi xanh", "type": "Thần thoại", "price": 16000, "desc": "+2% tỷ lệ thành công vĩnh viễn"},
        {"id": "b7", "name": "🌎 Mồi tinh cầu", "type": "Thần thoại", "price": 20000, "desc": "+50% thành công, +10% cá thần thoại"},
        {"id": "b8", "name": "🧜 Mồi nàng tiên cá", "type": "Thần thoại", "price": 20000, "desc": "+40% thành công, +5% cá thần thoại"},
        {"id": "b9", "name": "🎁 Mồi may mắn", "type": "Hỗn độn", "price": 100000, "desc": "50% Tăng cực lớn / 50% Giảm cực lớn hên xui"}
    ],
    "rod": [
        {"id": "r1", "name": "🥖 Cần bánh mì", "type": "Thường", "price": 10, "desc": "Cần cơ bản"},
        {"id": "r2", "name": "⚡ Cần sét", "type": "Hiếm", "price": 100, "desc": "Cần câu nhanh nhẹn"},
        {"id": "r3", "name": "🫏 Cần mèo", "type": "Hiếm", "price": 200, "desc": "Cần dễ thương"},
        {"id": "r4", "name": "🔥 Cần lửa", "type": "Hiếm", "price": 1000, "desc": "+3% tỷ lệ thành công"},
        {"id": "r5", "name": "🥶 Cần băng", "type": "Sử thi", "price": 10000, "desc": "+5% thành công, +4% cá sử thi/hiếm"},
        {"id": "r6", "name": "👺 Cần quỷ", "type": "Sử thi", "price": 20000, "desc": "+9% thành công, +10% cá thần thoại"},
        {"id": "r7", "name": "👑 Cần vua", "type": "Thần thoại", "price": 30000, "desc": "+15% thành công, +15% cá thần thoại"},
        {"id": "r8", "name": "🫯 Bom nguyên tử", "type": "Hư vô", "price": 33000, "desc": "+1% câu cá hư vô"}
    ],
    "food": [
        {"id": "f1", "name": "🍑 Đào lumi", "type": "Thường", "price": 20, "exp": 10, "cp": 0},
        {"id": "f2", "name": "🌹 Hoa furina", "type": "Thường", "price": 200, "exp": 100, "cp": 0},
        {"id": "f3", "name": "🍖 Thịt hổ", "type": "Thường", "price": 600, "exp": 300, "cp": 0},
        {"id": "f4", "name": "🍄 Nấm chaac", "type": "Hiếm", "price": 1500, "exp": 600, "cp": 10},
        {"id": "f5", "name": "🥬 Ravena", "type": "Hiếm", "price": 1450, "exp": 500, "cp": 0},
        {"id": "f6", "name": "🧅 Thái âm dương quả", "type": "Sử thi", "price": 2000, "exp": 1000, "cp": 0},
        {"id": "f7", "name": "🌕 Cửu diệp thảo quả", "type": "Sử thi", "price": 2300, "exp": 1100, "cp": 0},
        {"id": "f8", "name": "💀 Linh tủy quả", "type": "Sử thi", "price": 5000, "exp": 0, "cp": 100},
        {"id": "f9", "name": "🌏 Hỗn độn thanh liên Quả", "type": "Thần thoại", "price": 20000, "exp": 10000, "cp": 0},
        {"id": "f10", "name": "🐦‍🔥 Bất tử phượng hoàng quả", "type": "Thần thoại", "price": 30000, "exp": 1000, "cp": 1000}
    ],
    "equip": [
        {"id": "e1", "name": "🖕 Chi dục", "type": "Hỗn độn", "price": 100000, "desc": "Tăng 50% tỷ lệ thắng PVP"},
        {"id": "e2", "name": "🫸 Bình tĩnh", "type": "Hỗn độn", "price": 100000, "desc": "Giảm khả năng giảm sát thương Boss -30%"},
        {"id": "e3", "name": "🌀 Tịnh diệt kiếm ý", "type": "Thần thoại", "price": 50000, "desc": "+1000 Lực chiến vĩnh viễn"},
        {"id": "e4", "name": "🌚 Cửu u minh kiếm", "type": "Thần thoại", "price": 55000, "desc": "+2000 Lực chiến vĩnh viễn"},
        {"id": "e5", "name": "🔪 Pháp tắc chi nhân", "type": "Thần thoại", "price": 80000, "desc": "+5000 Lực chiến vĩnh viễn"},
        {"id": "e6", "name": "🔫 Súng XXX ZZZ", "type": "???", "price": 150000, "desc": "50% cơ hội tăng +10000 Lực chiến"}
    ]
}

TOWER_FLOORS = [
    {"floor": 1, "name": "👾 Quái nhỏ", "cp": 500, "reward_p": 100, "reward_exp": 20, "dmg_red": 0, "req_rarity": None},
    {"floor": 2, "name": "🧌 Zombie vua", "cp": 1000, "reward_p": 120, "reward_exp": 40, "dmg_red": 0, "req_rarity": None},
    {"floor": 3, "name": "🧛 Ma cà rồng", "cp": 3000, "reward_p": 200, "reward_exp": 100, "dmg_red": 0, "req_rarity": None},
    {"floor": 4, "name": "🩸 Lucifer", "cp": 5000, "reward_p": 300, "reward_exp": 300, "dmg_red": 0, "req_rarity": None},
    {"floor": 5, "name": "🫀 Abaddon", "cp": 10000, "reward_p": 320, "reward_exp": 310, "dmg_red": 0, "req_rarity": None},
    {"floor": 6, "name": "🐲 Leviathan", "cp": 15000, "reward_p": 1000, "reward_exp": 500, "dmg_red": 0, "req_rarity": None},
    {"floor": 7, "name": "🪐 Bàn cổ", "cp": 30000, "reward_p": 3000, "reward_exp": 1000, "dmg_red": 0.60, "req_rarity": None},
    {"floor": 8, "name": "🧿 Samyaza", "cp": 50000, "reward_p": 4000, "reward_exp": 2000, "dmg_red": 0.55, "req_rarity": ["Sử thi", "Thần thoại", "Hư vọng"], "title": "Chân nhân"},
    {"floor": 9, "name": "🪬 Kokabiel", "cp": 80000, "reward_p": 6000, "reward_exp": 3000, "dmg_red": 0.70, "req_rarity": ["Thần thoại", "Hư vọng"], "title": "Sáng thế nhân"},
    {"floor": 10, "name": "📿🪦🕧 ???", "cp": 100000, "reward_p": 100000, "reward_exp": 100000, "dmg_red": 1.00, "req_rarity": ["Thần thoại", "Hư vọng"], "title": "???"},
    {"floor": 11, "name": "💀 Admin", "cp": 999999999999, "reward_p": 1, "reward_exp": 1, "dmg_red": 0, "req_rarity": None, "title": "Tiểu Admin tối cao"}
]

# ==========================================
# HELPER CALCULATIONS
# ==========================================
def calc_pet_stats(pet_dict):
    pet_type = pet_dict["type"]
    level = pet_dict["level"]
    exp = pet_dict["exp"]
    bonus_cp = pet_dict.get("bonus_cp", 0)

    base_info = BASE_PETS.get(pet_type)
    if not base_info:
        return {"name": pet_dict.get("custom_name", "Pet Cổ Đại"), "level": level, "cp": 100 + bonus_cp, "rarity": "Đặc biệt"}

    stat_base = base_info["stat_base"]
    stat_high = base_info["stat_high"]
    
    if level < 20:
        cp = level * stat_base
    else:
        cp = (19 * stat_base) + ((level - 19) * stat_high)

    cp += bonus_cp

    stages = base_info["stages"]
    if level == 1:
        stage_name = stages[0]["name"]
    elif level == 2:
        stage_name = stages[1]["name"]
    elif level == 3:
        stage_name = stages[2]["name"]
    else:
        stage_name = f"{stages[2]['name']} [Cấp {level}]"

    return {
        "name": stage_name,
        "level": level,
        "exp": exp,
        "cp": cp,
        "rarity": base_info["rarity"]
    }

def get_required_exp(pet_type, level):
    base_info = BASE_PETS.get(pet_type)
    if not base_info:
        return 1000 * level
    stages = base_info["stages"]
    if level == 1:
        return stages[0]["max_exp"]
    elif level == 2:
        return stages[1]["max_exp"]
    elif level == 3:
        return stages[2]["max_exp"]
    else:
        prev_exp = get_required_exp(pet_type, level - 1)
        return int((prev_exp / 2) * level)

# ==========================================
# A. PET SYSTEM & EMBEDS
# ==========================================
class PetSystemView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = str(user_id)

    @discord.ui.button(label="🎲 Quay Pet (100 Đ)", style=discord.ButtonStyle.primary, custom_id="btn_gacha_pet")
    async def gacha_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = db_get_user(interaction.user.id)
        if user["points"] < 100:
            return await interaction.response.send_message("❌ Bạn không đủ 100 điểm để quay Pet!", ephemeral=True)

        db_update_user(interaction.user.id, points=user["points"] - 100)
        
        roll_list = [
            ("diathien", 0.1), ("phuonghoang", 1.0), ("rong", 1.0),
            ("kilan", 10.0), ("daibang", 20.0), ("camap", 50.0),
            ("gautruc", 50.0), ("gau", 70.0), ("sutu", 70.0)
        ]
        
        selected = "sutu"
        for key, rate in roll_list:
            if random.random() * 100 <= rate:
                selected = key
                break

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO pets (user_id, type, level, exp, bonus_cp) VALUES (?, ?, 1, 0, 0)", (str(interaction.user.id), selected))
        pet_id = c.lastrowid
        conn.commit()
        conn.close()

        if user["active_pet_idx"] is None:
            db_update_user(interaction.user.id, active_pet_idx=pet_id)

        pet_info = calc_pet_stats({"type": selected, "level": 1, "exp": 0, "bonus_cp": 0})
        embed = discord.Embed(
            title="🎉 BẠN ĐÃ QUAY RA PET MỚI!",
            description=f"Chúc mừng bạn thu phục được **{pet_info['name']}**!\n• **Phẩm chất:** {pet_info['rarity']}\n• **Lực chiến ban đầu:** {pet_info['cp']} CP",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Số điểm còn lại: {user['points'] - 100} điểm")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚙️ Update Pet (Admin)", style=discord.ButtonStyle.danger, custom_id="btn_update_pet")
    async def update_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Chỉ Admin mới có quyền sử dụng chức năng này!", ephemeral=True)
        await interaction.response.send_modal(AddPetModal())

class AddPetModal(discord.ui.Modal, title="Thêm Pet Mới Vào System"):
    pet_name = discord.ui.TextInput(label="Tên Pet", placeholder="VD: Rồng Băng Con")
    rarity = discord.ui.TextInput(label="Phẩm chất", placeholder="Thường / Hiếm / Sử thi / Thần thoại / Hư vọng")
    rate = discord.ui.TextInput(label="Tỉ lệ ra (%)", placeholder="VD: 5.0")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            r_val = float(self.rate.value)
        except ValueError:
            return await interaction.response.send_message("❌ Tỉ lệ phải là số!", ephemeral=True)

        custom_pets = get_config("custom_pets", [])
        custom_pets.append({"name": self.pet_name.value, "rarity": self.rarity.value, "rate": r_val})
        set_config("custom_pets", custom_pets)

        await interaction.response.send_message(f"✅ Đã thêm Pet **{self.pet_name.value}** thành công vào hệ thống!", ephemeral=True)

# ==========================================
# B. PVP PET SYSTEM
# ==========================================
class PVPConfirmView(discord.ui.View):
    def __init__(self, challenger: discord.Member, target: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.target = target

    @discord.ui.button(label="⚔️ Chấp Nhận Thách Đấu", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ Bạn không phải là người được thách đấu!", ephemeral=True)

        u1 = db_get_user(self.challenger.id)
        u2 = db_get_user(self.target.id)

        pets1 = db_get_user_pets(self.challenger.id)
        pets2 = db_get_user_pets(self.target.id)

        active_p1 = next((p for p in pets1 if p["pet_id"] == u1["active_pet_idx"]), None) if pets1 else None
        active_p2 = next((p for p in pets2 if p["pet_id"] == u2["active_pet_idx"]), None) if pets2 else None

        if not active_p1:
            return await interaction.response.send_message("❌ Người thách đấu không có Pet xuất chiến!", ephemeral=True)
        if not active_p2:
            return await interaction.response.send_message("❌ Bạn chưa chọn Pet xuất chiến!", ephemeral=True)

        p1 = calc_pet_stats(active_p1)
        p2 = calc_pet_stats(active_p2)

        cp1 = p1["cp"]
        cp2 = p2["cp"]

        diff = cp1 - cp2
        if diff == 0: win_rate_1 = 0.50
        elif 1 <= diff <= 3000: win_rate_1 = 0.60
        elif -3000 <= diff <= -1: win_rate_1 = 0.40
        elif 3000 < diff < 10000: win_rate_1 = 0.70
        elif -10000 < diff < -3000: win_rate_1 = 0.30
        elif diff >= 10000: win_rate_1 = 1.00
        else: win_rate_1 = 0.00

        if u1.get("equipped_pet_item") == "e1": win_rate_1 = min(1.0, win_rate_1 + 0.50)
        if u2.get("equipped_pet_item") == "e1": win_rate_1 = max(0.0, win_rate_1 - 0.50)

        roll = random.random()
        winner = self.challenger if roll <= win_rate_1 else self.target

        embed = discord.Embed(title="⚔️ KẾT QUẢ TRẬN ĐẤU PET PVP ⚔️", color=discord.Color.red())
        embed.add_field(name=f"🎮 {self.challenger.display_name}", value=f"Pet: **{p1['name']}**\nCP: **{cp1}**", inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        embed.add_field(name=f"🎮 {self.target.display_name}", value=f"Pet: **{p2['name']}**\nCP: **{cp2}**", inline=True)
        embed.add_field(name="🏆 CHIẾN THẮNG", value=f"Chúc mừng **{winner.mention}** đã giành chiến thắng chung cuộc!", inline=False)

        await interaction.response.edit_message(content=None, embed=embed, view=None)

    @discord.ui.button(label="🏳️ Từ Chối", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ Bạn không phải là người được thách đấu!", ephemeral=True)
        await interaction.response.edit_message(content=f"❌ {self.target.mention} đã từ chối lời thách đấu!", embed=None, view=None)

import os
import json
import time
import random
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==========================================
# C. FISHING SYSTEM (/causong)
# ==========================================
class FishingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎣 Câu Cá", style=discord.ButtonStyle.primary, custom_id="btn_do_fishing")
    async def do_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        user = db_get_user(user_id)
        inv = db_get_inventory(user_id)
        
        bait_id = user.get("equipped_bait")
        rod_id = user.get("equipped_rod")

        # Kiểm tra mồi câu trong túi đồ
        if bait_id:
            if inv.get(bait_id, 0) <= 0:
                # Tự động tháo mồi nếu đã hết
                db_update_user(user_id, equipped_bait=None)
                return await interaction.response.send_message("❌ Bạn đã hết mồi câu đang trang bị! Vui lòng mua hoặc trang bị mồi mới.", ephemeral=True)
            # Trừ 1 mồi câu khi sử dụng
            db_add_inventory(user_id, bait_id, -1)

        base_success = 0.45
        bonus_success = 0
        bonus_rare = 0
        bonus_epic = 0
        bonus_myth = 0

        # Chỉ số Cần Câu
        if rod_id == "r4": bonus_success += 0.03
        elif rod_id == "r5": bonus_success += 0.05; bonus_epic += 0.04
        elif rod_id == "r6": bonus_success += 0.09; bonus_myth += 0.10
        elif rod_id == "r7": bonus_success += 0.15; bonus_myth += 0.15

        # Chỉ số Mồi Câu
        if bait_id == "b1": pass
        elif bait_id == "b2": bonus_success += 0.10; bonus_rare += 0.10
        elif bait_id == "b3": bonus_success -= 0.30; bonus_myth += 0.10
        elif bait_id == "b4": bonus_success += 0.20; bonus_epic += 0.20
        elif bait_id == "b5": bonus_success += 0.50; bonus_rare += 0.15; bonus_epic += 0.15
        elif bait_id == "b6": bonus_success += 0.02
        elif bait_id == "b7": bonus_success += 0.50; bonus_myth += 0.10
        elif bait_id == "b8": bonus_success += 0.40; bonus_myth += 0.05
        elif bait_id == "b9":
            if random.random() <= 0.5:
                bonus_success += 1.00; bonus_myth += 0.40
            else:
                bonus_success -= 1.00; bonus_myth -= 0.40

        total_success = max(0.05, min(1.0, base_success + bonus_success))

        # Xử lý khi giật thất bại
        if random.random() > total_success:
            embed = discord.Embed(
                title="🎣 CÂU CÁ THẤT BẠI!", 
                description="💥 Rất tiếc, dây câu của bạn đã bị đứt!", 
                color=discord.Color.dark_grey()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Danh sách Cá mặc định
        fishes = [
            {"name": "🐟 Cá Rô Đồng", "type": "Thường", "pts": 10, "rate": 50},
            {"name": "🐠 Cá Chép Vàng", "type": "Thường", "pts": 10, "rate": 50},
            {"name": "🦈 Cá Tầm", "type": "Thường", "pts": 10, "rate": 50},
            {"name": "🐧 Chim Cút", "type": "Thường", "pts": 20, "rate": 50},
            {"name": "👞 Giày Cũ Bị Rách", "type": "Xui xẻo", "pts": -100, "rate": 40},
            {"name": "👑 Rương Báu Dưới Sông", "type": "Hiếm", "pts": 100, "rate": 40},
            {"name": "🐙 Bạch tuộc", "type": "Hiếm", "pts": 60, "rate": 40},
            {"name": "🐢 Rùa con", "type": "Hiếm", "pts": 70, "rate": 40},
            {"name": "🦭 Tiểu long cẩu", "type": "Sử thi", "pts": 200, "rate": 20},
            {"name": "🦞 Tôm suki", "type": "Sử thi", "pts": 210, "rate": 19},
            {"name": "⭐ Light suki", "type": "Sử thi", "pts": 220, "rate": 15},
            {"name": "🫍 Cá voi sát thần", "type": "Thần thoại", "pts": 500, "rate": 1, "title": "Sát long"},
            {"name": "🦠 Virut tử thần", "type": "Thần thoại", "pts": 1000, "rate": 0.5, "title": "Virut vương"},
            {"name": "🐉 Leviathan", "type": "Thần thoại", "pts": 2000, "rate": 0.1, "title": "Leviathan"},
            {"name": "🌑 Chân thiên tôn", "type": "Hư vô", "pts": 3000, "rate": 0.001, "title": "Thiên tôn"}
        ]

        # Lấy thêm cá tùy chỉnh từ config
        custom_fish = get_config("custom_fish", [])
        for cf in custom_fish:
            fishes.append({"name": cf["name"], "type": cf["rarity"], "pts": cf["pts"], "rate": cf["rate"], "title": cf.get("title")})

        caught = random.choices(fishes, weights=[f["rate"] for f in fishes], k=1)[0]
        
        new_pts = user["points"] + caught["pts"]
        db_update_user(user_id, points=new_pts)

        msg = f"Bạn đã câu được **{caught['name']}**!\n• **Phẩm cấp:** {caught['type']}\n• **Điểm:** {caught['pts']:+} điểm."
        
        user_titles = json.loads(user["titles"]) if user["titles"] else []
        if "title" in caught and caught["title"]:
            if caught["title"] not in user_titles:
                user_titles.append(caught["title"])
                db_update_user(user_id, titles=json.dumps(user_titles, ensure_ascii=False))
                msg += f"\n🎉 **NHẬN DANH HIỆU MỚI:** [{caught['title']}]"

        embed = discord.Embed(title="🎣 CÂU CÁ THÀNH CÔNG!", description=msg, color=discord.Color.blue())
        embed.set_footer(text=f"Tổng điểm hiện tại: {new_pts}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚙️ Thêm Cá (Admin)", style=discord.ButtonStyle.danger, custom_id="btn_add_fish")
    async def add_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Chỉ Admin mới có quyền sử dụng chức năng này!", ephemeral=True)
        await interaction.response.send_modal(AddFishModal())

class AddFishModal(discord.ui.Modal, title="Thêm Cá Mới Vào Hồ"):
    fish_name = discord.ui.TextInput(label="Tên Cá", placeholder="VD: Cá Rồng Hoàng Kim")
    rarity = discord.ui.TextInput(label="Phẩm cấp", placeholder="Thường / Hiếm / Sử thi / Thần thoại / Hư vô")
    rate = discord.ui.TextInput(label="Tỉ lệ ra (%)", placeholder="VD: 1.5")
    pts = discord.ui.TextInput(label="Điểm thưởng", placeholder="VD: 500")
    title = discord.ui.TextInput(label="Danh hiệu (Không bắt buộc)", required=False, placeholder="VD: Long Vương")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            r_val = float(self.rate.value)
            p_val = int(self.pts.value)
        except ValueError:
            return await interaction.response.send_message("❌ Tỉ lệ và điểm phải là số hợp lệ!", ephemeral=True)

        cfish = get_config("custom_fish", [])
        cfish.append({
            "name": self.fish_name.value, 
            "rarity": self.rarity.value, 
            "rate": r_val, 
            "pts": p_val, 
            "title": self.title.value if self.title.value else None
        })
        set_config("custom_fish", cfish)

        await interaction.response.send_message(f"✅ Đã thêm cá **{self.fish_name.value}** vào danh sách thành công!", ephemeral=True)

# ==========================================
# D. SHOP SYSTEM (/shop)
# ==========================================
class ShopMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎣 Cần & Mồi", style=discord.ButtonStyle.primary, custom_id="btn_shop_bait")
    async def shop_bait(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛒 CỬA HÀNG CẦN & MỒI CÂU", color=discord.Color.green())
        desc = "**--- MỒI CÂU ---**\n"
        for b in DEFAULT_SHOP["bait"]:
            desc += f"• **{b['name']}** ({b['type']}) - 💰 **{b['price']}đ**\n  *Tác dụng:* {b['desc']}\n"
        desc += "\n**--- CẦN CÂU ---**\n"
        for r in DEFAULT_SHOP["rod"]:
            desc += f"• **{r['name']}** ({r['type']}) - 💰 **{r['price']}đ**\n  *Tác dụng:* {r['desc']}\n"
        
        embed.description = desc
        await interaction.response.send_message(embed=embed, view=ShopBuySelectView("bait_rod"), ephemeral=True)

    @discord.ui.button(label="🍖 Đồ Ăn & Trang Bị Pet", style=discord.ButtonStyle.success, custom_id="btn_shop_pet")
    async def shop_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛒 CỬA HÀNG ĐỒ ĂN & TRANG BỊ PET", color=discord.Color.gold())
        desc = "**--- ĐỒ ĂN PET ---**\n"
        for f in DEFAULT_SHOP["food"]:
            desc += f"• **{f['name']}** ({f['type']}) - 💰 **{f['price']}đ**\n  *Tác dụng:* +{f['exp']} EXP, +{f['cp']} CP\n"
        desc += "\n**--- TRANG BỊ PET ---**\n"
        for e in DEFAULT_SHOP["equip"]:
            desc += f"• **{e['name']}** ({e['type']}) - 💰 **{e['price']}đ**\n  *Tác dụng:* {e['desc']}\n"
        
        embed.description = desc
        await interaction.response.send_message(embed=embed, view=ShopBuySelectView("food_equip"), ephemeral=True)

    @discord.ui.button(label="⚙️ Update Đồ Shop (Admin)", style=discord.ButtonStyle.danger, custom_id="btn_shop_admin")
    async def shop_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Chỉ Admin mới có quyền sử dụng chức năng này!", ephemeral=True)
        await interaction.response.send_modal(AddShopItemModal())

class ShopBuySelectView(discord.ui.View):
    def __init__(self, category):
        super().__init__(timeout=60)
        options = []
        if category == "bait_rod":
            for item in DEFAULT_SHOP["bait"] + DEFAULT_SHOP["rod"]:
                options.append(discord.SelectOption(label=item["name"], value=item["id"], description=f"{item['price']} điểm"))
        else:
            for item in DEFAULT_SHOP["food"] + DEFAULT_SHOP["equip"]:
                options.append(discord.SelectOption(label=item["name"], value=item["id"], description=f"{item['price']} điểm"))

        select = discord.ui.Select(placeholder="Chọn món đồ bạn muốn mua...", options=options[:25])
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        item_id = interaction.data["values"][0]
        user = db_get_user(interaction.user.id)

        all_items = DEFAULT_SHOP["bait"] + DEFAULT_SHOP["rod"] + DEFAULT_SHOP["food"] + DEFAULT_SHOP["equip"]
        target = next((x for x in all_items if x["id"] == item_id), None)

        if not target:
            return await interaction.response.send_message("❌ Vật phẩm không tồn tại!", ephemeral=True)

        if user["points"] < target["price"]:
            return await interaction.response.send_message("❌ Bạn không đủ điểm để mua vật phẩm này!", ephemeral=True)

        db_update_user(interaction.user.id, points=user["points"] - target["price"])
        db_add_inventory(interaction.user.id, item_id, 1)

        await interaction.response.send_message(f"🎉 Bạn đã mua thành công **{target['name']}** với giá **{target['price']}** điểm!", ephemeral=True)

class AddShopItemModal(discord.ui.Modal, title="Thêm Vật Phẩm Vào Shop"):
    shop_type = discord.ui.TextInput(label="Loại (bait / rod / food / equip)", placeholder="Điền 1 trong 4 loại trên")
    item_name = discord.ui.TextInput(label="Tên Vật Phẩm", placeholder="VD: Siêu Mồi Rồng")
    price = discord.ui.TextInput(label="Giá Điểm", placeholder="VD: 50000")
    effect = discord.ui.TextInput(label="Mô tả Hiệu Ứng", placeholder="VD: Tăng 20% tỉ lệ câu cá hư vô")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            p_val = int(self.price.value)
        except ValueError:
            return await interaction.response.send_message("❌ Giá tiền phải là số!", ephemeral=True)

        st = self.shop_type.value.strip().lower()
        if st not in ["bait", "rod", "food", "equip"]:
            return await interaction.response.send_message("❌ Loại vật phẩm không hợp lệ!", ephemeral=True)

        new_item = {
            "id": f"custom_{random.randint(1000, 9999)}", 
            "name": self.item_name.value, 
            "type": "Custom", 
            "price": p_val, 
            "desc": self.effect.value
        }
        DEFAULT_SHOP[st].append(new_item)

        await interaction.response.send_message(f"✅ Đã thêm **{self.item_name.value}** vào Cửa hàng!", ephemeral=True)

# ==========================================
# E. INVENTORY & EQUIPMENT MENU WITH PAGINATION
# ==========================================
class InventoryPaginatedView(discord.ui.View):
    def __init__(self, user_id, inv_dict):
        super().__init__(timeout=120)
        self.user_id = str(user_id)
        self.inv_dict = inv_dict
        self.page = 0
        self.items_per_page = 5
        self.item_keys = list(inv_dict.keys())
        self.max_pages = max(1, (len(self.item_keys) + self.items_per_page - 1) // self.items_per_page)

    def get_page_embed(self):
        user = db_get_user(self.user_id)
        user_obj = bot.get_user(int(self.user_id))
        display_name = user_obj.display_name if user_obj else "Người chơi"
        
        embed = discord.Embed(title=f"🎒 TÚI ĐỒ CỦA {display_name}", color=discord.Color.blue())
        embed.add_field(name="💰 Điểm hiện có", value=f"**{user['points']}** điểm", inline=True)

        # Trạng thái trang bị
        rod_name = next((r["name"] for r in DEFAULT_SHOP["rod"] if r["id"] == user["equipped_rod"]), "Chưa trang bị")
        bait_name = next((b["name"] for b in DEFAULT_SHOP["bait"] if b["id"] == user["equipped_bait"]), "Chưa trang bị")
        equip_name = next((e["name"] for e in DEFAULT_SHOP["equip"] if e["id"] == user["equipped_pet_item"]), "Chưa trang bị")

        embed.add_field(name="🛡️ Trang Bị Đang Kích Hoạt", value=f"• Cần câu: **{rod_name}**\n• Mồi câu: **{bait_name}**\n• Vật phẩm Pet: **{equip_name}**", inline=False)

        # Phân trang
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_keys = self.item_keys[start:end]

        all_shop = DEFAULT_SHOP["bait"] + DEFAULT_SHOP["rod"] + DEFAULT_SHOP["food"] + DEFAULT_SHOP["equip"]
        
        desc = ""
        for k in current_keys:
            item_info = next((x for x in all_shop if x["id"] == k), None)
            name = item_info["name"] if item_info else k
            desc += f"• **{name}**: {self.inv_dict[k]} cái\n"

        embed.add_field(name=f"📦 Danh Sách Vật Phẩm (Trang {self.page + 1}/{self.max_pages})", value=desc if desc else "Không có vật phẩm nào ở trang này.", inline=False)
        return embed

    @discord.ui.button(label="◀ Trang Trước", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.send_message("Bạn đang ở trang đầu tiên!", ephemeral=True)

    @discord.ui.button(label="Trang Sau ▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_pages - 1:
            self.page += 1
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.send_message("Bạn đang ở trang cuối cùng!", ephemeral=True)

    @discord.ui.button(label="⚙️ Đeo / Tháo Trang Bị", style=discord.ButtonStyle.primary)
    async def equip_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = db_get_user(interaction.user.id)
        all_equippables = DEFAULT_SHOP["bait"] + DEFAULT_SHOP["rod"] + DEFAULT_SHOP["equip"]
        owned = [x for x in all_equippables if self.inv_dict.get(x["id"], 0) > 0]

        if not owned:
            return await interaction.response.send_message("❌ Bạn không sở hữu Cần câu, Mồi hoặc Trang bị nào để đeo!", ephemeral=True)

        options = [discord.SelectOption(label=x["name"], value=x["id"], description=f"Loại: {x['type']}") for x in owned]
        view = discord.ui.View()
        select = discord.ui.Select(placeholder="Chọn trang bị muốn Đeo/Tháo...", options=options[:25])

        async def select_equip_cb(inter: discord.Interaction):
            item_id = inter.data["values"][0]
            item = next(x for x in all_equippables if x["id"] == item_id)

            if item_id.startswith("r"): # Rod
                new_val = None if user["equipped_rod"] == item_id else item_id
                db_update_user(inter.user.id, equipped_rod=new_val)
            elif item_id.startswith("b"): # Bait
                new_val = None if user["equipped_bait"] == item_id else item_id
                db_update_user(inter.user.id, equipped_bait=new_val)
            elif item_id.startswith("e"): # Equip
                new_val = None if user["equipped_pet_item"] == item_id else item_id
                db_update_user(inter.user.id, equipped_pet_item=new_val)

            status = "Tháo" if new_val is None else "Đeo"
            await inter.response.send_message(f"✅ Đã **{status}** thành công trang bị **{item['name']}**!", ephemeral=True)

        select.callback = select_equip_cb
        view.add_item(select)
        await interaction.response.send_message("⚙️ **MENU TRANG BỊ:**", view=view, ephemeral=True)

# ==========================================
# F. SLASH COMMANDS & ANTI-SPAM COOLDOWNS
# ==========================================
@bot.tree.command(name="nuoithu", description="Mở bảng điều khiển nuôi thú ảo")
async def nuoithu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🐾 HỆ THỐNG NUÔI THÚ ẢO",
        description="Chào mừng bạn đến với thế giới Thú Cưng! Tại đây bạn có thể quay Pet, nâng cấp và nuôi dưỡng linh thú của mình.",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed, view=PetSystemView(interaction.user.id))

@bot.tree.command(name="pvp_pet", description="Thách đấu Pet với người chơi khác")
async def pvp_pet(interaction: discord.Interaction, target: discord.Member):
    if target.id == interaction.user.id:
        return await interaction.response.send_message("❌ Bạn không thể tự thách đấu chính mình!", ephemeral=True)

    embed = discord.Embed(
        title="⚔️ LỜI THÁCH ĐẤU PET ⚔️",
        description=f"{interaction.user.mention} vừa gửi lời thách đấu Pet tới {target.mention}!\nBạn có đồng ý chấp nhận trận chiến này không?",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(content=target.mention, embed=embed, view=PVPConfirmView(interaction.user, target))

@bot.tree.command(name="leothap", description="Khiêu chiến Tháp Thử Thách")
async def leothap(interaction: discord.Interaction):
    user = db_get_user(interaction.user.id)
    pets = db_get_user_pets(interaction.user.id)

    active_p = next((p for p in pets if p["pet_id"] == user["active_pet_idx"]), None) if pets else None
    if not active_p:
        return await interaction.response.send_message("❌ Bạn cần chọn Pet xuất chiến mới có thể leo tháp!", ephemeral=True)

    p_info = calc_pet_stats(active_p)

    options = []
    for f in TOWER_FLOORS:
        options.append(discord.SelectOption(label=f"Tầng {f['floor']}: {f['name']}", value=str(f["floor"]), description=f"CP: {f['cp']} | Thưởng: {f['reward_p']}đ"))

    view = discord.ui.View()
    select = discord.ui.Select(placeholder="Chọn Tầng Tháp Muốn Khiêu Chiến...", options=options)

    async def tower_callback(inter: discord.Interaction):
        floor_num = int(inter.data["values"][0])
        floor = next(x for x in TOWER_FLOORS if x["floor"] == floor_num)

        if floor["req_rarity"]:
            if p_info["rarity"] not in floor["req_rarity"]:
                return await inter.response.send_message(f"❌ Boss tầng này yêu cầu Pet phải có phẩm chất **{', '.join(floor['req_rarity'])}** mới có thể đánh!", ephemeral=True)

        player_cp = p_info["cp"]
        effective_dmg_red = max(0, floor["dmg_red"] - 0.30) if user.get("equipped_pet_item") == "e2" else floor["dmg_red"]
        final_player_cp = player_cp * (1.0 - effective_dmg_red)

        if final_player_cp >= floor["cp"]:
            db_update_user(inter.user.id, points=user["points"] + floor["reward_p"])
            
            # Cập nhật Exp
            new_exp = active_p["exp"] + floor["reward_exp"]
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE pets SET exp = ? WHERE pet_id = ?", (new_exp, active_p["pet_id"]))
            conn.commit()
            conn.close()

            user_titles = json.loads(user["titles"]) if user["titles"] else []
            msg_title = ""
            if "title" in floor and floor["title"]:
                if floor["title"] not in user_titles:
                    user_titles.append(floor["title"])
                    db_update_user(inter.user.id, titles=json.dumps(user_titles, ensure_ascii=False))
                    msg_title = f"\n🏆 **BẠN NHẬN ĐƯỢC DANH HIỆU MỚI:** [{floor['title']}]"

            embed = discord.Embed(
                title=f"⚔️ CHIẾN THẮNG TẦNG {floor['floor']}!",
                description=f"Pet **{p_info['name']}** (Lực chiến hiệu quả: **{int(final_player_cp)}**) đã đánh bại **{floor['name']}**!\n• **Phần thưởng:** +{floor['reward_p']} điểm, +{floor['reward_exp']} EXP.{msg_title}",
                color=discord.Color.green()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title=f"💀 THẤT BẠI TẦNG {floor['floor']}!",
                description=f"Lực chiến hiệu quả của Pet (**{int(final_player_cp)}**) không đủ để vượt qua **{floor['name']}** (Lực chiến **{floor['cp']}**).",
                color=discord.Color.red()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)

    select.callback = tower_callback
    view.add_item(select)
    await interaction.response.send_message("📌 **THÁP THỬ THÁCH:**", view=view, ephemeral=True)

@bot.tree.command(name="causong", description="Mở giao diện câu cá sông")
async def causong(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌊 CÂU CÁ BÊN SÔNG 🎣",
        description="Hãy chuẩn bị cần câu & mồi để săn các loài cá quý hiếm và danh hiệu cao quý!",
        color=discord.Color.teal()
    )
    await interaction.response.send_message(embed=embed, view=FishingView())

@bot.tree.command(name="shop", description="Mở cửa hàng vật phẩm (Không thời hạn)")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏬 CỬA HÀNG TỔNG HỢP",
        description="Hãy chọn phân loại mặt hàng bạn muốn mua bên dưới:",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=ShopMainView())

@bot.tree.command(name="tuido", description="Xem điểm số, Pet và vật phẩm cá nhân (Có phân trang)")
async def tuido(interaction: discord.Interaction):
    inv_dict = db_get_inventory(interaction.user.id)
    view = InventoryPaginatedView(interaction.user.id, inv_dict)
    await interaction.response.send_message(embed=view.get_page_embed(), view=view, ephemeral=True)

@bot.tree.command(name="bangxephang", description="Xem Bảng Xếp Hạng Đại Gia")
async def bangxephang(interaction: discord.Interaction):
    lb_ids = get_config("lb_channel_ids", [])
    if interaction.channel_id not in lb_ids:
        lb_ids.append(interaction.channel_id)
        set_config("lb_channel_ids", lb_ids)

    embed = await build_leaderboard_embed()
    await interaction.response.send_message(embed=embed)

async def build_leaderboard_embed():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()

    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG TÀI PHÚ 🏆", color=discord.Color.gold())
    titles = get_config("top_titles", {
        "top1": {"title": "Khư quỷ", "color": "🔴"},
        "top2": {"title": "Khu la", "color": "🟠"},
        "top3": {"title": "Thế thần", "color": "🟡"}
    })

    desc = ""
    for idx, r in enumerate(rows, 1):
        t_str = ""
        if idx == 1: t_str = f" [{titles['top1']['color']} {titles['top1']['title']}]"
        elif idx == 2: t_str = f" [{titles['top2']['color']} {titles['top2']['title']}]"
        elif idx == 3: t_str = f" [{titles['top3']['color']} {titles['top3']['title']}]"

        desc += f"**#{idx}** <@{r['user_id']}>{t_str} — 💰 **{r['points']}** điểm\n"

    embed.description = desc if desc else "Chưa có dữ liệu người chơi."
    embed.set_footer(text="Tự động cập nhật vào 06:00 sáng hàng ngày!")
    return embed

@bot.tree.command(name="cuop", description="Thực hiện phi vụ cướp điểm ngẫu nhiên")
@app_commands.checks.cooldown(1, 30.0, key=lambda i: (i.guild_id, i.user.id))
async def cuop(interaction: discord.Interaction, target: discord.Member):
    if target.id == interaction.user.id:
        return await interaction.response.send_message("❌ Bạn không thể tự cướp chính mình!", ephemeral=True)

    u1 = db_get_user(interaction.user.id)
    u2 = db_get_user(target.id)

    if u2["points"] <= 0:
        return await interaction.response.send_message("❌ Nạn nhân đã cạn kiệt tài sản, không thể cướp!", ephemeral=True)

    if random.random() <= 0.45:
        stolen = u2["points"] if random.random() <= 0.05 else random.randint(10, min(1000, u2["points"]))
        db_update_user(target.id, points=u2["points"] - stolen)
        db_update_user(interaction.user.id, points=u1["points"] + stolen)

        embed = discord.Embed(title="🥷 CƯỚP THÀNH CÔNG!", description=f"Bạn đã cướp thành công **{stolen}** điểm từ {target.mention}!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    else:
        fine = random.randint(10, 1000)
        db_update_user(interaction.user.id, points=u1["points"] - fine)
        db_update_user(target.id, points=u2["points"] + fine)

        embed = discord.Embed(title="🚨 BỊ BẮT RỒI!", description=f"Phi vụ thất bại! Bạn bị phạt **{fine}** điểm đền bù trực tiếp cho {target.mention}!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="taixiu", description="Đặt cược Tài Xỉu gấp đôi tiền thưởng")
@app_commands.choices(choice=[
    app_commands.Choice(name="Tài 🎲", value="tai"),
    app_commands.Choice(name="Xỉu 🎲", value="xiu")
])
@app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
async def taixiu(interaction: discord.Interaction, amount: int, choice: app_commands.Choice[str]):
    user = db_get_user(interaction.user.id)
    if amount <= 0:
        return await interaction.response.send_message("❌ Số điểm cược phải lớn hơn 0!", ephemeral=True)
    if user["points"] < amount * 2:
        return await interaction.response.send_message("❌ Bạn phải có ít nhất x2 số tiền cược để đề phòng rủi ro!", ephemeral=True)

    res = random.choice(["tai", "xiu"])
    if choice.value == res:
        win_amt = amount * 2
        db_update_user(interaction.user.id, points=user["points"] + win_amt)
        msg = f"🎉 Kết quả là **{res.upper()}**! Bạn đã THẮNG và nhận được **+{win_amt}** điểm!"
        color = discord.Color.green()
    else:
        loss_amt = amount * 2
        db_update_user(interaction.user.id, points=user["points"] - loss_amt)
        msg = f"💥 Kết quả là **{res.upper()}**! Bạn đã THUA và bị trừ **-{loss_amt}** điểm!"
        color = discord.Color.red()

    embed = discord.Embed(title="🎲 KẾT QUẢ TÀI XỈU 🎲", description=msg, color=color)
    embed.set_footer(text=f"Điểm còn lại: {db_get_user(interaction.user.id)['points']}")
    await interaction.response.send_message(embed=embed)

# Error Handler cho Cooldown
@taixiu.error
@cuop.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Thao tác quá nhanh! Vui lòng chờ `{error.retry_after:.1f}s` nữa để tiếp tục.", ephemeral=True)

import os
import json
import time
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==========================================
# 0. BOT & DATABASE INITIALIZATION
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

DB_PATH = "bot_data.db"

def get_db():
    # Thêm timeout=10.0 để tránh lỗi 'database is locked' khi chat và voice ghi đồng thời
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    # Bật chế độ WAL giúp vừa đọc vừa ghi dữ liệu mượt mà hơn
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0,
            equipped_rod TEXT,
            equipped_bait TEXT,
            equipped_pet_item TEXT,
            active_pet_idx INTEGER,
            titles TEXT DEFAULT '[]'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_config(key, default=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return row["value"]
    return default

def set_config(key, value):
    conn = get_db()
    c = conn.cursor()
    val_str = json.dumps(value, ensure_ascii=False)
    c.execute("INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?", (key, val_str, val_str))
    conn.commit()
    conn.close()

def db_get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, points) VALUES (?, 1000)", (user_id,))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
    conn.close()
    return dict(row)

def db_update_user(user_id, **kwargs):
    conn = get_db()
    c = conn.cursor()
    fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    c.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

# ==========================================
# G. ADMIN MANAGEMENT COMMANDS
# ==========================================
@bot.tree.command(name="point_edit", description="[ADMIN] Cộng hoặc trừ điểm người chơi")
async def point_edit(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("⛔ Bạn không có quyền thực hiện lệnh này!", ephemeral=True)

    u = db_get_user(user.id)
    new_p = max(0, u["points"] + amount) # Đảm bảo điểm không bị âm
    db_update_user(user.id, points=new_p)

    await interaction.response.send_message(f"✅ Đã điều chỉnh điểm của {user.mention}: **{amount:+}** điểm (Tổng: **{new_p}**)", ephemeral=True)

@bot.tree.command(name="set_top_title", description="[ADMIN] Điều chỉnh danh hiệu Bảng Xếp Hạng")
async def set_top_title(interaction: discord.Interaction, top: int, title: str, color_icon: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("⛔ Bạn không có quyền thực hiện lệnh này!", ephemeral=True)

    if top not in [1, 2, 3]:
        return await interaction.response.send_message("❌ Top chỉ có thể là 1, 2 hoặc 3!", ephemeral=True)

    titles = get_config("top_titles", {
        "top1": {"title": "Khư quỷ", "color": "🔴"},
        "top2": {"title": "Khu la", "color": "🟠"},
        "top3": {"title": "Thế thần", "color": "🟡"}
    })
    titles[f"top{top}"] = {"title": title, "color": color_icon}
    set_config("top_titles", titles)

    await interaction.response.send_message(f"✅ Đã đổi danh hiệu Top {top} thành: {color_icon} **[{title}]**", ephemeral=True)

# ==========================================
# H. AUTOMATED SCHEDULER TASKS
# ==========================================
scheduler = AsyncIOScheduler()

async def daily_leaderboard_update():
    embed = await build_leaderboard_embed()
    lb_ids = get_config("lb_channel_ids", [])
    for cid in lb_ids:
        try:
            channel = bot.get_channel(cid)
            if channel:
                await channel.send("🌅 **[06:00 AM] CẬP NHẬT BẢNG XẾP HẠNG HẰNG NGÀY**", embed=embed)
        except Exception as e:
            print(f"Error sending LB update to channel {cid}: {e}")

async def weekly_leaderboard_reset():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, points, titles FROM users ORDER BY points DESC LIMIT 3")
    rows = c.fetchall()

    titles = get_config("top_titles", {
        "top1": {"title": "Khư quỷ", "color": "🔴"},
        "top2": {"title": "Khu la", "color": "🟠"},
        "top3": {"title": "Thế thần", "color": "🟡"}
    })

    for idx, r in enumerate(rows, 1):
        t_name = titles[f"top{idx}"]["title"]
        user_titles = json.loads(r["titles"]) if r["titles"] else []
        if t_name not in user_titles:
            user_titles.append(t_name)
            c.execute("UPDATE users SET titles = ? WHERE user_id = ?", (json.dumps(user_titles, ensure_ascii=False), r["user_id"]))

    c.execute("UPDATE users SET points = 1000")
    conn.commit()
    conn.close()

# =========================================================
# SYSTEM: CHAT & VOICE REWARD LOGIC
# =========================================================
last_text_earn = {}

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    user_id = message.author.id
    current_time = time.time()

    # Chat Cooldown: 10 giây -> Cộng 10 điểm
    if user_id not in last_text_earn or (current_time - last_text_earn[user_id]) >= 10:
        last_text_earn[user_id] = current_time
        
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (user_id, points) VALUES (?, 10) ON CONFLICT(user_id) DO UPDATE SET points = points + 10", 
            (user_id,)
        )
        conn.commit()
        conn.close()

    await bot.process_commands(message)

# Task Voice: Tối ưu hóa - Gom tất cả user vào 1 Lệnh Batch Update duy nhất
@tasks.loop(seconds=10)
async def voice_reward_task():
    eligible_users = []
    
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            # Bỏ qua nếu là kênh AFK của Server
            if guild.afk_channel and vc.id == guild.afk_channel.id:
                continue

            # Chỉ tính nếu trong room có từ 2 người dùng (không tính bot) trở lên
            non_bot_members = [m for m in vc.members if not m.bot]
            if len(non_bot_members) < 2:
                continue

            for member in non_bot_members:
                # Bỏ qua nếu thành viên đang Mute Tai hoặc ở trạng thái AFK
                if member.voice.self_deaf or member.voice.deaf or member.voice.afk:
                    continue
                
                eligible_users.append((member.id,))

    if eligible_users:
        conn = get_db()
        c = conn.cursor()
        c.executemany(
            "INSERT INTO users (user_id, points) VALUES (?, 20) ON CONFLICT(user_id) DO UPDATE SET points = points + 20",
            eligible_users
        )
        conn.commit()
        conn.close()

@voice_reward_task.before_loop
async def before_voice_task():
    await bot.wait_until_ready()

# =========================================================
# BOT EVENTS & STARTUP
# =========================================================
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập thành công dưới tên: {bot.user}")
    
    # Kích hoạt Voice Task
    if not voice_reward_task.is_running():
        voice_reward_task.start()

    # Đồng bộ Slash Commands
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Đã đồng bộ {len(synced)} lệnh Slash Commands.")
    except Exception as e:
        print(f"❌ Lỗi đồng bộ lệnh: {e}")

    # Đăng ký Persistent Views nếu class tồn tại
    try:
        bot.add_view(ShopMainView())
        bot.add_view(FishingView())
    except NameError:
        pass

    # Kích hoạt Scheduler
    if not scheduler.running:
        scheduler.add_job(daily_leaderboard_update, 'cron', hour=6, minute=0)
        scheduler.add_job(weekly_leaderboard_reset, 'cron', day_of_week='sun', hour=23, minute=59)
        scheduler.start()

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ Chưa cấu hình DISCORD_BOT_TOKEN trong Environment Variables!")
    else:
        bot.run(token)

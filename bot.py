import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
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

# ==============================================================================
# --- 1. WEB SERVER GIỮ BOT ONLINE 24/7 ---
# ==============================================================================
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

# ==============================================================================
# --- 2. BỘ TRUY XUẤT DỮ LIỆU TRONG RAM (KHÔNG NỔI LỖI FILE JSON) ---
# ==============================================================================
db_users = {}       # {user_id: {"weekly": 0, "total": 0, "titles": []}}
db_pets = {}        # {user_id: {"type": ..., "level": 1, "exp": 0, ...}}
db_config = {"game_channel_id": None}

db_titles = {
    "1": {"icon": "👑", "name": "Dạ Minh Tiên Tôn"},
    "2": {"icon": "😈", "name": "U Minh Quỷ Đế"},
    "3": {"icon": "🐢", "name": "Thiên Cơ Đạo Trưởng"}
}

db_trivia = [
    {"q": "Trong một cuộc thi chạy, nếu bạn vượt qua người đang đứng thứ hai, bạn sẽ đứng thứ mấy?", "a": ["thứ hai", "thứ 2", "2", "thu hai"]},
    {"q": "Bố của Mary có 5 cô con gái: Nana, Nene, Nini, Nono. Hỏi cô con gái thứ 5 tên là gì?", "a": ["mary", "tên là mary", "cô con gái thứ 5 tên là mary"]},
    {"q": "Có một chiếc xe tải đi vào đường cấm, dù đi qua trước mặt rất nhiều cảnh sát giao thông nhưng không ai phạt. Hỏi tại sao?", "a": ["đi bộ", "bác tài đi bộ", "tài xế đi bộ"]}
]

db_fishing_shop = {
    "moi_canh_gio": {"name": "🪽 Mồi cánh gió", "type": "moi", "rarity": "Thường ⚪", "price": 100, "succ_bonus": 0.01},
    "moi_sao": {"name": "✨ Mồi sao", "type": "moi", "rarity": "Hiếm 🟢", "price": 200, "succ_bonus": 0.10},
    "moi_sumo": {"name": "🥞 Mồi sumo", "type": "moi", "rarity": "Sử Thi 🟣", "price": 10000, "succ_bonus": 0.12},
    "moi_tien_ca": {"name": "🧜 Mồi nàng tiên cá", "type": "moi", "rarity": "Thần Thoại 🟡", "price": 25000, "succ_bonus": 0.16},
    "can_banh_mi": {"name": "🥖 Cần bánh mì", "type": "can", "rarity": "Thường ⚪", "price": 10, "succ_bonus": 0},
    "can_set": {"name": "⚡ Cần sét", "type": "can", "rarity": "Hiếm 🟢", "price": 100, "succ_bonus": 0.01},
    "can_lua": {"name": "🔥 Cần lửa", "type": "can", "rarity": "Hiếm 🟢", "price": 1000, "succ_bonus": 0.03}
}

db_pet_database = {
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

db_fish_table = [
    {"id": "ro_dong", "name": "🐟 Cá Rô Đồng", "type": "thuong", "pts": 10, "weight": 50},
    {"id": "chep_vang", "name": "🐠 Cá Chép Vàng", "type": "thuong", "pts": 10, "weight": 50},
    {"id": "giay_rach", "name": "👞 Giày Cũ Bị Rách", "type": "xui", "pts": -100, "weight": 40},
    {"id": "ruong_bau", "name": "👑 Rương Báu Dưới Sông", "type": "hiem", "pts": 100, "weight": 40},
    {"id": "voi_sat_than", "name": "🫍 Cá voi sát thần", "type": "than_thoai", "pts": 500, "title": "🛡️ Sát Long", "weight": 1.0}
]

def add_points(user_id: str, amount: int):
    if user_id not in db_users:
        db_users[user_id] = {"weekly": 0, "total": 0, "titles": []}
    
    db_users[user_id]["weekly"] = max(0, db_users[user_id].get("weekly", 0) + amount)
    if amount > 0:
        db_users[user_id]["total"] = db_users[user_id].get("total", 0) + amount
    return db_users[user_id]["weekly"]

def add_custom_title(user_id: str, title_str: str):
    if user_id not in db_users:
        db_users[user_id] = {"weekly": 0, "total": 0, "titles": []}
    if "titles" not in db_users[user_id]:
        db_users[user_id]["titles"] = []
    if title_str not in db_users[user_id]["titles"]:
        db_users[user_id]["titles"].append(title_str)

chat_cooldowns = {}

# ==============================================================================
# --- 3. CẤU HÌNH BOT ---
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def process_weekly_rewards():
    if not db_users:
        return "❌ Không có dữ liệu điểm tuần để chốt."

    sorted_users = sorted(db_users.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:3]
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

    for u_id in db_users:
        db_users[u_id]["weekly"] = 0
    
    return "\n".join(summary_lines) if summary_lines else "Không tìm thấy thành viên Top trong Server."

# ==============================================================================
# --- 4. TASKS TỰ ĐỘNG CHẠY NGẦM ---
# ==============================================================================
@tasks.loop(minutes=1)
async def auto_daily_leaderboard():
    vietnam_tz = timezone(timedelta(hours=7))
    now = datetime.now(vietnam_tz)
    
    if now.hour == 8 and now.minute == 0:
        channel_id = db_config.get("game_channel_id")
        if not channel_id: return
            
        channel = bot.get_channel(channel_id)
        if not channel: return
            
        sorted_users = sorted(db_users.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:10]
        
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
            if str(index) in db_titles:
                t_icon = db_titles[str(index)]["icon"]
                t_name = db_titles[str(index)]["name"]
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
        channel_id = db_config.get("game_channel_id")
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
        channel_id = db_config.get("game_channel_id")
        if not channel_id: return
        
        channel = bot.get_channel(channel_id)
        if not channel: return
        
        if not db_trivia: return
        
        item = random.choice(db_trivia)
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
    
    bot.add_view(CauSongView())
    print("[SYSTEM] Đã kích hoạt Persistent View (Vĩnh viễn) cho Shop và Cầu Sông!")

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

cooldown_fishing = {}

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
        db_fish_table.append(new_fish)

        embed = discord.Embed(
            title="✅ ĐÃ THÊM CÁ MỚI VÀO SÔNG!",
            description=f"🐟 **Tên:** {new_fish['name']}\n🏷️ **Loại:** `{new_fish['type']}` | 🎁 **Điểm:** `{new_fish['pts']}` | 📊 **Tỉ lệ:** `{new_fish['weight']}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CauSongView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout=None cho phép vĩnh viễn

    @discord.ui.button(label="Thả Cần Câu Cá 🎣", style=discord.ButtonStyle.success, custom_id="causong_fish_btn")
    async def fish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        current_time = time.time()

        if user_id in cooldown_fishing:
            elapsed = current_time - cooldown_fishing[user_id]
            if elapsed < 30:
                remaining = int(30 - elapsed)
                await interaction.response.send_message(
                    f"⏳ {interaction.user.mention}, bạn cần đợi **{remaining} giây** nữa mới được thả cần tiếp!",
                    ephemeral=True
                )
                return

        cooldown_fishing[user_id] = current_time

        user_inventory = db_pets.get(user_id, {}).get("inventory", {})
        base_success_rate = 0.45
        
        active_moi = user_inventory.get("active_moi")
        active_can = user_inventory.get("active_can")
        
        if active_moi and active_moi in db_fishing_shop:
            base_success_rate += db_fishing_shop[active_moi].get("succ_bonus", 0)
        if active_can and active_can in db_fishing_shop:
            base_success_rate += db_fishing_shop[active_can].get("succ_bonus", 0)

        # Trường hợp CÂU THẤT BẠI
        if random.random() > base_success_rate:
            await interaction.response.send_message(
                f"🎣 {interaction.user.mention} đã quăng cần nhưng **cá cắn hụt**, câu thất bại rồi!",
                ephemeral=False
            )
            return

        weights = []
        for fish in db_fish_table:
            w = fish["weight"]
            if fish["type"] == "hiem" and active_moi == "moi_sao":
                w *= 1.5
            elif fish["type"] == "su_thi" and active_moi == "moi_sumo":
                w *= 1.8
            elif fish["type"] == "than_thoai" and active_moi == "moi_tien_ca":
                w *= 2.0
            weights.append(w)

        caught = random.choices(db_fish_table, weights=weights)[0]
        pts = caught["pts"]
        new_score = add_points(user_id, pts)

        embed = discord.Embed(
            title="🎣 BẬT CẦN TRÚNG LỚN!",
            description=f"🎉 {interaction.user.mention} đã giật cần thành công và bắt được **{caught['name']}**!",
            color=discord.Color.blue()
        )
        if pts >= 0:
            embed.add_field(name="🎁 Phần Thưởng", value=f"**+{pts} điểm** (Tổng điểm tuần: `{new_score}`)", inline=False)
        else:
            embed.add_field(name="📉 Xui Xẻo", value=f"**{pts} điểm** (Điểm tuần còn lại: `{new_score}`)", inline=False)

        if "title" in caught:
            add_custom_title(user_id, caught["title"])
            embed.add_field(name="🎉 DANH HIỆU KHAI QUẬT", value=f"🏆 **[{caught['title']}]**", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @discord.ui.button(label="Thêm Cá Mới (Admin) ➕", style=discord.ButtonStyle.danger, custom_id="causong_add_fish_btn")
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
    if p_type not in db_pet_database:
        return 0
    cfg = db_pet_database[p_type]
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
    if pet_data["type"] not in db_pet_database:
        return "Pet Không Xác Định"
    p_cfg = db_pet_database[pet_data["type"]]
    lvl = str(pet_data["level"])
    forms = p_cfg.get("forms", {})
    return forms.get(lvl, forms.get("3", p_cfg.get("name", "Thần Thú")))

def add_exp_to_pet(pet_data, exp_amount):
    pet_data["exp"] += exp_amount
    p_cfg = db_pet_database.get(pet_data["type"], {})
    
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
    p_cfg = db_pet_database.get(pet_data["type"], {})
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

        db_pet_database[self.pet_id.value.strip()] = new_pet

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
        current_pts = db_users.get(self.user_id, {}).get("weekly", 0)
        if current_pts < 100:
            await interaction.response.send_message("❌ Bạn không đủ **100 điểm** để mở trứng Pet!", ephemeral=True)
            return

        add_points(self.user_id, -100)
        pet_keys = list(db_pet_database.keys())
        pet_choice = random.choice(pet_keys) if pet_keys else "sutu"

        p_info = db_pet_database.get(pet_choice, db_pet_database["sutu"])
        db_pets[self.user_id] = {
            "type": pet_choice,
            "level": 1,
            "exp": 0,
            "perm_power": 0,
            "temp_power": 0,
            "buff_until": 0
        }

        updated_pts = db_users.get(self.user_id, {}).get("weekly", 0)
        embed = create_pet_embed(interaction.user.display_name, db_pets[self.user_id], updated_pts)
        await interaction.response.edit_message(content=f"🎉 **Chúc mừng!** Bạn đã ấp thành công trứng và nhận được **{p_info['forms']['1']}**!", embed=embed, view=self)

    @discord.ui.button(label="Cho Pet Ăn (+100 EXP) - 500đ", style=discord.ButtonStyle.primary, emoji="🍖")
    async def feed_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = db_pets.get(self.user_id)
        if not p or "type" not in p:
            await interaction.response.send_message("❌ Bạn chưa sở hữu Pet nào! Hãy mở trứng trước.", ephemeral=True)
            return

        pts = db_users.get(self.user_id, {}).get("weekly", 0)
        if pts < 500:
            await interaction.response.send_message(f"❌ Bạn không đủ điểm! Cần **500 điểm** để cho Pet ăn (Hiện có: `{pts}` điểm).", ephemeral=True)
            return

        add_points(self.user_id, -500)
        leveled_up = add_exp_to_pet(p, 100)
        
        updated_pts = db_users.get(self.user_id, {}).get("weekly", 0)
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
    p = db_pets.get(user_id)
    user_pts = db_users.get(user_id, {}).get("weekly", 0)

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

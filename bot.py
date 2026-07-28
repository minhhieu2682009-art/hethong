import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import json
import os
import time
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread

# ==============================================================================
# --- 0. CẤU HÌNH ROLE TOP 1, 2, 3 (THAY ID ROLE THẬT CỦA BẠN VÀO ĐÂY) ---
# ==============================================================================
ROLE_TOP1_ID = 123456789012345678  # Thay bằng ID Role Top 1 (Đoàn Trưởng) của bạn
ROLE_TOP2_ID = 123456789012345678  # Thay bằng ID Role Top 2 của bạn
ROLE_TOP3_ID = 123456789012345678  # Thay bằng ID Role Top 3 của bạn

# --- 1. WEB SERVER GIỮ BOT ONLINE TRÊN RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Hệ Thống đang chạy 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. QUẢN LÝ DỮ LIỆU ĐIỂM, DANH HIỆU & THÚ ẢO (LƯU FILE JSON) ---
DATA_FILE = "user_points.json"
TITLES_FILE = "titles_config.json"
PETS_FILE = "user_pets.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_pets():
    if os.path.exists(PETS_FILE):
        with open(PETS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_pets(data):
    with open(PETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_titles():
    default_titles = {
        "1": {"icon": "👑", "name": "Quỷ Thần"},
        "2": {"icon": "⚔️", "name": "Thần Thương"},
        "3": {"icon": "🐎", "name": "Kị Vương"}
    }
    if os.path.exists(TITLES_FILE):
        with open(TITLES_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return default_titles
    return default_titles

def save_titles(titles):
    with open(TITLES_FILE, "w", encoding="utf-8") as f:
        json.dump(titles, f, ensure_ascii=False, indent=4)

def add_points(user_id: str, amount: int):
    data = load_data()
    if user_id not in data:
        data[user_id] = {"weekly": 0, "total": 0}
    
    data[user_id]["weekly"] += amount
    data[user_id]["total"] += amount
    save_data(data)
    return data[user_id]["weekly"]

def get_user_points(user_id: str):
    data = load_data()
    if user_id not in data:
        return 0
    return data[user_id].get("weekly", 0)

# Biến lưu thời gian cooldown nhắn tin của từng người dùng
chat_cooldowns = {}

# --- 3. CẤU HÌNH BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID Kênh phát trò chơi & thông báo bảng xếp hạng
GAME_CHANNEL_ID = None

# --- HÀM XỬ LÝ TRAO ROLE TOP & RESET ĐIỂM TUẦN ---
async def process_weekly_rewards():
    data = load_data()
    if not data:
        return "Không có dữ liệu điểm tuần."

    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:3]
    summary_msg = "🏆 **KẾT QUẢ VÀ TỰ ĐỘNG TRAO ROLE TOP TUẦN:**\n"
    
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
                        print(f"Lỗi gỡ role: {e}")

        for index, (u_id, score) in enumerate(sorted_users):
            member = guild.get_member(int(u_id))
            target_role = roles[index] if index < len(roles) else None
            
            if member:
                if target_role:
                    try:
                        await member.add_roles(target_role)
                    except Exception as e:
                        print(f"Lỗi trao role: {e}")
                summary_msg += f"🥇 **Top {index+1}:** {member.mention} (`{score.get('weekly', 0)} điểm`)\n"

    for u_id in data:
        data[u_id]["weekly"] = 0
    save_data(data)
    
    return summary_msg

# --- 4. TÁC VỤ TỰ ĐỘNG (BACKGROUND TASKS) ---

@tasks.loop(minutes=1)
async def auto_daily_leaderboard():
    vietnam_tz = timezone(timedelta(hours=7))
    now = datetime.now(vietnam_tz)
    
    if now.hour == 8 and now.minute == 0:
        global GAME_CHANNEL_ID
        if not GAME_CHANNEL_ID:
            return
            
        channel = bot.get_channel(GAME_CHANNEL_ID)
        if not channel:
            return
            
        data = load_data()
        titles = load_titles()
        sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:10]
        
        embed = discord.Embed(
            title="☀️ BẢNG XẾP HẠNG ĐIỂM TUẦN (CẬP NHẬT MỖI NGÀY) ☀️", 
            color=discord.Color.gold()
        )
        
        description = ""
        for index, (u_id, score) in enumerate(sorted_users, 1):
            user = bot.get_user(int(u_id))
            name = user.name if user else f"User ID: {u_id}"
            
            icon = "🔹"
            if str(index) in titles:
                t_icon = titles[str(index)]["icon"]
                t_name = titles[str(index)]["name"]
                icon = f"{t_icon} **[Top {index} - {t_name}]**"
            
            description += f"{index}. {icon} {name} — `{score.get('weekly', 0)} điểm`\n"
            
        embed.description = description if description else "Chưa có dữ liệu điểm tuần này."
        await channel.send(embed=embed)

@tasks.loop(minutes=1)
async def auto_reset_weekly_top():
    vietnam_tz = timezone(timedelta(hours=7))
    now = datetime.now(vietnam_tz)
    
    if now.weekday() == 0 and now.hour == 0 and now.minute == 0:
        msg = await process_weekly_rewards()
        global GAME_CHANNEL_ID
        if GAME_CHANNEL_ID:
            channel = bot.get_channel(GAME_CHANNEL_ID)
            if channel:
                await channel.send(f"🎉 **ĐÃ TỰ ĐỘNG CHỐT BẢNG XẾP HẠNG TUẦN!** 🎉\n\n{msg}")

@tasks.loop(minutes=5)
async def check_voice_points():
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            members = [m for m in vc.members if not m.bot and not m.voice.deaf and not m.voice.self_deaf]
            for member in members:
                add_points(str(member.id), 5)

@tasks.loop(minutes=30)
async def auto_minigame_task():
    global GAME_CHANNEL_ID
    if not GAME_CHANNEL_ID:
        return
    
    channel = bot.get_channel(GAME_CHANNEL_ID)
    if not channel:
        return
    
    game_type = random.choice(["math", "word", "fast_type"])
    
    if game_type == "math":
        a, b = random.randint(10, 99), random.randint(10, 99)
        ans = str(a + b)
        embed = discord.Embed(
            title="🎮 MINI-GAME TỰ ĐỘNG (30 PHÚT)",
            description=f"Tính nhanh: **{a} + {b} = ?**\nAi gõ đúng đáp án đầu tiên nhận ngay **+30 điểm**! *(Thời gian: 30s)*",
            color=discord.Color.green()
        )
    elif game_type == "word":
        words = ["genshin", "valorant", "minecraft", "roblox", "python", "discord", "system"]
        target = random.choice(words)
        scrambled = "".join(random.sample(target, len(target)))
        ans = target
        embed = discord.Embed(
            title="🎮 MINI-GAME TỰ ĐỘNG (30 PHÚT)",
            description=f"Giải mã từ bị xáo trộn: **`{scrambled}`**\nAi gõ đúng từ gốc tiếng Anh nhận ngay **+30 điểm**! *(Thời gian: 30s)*",
            color=discord.Color.purple()
        )
    else:
        words = ["HE THONG DISCORD", "QUY THAN", "THAN THUONG", "KI VUONG", "DISCORD BOT"]
        target = random.choice(words)
        ans = target
        embed = discord.Embed(
            title="🎮 MINI-GAME TỰ ĐỘNG (30 PHÚT)",
            description=f"Thử thách tay nhanh: Hãy gõ chính xác cụm từ: **`{target}`**\nNgười nhanh nhất nhận ngay **+30 điểm**! *(Thời gian: 30s)*",
            color=discord.Color.gold()
        )

    await channel.send(embed=embed)

    def check(m):
        return m.channel == channel and not m.bot and m.content.strip().lower() == ans.lower()

    try:
        msg = await bot.wait_for('message', timeout=30.0, check=check)
        new_score = add_points(str(msg.author.id), 30)
        await channel.send(f"🎉 Chúc mừng {msg.author.mention} đã trả lời đúng nhanh nhất! Bạn nhận **+30 điểm** (Tổng điểm tuần: `{new_score}`).")
    except Exception:
        await channel.send("⏰ Đã hết 30 giây mà không có ai trả lời đúng!")

@bot.event
async def on_ready():
    print(f"Bot đã online: {bot.user}")
    if not check_voice_points.is_running():
        check_voice_points.start()
    if not auto_minigame_task.is_running():
        auto_minigame_task.start()
    if not auto_reset_weekly_top.is_running():
        auto_reset_weekly_top.start()
    if not auto_daily_leaderboard.is_running():
        auto_daily_leaderboard.start()
        
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} lệnh Slash (/)...")
    except Exception as e:
        print(f"Lỗi sync: {e}")

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
# --- 5. HỆ THỐNG MINI GAME MỚI (NUÔI THÚ, CỜ VUA, CƯỢC MẶT ÚP/MỞ) ---
# ==============================================================================

# A. HỆ THỐNG NUÔI THÚ ẢO (/nuoithu)
@bot.tree.command(name="nuoithu", description="Hệ thống nuôi thú ảo, cho ăn và đi săn điểm!")
@app_commands.choices(hanhdong=[
    app_commands.Choice(name="Nhận/Xem Thú", value="xem"),
    app_commands.Choice(name="Cho Thú Ăn (-20 điểm)", value="an"),
    app_commands.Choice(name="Cho Thú Đi Săn Thưởng", value="san")
])
async def nuoithu(interaction: discord.Interaction, hanhdong: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    pets = load_pets()
    
    if hanhdong.value == "xem":
        if user_id not in pets:
            pets[user_id] = {"name": "Trứng Bí Ẩn", "level": 1, "exp": 0, "icon": "🥚"}
            save_pets(pets)
            await interaction.response.send_message("🐣 Bạn vừa nhận được một Quả Trứng Bí Ẩn! Hãy tích cực cho ăn và chăm sóc để trứng nở thành Thú cưng nhé.")
        else:
            p = pets[user_id]
            await interaction.response.send_message(f"🐾 **Thú Cưng Của Bạn:**\n- Tên/Loài: {p['icon']} **{p['name']}**\n- Cấp độ (Level): `{p['level']}`\n- Điểm kinh nghiệm (EXP): `{p['exp']}/100`")
            
    elif hanhdong.value == "an":
        if user_id not in pets:
            await interaction.response.send_message("❌ Bạn chưa có thú cưng! Hãy chọn hành động 'Nhận/Xem Thú' trước.")
            return
        
        current_pts = get_user_points(user_id)
        if current_pts < 20:
            await interaction.response.send_message("❌ Bạn không đủ **20 điểm tuần** để mua thức ăn cho thú!")
            return
            
        add_points(user_id, -20) # Trừ 20 điểm thức ăn
        p = pets[user_id]
        p['exp'] += 35
        
        msg = f"🍖 Bạn đã cho **{p['name']}** ăn thành công (-20 điểm tuần). Thú cưng nhận thêm `+35 EXP`!"
        if p['exp'] >= 100:
            p['level'] += 1
            p['exp'] = 0
            if p['level'] == 2:
                p['name'] = "Hỏa Long Nhỏ"
                p['icon'] = "🐉"
            elif p['level'] >= 3:
                p['name'] = "Thần Long Tối Thượng"
                p['icon'] = "👑🐉"
            msg += f"\n🎉 **CHÚC MỪNG!** Thú cưng của bạn đã tiến hóa lên cấp **{p['level']}** (`{p['name']}`)!"
            
        save_pets(pets)
        await interaction.response.send_message(msg)
        
    elif hanhdong.value == "san":
        if user_id not in pets:
            await interaction.response.send_message("❌ Bạn chưa có thú cưng!")
            return
        p = pets[user_id]
        reward = random.randint(10, 40) * p['level']
        add_points(user_id, reward)
        await interaction.response.send_message(f"🗡️ Thú cưng {p['icon']} **{p['name']}** của bạn đã xuất kích đi săn và mang về **+{reward} điểm tuần** cho chủ nhân!")


# B. HỆ THỐNG CƯỢC ĐIỂM (MẶT ÚP / MẶT MỞ - TÀI XỈU) (/cuocdiem)
@bot.tree.command(name="cuocdiem", description="Cược điểm may rủi: Chọn Tài/Xỉu hoặc Chẵn/Lẻ!")
@app_commands.choices(luachon=[
    app_commands.Choice(name="Tài (Tổng điểm xúc sắc từ 11 đến 18)", value="tai"),
    app_commands.Choice(name="Xỉu (Tổng điểm xúc sắc từ 3 đến 10)", value="xiu")
])
async def cuocdiem(interaction: discord.Interaction, sodiem_cuoc: int, luachon: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    current_pts = get_user_points(user_id)
    
    if sodiem_cuoc <= 0:
        await interaction.response.send_message("❌ Số điểm cược phải lớn hơn 0!")
        return
    if current_pts < sodiem_cuoc:
        await interaction.response.send_message(f"❌ Bạn không đủ điểm! Điểm tuần hiện tại của bạn chỉ có: `{current_pts}`.")
        return
        
    # Tung 3 con xúc sắc (1-6)
    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    result = "tai" if total >= 11 else "xiu"
    
    dice_str = f"🎲 Kết quả xúc sắc: **{d1} - {d2} - {d3}** (Tổng: **{total}**)"
    
    if luachon.value == result:
        add_points(user_id, sodiem_cuoc) # Thắng nhận thêm đúng số điểm cược
        await interaction.response.send_message(f"{dice_str}\n🎉 **CHIẾN THẮNG!** Bạn đoán chính xác và nhận thêm **+{sodiem_cuoc} điểm tuần**!")
    else:
        add_points(user_id, -sodiem_cuoc) # Thua trừ điểm cược
        await interaction.response.send_message(f"{dice_str}\n😢 **THẠT TIẾC!** Bạn đoán sai và mất **-{sodiem_cuoc} điểm tuần**.")


# C. HỆ THỐNG CỜ VUA MINI TƯƠNG TÁC BUTTON (/covua)
class ChessView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=120)
        self.p1 = p1
        self.p2 = p2
        self.turn = p1
        self.board_status = "Trận đấu cờ vua mini đang diễn ra giữa 2 bên..."

    @discord.ui.button(label="Đi Nước 1 (Tấn Công)", style=discord.ButtonStyle.green)
    async def move_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.turn:
            await interaction.response.send_message("⏳ Chưa tới lượt của bạn!", ephemeral=True)
            return
        self.turn = self.p2 if self.turn == self.p1 else self.p1
        await interaction.response.edit_message(content=f"♟️ **Cờ Vua Mini:** {interaction.user.mention} vừa đi một nước cờ hiểm hóc!\n👉 **Lượt tiếp theo:** {self.turn.mention}")

    @discord.ui.button(label="Đi Nước 2 (Phòng Thủ)", style=discord.ButtonStyle.blurple)
    async def move_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.turn:
            await interaction.response.send_message("⏳ Chưa tới lượt của bạn!", ephemeral=True)
            return
        self.turn = self.p2 if self.turn == self.p1 else self.p1
        await interaction.response.edit_message(content=f"♟️ **Cờ Vua Mini:** {interaction.user.mention} thiết lập thế trận phòng thủ vững chắc!\n👉 **Lượt tiếp theo:** {self.turn.mention}")

    @discord.ui.button(label="Đầu Hàng", style=discord.ButtonStyle.red)
    async def surrender(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.p1 and interaction.user != self.p2:
            await interaction.response.send_message("❌ Bạn không phải người chơi trong bàn cờ này!", ephemeral=True)
            return
        winner = self.p2 if interaction.user == self.p1 else self.p1
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"🏳️ {interaction.user.mention} đã đầu hàng! Chúc mừng **{winner.mention}** giành chiến thắng!", view=self)
        self.stop()

@bot.tree.command(name="covua", description="Mời một thành viên khác vào bàn đấu Cờ Vua Mini giao lưu!")
async def covua(interaction: discord.Interaction, opponent: discord.Member):
    if opponent.bot or opponent == interaction.user:
        await interaction.response.send_message("❌ Bạn không thể đấu với bot hoặc tự đấu với chính mình!", ephemeral=True)
        return
        
    view = ChessView(interaction.user, opponent)
    await interaction.response.send_message(
        f"♟️ **BÀN CỜ VUA MINI ĐÃ MỞ!**\nThách đấu giữa {interaction.user.mention} và {opponent.mention}!\n👉 **Lượt đi đầu tiên:** {interaction.user.mention}",
        view=view
    )


# --- 6. CÁC LỆNH ADMIN & CƠ BẢN KHÁC ---

@bot.tree.command(name="reset_week_manual", description="[ADMIN] Ép trao Role Top 1, 2, 3 và reset điểm tuần ngay lập tức")
@app_commands.checks.has_permissions(administrator=True)
async def reset_week_manual(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = await process_weekly_rewards()
    await interaction.followup.send(f"✅ **ĐÃ THỰC HIỆN RESET TUẦN THỦ CÔNG:**\n{msg}")

@bot.tree.command(name="set_top_title", description="[ADMIN] Đổi danh hiệu và biểu tượng hiển thị cho Top 1, 2 hoặc 3")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(top=[
    app_commands.Choice(name="Top 1", value=1),
    app_commands.Choice(name="Top 2", value=2),
    app_commands.Choice(name="Top 3", value=3)
])
async def set_top_title(interaction: discord.Interaction, top: app_commands.Choice[int], icon: str, title_name: str):
    titles = load_titles()
    rank_str = str(top.value)
    titles[rank_str] = {"icon": icon, "name": title_name}
    save_titles(titles)
    await interaction.response.send_message(f"✅ Đã đổi danh hiệu **Top {top.value}** thành: {icon} **[{title_name}]**!")

@bot.tree.command(name="set_game_channel", description="[ADMIN] Đặt kênh tự động phát Mini-game và gửi BXH mỗi ngày")
@app_commands.checks.has_permissions(administrator=True)
async def set_game_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global GAME_CHANNEL_ID
    GAME_CHANNEL_ID = channel.id
    await interaction.response.send_message(f"✅ Đã chọn kênh **{channel.mention}** làm nơi phát Mini-game và tự động thông báo BXH!")

@bot.tree.command(name="bangxephang", description="Xem Bảng Xếp Hạng điểm tuần!")
async def bangxephang(interaction: discord.Interaction):
    data = load_data()
    titles = load_titles()
    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:10]
    
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG ĐIỂM TUẦN 🏆", color=discord.Color.gold())
    
    description = ""
    for index, (u_id, score) in enumerate(sorted_users, 1):
        user = bot.get_user(int(u_id))
        name = user.name if user else f"User ID: {u_id}"
        
        icon = "🔹"
        if str(index) in titles:
            t_icon = titles[str(index)]['icon']
            t_name = titles[str(index)]['name']
            icon = f"{t_icon} **[Top {index} - {t_name}]**"
        
        description += f"{index}. {icon} {name} — `{score.get('weekly', 0)} điểm`\n"
        
    embed.description = description if description else "Chưa có dữ liệu điểm tuần này."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="point_edit", description="[ADMIN] Thay đổi điểm của người chơi")
@app_commands.checks.has_permissions(administrator=True)
async def point_edit(interaction: discord.Interaction, user: discord.User, amount: int):
    new_score = add_points(str(user.id), amount)
    await interaction.response.send_message(f"✅ Đã chỉnh điểm cho {user.mention}. Điểm tuần mới: `{new_score}`.")

@bot.tree.command(name="danhhieu_grant", description="[ADMIN] Trao danh hiệu thủ công cho thành viên")
@app_commands.checks.has_permissions(administrator=True)
async def danhhieu_grant(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    await user.add_roles(role)
    await interaction.response.send_message(f"🎉 Đã trao danh hiệu **{role.name}** cho {user.mention}!")

@bot.tree.command(name="danhhieu_revoke", description="[ADMIN] Thu hồi danh hiệu thủ công của thành viên")
@app_commands.checks.has_permissions(administrator=True)
async def danhhieu_revoke(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    await user.remove_roles(role)
    await interaction.response.send_message(f"🗑️ Đã thu hồi danh hiệu **{role.name}** từ {user.mention}!")

# --- 7. CHẠY BOT VỚI TOKEN TỪ BIẾN MÔI TRƯỜNG ---
keep_alive()
TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)

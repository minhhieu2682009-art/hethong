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

# --- 2. QUẢN LÝ DỮ LIỆU ĐIỂM & DANH HIỆU (LƯU FILE JSON) ---
DATA_FILE = "user_points.json"
TITLES_FILE = "titles_config.json"

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

def load_titles():
    default_titles = {
        "1": {"icon": "👑", "name": "Đoàn Trưởng"},
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

    # Sắp xếp lấy Top 3 người cao điểm nhất
    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:3]
    
    summary_msg = "🏆 **KẾT QUẢ VÀ TỰ ĐỘNG TRAO ROLE TOP TUẦN:**\n"
    
    for guild in bot.guilds:
        roles = [
            guild.get_role(ROLE_TOP1_ID),
            guild.get_role(ROLE_TOP2_ID),
            guild.get_role(ROLE_TOP3_ID)
        ]
        
        # 1. Gỡ Role Top cũ của tất cả thành viên trong Server
        for role in roles:
            if role:
                for member in role.members:
                    try:
                        await member.remove_roles(role)
                    except Exception as e:
                        print(f"Lỗi gỡ role {role.name} từ {member.display_name}: {e}")

        # 2. Trao Role Top mới cho Top 1, 2, 3
        for index, (u_id, score) in enumerate(sorted_users):
            member = guild.get_member(int(u_id))
            target_role = roles[index] if index < len(roles) else None
            
            if member:
                if target_role:
                    try:
                        await member.add_roles(target_role)
                    except Exception as e:
                        print(f"Lỗi trao role cho {member.display_name}: {e}")
                summary_msg += f"🥇 **Top {index+1}:** {member.mention} (`{score.get('weekly', 0)} điểm`)\n"

    # 3. Reset điểm tuần của tất cả mọi người về 0 (Giữ nguyên tổng điểm total)
    for u_id in data:
        data[u_id]["weekly"] = 0
    save_data(data)
    
    return summary_msg

# --- 4. TÁC VỤ TỰ ĐỘNG (BACKGROUND TASKS) ---

# TỰ ĐỘNG GỬI BẢNG XẾP HẠNG MỖI NGÀY LÚC 08:00 SÁNG (GIỜ VN)
@tasks.loop(minutes=1)
async def auto_daily_leaderboard():
    vietnam_tz = timezone(timedelta(hours=7))
    now = datetime.now(vietnam_tz)
    
    # Kiểm tra đúng 08:00 AM hàng ngày
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

# Tự động kiểm tra & trao Role Top + Reset điểm lúc 00:00 sáng Thứ Hai (Giờ VN)
@tasks.loop(minutes=1)
async def auto_reset_weekly_top():
    vietnam_tz = timezone(timedelta(hours=7))
    now = datetime.now(vietnam_tz)
    
    # Kiểm tra đúng 00:00 AM vào Thứ Hai (Monday = 0)
    if now.weekday() == 0 and now.hour == 0 and now.minute == 0:
        print("⏰ Đến 00:00 Thứ Hai! Đang tự động trao Role Top và Reset điểm tuần...")
        msg = await process_weekly_rewards()
        
        global GAME_CHANNEL_ID
        if GAME_CHANNEL_ID:
            channel = bot.get_channel(GAME_CHANNEL_ID)
            if channel:
                await channel.send(f"🎉 **ĐÃ TỰ ĐỘNG CHỐT BẢNG XẾP HẠNG TUẦN!** 🎉\n\n{msg}")

# Tự động cộng điểm Voice (mỗi 5 phút +5 điểm)
@tasks.loop(minutes=5)
async def check_voice_points():
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            members = [m for m in vc.members if not m.bot and not m.voice.deaf and not m.voice.self_deaf]
            for member in members:
                add_points(str(member.id), 5)

# Tự động phát Mini-game ngẫu nhiên mỗi 30 phút
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

# --- 5. TỰ ĐỘNG CỘNG ĐIỂM CHAT ---
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

# --- 6. CÁC LỆNH SLASH (COMMANDS) ---

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

@bot.tree.command(name="dovui", description="Trả lời đố vui nhận điểm thưởng!")
async def dovui(interaction: discord.Interaction):
    questions = [
        {"q": "Thủ đô của Việt Nam là gì?", "a": "Hà Nội"},
        {"q": "2 + 2 x 2 bằng bao nhiêu?", "a": "6"},
        {"q": "Con vật nào đại diện cho Genshin Impact?", "a": "Paimon"}
    ]
    item = random.choice(questions)
    
    await interaction.response.send_message(f"❓ **Câu hỏi:** {item['q']}\n*(Bạn có 15 giây để gõ đáp án vào chat!)*")
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for('message', timeout=15.0, check=check)
        if msg.content.strip().lower() == item['a'].lower():
            pts = random.randint(20, 50)
            new_score = add_points(str(interaction.user.id), pts)
            await interaction.followup.send(f"🎉 **Chính xác!** Bạn nhận **+{pts} điểm**. Tổng điểm tuần: `{new_score}`.")
        else:
            await interaction.followup.send(f"❌ Sai rồi! Đáp án đúng là: **{item['a']}**.")
    except Exception:
        await interaction.followup.send("⏰ Đã hết thời gian trả lời!")

@bot.tree.command(name="cuop", description="Thử vận may đi cướp điểm!")
@app_commands.checks.cooldown(1, 60)
async def cuop(interaction: discord.Interaction):
    success = random.choice([True, False])
    user_id = str(interaction.user.id)
    
    if success:
        pts = random.randint(30, 80)
        new_score = add_points(user_id, pts)
        await interaction.response.send_message(f"💰 **Thành công!** Bạn cướp được **+{pts} điểm**. Tổng điểm tuần: `{new_score}`.")
    else:
        pts = random.randint(10, 30)
        data = load_data()
        current = data.get(user_id, {}).get("weekly", 0)
        loss = min(current, pts)
        
        if user_id in data:
            data[user_id]["weekly"] -= loss
            save_data(data)
            
        await interaction.response.send_message(f"🚨 **Bị bắt!** Bạn bị trừ **-{loss} điểm**.")

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
            t_icon = titles[str(index)]["icon"]
            t_name = titles[str(index)]["name"]
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

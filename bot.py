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

# --- 2. QUẢN LÝ DỮ LIỆU ĐIỂM, DANH HIỆU & THÚ CƯNG (LƯU FILE JSON) ---
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

# Biến lưu thời gian cooldown nhắn tin
chat_cooldowns = {}

# ==============================================================================
# --- DANH SÁCH CÂU HỎI ĐỐ VUI MẸO & TOÁN HỌC ---
# ==============================================================================
CUSTOM_TRIVIA = [
    {
        "q": "Trong một cuộc thi chạy, nếu bạn vượt qua người đang đứng thứ hai, bạn sẽ đứng thứ mấy?", 
        "a": ["thứ hai", "thứ 2", "2", "thu hai"]
    },
    {
        "q": "Bố của Mary có 5 cô con gái: Nana, Nene, Nini, Nono. Hỏi cô con gái thứ 5 tên là gì?", 
        "a": ["mary", "tên là mary", "cô con gái thứ 5 tên là mary"]
    },
    {
        "q": "Có một chiếc xe tải đi vào đường cấm, dù đi qua trước mặt rất nhiều cảnh sát giao thông nhưng không ai phạt hay giữ xe lại. Hỏi tại sao?", 
        "a": ["đi bộ", "bác tài đi bộ", "vì bác tài xế đi bộ", "tài xế đi bộ", "bác tài xế đi bộ"]
    },
    {
        "q": "Lớp học có 30 học sinh, cô giáo chia đều thành 5 tổ. Hỏi có tổng cộng bao nhiêu cái chân bước vào lớp nếu cô giáo và tất cả học sinh đều có mặt đầy đủ?", 
        "a": ["2", "2 chân", "hai chân", "2 cái chân"]
    },
    {
        "q": "Có 3 quả táo trên bàn, bạn lấy đi 2 quả. Hỏi bạn còn bao nhiêu quả táo?", 
        "a": ["2", "2 quả", "hai quả", "2 quả táo"]
    },
    {
        "q": "Cái gì người nghèo có, người giàu muốn có, nhưng nếu bạn ăn vô sẽ chết?", 
        "a": ["không có gì", "khong co gi"]
    },
    {
        "q": "Cho dãy số: 1, 11, 21, 1211, 111221. Hỏi số tiếp theo là bao nhiêu?", 
        "a": ["312211"]
    },
    {
        "q": "Tìm hai số X và Y biết tổng của chúng bằng tích của chúng và cũng bằng hiệu của chúng?", 
        "a": [
            "x=0.5, y=-1", "x = 0.5, y = -1", "x=0,5, y=-1", "x = 0,5, y = -1",
            "0.5 và -1", "0,5 và -1", "0.5 va -1", "0,5 va -1",
            "x=1/2, y=-1", "1/2 và -1", "1/2 va -1"
        ]
    }
]

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
                        print(f"Lỗi gỡ role {role.name} từ {member.display_name}: {e}")

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
        print("⏰ Đến 00:00 Thứ Hai! Đang tự động trao Role Top và Reset điểm tuần...")
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
    
    game_type = random.choice(["custom_trivia", "math", "word", "fast_type"])
    
    if game_type == "custom_trivia":
        item = random.choice(CUSTOM_TRIVIA)
        valid_ans = item["a"]
        embed = discord.Embed(
            title="🎮 MINI-GAME TỰ ĐỘNG (30 PHÚT)",
            description=f"🧠 **Câu hỏi đố vui:** {item['q']}\n\nAi trả lời đúng đầu tiên nhận ngay **+30 điểm**! *(Thời gian: 30s)*",
            color=discord.Color.green()
        )
    elif game_type == "math":
        a, b = random.randint(10, 99), random.randint(10, 99)
        valid_ans = [str(a + b)]
        embed = discord.Embed(
            title="🎮 MINI-GAME TỰ ĐỘNG (30 PHÚT)",
            description=f"🧮 Tính nhanh: **{a} + {b} = ?**\nAi gõ đúng đáp án đầu tiên nhận ngay **+30 điểm**! *(Thời gian: 30s)*",
            color=discord.Color.green()
        )
    elif game_type == "word":
        words = ["genshin", "valorant", "minecraft", "roblox", "python", "discord", "system"]
        target = random.choice(words)
        scrambled = "".join(random.sample(target, len(target)))
        valid_ans = [target]
        embed = discord.Embed(
            title="🎮 MINI-GAME TỰ ĐỘNG (30 PHÚT)",
            description=f"🔤 Giải mã từ bị xáo trộn: **`{scrambled}`**\nAi gõ đúng từ gốc tiếng Anh nhận ngay **+30 điểm**! *(Thời gian: 30s)*",
            color=discord.Color.purple()
        )
    else:
        words = ["HE THONG DISCORD", "QUY THAN", "THAN THUONG", "KI VUONG", "DISCORD BOT"]
        target = random.choice(words)
        valid_ans = [target.lower()]
        embed = discord.Embed(
            title="🎮 MINI-GAME TỰ ĐỘNG (30 PHÚT)",
            description=f"⚡ Thử thách tay nhanh: Hãy gõ chính xác cụm từ: **`{target}`**\nNgười nhanh nhất nhận ngay **+30 điểm**! *(Thời gian: 30s)*",
            color=discord.Color.gold()
        )

    await channel.send(embed=embed)

    def check(m):
        return m.channel == channel and not m.bot and m.content.strip().lower() in [ans.lower() for ans in valid_ans]

    try:
        msg = await bot.wait_for('message', timeout=30.0, check=check)
        new_score = add_points(str(msg.author.id), 30)
        await channel.send(f"🎉 Chúc mừng {msg.author.mention} đã trả lời đúng nhanh nhất! Bạn nhận **+30 điểm** (Tổng điểm tuần: `{new_score}`).")
    except Exception:
        first_ans = valid_ans[0] if isinstance(valid_ans, list) else valid_ans
        await channel.send(f"⏰ Đã hết 30 giây! Đáp án đúng là: **{first_ans}**")

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
# --- 5. TẤT CẢ LỆNH SLASH (COMMANDS) ---
# ==============================================================================

# 1. LỆNH ĐỐ VUI (CÁCH THỨC CŨ)
@bot.tree.command(name="dovui", description="Trả lời đố vui nhận điểm thưởng!")
async def dovui(interaction: discord.Interaction):
    item = random.choice(CUSTOM_TRIVIA)
    
    await interaction.response.send_message(f"❓ **Câu hỏi:** {item['q']}\n*(Bạn có 15 giây để gõ đáp án vào chat!)*")
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for('message', timeout=15.0, check=check)
        user_ans = msg.content.strip().lower()
        valid_answers = [a.lower() for a in item['a']]
        
        if user_ans in valid_answers:
            pts = random.randint(20, 50)
            new_score = add_points(str(interaction.user.id), pts)
            await interaction.followup.send(f"🎉 **Chính xác!** Bạn nhận **+{pts} điểm**. Tổng điểm tuần: `{new_score}`.")
        else:
            first_ans = item['a'][0]
            await interaction.followup.send(f"❌ Sai rồi! Đáp án đúng là: **{first_ans}**.")
    except Exception:
        await interaction.followup.send("⏰ Đã hết thời gian trả lời!")

# 2. LỆNH CƯỚP ĐIỂM (CÁCH THỨC CŨ)
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

@cuop.error
async def cuop_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Cảnh sát đang đi tuần! Vui lòng đợi `{int(error.retry_after)}s` nữa để đi cướp lại.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Đã xảy ra lỗi khi thực hiện lệnh.", ephemeral=True)

# 3. LỆNH TÀI XỈU (/taixiu)
@bot.tree.command(name="taixiu", description="Đặt cược điểm tuần vào Tài hoặc Xỉu!")
@app_commands.choices(luachon=[
    app_commands.Choice(name="Tài (11 - 18)", value="tai"),
    app_commands.Choice(name="Xỉu (3 - 10)", value="xiu")
])
async def taixiu(interaction: discord.Interaction, sodiem_cuoc: int, luachon: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    data = load_data()
    current_pts = data.get(user_id, {}).get("weekly", 0)
    
    if sodiem_cuoc <= 0:
        await interaction.response.send_message("❌ Số điểm cược phải lớn hơn 0!", ephemeral=True)
        return
    if current_pts < sodiem_cuoc:
        await interaction.response.send_message(f"❌ Bạn không đủ điểm! Điểm tuần hiện tại của bạn: `{current_pts}`.", ephemeral=True)
        return
        
    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    result = "tai" if total >= 11 else "xiu"
    
    dice_str = f"🎲 Kết quả xúc sắc: **{d1} - {d2} - {d3}** (Tổng: **{total}**)"
    
    if luachon.value == result:
        new_score = add_points(user_id, sodiem_cuoc)
        await interaction.response.send_message(f"{dice_str}\n🎉 **CHIẾN THẮNG!** Bạn đoán chính xác và nhận thêm **+{sodiem_cuoc} điểm** (Tổng: `{new_score}`).")
    else:
        new_score = add_points(user_id, -sodiem_cuoc)
        await interaction.response.send_message(f"{dice_str}\n😢 **THẤT BẠI!** Bạn đoán sai và mất **-{sodiem_cuoc} điểm** (Còn lại: `{new_score}`).")

# 4. LỆNH NUÔI THÚ (/nuoithu)
@bot.tree.command(name="nuoithu", description="Hệ thống nuôi thú ảo, cho ăn và đi săn điểm!")
@app_commands.choices(hanhdong=[
    app_commands.Choice(name="Xem Thú Cưng", value="xem"),
    app_commands.Choice(name="Cho Ăn (-20 điểm)", value="an"),
    app_commands.Choice(name="Đi Săn Thưởng", value="san")
])
async def nuoithu(interaction: discord.Interaction, hanhdong: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    pets = load_pets()
    
    if hanhdong.value == "xem":
        if user_id not in pets:
            pets[user_id] = {"name": "Trứng Bí Ẩn", "level": 1, "exp": 0, "icon": "🥚"}
            save_pets(pets)
            await interaction.response.send_message("🐣 Bạn vừa nhận được một **Quả Trứng Bí Ẩn**! Hãy chăm sóc cho ăn để trứng sớm nở thành Thú Cưng nhé.")
        else:
            p = pets[user_id]
            await interaction.response.send_message(f"🐾 **Thú Cưng Của Bạn:**\n- Loài/Tên: {p['icon']} **{p['name']}**\n- Cấp độ: `{p['level']}`\n- EXP: `{p['exp']}/100`")
            
    elif hanhdong.value == "an":
        if user_id not in pets:
            await interaction.response.send_message("❌ Bạn chưa có thú cưng! Hãy chọn 'Xem Thú Cưng' để nhận trứng trước.", ephemeral=True)
            return
            
        data = load_data()
        current_pts = data.get(user_id, {}).get("weekly", 0)
        if current_pts < 20:
            await interaction.response.send_message("❌ Bạn không đủ **20 điểm tuần** để mua thức ăn!", ephemeral=True)
            return
            
        add_points(user_id, -20)
        p = pets[user_id]
        p['exp'] += 35
        
        msg = f"🍖 Bạn đã mua thức ăn cho **{p['name']}** (-20 điểm tuần). Thú cưng nhận `+35 EXP`!"
        if p['exp'] >= 100:
            p['level'] += 1
            p['exp'] = 0
            if p['level'] == 2:
                p['name'] = "Hỏa Long Nhỏ"
                p['icon'] = "🐉"
            elif p['level'] >= 3:
                p['name'] = "Thần Long Tối Thượng"
                p['icon'] = "👑🐉"
            msg += f"\n🎉 **TIẾN HÓA!** Thú cưng của bạn đã tăng lên Cấp **{p['level']}** (`{p['name']}`)!"
            
        save_pets(pets)
        await interaction.response.send_message(msg)
        
    elif hanhdong.value == "san":
        if user_id not in pets:
            await interaction.response.send_message("❌ Bạn chưa có thú cưng!", ephemeral=True)
            return
        p = pets[user_id]
        reward = random.randint(15, 45) * p['level']
        new_score = add_points(user_id, reward)
        await interaction.response.send_message(f"🗡️ Thú cưng {p['icon']} **{p['name']}** đã đi săn và mang về **+{reward} điểm tuần**! (Tổng điểm: `{new_score}`).")

# 5. LỆNH CÂU SÔNG (/causong)
@bot.tree.command(name="causong", description="Thư giãn đi câu cá bờ sông kiếm điểm thưởng!")
@app_commands.checks.cooldown(1, 120)
async def causong(interaction: discord.Interaction):
    fishes = [
        {"name": "Cá Rô Đồng", "pts": 15, "icon": "🐟"},
        {"name": "Cá Chép Vàng", "pts": 30, "icon": "🐠"},
        {"name": "Cá Tầm", "pts": 50, "icon": "🦈"},
        {"name": "Giày Cũ Bị Rách", "pts": 0, "icon": "👞"},
        {"name": "Rương Báu Dưới Sông", "pts": 100, "icon": "👑"}
    ]
    caught = random.choices(fishes, weights=[40, 30, 15, 10, 5])[0]
    user_id = str(interaction.user.id)
    
    if caught["pts"] > 0:
        new_score = add_points(user_id, caught["pts"])
        await interaction.response.send_message(f"🎣 Bạn quăng cần câu bờ sông và bắt được {caught['icon']} **{caught['name']}**! Nhận ngay **+{caught['pts']} điểm** (Tổng: `{new_score}`).")
    else:
        await interaction.response.send_message(f"🎣 Xui xẻo quá! Bạn chỉ kéo lên được {caught['icon']} **{caught['name']}** và không nhận được điểm nào.")

@causong.error
async def causong_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Cá đang sợ bóng người! Hãy chờ `{int(error.retry_after)}s` nữa để tiếp tục quăng cần.", ephemeral=True)

# 6. LỆNH XÌ DÁCH (/xidach)
@bot.tree.command(name="xidach", description="Chơi một ván Xì Dách (Blackjack) nhanh với Bot!")
async def xidach(interaction: discord.Interaction, sodiem_cuoc: int):
    user_id = str(interaction.user.id)
    data = load_data()
    current_pts = data.get(user_id, {}).get("weekly", 0)
    
    if sodiem_cuoc <= 0:
        await interaction.response.send_message("❌ Số điểm cược phải lớn hơn 0!", ephemeral=True)
        return
    if current_pts < sodiem_cuoc:
        await interaction.response.send_message(f"❌ Bạn không đủ điểm cược! Điểm tuần hiện tại: `{current_pts}`.", ephemeral=True)
        return

    player_card1, player_card2 = random.randint(1, 11), random.randint(1, 11)
    bot_card1, bot_card2 = random.randint(1, 11), random.randint(1, 11)
    
    player_total = player_card1 + player_card2
    bot_total = bot_card1 + bot_card2
    
    msg = f"🃏 **VÁN XÌ DÁCH NHANH**\n- Bài của bạn: `[{player_card1}] + [{player_card2}]` = **{player_total} điểm**\n- Bài của Bot: `[{bot_card1}] + [{bot_card2}]` = **{bot_total} điểm**\n\n"
    
    if player_total > 21 and bot_total > 21:
        msg += "🤝 Cả hai cùng quắc! Hoà tiền cược."
    elif player_total > 21:
        add_points(user_id, -sodiem_cuoc)
        msg += f"💥 Bạn bị quắc (vượt quá 21)! Bạn mất **-{sodiem_cuoc} điểm**."
    elif bot_total > 21 or player_total > bot_total:
        add_points(user_id, sodiem_cuoc)
        msg += f"🎉 **THẮNG RỒI!** Bạn vượt điểm Bot và nhận **+{sodiem_cuoc} điểm**!"
    elif player_total < bot_total:
        add_points(user_id, -sodiem_cuoc)
        msg += f"😢 **THUA RỒI!** Điểm Bot cao hơn và bạn mất **-{sodiem_cuoc} điểm**."
    else:
        msg += "🤝 Hai bên bằng điểm! Hoà tiền cược."
        
    await interaction.response.send_message(msg)

# 7. LỆNH BẢNG XẾP HẠNG
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

# 8. CÁC LỆNH ADMIN
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

# --- 6. CHẠY BOT VỚI TOKEN TỪ BIẾN MÔI TRƯỜNG ---
keep_alive()
TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)

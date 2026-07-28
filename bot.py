import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os
from flask import Flask
from threading import Thread

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

# --- 2. QUẢN LÝ DỮ LIỆU ĐIỂM (LƯU FILE JSON) ---
DATA_FILE = "user_points.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_points(user_id: str, amount: int):
    data = load_data()
    if user_id not in data:
        data[user_id] = {"weekly": 0, "total": 0}
    
    data[user_id]["weekly"] += amount
    data[user_id]["total"] += amount
    save_data(data)
    return data[user_id]["weekly"]

# --- 3. CẤU HÌNH BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot đã online: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} lệnh Slash (/)...")
    except Exception as e:
        print(f"Lỗi sync: {e}")

# --- 4. GAME KHUNG CHAT (ĐỐ VUI & CƯỚP) ---
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
    except TimeoutError:
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

# --- 5. BẢNG XẾP HẠNG & LỆNH ADMIN ---
@bot.tree.command(name="bangxephang", description="Xem Bảng Xếp Hạng điểm tuần!")
async def bangxephang(interaction: discord.Interaction):
    data = load_data()
    sorted_users = sorted(data.items(), key=lambda x: x[1].get("weekly", 0), reverse=True)[:10]
    
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG ĐIỂM TUẦN 🏆", color=discord.Color.gold())
    
    description = ""
    for index, (u_id, score) in enumerate(sorted_users, 1):
        user = bot.get_user(int(u_id))
        name = user.name if user else f"User ID: {u_id}"
        
        icon = "🔹"
        if index == 1: icon = "👹 **[Top 1 - Quỷ Thần]**"
        elif index == 2: icon = "⚔️ **[Top 2 - Thần Thương]**"
        elif index == 3: icon = "🐎 **[Top 3 - Kị Vương]**"
        
        description += f"{index}. {icon} {name} — `{score.get('weekly', 0)} điểm`\n"
        
    embed.description = description if description else "Chưa có dữ liệu điểm tuần này."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="point_edit", description="[ADMIN] Thay đổi điểm của người chơi")
@app_commands.checks.has_permissions(administrator=True)
async def point_edit(interaction: discord.Interaction, user: discord.User, amount: int):
    new_score = add_points(str(user.id), amount)
    await interaction.response.send_message(f"✅ Đã chỉnh điểm cho {user.mention}. Điểm tuần mới: `{new_score}`.")

@bot.tree.command(name="danhhieu_grant", description="[ADMIN] Trao danh hiệu cho thành viên")
@app_commands.checks.has_permissions(administrator=True)
async def danhhieu_grant(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    await user.add_roles(role)
    await interaction.response.send_message(f"🎉 Đã trao danh hiệu **{role.name}** cho {user.mention}!")

# --- 6. CHẠY BOT VỚI TOKEN TỪ BIẾN MÔI TRƯỜNG ---
keep_alive()
TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)

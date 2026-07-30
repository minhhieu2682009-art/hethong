import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
from typing import Optional, Dict, Any
import os
from flask import Flask
from threading import Thread

# ==========================================
# CẤU HÌNH & KHỞI TẠO BOT
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

ADMIN_IDS = [123456789012345678] 

# Database lưu trữ
database = {
    "users": {},
    "shops": {"fish": [], "pet": []},
    "questions": [
        {"question": "Con gì chân dài nhất?", "answer": "con đê"},
        {"question": "Cái gì càng thâu càng ngắn?", "answer": "điếu thuốc"},
        {"question": "Nắng ba năm tôi không bỏ bạn, mưa 1 ngày bạn bỏ tôi. Là cái gì?", "answer": "cái bóng"},
        {"question": "Bệnh gì bác sĩ bó tay?", "answer": "gãy tay"},
        {"question": "Lịch nào dài nhất?", "answer": "lịch sử"}
    ],
    "cooldowns": {},
    "game_channel_id": None  # Lưu ID kênh chơi game
}

# Biến quản lý trạng thái câu hỏi tự động hiện tại
current_quiz = {
    "question": None,
    "answer": None,
    "is_active": False
}

def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.user.id in ADMIN_IDS:
        return True
    if interaction.guild and interaction.user.guild_permissions.administrator:
        return True
    return False

def get_user_data(user_id: int):
    if user_id not in database["users"]:
        database["users"][user_id] = {
            "points": 1000,
            "weekly_points": 0,
            "title": "Tân thủ",
            "icon": "🔰",
            "pet": {"name": "Linh Thú", "power": 100, "exp": 0, "level": 1}
        }
    return database["users"][user_id]

# ==========================================
# HỆ THỐNG ĐỐ VUI TỰ ĐỘNG (1 GIỜ / LẦN - 60S TRẢ LỜI)
# ==========================================

# 1. Lệnh cài đặt kênh game
@bot.tree.command(name="set_game_channel", description="Cài đặt kênh xuất hiện câu hỏi đố vui tự động (Admin)")
async def set_game_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Chỉ có Admin mới được cài đặt kênh game!", ephemeral=True)
        return

    database["game_channel_id"] = channel.id
    embed = discord.Embed(
        title="⚙️ CÀI ĐẶT KÊNH GAME THÀNH CÔNG",
        description=f"✅ Từ bây giờ, các câu hỏi đố vui tự động sẽ xuất hiện tại kênh: {channel.mention}\n⏰ Tần suất: **1 giờ / lần** (Có **60 giây** để trả lời).",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# 2. Vòng lặp tự động tạo câu hỏi mỗi 1 giờ
@tasks.loop(hours=1)
async def auto_quiz_task():
    channel_id = database["game_channel_id"]
    if not channel_id or not database["questions"]:
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        return

    # Chọn ngẫu nhiên 1 câu hỏi
    quiz = random.choice(database["questions"])
    current_quiz["question"] = quiz["question"]
    current_quiz["answer"] = quiz["answer"].lower().strip()
    current_quiz["is_active"] = True

    embed = discord.Embed(
        title="🧠 CÂU HỎI ĐỐ VUI TỰ ĐỘNG 🧠",
        description=f"❓ **{current_quiz['question']}**\n\n⏳ Bạn có **60 giây** để nhập câu trả lời trực tiếp vào kênh này!",
        color=discord.Color.gold()
    )
    embed.set_footer(text="🎁 Trả lời đúng nhận ngẫu nhiên từ 1 đến 100 điểm!")
    await channel.send(embed=embed)

    # Chờ 60 giây
    await asyncio.sleep(60)

    # Nếu sau 60 giây vẫn chưa ai trả lời đúng
    if current_quiz["is_active"]:
        current_quiz["is_active"] = False
        timeout_embed = discord.Embed(
            title="⏰ HẾT GIỜ TRẢ LỜI!",
            description=f"Chưa có ai đưa ra câu trả lời chính xác.\n💡 Đáp án đúng là: **{current_quiz['answer']}**",
            color=discord.Color.red()
        )
        await channel.send(embed=timeout_embed)

# 3. Bắt tin nhắn trả lời của người chơi
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Chỉ kiểm tra nếu đúng kênh game và đang trong thời gian trả lời
    if database["game_channel_id"] and message.channel.id == database["game_channel_id"]:
        if current_quiz["is_active"]:
            user_answer = message.content.lower().strip()
            
            # Nếu người chơi đoán ĐÚNG
            if user_answer == current_quiz["answer"]:
                current_quiz["is_active"] = False  # Đóng câu hỏi lập tức
                
                # Thưởng điểm ngẫu nhiên 1 - 100
                reward_points = random.randint(1, 100)
                u_data = get_user_data(message.author.id)
                u_data["points"] += reward_points
                u_data["weekly_points"] += reward_points

                win_embed = discord.Embed(
                    title="🎉 CHÚC MỪNG BẠN ĐÃ TRẢ LỜI ĐÚNG! 🎉",
                    description=f"CHÍNH XÁC! {message.author.mention} đã trả lời đúng đáp án **{current_quiz['answer']}**!\n🎁 Bạn nhận được **+{reward_points} Điểm** thưởng.",
                    color=discord.Color.green()
                )
                await message.channel.send(embed=win_embed)
                return
            
            # Nếu đoán SAI: Bot hoàn toàn giữ im lặng (không gửi tin nhắn) để tránh làm rác kênh chat!

    await bot.process_commands(message)

# ==========================================
# 1. CƠ CHẾ /pvp_pet
# ==========================================
class PetPVPConfirmView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="Đồng ý Thách Đấu ⚔️", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Đây không phải lời mời dành cho bạn!", ephemeral=True)
            return

        p1_data = get_user_data(self.challenger.id)["pet"]
        p2_data = get_user_data(self.opponent.id)["pet"]

        if not p1_data or not p2_data:
            await interaction.response.send_message("❌ Một trong hai người chơi chưa sở hữu Pet!", ephemeral=True)
            return

        power1 = p1_data["power"]
        power2 = p2_data["power"]
        diff = abs(power1 - power2)

        if power1 == power2:
            win_rate_p1 = 0.50
        elif power1 > power2:
            if 10 <= diff <= 1000:
                win_rate_p1 = 0.60
            elif 1000 < diff <= 2000:
                win_rate_p1 = 0.70
            else:
                win_rate_p1 = 1.00
        else:
            if 10 <= diff <= 1000:
                win_rate_p1 = 0.40
            elif 1000 < diff <= 2000:
                win_rate_p1 = 0.30
            else:
                win_rate_p1 = 0.00

        winner = self.challenger if random.random() < win_rate_p1 else self.opponent

        embed = discord.Embed(
            title="⚔️ TỔNG KẾT TRẬN ĐẤU PET ⚔️",
            color=discord.Color.gold()
        )
        embed.add_field(name=f"🎮 {self.challenger.display_name}", value=f"🐾 Pet: **{p1_data['name']}**\n⚡ Lực chiến: **{power1}**", inline=True)
        embed.add_field(name=f"🎮 {self.opponent.display_name}", value=f"🐾 Pet: **{p2_data['name']}**\n⚡ Lực chiến: **{power2}**", inline=True)
        embed.add_field(name="🏆 KẾT QUẢ CHÍNH THỨC", value=f"🎉 **{winner.mention}** đã giành chiến thắng thuyết phục!", inline=False)
        
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="💥 **TRẬN ĐẤU ĐÃ BẮT ĐẦU!**", embed=embed, view=self)

    @discord.ui.button(label="Từ chối 🛡️", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Bạn không có quyền hủy lời mời này!", ephemeral=True)
            return
        await interaction.response.send_message(f"🛡️ {self.opponent.mention} đã từ chối lời thách đấu.")
        self.stop()

@bot.tree.command(name="pvp_pet", description="Thách đấu Pet với người chơi khác")
async def pvp_pet(interaction: discord.Interaction, opponent: discord.Member):
    if opponent.id == interaction.user.id:
        await interaction.response.send_message("❌ Bạn không thể tự thách đấu chính mình!", ephemeral=True)
        return
    
    view = PetPVPConfirmView(interaction.user, opponent)
    embed = discord.Embed(
        title="⚔️ LỜI THÁCH ĐẤU PET ⚔️",
        description=f"🔥 **{interaction.user.mention}** đã thách đấu Pet với **{opponent.mention}**!\nBạn có chấp nhận lời thách đấu này không?",
        color=discord.Color.red()
    )
    await interaction.response.send_message(content=opponent.mention, embed=embed, view=view)

# ==========================================
# 2. HỆ THỐNG SHOP (/shop)
# ==========================================
class AddItemModal(discord.ui.Modal):
    def __init__(self, shop_type: str):
        super().__init__(title=f"➕ Thêm Vật Phẩm Vào Shop {shop_type.upper()}")
        self.shop_type = shop_type

        self.item_name = discord.ui.TextInput(label="Tên vật phẩm", placeholder="VD: Trái Đột Biến")
        self.price = discord.ui.TextInput(label="Giá bán (Điểm)", placeholder="VD: 500")
        self.rarity = discord.ui.TextInput(label="Độ hiếm", placeholder="Thường / Hiếm / Thần Thoại")
        self.buff_type = discord.ui.TextInput(label="Loại Buff", placeholder="power_up / exp_up", required=False)
        self.buff_value = discord.ui.TextInput(label="Giá trị Buff", placeholder="VD: 50", required=False)

        self.add_item(self.item_name)
        self.add_item(self.price)
        self.add_item(self.rarity)
        self.add_item(self.buff_type)
        self.add_item(self.buff_value)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = float(self.buff_value.value) if self.buff_value.value else 0
            new_item = {
                "id": len(database["shops"][self.shop_type]) + 1,
                "name": self.item_name.value,
                "price": int(self.price.value),
                "rarity": self.rarity.value,
                "buff_type": self.buff_type.value or "None",
                "buff_value": val
            }
            database["shops"][self.shop_type].append(new_item)
            await interaction.response.send_message(f"✅ Đã thêm **{new_item['name']}** vào Shop!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Giá trị nhập vào không hợp lệ!", ephemeral=True)

class BuySelectView(discord.ui.View):
    def __init__(self, shop_type: str, user_id: int):
        super().__init__(timeout=60)
        self.shop_type = shop_type
        self.user_id = user_id
        
        items = database["shops"][shop_type]
        options = []
        for item in items:
            buff_str = f"| Buff: {item['buff_type']} (+{item['buff_value']})" if item['buff_type'] != "None" else ""
            options.append(discord.SelectOption(
                label=f"{item['name']} ({item['rarity']})",
                value=str(item['id']),
                description=f"Giá: {item['price']} Điểm {buff_str}",
                emoji="🛒"
            ))
        
        if options:
            select = discord.ui.Select(placeholder="🛒 Chọn vật phẩm...", options=options)
            select.callback = self.buy_callback
            self.add_item(select)

    async def buy_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không tạo menu này!", ephemeral=True)
            return

        item_id = int(interaction.data['values'][0])
        item = next((i for i in database["shops"][self.shop_type] if i["id"] == item_id), None)
        u_data = get_user_data(interaction.user.id)

        if not item or u_data["points"] < item["price"]:
            await interaction.response.send_message("❌ Không thể mua vật phẩm này!", ephemeral=True)
            return

        u_data["points"] -= item["price"]
        effect_msg = ""
        if item["buff_type"] == "power_up" and u_data["pet"]:
            u_data["pet"]["power"] += int(item["buff_value"])
            effect_msg = f"\n⚡ Pet +{item['buff_value']} Lực chiến!"
        elif item["buff_type"] == "exp_up" and u_data["pet"]:
            u_data["pet"]["exp"] += int(item["buff_value"])
            effect_msg = f"\n🌟 Pet +{item['buff_value']} EXP!"

        embed = discord.Embed(
            title="🎉 MUA HÀNG THÀNH CÔNG 🎉",
            description=f"Đã mua **{item['name']}**!\n💰 Số dư: **{u_data['points']} Điểm**{effect_msg}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ShopMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cửa Hàng Cá 🎣", style=discord.ButtonStyle.primary, custom_id="shop_fish_btn")
    async def fish_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.display_shop(interaction, "fish")

    @discord.ui.button(label="Cửa Hàng Pet 🐾", style=discord.ButtonStyle.success, custom_id="shop_pet_btn")
    async def pet_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.display_shop(interaction, "pet")

    @discord.ui.button(label="Thêm Vật Phẩm (Admin) ➕", style=discord.ButtonStyle.danger, custom_id="shop_add_btn")
    async def add_item_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Chỉ có Admin mới dùng được!", ephemeral=True)
            return
        
        view = discord.ui.View()
        btn_fish = discord.ui.Button(label="Shop Cá 🎣", style=discord.ButtonStyle.primary)
        btn_pet = discord.ui.Button(label="Shop Pet 🐾", style=discord.ButtonStyle.success)

        async def cb_fish(i): await i.response.send_modal(AddItemModal("fish"))
        async def cb_pet(i): await i.response.send_modal(AddItemModal("pet"))

        btn_fish.callback = cb_fish
        btn_pet.callback = cb_pet
        view.add_item(btn_fish)
        view.add_item(btn_pet)

        await interaction.response.send_message("🛠️ Chọn shop muốn thêm:", view=view, ephemeral=True)

    async def display_shop(self, interaction: discord.Interaction, shop_type: str):
        items = database["shops"][shop_type]
        embed = discord.Embed(title=f"🏪 CỬA HÀNG {shop_type.upper()}", color=discord.Color.teal())
        if not items:
            embed.description = "🕸️ Shop hiện tại đang trống!"
        else:
            for item in items:
                embed.add_field(name=f"📦 {item['name']} [{item['rarity']}]", value=f"💵 Giá: **{item['price']} Điểm**", inline=False)

        view = BuySelectView(shop_type, interaction.user.id) if items else None
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="shop", description="Mở cửa hàng trung tâm")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ HỆ THỐNG CỬA HÀNG TRUNG TÂM ✨", color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, view=ShopMainView())

# ==========================================
# 3. /nuoithu
# ==========================================
class AddPetModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🐾 Thêm Pet Mới (Admin)")
        self.pet_name = discord.ui.TextInput(label="Tên Pet", placeholder="VD: Rồng Lửa")
        self.base_power = discord.ui.TextInput(label="Lực chiến ban đầu", placeholder="VD: 500")
        self.add_item(self.pet_name)
        self.add_item(self.base_power)

    async def on_submit(self, interaction: discord.Interaction):
        u_data = get_user_data(interaction.user.id)
        u_data["pet"] = {"name": self.pet_name.value, "power": int(self.base_power.value), "exp": 0, "level": 1}
        await interaction.response.send_message(f"✅ Đã tạo Pet **{self.pet_name.value}**!", ephemeral=True)

class NuoiThuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cho Pet Ăn (100EXP) - 500 Điểm 🍖", style=discord.ButtonStyle.success)
    async def feed_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        u_data = get_user_data(interaction.user.id)
        pet = u_data["pet"]

        if not pet or u_data["points"] < 500:
            await interaction.response.send_message("❌ Không đủ điều kiện cho Pet ăn!", ephemeral=True)
            return

        u_data["points"] -= 500
        pet["exp"] += 100
        
        if pet["exp"] >= 500:
            pet["level"] += 1
            pet["power"] += 50
            pet["exp"] -= 500
            msg = f"🎉 Pet **{pet['name']}** lên **Lv.{pet['level']}** (+50 Lực chiến)!"
        else:
            msg = f"🍖 **{pet['name']}** đã ăn! Tăng +100 EXP."

        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="Thêm Pet (Admin) 🐾", style=discord.ButtonStyle.danger)
    async def add_pet_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Chỉ có Admin mới dùng được!", ephemeral=True)
            return
        await interaction.response.send_modal(AddPetModal())

@bot.tree.command(name="nuoithu", description="Bảng quản lý nuôi thú")
async def nuoithu(interaction: discord.Interaction):
    u_data = get_user_data(interaction.user.id)
    pet = u_data["pet"]

    embed = discord.Embed(title="🐾 TRANG TRẠI NUÔI THÚ 🐾", color=discord.Color.green())
    if pet:
        embed.add_field(name="📛 Tên Pet", value=f"**{pet['name']}**", inline=True)
        embed.add_field(name="⭐ Cấp độ", value=f"**Lv.{pet['level']}**", inline=True)
        embed.add_field(name="⚡ Lực chiến", value=f"**{pet['power']}**", inline=True)
        embed.add_field(name="🌟 EXP", value=f"**{pet['exp']}/500**", inline=True)
    else:
        embed.description = "❌ Bạn chưa có Pet nào."

    await interaction.response.send_message(embed=embed, view=NuoiThuView())

# ==========================================
# 4. /causong
# ==========================================
class CauSongView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Thả Cần Câu Cá 🎣", style=discord.ButtonStyle.primary)
    async def fish_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        now = asyncio.get_event_loop().time()
        
        if user_id in database["cooldowns"]:
            elapsed = now - database["cooldowns"][user_id]
            if elapsed < 5:
                await interaction.response.send_message(f"⏳ Chờ **{5 - elapsed:.1f}s** nữa!", ephemeral=True)
                return

        database["cooldowns"][user_id] = now
        await interaction.response.defer()
        await asyncio.sleep(5)

        fishes = ["🐟 Cá Chép", "🐠 Cá Hề", "🐉 Cá Rồng", "👞 Giầy Cũ"]
        result = random.choice(fishes)
        
        embed = discord.Embed(
            title="🎣 KẾT QUẢ CÂU SÔNG 🎣",
            description=f"🎉 {interaction.user.mention} câu được: **{result}**!",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="causong", description="Khu vực câu cá bên sông")
async def causong(interaction: discord.Interaction):
    embed = discord.Embed(title="🌊 KHU VỰC CÂU SÔNG 🌊", description="Bấm **Thả Cần Câu Cá** và chờ 5 giây!", color=discord.Color.dark_blue())
    await interaction.response.send_message(embed=embed, view=CauSongView())

# ==========================================
# 5. /danhboss
# ==========================================
class BossView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Tấn Công Boss ⚔️", style=discord.ButtonStyle.danger)
    async def attack_boss(self, interaction: discord.Interaction, button: discord.ui.Button):
        dmg = random.randint(100, 500)
        embed = discord.Embed(
            title="⚔️ TRẬN CHIẾN BOSS ⚔️",
            description=f"🔥 **{interaction.user.mention}** gây **{dmg} sát thương**!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="danhboss", description="Khu vực săn Boss thế giới")
async def danhboss(interaction: discord.Interaction):
    embed = discord.Embed(title="👹 SẢNH CHỜ CHIẾN BOSS 👹", color=discord.Color.dark_red())
    await interaction.response.send_message(embed=embed, view=BossView())

# ==========================================
# 6. QUẢN LÝ ADMIN
# ==========================================
@bot.tree.command(name="add_question", description="Thêm câu hỏi đố vui mới vào ngân hàng (Admin)")
async def add_question(interaction: discord.Interaction, question: str, answer: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Chỉ có Admin mới dùng được!", ephemeral=True)
        return

    database["questions"].append({"question": question, "answer": answer.lower().strip()})
    embed = discord.Embed(title="🧠 THÊM CÂU HỎI MỚI THÀNH CÔNG", color=discord.Color.purple())
    embed.add_field(name="❓ Câu hỏi", value=question, inline=False)
    embed.add_field(name="💡 Đáp án", value=f"`{answer}`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="point_edit", description="Cộng/Trừ điểm thành viên (Admin)")
async def point_edit(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Chỉ có Admin mới dùng được!", ephemeral=True)
        return

    u_data = get_user_data(user.id)
    u_data["points"] += amount
    u_data["weekly_points"] += amount
    await interaction.response.send_message(f"✅ Đã chỉnh điểm cho {user.mention}. Số dư mới: **{u_data['points']}**")

@bot.tree.command(name="bangxephang", description="Xem bảng xếp hạng")
async def bangxephang(interaction: discord.Interaction):
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG CAO THỦ 🏆", color=discord.Color.gold())
    embed.add_field(name="👑 Hạng 1", value=f"{interaction.user.mention} - 1000 Điểm", inline=False)
    await interaction.response.send_message(embed=embed)

# ==========================================
# KHỞI CHẠY BOT & FLASK KEEPALIVE
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot đang hoạt động 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

@bot.event
async def on_ready():
    await bot.tree.sync()
    # Kích hoạt vòng lặp tự động hỏi đố vui 1 tiếng/lần
    if not auto_quiz_task.is_running():
        auto_quiz_task.start()
    print(f"🤖 Bot {bot.user} đã sẵn sàng và kích hoạt tính năng tự động đố vui!")

keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ LỖI: Chưa cấu hình DISCORD_TOKEN!")

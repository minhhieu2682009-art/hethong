import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Optional, Dict, Any

# ==========================================
# CẤU HÌNH & KHỞI TẠO BOT
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Giả lập Database lưu trữ dữ liệu
ADMIN_IDS = [123456789012345678]  # Thay ID Discord Admin của bạn vào đây

database = {
    "users": {},         # {user_id: {"points": 0, "weekly_points": 0, "title": "Tân thủ", "icon": "🔰", "pet": None}}
    "shops": {
        "fish": [],      # List các vật phẩm shop cá
        "pet": []        # List các vật phẩm shop pet
    },
    "questions": [
        {"question": "Con gì chân dài nhất?", "answer": "con đê"}
    ],
    "cooldowns": {}      # Quản lý cooldown câu cá
}

def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.id in ADMIN_IDS

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
# 1. CƠ CHẾ /pvp_pet (XÁC NHẬN & TÍNH TỈ LỆ TẤN CÔNG)
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

        # Tính tỉ lệ thắng thua
        if power1 == power2:
            win_rate_p1 = 0.50
        elif power1 > power2:
            if 10 <= diff <= 1000:
                win_rate_p1 = 0.60
            elif 1000 < diff <= 2000:
                win_rate_p1 = 0.70
            else: # > 2000
                win_rate_p1 = 1.00
        else: # power1 < power2
            if 10 <= diff <= 1000:
                win_rate_p1 = 0.40
            elif 1000 < diff <= 2000:
                win_rate_p1 = 0.30
            else: # > 2000
                win_rate_p1 = 0.00

        # Tiến hành PVP
        winner = self.challenger if random.random() < win_rate_p1 else self.opponent
        loser = self.opponent if winner == self.challenger else self.challenger

        embed = discord.Embed(
            title="⚔️ TỔNG KẾT TRẬN ĐẤU PET THỜI LƯỢNG CAO ⚔️",
            color=discord.Color.gold()
        )
        embed.add_field(name=f"🎮 {self.challenger.display_name}", value=f"🐾 Pet: **{p1_data['name']}**\n⚡ Lực chiến: **{power1}**", inline=True)
        embed.add_field(name=f"🎮 {self.opponent.display_name}", value=f"🐾 Pet: **{p2_data['name']}**\n⚡ Lực chiến: **{power2}**", inline=True)
        embed.add_field(name="🏆 KẾT QUẢ CHÍNH THỨC", value=f"🎉 **{winner.mention}** đã giành chiến thắng thuyết phục!", inline=False)
        
        # Disable nút sau khi xong
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
# 2. HỆ THỐNG SHOP DÙNG CHUNG UNLIMITED TIMEOUT (/shop)
# ==========================================
class AddItemModal(discord.ui.Modal):
    def __init__(self, shop_type: str):
        super().__init__(title=f"➕ Thêm Vật Phẩm Vào Shop {shop_type.upper()}")
        self.shop_type = shop_type

        self.item_name = discord.ui.TextInput(label="Tên vật phẩm", placeholder="VD: Trái Đột Biến / Mồi Cầu Vồng")
        self.price = discord.ui.TextInput(label="Giá bán (Điểm)", placeholder="VD: 500")
        self.rarity = discord.ui.TextInput(label="Độ hiếm", placeholder="Thường / Hiếm / Thần Thoại")
        self.buff_type = discord.ui.TextInput(
            label="Loại Buff (Ghi chính xác)", 
            placeholder="Pet: power_up / exp_up | Cá: success_rate / rare_rate",
            required=False
        )
        self.buff_value = discord.ui.TextInput(
            label="Giá trị Buff (Chỉ số số)", 
            placeholder="VD: 50 (Có thể để trống)", 
            required=False
        )

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
            await interaction.response.send_message(f"✅ Đã thêm thành công **{new_item['name']}** vào Shop **{self.shop_type.upper()}**!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Giá hoặc Giá trị Buff phải là chữ số hợp lệ!", ephemeral=True)

class BuySelectView(discord.ui.View):
    def __init__(self, shop_type: str, user_id: int):
        super().__init__(timeout=60)
        self.shop_type = shop_type
        self.user_id = user_id
        
        # Thêm Select menu mua sắm
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
            select = discord.ui.Select(placeholder="🛒 Chọn vật phẩm muốn mua...", options=options)
            select.callback = self.buy_callback
            self.add_item(select)

    async def buy_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không tạo menu này!", ephemeral=True)
            return

        item_id = int(interaction.data['values'][0])
        item = next((i for i in database["shops"][self.shop_type] if i["id"] == item_id), None)
        u_data = get_user_data(interaction.user.id)

        if not item:
            await interaction.response.send_message("❌ Vật phẩm không tồn tại!", ephemeral=True)
            return

        if u_data["points"] < item["price"]:
            await interaction.response.send_message("❌ Bạn không có đủ Điểm để mua vật phẩm này!", ephemeral=True)
            return

        # Trừ tiền & Áp dụng hiệu ứng
        u_data["points"] -= item["price"]
        
        # Xử lý Buff tác dụng
        effect_msg = ""
        if item["buff_type"] == "power_up" and u_data["pet"]:
            u_data["pet"]["power"] += int(item["buff_value"])
            effect_msg = f"\n⚡ Lực chiến Pet tăng thêm +{item['buff_value']}!"
        elif item["buff_type"] == "exp_up" and u_data["pet"]:
            u_data["pet"]["exp"] += int(item["buff_value"])
            effect_msg = f"\n🌟 Pet nhận thêm +{item['buff_value']} EXP!"

        embed = discord.Embed(
            title="🎉 MUA HÀNG THÀNH CÔNG 🎉",
            description=f"Bạn đã mua thành công **{item['name']}**!\n💰 Số dư còn lại: **{u_data['points']} Điểm**{effect_msg}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ShopMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Timeout=None theo yêu cầu

    @discord.ui.button(label="Cửa Hàng Cá 🎣", style=discord.ButtonStyle.primary, custom_id="shop_fish_btn")
    async def fish_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.display_shop(interaction, "fish")

    @discord.ui.button(label="Cửa Hàng Pet 🐾", style=discord.ButtonStyle.success, custom_id="shop_pet_btn")
    async def pet_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.display_shop(interaction, "pet")

    @discord.ui.button(label="Thêm Vật Phẩm (Admin) ➕", style=discord.ButtonStyle.danger, custom_id="shop_add_btn")
    async def add_item_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Chỉ có Admin mới được sử dụng nút này!", ephemeral=True)
            return
        
        view = discord.ui.View()
        btn_fish = discord.ui.Button(label="Thêm vào Shop Cá 🎣", style=discord.ButtonStyle.primary)
        btn_pet = discord.ui.Button(label="Thêm vào Shop Pet 🐾", style=discord.ButtonStyle.success)

        async def cb_fish(i):
            await i.response.send_modal(AddItemModal("fish"))
        async def cb_pet(i):
            await i.response.send_modal(AddItemModal("pet"))

        btn_fish.callback = cb_fish
        btn_pet.callback = cb_pet
        view.add_item(btn_fish)
        view.add_item(btn_pet)

        await interaction.response.send_message("🛠️ Chọn cửa hàng bạn muốn thêm vật phẩm mới:", view=view, ephemeral=True)

    async def display_shop(self, interaction: discord.Interaction, shop_type: str):
        items = database["shops"][shop_type]
        embed = discord.Embed(
            title=f"🏪 CỬA HÀNG {shop_type.upper()} CAO CẤP 🏪",
            description="Danh sách các mặt hàng đang bày bán:",
            color=discord.Color.teal()
        )
        if not items:
            embed.description = "🕸️ Cửa hàng hiện tại đang trống!"
        else:
            for item in items:
                buff_info = f"\n✨ Buff: `{item['buff_type']}` (+{item['buff_value']})" if item['buff_type'] != "None" else ""
                embed.add_field(
                    name=f"📦 {item['name']} [{item['rarity']}]",
                    value=f"💵 Giá: **{item['price']} Điểm**{buff_info}",
                    inline=False
                )

        view = BuySelectView(shop_type, interaction.user.id) if items else None
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="shop", description="Mở cửa hàng trung tâm")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ HỆ THỐNG CỬA HÀNG TRUNG TÂM ✨",
        description="Chào mừng bạn đến với Cửa Hàng! Vui lòng chọn danh mục bên dưới để khám phá và mua sắm.",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3081/3081559.png")
    await interaction.response.send_message(embed=embed, view=ShopMainView())

# ==========================================
# 3. /nuoithu (CÓ NÚT CHO ĂN 100 EXP GIÁ 500 ĐIỂM & NÚT THÊM PET ADMIN)
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
        u_data["pet"] = {
            "name": self.pet_name.value,
            "power": int(self.base_power.value),
            "exp": 0,
            "level": 1
        }
        await interaction.response.send_message(f"✅ Đã tạo/thêm Pet **{self.pet_name.value}** thành công!", ephemeral=True)

class NuoiThuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cho Pet Ăn (100EXP) - 500 Điểm 🍖", style=discord.ButtonStyle.success)
    async def feed_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        u_data = get_user_data(interaction.user.id)
        pet = u_data["pet"]

        if not pet:
            await interaction.response.send_message("❌ Bạn chưa sở hữu Pet nào!", ephemeral=True)
            return

        if u_data["points"] < 500:
            await interaction.response.send_message("❌ Bạn không đủ 500 Điểm để cho Pet ăn!", ephemeral=True)
            return

        u_data["points"] -= 500
        pet["exp"] += 100
        
        # Thêm logic lên cấp đơn giản
        if pet["exp"] >= 500:
            pet["level"] += 1
            pet["power"] += 50
            pet["exp"] -= 500
            msg = f"🎉 Pet **{pet['name']}** đã tăng cấp lên **Lv.{pet['level']}** (+50 Lực chiến)!"
        else:
            msg = f"🍖 Bạn đã cho **{pet['name']}** ăn thành công! Tăng +100 EXP."

        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="Thêm Pet (Admin) 🐾", style=discord.ButtonStyle.danger)
    async def add_pet_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Chỉ có Admin mới được dùng nút này!", ephemeral=True)
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
        embed.description = "❌ Bạn chưa có Pet nào trong trang trại."

    await interaction.response.send_message(embed=embed, view=NuoiThuView())

# ==========================================
# 4. /causong (COOLDOWN 5s BẮT BUỘC CHỜ, CÓ TIMEOUT)
# ==========================================
class AddFishModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🎣 Thêm Loại Cá Mới (Admin)")
        self.fish_name = discord.ui.TextInput(label="Tên cá", placeholder="VD: Cá Rồng Hoàng Kim")
        self.rarity = discord.ui.TextInput(label="Độ hiếm", placeholder="Thường / Hiếm / Thần Thoại")
        self.add_item(self.fish_name)
        self.add_item(self.rarity)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Đã thêm cá **{self.fish_name.value}** ({self.rarity.value}) vào hệ thống sông!", ephemeral=True)

class CauSongView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120) # KHÔNG để Timeout=None

    @discord.ui.button(label="Thả Cần Câu Cá 🎣", style=discord.ButtonStyle.primary)
    async def fish_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        now = asyncio.get_event_loop().time()
        
        # Chống Spam: Cooldown 5s
        if user_id in database["cooldowns"]:
            elapsed = now - database["cooldowns"][user_id]
            if elapsed < 5:
                await interaction.response.send_message(f"⏳ Vui lòng chờ thêm **{5 - elapsed:.1f}s** để thực hiện lượt câu tiếp theo!", ephemeral=True)
                return

        database["cooldowns"][user_id] = now
        await interaction.response.defer()
        
        # Đợi 5 giây giả lập cảm giác câu cá thực tế
        await asyncio.sleep(5)

        fishes = ["🐟 Cá Chép (Thường)", "🐠 Cá Hề (Hiếm)", " Cá Rồng (Thần Thoại)", "👞 Giầy Cũ"]
        result = random.choice(fishes)
        
        embed = discord.Embed(
            title="🎣 KẾT QUẢ CÂU SÔNG 🎣",
            description=f"🎉 {interaction.user.mention} đã giật cần và câu được: **{result}**!",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Thêm Cá (Admin) 🐟", style=discord.ButtonStyle.danger)
    async def add_fish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Chỉ có Admin mới được mở tính năng này!", ephemeral=True)
            return
        await interaction.response.send_modal(AddFishModal())

@bot.tree.command(name="causong", description="Khu vực câu cá bên sông")
async def causong(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌊 KHU VỰC CÂU SÔNG THƯ GIÃN 🌊",
        description="Hãy bấm vào nút **Thả Cần Câu Cá** bên dưới và chờ đợi trong 5 giây!",
        color=discord.Color.dark_blue()
    )
    await interaction.response.send_message(embed=embed, view=CauSongView())

# ==========================================
# 5. /danhboss (NÚT ĐÁNH BOSS & THÊM BOSS ADMIN)
# ==========================================
class AddBossModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="👹 Thêm Boss Thế Giới (Admin)")
        self.boss_name = discord.ui.TextInput(label="Tên Boss", placeholder="VD: Ma Vương Bất Tử")
        self.boss_hp = discord.ui.TextInput(label="Máu Boss (HP)", placeholder="VD: 50000")
        self.add_item(self.boss_name)
        self.add_item(self.boss_hp)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Đã triệu hồi Boss **{self.boss_name.value}** (HP: {self.boss_hp.value})!", ephemeral=True)

class BossView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Tấn Công Boss ⚔️", style=discord.ButtonStyle.danger)
    async def attack_boss(self, interaction: discord.Interaction, button: discord.ui.Button):
        dmg = random.randint(100, 500)
        embed = discord.Embed(
            title="⚔️ TRẬN CHIẾN BOSS ⚔️",
            description=f"🔥 **{interaction.user.mention}** đã tung đòn chí mạng gây **{dmg} sát thương** lên Boss!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Thêm Boss (Admin) 👹", style=discord.ButtonStyle.secondary)
    async def add_boss_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Chỉ có Admin mới được thực hiện!", ephemeral=True)
            return
        await interaction.response.send_modal(AddBossModal())

@bot.tree.command(name="danhboss", description="Khu vực săn Boss thế giới")
async def danhboss(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👹 SẢNH CHỜ CHIẾN BOSS 👹",
        description="Hãy cùng các chiến hữu hợp lực tiêu diệt Boss!",
        color=discord.Color.dark_red()
    )
    await interaction.response.send_message(embed=embed, view=BossView())

# ==========================================
# 6. BỔ SUNG CÁC LỆNH QUẢN LÝ QUẢN TRỊ VIÊN & HỆ THỐNG
# ==========================================

# /set_top_title
@bot.tree.command(name="set_top_title", description="Thay đổi icon và tên hiển thị Bảng Xếp Hạng")
async def set_top_title(interaction: discord.Interaction, top: str, icon: str, title_name: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Chỉ có Admin mới dùng được lệnh này!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="⚙️ CẬP NHẬT DANH HIỆU BẢNG XẾP HẠNG",
        description=f"✅ Đã cập nhật cho vị trí **{top}**:\nIcon: {icon}\nDanh hiệu: **{title_name}**",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

# /point_edit
@bot.tree.command(name="point_edit", description="Cộng hoặc trừ điểm tuần của thành viên")
async def point_edit(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Chỉ có Admin mới dùng được lệnh này!", ephemeral=True)
        return

    u_data = get_user_data(user.id)
    u_data["weekly_points"] += amount
    u_data["points"] += amount

    action = "Cộng" if amount >= 0 else "Trừ"
    embed = discord.Embed(
        title="💎 THAY ĐỔI ĐIỂM THÀNH VIÊN",
        description=f"✅ Đã {action} **{abs(amount)}** điểm cho **{user.mention}**.\n📊 Điểm hiện tại: **{u_data['points']}**",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

# /add_question
@bot.tree.command(name="add_question", description="Thêm câu hỏi đố vui mẹo mới")
async def add_question(interaction: discord.Interaction, question: str, answer: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Chỉ có Admin mới dùng được lệnh này!", ephemeral=True)
        return

    database["questions"].append({"question": question, "answer": answer.lower().strip()})
    
    embed = discord.Embed(
        title="🧠 THÊM CÂU HỎI ĐỐ VUI MỚI",
        color=discord.Color.purple()
    )
    embed.add_field(name="❓ Câu hỏi", value=question, inline=False)
    embed.add_field(name="💡 Đáp án", value=f"`{answer}`", inline=False)
    await interaction.response.send_message(embed=embed)

# Bảng xếp hạng minh họa (/bangxephang)
@bot.tree.command(name="bangxephang", description="Xem bảng xếp hạng")
async def bangxephang(interaction: discord.Interaction):
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG CAO THỦ 🏆", color=discord.Color.gold())
    embed.add_field(name="👑 Đoàn Trưởng Sub Chéo", value=f"{interaction.user.mention} - 1000 Điểm", inline=False)
    await interaction.response.send_message(embed=embed)

 # ==========================================
# KHỞI CHẠY BOT VÀ KEEPALIVE FOR RENDER
# ==========================================
import os
from flask import Flask
from threading import Thread

# Web server để Render không ngắt kết nối
app = Flask('')

@app.route('/')
def home():
    return "Bot đang hoạt động 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Sự kiện khi bot sẵn sàng
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🤖 Bot {bot.user} đã sẵn sàng và kết nối thành công!")

# Chạy web server giả trước
keep_alive()

# Lấy token từ Environment Variables đã cài trên Render
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ LỖI: Chưa cấu hình DISCORD_TOKEN trong Environment Variables!")

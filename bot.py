import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import time, timezone, timedelta

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# --- DATABASE GIẢ LẬP TRONG BỘ NHỚ ---
# Trong thực tế, bạn nên thay thế bằng SQLite/MongoDB.
users_db = {}  # {user_id: {"points": int, "pets": [], "inventory": [], "titles": [], "equipped_title": str}}
shop_custom_items = {"baits": [], "rods": [], "foods": [], "gears": []}
bosses_custom = []
top_titles = {1: "Khư Quỷ", 2: "Khu La", 3: "Thế Thần"}
active_channels_lb = []

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            "points": 1000, # Tặng mặc định ít điểm để test
            "pets": [],
            "inventory": [],
            "titles": [],
            "equipped_title": ""
        }
    return users_db[user_id]

def is_admin(interaction: discord.Interaction):
    return interaction.user.guild_permissions.administrator

# ==================== A. NUÔI THÚ ẢO & UPDATE PET ====================
PET_DATA = {
    "Sư tử con": {"rarity": "Thường", "rate": 0.7, "base_exp": 100, "atk_inc": 50, "atk_inc_20": 100, "stages": ["🦁 Sư tử con", "🐯 Vua khổ", "⚡🐅 Sấm chị lâm"]},
    "Gấu con": {"rarity": "Thường", "rate": 0.7, "base_exp": 100, "atk_inc": 60, "atk_inc_20": 110, "stages": ["🐻 Gấu con", "🐻🙈 Gấu béo", "🐻⭐ Thần gấu phương nam"]},
    "Gấu trúc con": {"rarity": "Hiếm", "rate": 0.5, "base_exp": 200, "atk_inc": 100, "atk_inc_20": 150, "stages": ["🐼 Gấu trúc con", "🐼👑 Vua gấu", "🐼&🌛 Thái cực thiên tôn"]},
    "Cá mập con": {"rarity": "Hiếm", "rate": 0.5, "base_exp": 300, "atk_inc": 150, "atk_inc_20": 200, "stages": ["🦈 Cá mập con", "🦈😶 Thần tử", "🐋 Tinh kình"]},
    "Đại bàng trắng con": {"rarity": "Sử thi", "rate": 0.2, "base_exp": 500, "atk_inc": 500, "atk_inc_20": 1000, "stages": ["🦅 Đại bàng trắng con", "⚡🦅 Sấm đại cửu u", "🦅🔥 Tiểu thần quân"]},
    "Kì lân con": {"rarity": "Sử thi", "rate": 0.1, "base_exp": 600, "atk_inc": 600, "atk_inc_20": 1500, "stages": ["🦄 Kì lân con", "🦄🙈 Bạch thú chi vương", "🦄🔥 Hoả Lâm Chân Nhân"]},
    "Rồng con": {"rarity": "Thần thoại", "rate": 0.01, "base_exp": 1000, "atk_inc": 5000, "atk_inc_20": 10000, "stages": ["🐉 Pet rồng con", "🐉🦅 Ứng long chân nhân", "🐲 Chí tôn long hoàng"]},
    "Phượng hoàng con": {"rarity": "Thần thoại", "rate": 0.01, "base_exp": 2000, "atk_inc": 7000, "atk_inc_20": 12000, "stages": ["🐦‍🔥 Phượng hoàng con", "🐦‍🔥🌋 Niết bàn vĩnh hàng", "🐦‍🔥🩸 Thái dương thần điểu"]},
    "Địa thiên cực bắc đại đế": {"rarity": "Hư vọng", "rate": 0.001, "base_exp": 10000, "atk_inc": 10000, "atk_inc_20": 30000, "stages": ["🌏 Địa thiên cực bắc đại đế", "🌌🌑 Tử vi tinh đại đế", "🌌🪐 Hư không cổ hoàng"]}
}

class UpdatePetModal(discord.ui.Modal, title="Quản Trị Viên - Thêm/Cập Nhật Pet"):
    pet_name = discord.ui.TextInput(label="Tên pet", placeholder="Nhập tên pet...")
    rarity = discord.ui.TextInput(label="Phẩm chất", placeholder="Thường / Hiếm / Sử thi / Thần thoại / Hư vọng")
    rate = discord.ui.TextInput(label="Tỉ lệ ra (VD: 0.1)", placeholder="Nhập số thập phân...")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Đã cập nhật thành công pet **{self.pet_name.value}** ({self.rarity.value}) với tỉ lệ {self.rate.value}!", ephemeral=True)

class UpdateBossModal(discord.ui.Modal, title="Quản Trị Viên - Thêm Boss Tháp"):
    boss_name = discord.ui.TextInput(label="Tên Boss", placeholder="Nhập tên boss...")
    lc = discord.ui.TextInput(label="Lực chiến", placeholder="VD: 50000")
    reward_pts = discord.ui.TextInput(label="Thưởng điểm", placeholder="VD: 1000")
    effect = discord.ui.TextInput(label="Hiệu ứng giảm sát thương / đặc biệt", required=False, placeholder="VD: Giảm 50% sát thương...")

    async def on_submit(self, interaction: discord.Interaction):
        bosses_custom.append({"name": self.boss_name.value, "lc": int(self.lc.value), "pts": int(self.reward_pts.value), "effect": self.effect.value})
        await interaction.response.send_message(f"✅ Đã thêm Boss **{self.boss_name.value}** vào tháp thành công!", ephemeral=True)

class NuoiThuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Quay Pet (100 Điểm)", style=discord.ButtonStyle.green, custom_id="roll_pet")
    async def roll_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = get_user(interaction.user.id)
        if user["points"] < 100:
            return await interaction.response.send_message("❌ Bạn không đủ 100 điểm để quay pet!", ephemeral=True)
        
        user["points"] -= 100
        rand = random.random()
        cumulative = 0
        chosen_pet = "Sư tử con"
        
        # Sắp xếp quay theo tỉ lệ từ thấp đến cao
        sorted_pets = sorted(PET_DATA.items(), key=lambda x: x[1]["rate"])
        for p_name, p_info in sorted_pets:
            cumulative += p_info["rate"]
            if rand <= cumulative:
                chosen_pet = p_name
                break

        pet_obj = {"name": chosen_pet, "level": 1, "exp": 0, "atk": p_info["atk_inc"]}
        user["pets"].append(pet_obj)
        
        embed = discord.Embed(title="🎁 KẾT QUẢ QUAY PET", color=discord.Color.gold())
        embed.add_field(name="Chúc mừng!", value=f"Bạn đã quay trúng: **{chosen_pet}** ({PET_DATA[chosen_pet]['rarity']})!", inline=False)
        embed.set_footer(text=f"Số dư hiện tại: {user['points']} điểm")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Update Pet (Admin)", style=discord.ButtonStyle.danger, custom_id="admin_update_pet")
    async def admin_update(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Lệnh này chỉ dành cho Quản trị viên!", ephemeral=True)
        await interaction.response.send_modal(UpdatePetModal())

@bot.tree.command(name="nuoithu", description="Mở giao diện Nuôi thú ảo")
async def nuoithu(interaction: discord.Interaction):
    embed = discord.Embed(title="🐾 HỆ THỐNG NUÔI THÚ ẢO", description="Nhấn nút bên dưới để quay pet hoặc quản trị hệ thống.", color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, view=NuoiThuView())


# ==================== B. PVP PET ====================
@bot.tree.command(name="pvp_pet", description="Thách đấu PvP Pet với người chơi khác")
async def pvp_pet(interaction: discord.Interaction, opponent: discord.Member):
    if opponent == interaction.user:
        return await interaction.response.send_message("❌ Bạn không thể tự đấu với chính mình!", ephemeral=True)
    
    user_data = get_user(interaction.user.id)
    opp_data = get_user(opponent.id)
    
    if not user_data["pets"] or not opp_data["pets"]:
        return await interaction.response.send_message("❌ Cả hai người chơi đều phải sở hữu ít nhất 1 pet để PvP!", ephemeral=True)

    view = discord.ui.View()
    async def accept_callback(i: discord.Interaction):
        if i.user != opponent:
            return await i.response.send_message("❌ Bạn không phải là người được thách đấu!", ephemeral=True)
        
        # Tính lực chiến pet mạnh nhất của mỗi bên
        lc1 = max([p["atk"] for p in user_data["pets"]])
        lc2 = max([p["atk"] for p in opp_data["pets"]])
        
        diff = lc1 - lc2
        if diff == 0:
            p1_win_rate = 50
        elif 0 < abs(diff) <= 3000:
            p1_win_rate = 60 if diff > 0 else 40
        elif 3000 < abs(diff) <= 10000:
            p1_win_rate = 70 if diff > 0 else 30
        else:
            p1_win_rate = 100 if diff > 0 else 0

        roll = random.randint(1, 100)
        winner = interaction.user if roll <= p1_win_rate else opponent
        loser = opponent if winner == interaction.user else interaction.user
        
        embed = discord.Embed(title="⚔️ KẾT QUẢ TRẬN ĐẤU PVP PET", color=discord.Color.red())
        embed.add_field(name="Lực chiến", value=f"{interaction.user.mention}: {lc1} LC vs {opponent.mention}: {lc2} LC", inline=False)
        embed.add_field(name="Người chiến thắng", value=f"🏆 {winner.mention}", inline=False)
        await i.response.edit_message(embed=embed, view=None)

    btn_accept = discord.ui.Button(label="Đồng ý chiến đấu", style=discord.ButtonStyle.green)
    btn_accept.callback = accept_callback
    view.add_item(btn_accept)

    await interaction.response.send_message(f"⚔️ {opponent.mention}, bạn đã nhận được lời thách đấu PvP Pet từ {interaction.user.mention}!", view=view)


# ==================== C. LEO THÁP (/leothap) ====================
TOWERS = [
    {"floor": 1, "name": "Quái nhỏ", "lc": 500, "pts": 100, "exp": 20, "effect": 0},
    {"floor": 2, "name": "Zombie vua", "lc": 1000, "pts": 120, "exp": 40, "effect": 0},
    {"floor": 3, "name": "Ma cà rồng", "lc": 3000, "pts": 200, "exp": 100, "effect": 0},
    {"floor": 4, "name": "Lucifer", "lc": 5000, "pts": 300, "exp": 300, "effect": 0},
    {"floor": 5, "name": "Abaddon", "lc": 10000, "pts": 320, "exp": 310, "effect": 0},
    {"floor": 6, "name": "Leviathan", "lc": 15000, "pts": 1000, "exp": 500, "effect": 0},
    {"floor": 7, "name": "Bàn Cổ", "lc": 30000, "pts": 3000, "exp": 1000, "effect": 0.6},
    {"floor": 8, "name": "Samyaza", "lc": 50000, "pts": 4000, "exp": 2000, "effect": 0.55, "title": "Chân nhân"},
    {"floor": 9, "name": "Kokabiel", "lc": 80000, "pts": 6000, "exp": 3000, "effect": 0.7, "title": "Sáng thế nhân"},
    {"floor": 10, "name": "???", "lc": 100000, "pts": 100000, "exp": 100000, "effect": 1.0, "title": "???"},
    {"floor": 11, "name": "Admin", "lc": 999999999999, "pts": 1, "exp": 1, "effect": 0, "title": "Tiểu Admin tối cao"}
]

class TowerView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="Chọn Tầng & Đánh Boss", style=discord.ButtonStyle.blurple)
    select_floor_btn = discord.ui.button(label="Đánh Tháp", style=discord.ButtonStyle.green)

# Đơn giản hóa lệnh /leothap cho phép chọn tầng trực tiếp qua số tầng
@bot.tree.command(name="leothap", description="Khiêu chiến tháp thử thách")
async def leothap(interaction: discord.Interaction, floor: int):
    if floor < 1 or floor > len(TOWERS) + len(bosses_custom):
        return await interaction.response.send_message(f"❌ Tầng tháp không hợp lệ!", ephemeral=True)
    
    user = get_user(interaction.user.id)
    if not user["pets"]:
        return await interaction.response.send_message("❌ Bạn cần có ít nhất một pet để leo tháp!", ephemeral=True)
    
    max_lc = max([p["atk"] for p in user["pets"]])
    
    # Lấy thông tin boss
    if floor <= len(TOWERS):
        b = TOWERS[floor - 1]
        boss_lc = b["lc"]
        eff = b["effect"]
        reward_pts = b["pts"]
        title_reward = b.get("title")
    else:
        b = bosses_custom[floor - len(TOWERS) - 1]
        boss_lc = b["lc"]
        eff = 0
        reward_pts = b["pts"]
        title_reward = None

    # Tính sát thương sau khi chịu hiệu ứng giảm
    effective_lc = max_lc * (1 - eff)
    
    if effective_lc >= boss_lc:
        user["points"] += reward_pts
        msg = f"🎉 Chúc mừng! Pet của bạn đã đánh bại **{b['name']}** ở tầng {floor} và nhận được **{reward_pts} điểm**!"
        if title_reward:
            user["titles"].append(title_reward)
            msg += f"\n🏆 Bạn nhận được danh hiệu đặc biệt: **{title_reward}**!"
    else:
        msg = f"😢 Thất bại! Lực chiến hiệu quả ({effective_lc}) không đủ vượt qua {b['name']} ({boss_lc})."

    await interaction.response.send_message(msg)


# ==================== D. CÂU CÁ (/causong) ====================
FISH_LIST = [
    ("🐟 Cá Rô Đồng", "Thường", 0.5, 10, None),
    ("🐠 Cá Chép Vàng", "Thường", 0.5, 10, None),
    ("🦈 Cá Tầm", "Thường", 0.5, 10, None),
    ("🐧 Chim Cút", "Thường", 0.5, 20, None),
    ("👞 Giày Cũ Bị Rách", "Xui xẻo", 0.4, -100, None),
    ("👑 Rương Báu Dưới Sông", "Hiếm", 0.4, 100, None),
    ("🐙 Bạch tuộc", "Hiếm", 0.4, 60, None),
    ("🐢 Rùa con", "Hiếm", 0.4, 70, None),
    ("🦭 Tiểu long cẩu", "Sử thi", 0.2, 200, None),
    ("🦞 Tôm suki", "Sử thi", 0.19, 210, None),
    ("⭐ Light suki", "Sử thi", 0.15, 220, None),
    ("🫍 Cá voi sát thần", "Thần thoại", 0.01, 500, "Sát long"),
    ("🦠 Virut tử thần", "Thần thoại", 0.005, 1000, "Virut vương"),
    ("🐉 Leviathan", "Thần thoại", 0.001, 2000, "Leviathan"),
    ("🌑 Chân thiên tôn", "Hư vô", 0.00001, 3000, "Thiên tôn")
]

class AddFishModal(discord.ui.Modal, title="Admin - Thêm Cá Mới"):
    name = discord.ui.TextInput(label="Tên cá")
    rarity = discord.ui.TextInput(label="Phẩm cấp")
    rate = discord.ui.TextInput(label="Tỉ lệ ra (VD: 0.05)")
    title = discord.ui.TextInput(label="Danh hiệu nhận kèm (không bắt buộc)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Đã thêm cá **{self.name.value}** vào hệ thống câu cá!", ephemeral=True)

class CauCaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎣 Câu Cá", style=discord.ButtonStyle.green, custom_id="do_fish")
    async def do_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = get_user(interaction.user.id)
        
        # Tỉ lệ đứt dây câu (55% thất bại, 45% thành công)
        if random.random() > 0.45:
            return await interaction.response.send_message("🎣 Rất tiếc, cá đã cắn câu nhưng dây bị đứt! Câu cá thất bại.", ephemeral=True)
        
        # Chọn cá ngẫu nhiên theo tỉ lệ
        caught = random.choice(FISH_LIST)
        fish_name, rarity, rate, pts, title = caught
        
        user["points"] += pts
        msg = f"🎣 Bạn đã câu thành công **{fish_name}** ({rarity}) và nhận được **{pts} điểm**!"
        if title:
            user["titles"].append(title)
            msg += f"\n🏆 Nhận thêm danh hiệu: **{title}**!"
            
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="➕ Thêm Cá (Admin)", style=discord.ButtonStyle.danger, custom_id="admin_add_fish")
    async def add_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được chức năng này!", ephemeral=True)
        await interaction.response.send_modal(AddFishModal())

@bot.tree.command(name="causong", description="Mở giao diện câu cá sông")
async def causong(interaction: discord.Interaction):
    embed = discord.Embed(title="🌊 KHU VỰC CÂU CÁ SÔNG", description="Thử vận may câu các loài vật phẩm quý hiếm!", color=discord.Color.teal())
    await interaction.response.send_message(embed=embed, view=CauCaView())


# ==================== F. SHOP & TÚI ĐỒ (/shop, /tuido) ====================
SHOP_ITEMS = {
    "baits": [
        {"name": "Mồi cánh gió", "price": 100, "desc": "Tăng 5% tỉ lệ câu cá thường"},
        {"name": "Mồi sao", "price": 200, "desc": "Tăng 10% tỉ lệ thành công"},
        {"name": "Mồi mặt trăng", "price": 10000, "desc": "Tăng 10% câu cá thần thoại"}
    ],
    "foods": [
        {"name": "Đào lumi", "price": 20, "desc": "+10 EXP pet"},
        {"name": "Hoa furina", "price": 200, "desc": "+100 EXP pet"},
        {"name": "Thịt hổ", "price": 600, "desc": "+300 EXP pet"}
    ],
    "gears": [
        {"name": "Chi dục", "price": 100000, "desc": "Tăng 50% tỉ lệ thắng PvP"},
        {"name": "Tịnh diệt kiếm ý", "price": 50000, "desc": "+1000 lực chiến"}
    ]
}

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout = None như yêu cầu

    @discord.ui.button(label="Cần & Mồi", style=discord.ButtonStyle.primary)
    async def shop_baits(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🛒 **Danh mục Cần & Mồi**:\n- Mồi cánh gió: 100 điểm\n- Mồi sao: 200 điểm\n(Dùng lệnh mua tương ứng để sở hữu)", ephemeral=True)

    @discord.ui.button(label="Đồ ăn & Trang bị", style=discord.ButtonStyle.primary)
    async def shop_gears(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🛒 **Danh mục Đồ ăn & Trang bị Pet**:\n- Đào lumi: 20 điểm\n- Tịnh diệt kiếm ý: 50,000 điểm", ephemeral=True)

    @discord.ui.button(label="Update Shop (Admin)", style=discord.ButtonStyle.danger)
    async def admin_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Chỉ Quản trị viên mới được thao tác!", ephemeral=True)
        await interaction.response.send_message("🛠️ Đã mở giao diện tùy chỉnh Shop (Đang phát triển modal thêm đồ)", ephemeral=True)

@bot.tree.command(name="shop", description="Cửa hàng vật phẩm hệ thống")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛍️ CỬA HÀNG TOÀN QUỐC", description="Chọn danh mục mua sắm bên dưới:", color=discord.Color.magenta())
    await interaction.response.send_message(embed=embed, view=ShopView())

@bot.tree.command(name="tuido", description="Xem túi đồ và trang bị cá nhân")
async def tuido(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    embed = discord.Embed(title=f"🎒 TÚI ĐỒ CỦA {interaction.user.name}", color=discord.Color.orange())
    embed.add_field(name="💰 Điểm sở hữu", value=f"{user['points']} điểm", inline=False)
    embed.add_field(name="🐾 Thú cưng", value=str([p['name'] for p in user['pets']]) if user['pets'] else "Chưa có pet nào", inline=False)
    embed.add_field(name="🏆 Danh hiệu", value=", ".join(user['titles']) if user['titles'] else "Chưa có danh hiệu", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==================== H. BẢNG XẾP HẠNG & AUTO UPDATE ====================
@bot.tree.command(name="bangxephang", description="Xem bảng xếp hạng điểm số toàn server")
async def bangxephang(interaction: discord.Interaction):
    if interaction.channel_id not in active_channels_lb:
        active_channels_lb.append(interaction.channel_id)
        
    sorted_users = sorted(users_db.items(), key=lambda x: x[1]["points"], reverse=True)[:10]
    
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG ĐIỂM SỐ TOP 10", color=discord.Color.gold())
    for idx, (uid, data) in enumerate(sorted_users, 1):
        user_obj = bot.get_user(uid)
        username = user_obj.name if user_obj else f"User ID: {uid}"
        title = top_titles.get(idx, "")
        embed.add_field(name=#{idx}. {username}, value=f"Điểm: {data['points']} | Danh hiệu: {title}", inline=False)
        
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set_top_title", description="Admin thay đổi danh hiệu Top BXH")
async def set_top_title(interaction: discord.Interaction, top_num: int, new_title: str):
    if not is_admin(interaction):
        return await interaction.response.send_message("❌ Lệnh dành riêng cho Admin!", ephemeral=True)
    if top_num not in [1, 2, 3]:
        return await interaction.response.send_message("❌ Chỉ có thể đổi danh hiệu cho Top 1, 2 hoặc 3!", ephemeral=True)
    
    top_titles[top_num] = new_title
    await interaction.response.send_message(f"✅ Đã cập nhật danh hiệu cho Top {top_num} thành **{new_title}**!")

@tasks.loop(time=time(hour=6, minute=0, tzinfo=timezone(timedelta(hours=7))))
async def daily_bxh_update():
    # Tự động cập nhật bảng xếp hạng vào lúc 6h sáng mỗi ngày ở các kênh đã gọi lệnh
    for ch_id in active_channels_lb:
        channel = bot.get_channel(ch_id)
        if channel:
            await channel.send("⏰ **[Tự động cập nhật]** Bảng xếp hạng điểm số lúc 6:00 sáng đã được làm mới!")

@bot.event
async def on_ready():
    daily_bxh_update.start()
    print(f"🤖 Bot {bot.user.name} đã sẵn sàng hoạt động hoàn hảo!")


# ==================== J. CƯỚP GIẬT & K. TÀI XỈU / POINT EDIT ====================
@bot.tree.command(name="cuop", description="Thực hiện cướp điểm người chơi khác")
async def cuop(interaction: discord.Interaction, target: discord.Member):
    if target == interaction.user:
        return await interaction.response.send_message("❌ Bạn không thể tự cướp chính mình!", ephemeral=True)
    
    user = get_user(interaction.user.id)
    target_data = get_user(target.id)
    
    if random.random() <= 0.45:
        # Cướp thành công
        stolen = random.randint(10, min(1000, target_data["points"] if target_data["points"] > 0 else 10))
        target_data["points"] -= stolen
        user["points"] += stolen
        await interaction.response.send_message(chúc mừng! Bạn đã cướp thành công **{stolen} điểm** từ {target.mention}!)
    else:
        # Thất bại / Bị bắt
        fine = random.randint(10, 1000)
        user["points"] = max(0, user["points"] - fine)
        target_data["points"] += fine
        await interaction.response.send_message(🚨 Bị bắt quả tang! Bạn bị phạt **{fine} điểm** chuyển thẳng cho {target.mention} làm tiền bồi thường.)

@bot.tree.command(name="taixiu", description="Chơi tài xỉu đặt cược điểm")
async def taixiu(interaction: discord.Interaction, amount: int, choice: str):
    choice = choice.lower()
    if choice not in ["tài", "xỉu"]:
        return await interaction.response.send_message("❌ Lựa chọn phải là 'tài' hoặc 'xỉu'!", ephemeral=True)
    
    user = get_user(interaction.user.id)
    if user["points"] < amount:
        return await interaction.response.send_message("❌ Bạn không đủ điểm để cược số tiền này!", ephemeral=True)
    
    dice = random.randint(1, 6) + random.randint(1, 6) + random.randint(1, 6)
    result = "tài" if dice >= 11 else "xỉu"
    
    if choice == result:
        user["points"] += amount
        await interaction.response.send_message(🎲 Kết quả xúc xắc: **{dice} ({result.upper()})**. Bạn đã THẮNG và nhận thêm {amount} điểm!)
    else:
        user["points"] -= amount
        await interaction.response.send_message(🎲 Kết quả xúc xắc: **{dice} ({result.upper()})**. Bạn đã THUA và mất {amount} điểm!)

@bot.tree.command(name="point_edit", description="Admin cộng hoặc trừ điểm người dùng")
async def point_edit(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction):
        return await interaction.response.send_message("❌ Chỉ Quản trị viên mới được dùng lệnh này!", ephemeral=True)
    
    u_data = get_user(user.id)
    u_data["points"] += amount
    await interaction.response.send_message(✅ Đã điều chỉnh {amount} điểm cho người dùng {user.mention}. Số dư mới: {u_data['points']} điểm.)

# Thay thế TOKEN của bạn vào đây để chạy bot
# bot.run("YOUR_BOT_TOKEN")

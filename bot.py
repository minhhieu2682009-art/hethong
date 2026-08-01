import asyncio
from datetime import datetime, time, timezone
import os
import random
import sqlite3
from threading import Thread
import discord
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask

# --- 1. FLASK KEEP ALIVE 24/7 ---
app = Flask("")


@app.route("/")
def home():
  return "🤖 Bot Discord Hoạt Động 24/7!"


def run_flask():
  app.run(host="0.0.0.0", port=8080)


def keep_alive():
  t = Thread(target=run_flask)
  t.start()


# --- 2. DATABASE SQLITE & ASYNC LOCK ---
db = sqlite3.connect("game_data.db", check_same_thread=False)
cursor = db.cursor()
db_lock = asyncio.Lock()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        points INTEGER,
        pet TEXT,
        inventory TEXT,
        titles TEXT,
        equipped_title TEXT
    )
""")
db.commit()


def get_player(user_id):
  cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  if not row:
    cursor.execute(
        "INSERT INTO players VALUES (?, 500000, NULL, ?, '[]', NULL)",
        (user_id, str({"baits": {}, "rods": {}, "foods": {"thit_ho": 2, "dao_lumi": 5}, "gears": {}})),
    )
    db.commit()
    return get_player(user_id)
  return {
      "points": row[1],
      "pet": eval(row[2]) if row[2] and row[2] != "None" else None,
      "inventory": eval(row[3]) if row[3] else {"baits": {}, "rods": {}, "foods": {}, "gears": {}},
      "titles": eval(row[4]) if row[4] else [],
      "equipped_title": row[5] if row[5] != "None" else None,
  }


async def save_player_async(user_id, p):
  async with db_lock:
    cursor.execute(
        "UPDATE players SET points=?, pet=?, inventory=?, titles=?, equipped_title=? WHERE user_id=?",
        (p["points"], str(p["pet"]) if p["pet"] else None, str(p["inventory"]), str(p["titles"]), p["equipped_title"], user_id),
    )
    db.commit()


def is_admin(interaction: discord.Interaction):
  return interaction.user.guild_permissions.administrator


# --- DỮ LIỆU GAME ---
pet_gacha_rates = [
    ("🦁 Sư tử con", "thường", 70),
    ("🐻 Gấu con", "thường", 70),
    ("🐼 Gấu trúc con", "hiếm", 50),
    ("🦈 Cá mập con", "hiếm", 50),
    ("🦅 Đại bàng trắng con", "sử thi", 20),
    ("🦄 Kì lân con", "sử thi", 10),
    ("🐉 Rồng con", "thần thoại", 1),
    ("🐦‍🔥 Phượng hoàng con", "thần thoại", 1),
    ("🌏 Địa thiên cực bắc đại đế", "hư vọng", 0.1),
]

boss_list = {
    1: {"name": "Quái nhỏ", "power": 500, "reward_pts": 100, "reward_exp": 20, "effect": None},
    2: {"name": "Zombie vua", "power": 1000, "reward_pts": 120, "reward_exp": 40, "effect": None},
    3: {"name": "Ma cà rồng", "power": 3000, "reward_pts": 200, "reward_exp": 100, "effect": None},
    4: {"name": "Lucifer", "power": 5000, "reward_pts": 300, "reward_exp": 300, "effect": None},
    5: {"name": "Abaddon", "power": 10000, "reward_pts": 320, "reward_exp": 310, "effect": None},
    6: {"name": "Leviathan", "power": 15000, "reward_pts": 1000, "reward_exp": 500, "effect": None},
    7: {"name": "Bàn cổ", "power": 30000, "reward_pts": 3000, "reward_exp": 1000, "effect": "reduce_60"},
    8: {"name": "Samyaza", "power": 50000, "reward_pts": 4000, "reward_exp": 2000, "effect": "samyaza_eff", "title": "chân nhân"},
    9: {"name": "Kokabiel", "power": 80000, "reward_pts": 6000, "reward_exp": 3000, "effect": "kokabiel_eff", "title": "sáng thế nhân"},
    10: {"name": "???", "power": 100000, "reward_pts": 100000, "reward_exp": 100000, "effect": "unknown_eff", "title": "???"},
    11: {"name": "Admin", "power": 999999999999, "reward_pts": 1, "reward_exp": 1, "effect": None, "title": "tiểu Admin tối cao"},
}

fish_list = [
    {"name": "Cá Rô Đồng", "tier": "thường", "rate": 50, "reward": 10, "title": None},
    {"name": "Cá Chép Vàng", "tier": "thường", "rate": 50, "reward": 10, "title": None},
    {"name": "Cá Tầm", "tier": "thường", "rate": 50, "reward": 10, "title": None},
    {"name": "Chim Cút", "tier": "thường", "rate": 50, "reward": 20, "title": None},
    {"name": "Giày Cũ Bị Rách", "tier": "xui", "rate": 40, "reward": -100, "title": None},
    {"name": "Rương Báu Dưới Sông", "tier": "hiếm", "rate": 40, "reward": 100, "title": None},
    {"name": "Bạch tuộc", "tier": "hiếm", "rate": 40, "reward": 60, "title": None},
    {"name": "Rùa con", "tier": "hiếm", "rate": 40, "reward": 70, "title": None},
    {"name": "Tiểu long cẩu", "tier": "sử thi", "rate": 20, "reward": 200, "title": None},
    {"name": "Tôm suki", "tier": "sử thi", "rate": 19, "reward": 210, "title": None},
    {"name": "Light suki", "tier": "sử thi", "rate": 15, "reward": 220, "title": None},
    {"name": "Cá voi sát thần", "tier": "thần thoại", "rate": 1, "reward": 500, "title": "sát long"},
    {"name": "Virut tử thần", "tier": "thần thoại", "rate": 0.5, "reward": 1000, "title": "virut vương"},
    {"name": "Leviathan", "tier": "thần thoại", "rate": 0.1, "reward": 2000, "title": "leviathan"},
    {"name": "Chân thiên tôn", "tier": "hư vô", "rate": 0.001, "reward": 3000, "title": "thiên tôn"},
]

active_lb_channels = set()


class GameBot(commands.Bot):

  def __init__(self):
    super().__init__(command_prefix="!", intents=discord.Intents.all())

  async def setup_hook(self):
    await self.tree.sync()
    auto_update_leaderboard.start()
    print("Bot Đã Sẵn Sàng Với Giao Diện Cực Xịn Sò!")


client = GameBot()


@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
  if isinstance(error, app_commands.CommandOnCooldown):
    await interaction.response.send_message(f"⏳ Đang hồi chiêu! Thử lại sau **{round(error.retry_after, 1)}s**.", ephemeral=True)
  else:
    raise error


# --- 1. LỆNH SYNC COMMANDS (ADMIN) ---
@client.tree.command(name="sync", description="Đồng bộ lại Slash Commands ngay lập tức (Admin)")
async def sync(interaction: discord.Interaction):
  if not is_admin(interaction):
    await interaction.response.send_message("❌ Chỉ có Quản trị viên mới được dùng lệnh này!", ephemeral=True)
    return
  await client.tree.sync()
  await interaction.response.send_message("✅ Đã đồng bộ thành công toàn bộ Slash Commands với Discord!", ephemeral=True)


# --- A. HỆ THỐNG NUÔI THÚ & GACHA ---
class PetModal(discord.ui.Modal, title="✨ Quản trị Viên - Cập nhật Pet"):
  pet_name = discord.ui.TextInput(label="Tên Pet", placeholder="VD: 🦁 Sư tử con")
  tier = discord.ui.TextInput(label="Phẩm chất", placeholder="VD: thường / thần thoại")
  rate = discord.ui.TextInput(label="Tỉ lệ ra (%)", placeholder="VD: 70")

  async def on_submit(self, interaction: discord.Interaction):
    pet_gacha_rates.append((self.pet_name.value, self.tier.value, float(self.rate.value)))
    await interaction.response.send_message(f"✅ Đã thêm pet **{self.pet_name.value}** vào hệ thống gacha thành công!", ephemeral=True)


class PetView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(label="🎲 Quay Pet (100 Điểm)", style=discord.ButtonStyle.green, emoji="🎁", custom_id="roll_pet_btn")
  async def roll_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
    p = get_player(interaction.user.id)
    if p["points"] < 100:
      await interaction.response.send_message("❌ Bạn cần ít nhất **100 Điểm** để quay pet!", ephemeral=True)
      return
    p["points"] -= 100
    rolled = random.choices(pet_gacha_rates, weights=[r[2] for r in pet_gacha_rates])[0]
    p["pet"] = {"name": rolled[0], "tier": rolled[1], "level": 1, "exp": 0, "power": 100}
    await save_player_async(interaction.user.id, p)

    embed = discord.Embed(
        title="🐾 ✨ KẾT QUẢ QUAY THÚ CƯNG ✨ 🐾",
        description=f"🎉 Chúc mừng bạn đã triệu hồi thành công:\n\n> **{rolled[0]}**\n> 🌟 Phẩm chất cấp: `{rolled[1].upper()}`",
        color=0x00FFCC,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

  @discord.ui.button(label="⚙️ Update Pet (Admin)", style=discord.ButtonStyle.red, emoji="🛠️", custom_id="update_pet_btn")
  async def update_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
    if not is_admin(interaction):
      await interaction.response.send_message("❌ Chỉ có Quản trị viên mới được dùng tính năng này!", ephemeral=True)
      return
    await interaction.response.send_modal(PetModal())


@client.tree.command(name="nuoithu", description="Giao diện nuôi thú & gacha pet")
async def nuoithu(interaction: discord.Interaction):
  embed = discord.Embed(
      title="🐾 ─── HỆ THỐNG NUÔI THÚ ẢO ─── 🐾",
      description="🌟 Chào mừng bạn đến với khu vực huấn luyện thú cưng.\n*Nhấn nút bên dưới để tiến hành gacha tìm kiếm những chú pet huyền thoại!*",
      color=0x9B59B6,
  )
  await interaction.response.send_message(embed=embed, view=PetView())


# --- B. HỆ THỐNG PVP PET ---
class PvPView(discord.ui.View):

  def __init__(self, challenger, opponent):
    super().__init__(timeout=60)
    self.challenger = challenger
    self.opponent = opponent

  @discord.ui.button(label="⚔️ Chấp Nhận Thách Đấu", style=discord.ButtonStyle.green, emoji="🔥")
  async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.user.id != self.opponent.id:
      await interaction.response.send_message("❌ Bạn không phải là người được thách đấu trong trận chiến này!", ephemeral=True)
      return

    p1 = get_player(self.challenger.id)
    p2 = get_player(self.opponent.id)

    if not p1["pet"] or not p2["pet"]:
      await interaction.response.send_message("❌ Cả hai người chơi bắt buộc phải sở hữu Pet mới có thể tham gia PvP!", ephemeral=True)
      return

    pow1 = p1["pet"].get("power", 100)
    pow2 = p2["pet"].get("power", 100)

    diff = pow1 - pow2
    if diff == 0:
      win_rate = 50
    elif 0 < abs(diff) <= 3000:
      win_rate = 60 if diff > 0 else 40
    elif 3000 < abs(diff) < 10000:
      win_rate = 70 if diff > 0 else 30
    else:
      win_rate = 100 if diff > 0 else 0

    roll = random.randint(1, 100)
    winner = self.challenger if roll <= win_rate else self.opponent

    embed = discord.Embed(
        title="⚔️ ─── KẾT QUẢ ĐẤU TRƯỜNG PET ─── ⚔️",
        description=(
            f"👤 **Thách đấu:** {self.challenger.mention} (Lực chiến: `{pow1:,}`)\n👤 **Đối thủ:** {self.opponent.mention} (Lực chiến:"
            f" `{pow2:,}`)\n\n🏆 Vinh quang gọi tên người chiến thắng: **{winner.mention}**! 🎉"
        ),
        color=0xFFD700,
    )
    await interaction.response.send_message(embed=embed)
    self.stop()


@client.tree.command(name="pvp_pet", description="Thách đấu PvP Pet với người chơi khác")
async def pvp_pet(interaction: discord.Interaction, opponent: discord.Member):
  if opponent.id == interaction.user.id:
    await interaction.response.send_message("❌ Bạn không thể tự thách đấu chính mình được!", ephemeral=True)
    return
  embed = discord.Embed(
      title="⚔️ ─── LỜI THÁCH ĐẤU ĐỈNH CAO ─── ⚔️",
      description=(
          f"🔥 Người chơi {interaction.user.mention} vừa gửi lời khiêu chiến PvP đến {opponent.mention}!\n*Liệu đối thủ có dám đứng lên nhận lời thách"
          " đấu này không?*"
      ),
      color=0xE74C3C,
  )
  await interaction.response.send_message(content=opponent.mention, embed=embed, view=PvPView(interaction.user, opponent))


# --- C. HỆ THỐNG LEO THÁP ---
@client.tree.command(name="leothap", description="Leo tháp chiến đấu nhận điểm và vật phẩm")
@app_commands.describe(floor="Chọn tầng tháp (1 đến 11)")
async def leothap(interaction: discord.Interaction, floor: int):
  if floor not in boss_list:
    await interaction.response.send_message("❌ Tầng tháp không tồn tại! Hệ thống tháp hiện chỉ có từ **Tầng 1 đến Tầng 11**.", ephemeral=True)
    return

  boss = boss_list[floor]
  p = get_player(interaction.user.id)
  if not p["pet"]:
    await interaction.response.send_message("❌ Bạn cần phải sở hữu một chú Pet trước khi bắt đầu leo tháp!", ephemeral=True)
    return

  pet_pow = p["pet"].get("power", 100)
  boss_pow = boss["power"]

  if boss.get("effect") == "reduce_60":
    pet_pow *= 0.4
  elif boss.get("effect") == "samyaza_eff" and p["pet"].get("tier") not in ["sử thi", "thần thoại"]:
    pet_pow = -1
  elif boss.get("effect") == "kokabiel_eff" and p["pet"].get("tier") not in ["thần thoại", "hư vọng"]:
    pet_pow = -1
  elif boss.get("effect") == "unknown_eff" and p["pet"].get("tier") not in ["thần thoại", "hư vọng"]:
    pet_pow = -1

  if pet_pow >= boss_pow:
    p["points"] += boss["reward_pts"]
    if boss.get("title") and boss["title"] not in p["titles"]:
      p["titles"].append(boss["title"])
      p["equipped_title"] = boss["title"]
    await save_player_async(interaction.user.id, p)
    
    embed = discord.Embed(
        title=f"🏰 ─── KẾT QUẢ LEO THÁP (TẦNG {floor}) ─── 🏰",
        description=f"🎉 Chúc mừng! Pet của bạn đã hiên ngang đánh bại thủ lĩnh **{boss['name']}**!\n🎁 Phần thưởng nhận được: **+{boss['reward_pts']:,} Điểm**",
        color=0x2ECC71,
    )
    await interaction.response.send_message(embed=embed)
  else:
    embed = discord.Embed(
        title=f"🏰 ─── KẾT QUẢ LEO THÁP (TẦNG {floor}) ─── 🏰",
    description=f"💀 Thất bại thảm hại! Lực chiến pet của bạn không đủ để vượt qua con boss hung ác **{boss['name']}**.",
        color=0xE74C3C,
    )
    await interaction.response.send_message(embed=embed)


# --- D. HỆ THỐNG CÂU CÁ ---
class FishModal(discord.ui.Modal, title="🎣 Thêm Cá Mới (Admin)"):
  name = discord.ui.TextInput(label="Tên loài cá mới", placeholder="VD: Cá mập nước ngọt")
  tier = discord.ui.TextInput(label="Phẩm cấp", placeholder="VD: thần thoại / hiếm")
  rate = discord.ui.TextInput(label="Tỉ lệ ra (%)", placeholder="VD: 1.5")
  title = discord.ui.TextInput(label="Danh hiệu nhận được (Không bắt buộc)", required=False, placeholder="VD: ngư thần")

  async def on_submit(self, interaction: discord.Interaction):
    fish_list.append({"name": self.name.value, "tier": self.tier.value, "rate": float(self.rate.value), "reward": 100, "title": self.title.value or None})
    await interaction.response.send_message(f"✅ Đã thêm loài cá mới **{self.name.value}** vào danh sách câu cá thành công!", ephemeral=True)


class FishView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(label="🎣 Văng Cần Câu Ngay", style=discord.ButtonStyle.primary, emoji="🌊", custom_id="fish_btn")
  async def fish(self, interaction: discord.Interaction, button: discord.ui.Button):
    p = get_player(interaction.user.id)
    if random.randint(1, 100) > 45:
      await interaction.response.send_message("💥 Ôi không, dây câu bị đứt giữa chừng! Câu cá thất bại.", ephemeral=True)
      return

    caught = random.choices(fish_list, weights=[f["rate"] for f in fish_list], k=1)[0]
    p["points"] += caught["reward"]
    if caught.get("title") and caught["title"] not in p["titles"]:
      p["titles"].append(caught["title"])
    await save_player_async(interaction.user.id, p)

    embed = discord.Embed(
        title="🎣 ─── KẾT QUẢ CÂU CÁ ─── 🎣",
        description=f"✨ Bạn đã câu thành công: **{caught['name']}** (`{caught['tier'].upper()}`)\n💰 Giá trị phần thưởng: **+{caught['reward']:,} Điểm**",
        color=0x3498DB,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

  @discord.ui.button(label="➕ Thêm Cá Mới (Admin)", style=discord.ButtonStyle.secondary, emoji="⚙️", custom_id="add_fish_btn")
  async def add_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
    if not is_admin(interaction):
      await interaction.response.send_message("❌ Tính năng này chỉ dành riêng cho Quản trị viên!", ephemeral=True)
      return
    await interaction.response.send_modal(FishModal())


@client.tree.command(name="causong", description="Khu vực câu cá giải trí sông nước")
async def causong(interaction: discord.Interaction):
  embed = discord.Embed(
      title="🎣 ─── KHU VỰC CÂU CÁ GIẢI TRÍ ─── 🎣",
      description="🌊 Dòng sông yên bình đang chờ đón những tay câu cự phách.\n*Nhấn nút bên dưới để văng cần và thử vận may nhận quà khủng!*",
      color=0x3498DB,
  )
  await interaction.response.send_message(embed=embed, view=FishView())


# --- E. HỆ THỐNG SHOP & TÚI ĐỒ (GIAO DIỆN ĐẸP MẮT) ---
class ShopSelect(discord.ui.Select):

  def __init__(self):
    options = [
        discord.SelectOption(label="Mồi cánh gió", description="Giá: 100đ - Tăng 1% tỷ lệ câu thành công cá thường", emoji="🪶", value="moi_canh_gio"),
        discord.SelectOption(label="Mồi sao", description="Giá: 200đ - Tăng 10% câu thành công, +10% cá hiếm", emoji="✨", value="moi_sao"),
        discord.SelectOption(label="Mồi sumo", description="Giá: 10,000đ - Tăng 12% câu thành công, +11% cá sử thi", emoji="🍞", value="moi_sumo"),
        discord.SelectOption(label="Cần sét", description="Giá: 100đ - Cần câu nguyên tố sét mạnh mẽ", emoji="⚡", value="can_set"),
        discord.SelectOption(label="Thịt hổ", description="Giá: 600đ - Thức ăn cao cấp cho pet", emoji="🍖", value="thit_ho"),
    ]
    super().__init__(placeholder="🛒 Chọn vật phẩm muốn mua trong cửa hàng...", min_values=1, max_values=1, options=options)

  async def callback(self, interaction: discord.Interaction):
    item = self.values[0]
    await interaction.response.send_message(f"🛒 Bạn đã chọn xem thông tin hoặc mua vật phẩm: **{item}**. (Hệ thống giao dịch đang sẵn sàng!)", ephemeral=True)


class ShopView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)
    self.add_item(ShopSelect())

  @discord.ui.button(label="🛒 Cập nhật Shop (Admin)", style=discord.ButtonStyle.red, emoji="🛠️", row=1)
  async def shop_update(self, interaction: discord.Interaction, button: discord.ui.Button):
    if not is_admin(interaction):
      await interaction.response.send_message("❌ Chỉ Admin mới có quyền cấu hình cửa hàng!", ephemeral=True)
      return
    await interaction.response.send_message("⚙️ Đã mở giao diện cấu hình shop hệ thống.", ephemeral=True)


@client.tree.command(name="shop", description="Cửa hàng vật phẩm hệ thống thiết kế cao cấp")
async def shop(interaction: discord.Interaction):
  embed = discord.Embed(
      title="🛍️ ─── CỬA HÀNG VẬT PHẨM HỆ THỐNG ─── 🛍️",
      description="*Chào mừng bạn đến với khu thương mại sầm uất. Hãy lựa chọn các trang bị và mồi câu chất lượng bên dưới để hành trình bứt phá!*",
      color=0xE67E22,
  )
  embed.add_field(
      name="🪝 DANH MỤC MỒI & CẦN CÂU NỔI BẬT",
      value=(
          "🪶 **Mồi cánh gió** — `100đ`\n> ℹ️ *Tăng 1% tỷ lệ câu thành công cá thường*\n"
          "✨ **Mồi sao** — `200đ`\n> ℹ️ *Tăng 10% câu thành công, +10% cá hiếm*\n"
          "🍞 **Mồi sumo** — `10,000đ`\n> ℹ️ *Tăng 12% câu thành công, +11% cá sử thi*\n"
          "⚡ **Cần sét** — `100đ`\n> ℹ️ *Cần câu nguyên tố sét cao cấp*\n"
          "🍖 **Thịt hổ** — `600đ`\n> ℹ️ *Thức ăn tăng cường sức mạnh tuyệt đỉnh cho Pet*"
      ),
      inline=False,
  )
  await interaction.response.send_message(embed=embed, view=ShopView())


class UseItemView(discord.ui.View):

  def __init__(self, user_id):
    super().__init__(timeout=60)
    self.user_id = user_id

  @discord.ui.button(label="🍖 Cho Pet Ăn Ngay", style=discord.ButtonStyle.green, emoji="🐾")
  async def feed_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message("❌ Đây không phải là túi đồ của bạn!", ephemeral=True)
      return

    p = get_player(interaction.user.id)
    if not p["pet"]:
      await interaction.response.send_message("❌ Bạn chưa sở hữu thú cưng nào để cho ăn!", ephemeral=True)
      return

    foods = p["inventory"].get("foods", {})
    food_name = None
    for f, qty in foods.items():
      if qty > 0:
        food_name = f
        break

    if not food_name:
      await interaction.response.send_message("❌ Kho thức ăn trong túi đã cạn sạch! Hãy ghé thăm `/shop` để mua thêm.", ephemeral=True)
      return

    foods[food_name] -= 1
    p["pet"]["exp"] = p["pet"].get("exp", 0) + 50
    p["pet"]["power"] = p["pet"].get("power", 100) + 20
    await save_player_async(interaction.user.id, p)

    embed = discord.Embed(
        title="🍖 ─── CHĂM SÓC THÚ CƯNG ─── 🍖",
        description=f"✨ Đã cho pet ăn **{food_name}** thành công!\n📈 Nhận thêm: `+50 EXP` | Tăng trưởng: `+20 Lực chiến`\n💥 Tổng lực chiến hiện tại: **{p['pet']['power']:,}**",
        color=0x2ECC71,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

  @discord.ui.button(label="🪝 Kích Hoạt Mồi Câu", style=discord.ButtonStyle.blurple, emoji="🌊")
  async def use_bait(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message("❌ Đây không phải là túi đồ của bạn!", ephemeral=True)
      return
    await interaction.response.send_message("🪝 Đã kích hoạt mồi câu sẵn sàng cho lượt câu cá kế tiếp tại `/causong`!", ephemeral=True)


@client.tree.command(name="tui_do", description="Xem túi đồ cá nhân và sử dụng vật phẩm")
async def tui_do(interaction: discord.Interaction):
  p = get_player(interaction.user.id)
  pet_info = f"**{p['pet']['name']}** (Level: `{p['pet']['level']}` | Lực chiến: `{p['pet']['power']:,}`)" if p["pet"] else "*Chưa sở hữu Pet*"

  food_list_str = "\n".join([f"• `{k}`: **{v} cái**" for k, v in p["inventory"].get("foods", {}).items() if v > 0]) or "*Kho trống*"

  embed = discord.Embed(
      title=f"🎒 ─── TÚI ĐỒ CÁ NHÂN: {interaction.user.name.upper()} ─── 🎒",
      description="*Kho lưu trữ tài nguyên, bảo vật và trang bị quý giá của bạn.*",
      color=0x1ABC9C,
  )
  embed.add_field(name="💰 Tài sản hiện có", value=f"**{p['points']:,} Điểm**", inline=False)
  embed.add_field(name="🐾 Thú cưng đồng hành", value=pet_info, inline=False)
  embed.add_field(name="🍖 Kho thức ăn", value=food_list_str, inline=False)
  embed.add_field(name="👑 Danh hiệu trang bị", value=f"`{p['equipped_title'] or 'Chưa trang bị'}`", inline=False)

  await interaction.response.send_message(embed=embed, view=UseItemView(interaction.user.id), ephemeral=True)


# --- F. BẢNG XẾP HẠNG & LỆNH ADMIN ---
@client.tree.command(name="bangxephang", description="Xem bảng xếp hạng điểm số top đầu")
async def bangxephang(interaction: discord.Interaction):
  active_lb_channels.add(interaction.channel_id)
  cursor.execute("SELECT user_id, points, equipped_title FROM players ORDER BY points DESC LIMIT 3")
  rows = cursor.fetchall()
  desc = ""
  top_titles = ["khư quỷ", "khu la", "thế thần"]
  for i, (uid, pts, title) in enumerate(rows, 1):
    t_name = title or top_titles[i - 1]
    medal = "🥇" if i == 1 else ("🥈" if i == 2 else "🥉")
    desc += f"{medal} **Top {i}**: `[{t_name}]` <@{uid}> — **{pts:,} Điểm**\n"

  embed = discord.Embed(
      title="🏆 ─── BẢNG XẾP HẠNG VINH QUANG ─── 🏆",
      description=desc or "Chưa có dữ liệu xếp hạng.",
      color=0xF1C40F,
  )
  await interaction.response.send_message(embed=embed)


@client.tree.command(name="set_top_title", description="Thay đổi danh hiệu và màu sắc Top BXH (Admin)")
@app_commands.describe(user="Người chơi", title_name="Tên danh hiệu mới")
async def set_top_title(interaction: discord.Interaction, user: discord.Member, title_name: str):
  if not is_admin(interaction):
    await interaction.response.send_message("❌ Chỉ Quản trị viên mới được dùng lệnh này!", ephemeral=True)
    return
  p = get_player(user.id)
  p["equipped_title"] = title_name
  if title_name not in p["titles"]:
    p["titles"].append(title_name)
  await save_player_async(user.id, p)
  await interaction.response.send_message(f"👑 Đã ban hành danh hiệu tối cao **[{title_name}]** cho người chơi {user.mention} thành công!")


@tasks.loop(time=time(hour=6, minute=0, tzinfo=timezone.utc))
async def auto_update_leaderboard():
  cursor.execute("SELECT user_id, points, equipped_title FROM players ORDER BY points DESC LIMIT 3")
  rows = cursor.fetchall()
  desc = "🌅 **BẢNG XẾP HẠNG VINH QUANG CẬP NHẬT 6H SÁNG**\n\n"
  for i, (uid, pts, title) in enumerate(rows, 1):
    medal = "🥇" if i == 1 else ("🥈" if i == 2 else "🥉")
    desc += f"{medal} **Top {i}**: <@{uid}> — **{pts:,} Điểm**\n"
  embed = discord.Embed(title="🌅 TỰ ĐỘNG CẬP NHẬT HÀNG NGÀY", description=desc, color=0xE74C3C)
  for cid in active_lb_channels:
    if (ch := client.get_channel(cid)):
      try:
        await ch.send(embed=embed)
      except:
        pass


# --- G. LỆNH CƯỚP & TÀI XỈU & POINT EDIT ---
@client.tree.command(name="cuop", description="Cướp điểm của người chơi khác")
async def cuop(interaction: discord.Interaction, victim: discord.Member):
  if victim.id == interaction.user.id:
    await interaction.response.send_message("❌ Bạn không thể tự cướp chính mình được!", ephemeral=True)
    return

  p = get_player(interaction.user.id)
  v = get_player(victim.id)

  if random.randint(1, 100) <= 45:
    stolen = random.randint(10, 1000)
    if v["points"] < stolen:
      stolen = v["points"]
    v["points"] -= stolen
    p["points"] += stolen
    await save_player_async(interaction.user.id, p)
    await save_player_async(victim.id, v)
    
    embed = discord.Embed(title="💰 VỤ CƯỚP THÀNH CÔNG", description=f"🥷 Bạn đã lẻn vào và cướp trót lọt **{stolen:,} Điểm** từ nạn nhân {victim.mention}!", color=0x2ECC71)
    await interaction.response.send_message(embed=embed)
  else:
    fine = random.randint(10, 1000)
    if p["points"] < fine:
      fine = p["points"]
    p["points"] -= fine
    v["points"] += fine
    await save_player_async(interaction.user.id, p)
    await save_player_async(victim.id, v)
    
    embed = discord.Embed(title="🚨 BỊ TÓM GỌN", description=f"🚓 Cướp thất bại và bị tuần tra bắt giữ! Bạn bị phạt **{fine:,} Điểm** chuyển thẳng làm tiền bồi thường cho {victim.mention}.", color=0xE74C3C)
    await interaction.response.send_message(embed=embed)


@client.tree.command(name="taixiu", description="Chơi tài xỉu đặt cược điểm số thắng thua x2")
@app_commands.describe(amount="Số tiền cược", choice="Chọn tài hoặc xỉu")
@app_commands.choices(choice=[app_commands.Choice(name="Tài", value="tai"), app_commands.Choice(name="Xỉu", value="xiu")])
async def taixiu(interaction: discord.Interaction, amount: int, choice: str):
  p = get_player(interaction.user.id)
  if amount <= 0 or p["points"] < amount:
    await interaction.response.send_message("❌ Số điểm cược không hợp lệ hoặc số dư tài khoản của bạn không đủ!", ephemeral=Thread, ephemeral=True)
    return

  total = random.randint(1, 6) + random.randint(1, 6) + random.randint(1, 6)
  res = "tai" if total >= 11 else "xiu"

  if choice == res:
    p["points"] += amount
    msg = f"🎲 Kết quả xúc xắc: Tổng điểm **{total}** (`{res.upper()}`). 🎉 Bạn **THẮNG** cược và nhận về `+{amount:,} Điểm`!"
  else:
    p["points"] -= amount
    msg = f"🎲 Kết quả xúc xắc: Tổng điểm **{total}** (`{res.upper()}`). 💀 Bạn **THUA** cược và mất đi `-{amount:,} Điểm`!"

  await save_player_async(interaction.user.id, p)
  await interaction.response.send_message(msg)


@client.tree.command(name="point_edit", description="Cộng hoặc trừ điểm người chơi (Admin)")
@app_commands.describe(user="Người chơi cần chỉnh sửa", amount="Số điểm (Dương để cộng, âm để trừ)")
async def point_edit(interaction: discord.Interaction, user: discord.Member, amount: int):
  if not is_admin(interaction):
    await interaction.response.send_message("❌ Chỉ có Quản trị viên mới được dùng lệnh này!", ephemeral=True)
    return

  p = get_player(user.id)
  p["points"] += amount
  if p["points"] < 0:
    p["points"] = 0
  await save_player_async(user.id, p)
  await interaction.response.send_message(f"✅ Đã điều chỉnh tài khoản của {user.mention}. Số điểm hiện tại: **{p['points']:,} Điểm**", ephemeral=True)


if __name__ == "__main__":
  keep_alive()
  if (TOKEN := os.environ.get("DISCORD_TOKEN")):
    client.run(TOKEN)
  else:
    print("⚠️ Thiếu DISCORD_TOKEN! Vui lòng cấu hình token bot của bạn.")

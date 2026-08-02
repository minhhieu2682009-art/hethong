import asyncio
from zoneinfo import ZoneInfo
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
  return "🤖 Discord Game Bot Is Running 24/7!"


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
        "INSERT INTO players VALUES (?, 0, NULL, ?, '[]', NULL)",
        (user_id, str({"baits": {}, "rods": {}, "foods": {}, "gears": {}, "blox_fruits": {}})),
    )
    db.commit()
    return get_player(user_id)
  inv = eval(row[3]) if row[3] else {}
  if "baits" not in inv:
    inv["baits"] = {}
  if "rods" not in inv:
    inv["rods"] = {}
  if "foods" not in inv:
    inv["foods"] = {}
  if "gears" not in inv:
    inv["gears"] = {}
  if "blox_fruits" not in inv:
    inv["blox_fruits"] = {}
  return {
      "points": row[1],
      "pet": eval(row[2]) if row[2] and row[2] != "None" else None,
      "inventory": inv,
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


# --- DỮ LIỆU PET & GACHA ---
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

active_lb_channels = set()


class GameBot(commands.Bot):

  def __init__(self):
    super().__init__(command_prefix="!", intents=discord.Intents.all())

  async def setup_hook(self):
    await self.tree.sync()
    print("Bot Đã Sẵn Sàng Phần 1!")


client = GameBot()


@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
  if isinstance(error, app_commands.CommandOnCooldown):
    await interaction.response.send_message(f"⏳ Đang hồi chiêu! Thử lại sau **{round(error.retry_after, 1)}s**.", ephemeral=True)
  else:
    raise error


@client.tree.command(name="sync", description="Đồng bộ lại Slash Commands ngay lập tức (Admin)")
async def sync(interaction: discord.Interaction):
  if not is_admin(interaction):
    await interaction.response.send_message("❌ Chỉ Quản trị viên mới được dùng lệnh này!", ephemeral=True)
    return
  await client.tree.sync()
  await interaction.response.send_message("✅ Đã đồng bộ thành công Slash Commands!", ephemeral=True)


# --- HỆ THỐNG NUÔI THÚ & UPDATE PET (ADMIN) ---
class PetModal(discord.ui.Modal, title="✨ Cấu Hình Pet Mới (Admin)"):
  pet_name = discord.ui.TextInput(label="Tên Pet", placeholder="VD: 🦁 Sư tử con")
  tier = discord.ui.TextInput(label="Phẩm chất", placeholder="VD: thường / thần thoại")
  rate = discord.ui.TextInput(label="Tỉ lệ ra (%)", placeholder="VD: 70")

  async def on_submit(self, interaction: discord.Interaction):
    pet_gacha_rates.append((self.pet_name.value, self.tier.value, float(self.rate.value)))
    await interaction.response.send_message(f"✅ Đã thêm pet **{self.pet_name.value}** vào danh sách gacha!", ephemeral=True)


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
    
    # Xác định chỉ số lực chiến cơ bản theo loại pet
    base_power = 100
    p["pet"] = {"name": rolled[0], "tier": rolled[1], "level": 1, "exp": 0, "power": base_power}
    await save_player_async(interaction.user.id, p)

    embed = discord.Embed(
        title="🐾 ✨ KẾT QUẢ QUAY THÚ CƯNG ✨ 🐾",
        description=f"🎉 Chúc mừng bạn triệu hồi thành công:\n\n> **{rolled[0]}**\n> 🌟 Phẩm chất: `{rolled[1].upper()}`",
        color=0x00FFCC,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

  @discord.ui.button(label="⚙️ Update Pet (Admin)", style=discord.ButtonStyle.red, emoji="🛠️", custom_id="update_pet_btn")
  async def update_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
    if not is_admin(interaction):
      await interaction.response.send_message("❌ Chỉ Quản trị viên mới được dùng tính năng này!", ephemeral=True)
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
  # --- HỆ THỐNG PVP PET ---
class PvPButtonView(discord.ui.View):

  def __init__(self, challenger, opponent):
    super().__init__(timeout=60)
    self.challenger = challenger
    self.opponent = opponent
    self.accepted = False

  @discord.ui.button(label="⚔️ Đồng Ý Thách Đấu", style=discord.ButtonStyle.green, emoji="✅")
  async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.user.id != self.opponent.id:
      await interaction.response.send_message("❌ Bạn không phải là người được thách đấu!", ephemeral=True)
      return
    self.accepted = True
    self.stop()

    cp1 = get_player(self.challenger.id)
    cp2 = get_player(self.opponent.id)

    if not cp1["pet"] or not cp2["pet"]:
      await interaction.response.send_message("❌ Cả hai người chơi đều phải có Pet mới có thể PvP!", ephemeral=True)
      return

    pow1 = cp1["pet"]["power"]
    pow2 = cp2["pet"]["power"]

    # Kiểm tra trang bị Chi dục (+50% tỉ lệ thắng)
    inv1 = cp1["inventory"]["gears"]
    inv2 = cp2["inventory"]["gears"]
    if inv1.get("Chi dục", 0) > 0:
      pow1 *= 1.5
    if inv2.get("Chi dục", 0) > 0:
      pow2 *= 1.5

    diff = pow1 - pow2
    if diff == 0:
      win_rate1 = 50
    elif 0 < abs(diff) <= 3000:
      win_rate1 = 60 if diff > 0 else 40
    elif 3000 < abs(diff) < 10000:
      win_rate1 = 70 if diff > 0 else 30
    else:
      win_rate1 = 100 if diff > 0 else 0

    roll = random.randint(1, 100)
    winner = self.challenger if roll <= win_rate1 else self.opponent
    loser = self.opponent if winner == self.challenger else self.challenger

    embed = discord.Embed(
        title="⚔️ ─── KẾT QUẢ TRẬN ĐẤU PET (PVP) ─── ⚔️",
        description=f"🐾 Pet Thách Đấu: **{cp1['pet']['name']}** (Lực chiến: `{int(pow1)}`)\n🐾 Pet Đối Thủ: **{cp2['pet']['name']}** (Lực chiến: `{int(pow2)}`)\n\n🏆 Người chiến thắng: **{winner.mention}** 🎉",
        color=0xF1C40F,
    )
    await interaction.response.send_message(embed=embed)


@client.tree.command(name="pvp_pet", description="Thách đấu PvP Pet với người chơi khác")
@app_commands.describe(opponent="Chọn người chơi bạn muốn thách đấu")
async def pvp_pet(interaction: discord.Interaction, opponent: discord.Member):
  if opponent.bot or opponent.id == interaction.user.id:
    await interaction.response.send_message("❌ Không thể thách đấu chính mình hoặc bot!", ephemeral=True)
    return

  p1 = get_player(interaction.user.id)
  p2 = get_player(opponent.id)
  if not p1["pet"] or not p2["pet"]:
    await interaction.response.send_message("❌ Cả bạn và đối thủ đều phải sở hữu Pet để PvP!", ephemeral=True)
    return

  view = PvPButtonView(interaction.user, opponent)
  embed = discord.Embed(
      title="⚔️ LỜI THÁCH ĐẤU PET ⚔️",
      description=f"{opponent.mention}, bạn nhận được lời thách đấu PvP Pet từ {interaction.user.mention}!\n*Nhấn nút bên dưới để chấp nhận chiến đấu.*",
      color=0xE74C3C,
  )
  await interaction.response.send_message(embed=embed, view=view)


# --- HỆ THỐNG LEO THÁP BOSS ---
boss_list = {
    1: {"name": "Quái nhỏ", "power": 500, "reward_pts": 100, "reward_exp": 20, "reduce_dmg": 0, "block_tier": None, "title": None},
    2: {"name": "Zombie vua", "power": 1000, "reward_pts": 120, "reward_exp": 40, "reduce_dmg": 0, "block_tier": None, "title": None},
    3: {"name": "Ma cà rồng", "power": 3000, "reward_pts": 200, "reward_exp": 100, "reduce_dmg": 0, "block_tier": None, "title": None},
    4: {"name": "Lucifer", "power": 5000, "reward_pts": 300, "reward_exp": 300, "reduce_dmg": 0, "block_tier": None, "title": None},
    5: {"name": "Abaddon", "power": 10000, "reward_pts": 320, "reward_exp": 310, "reduce_dmg": 0, "block_tier": None, "title": None},
    6: {"name": "Leviathan", "power": 15000, "reward_pts": 1000, "reward_exp": 500, "reduce_dmg": 0, "block_tier": None, "title": None},
    7: {"name": "Bàn Cổ", "power": 30000, "reward_pts": 3000, "reward_exp": 1000, "reduce_dmg": 0.6, "block_tier": None, "title": None},
    8: {"name": "Samyaza", "power": 50000, "reward_pts": 4000, "reward_exp": 2000, "reduce_dmg": 0.55, "block_tier": ["thường", "hiếm"], "title": "chân nhân"},
    9: {"name": "Kokabiel", "power": 80000, "reward_pts": 6000, "reward_exp": 3000, "reduce_dmg": 0.7, "block_tier": ["thường", "hiếm", "sử thi"], "title": "sáng thế nhân"},
    10: {"name": "???", "power": 100000, "reward_pts": 100000, "reward_exp": 100000, "reduce_dmg": 1.0, "block_tier": ["thường", "hiếm", "sử thi"], "title": "???"},
    11: {"name": "Admin", "power": 999999999999, "reward_pts": 1, "reward_exp": 1, "reduce_dmg": 0, "block_tier": None, "title": "tiểu Admin tối cao"},
}


class BossModal(discord.ui.Modal, title="📌 Thêm Boss Mới (Admin)"):
  floor_num = discord.ui.TextInput(label="Số Tầng", placeholder="VD: 12")
  boss_name = discord.ui.TextInput(label="Tên Boss", placeholder="VD: Hắc Long")
  power = discord.ui.TextInput(label="Lực chiến Boss", placeholder="VD: 150000")
  reward_pts = discord.ui.TextInput(label="Điểm thưởng", placeholder="VD: 5000")
  reward_exp = discord.ui.TextInput(label="EXP thưởng", placeholder="VD: 2500")

  async def on_submit(self, interaction: discord.Interaction):
    f = int(self.floor_num.value)
    boss_list[f] = {
        "name": self.boss_name.value,
        "power": int(self.power.value),
        "reward_pts": int(self.reward_pts.value),
        "reward_exp": int(self.reward_exp.value),
        "reduce_dmg": 0,
        "block_tier": None,
        "title": None,
    }
    await interaction.response.send_message(f"✅ Đã thêm Boss **{self.boss_name.value}** vào Tầng {f} thành công!", ephemeral=True)


class BossView(discord.ui.View):

  def __init__(self, floor):
    super().__init__(timeout=60)
    self.floor = floor

  @discord.ui.button(label="⚔️ Khiêu Chiến Boss", style=discord.ButtonStyle.danger, emoji="🗡️")
  async def fight_boss(self, interaction: discord.Interaction, button: discord.ui.Button):
    p = get_player(interaction.user.id)
    if not p["pet"]:
      await interaction.response.send_message("❌ Bạn cần phải sở hữu một chú Pet để khiêu chiến tháp!", ephemeral=True)
      return

    b = boss_list[self.floor]
    pet = p["pet"]

    # Kiểm tra trang bị Bình tĩnh (giảm hiệu ứng giảm sát thương của boss -30%)
    reduce_rate = b["reduce_dmg"]
    if p["inventory"]["gears"].get("Bình tĩnh", 0) > 0:
      reduce_rate = max(0, reduce_rate - 0.3)

    effective_power = pet["power"] * (1 - reduce_rate)

    # Kiểm tra chặn phẩm cấp
    if b["block_tier"] and pet["tier"] in b["block_tier"]:
      win = False
    else:
      win = effective_power >= b["power"]

    if win:
      p["points"] += b["reward_pts"]
      pet["exp"] += b["reward_exp"]
      if b["title"] and b["title"] not in p["titles"]:
        p["titles"].append(b["title"])
      await save_player_async(interaction.user.id, p)
      await interaction.response.send_message(f"🎉 Chúc mừng! Pet của bạn đã đánh bại **{b['name']}** (Tầng {self.floor})!\n🎁 Nhận: `+{b['reward_pts']} điểm`, `+{b['reward_exp']} EXP`" + (f" và Danh hiệu **{b['title']}**!" if b["title"] else ""))
    else:
      await interaction.response.send_message(f"💀 Thất bại! Pet của bạn không đủ lực chiến hoặc đã bị khắc chế bởi hiệu ứng của **{b['name']}** (Tầng {self.floor}).")


@client.tree.command(name="leothap", description="Khiêu chiến tháp boss thử thách sức mạnh pet")
@app_commands.describe(floor="Chọn tầng tháp muốn đánh (1-11)")
async def leothap(interaction: discord.Interaction, floor: int):
  if floor not in boss_list:
    await interaction.response.send_message("❌ Tầng tháp không tồn tại!", ephemeral=True)
    return
  b = boss_list[floor]
  embed = discord.Embed(
      title=f"🏰 ─── THÁCH ĐẤU TẦNG {floor} ─── 🏰",
      description=f"👾 Tên Boss: **{b['name']}**\n⚡ Lực chiến: `{b['power']}`\n🎁 Phần thưởng: `{b['reward_pts']} điểm` | `{b['reward_exp']} EXP`\n" + (f"🛡️ Hiệu ứng giảm sát thương: `{int(b['reduce_dmg']*100)}%`\n" if b["reduce_dmg"] > 0 else "") + f"\n*Nhấn nút dưới để khiêu chiến!*",
      color=0xE67E22,
  )
  await interaction.response.send_message(embed=embed, view=BossView(floor))


@client.tree.command(name="boss_admin", description="Thêm hoặc xóa boss tháp (Admin)")
@app_commands.choices(action=[app_commands.Choice(name="Thêm Boss", value="add"), app_commands.Choice(name="Xóa Boss", value="del")])
async def boss_admin(interaction: discord.Interaction, action: str, floor: int):
  if not is_admin(interaction):
    await interaction.response.send_message("❌ Chỉ Admin mới dùng được lệnh này!", ephemeral=True)
    return
  if action == "add":
    await interaction.response.send_modal(BossModal())
  else:
    if floor in boss_list:
      del boss_list[floor]
      await interaction.response.send_message(f"✅ Đã xóa Boss ở tầng {floor}!", ephemeral=True)
    else:
      await interaction.response.send_message("❌ Tầng này không có boss!", ephemeral=True)


# --- HỆ THỐNG CÂU CÁ (/causong) ---
fish_list = [
    ("🐟 Cá Rô Đồng", "thường", 50, 10, None),
    ("🐠 Cá Chép Vàng", "thường", 50, 10, None),
    ("🦈 Cá Tầm", "thường", 50, 10, None),
    ("🐧 Chim Cút", "thường", 50, 20, None),
    ("👞 Giày Cũ Bị Rách", "xui", 40, -100, None),
    ("👑 Rương Báu Dưới Sông", "hiếm", 40, 100, None),
    ("🐙 Bạch tuộc", "hiếm", 40, 60, None),
    ("🐢 Rùa con", "hiếm", 40, 70, None),
    ("🦭 Tiểu long cẩu", "sử thi", 20, 200, None),
    ("🦞 Tôm suki", "sử thi", 19, 210, None),
    ("⭐ Light suki", "sử thi", 15, 220, None),
    ("🫍 Cá voi sát thần", "thần thoại", 1, 500, "sát long"),
    ("🦠 Virut tử thần", "thần thoại", 0.5, 1000, "virut vương"),
    ("🐉 Leviathan", "thần thoại", 0.1, 2000, "leviathan"),
    ("🌑 Chân thiên tôn", "hư vô", 0.001, 3000, "thiên tôn"),
]


class FishModal(discord.ui.Modal, title="🎣 Thêm Cá Mới (Admin)"):
  name = discord.ui.TextInput(label="Tên cá", placeholder="VD: Cá mập mini")
  tier = discord.ui.TextInput(label="Phẩm cấp", placeholder="VD: hiếm / thần thoại")
  rate = discord.ui.TextInput(label="Tỉ lệ ra (%)", placeholder="VD: 10")
  reward = discord.ui.TextInput(label="Điểm thưởng", placeholder="VD: 150")
  title = discord.ui.TextInput(label="Danh hiệu nhận được (Không bắt buộc)", required=False)

  async def on_submit(self, interaction: discord.Interaction):
    fish_list.append((self.name.value, self.tier.value, float(self.rate.value), int(self.reward.value), self.title.value if self.title.value else None))
    await interaction.response.send_message(f"✅ Đã thêm cá **{self.name.value}** vào danh sách câu sông!", ephemeral=True)


class FishView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(label="🎣 Câu Cá Sông", style=discord.ButtonStyle.green, emoji="🌊", custom_id="fish_btn")
  async def fish_action(self, interaction: discord.Interaction, button: discord.ui.Button):
    p = get_player(interaction.user.id)
    # Tỉ lệ thành công 45%, thất bại 55%
    success_roll = random.random() * 100
    if success_roll > 45:
      await interaction.response.send_message("❌ Rất tiếc, cá đã cắn câu nhưng dây câu bị đứt mất tiêu!", ephemeral=True)
      return

    caught = random.choices(fish_list, weights=[f[2] for f in fish_list])[0]
    p["points"] += caught[3]
    if caught[4] and caught[4] not in p["titles"]:
      p["titles"].append(caught[4])
    await save_player_async(interaction.user.id, p)

    embed = discord.Embed(
        title="🎣 KẾT QUẢ CÂU CÁ",
        description=f"🎉 Bạn đã câu thành công: **{caught[0]}** (`{caught[1].upper()}`)\n💰 Nhận được: `{caught[3]} điểm`" + (f"\n👑 Nhận danh hiệu mới: **{caught[4]}**!" if caught[4] else ""),
        color=0x3498DB,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

  @discord.ui.button(label="⚙️ Thêm Cá (Admin)", style=discord.ButtonStyle.red, emoji="➕", custom_id="add_fish_btn")
  async def add_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
    if not is_admin(interaction):
      await interaction.response.send_message("❌ Chỉ Admin mới dùng được tính năng này!", ephemeral=True)
      return
    await interaction.response.send_modal(FishModal())


@client.tree.command(name="causong", description="Khu vực câu cá giải trí nhận thưởng điểm")
async def causong(interaction: discord.Interaction):
  embed = discord.Embed(
      title="🌊 ─── KHU VỰC CÂU CÁ SÔNG ─── 🌊",
      description="*Thả cần câu thư giãn để săn những loài cá hiếm và vật phẩm độc quyền!*\n\n• Tỷ lệ giật cần thành công: **45%**\n• Tỷ lệ đứt dây câu: **55%**",
      color=0x2980B9,
  )
  await interaction.response.send_message(embed=embed, view=FishView())
  # --- DỮ LIỆU SHOP MẶC ĐỊNH ---
shop_items = {
    "baits": {
        "Mồi cánh gió": {"tier": "thường", "desc": "Tăng 5% tỉ lệ câu thành công cá thường", "price": 100},
        "Mồi sao": {"tier": "hiếm", "desc": "Tăng 10% tỉ lệ câu thành công và cá hiếm", "price": 200},
        "Mồi mặt trăng": {"tier": "hiếm", "desc": "-30% tỉ lệ thành công, +10% cá thần thoại", "price": 10000},
        "Mồi susanoo": {"tier": "sử thi", "desc": "+20% tỉ lệ thành công, +20% cá sử thi", "price": 11000},
        "Mồi mắt Gorgon": {"tier": "sử thi", "desc": "+50% tỉ lệ thành công, +15% cá hiếm & sử thi", "price": 15000},
        "Mồi cá voi xanh": {"tier": "thần thoại", "desc": "Tăng 2% tỉ lệ thành công vĩnh viễn", "price": 16000},
        "Mồi tinh cầu": {"tier": "thần thoại", "desc": "+50% tỉ lệ câu, +10% cá thần thoại", "price": 20000},
        "Mồi nàng tiên cá": {"tier": "thần thoại", "desc": "+40% tỉ lệ thành công, +5% cá thần thoại", "price": 25000},
        "Mồi may mắn": {"tier": "hỗn độn", "desc": "50% nhân đôi hoặc 50% thất bại thảm hại", "price": 100000},
    },
    "rods": {
        "Cần bánh mì": {"tier": "thường", "desc": "Cần câu tân thủ", "price": 10},
        "Cần sét": {"tier": "hiếm", "desc": "Cần câu nguyên tố sét", "price": 100},
        "Cần mèo": {"tier": "hiếm", "desc": "Cần câu phong cách mèo dễ thương", "price": 200},
        "Cần lửa": {"tier": "hiếm", "desc": "Tăng 3% tỉ lệ câu lên thành công", "price": 1000},
        "Cần băng": {"tier": "sử thi", "desc": "+5% tỉ lệ thành công, +4% cá sử thi & hiếm", "price": 10000},
        "Cần quỷ": {"tier": "sử thi", "desc": "+9% tỉ lệ thành công, +10% cá thần thoại", "price": 20000},
        "Cần vua": {"tier": "thần thoại", "desc": "+15% tỉ lệ thành công & cá thần thoại", "price": 30000},
        "Bom nguyên tử": {"tier": "hư vô", "desc": "Tăng 1% tỉ lệ câu được cá hư vô", "price": 33000},
    },
    "foods": {
        "Đào lumi": {"tier": "thường", "desc": "Tăng 10 EXP cho pet", "price": 20},
        "Hoa furina": {"tier": "thường", "desc": "Tăng 100 EXP cho pet", "price": 200},
        "Thịt hổ": {"tier": "thường", "desc": "Tăng 300 EXP cho pet", "price": 600},
        "Nấm chaac": {"tier": "hiếm", "desc": "Tăng 600 EXP và +10 lực chiến trong 10 phút", "price": 1500},
        "Ravena": {"tier": "hiếm", "desc": "Tăng 500 EXP cho pet", "price": 1450},
        "Thái âm dương quả": {"tier": "sử thi", "desc": "Tăng 1000 EXP cho pet", "price": 2000},
        "Cửu diệp thảo quả": {"tier": "sử thi", "desc": "Tăng 1100 EXP cho pet", "price": 2300},
        "Linh tủy quả": {"tier": "thần thoại", "desc": "Tăng 100 điểm lực chiến vĩnh viễn cho pet", "price": 5000},
        "Hỗn độn thanh liên Quả": {"tier": "thần thoại", "desc": "Tăng 10000 EXP cho pet", "price": 20000},
        "Bất tử phượng hoàng quả": {"tier": "thần thoại", "desc": "Tăng 1000 lực chiến vĩnh viễn và 1000 EXP", "price": 30000},
    },
    "gears": {
        "Chi dục": {"tier": "hỗn độn", "desc": "Tăng 50% tỉ lệ thắng trong PvP Pet", "price": 100000},
        "Bình tĩnh": {"tier": "hỗn độn", "desc": "Giảm hiệu ứng giảm sát thương của boss đi 30%", "price": 100000},
        "Tịnh diệt kiếm ý": {"tier": "thần thoại", "desc": "Tăng trực tiếp 1000 lực chiến pet", "price": 50000},
        "Cửu u minh kiếm": {"tier": "thần thoại", "desc": "Tăng trực tiếp 2000 lực chiến pet", "price": 55000},
        "Pháp tắc chi nhân": {"tier": "thần thoại", "desc": "Tăng trực tiếp 5000 lực chiến pet", "price": 80000},
        "Súng xxx zzz": {"tier": "???", "desc": "50% tỉ lệ khi dùng tăng 10000 lực chiến", "price": 150000},
    },
}


class AddShopModal(discord.ui.Modal, title="🛠️ Thêm Vật Phẩm Vào Shop (Admin)"):
  category = discord.ui.TextInput(label="Loại (baits/rods/foods/gears)", placeholder="VD: baits")
  item_name = discord.ui.TextInput(label="Tên vật phẩm", placeholder="VD: Mồi rồng")
  tier = discord.ui.TextInput(label="Phẩm cấp", placeholder="VD: thần thoại")
  desc = discord.ui.TextInput(label="Hiệu ứng / Mô tả", placeholder="VD: Tăng 50% tỷ lệ...")
  price = discord.ui.TextInput(label="Giá tiền (Điểm)", placeholder="VD: 50000")

  async def on_submit(self, interaction: discord.Interaction):
    cat = self.category.value.strip()
    if cat not in shop_items:
      shop_items[cat] = {}
    shop_items[cat][self.item_name.value] = {
        "tier": self.tier.value,
        "desc": self.desc.value,
        "price": int(self.price.value),
    }
    await interaction.response.send_message(f"✅ Đã thêm vật phẩm **{self.item_name.value}** vào danh mục `{cat}` thành công!", ephemeral=True)


class BuySelect(discord.ui.Select):

  def __init__(self, category_key):
    self.category_key = category_key
    items = shop_items.get(category_key, {})
    options = []
    for name, data in list(items.items())[:25]:  # Discord giới hạn tối đa 25 options
      options.append(discord.SelectOption(label=name, description=f"Giá: {data['price']}đ | {data['desc'][:50]}", value=name))
    if not options:
      options.append(discord.SelectOption(label="Trống", value="none", description="Chưa có vật phẩm"))
    super().__init__(placeholder=f"🛒 Chọn vật phẩm để mua từ danh mục [{category_key.upper()}]...", min_values=1, max_values=1, options=options)

  async def callback(self, interaction: discord.Interaction):
    item_name = self.values[0]
    if item_name == "none":
      await interaction.response.send_message("❌ Danh mục này hiện đang trống!", ephemeral=True)
      return

    # Xác định kho tương ứng
    inv_map = {"baits": "baits", "rods": "rods", "foods": "foods", "gears": "gears"}
    target_inv_key = inv_map.get(self.category_key, "baits")

    item_data = shop_items[self.category_key][item_name]
    price = item_data["price"]

    p = get_player(interaction.user.id)
    if p["points"] < price:
      await interaction.response.send_message(f"❌ Bạn không đủ điểm! Cần `{price} điểm` để mua món này.", ephemeral=True)
      return

    p["points"] -= price
    current_qty = p["inventory"][target_inv_key].get(item_name, 0)
    p["inventory"][target_inv_key][item_name] = current_qty + 1
    await save_player_async(interaction.user.id, p)

    await interaction.response.send_message(f"✅ Mua thành công **{item_name}** với giá `{price} điểm`! Đã cất vào túi đồ của bạn.", ephemeral=True)


class ShopDynamicView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(label="🪝 Cần & Mồi", style=discord.ButtonStyle.primary, emoji="🎣", custom_id="shop_baits_rods")
  async def shop_baits_rods(self, interaction: discord.Interaction, button: discord.ui.Button):
    view = discord.ui.View(timeout=60)
    view.add_item(BuySelect("baits"))
    view.add_item(BuySelect("rods"))
    await interaction.response.send_message("🛒 **DANH MỤC CẦN & MỒI CÂU:**\n*Chọn vật phẩm từ các menu dưới đây để mua:*", view=view, ephemeral=True)

  @discord.ui.button(label="🍖 Đồ Ăn & Trang Bị Pet", style=discord.ButtonStyle.success, emoji="🥩", custom_id="shop_foods_gears")
  async def shop_foods_gears(self, interaction: discord.Interaction, button: discord.ui.Button):
    view = discord.ui.View(timeout=60)
    view.add_item(BuySelect("foods"))
    view.add_item(BuySelect("gears"))
    await interaction.response.send_message("🛒 **DANH MỤC ĐỒ ĂN & TRANG BỊ PET:**\n*Chọn vật phẩm từ các menu dưới đây để mua:*", view=view, ephemeral=True)

  @discord.ui.button(label="⚙️ Update Đồ Shop (Admin)", style=discord.ButtonStyle.danger, emoji="🛠️", custom_id="shop_update_admin")
  async def shop_update(self, interaction: discord.Interaction, button: discord.ui.Button):
    if not is_admin(interaction):
      await interaction.response.send_message("❌ Chỉ Quản trị viên mới có quyền thêm đồ vào shop!", ephemeral=True)
      return
    await interaction.response.send_modal(AddShopModal())


@client.tree.command(name="shop", description="Cửa hàng hệ thống vật phẩm, cần câu, đồ ăn và trang bị pet")
async def shop(interaction: discord.Interaction):
  embed = discord.Embed(
      title="🛍️ ─── TRUNG TÂM MUA SẮM HỆ THỐNG ─── 🛍️",
      description="*Chào mừng bạn đến với Shop cao cấp.*\n• Sử dụng các nút bấm bên dưới để chuyển đổi qua lại giữa các danh mục mua sắm và trang bị.\n• Hệ thống hoạt động vĩnh viễn (`timeout=None`).",
      color=0x1ABC9C,
  )
  await interaction.response.send_message(embed=embed, view=ShopDynamicView())


# --- GIAO DIỆN TƯƠNG TÁC VÀ XEM TÚI ĐỒ ---
class InventoryActionSelect(discord.ui.Select):
    def __init__(self, all_items):
        options = []
        for category, items in all_items.items():
            for item_name, qty in items.items():
                if qty > 0:
                    icon = "🪱" if category == "baits" else "🎣" if category == "rods" else "🍖" if category == "gears" else "📦"
                    if category == "foods": icon = "🍖"
                    options.append(discord.SelectOption(
                        label=f"{item_name} (SL: {qty})",
                        value=f"{category}:{item_name}",
                        description=f"Danh mục: {category.upper()}",
                        emoji=icon
                    ))
        
        if not options:
            options.append(discord.SelectOption(label="Túi đồ trống", value="empty", description="Không có vật phẩm nào để sử dụng"))

        super().__init__(placeholder="🛒 Chọn vật phẩm muốn sử dụng...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "empty":
            await interaction.response.send_message("❌ Túi đồ của bạn đang trống!", ephemeral=True)
            return

        category, item_name = self.values[0].split(":")
        p = get_player(interaction.user.id)
        inv = p["inventory"]

        if item_name not in inv[category] or inv[category][item_name] <= 0:
            await interaction.response.send_message(f"❌ Vật phẩm **{item_name}** không còn trong túi!", ephemeral=True)
            return

        # Xử lý logic khi sử dụng đồ ăn cho pet
        if category == "foods":
            pet = p.get("pet")
            if not pet:
                await interaction.response.send_message("❌ Bạn chưa có Pet để sử dụng đồ ăn này!", ephemeral=True)
                return
            
            inv[category][item_name] -= 1
            if inv[category][item_name] <= 0:
                del inv[category][item_name]
            
            pet["level"] += 1
            pet["power"] += 500
            await save_player_async(interaction.user.id, p)

            embed = discord.Embed(
                title="🍖 ─── SỬ DỤNG ĐỒ ĂN THÀNH CÔNG ─── 🍖",
                description=f"🎉 Bạn đã dùng **{item_name}** cho **{pet['name']}**!\n📈 Cấp độ: `Cấp {pet['level']}` | Lực chiến: `{pet['power']:,}`",
                color=0x2ECC71
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"✨ Bạn đã chọn tương tác với vật phẩm: **{item_name}**", ephemeral=True)

class InventoryActionView(discord.ui.View):
    def __init__(self, all_items):
        super().__init__(timeout=60)
        self.add_item(InventoryActionSelect(all_items))

@client.tree.command(name="tuido", description="Xem túi đồ và chọn vật phẩm để sử dụng trực tiếp")
async def tuido(interaction: discord.Interaction):
    p = get_player(interaction.user.id)
    inv = p["inventory"]
    pet = p["pet"]

    pet_str = f"🐾 **{pet['name']}** (Cấp `{pet['level']}` | Lực chiến: `{pet['power']}`)" if pet else "❌ Chưa có thú cưng"
    title_str = f"👑 `{p['equipped_title']}`" if p["equipped_title"] else "Chưa lắp"

    baits_str = ", ".join([f"{k} x{v}" for k, v in inv["baits"].items() if v > 0]) or "Trống"
    rods_str = ", ".join([f"{k} x{v}" for k, v in inv["rods"].items() if v > 0]) or "Trống"
    foods_str = ", ".join([f"{k} x{v}" for k, v in inv["foods"].items() if v > 0]) or "Trống"
    gears_str = ", ".join([f"{k} x{v}" for k, v in inv["gears"].items() if v > 0]) or "Trống"

    embed = discord.Embed(
        title=f"🎒 ─── TÚI ĐỒ CỦA {interaction.user.display_name.upper()} ─── 🎒",
        description=f"💰 Số dư điểm: **{p['points']} điểm**\n{pet_str}\n🏷️ Danh hiệu đang đeo: {title_str}",
        color=0x34495E,
    )
    embed.add_field(name="🪱 Mồi Câu", value=baits_str, inline=False)
    embed.add_field(name="🎣 Cần Câu", value=rods_str, inline=False)
    embed.add_field(name="🍖 Đồ Ăn Cho Pet", value=foods_str, inline=False)
    embed.add_field(name="🛡️ Trang Bị Pet", value=gears_str, inline=False)
    embed.add_field(name="📜 Danh hiệu đã sở hữu", value=", ".join(p["titles"]) or "Chưa có", inline=False)

    # Gom vật phẩm để đưa vào Menu chọn
    all_items = {
        "baits": inv.get("baits", {}),
        "rods": inv.get("rods", {}),
        "foods": inv.get("foods", {}),
        "gears": inv.get("gears", {})
    }
    view = InventoryActionView(all_items)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
import random
import discord

# ==========================================
# DATABASE MỞ RỘNG (ĐÃ CÂN BẰNG LẠI KINH TẾ)
# ==========================================

BLOXL_FRUITS_DATABASE = {
    "Rocket": {
        "type": "Thường (Common)",
        "price": 5000,
        "desc": "Tên lửa tầm trung, dễ kiếm cho tân thủ.",
        "skill": "Phóng tên lửa định hướng",
        "mult": 1.0,
    },
    "Spin": {
        "type": "Thường (Common)",
        "price": 7500,
        "desc": "Xoay vòng tròn né tránh sát thương.",
        "skill": "Cơn lốc xoáy phi thân",
        "mult": 1.1,
    },
    "Flame": {
        "type": "Nguyên tố (Elemental)",
        "price": 250000,
        "desc": "Hỏa quyền thiêu đốt mọi mục tiêu.",
        "skill": "Đại hồng liên hỏa diệm",
        "mult": 1.3,
    },
    "Ice": {
        "type": "Nguyên tố (Elemental)",
        "price": 350000,
        "desc": "Đóng băng diện rộng, kiểm soát kẻ địch.",
        "skill": "Kỷ băng hà vĩnh cửu",
        "mult": 1.4,
    },
    "Light": {
        "type": "Nguyên tố (Elemental)",
        "price": 650000,
        "desc": "Tốc độ ánh sáng, đâm xuyên kẻ thù.",
        "skill": "Kiếm quang chiếu rọi",
        "mult": 1.6,
    },
    "Magma": {
        "type": "Nguyên tố (Elemental)",
        "price": 850000,
        "desc": "Gây sát thương hệ dung nham cực kỳ lớn.",
        "skill": "Mưa hỏa sơn hủy diệt",
        "mult": 1.8,
    },
    "Buddha": {
        "type": "Thú vật (Beast)",
        "price": 1200000,
        "desc": "Hóa thân Phật Tổ tăng cực nhiều giáp và tầm đánh.",
        "skill": "Kim thân bất tử",
        "mult": 2.1,
    },
    "Portal": {
        "type": "Đặc biệt (Special)",
        "price": 1900000,
        "desc": "Dịch chuyển tức thời qua không gian.",
        "skill": "Cổng không gian chiều thứ V",
        "mult": 2.4,
    },
    "Dough": {
        "type": "Huyền thoại (Legendary)",
        "price": 2800000,
        "desc": "Sức mạnh bột nhào thức tỉnh tối thượng (Awakened).",
        "skill": "Mưa bánh rán xuyên giáp",
        "mult": 2.8,
    },
    "Leopard": {
        "type": "Huyền thoại (Legendary)",
        "price": 5000000,
        "desc": "Hóa báo đốm với tốc độ di chuyển và combo vô địch.",
        "skill": "Móng vuốt báo xé gió",
        "mult": 3.5,
    },
    "Dragon": {
        "type": "Huyền thoại (Legendary)",
        "price": 3500000,
        "desc": "Hóa Rồng thiêu rụi toàn bộ chiến trường Sea.",
        "skill": "Hơi thở rồng tận thế",
        "mult": 4.0,
    },
}

# Tăng mạnh HP Boss và giảm phần thưởng để chống lạm phát kinh tế
BOSSES = {
    "The Saw": {"hp": 150000, "sea": 1, "reward_pts": 15000, "reward_frag": 30},
    "Smoke Admiral": {
        "hp": 450000,
        "sea": 2,
        "reward_pts": 45000,
        "reward_frag": 80,
    },
    "Beautiful Pirate": {
        "hp": 900000,
        "sea": 3,
        "reward_pts": 100000,
        "reward_frag": 180,
    },
    "Sea Beast": {
        "hp": 2000000,
        "sea": 2,
        "reward_pts": 200000,
        "reward_frag": 350,
    },
}

PLAYERS_DB = {}


def get_player(user_id):
  if user_id not in PLAYERS_DB:
    PLAYERS_DB[user_id] = {
        "level": 1,
        "exp": 0,
        "max_exp": 1000,
        "sea": 1,
        "points": 100000,  # Khởi đầu vừa phải
        "fragments": 100,
        "pity_counter": 0,
        "equipped_fruit": None,
        "awakened": False,
        "stats": {
            "melee": 10,
            "defense": 10,
            "sword": 10,
            "fruit": 10,
            "stat_points": 0,
        },
        "inventory": {"fruits": {}},
    }
  return PLAYERS_DB[user_id]


def add_exp(p, amount):
  p["exp"] += amount
  leveled_up = False
  while p["exp"] >= p["max_exp"]:
    p["exp"] -= p["max_exp"]
    p["level"] += 1
    p["max_exp"] = int(p["max_exp"] * 1.4)
    p["stats"]["stat_points"] += 3
    leveled_up = True
    if p["level"] >= 50 and p["sea"] == 1:
      p["sea"] = 2
    elif p["level"] >= 120 and p["sea"] == 2:
      p["sea"] = 3
  return leveled_up


# ==========================================
# 1. GIAO DIỆN GACHA & SHOP TRÁI ÁC QUỶ
# ==========================================


class BloxFruitGachaView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="🎰 Roll Trái (50k)", style=discord.ButtonStyle.success, emoji="🍈"
  )
  async def roll_fruit(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    p = get_player(interaction.user.id)
    cost = 50000
    if p["points"] < cost:
      await interaction.response.send_message(
          "❌ Bạn không đủ 50,000 Điểm để roll!", ephemeral=True
      )
      return

    p["points"] -= cost
    p["pity_counter"] += 1

    fruits = list(BLOXL_FRUITS_DATABASE.keys())
    if p["pity_counter"] >= 12:
      high_tier = [
          "Magma",
          "Buddha",
          "Portal",
          "Dough",
          "Leopard",
          "Dragon",
      ]
      chosen_fruit = random.choice(high_tier)
      p["pity_counter"] = 0
    else:
      weights = [35, 25, 15, 10, 7, 4, 2, 1.2, 0.5, 0.1, 0.2]
      chosen_fruit = random.choices(fruits, weights=weights, k=1)[0]
      if chosen_fruit not in ["Rocket", "Spin"]:
        p["pity_counter"] = 0

    f_info = BLOXL_FRUITS_DATABASE[chosen_fruit]
    inv = p["inventory"]["fruits"]
    if chosen_fruit in inv:
      inv[chosen_fruit] += 1
      frag_add = int(f_info["price"] / 15000)
      p["fragments"] += frag_add
      dup_text = f"\n🔄 *Trùng lặp! Đổi thành **+{frag_add} Fragments**.*"
    else:
      inv[chosen_fruit] = 1
      dup_text = "\n✨ *Đã cất vào kho đồ (`/kho_trai`)*"

    embed = discord.Embed(
        title="🍈 ─── KẾT QUẢ GACHA ─── 🍈",
        description=(
            f"🎉 **{interaction.user.mention}** nhận được:\n### 🌟"
            f" **{chosen_fruit}** (`{f_info['type']}`)\n📜 *Mô tả:*"
            f" {f_info['desc']}\n⚔️ *Kỹ năng:* `{f_info['skill']}`{dup_text}"
        ),
        color=0xE91E63,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 2. GIAO DIỆN SĂN BOSS & RAID CO-OP
# ==========================================


class RaidBossView(discord.ui.View):

  def __init__(self, boss_name, boss_data):
    super().__init__(timeout=60)
    self.boss_name = boss_name
    self.boss_hp = boss_data["hp"]
    self.max_hp = boss_data["hp"]
    self.data = boss_data
    self.participants = {}

  @discord.ui.button(
      label="💥 Tấn Công Boss", style=discord.ButtonStyle.danger, emoji="⚔️"
  )
  async def attack_boss(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    p = get_player(interaction.user.id)
    uid = interaction.user.id
    if uid not in self.participants:
      self.participants[uid] = 0

    base_dmg = (p["level"] * 30) + (p["stats"]["fruit"] * 15)
    fruit_mult = 1.0
    if p["equipped_fruit"]:
      fruit_mult = BLOXL_FRUITS_DATABASE[p["equipped_fruit"]]["mult"]
      if p["awakened"]:
        fruit_mult *= 1.4

    total_dmg = int(base_dmg * fruit_mult * random.uniform(0.8, 1.2))
    self.boss_hp -= total_dmg
    self.participants[uid] += total_dmg

    if self.boss_hp <= 0:
      for pid in self.participants:
        pl = get_player(pid)
        pl["points"] += self.data["reward_pts"]
        pl["fragments"] += self.data["reward_frag"]
        add_exp(pl, 500)

      end_embed = discord.Embed(
          title=f"🏆 ─── ĐÃ TIÊU DIỆT BOSS {self.boss_name.upper()}! ─── 🏆",
          description=(
              f"🎉 Vượt ải thành công!\n💎 Thưởng cho mỗi người tham"
              f" gia:\n• **+{self.data['reward_pts']:,} Điểm**\n•"
              f" **+{self.data['reward_frag']:,} Fragments**\n• **+500 EXP**"
          ),
          color=0x2ECC71,
      )
      for child in self.children:
        child.disabled = True
      await interaction.response.edit_message(embed=end_embed, view=self)
      return

    embed = discord.Embed(
        title=f"🔥 ─── ĐỘT KÍCH: {self.boss_name.upper()} ─── 🔥",
        description=(
            f"💥 **{interaction.user.mention}** gây ra **{total_dmg:,}"
            f" sát thương**!\n❤️ Máu Boss:"
            f" `🪓 {max(0, self.boss_hp):,}/{self.max_hp:,} HP`\n👥 Tham gia:"
            f" `{len(self.participants)} người`"
        ),
        color=0xE74C3C,
    )
    await interaction.response.edit_message(embed=embed, view=self)


# ==========================================
# CÁC LỆNH HỆ THỐNG
# ==========================================


async def profile(interaction: discord.Interaction):
  p = get_player(interaction.user.id)
  s = p["stats"]
  fruit_str = (
      f"✨ {p['equipped_fruit']} "
      f"{'*(Thức Tỉnh)*' if p['awakened'] else '*(Thường)*'}"
      if p["equipped_fruit"]
      else "Chưa trang bị"
  )

  embed = discord.Embed(
      title=f"🏴‍☠️ HỒ SƠ HẢI TẬC: {interaction.user.name.upper()}",
      description=(
          f"📊 **Cấp độ:** `{p['level']}` (Sea `{p['sea']}`)\n📈 **EXP:**"
          f" `{p['exp']:,} / {p['max_exp']:,}`\n🍈 **Trái đang dùng:**"
          f" {fruit_str}\n💰 **Điểm (Beli):**"
          f" `{p['points']:,}`\n💎 **Fragments:** `{p['fragments']:,}`\n\n🎯"
          f" **CHỈ SỐ TIỀM NĂNG (Dư: {s['stat_points']} điểm):**\n• Cận chiến"
          f" (Melee): `{s['melee']}`\n• Phòng thủ (Defense):"
          f" `{s['defense']}`\n• Kiếm sĩ (Sword): `{s['sword']}`\n• Trái Ác Quỷ"
          f" (Fruit): `{s['fruit']}`"
      ),
      color=0x3498DB,
  )
  await interaction.response.send_message(embed=embed, ephemeral=True)


async def stats_up(
    interaction: discord.Interaction, chỉ_số: str, số_lượng: int = 1
):
  p = get_player(interaction.user.id)
  s = p["stats"]

  if số_lượng <= 0 or s["stat_points"] < số_lượng:
    await interaction.response.send_message(
        "❌ Số lượng điểm không hợp lệ hoặc không đủ điểm tiềm năng!",
        ephemeral=True,
    )
    return

  chỉ_số = chỉ_số.lower()
  if chỉ_số not in ["melee", "defense", "sword", "fruit"]:
    await interaction.response.send_message(
        "❌ Chỉ số không tồn tại! Chọn: `melee`, `defense`, `sword`, `fruit`.",
        ephemeral=True,
    )
    return

  s["stat_points"] -= số_lượng
  s[chỉ_số] += số_lượng
  await interaction.response.send_message(
      f"✅ Đã tăng `{số_lượng}` điểm vào **{chỉ_số.upper()}**!", ephemeral=True
  )


async def shop_fruit(interaction: discord.Interaction):
  sample_fruits = random.sample(list(BLOXL_FRUITS_DATABASE.keys()), 3)
  desc = "🏴‍☠️ **Cửa hàng Chợ Đen (Blox Fruit Stock):**\n\n"
  for f in sample_fruits:
    info = BLOXL_FRUITS_DATABASE[f]
    desc += (
        f"• **{f}** (`{info['type']}`) - Giá: `{info['price']:,} Điểm`\n  📜"
        f" *{info['desc']}*\n\n"
    )

  desc += "👉 Dùng lệnh `/mua_trai [tên_trái]` để mua!"
  embed = discord.Embed(
      title="🛒 ─── CỬA HÀNG TRÁI ÁC QUỶ ─── 🛒",
      description=desc,
      color=0xF1C40F,
  )
  await interaction.response.send_message(embed=embed, ephemeral=True)


async def mua_trai(interaction: discord.Interaction, tên_trái: str):
  if tên_trái not in BLOXL_FRUITS_DATABASE:
    await interaction.response.send_message(
        "❌ Không tìm thấy tên trái ác quỷ này!", ephemeral=True
    )
    return

  p = get_player(interaction.user.id)
  info = BLOXL_FRUITS_DATABASE[tên_trái]
  price = info["price"]

  if p["points"] < price:
    await interaction.response.send_message(
        f"❌ Không đủ tiền! Cần `{price:,} Điểm`.", ephemeral=True
    )
    return

  p["points"] -= price
  p["inventory"]["fruits"][tên_trái] = (
      p["inventory"]["fruits"].get(tên_trái, 0) + 1
  )
  await interaction.response.send_message(
      f"🎉 Đã mua thành công trái **{tên_trái}**!", ephemeral=True
  )


async def do_quest(interaction: discord.Interaction):
  p = get_player(interaction.user.id)
  exp_gain = random.randint(200, 450)
  pts_gain = random.randint(15000, 35000)

  p["points"] += pts_gain
  leveled_up = add_exp(p, exp_gain)
  extra_msg = (
      f"\n🎉 **[LÊN CẤP!]** Đạt Level **{p['level']}** (Sea `{p['sea']}`)!"
      if leveled_up
      else ""
  )

  embed = discord.Embed(
      title="📜 ─── HOÀN THÀNH NHIỆM VỤ ─── 📜",
      description=(
          f"⚔️ **{interaction.user.mention}** hoàn thành nhiệm vụ ở Sea"
          f" {p['sea']}!\n🎁 Nhận:\n• **+{exp_gain} EXP**\n•"
          f" **+{pts_gain:,} Điểm**{extra_msg}"
      ),
      color=0x2ECC71,
  )
  await interaction.response.send_message(embed=embed)


async def dotkich_boss(
    interaction: discord.Interaction, chọn_boss: str = "The Saw"
):
  if chọn_boss not in BOSSES:
    chọn_boss = "The Saw"
  b_data = BOSSES[chọn_boss]

  p = get_player(interaction.user.id)
  if p["sea"] < b_data["sea"]:
    await interaction.response.send_message(
        f"❌ Cấp độ chưa đủ! Cần đạt Sea {b_data['sea']} để săn"
        f" **{chọn_boss}**.",
        ephemeral=True,
    )
    return

  view = RaidBossView(chọn_boss, b_data)
  embed = discord.Embed(
      title=f"⚠️ ─── SĂN BOSS: {chọn_boss.upper()} ─── ⚠️",
      description=(
          f"🏴‍☠️ **{interaction.user.mention}** đã khơi mào trận đánh"
          f" boss!\n\n❤️ Máu Boss: `🪓 {b_data['hp']:,} HP`\n👉 Nhấn nút liên"
          " tục bên dưới để tấn công!"
      ),
      color=0xE74C3C,
  )
  await interaction.response.send_message(
      content=interaction.user.mention, embed=embed, view=view
  )

# Múi giờ Việt Nam để đảm bảo 6h sáng chạy chính xác
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

# --- 1. CƠ CHẾ KIẾM ĐIỂM QUA CHAT & VOICE (CÓ CHỐNG SPAM) ---
chat_cooldowns = {}

@client.event
async def on_message(message):
    if message.author.bot:
        return
    
    user_id = message.author.id
    now = datetime.now()
    
    # Chống spam: Mỗi user phải cách nhau ít nhất 5 giây mới được tính điểm chat tiếp theo
    if user_id in chat_cooldowns:
        if (now - chat_cooldowns[user_id]).total_seconds() < 5:
            await client.process_commands(message)
            return
            
    chat_cooldowns[user_id] = now
    
    # Cộng điểm chat qua hàm chuẩn của bot
    p = get_player(user_id)
    if "points" not in p:
        p["points"] = 0
    p["points"] += 15
    await save_player_async(user_id, p)
    
    await client.process_commands(message)

# Vòng lặp cộng điểm Voice (cứ mỗi phút ở trong kênh thoại nhận 20 điểm)
async def voice_point_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.sleep(60)
        for guild in client.guilds:
            for member in guild.members:
                if member.voice and member.voice.channel and not member.bot:
                    p = get_player(member.id)
                    if "points" not in p:
                        p["points"] = 0
                    p["points"] += 20
                    await save_player_async(member.id, p)

# Khởi chạy các vòng lặp ngầm khi bot online
@client.event
async def on_ready():
    print(f"Bot đã đăng nhập thành công với tên {client.user}")
    if not hasattr(client, "bg_tasks_started"):
        client.loop.create_task(voice_point_loop())
        client.loop.create_task(daily_leaderboard_task())
        client.loop.create_task(weekly_reset_task())
        client.bg_tasks_started = True


# --- 2. CẤU HÌNH DANH HIỆU TOP & LỆNH ADMIN ---
TOP_CONFIG = {
    1: {"title": "Khư Quỷ", "color": 0xE74C3C},   # Top 1: Đỏ
    2: {"title": "Khu La", "color": 0x3498DB},    # Top 2: Xanh dương
    3: {"title": "Thế Thần", "color": 0xF1C40F}   # Top 3: Vàng
}

@client.tree.command(name="set_top_title", description="[Admin] Thay đổi tên danh hiệu và màu sắc cho Top 1, 2, 3")
@app_commands.checks.has_permissions(administrator=True)
async def set_top_title(interaction: discord.Interaction, rank: int, title: str, color_hex: str):
    if rank not in [1, 2, 3]:
        await interaction.response.send_message("❌ **Lỗi:** Chỉ có thể cấu hình cho Top 1, 2 hoặc 3!", ephemeral=True)
        return
    
    try:
        color_int = int(color_hex.replace("#", ""), 16)
    except ValueError:
        await interaction.response.send_message("❌ **Lỗi:** Mã màu không hợp lệ! Hãy dùng dạng HEX (Ví dụ: `E74C3C`)", ephemeral=True)
        return
    
    TOP_CONFIG[rank]["title"] = title
    TOP_CONFIG[rank]["color"] = color_int
    
    embed = discord.Embed(
        title="🛠️ ─── CẬP NHẬT DANH HIỆU THÀNH CÔNG ─── 🛠️",
        description=f"✨ Đã thay đổi danh hiệu **Top {rank}** thành: `[{title}]`",
        color=color_int
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Lệnh /point_edit dành cho Admin (Cộng hoặc trừ điểm) với giao diện đẹp mắt
@client.tree.command(name="point_edit", description="[Admin] Cộng hoặc trừ điểm của một người chơi")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    user="Thành viên cần thay đổi điểm",
    amount="Số điểm cần cộng (ví dụ: 100) hoặc trừ (ví dụ: -50)"
)
async def point_edit(interaction: discord.Interaction, user: discord.Member, amount: int):
    p = get_player(user.id)
    if "points" not in p:
        p["points"] = 0
        
    p["points"] += amount
    if p["points"] < 0:
        p["points"] = 0
        
    await save_player_async(user.id, p)
    
    is_add = amount > 0
    action_icon = "📈" if is_add else "📉"
    action_text = "Cộng điểm" if is_add else "Trừ điểm"
    abs_amount = abs(amount)
    
    embed = discord.Embed(
        title=f"{action_icon} ─── QUẢN LÝ ĐIỂM HỆ THỐNG ─── {action_icon}",
        description=(
            f"👤 **Thành viên:** {user.mention}\n"
            f"⚡ **Hành động:** `{action_text} ({'+' if is_add else '-'}{abs_amount:,} điểm)`\n"
            f"💰 **Tổng điểm hiện tại:** `{p['points']:,}` điểm"
        ),
        color=0x2ECC71 if is_add else 0xE74C3C
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- 3. LỆNH /bangxephang VÀ TỰ ĐỘNG CẬP NHẬT KÊNH ---
active_lb_channels = set()

def generate_leaderboard_embed():
    # Sửa lại thành truy vấn SQLite thay vì gọi .items() trên biến db
    cursor.execute("SELECT user_id, points FROM players")
    rows = cursor.fetchall()
    
    all_players = [(row[0], row[1] if row[1] is not None else 0) for row in rows]
    all_players.sort(key=lambda x: x[1], reverse=True)
    top_10 = all_players[:10]

    embed = discord.Embed(
        title="⚡ ─── BẢNG XẾP HẠNG ĐẠI HẢI TRÌNH ─── ⚡",
        description="🌟 *Hệ thống tự động cập nhật hàng ngày lúc* **06:00 sáng** *và vinh danh trao giải vào* **Chủ Nhật hàng tuần**!",
        color=0xF1C40F
    )

    desc_list = []
    for index, (uid, pts) in enumerate(top_10, start=1):
        if index == 1:
            rank_icon = "👑"
        elif index == 2:
            rank_icon = "🥈"
        elif index == 3:
            rank_icon = "🥉"
        else:
            rank_icon = f"🔹 `#{index:02d}`"
        
        title_display = ""
        if index in TOP_CONFIG:
            title_display = f" | 🏷️ **[{TOP_CONFIG[index]['title']}]**"

        desc_list.append(f"{rank_icon} ── <@{uid}> ── 🪙 **{pts:,} pts**{title_display}")

    embed.add_field(
        name="🏆 DANH SÁCH CAO THỦ TOP 10", 
        value="\n".join(desc_list) if desc_list else "📭 *Chưa có dữ liệu xếp hạng trong hệ thống.*", 
        inline=False
    )
    embed.set_footer(text="💡 Tích cực Chat (15 pts) và tham gia Voice (20 pts/phút) để vươn lên dẫn đầu!")
    return embed

@client.tree.command(name="bangxephang", description="Xem bảng xếp hạng điểm số toàn server")
async def bangxephang(interaction: discord.Interaction):
    active_lb_channels.add(interaction.channel_id)
    embed = generate_leaderboard_embed()
    await interaction.response.send_message(embed=embed)

# --- 4. TỰ ĐỘNG CẬP NHẬT LÚC 6H SÁNG (GIỜ VN) & RESET CUỐI TUẦN ---
async def daily_leaderboard_task():
    await client.wait_until_ready()
    while not client.is_closed():
        now = datetime.now(VN_TZ)
        target_time = datetime.combine(now.date(), time(6, 0), tzinfo=VN_TZ)
        if now >= target_time:
            target_time += timedelta(days=1)
        
        seconds_to_wait = (target_time - now).total_seconds()
        await asyncio.sleep(seconds_to_wait)
        
        embed = generate_leaderboard_embed()
        for channel_id in list(active_lb_channels):
            try:
                channel = client.get_channel(channel_id)
                if channel:
                    await channel.send("📢 **[THÔNG BÁO TỰ ĐỘNG]** Bảng xếp hạng đại hải trình đã được làm mới lúc **06:00 sáng**!", embed=embed)
            except Exception:
                pass

async def weekly_reset_task():
    await client.wait_until_ready()
    while not client.is_closed():
        now = datetime.now(VN_TZ)
        # Kiểm tra nếu là Chủ Nhật hàng tuần
        if now.weekday() == 6:
            all_players = sorted([(uid, data.get("points", 0)) for uid, data in db.items()], key=lambda x: x[1], reverse=True)
            if len(all_players) >= 1:
                for rank_idx, (uid, pts) in enumerate(all_players[:3], start=1):
                    p = get_player(int(uid))
                    earned_title = TOP_CONFIG[rank_idx]["title"]
                    if "titles" not in p:
                        p["titles"] = []
                    if earned_title not in p["titles"]:
                        p["titles"].append(earned_title)
                    p["equipped_title"] = earned_title
                    await save_player_async(int(uid), p)
                
                # Gửi thông báo tổng kết cuối tuần vào các kênh đang mở bảng xếp hạng
                for channel_id in list(active_lb_channels):
                    try:
                        channel = client.get_channel(channel_id)
                        if channel:
                            await channel.send("🎉 **[VINH DANH CUỐI TUẦN]** Hệ thống đã tổng kết BXH và trao thưởng danh hiệu độc quyền thành công cho **Top 3 cao thủ** xuất sắc nhất!")
                    except Exception:
                        pass
        
        # Chờ 24 tiếng sau kiểm tra lại
        await asyncio.sleep(86400)
# --- KHỞI ĐỘNG BOT VÀ GIỮ SỐNG 24/7 ---
if __name__ == "__main__":
  keep_alive()
  TOKEN = os.getenv("DISCORD_BOT_TOKEN")
  if not TOKEN:
    print("⚠️ Cảnh báo: Chưa cấu hình DISCORD_BOT_TOKEN trong biến môi trường!")
  client.run(TOKEN or "YOUR_BOT_TOKEN_HERE")
  

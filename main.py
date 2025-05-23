import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
import random

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="~", intents=intents)

giveaways = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Sync error: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if "http" in message.content or "discord.gg/" in message.content:
        if not message.author.guild_permissions.administrator:
            await message.delete()
            embed = discord.Embed(title="🚫 Anti-Link", description=f"{message.author.mention}, links are not allowed!", color=discord.Color.red())
            await message.channel.send(embed=embed)
    await bot.process_commands(message)

# === BASIC EMBED COMMANDS OMITTED HERE FOR SPACE (same as previous response) ===

# === /result slash command ===
@bot.tree.command(name="result", description="Post an EI Team result")
@app_commands.describe(
    applicant="Mention the applicant",
    username="Minecraft IGN",
    region="Region (AS or EU)",
    gamemode="Gamemode (Sword or Crystal)",
    result="Test Result (Selected or Not Selected)"
)
async def result(interaction: discord.Interaction, applicant: discord.Member, username: str, region: str, gamemode: str, result: str):
    embed = discord.Embed(title="EI Team Selection Result 🏆", color=discord.Color.blue())
    embed.add_field(name="Tester", value=interaction.user.mention, inline=False)
    embed.add_field(name="Username", value=username, inline=False)
    embed.add_field(name="Region", value=region.upper(), inline=True)
    embed.add_field(name="Gamemode", value=gamemode, inline=True)
    embed.add_field(name="Team Result", value=result, inline=False)
    embed.set_thumbnail(url=applicant.display_avatar.url)
    await interaction.response.send_message(content=applicant.mention, embed=embed)

# === Giveaway Commands ===
def convert_time(time_str):
    unit = time_str[-1]
    if unit not in "smhd":
        return None
    try:
        val = int(time_str[:-1])
    except:
        return None
    return {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit] * val

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, time: str, winners: int, *, prize: str):
    seconds = convert_time(time)
    if seconds is None:
        return await ctx.send("Invalid time format. Use `s/m/h/d`.")
    
    embed = discord.Embed(title="🎉 Giveaway!", color=discord.Color.blurple())
    embed.add_field(name="Prize", value=prize)
    embed.add_field(name="Hosted By", value=ctx.author.mention)
    embed.add_field(name="Ends In", value=f"{time}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    
    giveaways[msg.id] = {
        "end_time": datetime.utcnow() + timedelta(seconds=seconds),
        "winners": winners,
        "prize": prize,
        "host": ctx.author.id,
        "message": msg
    }
    
    await asyncio.sleep(seconds)
    new_msg = await ctx.channel.fetch_message(msg.id)
    users = await new_msg.reactions[0].users().flatten()
    users = [u for u in users if not u.bot]
    if len(users) < winners:
        await ctx.send("Not enough participants.")
    else:
        winners_list = random.sample(users, winners)
        win_mentions = ", ".join(w.mention for w in winners_list)
        result_embed = discord.Embed(title="🎉 Giveaway Ended", description=f"**Prize:** {prize}\n**Winner(s):** {win_mentions}", color=discord.Color.green())
        await ctx.send(embed=result_embed)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gend(ctx, message_id: int):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        users = await msg.reactions[0].users().flatten()
        users = [u for u in users if not u.bot]
        winners = giveaways[message_id]["winners"]
        prize = giveaways[message_id]["prize"]
        if len(users) < winners:
            return await ctx.send("Not enough participants.")
        winners_list = random.sample(users, winners)
        embed = discord.Embed(title="🎉 Giveaway Ended Early", description=f"**Prize:** {prize}\n**Winner(s):** {', '.join(w.mention for w in winners_list)}", color=discord.Color.gold())
        await ctx.send(embed=embed)
    except:
        await ctx.send("Failed to end giveaway.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def greroll(ctx, message_id: int):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        users = await msg.reactions[0].users().flatten()
        users = [u for u in users if not u.bot]
        winners = giveaways[message_id]["winners"]
        prize = giveaways[message_id]["prize"]
        if len(users) < winners:
            return await ctx.send("Not enough participants.")
        new_winners = random.sample(users, winners)
        embed = discord.Embed(title="🔄 Giveaway Rerolled", description=f"**Prize:** {prize}\n**New Winner(s):** {', '.join(w.mention for w in new_winners)}", color=discord.Color.orange())
        await ctx.send(embed=embed)
    except:
        await ctx.send("Failed to reroll giveaway.")

# === Timer Command ===
@bot.command()
async def timer(ctx, seconds: int):
    embed = discord.Embed(title="⏳ Timer Started", description=f"{seconds} seconds remaining...", color=discord.Color.purple())
    msg = await ctx.send(embed=embed)
    while seconds > 0:
        await asyncio.sleep(1)
        seconds -= 1
        embed.description = f"{seconds} seconds remaining..."
        await msg.edit(embed=embed)
    await msg.edit(embed=discord.Embed(title="⏰ Time's Up!", color=discord.Color.red()))

bot.run(TOKEN)

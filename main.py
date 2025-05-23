import os
import discord
import asyncio
import re
import random
from discord.ext import commands, tasks
from discord import app_commands
from keep_alive import keep_alive
from dotenv import load_dotenv
import aiohttp
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="~", intents=intents)
warns = {}

# Webhook logger
async def log_action(description, user=None):
    embed = discord.Embed(title="Mod Log", description=description, color=discord.Color.red())
    if user:
        embed.set_footer(text=f"{user}", icon_url=user.avatar.url if user.avatar else None)
    async with bot.session.post(WEBHOOK_URL, json={"embeds": [embed.to_dict()]}) as r:
        pass

# Events
@bot.event
async def on_ready():
    bot.session = aiohttp.ClientSession()
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_close():
    await bot.session.close()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not message.author.guild_permissions.administrator:
        if re.search(r"https?://", message.content):
            await message.delete()
            embed = discord.Embed(description="❌ No links allowed!", color=discord.Color.red())
            await message.channel.send(embed=embed)
    await bot.process_commands(message)

# Basic commands
@bot.command()
async def ping(ctx):
    await ctx.send(embed=discord.Embed(description=f"Pong! 🏓 `{round(bot.latency * 1000)}ms`", color=discord.Color.green()))

@bot.command()
async def say(ctx, *, msg):
    await ctx.send(embed=discord.Embed(description=msg, color=discord.Color.blue()))

@bot.command()
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(embed=discord.Embed(description=f"🧹 Cleared {amount} messages", color=discord.Color.orange()), delete_after=3)

@bot.command()
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(embed=discord.Embed(description=f"Kicked {member.mention} - {reason}", color=discord.Color.red()))
    await log_action(f"{ctx.author} kicked {member} for `{reason}`", member)

@bot.command()
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(embed=discord.Embed(description=f"Banned {member.mention} - {reason}", color=discord.Color.red()))
    await log_action(f"{ctx.author} banned {member} for `{reason}`", member)

@bot.command()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    uid = str(member.id)
    warns[uid] = warns.get(uid, 0) + 1
    await ctx.send(embed=discord.Embed(description=f"⚠️ Warned {member.mention} - {reason} (Total: {warns[uid]})", color=discord.Color.yellow()))
    await log_action(f"{ctx.author} warned {member}: `{reason}`", member)
    if warns[uid] >= 3:
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=10))
        await ctx.send(embed=discord.Embed(description=f"⏳ {member.mention} timed out for 10 minutes (3 warns)", color=discord.Color.red()))
        warns[uid] = 0

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(embed=discord.Embed(title=f"{member}'s Avatar", color=discord.Color.random()).set_image(url=member.avatar.url))

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member}", color=discord.Color.blurple())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"))
    embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=guild.name, color=discord.Color.green())
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Owner", value=guild.owner)
    embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.command()
async def accountage(ctx, member: discord.Member = None):
    member = member or ctx.author
    age = discord.utils.utcnow() - member.created_at
    await ctx.send(embed=discord.Embed(description=f"{member.mention}'s account is `{age.days}` days old", color=discord.Color.blurple()))

# Slash command: /result
@bot.tree.command(name="result", description="Post a team selection result")
@app_commands.describe(applicant="Mention the applicant", username="Minecraft username", region="AS or EU", gamemode="Sword or Crystal", result="Selected or Not Selected")
async def result(interaction: discord.Interaction, applicant: discord.Member, username: str, region: str, gamemode: str, result: str):
    embed = discord.Embed(title="JUMPER'S Team Selection Result 🏆", color=discord.Color.blue())
    embed.set_thumbnail(url=applicant.avatar.url)
    embed.add_field(name="Tester", value=interaction.user.mention, inline=False)
    embed.add_field(name="Username", value=username, inline=True)
    embed.add_field(name="Region", value=region.upper(), inline=True)
    embed.add_field(name="Gamemode", value=gamemode, inline=True)
    embed.add_field(name="Team Result", value=result, inline=True)
    await interaction.response.send_message(content=applicant.mention, embed=embed)

# Cool command: embedcreator
@bot.command()
async def embedcreator(ctx, title, desc, image_url):
    embed = discord.Embed(title=title, description=desc, color=discord.Color.blue())
    embed.set_image(url=image_url)
    await ctx.send(embed=embed)

# Cool command: giveaway
@bot.command()
async def giveaway(ctx, duration: int, *, prize):
    embed = discord.Embed(title="🎉 Giveaway 🎉", description=f"**Prize:** {prize}\nReact with 🎉 to enter!\nDuration: {duration} seconds", color=discord.Color.gold())
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(duration)

    msg = await ctx.channel.fetch_message(msg.id)
    users = [u async for u in msg.reactions[0].users() if not u.bot]

    if users:
        winner = random.choice(users)
        await ctx.send(embed=discord.Embed(description=f"🎊 Congratulations {winner.mention}, you won **{prize}**!", color=discord.Color.green()))
    else:
        await ctx.send("No participants.")

# Timer command
@bot.command()
async def timer(ctx, seconds: int):
    await ctx.send(embed=discord.Embed(description=f"⏳ Timer set for {seconds} seconds!", color=discord.Color.orange()))
    await asyncio.sleep(seconds)
    await ctx.send(embed=discord.Embed(description=f"⏰ Time's up!", color=discord.Color.red()))

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 JumperBot Help Menu",
        description="Here are my commands:\n\n"
                    "**</> Moderation**\n"
                    "`~ping`, `~userinfo`, `~serverinfo`, `~accountage`, `~avatar`, `~banner`, `~say`, `~clear`, `~kick`, `~ban`, `~warn`\n\n"
                    "**</> Anti-Link**\n"
                    "Auto deletes links from non-admins.\n\n"
                    "**</> Extras**\n"
                    "`~giveaway`, `~timer`, `~embed`\n\n"
                    "**</> Custom**\n"
                    "`/result` - Post test results for Crystal/Sword applicants.",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url="https://i.ibb.co/RTz5nPxt/JUMPERS.gif")
    embed.set_footer(text="Requested by {}".format(ctx.author), icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

keep_alive()
bot.run(TOKEN)

# Make sure to close session when bot stops
async def close_session():
    await bot.session.close()

import atexit
atexit.register(lambda: asyncio.get_event_loop().run_until_complete(close_session()))

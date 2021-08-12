#######################################################################
# PLEASE RUN "pip install -r requirements"                            #
# PLEASE EDIT CONFIG.JSON WITH THE CONFIGURATION THAT YOU LIKE        #
# GENERATE A BOT TOKEN AT https://discord.com/developers/applications #
# PLEASE ENABLE SERVER MEMBERS INTENT ON THE BOT YOU CREATE           #
#######################################################################

import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions
import json
import string
import random
import datetime
from typing import Optional
from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands.core import command
import utils
import luhn
import os
import time
import threading
import json

x = open("config.json", "r")
configuration = json.load(x)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=tuple(configuration['Prefixes']), case_insensitive=True, intents=intents)
bot.remove_command("help")

with open("users.json", "ab+") as ab:
    ab.close()
    f = open('users.json','r+')
    f.readline()
    if os.stat("users.json").st_size == 0:
      f.write("{}")
      f.close()
    else:
      pass
 
users = None

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{configuration['Prefixes'][0]}help"))
    print("Im online and ready!")


@bot.event
async def on_member_join(member):
    created_at = datetime.datetime.now() - member.created_at

    created_athours, created_atremainder = divmod(int(created_at .total_seconds()), 3600)
    created_atminutes, created_atseconds = divmod(created_atremainder, 60)
    created_atdays, created_athours = divmod(created_athours, 24)
    if int(created_atdays) < 7:
        await member.send("Your account is less than a week old. You have been kicked. Join back after a week.")
        await member.kick()

@bot.event    
async def on_message(message):
    if message.author.bot == False:
        global users
        with open('users.json', 'r') as f:
            users = json.load(f)
        await add_experience(users, message.author, message)
        await level_up(users, message.author, message)
        with open('users.json', 'w') as f:
            json.dump(users, f)
            await bot.process_commands(message)
 
async def add_experience(users, user, message):
    if not f'{user.id}' in users:
        users[f'{user.id}'] = {}
        users[f'{user.id}']['experience'] = 0
        users[f'{user.id}']['level'] = 0
    xp = None
    if len(message.clean_content) <= 10:
        xp = 4
    elif len(message.clean_content) <= 20:
        xp = 6
    elif len(message.clean_content) <= 40:
        xp = 8
    elif len(message.clean_content) <= 80:
        xp = 10
    else:
        xp = 12
    users[f'{user.id}']['experience'] += xp
 
async def level_up(users, user, message):
  experience = users[f'{user.id}']["experience"]
  lvl_start = users[f'{user.id}']["level"]
  lvl_end = int(experience ** (1 / 3))
  if lvl_start < lvl_end:
    await message.channel.send(f':tada: {user.mention} has reached level {lvl_end}. Congrats! :tada:')
    users[f'{user.id}']["level"] = lvl_end
 
@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def level(ctx, member: discord.Member = None):
    if member == None:
        userlvl = users[f'{ctx.author.id}']['level']
        userexp = users[f'{ctx.author.id}']['experience']
        await ctx.send(f'{ctx.author.mention} You are at level {userlvl}, with XP {userexp}')
    else:
        userlvl2 = users[f'{member.id}']['level']
        userexp2 = users[f'{member.id}']['experience']    
        await ctx.send(f'{member.mention} is at level {userlvl2}, with XP {userexp2}')
 
@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def leaderboard(ctx):
    data_levels = users.values()
    levels = []
    for x in data_levels:
        levels.append(x['level'])

    data_users = users.keys()
    userrs = []
    for x in data_users:
        userrs.append(x)

    userrs = [x for _,x in sorted(zip(levels,userrs), reverse=True)]
    levels = sorted(levels, reverse=True)

    stringThing = ''
    rank = 1
    for i, x in enumerate(userrs):
        stringThing = stringThing + f"#{rank} <@{x}> : Level {levels[i]}\n"
        rank += 1
    embed = discord.Embed(title="Leaderboard", description=stringThing)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def add(ctx, title, link, description):
    password_characters = string.digits
    UniqueID = ''.join(random.choice(password_characters) for _ in range(12))

    AwaitingApproval = discord.Embed(title=title, description=f"Submitter: <@{ctx.author.id}>", color=0x77c128)
    AwaitingApproval.add_field(name=link, value=description, inline=False)
    AwaitingApproval.add_field(name="Unique ID", value=int(UniqueID), inline=False)

    ApprovalChannel = bot.get_channel(configuration['ApproveChannelID'])
    await ApprovalChannel.send(embed=AwaitingApproval)
    await ctx.send("Thanks for your submission! The mods will check it out and approve or deny it.")

    NewSub = {"id": int(UniqueID), "title": title, "link": link, "description": description, "user": ctx.author.id}

    submissionsFile = open("submissions.json", "r")
    submissions = json.load(submissionsFile)
    submissions.append(NewSub)
    submissionsFile.close()

    submissionsFile = open("submissions.json", "w")
    json.dump(submissions, submissionsFile)
    submissionsFile.close()

@bot.command()
@commands.has_permissions(administrator=True)
async def approve(ctx, UniqueID, ChannelID):
    submissionsFile = open("submissions.json", "r")
    submissions = json.load(submissionsFile)
    submissionsFile.close()

    channel = bot.get_channel(int(ChannelID))

    for i, submission in enumerate(submissions):
        if submission["id"] == int(UniqueID):
            ApprovedSub = discord.Embed(title=submission['title'], description=f"Thanks to <@{submission['user']}>!", color=0x77c128)
            ApprovedSub.add_field(name=submission['link'], value=submission['description'], inline=False)

            await channel.send(embed=ApprovedSub)

            submissions.pop(i)
            submissionsFile = open("submissions.json", "w")
            json.dump(submissions, submissionsFile)
            submissionsFile.close()
            
            await ctx.send("Approved!")
            break
        else:
            pass
    else:
        await ctx.send("The ID provided is not a valid one. Please provide a valid ID.")
        return
    
@bot.command()
@commands.has_permissions(administrator=True)
async def deny(ctx, UniqueID):
    submissionsFile = open("submissions.json", "r")
    submissions = json.load(submissionsFile)
    submissionsFile.close()

    for i, submission in enumerate(submissions):
        if submission["id"] == int(UniqueID):
            submissions.pop(i)
            submissionsFile = open("submissions.json", "w")
            json.dump(submissions, submissionsFile)
            submissionsFile.close()
            
            await ctx.send("Denied!")
            break
        else:
            pass
    else:
        await ctx.send("The ID provided is not a valid one. Please provide a valid ID.")
        return


@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def generate(ctx, bin):
    CCs = []
    for x in range(5):
        CCs.append(utils.luhn(bin))
    
    verified = []
    for x in CCs:
        verified.append(luhn.verify(x))
    
    final = []
    for i, x in enumerate(verified):
        if x:
            final.append(CCs[i])
        else:
            pass
    card = ""
    for cc in final:
        card = card + f"{cc}\n"
    await ctx.send(f"Here are 5 validated credit card numbers:\n{card}")


@bot.command()
@commands.cooldown(1, 15, commands.BucketType.user)
async def validate(ctx, CC):
    valid = luhn.verify(CC)
    if valid:
        await ctx.send("The provided CC number is valid.")
    else:
        await ctx.send("The provided CC number is invalid.")

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def whois(ctx):
    if ctx.message.mentions:
        for x in ctx.message.mentions:
            duration = datetime.datetime.now() - x.joined_at

            hours, remainder = divmod(int(duration .total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            days, hours = divmod(hours, 24)

            created_at = datetime.datetime.now() - x.created_at

            created_athours, created_atremainder = divmod(int(created_at .total_seconds()), 3600)
            created_atminutes, created_atseconds = divmod(created_atremainder, 60)
            created_atdays, created_athours = divmod(created_athours, 24)

            roles = str([y.mention for y in x.roles]).replace('[','').replace(']','').replace('\'','')

            embed = discord.Embed(title="User Info", description=f"Here is <@{x.id}> profile details.")
            embed.set_thumbnail(url=x.avatar_url)
            embed.add_field(name="Id", value=x.id)
            embed.add_field(name="Created At", value=x.created_at.strftime('%d, %b %Y'))
            embed.add_field(name="Joined At", value=x.joined_at.strftime('%d, %b %Y'))
            embed.add_field(name="Display Name", value=x.display_name)
            embed.add_field(name="Avatar", value=f"[Link]({x.avatar_url})")
            embed.add_field(name="Roles", value=roles)
            embed.add_field(name="Account Age", value=f"{created_atdays} days, {created_athours} hours")
            embed.add_field(name="Join Age", value=f"{days} days, {hours} hours")

            await ctx.send(embed=embed)
    else:
        user = ctx.message.author.id
        x = ctx.guild.get_member(user_id=user)
        duration = datetime.datetime.now() - x.joined_at

        hours, remainder = divmod(int(duration .total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        created_at = datetime.datetime.now() - x.created_at
        created_athours, created_atremainder = divmod(int(created_at .total_seconds()), 3600)
        created_atminutes, created_atseconds = divmod(created_atremainder, 60)
        created_atdays, created_athours = divmod(created_athours, 24)

        roles = str([y.mention for y in x.roles]).replace('[','').replace(']','').replace('\'','')

        embed = discord.Embed(title="User Info", description=f"Here is <@{x.id}> profile details.")
        embed.set_thumbnail(url=x.avatar_url)
        embed.add_field(name="Id", value=x.id)
        embed.add_field(name="Created At", value=x.created_at.strftime('%d, %b %Y'))
        embed.add_field(name="Joined At", value=x.joined_at.strftime('%d, %b %Y'))
        embed.add_field(name="Display Name", value=x.display_name)
        embed.add_field(name="Avatar", value=f"[Link]({x.avatar_url})")
        embed.add_field(name="Roles", value=roles)
        embed.add_field(name="Account Age", value=f"{created_atdays} days, {created_athours} hours")
        embed.add_field(name="Join Age", value=f"{days} days, {hours} hours")

        await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, user_id: Optional[int]):
    if ctx.message.mentions:
        for x in ctx.message.mentions:
            await x.kick()
            await ctx.send(f"Kicked {x.mention}")
    elif user_id:
        x = ctx.guild.get_member(int(user_id))
        await x.kick()
        await ctx.send(f"Kicked {x.mention}")
    else:
        await ctx.send("You need to mention or provide the ID to kick!")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, user_id: Optional[int]):
    if ctx.message.mentions:
        for x in ctx.message.mentions:
            await x.ban()
            await ctx.send(f"Banned {x.mention}")
    elif user_id:
        x = ctx.guild.get_member(int(user_id))
        await x.ban()
        await ctx.send(f"Banned {x.mention}")
    else:
        await ctx.send("You need to mention user or provide the ID to ban!")


@bot.command()
async def help(ctx):
    helpEmbed = discord.Embed(title="Help!", description="These are the available commands!", color=0x77c128)
    helpEmbed.add_field(name=f'{configuration["Prefixes"][0]}add "title" "link" "description"', value="Adds a submission to the submission queue. Please provide all the command parameters as they are not optional and use double quotation marks for each parameter.")
    helpEmbed.add_field(name=f'{configuration["Prefixes"][0]}approve [unique id] [channel id]', value="ADMIN COMMAND ONLY. Approves a submission with id [unique id] and sends it to channel with id [channel id]. Don't include the square brackets they are not part of the command.")
    helpEmbed.add_field(name=f'{configuration["Prefixes"][0]}deny [unique id]', value="ADMIN COMMAND ONLY. Denies a submission with id [unique id]. Don't include the square brackets they are not part of the command.")

    await ctx.send(embed=helpEmbed)


@approve.error
@deny.error
@generate.error
@validate.error
@add.error
@whois.error
@level.error
async def permissions_error(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.send(error)
        return
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(error)
        return





bot.run(configuration['BotToken'])

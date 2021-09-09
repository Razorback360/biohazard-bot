#######################################################################
# PLEASE RUN "pip install -r requirements"                            #
# PLEASE EDIT CONFIG.JSON WITH THE CONFIGURATION THAT YOU LIKE        #
# GENERATE A BOT TOKEN AT https://discord.com/developers/applications #
# PLEASE ENABLE SERVER MEMBERS INTENT ON THE BOT YOU CREATE           #
#######################################################################

import discord
from discord.ext import commands
import json
import string
import random
import datetime
from typing import Optional
import utils
import luhn
import os
import json
from tortoise import Tortoise
from database import Levels, AFK, Submissions, RoleBlacklist, LevelRole, BackupMessages, BackupChannels, BackupRoles, BackupUsers, ReactionChannels
from tortoise.exceptions import DoesNotExist
import chat_exporter
import io
import discapty
import asyncio
import DiscordUtils

x = open("config.json", "r")
configuration = json.load(x)
x.close()


intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=tuple(configuration['Prefixes']), case_insensitive=True, intents=intents)
bot.remove_command("help")

##############################
#                            #
#         BOT EVENTS         #
#                            #
##############################


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{configuration['Prefixes'][0]}help"))
    await Tortoise.init(
        db_url="sqlite://db.sqlite3",
        modules={'models': ['database']}
    )
    await Tortoise.generate_schemas()

    chat_exporter.init_exporter(bot)
    print("Im online and ready!")


@bot.event
async def on_member_join(member):
    created_at = datetime.datetime.now() - member.created_at

    created_athours, created_atremainder = divmod(int(created_at .total_seconds()), 3600)
    created_atminutes, created_atseconds = divmod(created_atremainder, 60)
    created_atdays, created_athours = divmod(created_athours, 24)
    if int(created_atdays) < configuration["Age"] if configuration["Age"] else 1:
        await member.send(f"Your account is less than {configuration['Age']} day(s) old. You have been kicked. Join back after {configuration['Age']} day(S).")
        await member.kick()


@bot.event
async def on_message(message):
    if message.guild:
        if message.author.bot == False:
            for role in message.author.roles:
                try:
                    await RoleBlacklist.get(role_id=role.id)
                    await bot.process_commands(message)
                    return
                except DoesNotExist:
                    pass
                    continue
            try:
                user = await Levels.get(user_id=message.author.id)
                await add_experience(user, message.author, message)
            except DoesNotExist:
                await add_experience(None, message.author, message)
        if message.mentions:
            for x in message.mentions:
                try:
                    user = await AFK.get(user_id=x.id)
                    await message.channel.send(f"{x.display_name} is AFK: {user.message}")
                except DoesNotExist:
                    pass
        try:
            channel_reactions = await ReactionChannels.get(channel_id=message.channel.id)
            channel_reactions = await ReactionChannels.get(channel_id=message.channel.id).values()
            for channel in channel_reactions:
                reactions = json.loads(channel['reactions'])
            for reaction in reactions:
                emoji = discord.utils.get(bot.emojis, name=reaction)
                await message.add_reaction(emoji if emoji else reaction)
        except DoesNotExist:
            pass
    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    global tickets
    message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
    reaction = discord.utils.get(message.reactions, emoji="📧")
    user = payload.member
    if "TicketChannel" in configuration:
        if "TicketMessageID" in configuration:
            if message.id == configuration['TicketMessageID']:
                if user != bot.user:
                    await message.remove_reaction(payload.emoji, user)
                    if "CategoryID" in configuration:
                        guild = bot.get_guild(id=payload.guild_id)
                        category = guild.get_channel(configuration['CategoryID'])
                        channel = await category.create_text_channel(user.display_name)
                        member = guild.get_member(user.id)
                        await channel.edit(sync_permission=True)
                        await channel.set_permissions(member, read_messages=True, send_messages=True, read_message_history=True)
                        await channel.send(member.mention)


##############################
#                            #
#        MISCELLANEOUS       #
#                            #
##############################

@bot.command()
@commands.has_permissions(manage_channels=True)
async def set_log_channel(ctx, channel_id: Optional[int]):
    global configuration
    global x
    if ctx.message.channel_mentions:
        for channel in ctx.message.channel_mentions:
            configuration['LogChannel'] = channel.id
            y = open("config.json", "w")
            json.dump(configuration, y)
            y.close()
            x.close()
            x = open("config.json", "r")
            configuration = json.load(x)
            x.close()
            await ctx.send("Channel set.")
            break
    elif channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            configuration['LogChannel'] = channel_id
            y = open("config.json", "w")
            json.dump(configuration, y)
            y.close()
            x.close()
            x = open("config.json", "r")
            configuration = json.load(x)
            x.close()
            await ctx.send("Channel set.")
        else:
            await ctx.send("Invalid ID.")
    else:
        await ctx.send("No channel was mentioned and no ID was provided.")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_min_age(ctx, age: int):
    global configuration
    global x
    configuration['Age'] = age
    y = open("config.json", "w")
    json.dump(configuration, y)
    y.close()
    x.close()
    x = open("config.json", "r")
    configuration = json.load(x)
    x.close()
    await ctx.send(f"Minimum age set to {age} day(s).")


@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def whois(ctx):
    try:
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

                roles = str([y.mention for y in x.roles]).replace('[', '').replace(']', '').replace('\'', '')

                embed = discord.Embed(title="User Info", description=f"Here is <@{x.id}> profile details.", color=0xFF5733)
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

            roles = str([y.mention for y in x.roles]).replace('[', '').replace(']', '').replace('\'', '')

            embed = discord.Embed(title="User Info", description=f"Here is <@{x.id}> profile details.", color=0xFF5733)
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
    except:
        await ctx.send("User not found.")


@bot.command()
@commands.cooldown(1, 3, commands.BucketType.user)
async def afk(ctx, *, arg):
    await AFK(user_id=ctx.message.author.id, message=arg).save()
    await ctx.send("You are now AFK. Use unafk command to remove your AFK status.")


@bot.command()
@commands.cooldown(1, 3, commands.BucketType.user)
async def unafk(ctx):
    try:
        await AFK.get(user_id=ctx.message.author.id)
    except DoesNotExist:
        await ctx.send("You weren't AFK.")
        return

    await AFK.filter(user_id=ctx.message.author.id).delete()
    await ctx.send("You are no longer AFK.")


@bot.command()
async def help(ctx, command: Optional[str]):
    list_of_commands = [

        {"command": "add", "value": f"'[title]' '[link]' '[description]'\nMust have double quotes as shown.\n\n**Example: ?add 'Bin' 'https://test.url' 'Bin: 123456xxxx, Country: US'**"},
        {"command": "level", "value": f"<mention> or <user id> or nothing. \n\n**Example: {configuration['Prefixes'][0]}level or 12321321321 or <@{ctx.message.author.id}>**"},
        {"command": "leaderboard", "value": f"No arguments.\n\n**Example: {configuration['Prefixes'][0]}leaderboard**"},
        {"command": "generate", "value": f"[6 character bin]\n\n**Example: {configuration['Prefixes'][0]}generate 123456**"},
        {"command": "validate", "value": f"[card number].\n\n**Example: {configuration['Prefixes'][0]}validate 12341234567890**"},
        {"command": "afk", "value": f"[afk message].\n\n**Example: {configuration['Prefixes'][0]}afk I'm going to sleep.**"},
        {"command": "unafk", "value": f"No arguments.\n\n**Example: {configuration['Prefixes'][0]}unafk**"},
        {"command": "whois", "value": f"<mention> or nothing. \n\n**Example: {configuration['Prefixes'][0]}whois or <@{ctx.message.author.id}>**"},
        {"command": "verify", "value": f"No arguments."},
        {"command": "close_ticket", "value": f"No arguments.\n**__Must be used in ticket that is being closed.__**\n\n**Example: {configuration['Prefixes'][0]}closeticket**"},
        {"command": "backup", "value": f"No arguments.\nRequires adminstrator permission.\n\n**Example: {configuration['Prefixes'][0]}backup**"},
        {"command": "restore", "value": f"No arguments.\nRequires adminstrator permission.\n\n**Example: {configuration['Prefixes'][0]}restore**"},
        {"command": "approve",
         "value": f"[unique id] [<channel id> or <channel mention>].\nRequires manage messages permission.\n\n**Example: {configuration['Prefixes'][0]}approve 3146257 12345673432 or #general**"},
        {"command": "deny", "value": f"[unique id].\nRequires manage messages permission.\n\n**Example: {configuration['Prefixes'][0]}deny 121312341**"},
        {"command": "kick", "value": f"[<user id> or <user mention>].\nRequires kick members permission.\n\n**Example: {configuration['Prefixes'][0]}kick 12143214312321321 or <@{ctx.message.author.id}>**"},
        {"command": "ban", "value": f"[<user id> or <user mention>].\nRequires ban members permission.\n\n**Example: {configuration['Prefixes'][0]}ban 12123123214124123 or <@{ctx.message.author.id}>**"},
        {"command": "set_min_age", "value": f"[days].\nRequires adminstrator permission.\n\n**Example: {configuration['Prefixes'][0]}set_min_age 7**"},
        {"command": "set_verified_role", "value": f"[<role id> or <role mention>].\nRequires manage roles permission\n\n**Example: {configuration['Prefixes'][0]}set_verified_role 2134124123413421 or @role**"},
        {"command": "set_ticket",
         "value":
         f"[category id].\n**__Must be used in the channel where you want 'react to create ticket' to be__**.\nRequires manage channels and manage messages permissions.\n\n**Example: {configuration['Prefixes'][0]}set_ticket_channel 1231242314321213**"},
        {"command": "set_log_channel",
         "value": f"[<channel id> or <channel mention].\nRequires manage channels permission\n\n**Example: {configuration['Prefixes'][0]}set_log_channel 21321421342141 or #general**"},
        {"command": "set_level_channel",
         "value": f"[<channel id> or <channel mention>].\nRequires manage channels permission\n\n**Example: {configuration['Prefixes'][0]}set_level_channel 2314214231432141123 or #general**"},
        {"command": "add_reaction",
         "value": f"[<channel_id> or <channel mention>].\nRequires manage channels and manage messages permissions\n\n**Example: {configuration['Prefixes'][0]}add_reaction 213478963125489123 or #general**"},
        {"command": "add_level_role",
         "value": f"[level] [<role id> or <role mention>].\nRequires manage roles permission.\n\n**Example: {configuration['Prefixes'][0]}add_level_role 5 1241234114331 or @role**"},
        {"command": "blacklist", "value": f"[<role id> or <role mention>].\nRequires manage roles permission.\n\n**Example: {configuration['Prefixes'][0]}blacklist 2132143231423141 or @role**"},
        {"command": "unblacklist", "value": f"[<role id> or <role mention>].\nRequires manage roles permission.\n\n**Example: {configuration['Prefixes'][0]}unblacklist 2142314513531423114 or @role**"},
        {"command": "stop_reactions",
         "value": f"[<channel id> or <channel mention>].\nRequires manage channels and manage messages permissions.\n\n**Example: {configuration['Prefixes'][0]}stop_reactions 314231482301472314 or #general**"},
        {"command": "set_submission_channel",
         "value": f"[<channel id> or <channel mention].\nRequires manage channels permission\n\n**Example: {configuration['Prefixes'][0]}set_submission_channel 214832017423014 or #general**"}]

    if command:
        for com in list_of_commands:
            if com["command"] == command:
                value = com['value']
                value = value.replace("'", '"')
                embed1 = discord.Embed(title=command, description=f"{configuration['Prefixes'][0]}{command} {value}", color=0xFF5733)
                embed1.set_footer(text="Arguments between [] are required.\nArguments between <> are optional.\n[<> or <>] means it is required to use one.")
                await ctx.send(embed=embed1)
                return
    helpEmbedSubmissions = discord.Embed(
        title="Help! (Submissions)",
        description=f"These are the available commands!\nType '{configuration['Prefixes'][0]}help [command name]' for more info about a command.",
        color=0xFF5733, inline=True
    )
    helpEmbedSubmissions.add_field(
        name=f'add',
        value="Adds a submission to the submission queue.",
    )
    helpEmbedSubmissions.add_field(
        name=f'set_submission_channel',
        value="Sets submission channel."
    )
    helpEmbedSubmissions.add_field(
        name=f'approve',
        value="Approves a submission.",
        inline=True)
    helpEmbedSubmissions.add_field(
        name=f'deny',
        value="Denies a submission.",
        inline=True)
    helpEmbedLevels = discord.Embed(
        title="Help! (Levels)",
        description=f"These are the available commands!\nType '{configuration['Prefixes'][0]}help [command name]' for more info about a command.",
        color=0xFF5733, inline=True
    )
    helpEmbedMisc = discord.Embed(
        title="Help! (Miscellaneous)",
        description=f"These are the available commands!\nType '{configuration['Prefixes'][0]}help [command name]' for more info about a command.",
        color=0xFF5733, inline=True
    )
    helpEmbedCC = discord.Embed(
        title="Help! (Bins & Validation)",
        description=f"These are the available commands!\nType '{configuration['Prefixes'][0]}help [command name]' for more info about a command.",
        color=0xFF5733, inline=True
    )
    helpEmbedCaptcha = discord.Embed(
        title="Help! (Captcha)",
        description=f"These are the available commands!\nType '{configuration['Prefixes'][0]}help [command name]' for more info about a command.",
        color=0xFF5733, inline=True
    )
    helpEmbedTickets = discord.Embed(
        title="Help! (Tickets)",
        description=f"These are the available commands!\nType '{configuration['Prefixes'][0]}help [command name]' for more info about a command.",
        color=0xFF5733, inline=True
    )
    helpEmbedLevels.set_footer(text="Arguments between [] are required.\nArguments between <> are optional.\n[<> or <>] means it is required to use one.")
    helpEmbedLevels.add_field(
        name=f'level',
        value="Lists level and xp."
    )
    helpEmbedLevels.add_field(
        name=f'leaderboard',
        value="Level leaderboard."
    )
    helpEmbedCC.add_field(
        name=f'generate',
        value="Generates CC. (Must be 6 chars)"
    )
    helpEmbedCC.add_field(
        name=f'validate',
        value="Validates a CC."
    )
    helpEmbedMisc.add_field(
        name=f'afk',
        value="Sets user as AFK."
    )
    helpEmbedMisc.add_field(
        name=f'unafk',
        value="Removes user AFK."
    )
    helpEmbedMisc.add_field(
        name=f'whois',
        value="Sends user info."
    )
    helpEmbedCaptcha.add_field(
        name=f'verify',
        value="Initiates a captcha verification."
    )
    helpEmbedTickets.add_field(
        name=f'close_ticket',
        value="Closes a ticket."
    )
    helpEmbedBackup = discord.Embed(
        title="Help! (Backup & Restore)",
        description=f"These are the available commands!\nType '{configuration['Prefixes'][0]}help [command name] for more info about a command.",
        color=0xFF5733, inline=True
    )
    helpEmbedReaction = discord.Embed(
        title="Help! (Auto-React)",
        description=f"These are the available commands!\nType '{configuration['Prefixes'][0]}help [command name] for more info about a command.",
        color=0xFF5733, inline=True
    )
    helpEmbedBackup.set_footer(text="Arguments between [] are required.\nArguments between <> are optional.\n[<> or <>] means it is required to use one.")
    helpEmbedBackup.add_field(
        name=f'backup',
        value="Backup the server."
    )
    helpEmbedBackup.add_field(
        name=f'restore',
        value="Restore a backup."
    )
    helpEmbedMisc.add_field(
        name=f'kick',
        value="Kick a user."
    )
    helpEmbedMisc.add_field(
        name=f'ban',
        value="Ban a user."
    )
    helpEmbedCaptcha.add_field(
        name=f'set_min_age',
        value="Sets minimum age required to join server."
    )
    helpEmbedCaptcha.add_field(
        name=f'set_verified_role',
        value="Sets a role to be assigned when captcha is solved."
    )
    helpEmbedTickets.add_field(
        name=f'set_ticket',
        value="Sets channel for reaction tickets and category for channel creation."
    )
    helpEmbedTickets.add_field(
        name=f'set_log_channel',
        value="Sets log channel."
    )
    helpEmbedLevels.add_field(
        name=f'set_level_channel',
        value="Sets level notifictaion channel."
    )
    helpEmbedReaction.add_field(
        name=f'add_reaction',
        value="Add an auto react reaction to channel."
    )
    helpEmbedReaction.add_field(
        name=f'stop_reactions',
        value="Stops auto react."
    )
    helpEmbedLevels.add_field(
        name=f'add_level_role',
        value="Adds a role to a level."
    )
    helpEmbedLevels.add_field(
        name=f'blacklist',
        value="Blacklists a role to prevent from leveling."
    )
    helpEmbedLevels.add_field(
        name=f'unblacklist',
        value="Unblacklists."
    )
    paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx, remove_reactions=True)
    paginator.add_reaction('\u25c0', "back")
    paginator.add_reaction('\u25b6', "next")
    embeds = [helpEmbedSubmissions, helpEmbedBackup, helpEmbedCaptcha, helpEmbedCC, helpEmbedLevels, helpEmbedReaction, helpEmbedTickets, helpEmbedMisc]
    await paginator.run(embeds)

##############################
#                            #
#         MODERATION         #
#                            #
##############################


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

##############################
#                            #
#    CC GEN & VALIDATION     #
#                            #
##############################


@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def generate(ctx, bin):
    length = len(str(bin))
    if length > 6 or length < 6:
        await ctx.send("Only 6 digit bins please!")
        return
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
        data = utils.cvv_date()
        card = card + f"{cc} | {data['cvv']} | {data['date']}\n"
    await ctx.send(f"Here are 5 validated credit card numbers:\n{card}")


@bot.command()
@commands.cooldown(1, 15, commands.BucketType.user)
async def validate(ctx, CC):
    valid = luhn.verify(CC)
    if valid:
        await ctx.send("The provided CC number is valid.")
    else:
        await ctx.send("The provided CC number is invalid.")

##############################
#                            #
#         Submissions        #
#                            #
##############################
@bot.command()
@commands.has_permissions(manage_channels=True)
async def set_submission_channel(ctx, channel_id: Optional[int]):
    global configuration
    global x
    if ctx.message.channel_mentions:
        for channel in ctx.message.channel_mentions:
            configuration['SubmissionChannel'] = channel.id
            y = open("config.json", "w")
            json.dump(configuration, y)
            y.close()
            x.close()
            x = open("config.json", "r")
            configuration = json.load(x)
            x.close()
            await ctx.send("Channel set.")
            break
    elif channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            configuration['SubmissionChannel'] = channel_id
            y = open("config.json", "w")
            json.dump(configuration, y)
            y.close()
            x.close()
            x = open("config.json", "r")
            configuration = json.load(x)
            x.close()
            await ctx.send("Channel set.")
        else:
            await ctx.send("Invalid ID.")
            return
    else:
        await ctx.send("No channel was mentioned and no ID was provided.")

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def add(ctx, title, link, description):
    if configuration['SubmissionChannel']:
        password_characters = string.digits
        UniqueID = ''.join(random.choice(password_characters) for _ in range(12))

        AwaitingApproval = discord.Embed(title=title, description=f"Submitter: <@{ctx.message.author.id}>", color=0xFF5733)
        AwaitingApproval.add_field(name=link, value=description, inline=False)
        AwaitingApproval.add_field(name="Unique ID", value=int(UniqueID), inline=False)

        ApprovalChannel = bot.get_channel(configuration['SubmissionChannel'])
        await ApprovalChannel.send(embed=AwaitingApproval)
        await ctx.send("Thanks for your submission! The mods will check it out and approve or deny it.")

        await Submissions(user_id=ctx.message.author.id, title=title, link=link, description=description, unique_id=UniqueID).save()
    else:
        await ctx.send("Pleas contact adminstration to setup a submissions channel.")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def approve(ctx, UniqueID, ChannelID: Optional[int]):
    try:
        data = await Submissions.get(unique_id=UniqueID)
    except DoesNotExist:
        await ctx.send("The ID provided is not a valid one. Please provide a valid ID.")
        return
    channel = None
    if ctx.message.channel_mentions:
        for channelobj in ctx.message.channel_mentions:
            channel = channelobj
            break
    elif ChannelID:
        channel = bot.get_channel(int(ChannelID))
        if channel:
            pass
        else:
            await ctx.send("Channel ID is not a valid one.")
            return
    else:
        await ctx.send("No channel was mentioned and no ID was provided.")
    ApprovedSub = discord.Embed(
        title=data.title, description=f"Thanks to <@{data.user_id}>!\n\n**{data.link}**\n{data.description}"
        if data.link else f"Thanks to <@{data.user_id}>!\n\n{data.description}", color=0xFF5733)

    await channel.send(embed=ApprovedSub)
    await ctx.send("Approved!")
    await Submissions.filter(unique_id=UniqueID).delete()


@bot.command()
@commands.has_permissions(manage_messages=True)
async def deny(ctx, UniqueID):
    try:
        await Submissions.get(unique_id=UniqueID)
    except DoesNotExist:
        await ctx.send("The ID provided is not a valid one. Please provide a valid ID.")
        return

    await Submissions.filter(unique_id=UniqueID).delete()
    await ctx.send("Denied!")


##############################
#                            #
#           Tickets          #
#                            #
##############################


@bot.command()
@commands.has_permissions(manage_channels=True, manage_messages=True)
async def set_ticket(ctx, category_id):
    global configuration
    global x
    embed = discord.Embed(name="Create Ticket", description="React with :e_mail: to create a ticket", color=0xFF5733)
    channel = ctx.message.channel.id
    message = await ctx.send(embed=embed)
    await message.add_reaction("📧")
    configuration['TicketChannel'] = channel
    configuration['TicketMessageID'] = message.id
    configuration['CategoryID'] = int(category_id)
    y = open("config.json", "w")
    json.dump(configuration, y)
    y.close()
    x.close()
    x = open("config.json", "r")
    configuration = json.load(x)
    x.close()
    await ctx.message.delete()


@bot.command()
async def close_ticket(ctx):
    if configuration['LogChannelID']:
        log = bot.get_channel(id=configuration['LogChannelID'])
        transcript = await chat_exporter.export(ctx.channel)

        if transcript is None:
            return

        transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{ctx.channel.name}.html")

        await log.send(file=transcript_file)
    else:
        await ctx.send("Log channel is not setup. This ticket will not have a transcript. Please set a log channel if you would like transcripts")
    await asyncio.wait(3)
    await ctx.channel.delete()


##############################
#                            #
#      BACKUP & RESTORE      #
#                            #
##############################
@bot.command()
@commands.has_permissions(administrator=True)
async def backup(ctx):
    channels = ctx.guild.channels
    roles = ctx.guild.roles
    members = ctx.guild.members

    await BackupChannels().all().delete()
    await BackupMessages().all().delete()
    utils.clean_dir("attachment_backup")

    jsonVar = []
    for role in roles:
        jsonVar.append({"role": role.name,
                        "permissions": {permission[0]: permission[1] for permission in role.permissions},
                        "color": role.color.value, "position": role.position})
    for role in jsonVar:
        await BackupRoles(rolename=role['role'], permissisons=json.dumps(role['permissions']), color=role['color'], position=role['position']).save()
    for member in members:
        listRoles = []
        for role in member.roles:
            listRoles.append(role.name)
        await BackupUsers(user_id=member.id, roles=listRoles).save()

    n = 1
    for channel in channels:
        jsonVar1 = []
        for overwrite in channel.overwrites:
            if isinstance(overwrite, discord.member.Member):
                continue
            else:
                jsonVar1.append({"role": overwrite.name, "permissions": {
                    permission[0]: permission[1] for permission in overwrite.permissions}})
        chann_type = None
        if type(channel) == discord.TextChannel:
            chann_type = "text"
        elif type(channel) == discord.StageChannel:
            chann_type = "stage"
        elif type(channel) == discord.VoiceChannel:
            chann_type = "voice"
        else:
            continue

        if chann_type == "stage" or chann_type == "voice":
            await BackupChannels(name=channel.name, type=chann_type, category=channel.category.name, category_position=channel.category.position, channel_position=channel.position, roles=json.dumps(jsonVar1)).save()
            continue

        await BackupChannels(name=channel.name, type=chann_type, category=channel.category.name, category_position=channel.category.position, channel_position=channel.position, roles=json.dumps(jsonVar1)).save()
        data = await channel.history(limit=None).flatten()
        for message in data:
            if message.attachments:
                for attachment in message.attachments:
                    if os.path.exists(f"attachment_backup/{attachment.filename}"):
                        path = f"attachment_backup/{n}{attachment.filename}"
                        await attachment.save(f"attachment_backup/{n}{attachment.filename}")
                        n += 1
                    else:
                        path = f"attachment_backup/{attachment.filename}"
                        await attachment.save(f"attachment_backup/{attachment.filename}")
                    await BackupMessages(user_id=message.author.id, message=message.clean_content, channel=message.channel.name, date_time=message.created_at, attachment=path).save()
            elif message.embeds:
                for embed in message.embeds:
                    await BackupMessages(user_id=message.author.id, message=message.clean_content, channel=message.channel.name, date_time=message.created_at, embed=json.dumps(embed.to_dict())).save()
            else:
                await BackupMessages(user_id=message.author.id, message=message.clean_content, channel=message.channel.name, date_time=message.created_at).save()
    await ctx.send(f"Backup done <@{ctx.author.id}>.")


@bot.command()
@commands.has_permissions(administrator=True)
async def restore(ctx):
    channels = await BackupChannels().all().values()
    messages = await BackupMessages().all().values()
    roles = await BackupRoles().all().values()

    guild = ctx.guild

    roleposdict = {}

    for role in roles:
        permissions = json.loads(role['permissisons'])
        permissions = discord.Permissions(**permissions)
        roleobject = await guild.create_role(name=role['rolename'], permissions=permissions, colour=int(role['color']))
        roleposdict[roleobject if role['rolename'] != "@everyone" else guild.default_role] = role['position']

    await guild.edit_role_positions(roleposdict)

    for channel in channels:
        category = discord.utils.get(guild.categories, name=channel['category'])
        roledict = {}
        for role in json.loads(channel['roles']):
            roleobj = discord.utils.get(guild.roles, name=role['role'])
            permissions = role['permissions']
            if roleobj:
                roledict[roleobj] = discord.PermissionOverwrite(**permissions)
        if category:
            pass
        else:
            category = await guild.create_category_channel(name=channel['category'], position=channel['category_position'])
        if channel['type'] == "voice":
            await category.create_voice_channel(name=channel['name'], position=channel['channel_position'], overwrites=roledict)
        elif channel['type'] == "stage":
            await category.create_stage_channel(name=channel['name'], position=channel['channel_position'], overwrites=roledict)
        else:
            await category.create_text_channel(name=channel['name'], position=channel['channel_position'], overwrites=roledict)

    messages = sorted(messages, key=lambda x: datetime.datetime.strftime(x['date_time'], "%m-%d-%Y %H:%M:%S.%f"))
    for message in messages:
        channel = discord.utils.get(ctx.guild.channels, name=message['channel'])
        hooks = await channel.webhooks()
        user = bot.get_user(message['user_id'])
        if hooks:
            hook = hooks[0]
            try:
                await hook.send(content=message['message'], username=user.display_name if user else "invalid_user",
                                avatar_url=user.avatar_url if user else None, file=discord.File(message['attachment'], message['attachment']) if message['attachment'] else None, embed=discord.Embed.from_dict(json.loads(message['embed'])) if message['embed'] else None)
            except:
                continue
        else:
            hook = await channel.create_webhook(name="mywebhook")
            try:
                await hook.send(content=message['message'], username=user.display_name if user else "invalid_user",
                                avatar_url=user.avatar_url if user else None, file=discord.File(message['attachment'], message['attachment']) if message['attachment'] else None, embed=discord.Embed.from_dict(json.loads(message['embed'])) if message['embed'] else None)
            except:
                continue

    await ctx.send(f"Restore done <@{ctx.author.id}>.")


##############################
#                            #
#          REACTIONS         #
#                            #
##############################
@bot.command()
@commands.has_permissions(manage_channels=True, manage_messages=True)
async def add_reaction(ctx, channel_id: Optional[int]):
    channel_id_message = None
    if ctx.message.channel_mentions:
        for channel in ctx.message.channel_mentions:
            channel_id_message = channel.id
            break
    elif channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            pass
        else:
            await ctx.send("Invalid ID")
            return
        pass
    else:
        await ctx.send("No channel was mentioned and no ID was provided.")
        return

    await ctx.send("React with the emoji you want to add.")

    def check(reaction, user):
        return user == ctx.message.author

    data = await bot.wait_for("reaction_add", timeout=30, check=check)

    try:
        emoji = data[0].emoji.name
    except:
        emoji = str(data[0])
    try:
        reactionsobj = await ReactionChannels.get(channel_id=channel_id_message if channel_id_message else channel_id)
        reactions = await ReactionChannels.get(channel_id=channel_id_message if channel_id_message else channel_id).values()
        for reaction in reactions:
            newreactions = json.loads(reaction['reactions'])
        for stuff in newreactions:
            if stuff == emoji:
                await ctx.send("Reaction already present.")
                return
            else:
                continue
        newreactions.append(emoji)
        await ReactionChannels.filter(channel_id=channel_id_message if channel_id_message else channel_id).update(reactions=json.dumps(newreactions))
    except DoesNotExist:
        await ReactionChannels(channel_id=channel_id_message if channel_id_message else channel_id, reactions=json.dumps([emoji])).save()

    await ctx.send(f"Bot will now react with emoji {emoji} in channel <#{channel_id_message if channel_id_message else channel_id}>")


@bot.command()
@commands.has_permissions(manage_channels=True, manage_messages=True)
async def stop_reactions(ctx, channel_id: Optional[int]):
    channel_id_message = None
    if ctx.message.channel_mentions:
        for channel in ctx.message.channel_mentions:
            channel_id_message = channel.id
            break
    elif channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            pass
        else:
            await ctx.send("Invalid ID.")
            return
        pass
    else:
        await ctx.send("No channel was mentioned and no channel ID was provided.")
        return

    try:
        await ReactionChannels.get(channel_id=channel_id_message if channel_id_message else channel_id)
    except DoesNotExist:
        await ctx.send("Channel provided does not have auto react enabled.")
        return

    await ReactionChannels.filter(channel_id=channel_id_message if channel_id_message else channel_id).delete()
    await ctx.send("Auto react is now disabled for this channel.")

##############################
#                            #
#        VERIFICATION        #
#                            #
##############################


@bot.command()
@commands.has_permissions(manage_roles=True)
async def set_verified_role(ctx, role_id: Optional[int]):
    global configuration
    global x
    if ctx.message.role_mentions:
        for role in ctx.message.role_mentions:
            configuration['VerifiedRole'] = role.id
            y = open("config.json", "w")
            json.dump(configuration, y)
            y.close()
            x.close()
            x = open("config.json", "r")
            configuration = json.load(x)
            x.close()
            await ctx.send("Verified role set.")
            break
    elif role_id:
        if ctx.guild.get_role(role_id):
            configuration['VerifiedRole'] = role_id
            y = open("config.json", "w")
            json.dump(configuration, y)
            y.close()
            x.close()
            x = open("config.json", "r")
            configuration = json.load(x)
            x.close()
            await ctx.send("Verified role set.")
        else:
            await ctx.send("Invalid ID.")
            return
    else:
        await ctx.send("No role was mentioned and no ID was provided.")


@bot.command()
async def verify(ctx):
    if 'VerifiedRole' in configuration:
        role = ctx.guild.get_role(int(configuration['VerifiedRole']))
        captcha = discapty.Captcha("wheezy")
        captcha_image = discord.File(captcha.generate_captcha(), filename="captcha.png")
        try:
            await ctx.message.author.send("This captcha is Case Sensitive. You have 2 minutes and 3 tries to solve the captcha.", file=captcha_image)
            await ctx.send("I have sent a captcha to your DMs.")
        except:
            await ctx.send("Your DMs are closed. Please allow private messages and then use the command.")
            return

        def check(message):
            return message.channel.type == discord.ChannelType.private and message.author == ctx.message.author

        verified = False
        i = 3
        while not verified and i >= 1:
            try:
                message = await bot.wait_for("message", timeout=120, check=check)
            except:
                await ctx.message.author.send("Your 2 minutes are up. Please go and request a new captcha.")
                return

            if captcha.verify_code(message.content):
                await ctx.message.author.send("You are now verified.")
                await ctx.message.author.add_roles(role)
                break
            else:
                i -= 1
                if i == 0:
                    await ctx.message.author.send(f"Incorrect. You have run out of trials. Please return to server and request a new captcha.")
                else:
                    await ctx.message.author.send(f"Incorrect. Please try again. Trials remaining: {i}/3")

    else:
        await ctx.send("Please contact adminstration to setup verification.")


##############################
#                            #
#           LEVELING         #
#                            #
##############################
async def add_experience(users, user, message):
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
    if users:
        users = await Levels.filter(user_id=message.author.id).update(experience=users.experience + xp)
    else:
        await Levels(user_id=user.id, experience=xp, level=0).save()

    user = await Levels.get(user_id=message.author.id)
    await level_up(user, message)


async def level_up(users, message):
    guild = message.guild
    experience = users.experience
    lvl_start = users.level
    lvl_end = int(experience ** (1 / 3))

    async def send_message():
        await message.channel.send(f':tada: <@{users.user_id}> has reached level {lvl_end}. Congrats! :tada:')
        return

    if lvl_start < lvl_end:
        if "LevelLogChannel" in configuration:
            guild = message.guild
            channel = guild.get_channel(configuration["LevelLogChannel"])
            try:
                await channel.send(f':tada: <@{users.user_id}> has reached level {lvl_end}. Congrats! :tada:')
            except:
                await send_message()
                pass
        else:
            await send_message()
        try:
            role = await LevelRole.get(level=lvl_end)
            member = guild.get_member(users.user_id)
            roletoadd = guild.get_role(role.role_id)
            await member.add_roles(roletoadd)
        except DoesNotExist:
            pass
        await Levels.filter(user_id=message.author.id).update(level=lvl_end)


@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def level(ctx, member: discord.Member = None):
    if member == None:
        user = await Levels.get(user_id=ctx.message.author.id)
        userlvl = user.level
        userexp = user.experience
        await ctx.send(f'{ctx.author.mention} You are at level {userlvl}, with XP {userexp}')
    else:
        user = await Levels.get(user_id=member.id)
        userlvl = user.level
        userexp = user.experience
        await ctx.send(f'{member.mention} is at level {userlvl}, with XP {userexp}')


@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def leaderboard(ctx):
    data = await Levels.all().order_by('-level').values()
    stringThing = ''
    rank = 1
    for x in data:
        stringThing = stringThing + f"#{rank} <@{x['user_id']}> : Level {x['level']}\n"
        rank += 1
    embed = discord.Embed(title="Leaderboard", description=stringThing, color=0xFF5733)
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(manage_roles=True)
async def blacklist(ctx, role_id: Optional[int]):
    if ctx.message.role_mentions:
        for role in ctx.message.role_mentions:
            await RoleBlacklist(role_id=role.id).save()
            await ctx.send("Role blacklisted.")
    elif role_id:
        if ctx.guild.get_role(role_id):
            await RoleBlacklist(role_id=role_id).save()
            await ctx.send("Role blacklisted.")
        else:
            await ctx.send("Invalid role id")
    else:
        await ctx.send("No role was mentioned or no role_id was provided.")


@bot.command()
@commands.has_permissions(manage_roles=True)
async def unblacklist(ctx, role_id: Optional[int]):
    if role_id:
        if ctx.guild.get_role(role_id):    
            try:
                await RoleBlacklist.get(role_id=role_id)
                await RoleBlacklist.filter(role_id=role_id).delete()
                await ctx.send("Role unblacklisted.")
            except:
                await ctx.send("Provided role_id is not in the DB.")
                return
            await ctx.send("Role unblacklisted.")
        else:
            await ctx.send("Invalid ID.")
    elif ctx.message.role_mentions:
        for role in ctx.message.role_mentions:
            try:
                await RoleBlacklist.get(role_id=role.id)
                await RoleBlacklist.filter(role_id=role.id).delete()
                await ctx.send("Role unblacklisted.")
            except:
                await ctx.send("Provided role is not blacklisted.")
    else:
        await ctx.send("No role was mentioned or no role_id was provided.")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def set_level_channel(ctx, channel_id: Optional[int]):
    global configuration
    global x
    if ctx.message.channel_mentions:
        for channel in ctx.message.channel_mentions:
            configuration['LevelLogChannel'] = channel.id
            y = open("config.json", "w")
            json.dump(configuration, y)
            y.close()
            x.close()
            x = open("config.json", "r")
            configuration = json.load(x)
            x.close()
            await ctx.send("Channel set.")
            break
    elif channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            configuration['LevelLogChannel'] = channel_id
            y = open("config.json", "w")
            json.dump(configuration, y)
            y.close()
            x.close()
            x = open("config.json", "r")
            configuration = json.load(x)
            x.close()
            await ctx.send("Channel set.")
        else:
            await ctx.send("Invalid ID.")
    else:
        await ctx.send("No channel was mentioned and no ID was provided.")


@bot.command()
@commands.has_permissions(manage_roles=True)
async def add_level_role(ctx, level, role_id: Optional[int]):
    if level:
        if ctx.message.role_mentions:
            for role in ctx.message.role_mentions:
                await LevelRole(role_id=role.id, level=level).save()
                await ctx.send("Level role added.")
        elif role_id:
            if ctx.guild.get_role(role_id):
                await LevelRole(role_id=role_id, level=level).save()
                await ctx.send("Level role added.")
            else:
                await ctx.send("Invalid role id")
        else:
            await ctx.send("No role was mentioned or no role_id was provided.")
    else:
        await ctx.send("No level was provided.")


##############################
#                            #
#       ERROR HANDLING       #
#                            #
##############################
@approve.error
@deny.error
@generate.error
@validate.error
@add.error
@whois.error
@level.error
@backup.error
@restore.error
@add_level_role.error
@add_reaction.error
@set_level_channel.error
@blacklist.error
@unblacklist.error
@leaderboard.error
@verify.error
@set_verified_role.error
@close_ticket.error
@ban.error
@kick.error
@set_ticket.error
async def error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(error)
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(error)
        return
    else:
        await ctx.send(error)


##############################
#                            #
#            RUN             #
#                            #
##############################
bot.run(configuration['BotToken'])

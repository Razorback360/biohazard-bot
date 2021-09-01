#######################################################################
# PLEASE RUN "pip install -r requirements"                            #
# PLEASE EDIT CONFIG.JSON WITH THE CONFIGURATION THAT YOU LIKE        #
# GENERATE A BOT TOKEN AT https://discord.com/developers/applications #
# PLEASE ENABLE SERVER MEMBERS INTENT ON THE BOT YOU CREATE           #
#######################################################################

import discord
from discord import permissions
from discord import emoji
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

x = open("config.json", "r")
configuration = json.load(x)
x.close()


intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=tuple(configuration['Prefixes']), case_insensitive=True, intents=intents)
bot.remove_command("help")


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
    if int(created_atdays) < 7:
        await member.send("Your account is less than a week old. You have been kicked. Join back after a week.")
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
            print(channel_reactions)
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
    if lvl_start < lvl_end:
        if "LevelLogChannel" in configuration:
            guild = message.guild
            channel = guild.get_channel(configuration["LevelLogChannel"])
            await channel.send(f':tada: <@{users.user_id}> has reached level {lvl_end}. Congrats! :tada:')
        else:
            await message.channel.send(f':tada: <@{users.user_id}> has reached level {lvl_end}. Congrats! :tada:')
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
    embed = discord.Embed(title="Leaderboard", description=stringThing)
    await ctx.send(embed=embed)


@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def add(ctx, title, link, description):
    password_characters = string.digits
    UniqueID = ''.join(random.choice(password_characters) for _ in range(12))

    AwaitingApproval = discord.Embed(title=title, description=f"Submitter: <@{ctx.message.author.id}>", color=0x77c128)
    AwaitingApproval.add_field(name=link, value=description, inline=False)
    AwaitingApproval.add_field(name="Unique ID", value=int(UniqueID), inline=False)

    ApprovalChannel = bot.get_channel(configuration['ApproveChannelID'])
    await ApprovalChannel.send(embed=AwaitingApproval)
    await ctx.send("Thanks for your submission! The mods will check it out and approve or deny it.")

    if link:
        await Submissions(user_id=ctx.message.author.id, title=title, link=None, description=description, unique_id=UniqueID).save()
    else:
        await Submissions(user_id=ctx.message.author.id, title=title, link=link, description=description, unique_id=UniqueID).save()


@bot.command()
@commands.has_permissions(administrator=True)
async def approve(ctx, UniqueID, ChannelID):
    try:
        data = await Submissions.get(unique_id=UniqueID)
    except DoesNotExist:
        await ctx.send("The ID provided is not a valid one. Please provide a valid ID.")
        return

    channel = bot.get_channel(int(ChannelID))
    if data.link:
        ApprovedSub = discord.Embed(
            title=data.title,
            description=f"Thanks to <@{data.user_id}>!\n\n{data.description}", color=0x77c128)
        ApprovedSub.add_field(name="Link", value=data.link, inline=False)

        await channel.send(embed=ApprovedSub)
        await ctx.send("Approved!")
        await Submissions.filter(unique_id=UniqueID).delete()
        return
    else:
        ApprovedSub = discord.Embed(
            title=data.title,
            description=f"Thanks to <@{data.user_id}>!\n\n{data.description}", color=0x77c128)

        await channel.send(embed=ApprovedSub)
        await ctx.send("Approved!")
        await Submissions.filter(unique_id=UniqueID).delete()
        return


@bot.command()
@commands.has_permissions(administrator=True)
async def deny(ctx, UniqueID):
    try:
        await Submissions.get(unique_id=UniqueID)
    except DoesNotExist:
        await ctx.send("The ID provided is not a valid one. Please provide a valid ID.")
        return

    await Submissions.filter(unique_id=UniqueID).delete()
    await ctx.send("Denied!")


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


@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def whois(ctx):
    print("test")
    if ctx.message.mentions:
        print("test")
        for x in ctx.message.mentions:
            duration = datetime.datetime.now() - x.joined_at
            print("test")
            hours, remainder = divmod(int(duration .total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            days, hours = divmod(hours, 24)
            print("test")
            created_at = datetime.datetime.now() - x.created_at
            print("test")
            created_athours, created_atremainder = divmod(int(created_at .total_seconds()), 3600)
            created_atminutes, created_atseconds = divmod(created_atremainder, 60)
            created_atdays, created_athours = divmod(created_athours, 24)

            roles = str([y.mention for y in x.roles]).replace('[', '').replace(']', '').replace('\'', '')
            print("test")
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
            print("test")
            await ctx.send(embed=embed)
            print("test")
    else:
        print("test")
        user = ctx.message.author.id
        x = ctx.guild.get_member(user_id=user)
        duration = datetime.datetime.now() - x.joined_at
        print("test")

        hours, remainder = divmod(int(duration .total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        print("test")

        created_at = datetime.datetime.now() - x.created_at
        created_athours, created_atremainder = divmod(int(created_at .total_seconds()), 3600)
        created_atminutes, created_atseconds = divmod(created_atremainder, 60)
        created_atdays, created_athours = divmod(created_athours, 24)

        roles = str([y.mention for y in x.roles]).replace('[', '').replace(']', '').replace('\'', '')
        print("test")

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
        print("test")

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
async def afk(ctx, *, arg):
    await AFK(user_id=ctx.message.author.id, message=arg).save()
    await ctx.send("You are now AFK. Use unafk command to remove your AFK status.")


@bot.command()
async def unafk(ctx):
    try:
        await AFK.get(user_id=ctx.message.author.id)
    except DoesNotExist:
        await ctx.send("You weren't AFK.")
        return

    await AFK.filter(user_id=ctx.message.author.id).delete()
    await ctx.send("You are no longer AFK.")


@bot.command()
@commands.has_permissions(administrator=True)
async def set_channel(ctx, category_id):
    global configuration
    global x
    embed = discord.Embed(name="Create Ticket", description="React with :e_mail: to create a ticket")
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
@commands.has_permissions(administrator=True)
async def close_ticket(ctx):
    log = bot.get_channel(id=configuration['LogChannelID'])
    transcript = await chat_exporter.export(ctx.channel)

    if transcript is None:
        return

    transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{ctx.channel.name}.html")

    await log.send(file=transcript_file)
    await ctx.channel.delete()


@bot.command()
@commands.has_permissions(administrator=True)
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
@commands.has_permissions(administrator=True)
async def unblacklist(ctx, role_id: Optional[int]):
    if role_id:
        try:
            await RoleBlacklist.get(role_id=role_id)
            await RoleBlacklist.filter(role_id=role_id).delete()
            await ctx.send("Role unblacklisted.")
        except:
            await ctx.send("Provided role_id is inavlid or not in the DB.")
        await ctx.send("Role blacklisted.")
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
@commands.has_permissions(administrator=True)
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
        await ctx.send("No channel was mentioned and no ID was provided.")


@bot.command()
@commands.has_permissions(administrator=True)
async def addlevelrole(ctx, level, role_id: Optional[int]):
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


@bot.command()
@commands.has_permissions(administrator=True)
async def backup_messages_channels(ctx):
    channels = ctx.guild.channels
    await BackupChannels().all().delete()
    await BackupMessages().all().delete()
    utils.clean_dir("attachment_backup")
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
                    print("end of attachment")
            elif message.embeds:
                for embed in message.embeds:
                    await BackupMessages(user_id=message.author.id, message=message.clean_content, channel=message.channel.name, date_time=message.created_at, embed=json.dumps(embed.to_dict())).save()
            else:
                await BackupMessages(user_id=message.author.id, message=message.clean_content, channel=message.channel.name, date_time=message.created_at).save()
    await ctx.send(f"Backup done <@{ctx.author.id}>.")


@bot.command()
@commands.has_permissions(administrator=True)
async def backup_users(ctx):
    roles = ctx.guild.roles
    members = ctx.guild.members

    jsonVar = []
    for role in roles:
        jsonVar.append({"role": role.name, "permissions": {
                       permission[0]: permission[1] for permission in role.permissions}, "color": role.color.value, "position": role.position})
    print(jsonVar)
    for role in jsonVar:
        await BackupRoles(rolename=role['role'], permissisons=json.dumps(role['permissions']), color=role['color'], position=role['position']).save()
    print("here")
    for member in members:
        listRoles = []
        for role in member.roles:
            listRoles.append(role.name)
        await BackupUsers(user_id=member.id, roles=listRoles).save()
    print("now here")


@bot.command()
@commands.has_permissions(administrator=True)
async def startrestore(ctx):
    channels = await BackupChannels().all().values()
    messages = await BackupMessages().all().values()
    roles = await BackupRoles().all().values()

    guild = ctx.guild

    roleposdict = {}
    
    for role in roles:
        permissions = json.loads(role['permissisons'])
        print(permissions)
        permissions = discord.Permissions(**permissions)
        print(permissions)
        roleobject = await guild.create_role(name=role['rolename'], permissions=permissions, colour=int(role['color']))
        roleposdict[roleobject if role['rolename'] != "@everyone" else guild.default_role] = role['position']
    
    await guild.edit_role_positions(roleposdict)

    print(channels)
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
        if message['embed']:
            print(type(json.loads(message['embed'])))
        else:
            print(None)
        if message['message']:
            if hooks:
                hook = hooks[0]
                await hook.send(content=message['message'], username=user.display_name if user else "invalid_user",
                                avatar_url=user.avatar_url if user else None, file=discord.File(message['attachment'], message['attachment']) if message['attachment'] else None, embed=discord.Embed.from_dict(json.loads(message['embed'])) if message['embed'] else None)
            else:
                hook = await channel.create_webhook(name="mywebhook")
                await hook.send(content=message['message'], username=user.display_name if user else "invalid_user",
                                avatar_url=user.avatar_url if user else None, file=discord.File(message['attachment'], message['attachment']) if message['attachment'] else None, embed=discord.Embed.from_dict(json.loads(message['embed'])) if message['embed'] else None)
        elif message['attachment']:
            if hooks:
                hook = hooks[0]
                await hook.send(content=None, username=user.display_name if user else "invalid_user",
                                avatar_url=user.avatar_url if user else None, file=discord.File(message['attachment'], message['attachment']) if message['attachment'] else None, embed=discord.Embed.from_dict(json.loads(message['embed'])) if message['embed'] else None)
            else:
                hook = await channel.create_webhook(name="mywebhook")
                await hook.send(content=None, username=user.display_name if user else "invalid_user",
                                avatar_url=user.avatar_url if user else None, file=discord.File(message['attachment'], message['attachment']) if message['attachment'] else None, embed=discord.Embed.from_dict(json.loads(message['embed'])) if message['embed'] else None)
        elif message['embed']:
            if hooks:
                hook = hooks[0]
                await hook.send(content=None, username=user.display_name if user else "invalid_user",
                                avatar_url=user.avatar_url if user else None, file=discord.File(message['attachment'], message['attachment']) if message['attachment'] else None, embed=discord.Embed.from_dict(json.loads(message['embed'])) if message['embed'] else None)
            else:
                hook = await channel.create_webhook(name="mywebhook")
                await hook.send(content=None, username=user.display_name if user else "invalid_user",
                                avatar_url=user.avatar_url if user else None, file=discord.File(message['attachment'], message['attachment']) if message['attachment'] else None, embed=discord.Embed.from_dict(json.loads(message['embed'])) if message['embed'] else None)

    await ctx.send(f"Backup done <@{ctx.author.id}>.")

@bot.command()
async def verified_role(ctx, role_id: Optional[int]):
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
        await ctx.send("No role was mentioned and no ID was provided.")

@bot.command()
async def verify(ctx):
    if 'VerifiedRole' in configuration:
        role = ctx.guild.get_role(int(configuration['VerifiedRole']))
        captcha = discapty.Captcha("wheezy")
        captcha_image = discord.File(captcha.generate_captcha(), filename="captcha.png")
        await ctx.message.author.send("This captcha is Case Sensitive. You have 30 seconds to solve the captcha. IF incorrect go back to server and request a new one.",file=captcha_image)
        await ctx.send("I have sent a captcha to your DMs.")

        def check(message):
            return message.channel.type == discord.ChannelType.private and message.author == ctx.message.author

        message = await bot.wait_for("message", timeout = 30, check=check)

        print(message.content)
        print(type(message))
        print(captcha.verify_code(message.content))

        if captcha.verify_code(message.content):
            await ctx.message.author.send("You are now verified.")
            await ctx.message.author.add_roles(role)
        else:
            await ctx.message.author.send("Incorrect. Please return to the server and initiate the verification process again.")
    else:
        await ctx.send("Please contact adminstration to setup verification.")

@bot.command()
async def add_reaction(ctx, channel_id: Optional[int]):
    channel_id_message= None
    if ctx.message.channel_mentions:
        for channel in ctx.message.channel_mentions:
            channel_id_message = channel.id
            break
    elif channel_id:
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
        print(emoji)
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
        print(newreactions)
        await ReactionChannels.filter(channel_id=channel_id_message if channel_id_message else channel_id).update(reactions=json.dumps(newreactions))
    except DoesNotExist:
        await ReactionChannels(channel_id=channel_id_message if channel_id_message else channel_id, reactions=json.dumps([emoji])).save()
        
    await ctx.send(f"Bot will now react with emoji {emoji} in channel <#{channel_id_message if channel_id_message else channel_id}>")

@bot.command()
async def help(ctx):
    helpEmbed = discord.Embed(title="Help!", description="These are the available commands!", color=0x77c128)
    helpEmbed.add_field(
        name=f'{configuration["Prefixes"][0]}add "title" "link" "description"',
        value="Adds a submission to the submission queue. Please provide all the command parameters as they are not optional and use double quotation marks for each parameter.",
        inline=False)
    helpEmbed.add_field(
        name=f'{configuration["Prefixes"][0]}approve [unique id] [channel id]',
        value="ADMIN COMMAND ONLY. Approves a submission with id [unique id] and sends it to channel with id [channel id]. Don't include the square brackets they are not part of the command.",
        inline=False)
    helpEmbed.add_field(
        name=f'{configuration["Prefixes"][0]}deny [unique id]',
        value="ADMIN COMMAND ONLY. Denies a submission with id [unique id]. Don't include the square brackets they are not part of the command.",
        inline=False)

    await ctx.send(embed=helpEmbed)


@approve.error
@deny.error
@generate.error
@validate.error
@add.error
@whois.error
@level.error
async def permissions_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(error)
        return
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(error)
        return


bot.run(configuration['BotToken'])

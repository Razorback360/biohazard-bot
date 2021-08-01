#######################################################################
# PLEASE RUN "pip install -r requirements"                            #
# PLEASE EDIT CONFIG.JSON WITH THE CONFIGURATION THAT YOU LIKE        #
# GENERATE A BOT TOKEN AT https://discord.com/developers/applications #
#######################################################################

import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions
import json
import string
import random

x = open("config.json", "r")
configuration = json.load(x)

bot = commands.Bot(command_prefix=tuple(configuration['Prefixes']), case_insensitive=True)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{configuration['Prefixes'][0]}help"))
    print("Im online and ready!")


@bot.command()
async def add(ctx, title, link, description):
    password_characters = string.digits
    UniqueID = ''.join(random.choice(password_characters) for _ in range(12))

    AwaitingApproval = discord.Embed(title=title, description=None, color=0x77c128)
    AwaitingApproval.add_field(name=link, value=description, inline=False)
    AwaitingApproval.add_field(name="Unique ID", value=int(UniqueID), inline=False)

    ApprovalChannel = bot.get_channel(configuration['ApproveChannelID'])
    await ApprovalChannel.send(embed=AwaitingApproval)
    await ctx.send("Thanks for your submission! The mods will check it out and approve or deny it.")

    NewSub = {"id": int(UniqueID), "title": title, "link": link, "description": description}

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
            ApprovedSub = discord.Embed(title=submission['title'], description=None, color=0x77c128)
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

@approve.error
@deny.error
async def permissions_error(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.send("This is an adminstrator only command. Please refrain from using it.")


bot.run(configuration['BotToken'])
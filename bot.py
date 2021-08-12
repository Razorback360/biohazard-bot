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

from discord.ext.commands.core import cooldown
import utils
import luhn

x = open("config.json", "r")
configuration = json.load(x)

bot = commands.Bot(command_prefix=tuple(configuration['Prefixes']), case_insensitive=True)
bot.remove_command("help")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{configuration['Prefixes'][0]}help"))
    print("Im online and ready!")


@bot.command()
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
async def permissions_error(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.send("This is an adminstrator only command. Please refrain from using it.")
        return
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(error)
        return


bot.run(configuration['BotToken'])
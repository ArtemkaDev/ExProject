from discord_components import DiscordComponents, Button, ButtonStyle
from discord.ext import commands
import discord
import json
import os

with open("config.json") as f:
    data_json = json.load(f)

client = commands.Bot(command_prefix = data_json['PREFIX'])
client.remove_command('help')


async def input_info(response):
    await response.author.send("привет")

async def search_info(response):
    pass


#ds bot:
@client.event
async def on_ready():
    print ('We have logged in as {0.user}'.format(client))
    DiscordComponents(client)
    await client.change_presence(status = discord.Status.online, activity = discord.Game(".хелп Cервер разработчика discord.gg/N4t46H8Uue"))


@client.command()
async def reloadall(ctx):
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            if filename == "config.py":
                pass
            else:
                client.unload_extension(f"cogs.{filename[:-3]}")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            if filename == "config.py":
                pass
            else:
                client.load_extension(f"cogs.{filename[:-3]}")


@client.command()
async def load(ctx, extension):
    if ctx.author.id == 661271099404976174:
        client.load_extension(f"cogs.{extension}")
        print("load")


@client.command()
async def unload(ctx, extension):
    if ctx.author.id == 661271099404976174:
        client.unload_extension(f"cogs.{extension}")
        print("unload")


@client.command()
async def reload(ctx, extension):
    if ctx.author.id == 661271099404976174:
        client.unload_extension(f"cogs.{extension}")
        client.load_extension(f"cogs.{extension}")
        print("reload")


async def registr():
    await client.wait_until_ready()
    artemka = await client.fetch_user(user_id=661271099404976174)
    channel_verify = client.get_channel(920775955105054782)
    await channel_verify.purge(limit=100)
    await channel_verify.send(
        embed=discord.Embed(title="Зарегистрироваться на сервере"),
        components=[
            Button(style=ButtonStyle.green, label="Найти", emoji="🔍"),
            Button(style=ButtonStyle.blue, label="Ввести")
        ]
    )
    while True:
        response = await client.wait_for("button_click")
        if response.channel == channel_verify:
            if response.component.label == "Найти":
                await search_info(response)
            elif response.component.label == "Ввести":
                await input_info(response)
            else:
                await artemka.send(f"{response.author} как-то обошол модуль вопросы")

client.loop.create_task(registr())

for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        client.load_extension(f"cogs.{filename[:-3]}")


'''while True:
    lmessage = await client.wait_for('message')
    login = lmessage.content
    if lmessage.author == client.user:
        continue
    else:
        break'''


client.run(data_json['TOKEN'])


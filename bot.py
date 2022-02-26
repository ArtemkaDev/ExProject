from discord_components import DiscordComponents, Button, ButtonStyle
from pymysql import OperationalError
from discord.ext import commands
from config import settings
import pymysql
import discord
import config
import time
import os

client = commands.Bot(command_prefix = settings['PREFIX'])
client.remove_command('help')

connection = pymysql.connect(host='185.12.95.170', user='admin_Gop', password='7aMzOwd3Cl2BM', database='admin_base', cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()

def my_cursor(sql):
    while True:
        try:
            cursor.execute(sql)
            connection.commit()
            break
        except OperationalError:
            connection.ping(True)

def my_cursor_check(sql):
    while True:
        try:
            cursor.execute(sql)
            return cursor.fetchone()
            break
        except OperationalError:
            connection.ping(True)

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
    channel_verify = client.get_channel(862786498923593748)
    await channel_verify.purge(limit=100)
    await channel_verify.send(
        embed=discord.Embed(title="Зарегистрироваться на сервере"),
        components=[
            Button(style=ButtonStyle.green, label="Принять", emoji="✔"),
            Button(style=ButtonStyle.blue, label="Зачем?")
        ]
    )
    while True:
        response = await client.wait_for("button_click")
        if response.channel == channel_verify:
            if response.component.label == "Принять":
                if my_cursor_check(sql = f"SELECT id FROM users WHERE id = {response.author.id}") is None:
                    await response.author.send('Напишите ник который хотите в майкрафте')
                    while True:
                        lmessage = await client.wait_for('message')
                        login = lmessage.content
                        if lmessage.author == client.user:
                            continue
                        else:
                            break
                    time.sleep(1)
                    await response.author.send('Напишите пароль')
                    while True:
                        pmessage = await client.wait_for('message')
                        password = pmessage.content
                        if pmessage.author == client.user:
                            continue
                        else:
                            break
                    time.sleep(1)
                    await response.author.send('Id того хто пригласил (есть в .хелп информация) если нету напишите None')
                    while True:
                        rmessage = await client.wait_for('message')
                        referal = rmessage.content
                        if rmessage.author == client.user:
                            continue
                        else:
                            break
                    time.sleep(1)
                    if referal == 'None':
                        my_cursor(sql = f"INSERT INTO users (name, id, login, password, cash, lvl, xp, rub, welc) VALUES ('{response.author}','{response.author.id}','{login}','{password}',0,1,0,0,0)")
                        await response.author.send('Вы зарегистрировались! Теперь вам доступно общение в чате. Напишите одному из админов что вы зарегистрировались и он вам даст доступ в чат')
                        await response.author.send('Лаунчер для windows: http://185.12.95.170:9274/RpProjectRed.exe')
                        await response.author.send('Лаунчер для mac os или linux: http://185.12.95.170:9274/RpProjectRed.jar')
                        await artemka.send(f'Пользователь {response.author} зарегестрировался.')
                    else:
                        if my_cursor_check(sql =  f"SELECT id FROM users WHERE id = {response.author.id}") is None:
                            while True:
                                await response.author.send('Ошибка пользователь ненайден повторите попыткую Если хотите отменить реферальную систему напишите None')
                                while True:
                                    rmessage = await client.wait_for('message')
                                    referal = rmessage.content
                                    if lmessage.author == client.user:
                                        continue
                                    else:
                                        break
                                if referal == 'None':
                                    my_cursor(sql = f"INSERT INTO users (name, id, login, password, cash, lvl, xp, rub, welc) VALUES ('{response.author}','{response.author.id}','{login}','{password}',0,1,0,0,0)")
                                    await response.author.send('Вы зарегистрировались! Теперь вам доступно общение в чате. Напишите одному из админов что вы зарегистрировались и он вам даст доступ в чат')
                                    await response.author.send('Лаунчер для windows: http://185.12.95.170:9274/RpProjectRed.exe')
                                    await response.author.send('Лаунчер для mac os или linux: http://185.12.95.170:9274/RpProjectRed.jar')
                                    await artemka.send(f'Пользователь {response.author} зарегестрировался.')
                                    break
                                elif my_cursor_check(sql =  f"SELECT id FROM users WHERE id = {referal}") is None:
                                    continue
                                else:
                                    my_cursor(sql = f"INSERT INTO users (name, id, login, password, cash, lvl, xp, rub, welc) VALUES ('{response.author}','{response.author.id}','{login}','{password}',10,1,0,0,0)")
                                    my_cursor(sql = f"UPDATE users SET welc = welc + 1 WHERE id = {referal}")
                                    await response.author.send('Вы зарегистрировались! Теперь вам доступно общение в чате.')
                                    await response.author.send('Лаунчер для windows: http://185.12.95.170:9274/RpProjectRed.exe')
                                    await response.author.send('Лаунчер для mac os или linux: http://185.12.95.170:9274/RpProjectRed.jar')
                                    await artemka.send(f'Пользователь {response.author} зарегестрировался.')
                                    break
                        else:
                            my_cursor(sql = f"INSERT INTO users (name, id, login, password, cash, lvl, xp, rub, welc) VALUES ('{response.author}','{response.author.id}','{login}','{password}',10,1,0,0,0)")
                            my_cursor(sql = f"UPDATE users SET welc = welc + 1 WHERE id = {referal}")
                            await response.author.send('Вы зарегистрировались! Теперь вам доступно общение в чате. Напишите одному из админов что вы зарегистрировались и он вам даст доступ в чат')
                            await response.author.send('Лаунчер для windows: http://185.12.95.170:9274/RpProjectRed.exe')
                            await response.author.send('Лаунчер для mac os или linux: http://185.12.95.170:9274/RpProjectRed.jar')
                            await artemka.send(f'Пользователь {response.author} зарегестрировался.')
                        # info about bd:
                        # name, id, login, password, cash, lvl, xp, rub, welc(referal), after don't touch
                else:
                    await response.author.send('Вы уже зарегестированы')
            else:
                await response.author.send(config.WHY)

client.loop.create_task(registr())

for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        client.load_extension(f"cogs.{filename[:-3]}")

client.run(settings['TOKEN'])
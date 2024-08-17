import config
import disnake
import datetime
from disnake.ext import commands
from decorator import guild
import tracemalloc
import sqlite3
from cogs.solved import SolvedButton

intents = disnake.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
tracemalloc.start()

class AmnestyButton(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @disnake.ui.button(label="Амнистировать блокировку", style=disnake.ButtonStyle.grey, custom_id="amnesty", disabled=False)
    async def amnesty(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            bans = cursor.execute(""" SELECT moder, reason, proofs, date FROM bans WHERE id = ? """, [inter.author.id]).fetchone()
            amnesty = cursor.execute(""" DELETE FROM sqlite_sequence WHERE name='amnesty'; """)
            db.commit()
        
        if bans:
            moder, reason, proofs, date = bans[0], bans[1], bans[2], bans[3]
            moder = inter.guild.get_member(moder)
        else:
            await inter.send("У вас нет бана!", ephemeral=True)
            return

        embed = disnake.Embed(
            title=f"ABF-{moder.display_name.upper()}", 
            description="Вы создали ветку для амнистирования вашей блокировки. В этой ветке вы можете обжаловать её, если получиться 😉",
            color=config.Colors.TRANSPARENT
        )
        embed.add_field(name="Забаненный:", value=f"{inter.author.mention} (@{inter.author.display_name})")
        embed.add_field(name="Дата и время бана:", value='<t:'+date+':f>' if date else 'неизвестно')
        embed.add_field(name="Инициатор бана:", value=f"{moder.mention} (@{moder.display_name})", inline=False)
        embed.add_field(name="Причина бана:", value=reason if reason else 'неизвестно', inline=False)
        if proofs:
            embed.set_image(url=proofs)
        thread = await inter.channel.create_thread(name=f"af-{moder.display_name.lower()}", type=disnake.ChannelType.private_thread, invitable=False, slowmode_delay=30)
        await thread.add_user(inter.author)
        await thread.add_user(moder)        
        message = await thread.send(embed=embed, view=SolvedButton())
        await message.pin()
        await inter.send(f"Ветка для обжалования бана создана {thread.jump_url} (#{thread.name})!", ephemeral=True)

class Bans(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name=disnake.Localized("amnesty", key="AMNESTY_NAME"), description=disnake.Localized("The ban amnesty panel.", key="AMNESTY_DESCRIPTION"), default_member_permissions=disnake.Permissions(ban_members=True), guild_ids=[config.Guilds.MAIN])
    async def amnesty(self, inter):
        embed = disnake.Embed(
            title="АМНИСТИЯ", 
            description="Если вы видите этот канал и это сообщение, значит у вас есть действующая блокировка в этом дискорд сервере. Чтобы обжаловать бан, нажмите на кнопку ниже, для создания ветки.\n\nПринимаются различные видео, фото, которые могут повлиять на снятие блокировки в этом дискорд сервере. Видео загружайте на ютуб, фото можно напрямую в дискорд.",
            color=config.Colors.TRANSPARENT
        )
        embed.set_image(file=disnake.File("./image/amnesty.png", filename="amnesty.png"))
        await inter.send(embed=embed, view=AmnestyButton())

    @commands.slash_command(name=disnake.Localized("ban", key="BAN_NAME"), description=disnake.Localized("Issue a ban to the user.", key="BAN_DESCRIPTION"), default_member_permissions=disnake.Permissions(ban_members=True), guild_ids=[config.Guilds.MAIN])
    async def ban_slash(self, inter: disnake.GuildCommandInteraction, 
                        member: disnake.Member = commands.Param(name=disnake.Localized("member", key="BAN_MEMBER_NAME"), description=disnake.Localized("The user who needs to be banned.", key="BAN_MEMBER_DESCRIPTION")),
                        reason: str = commands.Param(name=disnake.Localized("reason", key="BAN_REASON_NAME")),
                        image: disnake.Attachment = commands.Param(name=disnake.Localized("proofs", key="BAN_IMAGE_NAME"), description=disnake.Localized("Evidence of violation of the rules by the user.", key="BAN_IMAGE_DESCRIPTION"))
    ):
        await inter.response.defer(ephemeral=True)
        await Banned(member, reason, image, True).ban(inter)



    @commands.slash_command(name=disnake.Localized("unban", key="UNBAN_NAME"), description=disnake.Localized("Remove the user's ban.", key="UNBAN_DESCRIPTION"), default_member_permissions=disnake.Permissions(ban_members=True), guild_ids=[config.Guilds.MAIN])
    async def unban_slash(self, inter: disnake.GuildCommandInteraction,
                          member: disnake.Member = commands.Param(name=disnake.Localized("member", key="UNBAN_MEMBER_NAME"), description=disnake.Localized("The user who needs to be banned.", key="UNBAN_MEMBER_DESCRIPTION"))
    ):
        await inter.response.defer(ephemeral=True)
        await UnBanned(member).unban(inter)



class UnBanned:
    def __init__(self, member=None):
        self.member = member

    async def unban(self, inter: disnake.ApplicationCommandInteraction):
        role_ban = inter.guild.get_role(config.Roles.BAN)
        if role_ban not in self.member.roles:
            await inter.send(f"У пользователя {self.member.mention} не имеется бана!", ephemeral=True)
            return False
        try:
            await self.member.remove_roles(role_ban)
        except:
            await inter.send(f"У пользователя {self.member.mention} роль выше вашей!", ephemeral=True)
            return False
        
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" DELETE FROM bans WHERE id = ? """, [self.member.id])
            db.commit()

        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"Пользователю {self.member.mention} (@{self.member.display_name}) снят бан модератором {inter.author.mention} (@{inter.author.display_name}).", color=config.Colors.TRANSPARENT))
        channel_warn = inter.guild.get_channel(config.Channels.WARNINGS)
        await channel_warn.send(f"{self.member.mention} (@{self.member.display_name}), у вас амнистрирован бан модератором {inter.author.mention} (@{inter.author.display_name}).")
        await inter.send(f"Пользователю {self.member.mention} (@{self.member.display_name}) снят бан!", ephemeral=True)

class Banned:
    def __init__(self, member=None, reason=None, image=None, delete=True):
        self.member = member
        self.reason = reason
        self.image = image
        self.delete = delete

    async def ban(self, inter: disnake.ApplicationCommandInteraction):
        role_ban = inter.guild.get_role(config.Roles.BAN)
        if role_ban in self.member.roles:
            await inter.send(f"У пользователя {self.member.mention} уже имеется бан!", ephemeral=True)
            return False
        if self.image != None:
            if not self.image.content_type.startswith('image/'):
                await inter.send(f"Прикрепленный файл не является изображением!", ephemeral=True)
                return False
        try:
            for roles in self.member.roles:
                if roles.is_assignable():
                    await self.member.remove_roles(roles)
            await self.member.add_roles(role_ban)
        except:
            await inter.send(f"У пользователя {self.member.mention} роль выше вашей!", ephemeral=True)
            return False
        three_days_ago = datetime.datetime.now()-datetime.timedelta(days=3)
        deleted = 0
        if self.delete:
            for channel in inter.guild.text_channels:
                async for message in channel.history(after=three_days_ago):
                    if message.author == self.member:
                        await message.delete()
                        deleted += 1
        
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" INSERT INTO bans (id, moder, reason, proofs) VALUES (?, ?, ?, ?) """, [self.member.id, inter.author.id, self.reason, self.image.url])
            cursor.execute(""" INSERT INTO moders (id, bans) VALUES (?, 1) ON CONFLICT(id) DO UPDATE SET bans = COALESCE(bans, 0) + 1 """, [inter.author.id])
            db.commit()

        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"Пользователю {self.member.mention} (@{self.member.display_name}) выдан бан модератором {inter.author.mention} (@{inter.author.display_name}), по причине: {self.reason.lower()}.", color=config.Colors.TRANSPARENT))
        channel_warn = inter.guild.get_channel(config.Channels.WARNINGS)
        await channel_warn.send(f"{self.member.mention} (@{self.member.display_name}), вам выдан бан модератором {inter.author.mention} (@{inter.author.display_name}), по причине: {self.reason.lower()}.")
        await inter.send(f"Пользователю {self.member.mention} (@{self.member.display_name}) выдан бан{' и удалено последних сообщений: '+str(deleted) if self.delete else ''}!", ephemeral=True)

def setup(bot):
    bot.add_cog(Bans(bot))

import config
import disnake
from disnake.ext import commands

class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    intents = disnake.Intents.default()
    intents.message_content = True

    @commands.slash_command(
        name=disnake.Localized("cleaning", key="CLEAR_NAME"), 
        description=disnake.Localized("Cleaning chat messages.", key="CLEAR_DESCRIPTION"), 
        default_member_permissions=disnake.Permissions(manage_guild=True), 
        guild_ids=[config.Guilds.MAIN]
    )
    async def clear(
        self,
        inter, 
        amount: int = commands.Param(
            name=disnake.Localized("amount", key="CLEAR_AMOUNT_NAME"),
            description=disnake.Localized("The number of messages to delete.", key="CLEAR_AMOUNT_DESCRIPTION")
        )
    ):
        # if not amount in range(1, 50):
        #     await inter.response.send_message(f"Значение количества сообщений для удаления не в диапазоне от 1 до 50!", ephemeral=True)
        #     return
        
        deleted_messages = await inter.channel.purge(limit=amount)
        embed = disnake.Embed(description=f"Модератор {inter.author.mention} (@{inter.author.display_name}) удалил сообщений: ` {len(deleted_messages)} `, в канале {inter.channel.mention} (#{inter.channel.name}). Удаленные сообщения:\n", color=config.Colors.TRANSPARENT)
        for message in deleted_messages:
            escaped_content = message.content.replace('`', '\\`')
            embed.description += f"```- {message.author.mention} (@{message.author.display_name}): {escaped_content}```"
        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        log_message = await channel_logs.send(embed=embed)
        
        await inter.send(f"Удалено [сообщений]({log_message.jump_url}): {len(deleted_messages)}!", ephemeral=True)

def setup(bot):
    bot.add_cog(Clear(bot))

import config
import disnake
from disnake.ext import commands
from decorator import guild_m
import asyncio
import datetime
import sqlite3
from cogs.solved import SolvedButton
from cogs.joins import JoinsButton
from cogs.bans import AmnestyButton



intents = disnake.Intents.default()
intents.guilds = True
intents.message_content = True



class Events(commands.Cog):
    def __init__(self, bot=commands.Bot):
        self.bot = bot
  
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(SolvedButton())
        self.bot.add_view(AmnestyButton())
        while True:
            await self.bot.change_presence(activity=disnake.Activity(type=disnake.ActivityType.watching, name=f"за {len(self.bot.guilds)} серверами!"), status=disnake.Status.idle)
            await asyncio.sleep(15)
            users = set()
            for guild in self.bot.guilds:
                for member in guild.members:
                    users.add(member.id)
            await self.bot.change_presence(activity=disnake.Activity(type=disnake.ActivityType.watching, name=f"за {len(users)} игроками!"), status=disnake.Status.idle)
            await asyncio.sleep(15)


        
    # @commands.Cog.listener()
    # async def on_slash_command_error(self, inter: disnake.ApplicationCommandInteraction, error: commands.CommandError):
    #     print(error)
    #     if isinstance(error, commands.MissingRequiredArgument):
    #         await inter.send(f"Ошибка: не хватает аргумента `{error.param.name}`.", ephemeral=True)
    #     elif isinstance(error, commands.CommandNotFound):
    #         await inter.send("Ошибка: команда не найдена.", ephemeral=True)
    #     elif isinstance(error, commands.CommandOnCooldown):
    #         await inter.send(f"Команда на перезарядке. Попробуйте снова через {round(error.retry_after, 2)} секунд.", ephemeral=True)
    #     else:
    #         await inter.send("Произошла неизвестная ошибка. Сообщите в баг-репорт на официальном сервере Провинции с упоминанием главного модератора!", ephemeral=True)
            
    #     channel_logs = self.bot.get_channel(config.Channels.ERRORS)
    #     if channel_logs:
    #         await channel_logs.send(f"<@527827158605758484>, ошибка команды `/{inter.data.name}` на сервере `{inter.guild.name}` пользователем {inter.author.mention}:```{error}```")



    @commands.Cog.listener()
    @guild_m
    async def on_message(self, message):
        if message.guild.id != config.Guilds.MAIN:
            return
        for id in config.Channels.NEWS:
            if message.channel.id == id:
                date = message.created_at+datetime.timedelta(hours=3)
                time_message = datetime.datetime.time(date).strftime("%H:%M")
                date_message = datetime.datetime.date(date).strftime("%d.%m.%Y")
                await message.create_thread(name=f"Обсуждение новости от {date_message} ({time_message})", slowmode_delay=30)
        for id in config.Channels.NEWS_PUBLISH:
            if message.channel.id == id:
                await message.publish()
        


    @commands.Cog.listener("on_thread_create")
    async def thread_create_detect(self, forum_create: disnake.Thread):
        for forum in config.Channels.FORUM:
            if forum_create.parent.id != forum["id"]:
                return
            def check(message):
                return message.thread == forum_create and message.author == forum_create.owner
            
            try:
                await self.bot.wait_for("message", check=check, timeout=300)
            except asyncio.TimeoutError:
                return 
            embed = disnake.Embed(
                title=forum_create.parent.name.upper(),
                description=forum["label"],
                color=config.Colors.TRANSPARENT
            )
            bot_message = await forum_create.send(embed=embed, view=SolvedButton())
            await bot_message.pin()
        


    @commands.Cog.listener("on_member_join")
    async def member_join_detect(self, member: disnake.Member):
    # @commands.slash_command(name="t", guild_id=config.Guilds.MAIN)
    # async def member_join_detect(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member.guild.id != config.Guilds.MAIN:
            return
        
        channel_tech = member.guild.get_channel(config.Channels.VERIFY_TECH)
        # channel_tech = inter

        user = await self.bot.fetch_user(member.id)
        
        created_time_f = disnake.utils.format_dt(user.created_at, style="f")
        created_time_R = disnake.utils.format_dt(user.created_at, style="R")
        
        embed = disnake.Embed(
            title="",
            description=f"**Участник:** {member.mention}\n"
                        f"**Имя пользователя:** {member.name} ({member.display_name})\n"
                        f"**Статус:** {next((activity for activity in member.activities if isinstance(activity, disnake.CustomActivity)), 'отсутствует')}\n"
                        f"**Зарегистрирован:** {created_time_f} {created_time_R}\n",
            color=config.Colors.TRANSPARENT
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        if user.banner:
            embed.set_image(url=user.banner.url)
        await channel_tech.send(embed=embed, view=JoinsButton(member, user))



    @commands.Cog.listener("on_guild_join")
    async def guild_join_detect(self, guild: disnake.Guild):
        guild_main = self.bot.get_guild(config.Guilds.MAIN)
        channel_moder = guild_main.get_channel(config.Channels.MODERS)
        if not channel_moder:
            print("Не удалось найти канал на сервере поддержки.")
            return
        webhook = await channel_moder.create_webhook(
            name=guild.name,
            avatar=await guild.icon.read() if guild.icon else None,
            reason=f"Бот добавлен на сервер: {guild.name}\n"
        )
        embed = disnake.Embed(
            title="",
            description=f"**Бот был добавлен на сервер:** {guild.name}\n**Количество участников:** {guild.member_count}",
            color=config.Colors.TRANSPARENT
        )
        # embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        await webhook.send(
            embed=embed,
            username=guild.name,
            avatar_url=guild.icon.url if guild.icon else None
        )
        await webhook.delete()



    @commands.Cog.listener("on_guild_remove")
    async def guild_remove_detect(self, guild: disnake.Guild):
        guild_main = self.bot.get_guild(config.Guilds.MAIN)
        channel_moder = guild_main.get_channel(config.Channels.MODERS)
        if not channel_moder:
            print("Не удалось найти канал на сервере поддержки.")
            return
        webhook = await channel_moder.create_webhook(
            name=guild.name,
            avatar=await guild.icon.read() if guild.icon else None,
            reason=f"Бот был удален с сервера: {guild.name}\n"
        )
        embed = disnake.Embed(
            title="",
            description=f"**Бот был удален с сервера:** {guild.name}",
            color=config.Colors.TRANSPARENT
        )
        # embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        await webhook.send(
            embed=embed,
            username=guild.name,
            avatar_url=guild.icon.url if guild.icon else None
        )
        await webhook.delete()
      


def setup(bot):
    bot.add_cog(Events(bot))

import config
import disnake
import sqlite3
import asyncio
import datetime
from disnake.ext import commands
from decorator import guild_m
from cogs.bans import Banned



class Joins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    pass



class JoinsButton(disnake.ui.View):
    def __init__(self, member: disnake.Member, user: disnake.User): 
        super().__init__(timeout=None)
        self.moder_id = None
        self.member = member 

        if member.activity:
            status_button = disnake.ui.Button(label="Статус", style=disnake.ButtonStyle.grey, custom_id="status", row=1)
            status_button.callback = self.status
            self.add_item(status_button)
        if member.avatar:
            avatar_button = disnake.ui.Button(label="Аватарка", style=disnake.ButtonStyle.grey, custom_id="avatar", row=1)
            avatar_button.callback = self.avatar
            self.add_item(avatar_button)
        if user.banner:
            banner_button = disnake.ui.Button(label="Баннер", style=disnake.ButtonStyle.grey, custom_id="banner", row=1)
            banner_button.callback = self.banner
            self.add_item(banner_button)

    global moder_id
    moder_id = None
        
    @disnake.ui.button(label="Обработать", style=disnake.ButtonStyle.blurple, custom_id="processing", row=0)
    async def processing(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" 
                INSERT INTO moders (id, joins) 
                VALUES (?, 1) 
                ON CONFLICT(id) 
                DO UPDATE SET joins = COALESCE(joins, 0) + 1 
            """, [inter.author.id])
            db.commit()

        components = [
            disnake.ui.Button(label="Обработано", style=disnake.ButtonStyle.grey, custom_id="success", disabled=True),
            disnake.ui.Button(label=f"модератором: {inter.author.display_name}", style=disnake.ButtonStyle.grey, custom_id="moder", disabled=True)
        ]
        await inter.response.edit_message(components=components)
        for i, component in enumerate(components):
            self.children.insert(i, component)
        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"Модератор {inter.author.mention} (@{inter.author.display_name}) обработал [заявку]({inter.message.jump_url}) о присоединении пользователя {self.member.mention} (@{self.member.display_name}).", color=config.Colors.TRANSPARENT))

    async def common_logic(self, inter: disnake.MessageInteraction):
        if self.moder_id is not None and self.moder_id != inter.author.id:
            await inter.response.send_message(f"Эта заявка уже обрабатывается модератором {inter.author.mention} (@{inter.author.display_name})!", ephemeral=True)
            return
        if self.moder_id is None:
            self.moder_id = inter.author.id
        for item in self.children:
            if item.custom_id == inter.component.custom_id or item.disabled:
                item.disabled = True
            else:
                item.disabled = False
            if item.custom_id in ["waiting", "moder", "ban"]:
                self.remove_item(item)

        for item in self.children.copy():
            if item.custom_id in ["waiting", "moder", "ban"]:
                self.remove_item(item)

        components = [
            disnake.ui.Button(label="В обработке", style=disnake.ButtonStyle.grey, custom_id="waiting", disabled=True, row=0),
            disnake.ui.Button(label=f"модератором: {inter.author.display_name}", style=disnake.ButtonStyle.grey, custom_id="moder", disabled=True, row=0),
            disnake.ui.Button(label="Бан", style=disnake.ButtonStyle.danger, custom_id="ban", disabled=True, row=0)
        ]
        for component in components:
            self.add_item(component)
        components[2].callback = self.ban
        global moder_id
        moder_id = inter.author.id
        for item in self.children:
            if item.custom_id == "processing":
                item.disabled = True
        await inter.response.edit_message(view=self)
        await asyncio.sleep(30*60) # ЗАДЕРЖКА
        for item in self.children:
            if item.custom_id in ["processing", "ban"]:
                item.disabled = False
            else:
                item.disabled = True
        await inter.edit_original_message(view=self)

    @disnake.ui.button(label="Ник", style=disnake.ButtonStyle.grey, custom_id="nick", row=1)
    async def nick(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        channel_warn = inter.guild.get_channel(config.Channels.WARNINGS)
        time = disnake.utils.format_dt(datetime.datetime.now()+datetime.timedelta(minutes=30), style="t")
        await channel_warn.send(config.Joins(self.member, inter.author, "никнейм", time))
        await self.common_logic(inter)

    async def status(self, inter: disnake.MessageInteraction):
        channel_warn = inter.guild.get_channel(config.Channels.WARNINGS)
        time = disnake.utils.format_dt(datetime.datetime.now()+datetime.timedelta(minutes=30), style="t")
        await channel_warn.send(config.Joins(self.member, inter.author, "пользовательский статус", time))
        await self.common_logic(inter)

    async def avatar(self, inter: disnake.MessageInteraction):
        channel_warn = inter.guild.get_channel(config.Channels.WARNINGS)
        time = disnake.utils.format_dt(datetime.datetime.now()+datetime.timedelta(minutes=30), style="t")
        await channel_warn.send(config.Joins(self.member, inter.author, "аватарку профиля", time))
        await self.common_logic(inter)

    async def banner(self, inter: disnake.MessageInteraction):
        channel_warn = inter.guild.get_channel(config.Channels.WARNINGS)
        time = disnake.utils.format_dt(datetime.datetime.now()+datetime.timedelta(minutes=30), style="t")
        await channel_warn.send(config.Joins(self.member, inter.author, "баннер профиля", time))
        await self.common_logic(inter)
        
    async def ban(self, inter: disnake.MessageInteraction):
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" 
                INSERT INTO moders (id, joins) 
                VALUES (?, 1) 
                ON CONFLICT(id) 
                DO UPDATE SET joins = COALESCE(joins, 0) + 1 
            """, [inter.author.id])
            db.commit()

        components = [
            disnake.ui.Button(label="Забанен", style=disnake.ButtonStyle.grey, custom_id="success", disabled=True),
            disnake.ui.Button(label=f"модератором: {inter.author.display_name}", style=disnake.ButtonStyle.grey, custom_id="moder", disabled=True)
        ]
        await inter.response.edit_message(components=components)
        await Banned(self.member, "игнорирование просьбы модератора от смены публичных данных профиля пользователя, нарушающие правила дискорд-сервера", None, False).ban(inter)
        for i, component in enumerate(components):
            self.children.insert(i, component)
        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"Модератор {inter.author.mention} (@{inter.author.display_name}) обработал [заявку]({inter.message.jump_url}) о присоединении пользователя {self.member.mention} (@{self.member.display_name}).", color=config.Colors.TRANSPARENT))

def setup(bot):
    bot.add_cog(Joins(bot))

import config
import disnake
from disnake.ext import commands
import requests
import sqlite3



intents = disnake.Intents.default()
intents.guilds = True
intents.members = True



class Moders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name=disnake.Localized("statistics", key="STATS_NAME"),
        description=disnake.Localized("Moderator statistics.", key="STATS_DESCRIPTION"),
        default_member_permissions=disnake.Permissions(administrator=True),
        guild_ids=[config.Guilds.MAIN]
    )
    async def statistics(self, inter):
        
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" SELECT id, verifications, bans, mutes, joins FROM moders """)
            rows = cursor.fetchall()
            db.commit()

        embed = disnake.Embed(
            title="СТАТИСТИКА",
            description="",
            color=config.Colors.TRANSPARENT
        )
        embed.add_field(
            name=f"Модератор:",
            value=f"` Ники `/` Баны `/` Муты `/` Присоединения `",
            inline=False
        )
        for row in rows:
            moder, verifications, bans, mutes, joins = row
            moder = inter.guild.get_member(moder)
            if moder:
                roles = [config.Roles.DEVELOPER, config.Roles.CHIEF_MODERATOR, config.Roles.MODERATOR, config.Roles.MANAGER]
                if any(role in [r.id for r in moder.roles] for role in roles):
                    embed.add_field(
                        name=f"{moder.display_name}:",
                        value=f"` {verifications if verifications else 0} `/` {bans if bans else 0} `/` {mutes if mutes else 0} `/` {joins if joins else 0} `",
                        inline=False
                    )
        embed.set_image(file=disnake.File("./image/statistics.png", filename="statistics.png"))
        await inter.send(embed=embed)



    @commands.slash_command(
        name=disnake.Localized("servers", key="SERVERS_NAME"),
        description=disnake.Localized("The list of servers that have a bot.", key="SERVERS_DESCRIPTION"),
        default_member_permissions=disnake.Permissions(administrator=True),
        guild_ids=[config.Guilds.MAIN]
    )
    async def servers(self, inter):
        guilds = self.bot.guilds
        guild_per_page = 15
        pages = [guilds[i:i + guild_per_page] for i in range(0, len(guilds), guild_per_page)]
        embeds = []

        for i, page in enumerate(pages):
            embed = disnake.Embed(title=f"СПИСОК СЕРВЕРОВ — {len(guilds)}", description="", color=config.Colors.TRANSPARENT)
            for guild in page:
                embed.description+=f"**{guild.name}:** {guild.member_count} участников\n"
            embeds.append(embed)

        current_page = 0

        async def update_message(inter):
            view.previous_button.disabled = current_page == 0
            view.next_button.disabled = current_page == len(embeds) - 1
            view.page_number_button.label = f"{current_page + 1} из {len(embeds)}"
            await inter.response.edit_message(embed=embeds[current_page], view=view)

        class PaginationView(disnake.ui.View):
            def __init__(self, message, timeout):
                super().__init__(timeout=timeout)
                self.message = message
                self.previous_button.disabled = True
                self.next_button.disabled = len(guilds) <= guild_per_page

            @disnake.ui.button(label="⬅️", style=disnake.ButtonStyle.gray)
            async def previous_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                nonlocal current_page
                if current_page > 0:
                    current_page -= 1
                    await update_message(inter)

            @disnake.ui.button(label="", style=disnake.ButtonStyle.gray, disabled=True)
            async def page_number_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                pass

            @disnake.ui.button(label="➡️", style=disnake.ButtonStyle.gray)
            async def next_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                nonlocal current_page
                if current_page < len(embeds) - 1:
                    current_page += 1
                    await update_message(inter)

            async def on_timeout(self):
                for item in self.children:
                    item.disabled = True
                if self.message:
                    await self.message.edit(view=self)

        view = PaginationView(message=None, timeout=30)
        view.page_number_button.label = f"1 из {len(embeds)}"
        await inter.response.send_message(embed=embeds[current_page], view=view)
        message = await inter.original_message()
        view.message = message
        await message.edit(view=view)


def setup(bot):
    bot.add_cog(Moders(bot))

import config
import disnake
from disnake.ext import commands
import requests



global api
api = "https://api.gtaprovince.tech/api/gateway/v2/online"



class Monitoring(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name=disnake.Localized("monitoring", key="MONITORING_NAME"),
        description=disnake.Localized("Monitoring of servers Province.", key="MONITORING_DESCRIPTION")
    )
    async def monitoring(self, inter):
        await inter.response.defer(with_message="Загрузка списка серверов, онлайна и их состояния...")
        response = requests.get(api)
        data = response.json()
        
        total_online = 0
        total_max_online = 0

        obt_servers = data["result"]["servers"].get("OBT", {})
        obt_info = []
        for server_data in obt_servers.values():
            obt_info.append(f"{'<:red:1274003670102708234>' if server_data['ping']==0 and server_data['online']==0 else '<:green:1274003689987641476>'} **Province OBT:** {server_data['online']}/{server_data['maxOnline']} ({server_data['ping']} мс)")
            total_online += server_data["online"]
            total_max_online += server_data["maxOnline"]
        obt_info = "\n".join(obt_info)

        rp_servers = data['result']['servers'].get("RP", {})
        rp_info = []
        for server_data in rp_servers.values():
            rp_info.append(f"{'<:red:1274003670102708234>' if server_data['ping']==0 and server_data['online']==0 else '<:green:1274003689987641476>'} **Province RP {server_data['id']}:** {server_data['online']}/{server_data['maxOnline']} ({server_data['ping']} мс)")
            total_online += server_data["online"]
            total_max_online += server_data["maxOnline"]
        rp_info = "\n".join(rp_info)

        peak_online_today = data['result']['max_daily_online']['count']

        embed = disnake.Embed(
            title="MTA PROVINCE — МОНИТОРИНГ", 
            description=f"{rp_info}\n{obt_info}\n\n**Текущий онлайн:** {total_online}/{total_max_online}\n**Пиковый онлайн:** {peak_online_today}/{total_max_online}",
            color=config.Colors.TRANSPARENT
        )
        embed.set_image(file=disnake.File("./image/monitoring.png", filename="monitoring.png"))
        await inter.send(embed=embed)



def setup(bot):
    bot.add_cog(Monitoring(bot))

import config
from loguru import logger
from disnake.ext import commands



class Reaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.guild_id != config.Guilds.MAIN:
            return
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = await guild.getch_member(payload.user_id)

        flags = ["🇦🇩","🇦🇲","🇦🇪","🇦🇴","🇦🇬","🇦🇮","🇦🇫","🇦🇱","🇧🇦","🇦🇹","🇧🇧","🇦🇺","🇦🇶","🇦🇽","🇧🇩","🇦🇷","🇦🇼","🇦🇸","🇧🇪","🇧🇫","🇧🇭","🇧🇴","🇧🇮","🇧🇲","🇧🇯","🇧🇬","🇧🇱","🇧🇳","🇨🇦","🇧🇷","🇧🇾","🇧🇿","🇧🇸","🇧🇶","🇨🇨","🇧🇹","🇨🇩","🇧🇻","🇧🇼","🇨🇭","🇨🇱","🇨🇬","🇨🇳","🇨🇫","🇨🇮","🇨🇲","🇨🇴","🇨🇷","🇩🇬","🇨🇼","🇩🇰","🇨🇺","🇩🇪","🇨🇽","🇨🇾","🇩🇯","🇨🇻","🇨🇿","🇪🇸","🇩🇿","🇪🇪","🇪🇷","🇩🇲","🇪🇬","🇪🇨","🇪🇦","🇪🇭","🇪🇹","🇩🇴","🇬🇧","🇫🇮","🇫🇯","🇫🇲","🇫🇷","🇬🇦","🇪🇺","🇬🇩","🇬🇱","🇬🇵","🇬🇪","🇬🇲","🇬🇭","🇬🇳","🇬🇫","🇬🇶","🇬🇾","🇬🇷","🇬🇺","🇭🇰","🇬🇸","🇬🇼","🇬🇹","🇭🇷","🇭🇳","🇭🇹","🇮🇩","🇮🇲","🇭🇺","🇮🇷","🇮🇶","🇮🇪","🇮🇳","🇮🇱","🇮🇴","🇯🇪","🇮🇹","🇯🇲","🇯🇴","🇮🇸","🇰🇪","🇰🇵","🇰🇲","🇰🇳","🇰🇭","🇯🇵","🇱🇧","🇱🇦","🇰🇷","🇰🇾","🇰🇿","🇱🇨","🇰🇼","🇱🇮","🇱🇹","🇱🇻","🇱🇾","🇱🇰","🇱🇷","🇱🇺","🇱🇸","🇲🇬","🇲🇲","🇲🇱","🇲🇦","🇲🇫","🇲🇪","🇲🇰","🇲🇨","🇲🇳","🇲🇩","🇳🇨","🇲🇵","🇲🇶","🇲🇷","🇳🇪","🇲🇹","🇲🇻","🇲🇾","🇳🇫","🇲🇺","🇲🇼","🇲🇽","🇳🇺","🇳🇿","🇳🇬","🇴🇲","🇳🇮","🇵🇦","🇳🇱","🇳🇴","🇳🇵","🇵🇱","🇵🇸","🇵🇲","🇵🇹","🇵🇳","🇵🇪","🇵🇷","🇵🇬","🇵🇭","🇵🇰","🇷🇼","🇵🇼","🇸🇦","🇵🇾","🇸🇧","🇶🇦","🇷🇪","🇷🇴","🇷🇸","🇷🇺","🇸🇨","🇸🇱","🇸🇲","🇸🇩","🇸🇪","🇸🇬","🇸🇭","🇸🇮","🇸🇯","🇸🇰","🇸🇸","🇸🇹","🇸🇸","🇸🇹","🇸🇻","🇸🇽","🇸🇾","🇸🇳","🇸🇴","🇸🇿","🇹🇳","🇹🇬","🇹🇭","🇹🇯","🇹🇰","🇹🇴","🇹🇱","🇹🇨","🇹🇲","🇹🇩","🇹🇿","🇺🇦","🇺🇬","🇺🇲","🇹🇷","🇹🇹","🇺🇳","🇺🇸","🇹🇻","🇹🇼","🇺🇾","🇳🇷","🇳🇦","🇲🇿","🇲🇸","🇲🇭","🇲🇴","🇰🇬","🇰🇮","🇭🇲","🇬🇬","🇬🇮","🇹🇫","🇵🇫","🇫🇴","🇫🇰","🇨🇰","🇨🇵","🇮🇨","🇦🇿","🇦🇨"]

        for flag in flags:
            if f"{payload.emoji}" == flag:
                await message.remove_reaction(payload.emoji, user)
                return
        return
        


def setup(bot: commands.Bot):
    bot.add_cog(Reaction(bot))


import disnake
import config
from disnake.ext import commands
from disnake import TextInputStyle
from decorator import guild, guild_m



class Solved:
    async def solved(inter: disnake.MessageInteraction):
        thread = inter.channel 
        if thread.parent_id is None:
            return await inter.send("Нельзя закрыть не пост!", ephemeral=True)
        user_permissions = thread.permissions_for(inter.author)
        if not user_permissions.manage_threads and thread.owner != inter.author:
            await inter.send("У вас нет прав на закрытие либо вы не создатель ветки!", ephemeral=True)
            return
        if thread.owner == inter.author:
            text = f"Автор {inter.author.mention} (@{inter.author.display_name}) закрыл ветку!"
        else:
            text = f"Модератор {inter.author.mention} (@{inter.author.display_name}) закрыл ветку от пользователя {thread.owner.mention} (@{thread.owner.display_name})!"
        await inter.send(text)
        await thread.edit(archived=True, locked=True)



class SolvedButton(disnake.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        
    @disnake.ui.button(label="Закрыть ветку", style=disnake.ButtonStyle.red, custom_id="solved_button", disabled=False)
    async def solved_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await Solved.solved(inter)



class SolvedCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.slash_command(
        name=disnake.Localized("close", key="SOLVED_NAME"),
        description=disnake.Localized("Close the forum thread.", key="SOLVED_DESCRIPTION"),
        guild_ids=[config.Guilds.MAIN]
    )
    async def solved_command(self, inter: disnake.GuildCommandInteraction):
        await Solved.solved(inter)



def setup(bot):
    bot.add_cog(SolvedCommand(bot))

import config
import disnake
import datetime
import sqlite3
from disnake.ext import commands
from decorator import guild, Logger

class Timeout(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name=disnake.Localized("timeout", key="TIMEOUT_NAME"),
        description=disnake.Localized("Give the user a timeout.", key="TIMEOUT_DESCRIPTION"),
        default_member_permissions=disnake.Permissions(mute_members=True),
        guild_ids=[config.Guilds.MAIN]
    )
    async def timeout(
        self, 
        inter: disnake.GuildCommandInteraction,
        member: disnake.Member = commands.Param(name=disnake.Localized("member", key="TIMEOUT_MEMBER_NAME"), description=disnake.Localized("The user who needs to be given a timeout.", key="TIMEOUT_MEMBER_DESCRIPTION")),
        reason: str = commands.Param(name=disnake.Localized("reason", key="TIMEOUT_REASON_NAME")),
        days: int = commands.Param(name=disnake.Localized("days", key="TIMEOUT_DAYS_NAME"), description=disnake.Localized("From 0 to 30 days.", key="TIMEOUT_DAYS_DESCRIPTION"), max_value=28, min_value=0, default=0),
        hours: int = commands.Param(name=disnake.Localized("hours", key="TIMEOUT_HOURS_NAME"), description=disnake.Localized("From 0 to 24 hours.", key="TIMEOUT_HOURS_DESCRIPTION"), max_value=24, min_value=0, default=0),
        minutes: int = commands.Param(name=disnake.Localized("minutes", key="TIMEOUT_MINUTES_NAME"), description=disnake.Localized("From 0 to 60 minutes.", key="TIMEOUT_MINUTES_DESCRIPTION"), max_value=60, min_value=0, default=0),
    ):
        time = datetime.timedelta(days=days, hours=hours, minutes=minutes)
        cool_time = disnake.utils.format_dt(datetime.datetime.now()+time, style="f")
        if member.current_timeout:
            await inter.send(f"У пользователя  {member.mention} (@{member.display_name}) имеется действующий тайм-аут!", ephemeral=True)
            return        
        await member.timeout(duration=time, reason=reason)
        
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" INSERT INTO moders (id, mutes) VALUES (?, 1) ON CONFLICT(id) DO UPDATE SET mutes = COALESCE(mutes, 0) + 1 """, [inter.author.id])
            db.commit()

        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"Пользователю {member.mention} (@{member.display_name}) выдан тайм-аут модератором {inter.author.mention} (@{inter.author.display_name}) на {' '+str(days)+' дн.' if days != 0 else ''}{' '+str(hours)+' ч.' if hours != 0 else ''}{' '+str(minutes)+' мин.' if minutes != 0 else ''}, по причине: {reason.lower()}.", color=config.Colors.TRANSPARENT))
        channel_warn = inter.guild.get_channel(config.Channels.WARNINGS)
        await channel_warn.send(f"{member.mention} (@{member.display_name}), вам выдан тайм-аут модератором {inter.author.mention} (@{inter.author.display_name}) до {cool_time} (на {' '+str(days)+' дн.' if days != 0 else ''}{' '+str(hours)+' ч.' if hours != 0 else ''}{' '+str(minutes)+' мин.' if minutes != 0 else ''}), по причине: {reason.lower()}.")
        await inter.send(f"Пользователю {member.mention} (@{member.display_name}) выдан тайм-аут до {cool_time} (на {' '+str(days)+' дн.' if days != 0 else ''}{' '+str(hours)+' ч.' if hours != 0 else ''}{' '+str(minutes)+' мин.' if minutes != 0 else ''})!", ephemeral=True)

    

    @commands.slash_command(
        name=disnake.Localized("untimeout", key="UNTIMEOUT_NAME"),
        description=disnake.Localized("Remove the user's timeout.", key="UNTIMEOUT_DESCRIPTION"),
        default_member_permissions=disnake.Permissions(mute_members=True),
        guild_ids=[config.Guilds.MAIN]
    )
    async def untimeout(
        self, 
        inter: disnake.GuildCommandInteraction,
        member: disnake.Member = commands.Param(name=disnake.Localized("member", key="UNTIMEOUT_MEMBER_NAME"), description=disnake.Localized("The user to take the timeout from.", key="UNTIMEOUT_MEMBER_DESCRIPTION"))
    ):
        if not member.current_timeout:
            await inter.send(f"У пользователя  {member.mention} нет тайм-аута!", ephemeral=True)
            return
        await member.timeout(until=None, reason=None)
        
        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"У пользователя {member.mention} (@{member.display_name}) изъят тайм-аут модератором {inter.author.mention} (@{inter.author.display_name}).", color=config.Colors.TRANSPARENT))
        channel_warn = inter.guild.get_channel(config.Channels.WARNINGS)
        await channel_warn.send(f"{member.mention} (@{member.display_name}), у вас изъят тайм-аут модератором {inter.author.mention} (@{inter.author.display_name}).")
        await inter.send(f"У пользователя {member.mention} (@{member.display_name}) изъят тайм-аут!")

def setup(bot):
    bot.add_cog(Timeout(bot))


import config
import disnake
import sqlite3
from disnake.ext import commands
from decorator import guild_m



class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener("on_message")
    async def on_message_detect(self, message: disnake.Message):
        if message.channel.id != config.Channels.VERIFY:
            return
        if "_" not in message.content or message.author.id == self.bot.user.id:
            if message.author.id == self.bot.user.id:
                return
            await message.delete()
            return
        else:
            channel = message.guild.get_channel(config.Channels.VERIFY)
            message_split = message.content.split("_")
            imya = message_split[0].title()
            familiya = message_split[1].title()

            with sqlite3.connect("./locale/database.db") as db:
                cursor = db.cursor()

            if cursor.execute(""" SELECT name FROM names WHERE name = ? """, [imya]).fetchone() is not None:
                if cursor.execute(""" SELECT id FROM blacklist WHERE id = ? """, [int(message.author.id)]).fetchone() is not None:
                
                    manual_change = ManualChange(message, nick=f"{imya}_{familiya}")
                    await manual_change.manual_change(channel)

                    db.commit()
                    
                    return
                auto_change = AutoChange(message, nick=f"{imya}_{familiya}")
                await auto_change.auto_change(channel)
            else:
                manual_change = ManualChange(message, nick=f"{imya}_{familiya}")
                await manual_change.manual_change(channel)
            
        db.commit()



class AutoChange:
    def __init__(self, message, nick):
        self.message = message
        self.nick = nick

    async def auto_change(self, channel):
        role = self.message.guild.get_role(config.Roles.VERIFY)
        if role not in self.message.author.roles:
            await self.message.author.add_roles(role)
        await self.message.author.edit(nick=self.nick)
        await self.message.add_reaction("🤝")
        channel_tech = self.message.guild.get_channel(config.Channels.VERIFY_TECH)
        embed=disnake.Embed(
            title="", 
            description=f"Пользователю {self.message.author.mention} (@{self.message.author.display_name}) сменен ник автоматически на {self.nick}!",
            color=config.Colors.TRANSPARENT
        )
        await channel_tech.send(embed=embed, view=AutoVerifyButton(self.message, self.nick))



class ManualChange:
    def __init__(self, message, nick):
        self.message = message
        self.nick = nick

    async def manual_change(self, channel):
        await self.message.add_reaction("👎")
        try:
            if self.message.thread == None:
                thread = await self.message.create_thread(name=f"Действия ({self.message.id})", auto_archive_duration=10080)
            else: 
                thread = self.message.thread
            await thread.send(f"Заявка не обработана автоматически и отправлена на проверку модераторам!")
        except: pass
        channel_tech = self.message.guild.get_channel(config.Channels.VERIFY_TECH)
        embed=disnake.Embed(
            title="", 
            description=f"Пользователю {self.message.author.mention} (@{self.message.author.display_name}) не сменен ник автоматически на {self.nick}!",
            color=config.Colors.TRANSPARENT
        )
        await channel_tech.send(embed=embed, view=ManualVerifyButton(self.message, self.nick))



class ManualVerifyButton(disnake.ui.View):
    def __init__(self, message, nick):
        self.message = message
        self.nick = nick
        super().__init__(timeout=None)
        self.message_link = disnake.ui.Button(label="Сообщение", url=self.message.jump_url)
        self.add_item(self.message_link)
        
    @disnake.ui.button(label="Сменить", style=disnake.ButtonStyle.green, custom_id="change")
    async def change(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(modal=ModalVerify(self.message, self.nick))
    @disnake.ui.button(label="Неверный ник", style=disnake.ButtonStyle.red, custom_id="invalid")
    async def invalid(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        try:
            if self.message.thread == None:
                thread = await self.message.create_thread(name=f"Действия ({self.message.id})", auto_archive_duration=10080)
            else: 
                thread = self.message.thread
            await thread.send(f"Ваша заявка обработана модератором {inter.author.mention} (@{inter.author.display_name}) и не соблюдает правила никнеймов на проекте, такого никнейма не существует либо заявка составлена не верно! Создайте заявку вновь, по истечению времени задержки!")
            try: await thread.remove_user(inter.author)
            except: pass
        except: pass
        
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" INSERT INTO moders (id, joins) VALUES (?, 1) ON CONFLICT(id) DO UPDATE SET joins = COALESCE(joins, 0) + 1 """, [inter.author.id])
            db.commit()

        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"Модератор {inter.author.mention} (@{inter.author.display_name}) обработал [заявку]({inter.message.jump_url}) о смене ника пользователю {self.message.author.mention} (@{self.message.author.display_name}).", color=config.Colors.TRANSPARENT))
        components=[
            disnake.ui.Button(label=f"Обработано как неверный ник", style=disnake.ButtonStyle.grey, custom_id="status", disabled=True),
            disnake.ui.Button(label=f"модератором: {inter.author.display_name}", style=disnake.ButtonStyle.grey, custom_id="moder", disabled=True),
            disnake.ui.Button(label="Сообщение", url=self.message.jump_url)
        ]
        await inter.edit_original_response(components=components)



class AutoVerifyButton(disnake.ui.View):
    def __init__(self, message, nick):
        self.message = message
        self.member = message.author
        self.nick = nick
        super().__init__(timeout=None)
        self.message_link = disnake.ui.Button(label="Сообщение", url=self.message.jump_url)
        self.add_item(self.message_link)
        
    @disnake.ui.button(label="Обработать", style=disnake.ButtonStyle.blurple, custom_id="processing")
    async def processing(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" INSERT INTO moders (id, joins) VALUES (?, 1) ON CONFLICT(id) DO UPDATE SET joins = COALESCE(joins, 0) + 1 """, [inter.author.id])
            db.commit()

        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"Модератор {inter.author.mention} (@{inter.author.display_name}) обработал [заявку]({inter.message.jump_url}) о смене ника пользователю {self.member.mention} (@{self.member.display_name}).", color=config.Colors.TRANSPARENT))
        components=[
            disnake.ui.Button(label=f"Обработано", style=disnake.ButtonStyle.grey, custom_id="succes", disabled=True),
            disnake.ui.Button(label=f"модератором: {inter.author.display_name}", style=disnake.ButtonStyle.grey, custom_id="moder", disabled=True),
            disnake.ui.Button(label="Сообщение", url=self.message.jump_url)
        ]
        await inter.response.edit_message(components=components)
        # await inter.send(f"Заявка {inter.message.jump_url} обработана!")
        pass
    @disnake.ui.button(label="Сменить", style=disnake.ButtonStyle.green, custom_id="change")
    async def change(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(modal=ModalVerify(self.message, self.nick))
    @disnake.ui.button(label="Сбросить", style=disnake.ButtonStyle.red, custom_id="reset")
    async def reset(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        role = inter.guild.get_role(config.Roles.VERIFY)
        try:
            if role in self.member.roles:
                await self.member.remove_roles(role)
            await self.member.edit(nick=self.member.name)
        except: pass
        try: 
            await self.message.clear_reactions()
            await self.message.add_reaction("👎")
            if self.message.thread == None:
                thread = await self.message.create_thread(name=f"Действия ({self.message.id})", auto_archive_duration=10080)
            else: 
                thread = self.message.thread
            await thread.send(f"Ник сброшен модератором {inter.author.mention} (@{inter.author.display_name}) до: {self.member.name}! Создайте заявку вновь, по истечению времени задержки!")
            try: await thread.remove_user(inter.author)
            except: pass
        except: pass
        
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" INSERT INTO moders (id, joins) VALUES (?, 1) ON CONFLICT(id) DO UPDATE SET joins = COALESCE(joins, 0) + 1 """, [inter.author.id])
            cursor.execute(""" INSERT INTO blacklist(id) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM blacklist WHERE id = ?) """, [self.member.id])
            db.commit()

        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"Модератор {inter.author.mention} (@{inter.author.display_name}) обработал [заявку]({inter.message.jump_url}) о смене ника пользователю {self.member.mention} (@{self.member.display_name}).", color=config.Colors.TRANSPARENT))
        components=[
            disnake.ui.Button(label=f"Сброшен до: {self.member.name}", style=disnake.ButtonStyle.grey, custom_id="succes", disabled=True),
            disnake.ui.Button(label=f"модератором: {inter.author.display_name}", style=disnake.ButtonStyle.grey, custom_id="moder", disabled=True),
            disnake.ui.Button(label="Сообщение", url=self.message.jump_url)
        ]
        await inter.edit_original_response(components=components)



class ModalVerify(disnake.ui.Modal):
    def __init__(self, message, nick) -> None:
        self.nick = nick
        self.message = message
        self.member = message.author

        components = [
            disnake.ui.TextInput(
                label="Никнейм",
                placeholder="Имя_Фамилия",
                custom_id="nick",
                style=disnake.TextInputStyle.short,
                value=f"{self.nick}",
                required=True,
            ),
        ]
        super().__init__(title=f"Сменить ник {self.member.display_name}", custom_id="modal_verify", components=components)

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        nick = inter.text_values["nick"]
        role = inter.guild.get_role(config.Roles.VERIFY)
        try: 
            if role not in self.member.roles:
                await self.member.add_roles(role)
            await self.member.edit(nick=nick)
        except: pass
        message = self.message
        try: 
            await message.clear_reactions()
            await message.add_reaction("🤝")
            if message.thread == None:
                thread = await message.create_thread(name=f"Действия ({message.id})", auto_archive_duration=10080)
            else: 
                thread = message.thread
            await thread.send(f"Ник сменен модератором {inter.author.mention} (@{inter.author.display_name}) на: {nick}!")
            try: await thread.remove_user(inter.author)
            except: pass
        except: pass
        components=[
            disnake.ui.Button(label=f"Сменен на: {nick}", style=disnake.ButtonStyle.grey, custom_id="succes", disabled=True),
            disnake.ui.Button(label=f"модератором: {inter.author.display_name}", style=disnake.ButtonStyle.grey, custom_id="moder", disabled=True),
            disnake.ui.Button(label="Сообщение", url=message.jump_url)
        ]
        nick = nick.split("_")
        imya = nick[0].title()
        
        with sqlite3.connect("./locale/database.db") as db:
            cursor = db.cursor()
            cursor.execute(""" INSERT INTO moders (id, joins) VALUES (?, 1) ON CONFLICT(id) DO UPDATE SET joins = COALESCE(joins, 0) + 1 """, [inter.author.id])
            cursor.execute(""" INSERT INTO names(name) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM names WHERE name = ?) """, [imya])
            db.commit()

        channel_logs = inter.guild.get_channel(config.Channels.LOGS)
        await channel_logs.send(embed=disnake.Embed(description=f"Модератор {inter.author.mention} (@{inter.author.display_name}) обработал [заявку]({inter.message.jump_url}) о смене ника пользователю {self.member.mention} (@{self.member.display_name}).", color=config.Colors.TRANSPARENT))
        await inter.response.edit_message(components=components)
        # await inter.send(f"Заявка {inter.message.jump_url} обработана!")
        pass


def setup(bot):
    bot.add_cog(Verify(bot))

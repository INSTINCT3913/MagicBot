import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient

class addClan(commands.Cog, name="Clan Setup"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.color = disnake.Color.dark_theme()

    @commands.slash_command(name="addclan", description="Add a clan to the server")
    async def addClan(self, ctx: disnake.ApplicationCommandInteraction, clan_tag:str, category: str, general_clan_role:disnake.Role, leadership_clan_role:disnake.Role,
                      clan_channel: disnake.TextChannel):
        """
            Parameters
            ----------
            clan_tag: clan to add to server
            category: choose a category or type your own
            general_clan_role: role that all members of this clan receive
            leadership_clan_role: role that leaders (typically co+) would receive
            clan_channel: channel where ban pings & welcome messages should go
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if general_clan_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(description=f"General Clan Role cannot be {ctx.guild.default_role.mention}.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if leadership_clan_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(description=f"Leadership Clan Role cannot be {ctx.guild.default_role.mention}.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if general_clan_role.id == leadership_clan_role.id:
            embed = disnake.Embed(description="General Clan Role & Clan Leadership Role cannot be the same.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await ctx.response.defer()
        #check if clan is already linked
        clan = await self.bot.getClan(clan_tag)
        if clan is None:
            return await ctx.send("Not a valid clan tag")
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = disnake.Embed(description=f"{clan.name} is already linked to this server.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        await self.bot.clan_db.insert_one({
            "name" : clan.name,
            "tag" : clan.tag,
            "generalRole" : general_clan_role.id,
            "leaderRole" : leadership_clan_role.id,
            "category" : category,
            "server" : ctx.guild.id,
            "clanChannel" : clan_channel.id
        })

        tags = await self.bot.clan_db.distinct("tag")
        self.bot.coc_client.add_war_updates(*tags)

        embed = disnake.Embed(title=f"{clan.name} successfully added.",
                              description=f"Clan Tag: {clan.tag}\n"
                                          f"General Role: {general_clan_role.mention}\n"
                                          f"Leadership Role: {leadership_clan_role.mention}\n"
                                          f"Clan Channel: {clan_channel.mention}\n"
                                          f"Category: {category}",
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        await ctx.edit_original_message(embed=embed)

    @addClan.autocomplete("category")
    async def autocomp_names(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        categories = ["General", "Feeder", "War", "Esports"]
        if query != "":
            categories.append(query)
        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if query.lower() in category.lower():
                if category not in categories:
                    categories.append(category)
        return categories[0:24]

    @commands.slash_command(name="removeclan", description="Remove a clan from the server")
    async def removeClan(self, ctx: disnake.ApplicationCommandInteraction, clan:str):
        """
            Parameters
            ----------
            clan: clan to add to server [clan tag, alias, or autocomplete]
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await ctx.response.defer()
        clan_search = clan.lower()
        first_clan = clan
        results = await self.bot.clan_db.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await self.bot.getClan(tag)
        else:
            clan = await self.bot.getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await self.bot.getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag.")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = disnake.Embed(description=f"{clan.name} is not currently set-up as a family clan.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        embed = disnake.Embed(description=f"Are you sure you want to remove {clan.name} [{clan.tag}]?",
                              color=disnake.Color.red())
        embed.set_thumbnail(url=clan.badge.large)

        page_buttons = [
            disnake.ui.Button(label="Yes", emoji="✅", style=disnake.ButtonStyle.green,
                              custom_id="Yes"),
            disnake.ui.Button(label="No", emoji="❌", style=disnake.ButtonStyle.red,
                               custom_id="No")
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)

        await ctx.edit_original_message(embed=embed, components=[buttons])
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        chose = False
        while chose is False:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author.id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", ephemeral=True)
                continue

            chose = res.data.custom_id

            if chose == "No":
                embed = disnake.Embed(description=f"Sorry to hear that. Canceling the command now.",
                                      color=disnake.Color.green())
                embed.set_thumbnail(url=clan.badge.large)
                return await res.response.edit_message(embed=embed,
                                      components=[])

        await self.bot.clan_db.find_one_and_delete({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})

        tags = await self.bot.clan_db.distinct("tag")
        self.bot.coc_client.add_war_updates(*tags)
        embed = disnake.Embed(
            description=f"{clan.name} removed as a family clan.",
            color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return await msg.edit(embed=embed, components=[])

    @removeClan.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]

def setup(bot: CustomClient):
    bot.add_cog(addClan(bot))

import discord
from discord.ext import commands


class SupportOperations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def show_support_menu(self, interaction: discord.Interaction):
        support_menu_embed = discord.Embed(
            title="🎯 Support Operations",
            description=(
                "Please select an operation:\n\n"
                "**Available Operations**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "📝 **Request Support**\n"
                "└ Get help and support\n\n"
                "👨‍💻 **Developer About**\n"
                "└ Developer information\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.blue()
        )

        view = SupportView(self)

        try:
            await interaction.response.edit_message(embed=support_menu_embed, view=view)
        except discord.errors.InteractionResponded:
            await interaction.message.edit(embed=support_menu_embed, view=view)

    async def show_support_info(self, interaction: discord.Interaction):
        support_embed = discord.Embed(
            title="🤖 Bot Support Information",
            description=(
                "Hello! If you need help with the bot or are experiencing any issues, "
                "you can always contact me.\n\n"
                # "**Discord Server:** [Click Here](https://discord.gg/h8w6N6my4a)\n"
                "**Developer Contact:** Discord Username: spiritingauto04\n\n"
                "Our bot's source code is always 100% open source. "
                "This bot was created and published by Reloisback for free and "
                "modified by SpiritingAuto04\n\n"
                "If you would like to support us\n"
                "[☕ Buy me a coffee](https://ko-fi.com/spiritingauto)\n\n"
                "You can always support by clicking this link.\n"
                "Thank you for using my bot.\n"
                "Feel free to contact me anytime for support."
            ),
            color=discord.Color.gold()
        )

        support_embed.set_thumbnail(url="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png")

        try:
            await interaction.response.send_message(embed=support_embed, ephemeral=True)
            try:
                await interaction.user.send(embed=support_embed)
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Could not send DM because your DMs are closed!",
                    ephemeral=True
                )
        except Exception as e:
            print(f"Error sending support info: {e}")


class SupportView(discord.ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    @discord.ui.button(
        label="Request Support",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="request_support"
    )
    async def support_request_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_support_info(interaction)

    '''@discord.ui.button(
        label="Developer About",
        emoji="👨‍💻",
        style=discord.ButtonStyle.primary,
        custom_id="developer_about"
    )
    async def developer_about_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        about_embed = discord.Embed(
            title="👨‍💻 About the Developer",
            description=(
                "Thank you for clicking this button, as it shows your interest in learning "
                "about the person behind this bot.\n\n"
                "**Personal Introduction**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "I'm Umut, a 27-year-old developer specializing in Python and PHP. "
                "While I used to be an avid gamer, my responsibilities as a family provider "
                "have shifted my priorities, leaving limited time for gaming.\n\n"
                "**Bot's Journey**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "White of Survival bot started as a fun project for my own alliance. "
                "Upon realizing there wasn't anything similar available, I decided to develop "
                "it further and share it with the community. You're currently experiencing "
                "Version 4, following successful releases of V1, V2, and V3.\n\n"
                "The development process has been intense, ranging from 1-2 hours some days "
                "to marathon 14-15 hour coding sessions.\n\n"
                "**Why Free?**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "I'm often asked why I keep this bot free. The answer is simple: accessibility. "
                "If monetized, the user base would shrink from thousands to perhaps just 10-15 users. "
                "Having experienced financial constraints myself, I understand the importance of "
                "making useful tools available to everyone, regardless of their financial situation.\n\n"
                "**Support & Development**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "For those who can and wish to support the project, you can use the "
                "[☕ Buy me a coffee](https://www.buymeacoffee.com/reloisback) link. "
                "These contributions help cover development costs (proxies, servers, testing) "
                "and support my family.\n\n"
                "**Final Words**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "To those unable to provide financial support - thank you for using the bot! "
                "Support has never been and will never be mandatory. This project will remain "
                "free forever.\n\n"
                "I love this community and thank you all for being part of this journey. ❤️"
            ),
            color=discord.Color.purple()
        )

        about_embed.set_footer(text="Made with ❤️ by Reloisback")

        try:
            await interaction.response.send_message(embed=about_embed, ephemeral=True)
            try:
                await interaction.user.send(embed=about_embed)
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Could not send DM because your DMs are closed!",
                    ephemeral=True
                )
        except Exception as e:
            print(f"Error sending developer info: {e}")'''

    @discord.ui.button(
        label="Main Menu",
        emoji="🏠",
        style=discord.ButtonStyle.secondary,
        custom_id="main_menu"
    )
    async def main_menu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        alliance_cog = self.cog.bot.get_cog("Alliance")
        if alliance_cog:
            try:
                await interaction.message.edit(content=None, embed=None, view=None)
                await alliance_cog.show_main_menu(interaction)
            except discord.errors.InteractionResponded:
                await interaction.message.edit(content=None, embed=None, view=None)
                await alliance_cog.show_main_menu(interaction)


async def setup(bot):
    await bot.add_cog(SupportOperations(bot))
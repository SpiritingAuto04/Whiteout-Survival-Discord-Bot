from discord import app_commands
from discord.ext import commands
import discord
import sqlite3


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Verify your character by entering the game ID")
    async def verify_user(self, interaction: discord.Interaction, character_id: str):
        user = interaction.user
        user_id = str(user.id)

        conn = sqlite3.connect("db/users.sqlite")
        conn2 = sqlite3.connect("db/alliance.sqlite")

        cursor = conn.cursor()
        cursor2 = conn2.cursor()

        cursor.execute("SELECT fid FROM users WHERE discord_id = ?", (user_id,))
        existing_id = cursor.fetchone()

        if existing_id:
            await interaction.response.send_message(
                f"❌ Have you already verified a character with ID `{existing_id[0]}` and cannot check another.",
                ephemeral=True
            )
            conn.close()
            return

        cursor.execute("SELECT nickname FROM users WHERE fid = ?", (character_id,))
        result = cursor.fetchone()

        if result:
            character_name = result[0]

            cursor.execute("UPDATE users SET discord_id = ? WHERE fid = ?", (user_id, character_id))
            conn.commit()

            guild = interaction.guild
            guild_id = guild.id

            cursor.execute(f"SELECT gid FROM users WHERE gid =?", (guild_id))
            conn.commit()

            roleID = cursor2.execute("SELECT role_id WHERE gid = ?", (guild_id))

            role = self.bot.get_role(roleID)
            conn2.close()

            if role:
                try:
                    await user.add_roles(role)
                    print(f"[LOG] Cargo '{role.name}' atribuído a {user.name}")
                except discord.Forbidden:
                    print("[ERRO] Permissão negada para atribuir cargos.")
                    await interaction.response.send_message("⚠️ I don't have permission to add roles.", ephemeral=True)
                    conn.close()
                    return

                await interaction.response.send_message(
                    f"✅ {user.mention}, Your verification is complete! You have been assigned the position **{role.name}**.",
                    ephemeral=True
                )

                try:
                    await user.edit(nick=character_name)
                    print(f"[LOG] Apelido de {user.name} alterado para '{character_name}'")
                    await interaction.followup.send(f"🔹 Seu apelido foi alterado para **{character_name}**.",
                                                    ephemeral=True)
                except discord.Forbidden:
                    print("[ERRO] Permissão negada para alterar apelidos.")
                    await interaction.followup.send(
                        "⚠️ I don't have permission to change your nickname. Please change it manually.",
                        ephemeral=True)

            else:
                print("[ERRO] Cargo não encontrado.")
                await interaction.response.send_message("⚠️ The position was not found. Contact an administrator.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid character ID. Please check and try again.",
                                                    ephemeral=True)

        conn.close()


async def setup(bot):
    await bot.add_cog(Verification(bot))

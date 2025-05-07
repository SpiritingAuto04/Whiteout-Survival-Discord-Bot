import discord
import requests
import json
import time

from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from random import choice

class AgeUnlocks:
    def create_unix_time(self, date: datetime, days: int, hours: int, minutes: int, seconds: int) -> str:
        end_date = date + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        date_touple = (end_date.year, end_date.month, end_date.day, end_date.hour, end_date.minute, end_date.second)

        return f'<t:{int(time.mktime(datetime(*date_touple).timetuple()))}:R>'


    '''def agecalc(self, server_age):
        # today = datetime.today().strftime("")
        # server_start = server_age

        difference = server_age - datetime.today().timestamp()

        with open('./random_json/state_unlocks.json', 'r', encoding='utf-8') as unlocks:
            unlock = json.load(unlocks)
            unlock = unlock['milestones']

            for entry in unlock:
                if entry['day'] <= difference:

                    print()'''




    # milestones = json.loads()

class MiscCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="server_age_calculator", description="Lookup the server age using the server number!")
    @app_commands.describe(stateid="The Server number you want to lookup")
    async def serverage(self, interaction: discord.Interaction, stateid : int):
        api = "https://wosland.com/bahraini/stateage/api.php"
        urlstring = f"{api}?state_id={stateid}"

        # msg = await interaction.response.send_message(f"Sending request to:\n{urlstring}", ephemeral=True)

        payload = {}
        headers = {
            'Content-Type': 'application/json'
        }

        r = requests.get(url=urlstring, headers=headers, data=payload)

        t = json.loads(r.text)
        t = t['timestamp']

        # AgeUnlocks.agecalc(self, t)

        timestamp = datetime.fromtimestamp(t)

        # e = discord.Embed(title="Server Age", description=f"The server `{stateid}` was created <t:{t}> your local time ({timestamp} UTC)")
        e = discord.Embed(title="Server Age", color=discord.Color.random())
        e.add_field(name="Server Creation Date:", value=f"Your Localised Time: <t:{t}> \nUTC Time: ({timestamp})")
        # e.add_field(name="Age", value=datetime.strptime(t, "%d/%m/%Y %H:%M:%S"), inline=False)
        # e.add_field(name="Just Unlocked:", value=)

        await interaction.response.send_message(content = f"{stateid}'s creation",embed=e, ephemeral=True)

        # await interaction.response.send_message(f"The server `{stateid}` was created <t:{t}> your local time ({timestamp} UTC) <t:{t}:R>", ephemeral=True)


async def setup(bot):
    await bot.add_cog(MiscCommands(bot))

import discord
from discord.ext import commands
import json
import base64
from datetime import datetime
import pytz
import urllib.parse
import traceback


class CodeInputModal(discord.ui.Modal):
    def __init__(self, editor_cog, notification_id):
        super().__init__(title="Enter Embed Code")
        self.editor_cog = editor_cog
        self.notification_id = notification_id

        self.code_input = discord.ui.TextInput(
            label="Code from Web Panel",
            placeholder="Paste your code here...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            embed_data = self.editor_cog.decode_embed_data(self.code_input.value)
            if not embed_data:
                await interaction.response.send_message(
                    "❌ Invalid code! Please use the code from web panel.",
                    ephemeral=True
                )
                return

            preview_embed = discord.Embed(
                title=embed_data.get('title', 'Bear Trap Notification'),
                description=embed_data.get('description', 'Get ready for Bear! Only %t remaining.'),
                color=embed_data.get('color', discord.Color.blue().value)
            )

            if embed_data.get('image_url'):
                preview_embed.set_image(url=embed_data['image_url'])
            if embed_data.get('thumbnail_url'):
                preview_embed.set_thumbnail(url=embed_data['thumbnail_url'])
            if embed_data.get('footer'):
                preview_embed.set_footer(text=embed_data['footer'])
            if embed_data.get('author'):
                preview_embed.set_author(name=embed_data['author'])

            mention_preview = embed_data.get('mention_message', '@tag')
            example_time = "30 minutes"
            if mention_preview:
                mention_preview = mention_preview.replace("%t", example_time)
                mention_preview = mention_preview.replace("{time}", example_time)

            class PreviewView(discord.ui.View):
                def __init__(self, modal):
                    super().__init__()
                    self.modal = modal

                @discord.ui.button(label="Select Channel and Tag", style=discord.ButtonStyle.primary, emoji="🔄")
                async def select_channel_mention(self, button_interaction: discord.Interaction,
                                                 button: discord.ui.Button):
                    view = ChannelMentionSelectView(self.modal.editor_cog, self.modal.notification_id, embed_data)
                    embed = discord.Embed(
                        title="📝 Channel Selection",
                        description="Please select the channel for notification.",
                        color=discord.Color.blue()
                    )
                    await button_interaction.response.edit_message(embed=embed, view=view)

                @discord.ui.button(label="Update Embed Only", style=discord.ButtonStyle.success, emoji="💾")
                async def update_embed_only(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if not self.modal.notification_id:
                        await button_interaction.response.send_message(
                            "❌ This option is only available in edit mode!",
                            ephemeral=True
                        )
                        return

                    success, message = await self.modal.editor_cog.update_notification(
                        self.modal.notification_id,
                        embed_data,
                        skip_channel_mention=True
                    )

                    if success:
                        result_embed = discord.Embed(
                            title="✅ Notification Updated",
                            description="Notification settings updated successfully!",
                            color=discord.Color.green()
                        )
                    else:
                        result_embed = discord.Embed(
                            title="❌ Error",
                            description=message,
                            color=discord.Color.red()
                        )
                    await button_interaction.response.edit_message(embed=result_embed, view=None)

                @discord.ui.button(label="Edit Again", style=discord.ButtonStyle.secondary, emoji="✏️")
                async def edit_again_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    modal = CodeInputModal(self.modal.editor_cog, self.modal.notification_id)
                    await button_interaction.response.send_modal(modal)

            info_text = (
                "**📝 Embed Preview**\n\n"
                f"**Mention Message Preview:**\n{mention_preview}"
            )

            if self.notification_id:
                bear_trap = self.editor_cog.bot.get_cog('BearTrap')
                if bear_trap:
                    bear_trap.cursor.execute("""
                        SELECT channel_id, mention_type
                        FROM bear_notifications 
                        WHERE id = ?
                    """, (self.notification_id,))
                    result = bear_trap.cursor.fetchone()
                    if result:
                        channel_id, mention_type = result
                        channel = interaction.guild.get_channel(channel_id)
                        mention_display = self.get_mention_display(interaction.guild, mention_type)

                        info_text += (
                            "\n\n**Current Settings**\n"
                            f"📢 Channel: {channel.mention if channel else 'Unknown'}\n"
                            f"👥 Tag: {mention_display}\n\n"
                            "🔄 Change channel and tag, use 'Select Channel and Tag' button.\n"
                            "💾 Update only the embed, use 'Update Embed Only' button.\n"
                            "✏️ Edit again, use 'Edit Again' button."
                        )

            await interaction.response.send_message(
                content=info_text,
                embed=preview_embed,
                view=PreviewView(self),
                ephemeral=True
            )

        except Exception as e:
            print(f"Error processing code: {e}")
            await interaction.response.send_message(
                "❌ Error processing code!",
                ephemeral=True
            )

    def get_mention_display(self, guild, mention_type):
        match mention_type:
            case "everyone":
                return "@everyone"
            case mention_type.startswith("role_"):
                role_id = int(mention_type.split('_')[1])
                role = guild.get_role(role_id)
                return f"@{role.name}" if role else f"Role: {role_id}"
            case mention_type.startswith("member_"):
                member_id = int(mention_type.split('_')[1])
                member = guild.get_member(member_id)
                return f"@{member.display_name}" if member else f"Member: {member_id}"
            case _:
                return "No Mention"


class NotificationEditView(discord.ui.View):
    def __init__(self, editor_cog, notification_id):
        super().__init__()
        self.editor_cog = editor_cog
        self.notification_id = notification_id

    @discord.ui.button(label="Edit on Web Panel", style=discord.ButtonStyle.primary, emoji="🌐")
    async def edit_web_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            bear_trap = self.editor_cog.bot.get_cog('BearTrap')
            if not bear_trap:
                await interaction.response.send_message(
                    "❌ Bear Trap module not found!",
                    ephemeral=True
                )
                return

            bear_trap.cursor.execute("""
                SELECT n.*, e.* 
                FROM bear_notifications n 
                LEFT JOIN bear_notification_embeds e ON n.id = e.notification_id 
                WHERE n.id = ? AND n.guild_id = ?
            """, (self.notification_id, interaction.guild_id))

            result = bear_trap.cursor.fetchone()
            if not result:
                await interaction.response.send_message(
                    "❌ Notification not found!",
                    ephemeral=True
                )
                return

            notification_columns = 16

            embed_data = {
                'title': result[18] if result[18] else "Bear Trap Notification",
                'description': result[19] if result[19] else "Get ready for Bear! Only %t remaining.",
                'color': result[20] if result[20] else 3447003,
                'image_url': result[21] if result[21] else None,
                'thumbnail_url': result[22] if result[22] else None,
                'footer': result[23] if result[23] else "Bear Trap Notification System",
                'author': result[24] if result[24] else None,
                'mention_message': result[25] if result[25] else "30 minutes @tag sa as",
                'notification': {
                    'date': result[15].strftime('%Y-%m-%d') if isinstance(result[15],
                                                                          datetime) else datetime.fromisoformat(
                        str(result[15])).strftime('%Y-%m-%d'),
                    'hour': result[3],
                    'minute': result[4],
                    'timezone': result[5],
                    'type': result[7],
                    'repeat_enabled': bool(result[9]),
                    'repeat_minutes': result[10],
                    'custom_times': result[6].split('|')[0].replace('CUSTOM_TIMES:', '') if result[6].startswith(
                        'CUSTOM_TIMES:') else None
                }
            }

            for key in list(embed_data.keys()):
                if embed_data[key] is None:
                    del embed_data[key]

            for key in list(embed_data['notification'].keys()):
                if embed_data['notification'][key] is None:
                    del embed_data['notification'][key]

            json_str = json.dumps(embed_data)
            encoded_data = urllib.parse.quote(json_str)
            edit_url = f"https://wosland.com/notification/notification.php?data={encoded_data}"

            embed = discord.Embed(
                title="🔄 Notification Edit",
                description=(
                    f"**Notification ID:** {self.notification_id}\n\n"
                    f"1️⃣ [Click to go to edit page]({edit_url})\n"
                    "2️⃣ Make necessary changes\n"
                    "3️⃣ Use the 'Apply Code' button to use the code you received"
                ),
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            print(f"Error generating edit URL: {e}")
            await interaction.response.send_message(
                "❌ Error generating edit URL!",
                ephemeral=True
            )

    @discord.ui.button(label="Apply Code", style=discord.ButtonStyle.success, emoji="💾")
    async def apply_code_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CodeInputModal(self.editor_cog, self.notification_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="◀️")
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        bear_trap = self.editor_cog.bot.get_cog('BearTrap')
        if bear_trap:
            await bear_trap.show_bear_trap_menu(interaction)
        else:
            await interaction.response.send_message(
                "❌ Error returning to main menu!",
                ephemeral=True
            )


class ChannelMentionSelectView(discord.ui.View):
    def __init__(self, editor_cog, notification_id, embed_data):
        super().__init__()
        self.editor_cog = editor_cog
        self.notification_id = notification_id
        self.embed_data = embed_data

        self.channel_select = discord.ui.ChannelSelect(
            placeholder="Select channel...",
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.private,
                discord.ChannelType.news,
                discord.ChannelType.forum,
                discord.ChannelType.news_thread,
                discord.ChannelType.public_thread,
                discord.ChannelType.private_thread,
                discord.ChannelType.stage_voice
            ],
            min_values=1,
            max_values=1
        )
        self.channel_select.callback = self.channel_select_callback
        self.add_item(self.channel_select)

        if notification_id:
            skip_button = discord.ui.Button(
                label="Skip",
                style=discord.ButtonStyle.secondary,
                emoji="⏭️"
            )
            skip_button.callback = self.skip_button_callback
            self.add_item(skip_button)

    async def channel_select_callback(self, interaction: discord.Interaction):
        self.selected_channel = self.channel_select.values[0]

        view = MentionTypeView(self.editor_cog, self.notification_id, self.selected_channel, self.embed_data)
        embed = discord.Embed(
            title="👥 Tag Selection",
            description=(
                "Select tag type for notification:\n\n"
                "📢 **@everyone** - Tag all members in the server\n"
                "👤 **Member Select** - Tag a specific member\n"
                "👥 **Role Select** - Tag a specific role\n"
                "🔕 **No Mention** - Send without mentioning"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def skip_button_callback(self, interaction: discord.Interaction):
        success, message = await self.editor_cog.update_notification(
            self.notification_id,
            self.embed_data,
            skip_channel_mention=True
        )
        if success:
            embed = discord.Embed(
                title="✅ Notification Updated",
                description="Notification settings updated successfully!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description=message,
                color=discord.Color.red()
            )
        await interaction.response.edit_message(embed=embed, view=None)


class MentionTypeView(discord.ui.View):
    def __init__(self, editor_cog, notification_id, channel, embed_data):
        super().__init__()
        self.editor_cog = editor_cog
        self.notification_id = notification_id
        self.channel = channel
        self.embed_data = embed_data

    @discord.ui.button(label="@everyone", style=discord.ButtonStyle.danger, emoji="📢", row=0)
    async def everyone_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.save_new_notification(interaction, "everyone", self.channel.id)

    @discord.ui.button(label="Member Select", style=discord.ButtonStyle.primary, emoji="👤", row=0)
    async def member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = discord.ui.UserSelect(
            placeholder="Select member...",
            min_values=1,
            max_values=1
        )

        async def user_select_callback(select_interaction):
            user = select.values[0]
            await self.save_new_notification(select_interaction, f"member_{user.id}", self.channel.id)

        select.callback = user_select_callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.edit_message(view=view)

    @discord.ui.button(label="Role Select", style=discord.ButtonStyle.success, emoji="👥", row=0)
    async def role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = discord.ui.RoleSelect(
            placeholder="Select role...",
            min_values=1,
            max_values=1
        )

        async def role_select_callback(select_interaction):
            role = select.values[0]
            await self.save_new_notification(select_interaction, f"role_{role.id}", self.channel.id)

        select.callback = role_select_callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.edit_message(view=view)

    @discord.ui.button(label="No Mention", style=discord.ButtonStyle.secondary, emoji="🔕", row=0)
    async def no_mention_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.save_new_notification(interaction, "none", self.channel.id)

    async def save_new_notification(self, interaction: discord.Interaction, mention_type: str, channel_id: int):
        try:
            bear_trap = self.editor_cog.bot.get_cog('BearTrap')
            if not bear_trap:
                await interaction.response.send_message("❌ Bear Trap module not found!", ephemeral=True)
                return

            if self.notification_id:
                success, message = await self.editor_cog.update_notification(
                    self.notification_id,
                    self.embed_data,
                    channel_id=channel_id,
                    mention_type=mention_type,
                    skip_channel_mention=False
                )

                if success:
                    embed = discord.Embed(
                        title="✅ Notification Updated",
                        description=(
                            "Notification updated successfully!\n\n"
                            f"📝 Channel: <#{channel_id}>\n"
                            f"👥 Tag: {mention_type}"
                        ),
                        color=discord.Color.green()
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Error",
                        description=f"Error updating notification: {message}",
                        color=discord.Color.red()
                    )
                await interaction.response.edit_message(embed=embed, view=None)
                return

            notification_id = await bear_trap.save_notification(
                guild_id=interaction.guild_id,
                channel_id=channel_id,
                start_date=datetime.strptime(self.embed_data['notification']['date'], '%Y-%m-%d'),
                hour=self.embed_data['notification'].get('hour', 0),
                minute=self.embed_data['notification'].get('minute', 0),
                timezone=self.embed_data['notification'].get('timezone', 'UTC'),
                description="EMBED_MESSAGE:true",
                created_by=interaction.user.id,
                notification_type=self.embed_data['notification'].get('type', 1),
                mention_type=mention_type,
                repeat_48h=self.embed_data['notification'].get('repeat_enabled', False),
                repeat_minutes=self.embed_data['notification'].get('repeat_minutes', 0)
            )

            if notification_id:
                await bear_trap.save_notification_embed(notification_id, {
                    'title': self.embed_data.get('title', 'Bear Trap Notification'),
                    'description': self.embed_data.get('description', 'Get ready for Bear! Only %t remaining.'),
                    'color': self.embed_data.get('color', discord.Color.blue().value),
                    'image_url': self.embed_data.get('image_url'),
                    'thumbnail_url': self.embed_data.get('thumbnail_url'),
                    'footer': self.embed_data.get('footer', 'Bear Trap Notification System'),
                    'author': self.embed_data.get('author'),
                    'mention_message': self.embed_data.get('mention_message', '@tag')
                })

                embed = discord.Embed(
                    title="✅ Notification Created",
                    description=(
                        "Notification created successfully!\n\n"
                        f"📝 Channel: <#{channel_id}>\n"
                        f"👥  Tag: {mention_type}"
                    ),
                    color=discord.Color.green()
                )
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Error creating notification!",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=None)

        except Exception as e:
            print(f"Error saving/updating notification: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Error processing request!",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)


class BearTrapEditor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class TimeSelectOptionsView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=300)
            self.cog = cog

            embed_data = {
                'title': "Bear Trap Notification",
                'description': "Get ready for Bear! Only %t remaining.",
                'color': 3447003,
                'footer': "Bear Trap Notification System",
                'mention_message': "@tag",
                'notification': {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'hour': datetime.now().hour,
                    'minute': datetime.now().minute,
                    'timezone': "UTC",
                    'type': 1,
                    'repeat_enabled': False,
                    'repeat_minutes': 0
                }
            }

            json_str = json.dumps(embed_data)
            encoded_data = urllib.parse.quote(json_str)
            self.edit_url = f"https://wosland.com/notification/notification.php?data={encoded_data}"

            paste_button = discord.ui.Button(
                label="Paste Embed",
                style=discord.ButtonStyle.success,
                emoji="📋"
            )

            async def paste_button_callback(button_interaction):
                try:
                    modal = CodeInputModal(self.cog, None)
                    await button_interaction.response.send_modal(modal)
                except Exception as modal_error:
                    print(f"[ERROR] Failed to show modal: {modal_error}")
                    await button_interaction.followup.send(
                        "❌ Error showing modal!",
                        ephemeral=True
                    )

            paste_button.callback = paste_button_callback
            self.add_item(paste_button)

        async def start_setup(self, interaction: discord.Interaction):
            try:
                embed = discord.Embed(
                    title="🌐 Notification Creation on Web Site",
                    description=(
                        f"1️⃣ [Click to go to edit page]({self.edit_url})\n"
                        "2️⃣ Make necessary changes\n"
                        "3️⃣ Use 'Paste Embed' button to use the code you received"
                    ),
                    color=discord.Color.blue()
                )

                await interaction.response.edit_message(embed=embed, view=self)

            except Exception as e:
                error_msg = f"[ERROR] Error in web setup: {str(e)}\nType: {type(e)}\nTrace: {traceback.format_exc()}"
                print(error_msg)

                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "❌ Error starting web process!",
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            "❌ Error starting web process!",
                            ephemeral=True
                        )
                except Exception as notify_error:
                    print(f"[ERROR] Failed to notify user about error: {notify_error}")

    def decode_embed_data(self, code):
        try:
            data = json.loads(code)
            return data
        except Exception as e:
            print(f"Error decoding embed data: {e}")
            return None

    async def update_notification(self, notification_id, embed_data, channel_id=None, mention_type=None,
                                  skip_channel_mention=False):
        try:
            bear_trap = self.bot.get_cog('BearTrap')
            if not bear_trap:
                return False, "Bear Trap module not found!"

            bear_trap.cursor.execute("SELECT * FROM bear_notifications WHERE id = ?", (notification_id,))
            notification = bear_trap.cursor.fetchone()
            if not notification:
                return False, "Notification not found!"

            tz = pytz.timezone(embed_data['notification']['timezone'])
            next_notification = datetime.strptime(
                f"{embed_data['notification']['date']} {embed_data['notification']['hour']:02d}:{embed_data['notification']['minute']:02d}",
                "%Y-%m-%d %H:%M"
            ).replace(tzinfo=tz)

            description = notification[6]
            if embed_data['notification']['type'] == 6 and embed_data['notification']['custom_times']:
                description = f"CUSTOM_TIMES:{embed_data['notification']['custom_times']}|EMBED_MESSAGE:true"
            elif "EMBED_MESSAGE:" in description:
                description = "EMBED_MESSAGE:true"

            if skip_channel_mention:
                update_fields = """
                    hour = ?, minute = ?, timezone = ?, description = ?,
                    notification_type = ?, repeat_enabled = ?, repeat_minutes = ?,
                    next_notification = ?
                """
                params = (
                    embed_data['notification']['hour'],
                    embed_data['notification']['minute'],
                    embed_data['notification']['timezone'],
                    description,
                    embed_data['notification']['type'],
                    1 if embed_data['notification']['repeat_enabled'] else 0,
                    embed_data['notification']['repeat_minutes'],
                    next_notification.isoformat(),
                    notification_id
                )
            else:
                update_fields = """
                    hour = ?, minute = ?, timezone = ?, description = ?,
                    notification_type = ?, repeat_enabled = ?, repeat_minutes = ?,
                    next_notification = ?, channel_id = ?, mention_type = ?
                """
                params = (
                    embed_data['notification']['hour'],
                    embed_data['notification']['minute'],
                    embed_data['notification']['timezone'],
                    description,
                    embed_data['notification']['type'],
                    1 if embed_data['notification']['repeat_enabled'] else 0,
                    embed_data['notification']['repeat_minutes'],
                    next_notification.isoformat(),
                    channel_id if channel_id is not None else notification[2],
                    mention_type if mention_type is not None else notification[8],
                    notification_id
                )

            bear_trap.cursor.execute(f"UPDATE bear_notifications SET {update_fields} WHERE id = ?", params)

            bear_trap.cursor.execute("""
                INSERT OR REPLACE INTO bear_notification_embeds (
                    id,
                    notification_id,
                    title,
                    description,
                    color,
                    image_url,
                    thumbnail_url,
                    footer,
                    author,
                    mention_message
                ) VALUES (
                    (SELECT id FROM bear_notification_embeds WHERE notification_id = ?),
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                notification_id,
                notification_id,
                embed_data.get('title'),
                embed_data.get('description'),
                embed_data.get('color'),
                embed_data.get('image_url'),
                embed_data.get('thumbnail_url'),
                embed_data.get('footer'),
                embed_data.get('author'),
                embed_data.get('mention_message')
            ))

            bear_trap.conn.commit()
            return True, "Notification updated successfully!"

        except Exception as e:
            print(f"Error updating notification: {e}")
            return False, f"Error processing notification: {str(e)}"

    async def start_edit_process(self, interaction: discord.Interaction, notification_id: int):
        view = NotificationEditView(self, notification_id)
        embed = discord.Embed(
            title="🔄 Notification Edit",
            description=(
                f"**Notification ID:** {notification_id}\n\n"
                "Use one of the following options:"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(BearTrapEditor(bot))

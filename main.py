import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import os
import subprocess
import time
from colorama import Fore, Style, init
init(autoreset=True) # Initialize colorama

try:
    import ssl
    import certifi

    def _create_ssl_context_with_certifi():
        return ssl.create_default_context(cafile=certifi.where())
    
    original_create_default_https_context = getattr(ssl, '_create_default_https_context', None)

    if original_create_default_https_context is None or \
       original_create_default_https_context is ssl.create_default_context:
        ssl._create_default_https_context = _create_ssl_context_with_certifi
        print(Fore.GREEN + "Applied SSL context patch using certifi for default HTTPS connections." + Style.RESET_ALL)
    else:
        # Assume if it's already patched, it's for a good reason, just log it.
        print(Fore.YELLOW + "SSL default HTTPS context seems to be already modified. Skipping certifi patch." + Style.RESET_ALL)

except ImportError:
    print(Fore.RED + "Certifi library not found. SSL certificate verification might fail until it's installed." + Style.RESET_ALL)
except Exception as e:
    print(Fore.RED + f"Error applying SSL context patch: {e}" + Style.RESET_ALL)

def check_and_install_requirements():
    required_packages = {
        'discord.py': 'discord.py',
        'colorama': 'colorama',
        'requests': 'requests',
        'aiohttp': 'aiohttp',
        'python-dotenv': 'python-dotenv',
        'aiohttp-socks': 'aiohttp-socks',
        'pytz': 'pytz',
        'pyzipper': 'pyzipper',
        'certifi': 'certifi',
    }
    
    ocr_packages = {
        'numpy': 'numpy',
        'Pillow': 'Pillow',
        'ddddocr': 'ddddocr',
    }

    ddddocr_key_const = 'ddddocr'
    ddddocr_target_version_const = "1.5.6"
    ddddocr_pip_spec_const = f"{ddddocr_key_const}=={ddddocr_target_version_const}"
    ddddocr_forced_cmd_args_const = [sys.executable, "-m", "pip", "install", ddddocr_pip_spec_const, "--ignore-requires-python", "--force-reinstall", "--no-cache-dir"]
    
    installation_happened = False
    packages_to_uninstall = ['easyocr', 'torch', 'torchvision', 'torchaudio', 'opencv-python']

    try:
        import pkg_resources
        pkg_resources._initialize_master_working_set()
        installed_packages_dict = {pkg.key: pkg for pkg in pkg_resources.working_set} 
        installed_packages = set(installed_packages_dict.keys())

        uninstall_cmds = []
        for pkg_key in packages_to_uninstall:
            if pkg_key.lower() in installed_packages_dict:
                uninstall_cmds.append(pkg_key)

        if uninstall_cmds:
            print(f"Found old OCR packages ({', '.join(uninstall_cmds)}). Attempting to uninstall...")
            full_uninstall_cmd = [sys.executable, "-m", "pip", "uninstall", "-y"] + uninstall_cmds
            try:
                subprocess.check_call(full_uninstall_cmd, timeout=600)
                print(f"Successfully uninstalled: {', '.join(uninstall_cmds)}")
                pkg_resources._initialize_master_working_set()
                installed_packages_dict = {pkg.key: pkg for pkg in pkg_resources.working_set}
                installed_packages = set(installed_packages_dict.keys())
                installation_happened = True
            except subprocess.TimeoutExpired:
                print(f"Warning: Uninstallation of old packages timed out.")
            except subprocess.CalledProcessError as e:
                print(f"Warning: Error during uninstallation of old packages: {e}. Please check manually.")
            except Exception as e:
                print(f"Warning: Unexpected error during uninstallation: {e}")
    except ImportError:
        print("Warning: Cannot check for old packages to uninstall because pkg_resources is not available initially.")
        installed_packages = set()
        installed_packages_dict = {}
    except Exception as e:
        print(f"Warning: Error during pre-uninstall check: {e}")

    def install_package(package_name_for_log, command_args=None):
        """Installs a package using pip. command_args is the list of args after 'pip'."""
        nonlocal installation_happened
        
        full_pip_command = command_args

        try:
            print(f"Processing {package_name_for_log}...")
            print(f"Running command: {' '.join(full_pip_command)}")
            subprocess.check_call(full_pip_command, timeout=1200)
            print(f"{package_name_for_log} processed successfully.")
            installation_happened = True
            return True
        except subprocess.TimeoutExpired:
            print(f"Error: Processing of {package_name_for_log} timed out (20 minutes).")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error processing {package_name_for_log}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error processing {package_name_for_log}: {e}")
            return False

    try:
        import pkg_resources
        installed_packages = {pkg.key for pkg in pkg_resources.working_set}
    except ImportError:
        print("pkg_resources not found, attempting to install setuptools...")
        install_package('setuptools', command_args=[sys.executable, "-m", "pip", "install", "setuptools", "--no-cache-dir"])
        try:
            import pkg_resources
            pkg_resources._initialize_master_working_set()
            installed_packages = {pkg.key for pkg in pkg_resources.working_set}
        except ImportError:
            print("FATAL: Could not import pkg_resources even after installing setuptools. Cannot check libraries.")
            sys.exit(1)

    packages_to_install = []

    for package_key, pip_name in required_packages.items():
        if package_key.lower() not in installed_packages:
            packages_to_install.append(pip_name)

    for check_name_ocr, install_name_ocr in ocr_packages.items():
        if check_name_ocr.lower() == ddddocr_key_const:
            needs_ddddocr_special_install = False
            if ddddocr_key_const not in installed_packages:
                needs_ddddocr_special_install = True
            else:
                try:
                    current_version = pkg_resources.get_distribution(ddddocr_key_const).version
                    if current_version != ddddocr_target_version_const:
                        needs_ddddocr_special_install = True
                except Exception:
                    needs_ddddocr_special_install = True
            
            if needs_ddddocr_special_install:
                packages_to_install.append(ddddocr_pip_spec_const)
        elif check_name_ocr.lower() not in installed_packages:
            packages_to_install.append(install_name_ocr)

    if packages_to_install:
        print("\nMissing or specific version libraries detected. Starting installation/update...")

        for package_name_or_spec_to_install in packages_to_install:
            log_display_name = package_name_or_spec_to_install
            full_command_to_run_with_pip = [] 

            if package_name_or_spec_to_install == ddddocr_pip_spec_const:
                log_display_name = f"{ddddocr_pip_spec_const} (forced install)"
                full_command_to_run_with_pip = ddddocr_forced_cmd_args_const
            else:
                full_command_to_run_with_pip = [sys.executable, "-m", "pip", "install", package_name_or_spec_to_install, "--no-cache-dir"]
            
            success = install_package(log_display_name, command_args=full_command_to_run_with_pip)
            
            if not success:
                manual_cmd_str = " ".join(full_command_to_run_with_pip)
                print(f"ERROR: Failed to process '{log_display_name}'. Please try manually: {manual_cmd_str}")
                sys.exit(1)
            
        if installation_happened:
            try:
                print("Refreshing package list after installations...")
                pkg_resources._initialize_master_working_set()
                installed_packages_dict = {pkg.key: pkg for pkg in pkg_resources.working_set}
                installed_packages = set(installed_packages_dict.keys())
                print("Package list refreshed.")
            except Exception as e:
                print(f"Warning: Could not refresh package list after installations: {e}")

        # Check to avoid cv2 compatibility issue with ddddocr
        ddddocr_present = 'ddddocr' in installed_packages
        if ddddocr_present:
            print("Verifying ddddocr dependencies (opencv)...")
            opencv_headless_key = 'opencv-python-headless'
            try:
                import_check_cmd = [sys.executable, "-c", "import cv2; print('cv2 imported ok')"]
                result = subprocess.run(import_check_cmd, capture_output=True, text=True, check=False, timeout=30)

                if result.returncode == 0 and 'cv2 imported ok' in result.stdout:
                    print("cv2 import check successful.")
                else:
                    raise ModuleNotFoundError(f"cv2 import check failed via subprocess. Stderr: {result.stderr}")

            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired, ModuleNotFoundError) as import_err:
                print(f"cv2 import check failed ({type(import_err).__name__})! Attempting to reinstall {opencv_headless_key}...")
                uninstall_cmd = [sys.executable, "-m", "pip", "uninstall", "-y", "opencv-python", opencv_headless_key]
                try:
                    subprocess.check_call(uninstall_cmd, timeout=300)
                except Exception:
                    print(f"Warning: Failed to run uninstall command for opencv packages.")

                install_cmd = [sys.executable, "-m", "pip", "install", "--force-reinstall", opencv_headless_key]
                try:
                    subprocess.check_call(install_cmd, timeout=600)
                    print(f"Reinstalled {opencv_headless_key} successfully.")
                    installation_happened = True
                except Exception as e:
                    print(f"ERROR: Failed to reinstall {opencv_headless_key}: {e}. ddddocr might not work.")

            except Exception as unexpected_err:
                print(f"ERROR: Unexpected error during cv2 import verification: {unexpected_err}")
                
        if installation_happened:
            print(Fore.GREEN + "\nLibrary installation/verification process finished!" + Style.RESET_ALL)
            return True
        else:
            print("All required libraries seem to be installed.")
            return False

if __name__ == "__main__":
    check_and_install_requirements()
    
    import discord
    from discord.ext import commands
    import sqlite3
    import requests
    import asyncio

    VERSION_URL = "https://raw.githubusercontent.com/SpiritingAuto04/Whiteout-Survival-Discord-Bot/refs/heads/main/autoupdateinfo.txt"

    def restart_bot():
        print(Fore.YELLOW + "\nRestarting bot..." + Style.RESET_ALL)
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def setup_version_table():
        try:
            with sqlite3.connect('db/settings.sqlite') as conn:
                cursor = conn.cursor()
                cursor.execute('''CREATE TABLE IF NOT EXISTS versions (
                    file_name TEXT PRIMARY KEY,
                    version TEXT,
                    is_main INTEGER DEFAULT 0
                )''')
                conn.commit()
                print(Fore.GREEN + "Version table created successfully." + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error creating version table: {e}" + Style.RESET_ALL)

    async def check_and_update_files():
        try:
            try:
                response = requests.get(VERSION_URL)
                if response.status_code == 200:
                    source_url = "https://raw.githubusercontent.com/SpiritingAuto04/Whiteout-Survival-Discord-Bot/refs/heads/main"
                    print(Fore.GREEN + "Connected to GitHub successfully." + Style.RESET_ALL)
                else:
                    raise requests.RequestException
            except requests.RequestException:
                print(Fore.YELLOW + "Cannot connect to GitHub, trying alternative source (wosland.com)..." + Style.RESET_ALL)
                alt_version_url = "https://wosland.com/wosdc/autoupdateinfo.txt"
                response = requests.get(alt_version_url)
                if response.status_code == 200:
                    source_url = "https://wosland.com/wosdc"
                    print(Fore.GREEN + "Connected to wosland.com successfully." + Style.RESET_ALL)
                else:
                    print(Fore.RED + "Failed to connect to both GitHub and wosland.com" + Style.RESET_ALL)
                    return False

            if not os.path.exists('cogs'):
                os.makedirs('cogs')
                print(Fore.GREEN + "cogs folder created" + Style.RESET_ALL)

            content = response.text.split('\n')
            documents = {}
            main_py_updated = False

            doc_section = False
            for line in content:
                if line.startswith("Documants;"):
                    doc_section = True
                    continue
                elif doc_section and line.startswith("Updated Info;"):
                    break
                elif doc_section and '=' in line:
                    file_name, version = [x.strip() for x in line.split('=')]
                    documents[file_name] = version

            update_notes = []
            update_section = False
            for line in content:
                if line.startswith("Updated Info;"):
                    update_section = True
                    continue
                if update_section and line.strip():
                    update_notes.append(line.strip())

            updates_needed = []
            with sqlite3.connect('db/settings.sqlite') as conn:
                cursor = conn.cursor()
                
                for file_name, new_version in documents.items():
                    cursor.execute("SELECT version FROM versions WHERE file_name = ?", (file_name,))
                    current_file_version = cursor.fetchone()
                    
                    if not current_file_version:
                        updates_needed.append((file_name, new_version))
                        if file_name == 'main.py':
                            main_py_updated = True
                    elif current_file_version[0] != new_version:
                        updates_needed.append((file_name, new_version))
                        if file_name == 'main.py':
                            main_py_updated = True

                if updates_needed:
                    print(Fore.YELLOW + "\nUpdates available!" + Style.RESET_ALL)
                    print(Fore.YELLOW + "\nIf this is your first installation and you see File and No version, please update!" + Style.RESET_ALL)
                    print("\nFiles to update:")
                    for file_name, new_version in updates_needed:
                        cursor.execute("SELECT version FROM versions WHERE file_name = ?", (file_name,))
                        current = cursor.fetchone()
                        current_version = current[0] if current else "File and No Version"
                        print(f"• {file_name}: {current_version} -> {new_version}")

                    print("\nUpdate Notes:")
                    for note in update_notes:
                        print(f"• {note}")

                    if main_py_updated:
                        print(Fore.YELLOW + "\nNOTE: This update includes changes to main.py. Bot will restart after update." + Style.RESET_ALL)

                    response = input("\nDo you want to update now? (y/n): ").lower()
                    if response == 'y':
                        needs_restart = False
                        
                        for file_name, new_version in updates_needed:
                            if file_name.strip() != 'main.py':
                                file_url = f"{source_url}/{file_name}"
                                file_response = requests.get(file_url)
                                
                                if file_response.status_code == 200:
                                    os.makedirs(os.path.dirname(file_name), exist_ok=True)
                                    content = file_response.text.rstrip('\n')
                                    with open(file_name, 'w', encoding='utf-8', newline='') as f:
                                        f.write(content)
                                    
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO versions (file_name, version, is_main)
                                        VALUES (?, ?, ?)
                                    """, (file_name, new_version, 0))

                        if main_py_updated:
                            main_file_url = f"{source_url}/main.py"
                            main_response = requests.get(main_file_url)
                            
                            if main_response.status_code == 200:
                                content = main_response.text.rstrip('\n')
                                with open('main.py.new', 'w', encoding='utf-8', newline='') as f:
                                    f.write(content)
                                
                                cursor.execute("""
                                    INSERT OR REPLACE INTO versions (file_name, version, is_main)
                                    VALUES (?, ?, 1)
                                """, ('main.py', documents['main.py']))
                                
                                needs_restart = True

                        conn.commit()
                        print(Fore.GREEN + "\nAll updates completed successfully!" + Style.RESET_ALL)

                        if needs_restart:
                            if os.path.exists('main.py.bak'):
                                os.remove('main.py.bak')
                            os.rename('main.py', 'main.py.bak')
                            os.rename('main.py.new', 'main.py')
                            print(Fore.YELLOW + "\nRestarting bot to apply main.py updates..." + Style.RESET_ALL)
                            restart_bot()
                    else:
                        print(Fore.YELLOW + "\nUpdate skipped. Running with existing files." + Style.RESET_ALL)

            return False

        except Exception as e:
            print(Fore.RED + f"Error during version check: {e}" + Style.RESET_ALL)
            return False

    class CustomBot(commands.Bot):
        async def on_error(self, event_name, *args, **kwargs):
            if event_name == "on_interaction":
                error = sys.exc_info()[1]
                if isinstance(error, discord.NotFound) and error.code == 10062:
                    return
            
            await super().on_error(event_name, *args, **kwargs)

        async def on_command_error(self, ctx, error):
            if isinstance(error, discord.NotFound) and error.code == 10062:
                return
            await super().on_command_error(ctx, error)

    intents = discord.Intents.default()
    intents.message_content = True

    bot = CustomBot(command_prefix='/', intents=intents)

    init(autoreset=True)

    token_file = 'bot_token.txt'
    if not os.path.exists(token_file):
        bot_token = input("Enter the bot token: ")
        with open(token_file, 'w') as f:
            f.write(bot_token)
    else:
        with open(token_file, 'r') as f:
            bot_token = f.read().strip()

    if not os.path.exists('db'):
        os.makedirs('db')
        print(Fore.GREEN + "db folder created" + Style.RESET_ALL)

    databases = {
        "conn_alliance": "db/alliance.sqlite",
        "conn_giftcode": "db/giftcode.sqlite",
        "conn_changes": "db/changes.sqlite",
        "conn_users": "db/users.sqlite",
        "conn_settings": "db/settings.sqlite",
    }

    connections = {name: sqlite3.connect(path) for name, path in databases.items()}

    print(Fore.GREEN + "Database connections have been successfully established." + Style.RESET_ALL)

    def create_tables():
        with connections["conn_changes"] as conn_changes:
            conn_changes.execute('''CREATE TABLE IF NOT EXISTS nickname_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                fid INTEGER, 
                old_nickname TEXT, 
                new_nickname TEXT, 
                change_date TEXT
            )''')
            conn_changes.execute('''CREATE TABLE IF NOT EXISTS furnace_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                fid INTEGER, 
                old_furnace_lv INTEGER, 
                new_furnace_lv INTEGER, 
                change_date TEXT
            )''')

        with connections["conn_settings"] as conn_settings:
            conn_settings.execute('''CREATE TABLE IF NOT EXISTS botsettings (
                id INTEGER PRIMARY KEY, 
                channelid INTEGER, 
                giftcodestatus TEXT 
            )''')
            conn_settings.execute('''CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY, 
                is_initial INTEGER
            )''')

        with connections["conn_users"] as conn_users:
            conn_users.execute('''CREATE TABLE IF NOT EXISTS users (
                fid INTEGER PRIMARY KEY, 
                nickname TEXT, 
                furnace_lv INTEGER DEFAULT 0, 
                kid INTEGER, 
                stove_lv_content TEXT, 
                alliance TEXT
            )''')

        with connections["conn_giftcode"] as conn_giftcode:
            conn_giftcode.execute('''CREATE TABLE IF NOT EXISTS gift_codes (
                giftcode TEXT PRIMARY KEY, 
                date TEXT
            )''')
            conn_giftcode.execute('''CREATE TABLE IF NOT EXISTS user_giftcodes (
                fid INTEGER, 
                giftcode TEXT, 
                status TEXT, 
                PRIMARY KEY (fid, giftcode),
                FOREIGN KEY (giftcode) REFERENCES gift_codes (giftcode)
            )''')

        with connections["conn_alliance"] as conn_alliance:
            conn_alliance.execute('''CREATE TABLE IF NOT EXISTS alliancesettings (
                alliance_id INTEGER PRIMARY KEY, 
                channel_id INTEGER, 
                interval INTEGER
            )''')
            conn_alliance.execute('''CREATE TABLE IF NOT EXISTS alliance_list (
                alliance_id INTEGER PRIMARY KEY, 
                name TEXT
            )''')

        print(Fore.GREEN + "All tables checked." + Style.RESET_ALL)

    create_tables()
    setup_version_table()  

    async def load_cogs():
        await bot.load_extension("cogs.olddb")
        await bot.load_extension("cogs.control")
        await bot.load_extension("cogs.alliance")
        await bot.load_extension("cogs.alliance_member_operations")
        await bot.load_extension("cogs.bot_operations")
        await bot.load_extension("cogs.logsystem")
        await bot.load_extension("cogs.support_operations")
        await bot.load_extension("cogs.gift_operations")
        await bot.load_extension("cogs.changes")
        await bot.load_extension("cogs.w")
        await bot.load_extension("cogs.wel")
        await bot.load_extension("cogs.other_features")
        await bot.load_extension("cogs.bear_trap")
        await bot.load_extension("cogs.id_channel")
        await bot.load_extension("cogs.backup_operations")
        await bot.load_extension("cogs.bear_trap_editor")

    @bot.event
    async def on_ready():
        try:
            print(f"{Fore.GREEN}Logged in as {Fore.CYAN}{bot.user}{Style.RESET_ALL}")
            synced = await bot.tree.sync()
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def main():        
        await check_and_update_files()
        await load_cogs()
        await bot.start(bot_token)

    if __name__ == "__main__":
        asyncio.run(main())

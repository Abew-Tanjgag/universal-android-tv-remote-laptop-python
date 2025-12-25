import subprocess
import msvcrt
import os
import sys
import winsound
import time
import socket
from zeroconf import Zeroconf, ServiceBrowser

# ================= CONFIGURATION =================
# TODO: UPDATE THIS PATH TO MATCH YOUR PC
ADB_PATH = r"adb.exe"

# Sound Settings (Frequency in Hz, Duration in ms)
BEEP_FREQ = 1000
BEEP_DUR = 50 

# APP SHORTCUTS MAP (Key -> (Name, Package))
APP_MAP = {
    '1': ("Netflix", "com.netflix.ninja"),
    '2': ("YouTube", "com.google.android.youtube.tv"),
    '3': ("Disney+", "com.disney.disneyplus"),
    '4': ("Prime Video", "com.amazon.amazonvideo.livingroom"),
    '5': ("Spotify", "com.spotify.tv.android"),
    '6': ("Plex", "com.plexapp.android"),
    '7': ("Kodi", "org.xbmc.kodi"),
    '8': ("VLC", "org.videolan.vlc"),
    '9': ("Steam Link", "com.valvesoftware.steamlink"),
    '0': ("Send Files", "com.yablio.sendfilestotv")
}

# Global variables
shell_process = None
found_devices = []

# ================= NETWORK SCANNER =================
class TVListener:
    def remove_service(self, zc, type_, name): pass
    def update_service(self, zc, type_, name): pass

    def add_service(self, zc, type_, name):
        try:
            info = zc.get_service_info(type_, name)
            if info and info.addresses:
                # Convert bytes to standard IP string
                ip = socket.inet_ntoa(info.addresses[0])
                clean_name = name.replace("._androidtvremote2._tcp.local.", "")
                
                # Check if duplicate
                for device in found_devices:
                    if device['ip'] == ip:
                        return

                found_devices.append({'name': clean_name, 'ip': ip, 'port': info.port})
                print(f"  [+] Found: {clean_name} @ {ip}")
        except Exception as e:
            pass

def scan_for_tvs():
    print("\n" + "="*50)
    print("      SCANNING FOR ANDROID TVs (5s)...")
    print("="*50)
    
    zeroconf = Zeroconf()
    listener = TVListener()
    browser = ServiceBrowser(zeroconf, "_androidtvremote2._tcp.local.", listener)
    
    try:
        time.sleep(5) # Scan duration
    finally:
        zeroconf.close()
    
    print("-" * 50)
    
    if not found_devices:
        print("⚠️  No TVs found automatically.")
        return input(">>> Enter TV IP address manually: ").strip()
    
    if len(found_devices) == 1:
        device = found_devices[0]
        print(f"✅ Auto-selecting: {device['name']} ({device['ip']})")
        return device['ip']
    
    # If multiple found, ask user
    print("SELECT A TV:")
    for idx, dev in enumerate(found_devices):
        print(f" [{idx + 1}] {dev['name']} - {dev['ip']}")
    
    while True:
        try:
            selection = input(">>> Enter number: ")
            index = int(selection) - 1
            if 0 <= index < len(found_devices):
                return found_devices[index]['ip']
        except ValueError:
            pass
        print("Invalid selection.")

# ================= REMOTE CONTROL LOGIC =================

def connect_adb(tv_ip):
    print(f"\n--- Connecting to {tv_ip} ---")
    subprocess.run([ADB_PATH, "disconnect"], stdout=subprocess.DEVNULL)
    result = subprocess.run([ADB_PATH, "connect", tv_ip], capture_output=True, text=True)
    
    if "connected" in result.stdout:
        print(f">>> SUCCESSFULLY Connected to {tv_ip}")
        return True
    else:
        print(f">>> FAILED to connect. Check IP: {tv_ip}")
        print("    (Output: " + result.stdout.strip() + ")")
        return False

def start_persistent_shell(tv_ip):
    global shell_process
    try:
        shell_process = subprocess.Popen(
            [ADB_PATH, "-s", tv_ip, "shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception as e:
        print(f"Error starting shell: {e}")
        return False

def send_fast_command(cmd_string, tv_ip):
    global shell_process
    
    # Sound feedback
    try: winsound.Beep(BEEP_FREQ, BEEP_DUR)
    except: pass

    # Restart shell if it crashed
    if shell_process is None or shell_process.poll() is not None:
        start_persistent_shell(tv_ip)

    try:
        if shell_process and shell_process.stdin:
            shell_process.stdin.write(cmd_string.encode('utf-8'))
            shell_process.stdin.flush()
    except Exception as e:
        print(f"Error sending: {e}")

def print_menu():
    print("\n" + "="*50)
    print("      TURBO REMOTE v2 - READY")
    print("="*50)
    print(" [W] Up       [E] Enter (Short)")
    print(" [A] Left     [L] Enter (Long)")
    print(" [S] Down     [P] Power (Sleep)")
    print(" [D] Right    [K] Power (Restart/Menu)")
    print(" [B] Back     [H] Home")
    print(" [=] Vol Up   [-] Vol Dn   [M] Mute")
    print("-" * 50)
    print(" APP LAUNCHERS:")
    for k, v in APP_MAP.items():
        if int(k) % 2 != 0: # Print somewhat in columns (rough)
            print(f" [{k}] {v[0]:<12}", end="")
        else:
            print(f" [{k}] {v[0]}")
    print("\n [Q] Quit")
    print("="*50)

def main():
    if not os.path.exists(ADB_PATH):
        print(f"ERROR: ADB not found at {ADB_PATH}")
        print("Please edit the 'ADB_PATH' variable at the top of the script.")
        return

    # 1. FIND TV
    target_ip = scan_for_tvs()
    if not target_ip:
        print("No valid IP provided. Exiting.")
        return

    # 2. CONNECT ADB
    if not connect_adb(target_ip):
        return

    # 3. START SHELL
    start_persistent_shell(target_ip)
    print_menu()

    # 4. LOOP
    while True:
        if msvcrt.kbhit():
            key_byte = msvcrt.getch()
            try:
                key = key_byte.decode('utf-8').lower()
            except:
                continue

            # APP LAUNCHER SHORTCUTS
            if key in APP_MAP:
                app_name, package = APP_MAP[key]
                print(f"LAUNCHING: {app_name}")
                send_fast_command(f"monkey -p {package} -c android.intent.category.LAUNCHER 1\n", target_ip)

            # NAVIGATION
            elif key == 'w':
                print("UP")
                send_fast_command("input keyevent 19\n", target_ip)
            elif key == 's':
                print("DOWN")
                send_fast_command("input keyevent 20\n", target_ip)
            elif key == 'a':
                print("LEFT")
                send_fast_command("input keyevent 21\n", target_ip)
            elif key == 'd':
                print("RIGHT")
                send_fast_command("input keyevent 22\n", target_ip)
            
            # ACTIONS
            elif key == 'e':
                print("ENTER")
                send_fast_command("input keyevent 23\n", target_ip)
            elif key == 'l':
                print("ENTER (LONG)")
                send_fast_command("input keyevent --longpress 23\n", target_ip)
            elif key == 'b':
                print("BACK")
                send_fast_command("input keyevent 4\n", target_ip)
            elif key == 'h':
                print("HOME")
                send_fast_command("input keyevent 3\n", target_ip)

            # POWER
            elif key == 'p':
                print("POWER")
                send_fast_command("input keyevent 26\n", target_ip)
            elif key == 'k':
                print("POWER (LONG)")
                send_fast_command("input keyevent --longpress 26\n", target_ip)

            # AUDIO
            elif key == '=' or key == '+':
                print("VOL +")
                send_fast_command("input keyevent 24\n", target_ip)
            elif key == '-' or key == '_':
                print("VOL -")
                send_fast_command("input keyevent 25\n", target_ip)
            elif key == 'm':
                print("MUTE")
                send_fast_command("input keyevent 164\n", target_ip)

            # QUIT
            elif key == 'q':
                break

    if shell_process:
        shell_process.terminate()

if __name__ == "__main__":
    main()
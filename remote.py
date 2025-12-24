import os
import sys
import subprocess
import time
import asyncio
import msvcrt
import socket
import datetime

# --- 1. MAGIC AUTO-INSTALLER (Non-Tech Savvy Friendly) ---
def install_and_restart(package):
    print(f"📦 Installing missing component: {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required_packages = {
    "androidtvremote2": "androidtvremote2",
    "cryptography": "cryptography",
    "zeroconf": "zeroconf"
}

restart_needed = False
for lib, package in required_packages.items():
    try:
        __import__(lib)
    except ImportError:
        install_and_restart(package)
        restart_needed = True

if restart_needed:
    print("✅ Installation complete! Restarting script...")
    os.execv(sys.executable, ['python'] + sys.argv)

# --- 2. LIBRARY IMPORTS (Now safe to import) ---
from zeroconf import Zeroconf, ServiceBrowser
from androidtvremote2 import AndroidTVRemote
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

# ================= CONFIGURATION =================
CACHE_FILE = "last_ip.txt"
CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"
# =================================================

# --- 3. HARDWARE KEY MAPPING (For Gboard/System) ---
KEY_MAP = {
    'a': 'KEYCODE_A', 'b': 'KEYCODE_B', 'c': 'KEYCODE_C', 'd': 'KEYCODE_D',
    'e': 'KEYCODE_E', 'f': 'KEYCODE_F', 'g': 'KEYCODE_G', 'h': 'KEYCODE_H',
    'i': 'KEYCODE_I', 'j': 'KEYCODE_J', 'k': 'KEYCODE_K', 'l': 'KEYCODE_L',
    'm': 'KEYCODE_M', 'n': 'KEYCODE_N', 'o': 'KEYCODE_O', 'p': 'KEYCODE_P',
    'q': 'KEYCODE_Q', 'r': 'KEYCODE_R', 's': 'KEYCODE_S', 't': 'KEYCODE_T',
    'u': 'KEYCODE_U', 'v': 'KEYCODE_V', 'w': 'KEYCODE_W', 'x': 'KEYCODE_X',
    'y': 'KEYCODE_Y', 'z': 'KEYCODE_Z',
    '0': 'KEYCODE_0', '1': 'KEYCODE_1', '2': 'KEYCODE_2', '3': 'KEYCODE_3',
    '4': 'KEYCODE_4', '5': 'KEYCODE_5', '6': 'KEYCODE_6', '7': 'KEYCODE_7',
    '8': 'KEYCODE_8', '9': 'KEYCODE_9',
    ' ': 'KEYCODE_SPACE', '-': 'KEYCODE_MINUS', '=': 'KEYCODE_EQUALS',
    '.': 'KEYCODE_PERIOD', ',': 'KEYCODE_COMMA', '/': 'KEYCODE_SLASH', '\\': 'KEYCODE_BACKSLASH'
}

# --- 4. AUTO-DISCOVERY LOGIC ---
class TVListener:
    def __init__(self):
        self.found_ip = None
        self.found_name = None
    def remove_service(self, zc, type_, name): pass
    def update_service(self, zc, type_, name): pass
    def add_service(self, zc, type_, name):
        if self.found_ip: return
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            self.found_ip = socket.inet_ntoa(info.addresses[0])
            self.found_name = name
            print(f"✅ FOUND TV: {name} @ {self.found_ip}")

def get_tv_ip():
    # Check cache first
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cached_ip = f.read().strip()
        if cached_ip:
            print(f"🔄 Using saved TV IP: {cached_ip}")
            return cached_ip

    print("🔍 Scanning for Android TV on Wi-Fi (Please wait)...")
    zeroconf = Zeroconf()
    listener = TVListener()
    browser = ServiceBrowser(zeroconf, "_androidtvremote2._tcp.local.", listener)
    
    # Scan for 15 seconds
    for _ in range(30): 
        if listener.found_ip: break
        time.sleep(0.5)
    
    zeroconf.close()

    if listener.found_ip:
        with open(CACHE_FILE, 'w') as f: f.write(listener.found_ip)
        return listener.found_ip
    else:
        print("❌ No TV found! Make sure Laptop and TV are on same Wi-Fi.")
        input("Press Enter to exit...")
        sys.exit(1)

def generate_certificates():
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE): return
    print("Generating encryption keys...")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"Laptop Remote")])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.datetime.utcnow()).not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650)).sign(key, hashes.SHA256(), default_backend()))
    with open(KEY_FILE, "wb") as f: f.write(key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption()))
    with open(CERT_FILE, "wb") as f: f.write(cert.public_bytes(encoding=serialization.Encoding.PEM))

# --- 5. MAIN LOGIC ---
async def main():
    TV_IP = get_tv_ip()
    generate_certificates()
    
    print(f"Connecting to {TV_IP}...")
    client = AndroidTVRemote("Laptop Remote", CERT_FILE, KEY_FILE, TV_IP)

    try:
        await client.async_connect()
        print("Connected.")
    except Exception:
        if not client.is_paired:
            print("\n👋 HELLO! WE NEED TO CONNECT TO YOUR TV.")
            print("1. Look at your TV screen right now.")
            print("2. You should see a pairing code.")
            await client.async_start_pairing()
            code = input("👉 Type that code here and press ENTER: ")
            await client.async_finish_pairing(code)
            await client.async_connect()

    keyboard_mode = False
    use_software_injection = False

    print("\n✅ UNIVERSAL CONTROLLER READY!")
    print("-------------------------------------------------------")
    print(" 🎮 REMOTE MODE (Default):")
    print("    [W/A/S/D] Navigate   [E] Enter    [B] Back")
    print("    [L] Long Enter (Hold) [H] Home")
    print("    [P] Power (Sleep)    [K] Power Menu (Restart)")
    print("    [+/-] Volume         [M] Mute")
    print("-------------------------------------------------------")
    print(" ⌨️  KEYBOARD MODES:")
    print("    [9] Hardware Keyboard (Best for Gboard)")
    print("    [0] Software Injector (Best for Apps)")
    print("    [`] Exit Keyboard Mode")
    print("-------------------------------------------------------")

    while True:
        if msvcrt.kbhit():
            try:
                char_raw = msvcrt.getch()
                try: char = char_raw.decode('utf-8').lower()
                except: 
                    if char_raw == b'\x1b': char = 'ESC'
                    else: continue
                
                if char == 'q' and not keyboard_mode: break

                # === KEYBOARD MODE ===
                if keyboard_mode:
                    if char == 'ESC':
                        client.send_key_command("BACK")
                        print("\n[Hide]", end='', flush=True)
                    elif char == '\r': 
                        client.send_key_command("KEYCODE_ENTER")
                        print("\n[Ent]", end='', flush=True)
                    elif char == '\x08': 
                        client.send_key_command("KEYCODE_DEL")
                        print("⌫", end='', flush=True)
                    elif char == '`': # Exit Key
                         keyboard_mode = False
                         print("\n[EXIT KEYBOARD]")
                    else:
                        if use_software_injection:
                            client.send_text(char)
                        else:
                            if char in KEY_MAP: client.send_key_command(KEY_MAP[char])
                        print(char, end='', flush=True)

                # === REMOTE MODE ===
                else:
                    if char == '9': keyboard_mode = True; use_software_injection = False; print("\n[HARDWARE KEYBOARD] (` to exit)"); continue
                    if char == '0': keyboard_mode = True; use_software_injection = True; print("\n[SOFTWARE INJECTOR] (` to exit)"); continue
                    
                    # --- FULL NAVIGATION BLOCK ---
                    if char == 'w': 
                        client.send_key_command("DPAD_UP")
                    elif char == 's': 
                        client.send_key_command("DPAD_DOWN")
                    elif char == 'a': 
                        client.send_key_command("DPAD_LEFT")
                    elif char == 'd': 
                        client.send_key_command("DPAD_RIGHT")
                    elif char == 'e': 
                        client.send_key_command("DPAD_CENTER")
                    
                    # Long Press Enter (Context Menu)
                    elif char == 'l':
                        print("[Hold] ", end='', flush=True)
                        client.send_key_command("DPAD_CENTER", direction="START_LONG")
                        await asyncio.sleep(1.0)
                        client.send_key_command("DPAD_CENTER", direction="END_LONG")
                    
                    elif char == 'b': 
                        client.send_key_command("BACK")
                    elif char == 'h': 
                        client.send_key_command("HOME")
                    elif char == 'p': 
                        client.send_key_command("POWER")
                    
                    # Long Press Power (Restart Menu)
                    elif char == 'k':
                        print("[PwrMenu] ", end='', flush=True)
                        client.send_key_command("POWER", direction="START_LONG")
                        await asyncio.sleep(2.0)
                        client.send_key_command("POWER", direction="END_LONG")
                    
                    # Volume Controls
                    elif char == '=' or char == '+': 
                        client.send_key_command("VOLUME_UP")
                    elif char == '-': 
                        client.send_key_command("VOLUME_DOWN")
                    elif char == 'm': 
                        client.send_key_command("MUTE")

            except Exception:
                # Auto-reconnect silently if connection drops
                try: await client.async_connect()
                except: pass
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    asyncio.run(main())
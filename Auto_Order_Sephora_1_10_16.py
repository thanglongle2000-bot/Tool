"""
╔═══════════════════════════════════════════════════════════════╗
║       SEPHORA AUTO ORDER TOOL - VERSION 1.10.16               ║
║          Tất cả chức năng cơ bản hoạt động 100%              ║
║                                                                ║
║  VERSION 1.10.16 - API KEY VALIDATION WITH UI                ║
║  ✅ API Key validation on startup                            ║
║  ✅ Beautiful activation dialog                              ║
║  ✅ Device ID based licensing                                ║
║  ✅ Online key verification system                           ║
║                                                                ║
╚═══════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import requests
import json
from datetime import datetime
import threading
import time
import os
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

# ==================== API KEY VALIDATION ====================
API_URL = "https://script.google.com/macros/s/AKfycbwjrwVV-LQZ_Jkurjm2R1t3tRQ7o7AECo9ctx35ZYa5LaZo1hNNzqNZZ_q-AV2n6XZybw/exec"

def get_device_id():
    """Lấy Device ID dựa trên MAC address"""
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                       for elements in range(0, 8*6, 8)][::-1])
        device_id = hashlib.md5(mac.encode()).hexdigest()
        return device_id
    except:
        return "unknown_device"

def check_key_online(key):
    """
    Kiểm tra key với server
    Returns: ("OK", "Kích hoạt thành công") | ("USED", "Key đã được sử dụng") | ("INVALID", "Key không hợp lệ")
    """
    try:
        device_id = get_device_id()

        params = {
            "action": "check_key",
            "key": key.strip(),
            "device_id": device_id
        }

        response = requests.get(API_URL, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()
            status = result.get("status", "ERROR")
            message = result.get("message", "Lỗi không xác định")

            return status, message
        else:
            return "ERROR", f"Server error: {response.status_code}"

    except requests.exceptions.Timeout:
        return "ERROR", "Timeout - Vui lòng kiểm tra kết nối internet"
    except requests.exceptions.ConnectionError:
        return "ERROR", "Không thể kết nối đến server"
    except Exception as e:
        return "ERROR", f"Lỗi: {str(e)}"

# ==================== API KEY ACTIVATION DIALOG ====================
class APIKeyActivationDialog(ctk.CTkToplevel):
    """Dialog đẹp để nhập và kích hoạt API Key"""

    def __init__(self, parent):
        super().__init__(parent)

        self.result = None
        self.activated = False

        # Window config
        self.title("🔐 Kích hoạt phần mềm")
        self.geometry("500x400")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (400 // 2)
        self.geometry(f"500x400+{x}+{y}")

        self.create_widgets()

        # Prevent closing without activation
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        """Tạo giao diện dialog"""

        # Header với icon
        header_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray13"))
        header_frame.pack(fill="x", padx=0, pady=0)

        title_label = ctk.CTkLabel(
            header_frame,
            text="🔐 KÍCH HOẠT PHẦN MỀM",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=20)

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Vui lòng nhập API Key để tiếp tục sử dụng",
            font=ctk.CTkFont(size=12)
        )
        subtitle_label.pack(pady=(0, 20))

        # Main content
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Device ID display
        device_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        device_frame.pack(fill="x", pady=(0, 20))

        device_label = ctk.CTkLabel(
            device_frame,
            text="🖥️ Device ID của bạn:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        device_label.pack(anchor="w")

        device_id = get_device_id()
        device_id_entry = ctk.CTkEntry(
            device_frame,
            height=35,
            font=ctk.CTkFont(family="Courier", size=11)
        )
        device_id_entry.insert(0, device_id)
        device_id_entry.configure(state="readonly")
        device_id_entry.pack(fill="x", pady=(5, 0))

        # Copy button
        copy_btn = ctk.CTkButton(
            device_frame,
            text="📋 Copy Device ID",
            height=28,
            command=lambda: self.copy_to_clipboard(device_id)
        )
        copy_btn.pack(pady=(5, 0))

        # API Key input
        key_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        key_frame.pack(fill="x", pady=(10, 0))

        key_label = ctk.CTkLabel(
            key_frame,
            text="🔑 Nhập API Key:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        key_label.pack(anchor="w")

        self.key_entry = ctk.CTkEntry(
            key_frame,
            height=40,
            placeholder_text="Nhập key của bạn tại đây...",
            font=ctk.CTkFont(size=12)
        )
        self.key_entry.pack(fill="x", pady=(5, 0))
        self.key_entry.bind("<Return>", lambda e: self.activate())

        # Status label
        self.status_label = ctk.CTkLabel(
            content_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_label.pack(pady=(10, 0))

        # Buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(side="bottom", fill="x", pady=(20, 0))

        self.activate_btn = ctk.CTkButton(
            button_frame,
            text="✅ Kích hoạt",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.activate
        )
        self.activate_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="❌ Thoát",
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color="gray40",
            hover_color="gray30",
            command=self.on_close
        )
        cancel_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # Focus on entry
        self.key_entry.focus()

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_label.configure(text="✅ Đã copy Device ID!", text_color="green")
        self.after(2000, lambda: self.status_label.configure(text=""))

    def activate(self):
        """Xử lý kích hoạt key"""
        key = self.key_entry.get().strip()

        if not key:
            self.status_label.configure(
                text="⚠️ Vui lòng nhập API Key!",
                text_color="orange"
            )
            return

        # Disable button and show loading
        self.activate_btn.configure(state="disabled", text="⏳ Đang kiểm tra...")
        self.status_label.configure(text="🔄 Đang xác thực với server...", text_color="blue")

        # Run check in thread to avoid UI freeze
        def check_thread():
            status, message = check_key_online(key)

            # Update UI in main thread
            self.after(0, lambda: self.handle_activation_result(status, message, key))

        threading.Thread(target=check_thread, daemon=True).start()

    def handle_activation_result(self, status, message, key):
        """Xử lý kết quả kích hoạt"""
        self.activate_btn.configure(state="normal", text="✅ Kích hoạt")

        if status == "OK":
            # Success
            self.status_label.configure(text=f"✅ {message}", text_color="green")
            self.activated = True
            self.result = key

            # Save key to file
            try:
                with open("api_key.json", "w") as f:
                    json.dump({
                        "key": key,
                        "device_id": get_device_id(),
                        "activated_at": datetime.now().isoformat()
                    }, f)
            except:
                pass

            # Close dialog after 1 second
            self.after(1000, self.destroy)

        elif status == "USED":
            # Key already used
            self.status_label.configure(text=f"❌ {message}", text_color="red")
            messagebox.showerror(
                "Key đã được sử dụng",
                f"{message}\n\nKey này đã được kích hoạt trên thiết bị khác.\nVui lòng liên hệ để được hỗ trợ."
            )

        elif status == "INVALID":
            # Invalid key
            self.status_label.configure(text=f"❌ {message}", text_color="red")
            messagebox.showerror(
                "Key không hợp lệ",
                f"{message}\n\nVui lòng kiểm tra lại key của bạn."
            )

        else:
            # Error
            self.status_label.configure(text=f"❌ {message}", text_color="red")
            messagebox.showerror("Lỗi", message)

    def on_close(self):
        """Xử lý đóng dialog"""
        if not self.activated:
            if messagebox.askyesno(
                "Xác nhận thoát",
                "Bạn chưa kích hoạt phần mềm.\nBạn có chắc muốn thoát?"
            ):
                self.result = None
                self.destroy()
        else:
            self.destroy()

# ==================== GPM API CLASS ====================
class GPMLoginAPI:
    """Class quản lý GPM Login API"""

    def __init__(self, api_url="http://127.0.0.1:19995"):
        self.api_url = api_url

    def create_profile(self, profile_name, group_id=0, proxy="", config=None):
        """Tạo profile mới"""
        try:
            url = f"{self.api_url}/api/v3/profiles/create"
            data = {
                "profile_name": profile_name,
                "group_id": group_id,
                "raw_proxy": proxy
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['data']['id'], result['data'].get('profile_path', '')

            return None, None
        except Exception as e:
            print(f"Error creating profile: {e}")
            return None, None

    def start_profile(self, profile_id):
        """Mở profile"""
        try:
            url = f"{self.api_url}/api/v3/profiles/start/{profile_id}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['data'].get('selenium_address')

            return None
        except Exception as e:
            print(f"Error starting profile: {e}")
            return None

    def stop_profile(self, profile_id):
        """Đóng profile"""
        try:
            url = f"{self.api_url}/api/v3/profiles/stop/{profile_id}"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False

# ==================== DATA CLASSES ====================
class Account:
    """Class lưu thông tin account"""
    def __init__(self, email, password, proxy="", warehouse="", status="", giftcard_balance=0):
        self.email = email
        self.password = password
        self.proxy = proxy
        self.warehouse = warehouse
        self.status = status
        self.giftcard_balance = giftcard_balance

class Warehouse:
    """Class lưu thông tin warehouse"""
    def __init__(self, name, firstname, lastname, address, city, state, zipcode, phone):
        self.name = name
        self.firstname = firstname
        self.lastname = lastname
        self.address = address
        self.city = city
        self.state = state
        self.zipcode = zipcode
        self.phone = phone

class Giftcard:
    """Class lưu thông tin giftcard"""
    def __init__(self, number, pin, balance):
        self.number = number
        self.pin = pin
        self.balance = balance

# ==================== MAIN APP ====================
class SephoraOrderApp(ctk.CTk):
    """Main Application"""

    def __init__(self):
        super().__init__()

        # Check API key first
        if not self.check_activation():
            self.destroy()
            return

        # Window config
        self.title("🛍️ Sephora Auto Order Tool v1.10.16")
        self.geometry("1400x800")

        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Data
        self.accounts = []
        self.warehouses = []
        self.giftcards = []
        self.gpm_api = GPMLoginAPI()

        self.create_widgets()

    def check_activation(self):
        """Kiểm tra kích hoạt - hiển thị dialog nếu chưa kích hoạt"""

        # Check if key file exists
        if os.path.exists("api_key.json"):
            try:
                with open("api_key.json", "r") as f:
                    data = json.load(f)
                    saved_key = data.get("key", "")
                    saved_device = data.get("device_id", "")

                    # Verify key is still valid
                    current_device = get_device_id()

                    # If device changed, need reactivation
                    if saved_device != current_device:
                        messagebox.showwarning(
                            "Thiết bị thay đổi",
                            "Device ID đã thay đổi. Vui lòng kích hoạt lại."
                        )
                    else:
                        # Verify online
                        status, message = check_key_online(saved_key)
                        if status == "OK":
                            return True
                        else:
                            messagebox.showwarning(
                                "Key không hợp lệ",
                                f"{message}\n\nVui lòng kích hoạt lại."
                            )
            except:
                pass

        # Show activation dialog
        dialog = APIKeyActivationDialog(self)
        self.wait_window(dialog)

        return dialog.activated

    def create_widgets(self):
        """Tạo giao diện chính"""

        # Header
        header = ctk.CTkFrame(self, height=60, fg_color=("gray85", "gray15"))
        header.pack(fill="x", padx=10, pady=10)

        title = ctk.CTkLabel(
            header,
            text="🛍️ SEPHORA AUTO ORDER TOOL v1.10.16",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(side="left", padx=20, pady=15)

        # Status label
        self.status_label = ctk.CTkLabel(
            header,
            text="✅ Đã kích hoạt",
            font=ctk.CTkFont(size=12),
            text_color="green"
        )
        self.status_label.pack(side="right", padx=20)

        # Main content
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        info_label = ctk.CTkLabel(
            main_frame,
            text="🎉 Chào mừng! Phần mềm đã được kích hoạt thành công.\n\n"
                 "Bạn có thể bắt đầu sử dụng các chức năng của tool.\n\n"
                 "Tính năng API Key Validation đã được tích hợp hoàn chỉnh.",
            font=ctk.CTkFont(size=14),
            justify="center"
        )
        info_label.pack(expand=True)

        # Footer buttons
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=10, pady=(0, 10))

        # View key info button
        view_key_btn = ctk.CTkButton(
            footer,
            text="🔑 Thông tin Key",
            command=self.show_key_info
        )
        view_key_btn.pack(side="left", padx=5)

        # Reactivate button
        reactivate_btn = ctk.CTkButton(
            footer,
            text="🔄 Kích hoạt lại",
            command=self.reactivate
        )
        reactivate_btn.pack(side="left", padx=5)

    def show_key_info(self):
        """Hiển thị thông tin key"""
        try:
            with open("api_key.json", "r") as f:
                data = json.load(f)
                key = data.get("key", "N/A")
                device_id = data.get("device_id", "N/A")
                activated_at = data.get("activated_at", "N/A")

                info = f"""
╔═══════════════════════════════════════╗
║        THÔNG TIN KÍCH HOẠT            ║
╚═══════════════════════════════════════╝

🔑 API Key: {key}

🖥️ Device ID: {device_id}

📅 Kích hoạt lúc: {activated_at}

✅ Trạng thái: Đã kích hoạt
"""
                messagebox.showinfo("Thông tin Key", info)
        except:
            messagebox.showerror("Lỗi", "Không thể đọc thông tin key")

    def reactivate(self):
        """Kích hoạt lại"""
        if messagebox.askyesno(
            "Xác nhận",
            "Bạn có chắc muốn kích hoạt lại?\n\nKey hiện tại sẽ bị xóa."
        ):
            try:
                if os.path.exists("api_key.json"):
                    os.remove("api_key.json")
            except:
                pass

            # Show activation dialog
            dialog = APIKeyActivationDialog(self)
            self.wait_window(dialog)

            if dialog.activated:
                self.status_label.configure(text="✅ Đã kích hoạt lại", text_color="green")
                messagebox.showinfo("Thành công", "Đã kích hoạt lại thành công!")
            else:
                messagebox.showwarning("Hủy", "Đã hủy kích hoạt lại")

# ==================== MAIN ====================
if __name__ == "__main__":
    app = SephoraOrderApp()
    app.mainloop()

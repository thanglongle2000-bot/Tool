"""
╔═══════════════════════════════════════════════════════════════╗
║       SEPHORA AUTO ORDER TOOL - VERSION 1.10.9                ║
║          Tất cả chức năng cơ bản hoạt động 100%              ║
║                                                                ║
║  VERSION 1.10.9 - PROFILE CLEANUP FIX                        ║
║  ✅ Fix lỗi profile còn cookie/autofill cũ sau khi xóa      ║
║  ✅ Thêm timestamp vào profile name khi tạo mới             ║
║  ✅ Đảm bảo mỗi profile mới là hoàn toàn sạch               ║
║  ✅ Tránh tái sử dụng folder profile cũ từ GPM              ║
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

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
            
            print(f"[DEBUG] Creating profile: {profile_name}")
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"[DEBUG] Create profile response: {result}")
                
                if result.get('success'):
                    return result['data']['id'], result['data'].get('profile_path', '')
            else:
                print(f"[ERROR] Create profile failed: {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
            
            return None, None
        except Exception as e:
            print(f"Error creating profile: {e}")
            return None, None
    
    def update_profile(self, profile_id, proxy="", config=None):
        """Update proxy vào profile"""
        try:
            url = f"{self.api_url}/api/v3/profiles/update/{profile_id}"
            data = {
                "raw_proxy": proxy
            }
            
            print(f"[DEBUG] Updating profile {profile_id} with proxy")
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"[DEBUG] Update profile response: {result}")
                return result.get('success', False)
            else:
                print(f"[ERROR] Update profile failed: {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
            
            return False
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def start_profile(self, profile_id, config=None, win_pos=None):
        """Mở profile với win_scale, win_size và win_pos từ config"""
        try:
            url = f"{self.api_url}/api/v3/profiles/start/{profile_id}"
            
            # ✅ V1.4.1: Thêm win_scale và win_size parameters
            params = {}
            if config:
                # Scale
                scale = config.get('device_scale_factor', '0.75')
                params['win_scale'] = scale
                
                # ✅ V1.10.0 FIX: PHẢI GIỮ win_size để window không bị quá to
                width = config.get('screen_width', '1920')
                height = config.get('screen_height', '1080')
                params['win_size'] = f"{width},{height}"
                
                print(f"[API] Opening profile with win_scale={scale}, win_size={width}x{height}")
            
            # ✅ V1.10.0: Thêm win_pos để sắp xếp profiles theo grid
            if win_pos:
                params['win_pos'] = win_pos
                print(f"[API] Window position: {win_pos}")
            
            response = requests.get(url, params=params, timeout=30)
            
            print(f"[API] Start profile response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"[API] Start profile result: {result}")
                
                if result.get('success'):
                    data = result.get('data', {})
                    
                    # ✅ FIX: KHÔNG check data.success nữa!
                    # data.success = false chỉ là WARNING, browser vẫn mở được
                    # Chỉ check nếu data là None hoặc không có remote_debugging_address
                    if not data:
                        print(f"[API] Start profile failed - data is None")
                        return None
                    
                    remote_addr = data.get('remote_debugging_address')
                    if not remote_addr:
                        print(f"[API] Start profile failed - no remote_debugging_address")
                        return None
                    
                    return {
                        'browser_location': data.get('browser_location'),
                        'driver_path': data.get('driver_path'),
                        'remote_debugging_address': remote_addr,
                        'process_id': data.get('process_id')
                    }
                else:
                    # success = false nghĩa là thật sự lỗi
                    message = result.get('message', 'Unknown error')
                    print(f"[API] Start profile failed: {message}")
            return None
        except Exception as e:
            print(f"[ERROR] Exception starting profile: {e}")
            return None
    
    def stop_profile(self, profile_id):
        """Đóng profile"""
        try:
            url = f"{self.api_url}/api/v3/profiles/close/{profile_id}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                success = result.get('success', False)
                
                if not success:
                    # Log lỗi nếu có
                    error_msg = result.get('message', 'Unknown error')
                    print(f"Stop profile failed: {error_msg}")
                
                return success
            else:
                print(f"Stop profile HTTP error: {response.status_code}")
                return False
        except Exception as e:
            print(f"Stop profile exception: {e}")
            return False
    
    def delete_profile(self, profile_id):
        """Xóa profile"""
        try:
            url = f"{self.api_url}/api/v3/profiles/delete/{profile_id}"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False


# ==================== ACCOUNT CLASS ====================
class Account:
    """Class đại diện cho 1 account Sephora"""
    
    def __init__(self, email, password, profile_id="", proxy="", note="", folder="Default"):
        self.id = profile_id
        self.name = email.split('@')[0] if email else ""
        self.email = email
        self.password = password
        self.phone = ""
        self.create_time = datetime.now().strftime("%H:%M %d/%m")
        self.last_run = ""
        self.status = "Ready"
        self.note = note
        self.proxy = proxy
        self.folder = folder
        self.cookie = ""
        self.warehouse_name = ""  # ✅ V1.6.5: Tên kho được gán cho account này
        self.order_id = ""  # ✅ V1.6.9: Order ID
        self.order_total = ""  # ✅ V1.7.4: Order Total ($)
        self.gift1 = ""  # ✅ V1.6.9: Giftcard 1
        self.gift2 = ""  # ✅ V1.6.9: Giftcard 2
        self.gift1_used = 0.0  # ✅ V1.7.8: Số tiền đã dùng từ Gift 1
        self.gift2_used = 0.0  # ✅ V1.7.8: Số tiền đã dùng từ Gift 2
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'password': self.password,
            'phone': self.phone,
            'create': self.create_time,
            'last': self.last_run,
            'status': self.status,
            'note': self.note,
            'proxy': self.proxy,
            'folder': self.folder,
            'cookie': self.cookie,
            'warehouse_name': self.warehouse_name,  # ✅ V1.6.5
            'order_id': self.order_id,  # ✅ V1.6.9
            'order_total': self.order_total,  # ✅ V1.7.4
            'gift1': self.gift1,  # ✅ V1.6.9
            'gift2': self.gift2,  # ✅ V1.6.9
            'gift1_used': self.gift1_used,  # ✅ V1.7.8
            'gift2_used': self.gift2_used  # ✅ V1.7.8
        }


# ==================== HELPER FUNCTIONS ====================

def parse_balance(balance_str):
    """
    ✅ V1.7.1: Parse balance hỗ trợ cả dấu phẩy và dấu chấm
    Input: "18,26" hoặc "18.26" hoặc 18.26
    Output: 18.26 (float)
    """
    try:
        if isinstance(balance_str, (int, float)):
            return float(balance_str)
        
        # Convert string: Replace comma with dot
        balance_str = str(balance_str).replace(',', '.')
        return float(balance_str)
    except:
        return 0.0

def format_balance(balance_value):
    """
    ✅ V1.7.1: Format balance để hiển thị (dùng dấu phẩy)
    Input: 18.26 (float)
    Output: "18,26" (string)
    """
    try:
        balance_float = float(balance_value)
        
        # Check if integer
        if balance_float == int(balance_float):
            return str(int(balance_float))
        else:
            # Format with comma
            return str(balance_float).replace('.', ',')
    except:
        return "0"

def clean_order_total(total_str):
    """
    ✅ V1.7.5: Clean order total format
    Input: "$20.00" hoặc "$20.50"
    Output: "20" hoặc "20,5"
    """
    try:
        # Remove $ và khoảng trắng
        cleaned = total_str.replace('$', '').replace(',', '').strip()
        
        # Convert to float
        value = float(cleaned)
        
        # Check if it's a whole number
        if value == int(value):
            return str(int(value))
        else:
            # Format với dấu phẩy, bỏ số 0 thừa
            formatted = f"{value:.2f}".rstrip('0').rstrip('.')
            return formatted.replace('.', ',')
    except:
        return total_str

# ==================== GIFTCARD CLASS ====================
class Giftcard:
    """Class đại diện cho 1 giftcard"""
    
    def __init__(self, card_number, pin, balance):
        self.card_number = card_number
        self.pin = pin
        # ✅ V1.7.1: Normalize balance (chuyển dấu phẩy thành dấu chấm)
        self.balance = self._normalize_balance(balance)
        self.create_time = datetime.now().strftime("%H:%M %d/%m")
    
    def _normalize_balance(self, balance_str):
        """
        ✅ V1.7.1: Parse và format balance với dấu phẩy
        Input: "18,26" hoặc "18.26" hoặc 18.26
        Output: "18,26" (string với dấu phẩy)
        """
        try:
            # Parse balance (hỗ trợ cả dấu phẩy và chấm)
            balance_float = parse_balance(balance_str)
            # Format lại với dấu phẩy
            return format_balance(balance_float)
        except:
            return "0"
    
    def to_dict(self):
        return {
            'card_number': self.card_number,
            'pin': self.pin,
            'balance': self.balance,
            'create': self.create_time
        }


# ==================== WAREHOUSE CLASS ====================
class Warehouse:
    """Class đại diện cho 1 kho hàng / địa chỉ giao hàng"""
    
    def __init__(self, first_name, last_name, address, city, state, zip_code, phone, name=""):
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.city = city
        self.state = state
        self.zip = zip_code
        self.phone = phone
        self.name = name if name else f"{first_name} {last_name}"
        self.create_time = datetime.now().strftime("%H:%M %d/%m")
    
    def to_dict(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip': self.zip,
            'phone': self.phone,
            'name': self.name,
            'create': self.create_time
        }


# ==================== SETTINGS WINDOW ====================
class SettingsWindow(ctk.CTkToplevel):
    """Cửa sổ Settings"""
    
    def __init__(self, parent, config):
        super().__init__(parent)
        
        self.config = config
        self.title("Settings")
        self.geometry("900x700")
        self.transient(parent)
        self.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(main_frame, text="⚙️ SETTINGS", font=("Arial", 20, "bold"))
        title.pack(pady=10)
        
        # Create tabview
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill="both", expand=True, pady=10)
        
        # Add tabs
        self.tab_gpm = self.tabview.add("GPM Login")
        self.tab_captcha = self.tabview.add("Captcha")
        self.tab_proxy = self.tabview.add("Proxy")
        self.tab_checkout = self.tabview.add("Checkout")  # ✅ V1.7.1
        
        self.create_gpm_tab()
        self.create_captcha_tab()
        self.create_proxy_tab()
        self.create_checkout_tab()  # ✅ V1.7.1
        
        # Save button
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="💾 Lưu", command=self.save_settings, 
                     width=120, height=35, fg_color="#2b7a3a").pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="❌ Hủy", command=self.destroy, 
                     width=120, height=35, fg_color="#8b0000").pack(side="right", padx=5)
    
    def create_gpm_tab(self):
        """Tab GPM Login"""
        frame = ctk.CTkScrollableFrame(self.tab_gpm)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # API URL
        ctk.CTkLabel(frame, text="API URL:", anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=5)
        self.gpm_api_url = ctk.CTkEntry(frame, height=35)
        self.gpm_api_url.insert(0, self.config.get('gpm_api_url', 'http://127.0.0.1:19995'))
        self.gpm_api_url.pack(fill="x", pady=5)
        
        # Tên Group
        ctk.CTkLabel(frame, text="Tên Group:", anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=5)
        self.gpm_group = ctk.CTkEntry(frame, height=35)
        self.gpm_group.insert(0, self.config.get('gpm_group', 'All'))
        self.gpm_group.pack(fill="x", pady=5)
        
        # Thư Mục Profile
        ctk.CTkLabel(frame, text="Thư Mục Profile:", anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=5)
        
        path_frame = ctk.CTkFrame(frame, fg_color="transparent")
        path_frame.pack(fill="x", pady=5)
        
        self.gpm_profile_path = ctk.CTkEntry(path_frame, height=35)
        self.gpm_profile_path.insert(0, self.config.get('gpm_profile_path', 'C:/Users/King/Documents/GPM/profiles'))
        self.gpm_profile_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(path_frame, text="📁 Browse", width=100, height=35,
                     command=self.browse_profile_path).pack(side="left")
        
        # ✅ V1.3.8: Resolution và Scale Config
        ctk.CTkLabel(frame, text="", height=5).pack()  # Spacer
        ctk.CTkLabel(frame, text="🖥️ PROFILE DISPLAY SETTINGS", anchor="w", 
                    font=("Arial", 13, "bold"), text_color="#1f6aa5").pack(fill="x", pady=10)
        
        # Resolution
        res_frame = ctk.CTkFrame(frame, fg_color="transparent")
        res_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(res_frame, text="Resolution:", anchor="w", 
                    font=("Arial", 12, "bold"), width=120).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(res_frame, text="Width:", anchor="w").pack(side="left", padx=(0, 5))
        self.gpm_screen_width = ctk.CTkEntry(res_frame, width=80, height=35)
        self.gpm_screen_width.insert(0, self.config.get('screen_width', '1920'))
        self.gpm_screen_width.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(res_frame, text="Height:", anchor="w").pack(side="left", padx=(0, 5))
        self.gpm_screen_height = ctk.CTkEntry(res_frame, width=80, height=35)
        self.gpm_screen_height.insert(0, self.config.get('screen_height', '1080'))
        self.gpm_screen_height.pack(side="left")
        
        # Scale
        scale_frame = ctk.CTkFrame(frame, fg_color="transparent")
        scale_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(scale_frame, text="Scale:", anchor="w", 
                    font=("Arial", 12, "bold"), width=120).pack(side="left", padx=(0, 10))
        
        self.gpm_scale = ctk.CTkEntry(scale_frame, width=80, height=35)
        self.gpm_scale.insert(0, self.config.get('device_scale_factor', '0.75'))
        self.gpm_scale.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(scale_frame, text="ℹ️ Recommended: 0.75 (hiển thị full content)", 
                    text_color="gray", anchor="w").pack(side="left")
        
        # ✅ V1.10.3: Auto Detect for 4 Columns
        auto_frame = ctk.CTkFrame(frame, fg_color="transparent")
        auto_frame.pack(fill="x", pady=10)
        
        self.auto_detect_var = ctk.BooleanVar(value=self.config.get('auto_detect_4cols', False))
        self.auto_detect_checkbox = ctk.CTkCheckBox(
            auto_frame, 
            text="🤖 Auto Detect for 4 Columns", 
            variable=self.auto_detect_var,
            font=("Arial", 12, "bold"),
            text_color="#1f6aa5"
        )
        self.auto_detect_checkbox.pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            auto_frame, 
            text="🔧 Calculate & Apply",
            command=self.auto_calculate_scale,
            width=150,
            height=35,
            fg_color="#2b7a3a"
        ).pack(side="left")
        
        # Info text
        info_frame = ctk.CTkFrame(frame, fg_color="transparent")
        info_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(
            info_frame, 
            text="ℹ️ Tự động tính Scale để fit 4 profiles/row dựa trên màn hình của bạn", 
            text_color="gray", 
            anchor="w"
        ).pack(fill="x")
        
        # ✅ V1.4.9: TopCashback URL Config
        ctk.CTkLabel(frame, text="", height=5).pack()  # Spacer
        ctk.CTkLabel(frame, text="🔗 TOPCASHBACK SETTINGS", anchor="w", 
                    font=("Arial", 13, "bold"), text_color="#1f6aa5").pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame, text="TopCashback URL:", anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=5)
        
        self.topcashback_url = ctk.CTkEntry(frame, height=35)
        default_tcb_url = "https://www.topcashback.com/EmailAuthentication/?g=N0k1Unk2ZmZiQUEwV0JlKzJIaytrMWJmU09PYUhhU3lYR2hHSGovOXpIdE5tVG9Nbm9oUUd3PT0%3d&u=OTcyNDRtZW1rdFhrSHcwSWxxcVR3ZzhuM2tmSTE4L3A%3d&wl=1&utm_source=ACEEmail9&utm_medium=email&utm_campaign=TCB%20Account%20Emails"
        self.topcashback_url.insert(0, self.config.get('topcashback_url', default_tcb_url))
        self.topcashback_url.pack(fill="x", pady=5)
        
        ctk.CTkLabel(frame, text="ℹ️ Mỗi user có link TopCashback riêng, paste link của bạn vào đây", 
                    text_color="gray", anchor="w").pack(fill="x", pady=5)
    
    def create_captcha_tab(self):
        """Tab Captcha"""
        frame = ctk.CTkScrollableFrame(self.tab_captcha)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="2Captcha API Key:", anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=5)
        self.captcha_api = ctk.CTkEntry(frame, height=35)
        self.captcha_api.insert(0, self.config.get('captcha_api', ''))
        self.captcha_api.pack(fill="x", pady=5)
        
        info = ctk.CTkLabel(frame, text="ℹ️ Get API key from: https://2captcha.com", 
                           text_color="gray", anchor="w")
        info.pack(fill="x", pady=5)
    
    def create_proxy_tab(self):
        """Tab Proxy"""
        frame = ctk.CTkScrollableFrame(self.tab_proxy)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Proxy timeout
        ctk.CTkLabel(frame, text="Timeout (phút):", anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=5)
        self.proxy_timeout = ctk.CTkEntry(frame, height=35)
        self.proxy_timeout.insert(0, self.config.get('proxy_timeout', '20'))
        self.proxy_timeout.pack(fill="x", pady=5)
        
        # Proxy API
        ctk.CTkLabel(frame, text="Proxy API Key:", anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=5)
        self.proxy_api_key = ctk.CTkEntry(frame, height=35)
        self.proxy_api_key.insert(0, self.config.get('proxy_api_key', ''))
        self.proxy_api_key.pack(fill="x", pady=5)
    
    def browse_profile_path(self):
        """Browse folder"""
        folder = filedialog.askdirectory(title="Chọn thư mục Profile")
        if folder:
            self.gpm_profile_path.delete(0, "end")
            self.gpm_profile_path.insert(0, folder)
    
    def create_checkout_tab(self):
        """✅ V1.7.1: Tab Checkout - Giftcard Settings"""
        frame = ctk.CTkScrollableFrame(self.tab_checkout)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(frame, text="🎁 GIFTCARD CHECKOUT SETTINGS", anchor="w", 
                    font=("Arial", 13, "bold"), text_color="#1f6aa5").pack(fill="x", pady=10)
        
        # Total Price Selector
        ctk.CTkLabel(frame, text="Total Price Selector (XPath hoặc CSS):", 
                    anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=5)
        self.total_price_selector = ctk.CTkEntry(frame, height=35, 
                                                placeholder_text="span[data-at='bsk_total_cc']")
        self.total_price_selector.insert(0, self.config.get('total_price_selector', 'span[data-at="bsk_total_cc"]'))
        self.total_price_selector.pack(fill="x", pady=5)
        
        ctk.CTkLabel(frame, text="ℹ️ Selector để lấy tổng tiền đơn hàng sau khi điền địa chỉ", 
                    text_color="gray", anchor="w").pack(fill="x", pady=2)
        
        # ⚠️ TODO: User sẽ khai báo các field giftcard sau
        ctk.CTkLabel(frame, text="", height=10).pack()
        ctk.CTkLabel(frame, text="⚠️ Giftcard form elements - Coming soon!", 
                    anchor="w", font=("Arial", 11, "bold"), text_color="#FFA500").pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text="Hiện tại tool chỉ gán Gift 1, Gift 2 vào account và trừ balance.\nBạn sẽ khai báo element giftcard sau để tool tự động apply.", 
                    anchor="w", text_color="gray").pack(fill="x", pady=2)
    
    def auto_calculate_scale(self):
        """
        ✅ V1.10.4: Auto-calculate scale để fit 4 columns (công thức đơn giản)
        """
        try:
            # Get screen width
            try:
                screen_width = self.winfo_screenwidth()
                # Nếu > 2560 → có 2 màn, chia đôi
                if screen_width > 2560:
                    screen_width = screen_width // 2
            except:
                screen_width = 1920
            
            # Get resolution từ user input
            try:
                config_width = int(self.gpm_screen_width.get())
            except:
                messagebox.showerror("Lỗi", "Resolution Width không hợp lệ!")
                return
            
            # ✅ V1.10.4 FIX: Công thức đơn giản
            # Mỗi column = screen_width / 4
            target_cols = 4
            available_width_per_col = screen_width / target_cols
            
            # Scale = available_width / config_width
            # Để an toàn, trừ 5% cho margin
            calculated_scale = (available_width_per_col * 0.95) / config_width
            
            # Round to 2 decimal places
            calculated_scale = round(calculated_scale, 2)
            
            # Validate scale (min 0.1, max 1.0)
            if calculated_scale < 0.1:
                calculated_scale = 0.1
            elif calculated_scale > 1.0:
                calculated_scale = 1.0
            
            # Update scale entry
            self.gpm_scale.delete(0, "end")
            self.gpm_scale.insert(0, str(calculated_scale))
            
            # Show result
            actual_width = int(config_width * calculated_scale)
            messagebox.showinfo(
                "✅ Auto Calculate Success",
                f"Screen: {screen_width}px\n"
                f"Resolution: {config_width}px\n"
                f"Target: 4 columns\n\n"
                f"Calculated Scale: {calculated_scale}\n"
                f"Actual Window Width: {actual_width}px\n"
                f"Column spacing: {int(available_width_per_col)}px\n"
                f"Margin per window: ~{int(available_width_per_col - actual_width)}px"
            )
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tính scale: {e}")
    
    def save_settings(self):
        """Lưu settings"""
        self.config['gpm_api_url'] = self.gpm_api_url.get()
        self.config['gpm_group'] = self.gpm_group.get()
        self.config['gpm_profile_path'] = self.gpm_profile_path.get()
        self.config['captcha_api'] = self.captcha_api.get()
        self.config['proxy_timeout'] = self.proxy_timeout.get()
        self.config['proxy_api_key'] = self.proxy_api_key.get()
        
        # ✅ V1.3.8: Lưu resolution và scale config
        self.config['screen_width'] = self.gpm_screen_width.get()
        self.config['screen_height'] = self.gpm_screen_height.get()
        self.config['device_scale_factor'] = self.gpm_scale.get()
        
        # ✅ V1.10.3: Lưu auto detect 4 columns
        self.config['auto_detect_4cols'] = self.auto_detect_var.get()
        
        # ✅ V1.4.9: Lưu TopCashback URL
        self.config['topcashback_url'] = self.topcashback_url.get()
        
        # ✅ V1.7.1: Lưu Checkout/Giftcard settings
        self.config['total_price_selector'] = self.total_price_selector.get()
        
        # ✅ V1.8.6: Lưu Threads và Delay từ main window
        if hasattr(self.parent, 'threads_entry'):
            self.config['threads'] = self.parent.threads_entry.get()
        if hasattr(self.parent, 'delay_entry'):
            self.config['delay'] = self.parent.delay_entry.get()
        
        messagebox.showinfo("✅ Thành công", "Đã lưu settings!")
        self.destroy()


# ==================== GIFTCARD WINDOW ====================
class GiftcardWindow(ctk.CTkToplevel):
    """Cửa sổ quản lý Giftcard"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.title("Quản lý Giftcard")
        self.geometry("900x600")
        self.transient(parent)
        self.grab_set()
        
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(main_frame, text="🎁 QUẢN LÝ GIFTCARD", font=("Arial", 20, "bold"))
        title.pack(pady=10)
        
        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="+ Thêm Giftcard", width=130, height=35,
                     fg_color="#2b7a3a", command=self.add_giftcard).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📁 Import", width=100, height=35,
                     command=self.import_giftcards).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🗑️ Xóa", width=100, height=35,
                     fg_color="#8b0000", command=self.delete_selected).pack(side="left", padx=5)
        
        # Table
        self.create_table(main_frame)
        
        # Close button
        ctk.CTkButton(main_frame, text="Đóng", width=120, height=35,
                     command=self.destroy).pack(pady=10)
        
        # Load data
        self.refresh_table()
    
    def create_table(self, parent):
        """Tạo bảng giftcard"""
        table_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b")
        table_frame.pack(fill="both", expand=True, pady=10)
        
        # Style
        style = ttk.Style()
        style.configure("Giftcard.Treeview", background="#2a2d2e", foreground="white",
                       rowheight=25, fieldbackground="#2a2d2e")
        style.map('Giftcard.Treeview', background=[('selected', '#22559b')])
        
        # Columns
        columns = ("STT", "Giftcard", "Pin", "Balance", "Create")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="tree headings",
                                selectmode="extended", style="Giftcard.Treeview")
        
        widths = {"STT": 50, "Giftcard": 250, "Pin": 150, "Balance": 150, "Create": 150}
        
        # ✅ V1.6.9: Sort state tracking
        self.sort_reverse = {}
        
        for col in columns:
            # ✅ V1.6.9: Bind click để sort
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=widths[col], anchor="w")
            self.sort_reverse[col] = False
        
        self.tree.column("#0", width=0, stretch=False)
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Drag selection
        self.drag_start_item = None
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<B1-Motion>", self.on_drag_motion)
        self.tree.bind("<Control-a>", self.select_all)
        self.tree.bind("<Control-A>", self.select_all)
        
        # ✅ V1.6.9: Context menu
        self.tree.bind("<Button-3>", self.show_context_menu)
    
    def on_drag_start(self, event):
        """Bắt đầu drag"""
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_start_item = item
    
    def on_drag_motion(self, event):
        """Kéo chuột để chọn"""
        if not self.drag_start_item:
            return
        
        current_item = self.tree.identify_row(event.y)
        if not current_item:
            return
        
        all_items = self.tree.get_children()
        
        try:
            start_idx = all_items.index(self.drag_start_item)
            end_idx = all_items.index(current_item)
            
            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx
            
            items_to_select = all_items[start_idx:end_idx + 1]
            self.tree.selection_set(items_to_select)
        except:
            pass
    
    def select_all(self, event=None):
        """Select all giftcards"""
        all_items = self.tree.get_children()
        self.tree.selection_set(all_items)
        return "break"
    
    def sort_column(self, col):
        """✅ V1.6.9: Sort column khi click vào heading"""
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        
        reverse = self.sort_reverse[col]
        
        try:
            # Try numeric sort for Balance
            if col == "Balance":
                items.sort(key=lambda x: float(x[0]) if x[0] else 0, reverse=reverse)
            else:
                items.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)
        except (ValueError, TypeError):
            items.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)
        
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)
        
        self.sort_reverse[col] = not reverse
        
        # Update heading arrow
        arrow = " ▼" if reverse else " ▲"
        for c in self.sort_reverse.keys():
            self.tree.heading(c, text=c.replace(" ▲", "").replace(" ▼", ""))
        self.tree.heading(col, text=col + arrow)
    
    def show_context_menu(self, event):
        """✅ V1.6.9: Context menu"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        current_selection = self.tree.selection()
        if item not in current_selection:
            self.tree.selection_set(item)
        
        menu = ctk.CTkToplevel(self)
        menu.wm_overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color="#2b2b2b")
        
        # Copy options
        ctk.CTkButton(
            menu,
            text="📋 Copy Giftcard",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.copy_field("giftcard", menu)
        ).pack(fill="x", pady=1)
        
        ctk.CTkButton(
            menu,
            text="📋 Copy Giftcard:PIN",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.copy_field("giftcard:pin", menu)
        ).pack(fill="x", pady=1)
        
        ctk.CTkButton(
            menu,
            text="📋 Copy Giftcard:PIN:Balance",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.copy_field("giftcard:pin:balance", menu)
        ).pack(fill="x", pady=1)
        
        # Separator
        ctk.CTkLabel(menu, text="─" * 30, text_color="gray").pack(fill="x")
        
        # ✅ V1.7.0: Edit Balance
        ctk.CTkButton(
            menu,
            text="✏️ Edit Balance",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.edit_balance(menu)
        ).pack(fill="x", pady=1)
        
        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_set()
    
    def copy_field(self, field_type, menu):
        """✅ V1.6.9: Copy field to clipboard"""
        selected = self.tree.selection()
        if not selected:
            return
        
        menu.destroy()
        
        result = []
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            giftcard = str(values[1])  # Giftcard column
            pin = str(values[2])       # Pin column
            balance = str(values[3])   # Balance column
            
            if field_type == "giftcard":
                result.append(giftcard)
            elif field_type == "giftcard:pin":
                result.append(f"{giftcard}:{pin}")
            elif field_type == "giftcard:pin:balance":
                result.append(f"{giftcard}:{pin}:{balance}")
        
        text = "\n".join(result)
        
        # ✅ FIX: Use parent window clipboard instead
        try:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)
            self.parent.update()
        except:
            pass
        
        messagebox.showinfo(
            "✅ Đã copy!",
            f"Đã copy {len(selected)} giftcard(s) vào clipboard!"
        )
    
    def edit_balance(self, menu):
        """✅ V1.7.0: Edit balance của giftcard(s)"""
        selected = self.tree.selection()
        if not selected:
            return
        
        menu.destroy()
        
        # Dialog nhập balance
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Balance")
        dialog.geometry("650x500")  # ✅ Tăng size từ 500x350 lên 650x500
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="✏️ EDIT BALANCE", font=("Arial", 18, "bold")).pack(pady=15)
        
        # Info
        info_frame = ctk.CTkFrame(frame, fg_color="#1a1a1a")
        info_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(info_frame, 
                    text=f"Đang chọn: {len(selected)} giftcard(s)",
                    anchor="w", font=("Arial", 13, "bold")).pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(info_frame,
                    text="• Nhập 1 số: Set tất cả về balance đó\n• Nhập nhiều dòng: Set theo thứ tự (50\\n30\\n20)",
                    anchor="w", font=("Arial", 11), text_color="gray").pack(fill="x", padx=15, pady=5)
        
        # Textarea
        ctk.CTkLabel(frame, text="Nhập balance:", anchor="w", font=("Arial", 12)).pack(fill="x", pady=(15, 5))
        textbox = ctk.CTkTextbox(frame, height=150, font=("Consolas", 14))  # ✅ Tăng height và font
        textbox.pack(fill="both", expand=True, pady=5)
        textbox.focus_set()
        
        def save():
            content = textbox.get("1.0", "end-1c").strip()
            if not content:
                messagebox.showwarning("⚠️ Cảnh báo", "Vui lòng nhập balance!")
                return
            
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            # Get selected giftcard indices
            selected_items = list(selected)
            
            updated = 0
            for idx, item_id in enumerate(selected_items):
                values = self.tree.item(item_id)['values']
                giftcard_number = str(values[1])
                
                # Find giftcard in parent list
                gc = None
                for g in self.parent.giftcards:
                    if g.card_number == giftcard_number:
                        gc = g
                        break
                
                if gc:
                    # Determine which balance to use
                    if len(lines) == 1:
                        # Single value: apply to all
                        new_balance = lines[0]
                    elif idx < len(lines):
                        # Multiple values: apply in order
                        new_balance = lines[idx]
                    else:
                        # Not enough values: skip
                        continue
                    
                    # ✅ V1.7.1: Parse và format balance (dấu phẩy)
                    try:
                        # Parse balance (hỗ trợ cả dấu phẩy và chấm)
                        balance_float = parse_balance(new_balance)
                        # Format lại với dấu phẩy
                        gc.balance = format_balance(balance_float)
                        updated += 1
                    except Exception as e:
                        print(f"[ERROR] Invalid balance format: {new_balance}")
                        continue
            
            if updated > 0:
                self.parent.save_giftcards()
                self.refresh_table()
                messagebox.showinfo("✅ OK", f"Đã cập nhật {updated} giftcard(s)!")
                dialog.destroy()
            else:
                messagebox.showwarning("⚠️ Cảnh báo", "Không có giftcard nào được cập nhật!")
        
        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)
        
        ctk.CTkButton(btn_frame, text="Hủy", width=120, height=40, font=("Arial", 13),
                     command=dialog.destroy).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="✅ Lưu", width=120, height=40, font=("Arial", 13),
                     fg_color="#2b7a3a", command=save).pack(side="right", padx=5)
    
    def refresh_table(self):
        """Refresh bảng"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for idx, gc in enumerate(self.parent.giftcards, 1):
            self.tree.insert("", "end", values=(
                idx, gc.card_number, gc.pin, gc.balance, gc.create_time
            ))
    
    def add_giftcard(self):
        """Thêm giftcard mới"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Thêm Giftcard")
        dialog.geometry("700x450")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="THÊM GIFTCARD", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Format info
        format_frame = ctk.CTkFrame(frame, fg_color="#1a1a1a")
        format_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(format_frame, text="List giftcard (Format: Giftcard:Pin:Balance):",
                    anchor="w", font=("Arial", 10)).pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(format_frame, text="# Mỗi dòng 1 giftcard\n# Format: Giftcard:Pin:Balance\n# Ví dụ: 6245123456789012:1234:100 hoặc 100,50\n# Hỗ trợ cả dấu phẩy (,) và dấu chấm (.)",
                    anchor="w", font=("Arial", 9), text_color="gray").pack(fill="x", padx=10, pady=2)
        
        # Textarea
        textbox = ctk.CTkTextbox(frame, height=200, font=("Consolas", 11))
        textbox.pack(fill="both", expand=True, pady=10)
        
        def save():
            content = textbox.get("1.0", "end-1c").strip()
            if not content:
                messagebox.showwarning("⚠️ Cảnh báo", "Vui lòng nhập dữ liệu!")
                return
            
            lines = content.split('\n')
            count = 0
            errors = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(':')
                if len(parts) == 3:
                    try:
                        gc = Giftcard(
                            card_number=parts[0].strip(),
                            pin=parts[1].strip(),
                            balance=parts[2].strip()
                        )
                        self.parent.giftcards.append(gc)
                        count += 1
                    except Exception as e:
                        errors.append(f"Dòng {line_num}: {str(e)}")
                else:
                    errors.append(f"Dòng {line_num}: Sai format (cần 3 phần, có {len(parts)})")
            
            self.parent.save_giftcards()
            self.refresh_table()
            
            if errors:
                error_msg = "\n".join(errors[:5])
                messagebox.showwarning("⚠️ Cảnh báo", 
                                     f"Đã thêm {count} giftcard!\n\nLỗi:\n{error_msg}")
            else:
                messagebox.showinfo("✅ OK", f"Đã thêm {count} giftcard!")
            
            dialog.destroy()
        
        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(btn_frame, text="Hủy", width=100, height=35,
                     fg_color="#8b0000", command=dialog.destroy).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="+ Thêm", width=100, height=35,
                     fg_color="#2b7a3a", command=save).pack(side="right", padx=5)
    
    def import_giftcards(self):
        """Import giftcard từ file"""
        file_path = filedialog.askopenfilename(
            title="Chọn file Import",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            count = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(':')
                if len(parts) == 3:
                    gc = Giftcard(
                        card_number=parts[0].strip(),
                        pin=parts[1].strip(),
                        balance=parts[2].strip()
                    )
                    self.parent.giftcards.append(gc)
                    count += 1
            
            self.parent.save_giftcards()
            self.refresh_table()
            messagebox.showinfo("✅ OK", f"Đã import {count} giftcard!")
        except Exception as e:
            messagebox.showerror("❌ Lỗi", f"Import lỗi: {e}")
    
    def delete_selected(self):
        """Xóa giftcard đã chọn"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("⚠️ Cảnh báo", "Hãy chọn giftcard cần xóa!")
            return
        
        if messagebox.askyesno("⚠️ Xác nhận", f"Xóa {len(selected)} giftcard?"):
            indices = []
            for item in selected:
                values = self.tree.item(item)['values']
                idx = int(values[0]) - 1
                indices.append(idx)
            
            for idx in sorted(indices, reverse=True):
                del self.parent.giftcards[idx]
            
            self.parent.save_giftcards()
            self.refresh_table()
            messagebox.showinfo("✅ OK", f"Đã xóa {len(selected)} giftcard!")


# ==================== WAREHOUSE WINDOW ====================
class WarehouseWindow(ctk.CTkToplevel):
    """Cửa sổ quản lý Kho"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.title("Quản lý Kho")
        self.geometry("1000x600")
        self.transient(parent)
        self.grab_set()
        
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(main_frame, text="📦 QUẢN LÝ KHO", font=("Arial", 20, "bold"))
        title.pack(pady=10)
        
        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="+ Thêm Kho", width=120, height=35,
                     fg_color="#2b7a3a", command=self.add_warehouse).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📁 Import", width=100, height=35,
                     command=self.import_warehouses).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🗑️ Xóa", width=100, height=35,
                     fg_color="#8b0000", command=self.delete_selected).pack(side="left", padx=5)
        
        # Table
        self.create_table(main_frame)
        
        # Close button
        ctk.CTkButton(main_frame, text="Đóng", width=120, height=35,
                     command=self.destroy).pack(pady=10)
        
        # Load data
        self.refresh_table()
    
    def create_table(self, parent):
        """Tạo bảng kho"""
        table_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b")
        table_frame.pack(fill="both", expand=True, pady=10)
        
        # Style
        style = ttk.Style()
        style.configure("Warehouse.Treeview", background="#2a2d2e", foreground="white",
                       rowheight=25, fieldbackground="#2a2d2e")
        style.map('Warehouse.Treeview', background=[('selected', '#22559b')])
        
        # Columns
        columns = ("STT", "First Name", "Last Name", "Address", "City", "State", "ZIP", "Phone", "Kho", "Create")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="tree headings",
                                selectmode="extended", style="Warehouse.Treeview")
        
        widths = {"STT": 50, "First Name": 100, "Last Name": 100,
                 "Address": 200, "City": 100, "State": 60, "ZIP": 80, "Phone": 120, "Kho": 150, "Create": 100}
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor="w")
        
        self.tree.column("#0", width=0, stretch=False)
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # ✅ Drag selection
        self.drag_start_item = None
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<B1-Motion>", self.on_drag_motion)
        self.tree.bind("<Control-a>", self.select_all)
        self.tree.bind("<Control-A>", self.select_all)
    
    def on_drag_start(self, event):
        """Bắt đầu drag"""
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_start_item = item
    
    def on_drag_motion(self, event):
        """Kéo chuột để chọn"""
        if not self.drag_start_item:
            return
        
        current_item = self.tree.identify_row(event.y)
        if not current_item:
            return
        
        # Get all items
        all_items = self.tree.get_children()
        
        try:
            start_idx = all_items.index(self.drag_start_item)
            end_idx = all_items.index(current_item)
            
            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx
            
            # Select range
            items_to_select = all_items[start_idx:end_idx + 1]
            self.tree.selection_set(items_to_select)
        except:
            pass
    
    def select_all(self, event=None):
        """Select all warehouses"""
        all_items = self.tree.get_children()
        self.tree.selection_set(all_items)
        return "break"
    
    def refresh_table(self):
        """Refresh bảng"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for idx, wh in enumerate(self.parent.warehouses, 1):
            self.tree.insert("", "end", values=(
                idx, wh.first_name, wh.last_name, wh.address,
                wh.city, wh.state, wh.zip, wh.phone, wh.name, wh.create_time
            ))
    
    def add_warehouse(self):
        """Thêm kho mới - giống Add Account"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Thêm Kho Mới")
        dialog.geometry("700x500")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="THÊM KHO MỚI", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Format info
        format_frame = ctk.CTkFrame(frame, fg_color="#1a1a1a")
        format_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(format_frame, text="List warehouse (Format: FirstName|LastName|Address|City|State|ZIP|Phone|Name Kho):",
                    anchor="w", font=("Arial", 10)).pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(format_frame, text="# Mỗi dòng 1 kho\n# Format: FirstName|LastName|Address|City|State|ZIP|Phone|Name Kho",
                    anchor="w", font=("Arial", 9), text_color="gray").pack(fill="x", padx=10, pady=2)
        
        # Textarea
        textbox = ctk.CTkTextbox(frame, height=250, font=("Consolas", 11))
        textbox.pack(fill="both", expand=True, pady=10)
        
        def save():
            content = textbox.get("1.0", "end-1c").strip()
            if not content:
                messagebox.showwarning("⚠️ Cảnh báo", "Vui lòng nhập dữ liệu!")
                return
            
            lines = content.split('\n')
            count = 0
            errors = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('|')
                if len(parts) == 8:
                    try:
                        wh = Warehouse(
                            first_name=parts[0].strip(),
                            last_name=parts[1].strip(),
                            address=parts[2].strip(),
                            city=parts[3].strip(),
                            state=parts[4].strip(),
                            zip_code=parts[5].strip(),
                            phone=parts[6].strip(),
                            name=parts[7].strip()
                        )
                        self.parent.warehouses.append(wh)
                        count += 1
                    except Exception as e:
                        errors.append(f"Dòng {line_num}: {str(e)}")
                else:
                    errors.append(f"Dòng {line_num}: Sai format (cần 8 phần, có {len(parts)})")
            
            self.parent.save_warehouses()
            self.refresh_table()
            self.parent.update_warehouse_dropdown()
            
            if errors:
                error_msg = "\n".join(errors[:5])  # Show first 5 errors
                messagebox.showwarning("⚠️ Cảnh báo", 
                                     f"Đã thêm {count} kho!\n\nLỗi:\n{error_msg}")
            else:
                messagebox.showinfo("✅ OK", f"Đã thêm {count} kho!")
            
            dialog.destroy()
        
        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(btn_frame, text="Hủy", width=100, height=35,
                     fg_color="#8b0000", command=dialog.destroy).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="+ Thêm", width=100, height=35,
                     fg_color="#2b7a3a", command=save).pack(side="right", padx=5)
    
    def import_warehouses(self):
        """Import kho từ file"""
        file_path = filedialog.askopenfilename(
            title="Chọn file Import",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            count = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('|')
                if len(parts) == 8:
                    wh = Warehouse(
                        first_name=parts[0].strip(),
                        last_name=parts[1].strip(),
                        address=parts[2].strip(),
                        city=parts[3].strip(),
                        state=parts[4].strip(),
                        zip_code=parts[5].strip(),
                        phone=parts[6].strip(),
                        name=parts[7].strip()
                    )
                    self.parent.warehouses.append(wh)
                    count += 1
            
            self.parent.save_warehouses()
            self.refresh_table()
            self.parent.update_warehouse_dropdown()
            messagebox.showinfo("✅ OK", f"Đã import {count} kho!")
        except Exception as e:
            messagebox.showerror("❌ Lỗi", f"Import lỗi: {e}")
    
    def delete_selected(self):
        """Xóa kho đã chọn"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("⚠️ Cảnh báo", "Hãy chọn kho cần xóa!")
            return
        
        if messagebox.askyesno("⚠️ Xác nhận", f"Xóa {len(selected)} kho?"):
            # Get indices
            indices = []
            for item in selected:
                values = self.tree.item(item)['values']
                idx = int(values[0]) - 1
                indices.append(idx)
            
            # Delete from list (reverse order)
            for idx in sorted(indices, reverse=True):
                del self.parent.warehouses[idx]
            
            self.parent.save_warehouses()
            self.refresh_table()
            self.parent.update_warehouse_dropdown()
            messagebox.showinfo("✅ OK", f"Đã xóa {len(selected)} kho!")


# ==================== MAIN APP ====================
class SephoraAutoTool(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Cấu hình theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Cấu hình window
        self.title("Sephora Auto Order - 1.10.9")
        self.geometry("1400x700")
        
        # Biến
        self.accounts = []
        self.warehouses = []  # ✅ V1.6.1: Danh sách kho
        self.giftcards = []  # ✅ V1.6.8: Danh sách giftcard
        self.warehouse_selected = None  # ✅ V1.6.2: Kho được chọn để checkout
        self.folders = ["Default", "Mặc định", "Check gift Sep", "Check gift Macys", "ABC"]
        self.config = self.load_config()
        self.gpm_api = GPMLoginAPI(self.config.get('gpm_api_url', 'http://127.0.0.1:19995'))
        self.is_running = False
        self.stop_flag = False  # ✅ V1.3.4
        self.search_filter = ""  # ✅ NEW v1.2.4: Search filter text
        
        # ✅ V1.8.1: Thread locks cho multi-threading
        self.refresh_lock = threading.Lock()
        self.save_lock = threading.Lock()
        
        # ✅ V1.7.0: Column visibility tracking
        self.column_visibility = {}  # Track which columns are visible
        self.column_widths = {}  # Track column widths
        
        # ✅ NEW v1.2.6: Region checkboxes
        self.region_usa = ctk.BooleanVar(value=False)
        self.region_can = ctk.BooleanVar(value=False)
        
        # Tạo giao diện
        self.create_sidebar()
        self.create_main_content()
        
        # Load accounts
        self.load_accounts()
        
        # ✅ V1.6.1: Load warehouses
        self.load_warehouses()
        
        # ✅ V1.6.8: Load giftcards
        self.load_giftcards()
        
        # ✅ V1.5.2: Load Items và Quantity - CHỈ insert nếu có giá trị (giữ placeholder nếu rỗng)
        if hasattr(self, 'item1_entry'):
            item1_val = self.config.get('item1', '')
            if item1_val:  # Chỉ insert nếu không rỗng
                self.item1_entry.insert(0, item1_val)
        
        if hasattr(self, 'item2_entry'):
            item2_val = self.config.get('item2', '')
            if item2_val:
                self.item2_entry.insert(0, item2_val)
        
        if hasattr(self, 'item3_entry'):
            item3_val = self.config.get('item3', '')
            if item3_val:
                self.item3_entry.insert(0, item3_val)
        
        # Quantity luôn có giá trị default, nên vẫn load bình thường
        if hasattr(self, 'qty1_entry'):
            qty1 = self.config.get('qty1', '1')
            self.qty1_entry.delete(0, 'end')
            self.qty1_entry.insert(0, qty1)
        if hasattr(self, 'qty2_entry'):
            qty2 = self.config.get('qty2', '1')
            self.qty2_entry.delete(0, 'end')
            self.qty2_entry.insert(0, qty2)
        if hasattr(self, 'qty3_entry'):
            qty3 = self.config.get('qty3', '1')
            self.qty3_entry.delete(0, 'end')
            self.qty3_entry.insert(0, qty3)
        
        # ✅ V1.5.7: Load Coupon và Sample
        if hasattr(self, 'coupon_entry'):
            coupon_val = self.config.get('coupon', '')
            if coupon_val:
                self.coupon_entry.insert(0, coupon_val)
        
        # ✅ V1.9.4: Load Coupon items
        if hasattr(self, 'coupon_item1_entry'):
            val = self.config.get('coupon_item1', '')
            if val:
                self.coupon_item1_entry.insert(0, val)
        if hasattr(self, 'coupon_item2_entry'):
            val = self.config.get('coupon_item2', '')
            if val:
                self.coupon_item2_entry.insert(0, val)
        if hasattr(self, 'coupon_item3_entry'):
            val = self.config.get('coupon_item3', '')
            if val:
                self.coupon_item3_entry.insert(0, val)
        if hasattr(self, 'coupon_item4_entry'):
            val = self.config.get('coupon_item4', '')
            if val:
                self.coupon_item4_entry.insert(0, val)
        
        if hasattr(self, 'sample1_entry'):
            sample1_val = self.config.get('sample1', '')
            if sample1_val:
                self.sample1_entry.insert(0, sample1_val)
        
        if hasattr(self, 'sample2_entry'):
            sample2_val = self.config.get('sample2', '')
            if sample2_val:
                self.sample2_entry.insert(0, sample2_val)

        # ✅ V1.10.7: Load Point 1-5
        if hasattr(self, 'point1_entry'):
            val = self.config.get('point1', '')
            if val:
                self.point1_entry.insert(0, val)
        if hasattr(self, 'point2_entry'):
            val = self.config.get('point2', '')
            if val:
                self.point2_entry.insert(0, val)
        if hasattr(self, 'point3_entry'):
            val = self.config.get('point3', '')
            if val:
                self.point3_entry.insert(0, val)
        if hasattr(self, 'point4_entry'):
            val = self.config.get('point4', '')
            if val:
                self.point4_entry.insert(0, val)
        if hasattr(self, 'point5_entry'):
            val = self.config.get('point5', '')
            if val:
                self.point5_entry.insert(0, val)

        # Auto-save config khi đóng
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_sidebar(self):
        """Tạo sidebar"""
        sidebar = ctk.CTkFrame(self, width=85, fg_color="#1a1a1a")  # ✅ Tăng width từ 60 lên 85
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Logo
        logo = ctk.CTkFrame(sidebar, fg_color="green", width=45, height=45, corner_radius=10)
        logo.pack(pady=20, padx=20)
        
        # Menu icons với labels
        icons = [
            ("☰", "menu", "Menu"),
            ("📦", "warehouse", "Kho"),
            ("🎁", "giftcard", "Giftcard"),
            ("💾", "save", "Lưu"),
            ("⚙️", "settings", "Cài đặt")
        ]
        
        for icon, cmd, label in icons:
            # Container cho icon + label
            container = ctk.CTkFrame(sidebar, fg_color="transparent")
            container.pack(pady=5, padx=7)
            
            # Icon button
            btn = ctk.CTkButton(
                container,
                text=icon,
                width=45,
                height=45,
                font=("Arial", 20),  # ✅ V1.8.7: Tăng từ 18 lên 20
                fg_color="transparent",
                hover_color="#2b2b2b",
                command=lambda c=cmd: self.on_sidebar_click(c)
            )
            btn.pack()
            
            # Label text
            ctk.CTkLabel(
                container,
                text=label,
                font=("Arial", 11),  # ✅ V1.8.7: Tăng từ 8 lên 11
                text_color="#888888"
            ).pack()
    
    def on_sidebar_click(self, cmd):
        """Xử lý click sidebar"""
        if cmd == "settings":
            SettingsWindow(self, self.config)
        elif cmd == "warehouse":
            WarehouseWindow(self)
        elif cmd == "giftcard":
            GiftcardWindow(self)  # ✅ V1.6.8
        elif cmd == "save":
            self.save_accounts()
            self.save_config()
            self.save_warehouses()
            self.save_giftcards()  # ✅ V1.6.8
            messagebox.showinfo("✅ OK", "Đã lưu dữ liệu!")
    
    def create_main_content(self):
        """Tạo nội dung chính"""
        main_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        main_frame.pack(side="left", fill="both", expand=True)
        
        self.create_top_controls(main_frame)
        self.create_table(main_frame)
        self.create_status_bar(main_frame)
    
    def create_top_controls(self, parent):
        """Tạo controls"""
        top = ctk.CTkFrame(parent, fg_color="#1a1a1a")
        top.pack(side="top", fill="x", padx=10, pady=5)
        
        # Row 1
        row1 = ctk.CTkFrame(top, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        
        # Folder dropdown
        self.folder_var = ctk.StringVar(value=self.folders[0])
        self.folder_menu = ctk.CTkOptionMenu(
            row1,
            variable=self.folder_var,
            values=self.folders,
            width=150,
            command=lambda x: self.refresh_table()
        )
        self.folder_menu.pack(side="left", padx=5)
        
        # Function dropdown (✅ NEW v1.2.6: Added Sephora Order)
        self.function_var = ctk.StringVar(value="--Chọn chức năng")
        function_menu = ctk.CTkOptionMenu(
            row1,
            variable=self.function_var,
            values=["--Chọn chức năng", "Sephora Order"],
            width=180
        )
        function_menu.pack(side="left", padx=5)
        
        # Luồng
        ctk.CTkLabel(row1, text="Luồng:").pack(side="left", padx=5)
        self.threads_entry = ctk.CTkEntry(row1, width=60)
        self.threads_entry.insert(0, self.config.get('threads', '12'))  # ✅ V1.8.6: Load từ config
        self.threads_entry.pack(side="left", padx=5)
        
        # Row 2
        row2 = ctk.CTkFrame(top, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        
        # Thư Mục button
        ctk.CTkButton(
            row2,
            text="📁 Thư Mục",
            width=100,
            command=self.manage_folders
        ).pack(side="left", padx=5)
        
        # ✅ V1.7.0: Columns button
        ctk.CTkButton(
            row2,
            text="⚙️ Columns",
            width=100,
            command=self.manage_columns
        ).pack(side="left", padx=5)
        
        # ✅ REMOVED: "Set Status, Note..." button (now in context menu only)
        
        # Delay
        ctk.CTkLabel(row2, text="Delay:").pack(side="left", padx=5)
        self.delay_entry = ctk.CTkEntry(row2, width=60)
        self.delay_entry.insert(0, self.config.get('delay', '2'))  # ✅ V1.8.6: Load từ config
        self.delay_entry.pack(side="left", padx=5)
        
        # Chạy button
        self.run_button = ctk.CTkButton(
            row2,
            text="▶ Chạy",
            width=90,
            fg_color="#1f6aa5",
            command=self.run_automation
        )
        self.run_button.pack(side="left", padx=10)
        
        # ✅ NEW v1.2.6: Region checkboxes
        ctk.CTkCheckBox(
            row2,
            text="USA",
            variable=self.region_usa,
            width=60,
            command=lambda: self.toggle_region('usa')
        ).pack(side="left", padx=5)
        
        ctk.CTkCheckBox(
            row2,
            text="CAN",
            variable=self.region_can,
            width=60,
            command=lambda: self.toggle_region('can')
        ).pack(side="left", padx=5)
        
        # ✅ V1.7.5: Copy Sephora button
        ctk.CTkButton(
            row2,
            text="📋 Copy Sephora",
            width=120,
            fg_color="#2b7a3a",
            command=self.copy_sephora_format
        ).pack(side="left", padx=5)
        
        # ✅ V1.10.6: Total Item validation
        ctk.CTkLabel(row2, text="Total Item:", font=("Arial", 10, "bold")).pack(side="left", padx=(10, 2))
        self.total_item_entry = ctk.CTkEntry(row2, width=50, placeholder_text="1-20")
        # ✅ Chỉ insert nếu có value, nếu rỗng thì để trống để hiện placeholder
        saved_total = self.config.get('total_item', '')
        if saved_total:
            self.total_item_entry.insert(0, saved_total)
        self.total_item_entry.pack(side="left", padx=2)

        # ✅ V1.10.7: Checkbox Giảm 10$ và 20$ (mutually exclusive)
        self.discount_10_var = ctk.BooleanVar(value=self.config.get('discount_10', False))
        self.discount_10_checkbox = ctk.CTkCheckBox(
            row2,
            text="Giảm 10$",
            variable=self.discount_10_var,
            width=80,
            font=("Arial", 10, "bold"),
            command=lambda: self.on_discount_10_check()
        )
        self.discount_10_checkbox.pack(side="left", padx=(10, 2))

        self.discount_20_var = ctk.BooleanVar(value=self.config.get('discount_20', False))
        self.discount_20_checkbox = ctk.CTkCheckBox(
            row2,
            text="Giảm 20$",
            variable=self.discount_20_var,
            width=80,
            font=("Arial", 10, "bold"),
            command=lambda: self.on_discount_20_check()
        )
        self.discount_20_checkbox.pack(side="left", padx=2)

        # Right controls
        ctk.CTkButton(
            row2,
            text="+ Thêm Account",
            width=130,
            fg_color="#2b7a3a",
            command=self.add_account_dialog
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            row2,
            text="⚡ Đóng profile",
            width=100,
            fg_color="#8b0000",
            command=self.kill_all_drivers
        ).pack(side="right", padx=5)
        
        # ✅ V1.5.1: Row 3 - Items với Quantity riêng biệt
        row3 = ctk.CTkFrame(top, fg_color="transparent")
        row3.pack(fill="x", pady=5)
        
        # Item 1 + Qty 1
        ctk.CTkLabel(row3, text="Item 1:", font=("Arial", 10, "bold")).pack(side="left", padx=(5, 2))
        self.item1_entry = ctk.CTkEntry(row3, placeholder_text="Link sản phẩm 1", width=220)
        self.item1_entry.pack(side="left", padx=2)
        ctk.CTkLabel(row3, text="Qty:", font=("Arial", 9)).pack(side="left", padx=(3, 1))
        self.qty1_entry = ctk.CTkEntry(row3, placeholder_text="1", width=40)
        self.qty1_entry.insert(0, "1")
        self.qty1_entry.pack(side="left", padx=2)
        
        # Item 2 + Qty 2
        ctk.CTkLabel(row3, text="Item 2:", font=("Arial", 10, "bold")).pack(side="left", padx=(8, 2))
        self.item2_entry = ctk.CTkEntry(row3, placeholder_text="Link sản phẩm 2", width=220)
        self.item2_entry.pack(side="left", padx=2)
        ctk.CTkLabel(row3, text="Qty:", font=("Arial", 9)).pack(side="left", padx=(3, 1))
        self.qty2_entry = ctk.CTkEntry(row3, placeholder_text="1", width=40)
        self.qty2_entry.insert(0, "1")
        self.qty2_entry.pack(side="left", padx=2)
        
        # Item 3 + Qty 3
        ctk.CTkLabel(row3, text="Item 3:", font=("Arial", 10, "bold")).pack(side="left", padx=(8, 2))
        self.item3_entry = ctk.CTkEntry(row3, placeholder_text="Link sản phẩm 3", width=220)
        self.item3_entry.pack(side="left", padx=2)
        ctk.CTkLabel(row3, text="Qty:", font=("Arial", 9)).pack(side="left", padx=(3, 1))
        self.qty3_entry = ctk.CTkEntry(row3, placeholder_text="1", width=40)
        self.qty3_entry.insert(0, "1")
        self.qty3_entry.pack(side="left", padx=2)
        
        # Search box moved to row3
        self.search_entry = ctk.CTkEntry(row3, placeholder_text="Tìm kiếm...", width=120)
        self.search_entry.pack(side="right", padx=5)
        self.search_entry.bind("<KeyRelease>", self.on_search)  # ✅ Real-time search
        
        # ✅ V1.5.7: Row 4 - Coupon và Sample
        row4 = ctk.CTkFrame(top, fg_color="transparent")
        row4.pack(fill="x", pady=5)
        
        # Coupon
        ctk.CTkLabel(row4, text="Coupon:", font=("Arial", 10, "bold")).pack(side="left", padx=(5, 2))
        self.coupon_entry = ctk.CTkEntry(row4, placeholder_text="Mã giảm giá", width=150)
        self.coupon_entry.pack(side="left", padx=2)
        
        # ✅ V1.9.7: Coupon popup items (4 ô) - nhập tên thay vì số
        ctk.CTkLabel(row4, text="Items:", font=("Arial", 9)).pack(side="left", padx=(5, 1))
        self.coupon_item1_entry = ctk.CTkEntry(row4, placeholder_text="Brand/Name", width=100)
        self.coupon_item1_entry.pack(side="left", padx=1)
        self.coupon_item2_entry = ctk.CTkEntry(row4, placeholder_text="Brand/Name", width=100)
        self.coupon_item2_entry.pack(side="left", padx=1)
        self.coupon_item3_entry = ctk.CTkEntry(row4, placeholder_text="Brand/Name", width=100)
        self.coupon_item3_entry.pack(side="left", padx=1)
        self.coupon_item4_entry = ctk.CTkEntry(row4, placeholder_text="Brand/Name", width=100)
        self.coupon_item4_entry.pack(side="left", padx=1)
        
        # Sample 1
        ctk.CTkLabel(row4, text="Sample 1:", font=("Arial", 10, "bold")).pack(side="left", padx=(15, 2))
        self.sample1_entry = ctk.CTkEntry(row4, placeholder_text="Product Name", width=120)
        self.sample1_entry.pack(side="left", padx=2)
        
        # Sample 2
        ctk.CTkLabel(row4, text="Sample 2:", font=("Arial", 10, "bold")).pack(side="left", padx=(8, 2))
        self.sample2_entry = ctk.CTkEntry(row4, placeholder_text="Product Name", width=120)
        self.sample2_entry.pack(side="left", padx=2)

        # ✅ V1.10.7: Row 5 - Point Rewards (5 ô)
        row5 = ctk.CTkFrame(top, fg_color="transparent")
        row5.pack(fill="x", pady=5)

        ctk.CTkLabel(row5, text="Point 1:", font=("Arial", 10, "bold")).pack(side="left", padx=(5, 2))
        self.point1_entry = ctk.CTkEntry(row5, placeholder_text="Product Name", width=100)
        self.point1_entry.pack(side="left", padx=2)

        ctk.CTkLabel(row5, text="Point 2:", font=("Arial", 10, "bold")).pack(side="left", padx=(8, 2))
        self.point2_entry = ctk.CTkEntry(row5, placeholder_text="Product Name", width=100)
        self.point2_entry.pack(side="left", padx=2)

        ctk.CTkLabel(row5, text="Point 3:", font=("Arial", 10, "bold")).pack(side="left", padx=(8, 2))
        self.point3_entry = ctk.CTkEntry(row5, placeholder_text="Product Name", width=100)
        self.point3_entry.pack(side="left", padx=2)

        ctk.CTkLabel(row5, text="Point 4:", font=("Arial", 10, "bold")).pack(side="left", padx=(8, 2))
        self.point4_entry = ctk.CTkEntry(row5, placeholder_text="Product Name", width=100)
        self.point4_entry.pack(side="left", padx=2)

        ctk.CTkLabel(row5, text="Point 5:", font=("Arial", 10, "bold")).pack(side="left", padx=(8, 2))
        self.point5_entry = ctk.CTkEntry(row5, placeholder_text="Product Name", width=100)
        self.point5_entry.pack(side="left", padx=2)

    def on_discount_10_check(self):
        """Nếu tích Giảm 10$ thì bỏ tích Giảm 20$"""
        if self.discount_10_var.get():
            self.discount_20_var.set(False)

    def on_discount_20_check(self):
        """Nếu tích Giảm 20$ thì bỏ tích Giảm 10$"""
        if self.discount_20_var.get():
            self.discount_10_var.set(False)

    def create_table(self, parent):
        """Tạo table"""
        center = ctk.CTkFrame(parent, fg_color="#2b2b2b")
        center.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Style
        style = ttk.Style()
        style.theme_use('default')
        
        # Configure Treeview with GRIDLINES
        style.configure("Treeview",
                       background="#2a2d2e",
                       foreground="white",
                       rowheight=25,
                       fieldbackground="#2a2d2e",
                       borderwidth=1,
                       relief="solid")
        
        style.map('Treeview', background=[('selected', '#22559b')])
        
        # Configure Treeview.Heading
        style.configure("Treeview.Heading",
                       background="#1f6aa5",
                       foreground="white",
                       relief="raised",
                       borderwidth=1)
        
        style.map("Treeview.Heading", background=[('active', '#144870')])
        
        # Treeview with MULTI-SELECT
        # ✅ V1.7.0: Đổi thứ tự Email trước Password
        columns = ("STT", "ID", "Name", "Email", "Password", "Phone", "Create", "Last", "Status", "Kho", "Order ID", "Đơn", "Gift 1", "Gift 2", "Note", "Proxy")
        self.tree = ttk.Treeview(center, columns=columns, show="tree headings", selectmode="extended")
        
        # ✅ V1.7.0: Default widths (Email trước Password)
        default_widths = {"STT": 50, "ID": 100, "Name": 100, "Email": 180, "Password": 100,
                         "Phone": 100, "Create": 90, "Last": 90, "Status": 150, "Kho": 120, 
                         "Order ID": 120, "Đơn": 80, "Gift 1": 150, "Gift 2": 150, "Note": 80, "Proxy": 130}
        
        # ✅ V1.7.0: Load column settings from config
        saved_widths = self.config.get('column_widths', {})
        saved_visibility = self.config.get('column_visibility', {})
        
        # Initialize visibility for all columns (default: visible)
        for col in columns:
            if col not in saved_visibility:
                self.column_visibility[col] = True
            else:
                self.column_visibility[col] = saved_visibility[col]
        
        # ✅ NEW: Sort state tracking
        self.sort_reverse = {}
        
        for col in columns:
            # ✅ NEW: Bind click để sort
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            
            # ✅ V1.7.0: Apply width from config or default
            width = saved_widths.get(col, default_widths[col])
            self.tree.column(col, width=width, anchor="w")
            self.column_widths[col] = width
            
            self.sort_reverse[col] = False  # Track sort direction
        
        # ✅ V1.7.0: Apply column visibility
        self.apply_column_visibility()
        
        # Hide tree column but keep for selection
        self.tree.column("#0", width=0, stretch=False)
        
        # Scrollbars
        vsb = ttk.Scrollbar(center, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(center, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        center.grid_rowconfigure(0, weight=1)
        center.grid_columnconfigure(0, weight=1)
        
        # Context menu
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Update status on selection change
        self.tree.bind("<<TreeviewSelect>>", self.on_selection_change)
        
        # ✅ NEW: Ctrl+A để select all
        self.tree.bind("<Control-a>", self.select_all)
        self.tree.bind("<Control-A>", self.select_all)
        
        # ✅ NEW: Drag mouse để select (click và kéo)
        self.drag_start_item = None
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<B1-Motion>", self.on_drag_motion)
        
        # ✅ V1.7.0: Auto-save khi resize column
        self.tree.bind("<ButtonRelease-1>", self.on_column_resize, add="+")
    
    def create_status_bar(self, parent):
        """Status bar"""
        bottom = ctk.CTkFrame(parent, fg_color="#1a1a1a", height=30)
        bottom.pack(side="bottom", fill="x", padx=10, pady=5)
        
        self.status_label = ctk.CTkLabel(bottom, text="Tổng: 0     Đang chọn: 0", anchor="w")
        self.status_label.pack(side="left", padx=10)
    
    def show_context_menu(self, event):
        """Context menu"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        # ✅ FIX: Preserve multi-selection khi right-click
        current_selection = self.tree.selection()
        if item not in current_selection:
            # Chỉ set selection khi click vào item chưa được chọn
            self.tree.selection_set(item)
        
        menu = ctk.CTkToplevel(self)
        menu.wm_overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color="#2b2b2b")
        
        # ✅ V1.6.5: Copy submenu (gọn hơn)
        ctk.CTkButton(
            menu,
            text="📋 Copy",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.show_copy_submenu(menu, event)
        ).pack(fill="x", pady=1)
        
        # Separator
        ctk.CTkLabel(menu, text="─" * 30, text_color="gray").pack(fill="x")
        
        # Mở Profile
        ctk.CTkButton(
            menu,
            text="▶ Mở Profile",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.open_profile(menu)
        ).pack(fill="x", pady=1)
        
        # ✅ FIXED: Chuyển Folder - Click thay vì hover
        ctk.CTkButton(
            menu,
            text="📁 Chuyển Folder",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.show_folder_submenu_click(menu)
        ).pack(fill="x", pady=1)
        
        # ✅ V1.6.5: Chọn Kho
        ctk.CTkButton(
            menu,
            text="🏪 Chọn Kho",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.show_warehouse_submenu(menu)
        ).pack(fill="x", pady=1)
        
        # Update Account
        ctk.CTkButton(
            menu,
            text="🔄 Update Proxy",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.update_account_dialog(menu)
        ).pack(fill="x", pady=1)
        
        # ✅ NEW v1.2.3: Clear Proxy
        ctk.CTkButton(
            menu,
            text="❌ Clear Proxy",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.clear_proxy(menu)
        ).pack(fill="x", pady=1)
        
        # ✅ NEW: Set Note
        ctk.CTkButton(
            menu,
            text="📝 Set Note",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.set_note_dialog(menu)
        ).pack(fill="x", pady=1)
        
        # ✅ NEW: Set Status
        ctk.CTkButton(
            menu,
            text="⚡ Set Status",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=lambda: self.set_status_dialog(menu)
        ).pack(fill="x", pady=1)
        
        # ✅ V1.7.7: Restore Gift
        ctk.CTkButton(
            menu,
            text="↩️ Restore Gift",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#2b7a3a",
            command=lambda: self.restore_gifts(menu)
        ).pack(fill="x", pady=1)
        
        # ✅ NEW: 2 Delete options
        # Separator
        ctk.CTkLabel(menu, text="─" * 30, text_color="gray").pack(fill="x")
        
        ctk.CTkButton(
            menu,
            text="🗑️ Xóa Profile (GPM only)",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#8b0000",
            command=lambda: self.delete_profiles_only(menu)
        ).pack(fill="x", pady=1)
        
        ctk.CTkButton(
            menu,
            text="🗑️ Xóa Account (Tool + GPM)",
            width=200,
            anchor="w",
            fg_color="transparent",
            hover_color="#8b0000",
            command=lambda: self.delete_accounts_and_profiles(menu)
        ).pack(fill="x", pady=1)
        
        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_set()
    
    def show_folder_submenu(self, event, parent_menu):
        """Show folder submenu"""
        submenu = ctk.CTkToplevel(self)
        submenu.wm_overrideredirect(True)
        x = parent_menu.winfo_x() + parent_menu.winfo_width()
        y = parent_menu.winfo_y()
        submenu.geometry(f"+{x}+{y}")
        submenu.configure(fg_color="#2b2b2b")
        
        for folder in self.folders:
            btn = ctk.CTkButton(
                submenu,
                text=folder,
                width=180,
                anchor="w",
                fg_color="transparent",
                hover_color="#3a3a3a",
                command=lambda f=folder: self.move_to_folder(f, submenu, parent_menu)
            )
            btn.pack(fill="x", pady=1)
        
        # ✅ FIX: Multiple ways to close submenu
        submenu.bind("<FocusOut>", lambda e: submenu.destroy())
        submenu.bind("<Leave>", lambda e: submenu.after(500, lambda: self.check_and_close_submenu(submenu)))
        
        # Auto close after 10 seconds if no interaction
        submenu.after(10000, lambda: self.safe_destroy_widget(submenu))
    
    def show_folder_submenu_click(self, parent_menu):
        """✅ NEW: Show folder submenu on CLICK (simpler, no hover bugs)"""
        submenu = ctk.CTkToplevel(self)
        submenu.wm_overrideredirect(True)
        
        # Position next to parent menu
        x = parent_menu.winfo_x() + parent_menu.winfo_width()
        y = parent_menu.winfo_y()
        submenu.geometry(f"+{x}+{y}")
        submenu.configure(fg_color="#2b2b2b")
        
        # Add folder buttons
        for folder in self.folders:
            btn = ctk.CTkButton(
                submenu,
                text=folder,
                width=180,
                anchor="w",
                fg_color="transparent",
                hover_color="#3a3a3a",
                command=lambda f=folder: self.move_to_folder(f, submenu, parent_menu)
            )
            btn.pack(fill="x", pady=1)
        
        # Simple close on focus out
        submenu.bind("<FocusOut>", lambda e: self.safe_destroy_widget(submenu))
        
        # Focus the submenu
        submenu.focus_set()
    
    def show_copy_submenu(self, parent_menu, event):
        """✅ V1.6.5: Show Copy submenu"""
        submenu = ctk.CTkToplevel(self)
        submenu.wm_overrideredirect(True)
        
        # Position next to parent menu
        x = parent_menu.winfo_x() + parent_menu.winfo_width()
        y = parent_menu.winfo_y()
        submenu.geometry(f"+{x}+{y}")
        submenu.configure(fg_color="#2b2b2b")
        
        # Copy options
        copy_items = ["Email", "Password", "Email|Password", "Proxy", "Profile ID", "Order ID", "Status"]
        for item_text in copy_items:
            btn = ctk.CTkButton(
                submenu,
                text=item_text,
                width=180,
                anchor="w",
                fg_color="transparent",
                hover_color="#3a3a3a",
                command=lambda t=item_text: self.copy_field_from_submenu(t, submenu, parent_menu)
            )
            btn.pack(fill="x", pady=1)
        
        # Simple close on focus out
        submenu.bind("<FocusOut>", lambda e: self.safe_destroy_widget(submenu))
        submenu.focus_set()
    
    def show_warehouse_submenu(self, parent_menu):
        """✅ V1.6.5: Show Warehouse submenu để chọn kho cho account"""
        submenu = ctk.CTkToplevel(self)
        submenu.wm_overrideredirect(True)
        
        # Position next to parent menu
        x = parent_menu.winfo_x() + parent_menu.winfo_width()
        y = parent_menu.winfo_y()
        submenu.geometry(f"+{x}+{y}")
        submenu.configure(fg_color="#2b2b2b")
        
        # ✅ Option to clear warehouse
        clear_btn = ctk.CTkButton(
            submenu,
            text="❌ Không chọn kho",
            width=180,
            anchor="w",
            fg_color="transparent",
            hover_color="#8b0000",
            command=lambda: self.assign_warehouse_to_account("", submenu, parent_menu)
        )
        clear_btn.pack(fill="x", pady=1)
        
        # Separator
        if self.warehouses:
            ctk.CTkLabel(submenu, text="─" * 25, text_color="gray").pack(fill="x")
        
        # Warehouse buttons
        if not self.warehouses:
            ctk.CTkLabel(
                submenu,
                text="Chưa có kho nào!",
                text_color="gray"
            ).pack(fill="x", pady=5, padx=10)
        else:
            for wh in self.warehouses:
                btn = ctk.CTkButton(
                    submenu,
                    text=wh.name,
                    width=180,
                    anchor="w",
                    fg_color="transparent",
                    hover_color="#3a3a3a",
                    command=lambda w=wh.name: self.assign_warehouse_to_account(w, submenu, parent_menu)
                )
                btn.pack(fill="x", pady=1)
        
        # Simple close on focus out
        submenu.bind("<FocusOut>", lambda e: self.safe_destroy_widget(submenu))
        submenu.focus_set()
    
    def copy_field_from_submenu(self, field_type, submenu, parent_menu):
        """✅ V1.6.5: Copy field from submenu"""
        submenu.destroy()
        parent_menu.destroy()
        
        selected = self.tree.selection()
        if not selected:
            return
        
        # Sử dụng lại logic copy_field
        if field_type == "Status":
            self.copy_status(None)
        else:
            self.copy_field(field_type, None)
    
    def assign_warehouse_to_account(self, warehouse_name, submenu, parent_menu):
        """✅ V1.6.5: Gán kho cho account"""
        submenu.destroy()
        parent_menu.destroy()
        
        selected = self.tree.selection()
        if not selected:
            return
        
        # Update warehouse_name cho các accounts được chọn
        count = 0
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            email = values[3]  # Email column
            
            for acc in self.accounts:
                if acc.email == email:
                    acc.warehouse_name = warehouse_name
                    count += 1
                    break
        
        # Save và refresh
        self.save_accounts()
        self.refresh_table()
        
        # Thông báo
        if warehouse_name:
            messagebox.showinfo("✅ OK", f"Đã gán kho '{warehouse_name}' cho {count} account(s)!")
        else:
            messagebox.showinfo("✅ OK", f"Đã xóa kho cho {count} account(s)!")
    
    def check_and_close_submenu(self, submenu):
        """Check if mouse still outside and close submenu"""
        try:
            if submenu.winfo_exists():
                # Check mouse position
                x, y = submenu.winfo_pointerx(), submenu.winfo_pointery()
                submenu_x = submenu.winfo_rootx()
                submenu_y = submenu.winfo_rooty()
                submenu_width = submenu.winfo_width()
                submenu_height = submenu.winfo_height()
                
                # If mouse is outside submenu area, close it
                if not (submenu_x <= x <= submenu_x + submenu_width and 
                       submenu_y <= y <= submenu_y + submenu_height):
                    submenu.destroy()
        except:
            pass
    
    def safe_destroy_widget(self, widget):
        """Safely destroy widget if it still exists"""
        try:
            if widget.winfo_exists():
                widget.destroy()
        except:
            pass
    
    def copy_field(self, field_type, menu):
        """Copy field to clipboard - support multiple selections"""
        selected = self.tree.selection()
        if not selected:
            return
        
        # ✅ Copy tất cả selected accounts (mỗi dòng 1 account)
        lines = []
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            
            # ✅ V1.7.0: Email=3, Password=4 (sau khi đổi thứ tự)
            if field_type == "Email":
                text = values[3]
            elif field_type == "Password":
                text = values[4]
            elif field_type == "Email|Password":
                text = f"{values[3]}|{values[4]}"
            elif field_type == "Proxy":
                text = values[14]  # Proxy index cũng thay đổi
            elif field_type == "Profile ID":
                text = values[1]
            elif field_type == "Order ID":
                text = values[10]  # ✅ V1.7.7: Order ID column
            else:
                text = ""
            
            lines.append(text)
        
        # Join tất cả lines
        result = "\n".join(lines)
        
        self.clipboard_clear()
        self.clipboard_append(result)
        menu.destroy()
        
        # Thông báo
        if len(selected) == 1:
            messagebox.showinfo("✅ OK", f"Đã copy: {result[:50]}...")
        else:
            messagebox.showinfo("✅ OK", f"Đã copy {len(selected)} dòng!")
    
    
    def open_profile(self, menu):
        """✅ FIXED: Mở TẤT CẢ GPM profiles đã chọn (không dùng scale/resolution từ settings)"""
        selected = self.tree.selection()
        if not selected:
            return
        
        menu.destroy()
        
        # ✅ FIX: Mở tất cả profiles đã chọn
        success_count = 0
        error_count = 0
        
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            profile_id = values[1]
            email = values[3]
            
            # Find account
            account = None
            for acc in self.accounts:
                if acc.email == email:
                    account = acc
                    break
            
            if not account:
                error_count += 1
                continue
            
            # ✅ FIX: Check if profile needs to be created (bao gồm empty ID)
            if not account.id or account.id.startswith("PENDING_") or account.id.startswith("LOCAL_"):
                # Create GPM profile now
                # ✅ V1.10.9: Thêm timestamp vào profile name để tránh tái sử dụng profile cũ
                profile_name = f"Sephora_{account.email.split('@')[0]}_{int(time.time())}"
                # ✅ V1.10.0: KHÔNG truyền config - dùng giá trị mặc định
                profile_id_new, _ = self.gpm_api.create_profile(profile_name, 0, account.proxy, None)
                
                if profile_id_new:
                    account.id = profile_id_new
                    account.status = "GPM Profile Created"
                else:
                    account.status = "Create Failed"
                    error_count += 1
                    continue
            
            # ✅ NEW v1.2.4: Update proxy vào profile trước khi mở (cả profile mới & cũ)
            if account.proxy:
                # ✅ V1.10.0: KHÔNG truyền config - dùng giá trị mặc định
                self.gpm_api.update_profile(account.id, account.proxy, None)
            
            # ✅ V1.10.0: Mở profile KHÔNG dùng scale/resolution từ settings
            profile_data = self.gpm_api.start_profile(account.id, None)
            if profile_data:
                account.status = "Profile Opened"
                account.last_run = datetime.now().strftime("%H:%M %d/%m")
                success_count += 1
            else:
                account.status = "Open Failed"
                error_count += 1
        
        self.save_accounts()
        self.refresh_table()
        
        # Show result (chỉ hiện nếu có lỗi)
        if error_count > 0 and success_count > 0:
            messagebox.showwarning("⚠️ Một phần thành công", 
                                  f"✅ Mở thành công: {success_count}\n❌ Lỗi: {error_count}\n\nCheck status trong table!")
        elif error_count > 0 and success_count == 0:
            messagebox.showerror("❌ Lỗi", 
                               f"Không thể mở profile!\n\nKiểm tra:\n- GPM Login đang chạy\n- API URL đúng trong Settings")

    
    def move_to_folder(self, folder, submenu, parent_menu):
        """Move accounts to folder"""
        selected = self.tree.selection()
        if not selected:
            return
        
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            email = values[3]
            
            for acc in self.accounts:
                if acc.email == email:
                    acc.folder = folder
        
        submenu.destroy()
        parent_menu.destroy()
        
        self.refresh_table()
        self.save_accounts()
        messagebox.showinfo("✅ OK", f"Đã chuyển {len(selected)} account(s) vào: {folder}")
    
    def delete_selected(self, menu):
        """Xóa accounts"""
        selected = self.tree.selection()
        if not selected:
            return
        
        menu.destroy()
        
        if not messagebox.askyesno("⚠️ Xác nhận", f"Xóa {len(selected)} account(s)?"):
            return
        
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            email = values[3]
            
            # Xóa account
            self.accounts = [acc for acc in self.accounts if acc.email != email]
        
        self.refresh_table()
        self.save_accounts()
        messagebox.showinfo("✅ OK", f"Đã xóa {len(selected)} account(s)!")
    
    # ==================== VERSION 1.2 - NEW FUNCTIONS ====================
    
    def sort_column(self, col):
        """✅ NEW: Sort column khi click vào heading"""
        # Get current items
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        
        # Determine sort order
        reverse = self.sort_reverse[col]
        
        # Sort items
        try:
            # Try numeric sort first
            items.sort(key=lambda x: float(x[0]) if x[0] else 0, reverse=reverse)
        except (ValueError, TypeError):
            # Fall back to string sort
            items.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)
        
        # Rearrange items in sorted order
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)
        
        # Toggle sort direction for next time
        self.sort_reverse[col] = not reverse
        
        # Update heading to show sort direction
        arrow = " ▼" if reverse else " ▲"
        # Clear all arrows first
        for c in self.sort_reverse.keys():
            self.tree.heading(c, text=c.replace(" ▲", "").replace(" ▼", ""))
        # Add arrow to sorted column
        self.tree.heading(col, text=col + arrow)
    
    def select_all(self, event):
        """✅ NEW: Ctrl+A để select all"""
        all_items = self.tree.get_children()
        self.tree.selection_set(all_items)
        return "break"  # Prevent default behavior
    
    def on_drag_start(self, event):
        """✅ NEW: Bắt đầu drag select"""
        # Get item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_start_item = item
            # Don't clear selection yet - let motion handle it
    
    def on_drag_motion(self, event):
        """✅ NEW: Drag mouse để select multiple"""
        if not self.drag_start_item:
            return
        
        # Get current item under cursor
        current_item = self.tree.identify_row(event.y)
        if not current_item:
            return
        
        # Get all items
        all_items = self.tree.get_children()
        if not all_items:
            return
        
        try:
            # Find indices
            start_idx = all_items.index(self.drag_start_item)
            end_idx = all_items.index(current_item)
            
            # Determine range
            if start_idx <= end_idx:
                items_to_select = all_items[start_idx:end_idx + 1]
            else:
                items_to_select = all_items[end_idx:start_idx + 1]
            
            # Select range
            self.tree.selection_set(items_to_select)
        except (ValueError, IndexError):
            pass
    
    def delete_profiles_only(self, menu):
        """✅ NEW: Xóa chỉ GPM profiles, giữ data trong tool"""
        selected = self.tree.selection()
        if not selected:
            return
        
        menu.destroy()
        
        if not messagebox.askyesno(
            "⚠️ Xác nhận",
            f"Xóa {len(selected)} GPM profile(s)?\n\n"
            "📌 Data (email|password) vẫn giữ trong tool\n"
            "🗑️ Chỉ xóa profile ở GPM Login"
        ):
            return
        
        deleted_count = 0
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            profile_id = values[1]  # ID column
            email = values[3]
            
            # Find account và xóa GPM profile
            for acc in self.accounts:
                if acc.email == email:
                    if acc.id and self.gpm_api.delete_profile(acc.id):
                        deleted_count += 1
                    # ✅ FIX: Reset về PENDING_ để có thể tạo lại profile
                    acc.id = f"PENDING_{int(time.time())}"
                    acc.status = "Ready"
                    break
        
        self.refresh_table()
        self.save_accounts()
        messagebox.showinfo(
            "✅ OK",
            f"Đã xóa {deleted_count} GPM profile(s)!\n\n"
            f"📌 {len(selected)} account(s) vẫn còn trong tool"
        )
    
    def delete_accounts_and_profiles(self, menu):
        """✅ NEW: Xóa cả accounts trong tool VÀ GPM profiles"""
        selected = self.tree.selection()
        if not selected:
            return
        
        menu.destroy()
        
        if not messagebox.askyesno(
            "⚠️ Xác nhận",
            f"Xóa HOÀN TOÀN {len(selected)} account(s)?\n\n"
            "🗑️ Xóa data trong tool\n"
            "🗑️ Xóa profile ở GPM Login\n\n"
            "⚠️ KHÔNG THỂ KHÔI PHỤC!"
        ):
            return
        
        deleted_gpm = 0
        emails_to_delete = []
        
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            profile_id = values[1]
            email = values[3]
            emails_to_delete.append(email)
            
            # Xóa GPM profile nếu có
            for acc in self.accounts:
                if acc.email == email:
                    if acc.id and self.gpm_api.delete_profile(acc.id):
                        deleted_gpm += 1
                    break
        
        # Xóa accounts khỏi tool
        self.accounts = [acc for acc in self.accounts if acc.email not in emails_to_delete]
        
        self.refresh_table()
        self.save_accounts()
        messagebox.showinfo(
            "✅ OK",
            f"Đã xóa hoàn toàn {len(selected)} account(s)!\n\n"
            f"🗑️ Tool: {len(selected)} accounts\n"
            f"🗑️ GPM: {deleted_gpm} profiles"
        )
    
    def add_account_dialog(self):
        """Dialog thêm account"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Account")
        dialog.geometry("700x550")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_bar = ctk.CTkFrame(frame, fg_color="#1f6aa5", height=50)
        title_bar.pack(fill="x", pady=(0, 10))
        title_bar.pack_propagate(False)
        
        ctk.CTkLabel(title_bar, text="Add Account", 
                    font=("Arial", 16, "bold")).pack(side="left", padx=15, pady=10)
        
        ctk.CTkButton(title_bar, text="✕", width=40, height=30,
                     fg_color="#8b0000", command=dialog.destroy).pack(side="right", padx=10)
        
        # Site config
        config_frame = ctk.CTkFrame(frame, fg_color="transparent")
        config_frame.pack(fill="x", pady=10)
        
        site_entry = ctk.CTkEntry(config_frame, width=150, placeholder_text="fastorderdp.site")
        site_entry.pack(side="left", padx=5)
        
        count_entry = ctk.CTkEntry(config_frame, width=80, placeholder_text="1000")
        count_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(config_frame, text="Random", width=100).pack(side="left", padx=5)
        
        # Textarea
        ctk.CTkLabel(frame, text="List account (Format: Email|Password):", 
                    anchor="w", font=("Arial", 11, "bold")).pack(fill="x", pady=5)
        
        accounts_text = ctk.CTkTextbox(frame, height=250)
        accounts_text.pack(fill="both", expand=True, pady=5)
        accounts_text.insert("1.0", "# Mỗi dòng 1 account\n# Format: email|password\n\n")
        
        # Options
        options_frame = ctk.CTkFrame(frame, fg_color="transparent")
        options_frame.pack(fill="x", pady=10)
        
        format_label = ctk.CTkLabel(options_frame, text="Định dạng: Email|Password")
        format_label.pack(side="left", padx=10)
        
        proxy_var = ctk.BooleanVar()
        proxy_check = ctk.CTkCheckBox(options_frame, text="Thêm proxy rotating://",
                                      variable=proxy_var)
        proxy_check.pack(side="left", padx=20)
        
        pass_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        pass_frame.pack(side="right")
        
        ctk.CTkLabel(pass_frame, text="Pass mặc định:").pack(side="left", padx=5)
        default_pass = ctk.CTkEntry(pass_frame, width=120)
        default_pass.pack(side="left", padx=5)
        
        # Add button
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        def do_add():
            text = accounts_text.get("1.0", "end").strip()
            lines = [l.strip() for l in text.split('\n') if l.strip() and not l.startswith('#')]
            
            if not lines:
                messagebox.showerror("❌ Lỗi", "Chưa nhập account nào!")
                return
            
            added = 0
            errors = 0
            
            # FAST MODE: Không tạo GPM profile ngay
            # Profile sẽ được tạo khi click "Mở Profile" hoặc "Chạy"
            for line in lines:
                parts = line.split('|')
                if len(parts) >= 2:
                    email = parts[0].strip()
                    password = parts[1].strip()
                elif len(parts) == 1 and default_pass.get():
                    email = parts[0].strip()
                    password = default_pass.get()
                else:
                    errors += 1
                    continue
                
                # Check duplicate
                if any(acc.email == email for acc in self.accounts):
                    errors += 1
                    continue
                
                # Tạo ID tạm thời - GPM profile sẽ được tạo sau
                profile_id = f"PENDING_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{added}"
                
                # Create account
                acc = Account(email, password, profile_id, "", "", self.folder_var.get())
                self.accounts.append(acc)
                added += 1
            
            self.refresh_table()
            self.save_accounts()
            
            msg = f"✅ Đã thêm: {added} account(s)\n"
            if errors > 0:
                msg += f"❌ Lỗi: {errors} dòng\n\n"
            msg += "ℹ️ GPM profiles sẽ được tạo khi bạn mở profile."
            
            messagebox.showinfo("Kết quả", msg)
            dialog.destroy()
        
        ctk.CTkButton(btn_frame, text="+ Thêm", width=120, height=35,
                     fg_color="#2b7a3a", command=do_add).pack(side="right", padx=5)
        
        ctk.CTkButton(btn_frame, text="Hủy", width=120, height=35,
                     fg_color="#8b0000", command=dialog.destroy).pack(side="right", padx=5)
    
    def update_account_dialog(self, menu):
        """Dialog update proxy"""
        selected = self.tree.selection()
        if not selected:
            menu.destroy()
            messagebox.showerror("❌ Lỗi", "Chọn account trước!")
            return
        
        menu.destroy()
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Update Proxy")
        dialog.geometry("700x550")  # ✅ IMPROVED v1.2.4: Tăng size dialog
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_bar = ctk.CTkFrame(frame, fg_color="#1f6aa5", height=50)
        title_bar.pack(fill="x", pady=(0, 10))
        title_bar.pack_propagate(False)
        
        ctk.CTkLabel(title_bar, text="Update Proxy", 
                    font=("Arial", 16, "bold")).pack(side="left", padx=15, pady=10)
        
        ctk.CTkButton(title_bar, text="✕", width=40, height=30,
                     fg_color="#8b0000", command=dialog.destroy).pack(side="right", padx=10)
        
        # Textarea
        ctk.CTkLabel(frame, text="List proxy (Format: host:port:user:pass):", 
                    anchor="w", font=("Arial", 11, "bold")).pack(fill="x", pady=5)
        
        proxy_text = ctk.CTkTextbox(frame, height=320)  # ✅ IMPROVED v1.2.4: Tăng height
        proxy_text.pack(fill="both", expand=True, pady=5)
        proxy_text.insert("1.0", "# Mỗi dòng 1 proxy\n# Format: host:port:user:pass\n\n")
        
        # To All checkbox
        to_all_var = ctk.BooleanVar()
        to_all_check = ctk.CTkCheckBox(frame, text="☑ Apply cho TẤT CẢ accounts",
                                       variable=to_all_var, font=("Arial", 11, "bold"))
        to_all_check.pack(anchor="w", pady=10)
        
        # Save button
        def do_update():
            text = proxy_text.get("1.0", "end").strip()
            proxies = [l.strip() for l in text.split('\n') if l.strip() and not l.startswith('#')]
            
            if not proxies:
                messagebox.showerror("❌ Lỗi", "Chưa nhập proxy nào!")
                return
            
            # Get target accounts
            if to_all_var.get():
                targets = self.accounts
            else:
                targets = []
                for item_id in selected:
                    values = self.tree.item(item_id)['values']
                    email = values[3]
                    for acc in self.accounts:
                        if acc.email == email:
                            targets.append(acc)
            
            # Update proxy
            for i, acc in enumerate(targets):
                acc.proxy = proxies[i % len(proxies)]
            
            self.refresh_table()
            self.save_accounts()
            
            messagebox.showinfo("✅ OK", f"Đã update proxy cho {len(targets)} account(s)!")
            dialog.destroy()
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="💾 Lưu", width=120, height=35,
                     fg_color="#2b7a3a", command=do_update).pack(side="right", padx=5)
        
        ctk.CTkButton(btn_frame, text="Hủy", width=120, height=35,
                     fg_color="#8b0000", command=dialog.destroy).pack(side="right", padx=5)
    
    def clear_proxy(self, menu):
        """✅ NEW v1.2.3: Xóa/Clear proxy cho selected accounts"""
        selected = self.tree.selection()
        if not selected:
            menu.destroy()
            messagebox.showerror("❌ Lỗi", "Chọn account trước!")
            return
        
        menu.destroy()
        
        # Confirm
        if not messagebox.askyesno(
            "⚠️ Xác nhận",
            f"Xóa proxy cho {len(selected)} account(s)?\n\n"
            "Proxy sẽ được set về rỗng (không proxy)"
        ):
            return
        
        # Clear proxy cho tất cả selected accounts
        count = 0
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            email = values[3]
            
            for acc in self.accounts:
                if acc.email == email:
                    acc.proxy = ""
                    
                    # ✅ FIX v1.2.4: Update proxy vào GPM để xóa luôn (không chỉ trong tool)
                    if acc.id:
                        self.gpm_api.update_profile(acc.id, "", self.config)
                    
                    count += 1
                    break
        
        self.refresh_table()
        self.save_accounts()
        
        messagebox.showinfo("✅ OK", f"Đã xóa proxy cho {count} account(s)!")
    
    def set_note_dialog(self, menu):
        """✅ NEW: Dialog set note cho selected accounts"""
        selected = self.tree.selection()
        if not selected:
            menu.destroy()
            messagebox.showerror("❌ Lỗi", "Chọn account trước!")
            return
        
        menu.destroy()
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Set Note")
        dialog.geometry("500x250")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        ctk.CTkLabel(
            frame,
            text=f"📝 Set Note cho {len(selected)} account(s)",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
        # Info
        ctk.CTkLabel(
            frame,
            text="Nhập note muốn set (ví dụ: Error, Success, Testing...)",
            text_color="gray"
        ).pack(pady=5)
        
        # Input
        note_entry = ctk.CTkEntry(frame, height=40, placeholder_text="Nhập note...")
        note_entry.pack(fill="x", pady=10)
        note_entry.focus()
        
        # Buttons
        def do_set():
            note_text = note_entry.get().strip()
            if not note_text:
                messagebox.showerror("❌ Lỗi", "Chưa nhập note!")
                return
            
            # Update note cho tất cả accounts đã chọn
            count = 0
            for item_id in selected:
                values = self.tree.item(item_id)['values']
                email = values[3]
                
                for acc in self.accounts:
                    if acc.email == email:
                        acc.note = note_text
                        count += 1
                        break
            
            self.refresh_table()
            self.save_accounts()
            
            messagebox.showinfo("✅ OK", f"Đã set note cho {count} account(s)!")
            dialog.destroy()
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="✅ Xác nhận",
            width=120,
            height=35,
            fg_color="#2b7a3a",
            command=do_set
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="❌ Hủy",
            width=120,
            height=35,
            fg_color="#8b0000",
            command=dialog.destroy
        ).pack(side="right", padx=5)
        
        # Enter key để submit
        note_entry.bind("<Return>", lambda e: do_set())
    
    def set_status_dialog(self, menu):
        """✅ NEW: Dialog set status cho selected accounts"""
        selected = self.tree.selection()
        if not selected:
            menu.destroy()
            messagebox.showerror("❌ Lỗi", "Chọn account trước!")
            return
        
        menu.destroy()
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Set Status")
        dialog.geometry("550x350")  # ✅ V1.3.4: Tăng size từ 500x300 lên 550x350
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        ctk.CTkLabel(
            frame,
            text=f"⚡ Set Status cho {len(selected)} account(s)",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
        # Info
        ctk.CTkLabel(
            frame,
            text="Chọn status hoặc nhập custom status",
            text_color="gray"
        ).pack(pady=5)
        
        # Dropdown với các status phổ biến
        status_var = ctk.StringVar(value="Ready")
        status_dropdown = ctk.CTkComboBox(
            frame,
            values=["Ready", "Running", "Success", "Error", "Pending", "Stopped", "Banned"],
            variable=status_var,
            height=40,
            width=200
        )
        status_dropdown.pack(pady=10)
        
        # Hoặc nhập custom
        ctk.CTkLabel(frame, text="Hoặc nhập custom:", text_color="gray").pack(pady=5)
        custom_entry = ctk.CTkEntry(frame, height=40, placeholder_text="Custom status...")
        custom_entry.pack(fill="x", pady=5)
        
        # Buttons
        def do_set():
            # Ưu tiên custom entry nếu có nhập
            status_text = custom_entry.get().strip()
            if not status_text:
                status_text = status_var.get()
            
            if not status_text:
                messagebox.showerror("❌ Lỗi", "Chọn hoặc nhập status!")
                return
            
            # Update status cho tất cả accounts đã chọn
            count = 0
            for item_id in selected:
                values = self.tree.item(item_id)['values']
                email = values[3]
                
                for acc in self.accounts:
                    if acc.email == email:
                        acc.status = status_text
                        count += 1
                        break
            
            self.refresh_table()
            self.save_accounts()
            
            messagebox.showinfo("✅ OK", f"Đã set status cho {count} account(s)!")
            dialog.destroy()
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="✅ Xác nhận",
            width=150,  # ✅ V1.3.4: Tăng từ 120 lên 150
            height=45,  # ✅ V1.3.4: Tăng từ 35 lên 45
            font=("Arial", 14, "bold"),  # ✅ V1.3.4: Thêm font to hơn
            fg_color="#2b7a3a",
            command=do_set
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="❌ Hủy",
            width=150,  # ✅ V1.3.4: Tăng từ 120 lên 150
            height=45,  # ✅ V1.3.4: Tăng từ 35 lên 45
            font=("Arial", 14, "bold"),  # ✅ V1.3.4: Thêm font to hơn
            fg_color="#8b0000",
            command=dialog.destroy
        ).pack(side="right", padx=5)
        
        # Enter key để submit
        custom_entry.bind("<Return>", lambda e: do_set())
    
    def copy_status(self, menu):
        """
        ✅ NEW v1.2.7: Copy Status của selected accounts vào clipboard
        """
        selected = self.tree.selection()
        if not selected:
            menu.destroy()
            messagebox.showerror("❌ Lỗi", "Chọn account trước!")
            return
        
        menu.destroy()
        
        # Get status của các accounts được chọn
        status_list = []
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            email = values[3]
            status = values[8]  # Status column
            
            status_list.append(f"{email}: {status}")
        
        # Copy vào clipboard
        status_text = "\n".join(status_list)
        self.clipboard_clear()
        self.clipboard_append(status_text)
        self.update()  # Required for clipboard to work
        
        messagebox.showinfo(
            "✅ Đã copy!", 
            f"Đã copy status của {len(selected)} account(s) vào clipboard!\n\n"
            f"Preview:\n{status_text[:200]}{'...' if len(status_text) > 200 else ''}"
        )
    
    def copy_sephora_format(self):
        """
        ✅ V1.7.5: Copy Sephora format: Email|Password|OrderID|Đơn|Gift1|Gift2|Kho
        """
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("❌ Lỗi", "Chọn account trước!")
            return
        
        # Get data của các accounts được chọn
        sephora_lines = []
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            # columns = ("STT", "ID", "Name", "Email", "Password", "Phone", "Create", "Last", "Status", "Kho", "Order ID", "Đơn", "Gift 1", "Gift 2", "Note", "Proxy")
            email = values[3]        # Email
            password = values[4]     # Password
            order_id = values[10]    # Order ID
            order_total = values[11] # Đơn
            gift1 = values[12]       # Gift 1
            gift2 = values[13]       # Gift 2
            kho = values[9]          # Kho
            
            # Format: Email|Password|OrderID|Đơn|Gift1|Gift2|Kho
            line = f"{email}|{password}|{order_id}|{order_total}|{gift1}|{gift2}|{kho}"
            sephora_lines.append(line)
        
        # Copy vào clipboard
        sephora_text = "\n".join(sephora_lines)
        self.clipboard_clear()
        self.clipboard_append(sephora_text)
        self.update()  # Required for clipboard to work
        
        messagebox.showinfo(
            "✅ Đã copy!", 
            f"Đã copy {len(selected)} dòng Sephora format vào clipboard!\n\n"
            f"Format: Email|Password|OrderID|Đơn|Gift1|Gift2|Kho\n\n"
            f"Preview:\n{sephora_text[:300]}{'...' if len(sephora_text) > 300 else ''}"
        )
    
    def restore_gifts(self, menu):
        """
        ✅ V1.7.8: Hoàn trả balance từ gift1_used và gift2_used về giftcard và clear order info
        """
        selected = self.tree.selection()
        if not selected:
            menu.destroy()
            messagebox.showerror("❌ Lỗi", "Chọn account trước!")
            return
        
        menu.destroy()
        
        # Confirm
        if not messagebox.askyesno("⚠️ Xác nhận", 
                                   f"Restore gift và clear order info cho {len(selected)} account(s)?"):
            return
        
        restored_count = 0
        error_count = 0
        
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            email = values[3]
            
            # Find account
            account = None
            for acc in self.accounts:
                if acc.email == email:
                    account = acc
                    break
            
            if not account:
                error_count += 1
                continue
            
            # Get gift cards and used amounts
            gift1_card = account.gift1
            gift2_card = account.gift2
            gift1_used = getattr(account, 'gift1_used', 0.0)
            gift2_used = getattr(account, 'gift2_used', 0.0)
            
            if not gift1_card and not gift2_card:
                print(f"[INFO] {email}: No gifts to restore")
                continue
            
            # Restore Gift 1
            if gift1_card and gift1_used > 0:
                gift_found = False
                for gc in self.giftcards:
                    if gc.card_number == gift1_card:
                        # Cộng lại số tiền đã dùng
                        old_balance = self.normalize_balance(gc.balance)
                        gc.balance = format_balance(old_balance + gift1_used)
                        print(f"[INFO] Restored Gift 1 {gift1_card}: ${old_balance} + ${gift1_used} = ${gc.balance}")
                        gift_found = True
                        restored_count += 1
                        break
                
                if not gift_found:
                    print(f"[WARNING] Gift 1 {gift1_card} not found in giftcard list!")
                    error_count += 1
            
            # Restore Gift 2
            if gift2_card and gift2_used > 0:
                gift_found = False
                for gc in self.giftcards:
                    if gc.card_number == gift2_card:
                        # Cộng lại số tiền đã dùng
                        old_balance = self.normalize_balance(gc.balance)
                        gc.balance = format_balance(old_balance + gift2_used)
                        print(f"[INFO] Restored Gift 2 {gift2_card}: ${old_balance} + ${gift2_used} = ${gc.balance}")
                        gift_found = True
                        restored_count += 1
                        break
                
                if not gift_found:
                    print(f"[WARNING] Gift 2 {gift2_card} not found in giftcard list!")
                    error_count += 1
            
            # Clear order info và gifts khỏi account
            account.order_id = ""
            account.order_total = ""
            account.gift1 = ""
            account.gift2 = ""
            account.gift1_used = 0.0
            account.gift2_used = 0.0
            print(f"[INFO] Cleared order info from account {email}")
        
        # Save
        self.save_giftcards()
        self.save_accounts()
        self.refresh_table()
        
        if error_count > 0:
            messagebox.showwarning("⚠️ Hoàn thành", 
                                 f"✅ Restored: {restored_count}\n❌ Errors: {error_count}")
        else:
            messagebox.showinfo("✅ OK", 
                              f"Đã restore {restored_count} gift card(s) thành công!")
    
    def manage_folders(self):
        """Quản lý folders"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Quản lý Folders")
        dialog.geometry("450x500")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(frame, text="📁 Quản lý Folders", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Info
        info = ctk.CTkLabel(frame, text="Click vào folder để chọn, sau đó click Xóa", 
                           text_color="gray", font=("Arial", 10))
        info.pack(pady=5)
        
        # Listbox frame with border
        list_container = ctk.CTkFrame(frame, fg_color="#1a1a1a", border_width=2, border_color="#3a3a3a")
        list_container.pack(fill="both", expand=True, pady=10)
        
        # Create custom listbox using CTkScrollableFrame
        scrollable = ctk.CTkScrollableFrame(list_container, fg_color="#2a2d2e")
        scrollable.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Store folder buttons
        folder_buttons = []
        selected_folder = {"name": None, "button": None}
        
        def create_folder_item(folder_name, index):
            """Create a clickable folder item"""
            btn_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
            btn_frame.pack(fill="x", pady=2)
            
            def on_click():
                # Deselect previous
                if selected_folder["button"]:
                    selected_folder["button"].configure(fg_color="transparent")
                
                # Select current
                btn.configure(fg_color="#1f6aa5")
                selected_folder["name"] = folder_name
                selected_folder["button"] = btn
            
            btn = ctk.CTkButton(
                btn_frame,
                text=f"{index}. {folder_name}",
                anchor="w",
                fg_color="transparent",
                hover_color="#3a3a3a",
                height=35,
                command=on_click
            )
            btn.pack(fill="x", padx=5)
            
            return btn
        
        def refresh_folders():
            # Clear
            for widget in scrollable.winfo_children():
                widget.destroy()
            
            folder_buttons.clear()
            selected_folder["name"] = None
            selected_folder["button"] = None
            
            # Recreate
            for i, folder in enumerate(self.folders, 1):
                btn = create_folder_item(folder, i)
                folder_buttons.append(btn)
        
        refresh_folders()
        
        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        def add_folder():
            name = ctk.CTkInputDialog(text="Tên folder mới:", title="Thêm Folder").get_input()
            if name and name.strip():
                if name not in self.folders:
                    self.folders.append(name)
                    refresh_folders()
                    self.save_config()
                    self.refresh_folder_dropdown()
                    messagebox.showinfo("✅ OK", f"Đã thêm folder: {name}")
                else:
                    messagebox.showerror("❌ Lỗi", "Folder đã tồn tại!")
        
        def delete_folder():
            if not selected_folder["name"]:
                messagebox.showerror("❌ Lỗi", "Hãy click chọn folder cần xóa!")
                return
            
            folder_name = selected_folder["name"]
            
            if folder_name in ["Default", "Mặc định"]:
                messagebox.showerror("❌ Lỗi", "Không thể xóa folder mặc định!")
                return
            
            if messagebox.askyesno("⚠️ Xác nhận", f"Xóa folder: {folder_name}?"):
                self.folders.remove(folder_name)
                
                # Move accounts to Default
                for acc in self.accounts:
                    if acc.folder == folder_name:
                        acc.folder = "Default"
                
                refresh_folders()
                self.save_config()
                self.save_accounts()
                self.refresh_folder_dropdown()
                
                # Switch to Default folder if current folder was deleted
                if self.folder_var.get() == folder_name:
                    self.folder_var.set("Default")
                    self.refresh_table()
                
                messagebox.showinfo("✅ OK", f"Đã xóa folder: {folder_name}")
        
        ctk.CTkButton(btn_frame, text="+ Thêm", width=100, height=35,
                     fg_color="#2b7a3a", command=add_folder).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="🗑️ Xóa", width=100, height=35,
                     fg_color="#8b0000", command=delete_folder).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="Đóng", width=100, height=35,
                     command=dialog.destroy).pack(side="right", padx=5)
    
    def manage_columns(self):
        """✅ V1.7.0: Quản lý ẩn/hiện cột"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Quản lý Columns")
        dialog.geometry("400x600")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(frame, text="⚙️ Quản lý Columns", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Info
        info = ctk.CTkLabel(frame, text="Chọn cột để hiển thị hoặc ẩn", 
                           text_color="gray", font=("Arial", 10))
        info.pack(pady=5)
        
        # Scrollable frame for checkboxes
        scrollable = ctk.CTkScrollableFrame(frame, fg_color="#1a1a1a")
        scrollable.pack(fill="both", expand=True, pady=10)
        
        # Create checkboxes for each column
        column_vars = {}
        columns = self.tree["columns"]
        
        for col in columns:
            var = ctk.BooleanVar(value=self.column_visibility.get(col, True))
            column_vars[col] = var
            
            ctk.CTkCheckBox(
                scrollable,
                text=col,
                variable=var,
                font=("Arial", 12),
                height=30
            ).pack(anchor="w", padx=20, pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        def apply_changes():
            # Update visibility
            for col, var in column_vars.items():
                self.column_visibility[col] = var.get()
            
            # Apply and save
            self.apply_column_visibility()
            self.save_column_settings()
            messagebox.showinfo("✅ OK", "Đã áp dụng thay đổi!")
            dialog.destroy()
        
        def select_all():
            for var in column_vars.values():
                var.set(True)
        
        def deselect_all():
            for var in column_vars.values():
                var.set(False)
        
        ctk.CTkButton(btn_frame, text="Chọn tất cả", width=100, height=35,
                     command=select_all).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="Bỏ chọn tất cả", width=120, height=35,
                     command=deselect_all).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="✅ Áp dụng", width=100, height=35,
                     fg_color="#2b7a3a", command=apply_changes).pack(side="right", padx=5)
    
    def apply_column_visibility(self):
        """✅ V1.7.0: Áp dụng visibility settings cho columns"""
        columns = self.tree["columns"]
        
        for col in columns:
            is_visible = self.column_visibility.get(col, True)
            
            if is_visible:
                # Show column with saved width
                width = self.column_widths.get(col, 100)
                self.tree.column(col, width=width)
            else:
                # Hide column by setting width to 0
                self.tree.column(col, width=0, stretch=False)
    
    def on_column_resize(self, event):
        """✅ V1.7.0: Auto-save khi resize column"""
        # Delay to ensure resize is complete
        self.after(100, self.save_current_column_widths)
    
    def save_current_column_widths(self):
        """✅ V1.7.0: Lưu độ rộng cột hiện tại"""
        try:
            columns = self.tree["columns"]
            for col in columns:
                width = self.tree.column(col, "width")
                # Only save if width > 0 (visible columns)
                if width > 0:
                    self.column_widths[col] = width
            
            # Auto-save to config
            self.save_column_settings()
        except Exception as e:
            print(f"[ERROR] Save column widths failed: {e}")
    
    def save_column_settings(self):
        """✅ V1.7.0: Lưu column settings vào config"""
        try:
            self.config['column_widths'] = self.column_widths
            self.config['column_visibility'] = self.column_visibility
            self.save_config()
        except Exception as e:
            print(f"[ERROR] Save column settings failed: {e}")
    
    def on_selection_change(self, event):
        """Update status bar when selection changes"""
        selected = self.tree.selection()
        total = len(self.accounts)
        self.status_label.configure(text=f"Tổng: {total}     Đang chọn: {len(selected)}")
    
    def refresh_folder_dropdown(self):
        """Refresh folder dropdown menu"""
        # Update dropdown values
        if hasattr(self, 'folder_menu'):
            self.folder_menu.configure(values=self.folders)
    
    def refresh_table(self):
        """
        Cập nhật table
        ✅ IMPROVED v1.2.4: Hỗ trợ search filter
        ✅ V1.8.1: Thread-safe với lock
        """
        # ✅ V1.8.1: Sử dụng lock để tránh race condition trong multi-threading
        with self.refresh_lock:
            try:
                for item in self.tree.get_children():
                    self.tree.delete(item)
            except Exception as e:
                # Bỏ qua lỗi nếu item không tồn tại
                print(f"[WARNING] Refresh table error (safe to ignore): {e}")
                return
            
            current_folder = self.folder_var.get()
            filtered = [acc for acc in self.accounts if acc.folder == current_folder]
            
            # ✅ NEW v1.2.4: Filter by search text
            if self.search_filter:
                search_lower = self.search_filter.lower()
                filtered = [acc for acc in filtered if (
                    search_lower in acc.email.lower() or
                    search_lower in acc.name.lower() or
                    search_lower in acc.status.lower() or
                    search_lower in acc.note.lower()
                )]
            
            for idx, acc in enumerate(filtered, 1):
                short_id = acc.id[:12] + "..." if len(acc.id) > 12 else acc.id
                short_proxy = acc.proxy[:20] + "..." if len(acc.proxy) > 20 else acc.proxy
                
                # ✅ V1.6.5: Lấy warehouse_name nếu có
                warehouse_name = getattr(acc, 'warehouse_name', '')
                
                # ✅ V1.6.9: Lấy order_id, gift1, gift2
                order_id = getattr(acc, 'order_id', '')
                order_total = getattr(acc, 'order_total', '')  # ✅ V1.7.4
                gift1 = getattr(acc, 'gift1', '')
                gift2 = getattr(acc, 'gift2', '')
                
                # ✅ V1.7.0: Đổi thứ tự Email trước Password
                self.tree.insert("", "end", values=(
                    idx, short_id, acc.name, acc.email, acc.password,
                    acc.phone, acc.create_time, acc.last_run, acc.status,
                    warehouse_name, order_id, order_total, gift1, gift2, acc.note, short_proxy
                ))
            
            total = len(self.accounts)
            filtered_count = len(filtered)
            
            # ✅ IMPROVED v1.2.4: Update status bar with search info
            if self.search_filter:
                self.status_label.configure(text=f"Tổng: {total}     Tìm thấy: {filtered_count}     Đang chọn: 0")
            else:
                self.status_label.configure(text=f"Tổng: {total}     Đang chọn: 0")
    
    def on_search(self, event=None):
        """
        ✅ NEW METHOD v1.2.4: Search/filter accounts real-time
        """
        search_text = self.search_entry.get().strip().lower()
        self.search_filter = search_text
        self.refresh_table()
    
    def toggle_region(self, selected):
        """
        ✅ NEW v1.2.6: Toggle region checkboxes (chỉ cho chọn 1)
        """
        if selected == 'usa':
            if self.region_usa.get():
                self.region_can.set(False)
        elif selected == 'can':
            if self.region_can.get():
                self.region_usa.set(False)
    
    def update_warehouse_dropdown(self):
        """Update danh sách kho vào dropdown"""
        if hasattr(self, 'warehouse_menu'):
            warehouse_names = ["--Chọn kho"] + [wh.name for wh in self.warehouses]
            self.warehouse_menu.configure(values=warehouse_names)
    
    def on_warehouse_selected(self, warehouse_name):
        """Xử lý khi chọn kho"""
        if warehouse_name == "--Chọn kho":
            self.warehouse_selected = None
        else:
            # Tìm warehouse theo name
            for wh in self.warehouses:
                if wh.name == warehouse_name:
                    self.warehouse_selected = wh
                    print(f"[INFO] Selected warehouse: {wh.name}")
                    print(f"[INFO] Address: {wh.address}, {wh.city}, {wh.state} {wh.zip}")
                    break
    
    # ==================== GIFTCARD FUNCTIONS - V1.7.1 ====================
    
    def normalize_balance(self, balance_str):
        """
        ✅ V1.7.1: Normalize balance string
        Chuyển dấu phẩy thành dấu chấm để parse float
        "18,26" → "18.26"
        "18.26" → "18.26"
        """
        try:
            if isinstance(balance_str, (int, float)):
                return float(balance_str)
            
            # Replace comma with dot
            balance_str = str(balance_str).replace(',', '.')
            return float(balance_str)
        except:
            return 0.0
    
    def select_giftcards_for_order(self, account, order_total):
        """
        ✅ V1.7.9: Chọn giftcard cho đơn hàng
        ✅ UPDATED: 
        - Ưu tiên 1: Tìm gift = đúng total
        - Ưu tiên 2: Tìm 2 gifts (Gift 1 nhỏ hơn, Gift 2 lớn hơn)
        - Ưu tiên 3: Tìm 1 gift > total (waste ít nhất)
        - TRỪ BALANCE NGAY khi gán
        - Lưu backup balance để restore khi lỗi
        Returns: (gift1, gift2, backup_balances) hoặc (None, None, None) nếu không đủ
        """
        try:
            order_total = float(order_total)
        except:
            print(f"[ERROR] Invalid order total: {order_total}")
            return None, None, None
        
        # Check: Account đã gán Gift 1, Gift 2 chưa?
        if account.gift1 and account.gift2:
            # Đã gán → Dùng gift đã gán
            gift1 = None
            gift2 = None
            
            for gc in self.giftcards:
                if gc.card_number == account.gift1:
                    gift1 = gc
                if gc.card_number == account.gift2:
                    gift2 = gc
            
            if gift1 and gift2:
                # Check đủ tiền không
                total_balance = self.normalize_balance(gift1.balance) + self.normalize_balance(gift2.balance)
                if total_balance >= order_total:
                    # Lưu backup
                    backup = {
                        'gift1_old': gift1.balance,
                        'gift2_old': gift2.balance
                    }
                    return gift1, gift2, backup
                else:
                    print(f"[ERROR] Assigned gifts not enough: {total_balance} < {order_total}")
                    return None, None, None
            else:
                print(f"[ERROR] Assigned gifts not found in giftcard list")
                # Fall through to auto-select
        
        elif account.gift1:
            # Chỉ có Gift 1
            gift1 = None
            for gc in self.giftcards:
                if gc.card_number == account.gift1:
                    gift1 = gc
                    break
            
            if gift1:
                if self.normalize_balance(gift1.balance) >= order_total:
                    backup = {
                        'gift1_old': gift1.balance,
                        'gift2_old': None
                    }
                    return gift1, None, backup
                else:
                    print(f"[ERROR] Assigned gift1 not enough: {gift1.balance} < {order_total}")
                    return None, None, None
        
        # Chưa gán → Tự động chọn từ pool
        print(f"[INFO] Auto-selecting giftcards for order ${order_total}")
        
        # ✅ V1.9.1: CRITICAL FIX - Filter gifts có balance > 0
        # Loại bỏ gifts đã dùng hết (balance = 0 hoặc rất nhỏ)
        available_giftcards = [
            gc for gc in self.giftcards 
            if self.normalize_balance(gc.balance) >= 0.01  # Tối thiểu $0.01
        ]
        
        if len(available_giftcards) == 0:
            print(f"[ERROR] No available giftcards (all have $0 balance)")
            return None, None, None
        
        print(f"[INFO] Available giftcards: {len(available_giftcards)}/{len(self.giftcards)}")
        for gc in available_giftcards:
            print(f"[INFO]   - {gc.card_number}: ${gc.balance}")
        
        # Sắp xếp giftcard theo balance tăng dần
        sorted_giftcards = sorted(available_giftcards, key=lambda x: self.normalize_balance(x.balance))
        
        if len(sorted_giftcards) == 0:
            print(f"[ERROR] No giftcards available")
            return None, None, None
        
        # ============================================================
        # ✅ V1.9.1: NEW LOGIC - 4 ƯU TIÊN
        # ============================================================
        
        # ✅ ƯU TIÊN 1: Gift = Subtotal → Dùng 1 gift → Xả về $0
        print(f"[INFO] Priority 1: Checking for exact match gift...")
        for gc in sorted_giftcards:
            balance = self.normalize_balance(gc.balance)
            
            # ✅ V1.9.1: Dùng epsilon comparison (tránh lỗi float precision)
            # Chênh lệch < $0.01 = Coi như bằng nhau
            if abs(balance - order_total) < 0.01:
                print(f"[SUCCESS] ⭐ Perfect match! Gift {gc.card_number} (${balance}) ≈ Subtotal (${order_total})")
                
                # Backup
                backup = {
                    'gift1_old': gc.balance,
                    'gift2_old': None
                }
                
                # TRỪ BALANCE
                gc.balance = "0"
                print(f"[INFO] Gift balance: ${backup['gift1_old']} → $0")
                
                return gc, None, backup
        
        print(f"[INFO] No exact match found")
        
        # ✅ ƯU TIÊN 2: Smallest + Biggest >= Subtotal → Dùng 2 gifts
        if len(sorted_giftcards) >= 2:
            print(f"[INFO] Priority 2: Checking smallest + biggest...")
            
            smallest = sorted_giftcards[0]
            biggest = sorted_giftcards[-1]
            
            balance_smallest = self.normalize_balance(smallest.balance)
            balance_biggest = self.normalize_balance(biggest.balance)
            total_balance = balance_smallest + balance_biggest
            
            print(f"[INFO] Smallest: {smallest.card_number} (${balance_smallest})")
            print(f"[INFO] Biggest: {biggest.card_number} (${balance_biggest})")
            print(f"[INFO] Total: ${total_balance} vs Subtotal: ${order_total}")
            
            if total_balance >= order_total:
                print(f"[SUCCESS] ✅ Smallest + Biggest >= Subtotal")
                
                # Backup
                backup = {
                    'gift1_old': smallest.balance,
                    'gift2_old': biggest.balance
                }
                
                # TRỪ BALANCE
                # Gift 1 (smallest) cắn hết
                smallest.balance = "0"
                
                # Gift 2 (biggest) trừ phần còn lại
                remaining = order_total - balance_smallest
                new_balance_biggest = balance_biggest - remaining
                biggest.balance = format_balance(new_balance_biggest)
                
                print(f"[INFO] Gift 1 balance: ${backup['gift1_old']} → $0")
                print(f"[INFO] Gift 2 balance: ${backup['gift2_old']} → ${biggest.balance}")
                
                return smallest, biggest, backup
            else:
                print(f"[INFO] Smallest + Biggest < Subtotal (${total_balance} < ${order_total})")
        
        # ✅ ƯU TIÊN 3: Loop gifts (tăng dần) + Biggest >= Subtotal
        if len(sorted_giftcards) >= 2:
            print(f"[INFO] Priority 3: Looping to find suitable gift + biggest...")
            
            biggest = sorted_giftcards[-1]
            balance_biggest = self.normalize_balance(biggest.balance)
            
            # Loop từ gift thứ 2 (index 1) đến trước biggest
            for i in range(1, len(sorted_giftcards) - 1):
                gc = sorted_giftcards[i]
                balance_gc = self.normalize_balance(gc.balance)
                total_balance = balance_gc + balance_biggest
                
                print(f"[INFO] Trying: {gc.card_number} (${balance_gc}) + Biggest (${balance_biggest}) = ${total_balance}")
                
                if total_balance >= order_total:
                    print(f"[SUCCESS] ✅ Found suitable pair!")
                    
                    # Backup
                    backup = {
                        'gift1_old': gc.balance,
                        'gift2_old': biggest.balance
                    }
                    
                    # TRỪ BALANCE
                    # Gift 1 cắn hết
                    gc.balance = "0"
                    
                    # Gift 2 (biggest) trừ phần còn lại
                    remaining = order_total - balance_gc
                    new_balance_biggest = balance_biggest - remaining
                    biggest.balance = format_balance(new_balance_biggest)
                    
                    print(f"[INFO] Gift 1 balance: ${backup['gift1_old']} → $0")
                    print(f"[INFO] Gift 2 balance: ${backup['gift2_old']} → ${biggest.balance}")
                    
                    return gc, biggest, backup
            
            print(f"[INFO] No suitable pair found in loop")
        
        # ✅ ƯU TIÊN 4: Không đủ → Return None
        print(f"[ERROR] Not enough giftcard balance for order ${order_total}")
        return None, None, None
    
    def remove_pre_applied_giftcards(self, driver):
        """
        ✅ V1.7.2: Remove các gift card đã được gắn sẵn trong checkout
        ✅ Xử lý popup confirm "Remove Gift Card"
        ✅ Loop cho đến khi xóa HẾT tất cả gift cards
        Returns: Số gift card đã remove
        """
        try:
            removed_count = 0
            
            # ✅ Loop cho đến khi không còn button "Remove" nào
            while True:
                # ✅ Đảm bảo không còn popup nào đang mở
                try:
                    # Check nếu có popup đang mở thì đóng (bất kỳ modal nào)
                    modal = driver.find_element(By.CSS_SELECTOR, 'div[role="dialog"][id*="Dialog"]')
                    if modal.is_displayed():
                        print("[INFO] Closing existing popup...")
                        try:
                            # Try clicking Cancel
                            cancel_btn = modal.find_element(By.XPATH, ".//button[text()='Cancel']")
                            cancel_btn.click()
                            time.sleep(1)
                        except:
                            # Try clicking close button
                            try:
                                close_btn = modal.find_element(By.CSS_SELECTOR, 'button[data-at="modal_close"]')
                                close_btn.click()
                                time.sleep(1)
                            except:
                                pass
                except:
                    pass
                
                # Tìm lại buttons mỗi lần (DOM thay đổi sau mỗi lần remove)
                remove_buttons = driver.find_elements(By.XPATH, "//button[text()='Remove']")
                
                # Nếu không còn button nào, thoát
                if len(remove_buttons) == 0:
                    if removed_count == 0:
                        print("[INFO] No pre-applied gift cards found")
                    break
                
                # Log lần đầu
                if removed_count == 0:
                    print(f"[INFO] Found {len(remove_buttons)} pre-applied gift card(s)")
                
                try:
                    # Click button đầu tiên
                    btn = remove_buttons[0]
                    print(f"[INFO] Removing gift card {removed_count + 1}...")
                    
                    # Scroll to button
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.5)
                    
                    btn.click()
                    time.sleep(1.5)
                    
                    # ✅ Wait for popup and click Remove button in popup
                    try:
                        # ✅ Wait for ANY popup to appear (modal2Dialog, modal4Dialog, etc.)
                        popup = WebDriverWait(driver, 5).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"][id*="Dialog"]'))
                        )
                        
                        # Log popup ID
                        popup_id = popup.get_attribute('id')
                        print(f"[DEBUG] Popup appeared: {popup_id}")
                        
                        # Wait thêm cho popup load hoàn toàn
                        time.sleep(1)
                        
                        # ✅ Tìm button Remove trong popup (button màu đen, thường là button đầu tiên)
                        # Try 1: Tìm trong modal footer
                        try:
                            remove_confirm_btn = popup.find_element(By.CSS_SELECTOR, 'button.css-1tjizbm')
                        except:
                            # Try 2: Tìm button text "Remove" trong popup
                            remove_confirm_btn = popup.find_element(By.XPATH, ".//button[text()='Remove']")
                        
                        # Scroll to button
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", remove_confirm_btn)
                        time.sleep(0.3)
                        
                        # Click
                        remove_confirm_btn.click()
                        print(f"[SUCCESS] Removed gift card {removed_count + 1}")
                        removed_count += 1
                        
                        # ✅ Wait for popup to close completely
                        time.sleep(2)
                        
                        # Đảm bảo popup đã đóng (check popup_id cụ thể)
                        try:
                            WebDriverWait(driver, 3).until(
                                EC.invisibility_of_element_located((By.CSS_SELECTOR, f'div#{popup_id}[role="dialog"]'))
                            )
                            print("[DEBUG] Popup closed successfully")
                        except:
                            print("[WARNING] Popup may still be visible")
                            pass
                        
                        # ✅ CRITICAL: Wait for DOM to update after removing gift card
                        print("[DEBUG] Waiting for DOM to update...")
                        time.sleep(2)
                        
                        # Verify số lượng buttons đã giảm
                        try:
                            new_buttons = driver.find_elements(By.XPATH, "//button[text()='Remove']")
                            print(f"[DEBUG] Buttons remaining: {len(new_buttons)}")
                        except:
                            pass
                        
                    except Exception as popup_error:
                        print(f"[ERROR] Failed to confirm remove in popup: {popup_error}")
                        
                        # Try to close popup
                        try:
                            close_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-at="modal_close"]')
                            close_btn.click()
                            time.sleep(1)
                        except:
                            pass
                        
                        # Break để tránh loop vô hạn
                        break
                    
                except Exception as e:
                    print(f"[ERROR] Failed to remove gift card: {e}")
                    # Nếu có lỗi, break để tránh loop vô hạn
                    break
            
            if removed_count > 0:
                print(f"[SUCCESS] Removed {removed_count} pre-applied gift card(s)")
            
            time.sleep(1)
            return removed_count
            
        except Exception as e:
            print(f"[ERROR] Failed to check/remove pre-applied gift cards: {e}")
            return 0
    
    def apply_giftcards_to_checkout(self, driver, gift1, gift2):
        """
        ✅ V1.7.2: Apply giftcard vào checkout form
        ✅ V1.7.2: Remove pre-applied gift cards trước
        ✅ Xử lý error modal (balance = 0) và retry với gift khác
        Returns: True nếu thành công, False nếu thất bại
        """
        try:
            # ✅ V1.7.2: Step 0: Remove pre-applied gift cards
            print("[INFO] Checking for pre-applied gift cards...")
            removed_count = self.remove_pre_applied_giftcards(driver)
            if removed_count > 0:
                print(f"[INFO] Cleared {removed_count} old gift card(s)")
                time.sleep(1)
            
            # Step 1: Click "Use a Gift Card" button
            print("[INFO] Clicking 'Use a Gift Card' button...")
            
            try:
                # ✅ Đảm bảo không có popup nào đang mở
                try:
                    modal = driver.find_element(By.CSS_SELECTOR, 'div[role="dialog"][id*="Dialog"]')
                    if modal.is_displayed():
                        modal_id = modal.get_attribute('id')
                        print(f"[INFO] Closing lingering popup: {modal_id}")
                        close_btn = modal.find_element(By.CSS_SELECTOR, 'button[data-at="modal_close"]')
                        close_btn.click()
                        time.sleep(1)
                except:
                    pass
                
                # Try multiple selectors
                use_gift_button = None
                
                # Try 1: CSS class
                try:
                    use_gift_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.css-1kby9rz'))
                    )
                except:
                    pass
                
                # Try 2: CSS class alternative
                if not use_gift_button:
                    try:
                        use_gift_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.css-s516nn'))
                        )
                    except:
                        pass
                
                # Try 3: Text content
                if not use_gift_button:
                    try:
                        use_gift_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Use a Gift Card') or contains(text(), 'Gift Card')]"))
                        )
                    except:
                        pass
                
                # Try 4: Any button containing "gift"
                if not use_gift_button:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if "gift" in btn.text.lower() and btn.is_displayed():
                            use_gift_button = btn
                            break
                
                if use_gift_button:
                    # Scroll to button
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", use_gift_button)
                    time.sleep(0.5)
                    
                    # Try normal click first
                    try:
                        use_gift_button.click()
                    except:
                        # If blocked, use JS click
                        print("[INFO] Normal click blocked, using JS click...")
                        driver.execute_script("arguments[0].click();", use_gift_button)
                    
                    time.sleep(2)
                    print("[INFO] Gift card form opened")
                else:
                    raise Exception("Could not find 'Use a Gift Card' button with any selector")
                    
            except Exception as e:
                print(f"[ERROR] Failed to click 'Use a Gift Card' button: {e}")
                return False
            
            # Prepare gifts to try
            gifts_to_try = []
            if gift1:
                gifts_to_try.append(gift1)
            if gift2:
                gifts_to_try.append(gift2)
            
            # Try each gift
            for idx, gift in enumerate(gifts_to_try, 1):
                print(f"\n[INFO] Applying Gift {idx}: {gift.card_number}")
                
                try:
                    # Step 2: Wait for form inputs
                    number_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'input#giftCardNumber'))
                    )
                    pin_field = driver.find_element(By.CSS_SELECTOR, 'input#giftCardPin')
                    
                    # ✅ CLEAR OLD VALUE trước khi điền
                    print("[INFO] Clearing old values...")
                    number_field.clear()
                    time.sleep(0.3)
                    pin_field.clear()
                    time.sleep(0.3)
                    
                    # Step 3: Fill giftcard number
                    print(f"[INFO] Filling giftcard number: {gift.card_number}")
                    number_field.send_keys(gift.card_number)
                    time.sleep(0.5)
                    
                    # Step 4: Fill PIN
                    print(f"[INFO] Filling PIN: {gift.pin}")
                    pin_field.send_keys(gift.pin)
                    time.sleep(0.5)
                    
                    # Step 5: Click Apply button
                    print("[INFO] Clicking Apply button...")
                    apply_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-at="gc_apply_btn"]'))
                    )
                    apply_button.click()
                    time.sleep(3)  # Wait for processing
                    
                    # Step 6: Check for error modal (balance = $0)
                    try:
                        error_modal = driver.find_element(By.CSS_SELECTOR, 'div#modal2Dialog[role="dialog"]')
                        
                        # Check if it's the "$0.00 value" error
                        modal_text = error_modal.text
                        if "$0.00" in modal_text or "0.00 value" in modal_text:
                            print(f"[WARNING] Gift {gift.card_number} has $0 balance - trying next gift...")
                            
                            # Click OK to close modal
                            ok_button = driver.find_element(By.CSS_SELECTOR, 'button.css-1tjizbm')
                            ok_button.click()
                            time.sleep(1)
                            
                            # Continue to next gift
                            continue
                        
                    except:
                        # No error modal = Success!
                        print(f"[SUCCESS] Gift {idx} applied successfully: {gift.card_number}")
                        
                        # If this was gift1 and we have gift2, continue to apply gift2
                        if idx < len(gifts_to_try):
                            print("[INFO] Continuing to apply next gift...")
                            time.sleep(2)
                            
                            # ✅ V1.7.2: Form đã đóng sau Gift 1, cần mở lại cho Gift 2
                            print("[INFO] Reopening gift card form for next gift...")
                            try:
                                # Click "Use a Gift Card" again
                                use_gift_button = None
                                
                                # Try multiple selectors
                                try:
                                    use_gift_button = WebDriverWait(driver, 5).until(
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.css-1kby9rz'))
                                    )
                                except:
                                    pass
                                
                                if not use_gift_button:
                                    try:
                                        use_gift_button = WebDriverWait(driver, 5).until(
                                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.css-s516nn'))
                                        )
                                    except:
                                        pass
                                
                                if not use_gift_button:
                                    try:
                                        use_gift_button = WebDriverWait(driver, 5).until(
                                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Use a Gift Card')]"))
                                        )
                                    except:
                                        pass
                                
                                if use_gift_button:
                                    # Scroll to button
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", use_gift_button)
                                    time.sleep(0.5)
                                    
                                    # Try normal click first
                                    try:
                                        use_gift_button.click()
                                    except:
                                        # If blocked, use JS click
                                        print("[INFO] Using JS click for gift card button...")
                                        driver.execute_script("arguments[0].click();", use_gift_button)
                                    
                                    time.sleep(2)
                                    print("[INFO] Gift card form reopened for Gift 2")
                                else:
                                    print("[WARNING] Could not find 'Use a Gift Card' button for Gift 2")
                                    
                            except Exception as reopen_error:
                                print(f"[ERROR] Failed to reopen gift card form: {reopen_error}")
                            
                            continue
                        else:
                            # All gifts applied
                            print("[SUCCESS] All giftcards applied!")
                            return True
                
                except Exception as gift_error:
                    print(f"[ERROR] Failed to apply Gift {idx}: {gift_error}")
                    
                    # Try to close any open modal
                    try:
                        close_button = driver.find_element(By.CSS_SELECTOR, 'button[data-at="modal_close"]')
                        close_button.click()
                        time.sleep(1)
                    except:
                        pass
                    
                    continue
            
            # If we get here, all gifts failed
            print("[ERROR] All giftcards failed to apply")
            return False
            
        except Exception as e:
            print(f"[ERROR] apply_giftcards_to_checkout failed: {e}")
            return False
    
    def verify_giftcards_applied(self, driver, expected_count):
        """
        ✅ V1.8.9: Verify số lượng giftcards đã được apply vào checkout
        Kiểm tra element: div[data-at="applied_gift_cards_section"]
        Returns: (success: bool, actual_count: int)
        """
        try:
            print(f"[INFO] Verifying giftcards applied (expected: {expected_count})...")
            
            # Wait a bit for page to update
            time.sleep(2)
            
            # Tìm section chứa applied giftcards
            try:
                applied_section = driver.find_element(By.CSS_SELECTOR, 'div[data-at="applied_gift_cards_section"]')
                
                # Đếm số lượng giftcard items
                applied_items = applied_section.find_elements(By.CSS_SELECTOR, 'div[data-at="applied_gift_card_item"]')
                actual_count = len(applied_items)
                
                print(f"[INFO] Found {actual_count} applied giftcard(s)")
                
                # Log chi tiết từng card
                for idx, item in enumerate(applied_items, 1):
                    try:
                        card_number = item.find_element(By.CSS_SELECTOR, 'span.css-ou7t42').text
                        card_amount = item.find_element(By.CSS_SELECTOR, 'span.css-y2q6bq').text
                        print(f"  - Gift {idx}: {card_number} - {card_amount}")
                    except:
                        pass
                
                # Verify số lượng
                if actual_count == expected_count:
                    print(f"[SUCCESS] Giftcard verification PASSED: {actual_count}/{expected_count}")
                    return True, actual_count
                else:
                    print(f"[ERROR] Giftcard verification FAILED: {actual_count}/{expected_count}")
                    return False, actual_count
                
            except Exception as find_error:
                print(f"[ERROR] Could not find applied_gift_cards_section: {find_error}")
                # Có thể section không tồn tại nếu không có gift nào applied
                return False, 0
            
        except Exception as e:
            print(f"[ERROR] verify_giftcards_applied failed: {e}")
            return False, 0
    
    def assign_giftcards_to_account(self, account, gift1, gift2, backup_balances=None):
        """
        ✅ V1.7.8: Gán giftcard vào account và lưu số tiền đã dùng
        """
        try:
            # Lưu gift vào account
            account.gift1 = gift1.card_number
            if gift2:
                account.gift2 = gift2.card_number
            else:
                account.gift2 = ""
            
            # ✅ V1.7.8: Tính và lưu số tiền đã dùng từ mỗi gift
            if backup_balances:
                # Gift 1
                if backup_balances.get('gift1_old') is not None:
                    old_balance1 = self.normalize_balance(backup_balances['gift1_old'])
                    new_balance1 = self.normalize_balance(gift1.balance)
                    account.gift1_used = old_balance1 - new_balance1
                    print(f"[INFO] Gift 1 used: ${account.gift1_used}")
                
                # Gift 2
                if gift2 and backup_balances.get('gift2_old') is not None:
                    old_balance2 = self.normalize_balance(backup_balances['gift2_old'])
                    new_balance2 = self.normalize_balance(gift2.balance)
                    account.gift2_used = old_balance2 - new_balance2
                    print(f"[INFO] Gift 2 used: ${account.gift2_used}")
            
            print(f"[INFO] Assigned to account:")
            print(f"[INFO]   Gift 1: {account.gift1}")
            if gift2:
                print(f"[INFO]   Gift 2: {account.gift2}")
            
            # Lưu giftcards và accounts
            self.save_giftcards()
            self.save_accounts()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to assign giftcards to account: {e}")
            return False
    
    def restore_giftcard_balances(self, account, gift1, gift2, backup_balances):
        """
        ✅ V1.7.8: HOÀN LẠI balance khi có lỗi checkout và clear used amounts
        """
        try:
            print(f"[INFO] Restoring giftcard balances due to checkout error...")
            
            # Restore Gift 1
            if gift1 and backup_balances.get('gift1_old'):
                gift1.balance = backup_balances['gift1_old']
                print(f"[INFO] Restored Gift 1 balance: ${gift1.balance}")
            
            # Restore Gift 2
            if gift2 and backup_balances.get('gift2_old'):
                gift2.balance = backup_balances['gift2_old']
                print(f"[INFO] Restored Gift 2 balance: ${gift2.balance}")
            
            # Xóa gift khỏi account
            account.gift1 = ""
            account.gift2 = ""
            account.gift1_used = 0.0  # ✅ V1.7.8
            account.gift2_used = 0.0  # ✅ V1.7.8
            
            self.save_giftcards()
            self.save_accounts()
            
            print(f"[INFO] Gifts cleared from account and balances restored")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to restore giftcard balances: {e}")
            return False
    
    def check_basket_items_count(self, driver):
        """
        ✅ V1.10.6: Check số lượng items trong basket
        Parse từ element <h2 data-at="bsk__items_label">Get It Shipped (6)</h2>
        Returns: số items hoặc None nếu không tìm thấy
        """
        try:
            # Tìm element
            basket_label = driver.find_element(By.CSS_SELECTOR, 'h2[data-at="bsk__items_label"]')
            label_text = basket_label.text.strip()
            
            print(f"[INFO] Basket label text: {label_text}")
            
            # Parse số từ text "Get It Shipped (6)"
            import re
            match = re.search(r'\((\d+)\)', label_text)
            
            if match:
                items_count = int(match.group(1))
                print(f"[INFO] Basket contains {items_count} items")
                return items_count
            else:
                print(f"[WARNING] Could not parse items count from: {label_text}")
                return None
                
        except Exception as e:
            print(f"[ERROR] Failed to check basket items count: {e}")
            return None
    
    def check_gift_card_redeemed(self, driver):
        """
        ✅ V1.7.2: Kiểm tra Gift Card Redeemed đã đủ chưa
        Returns: (is_sufficient, redeemed_amount, subtotal)
        """
        try:
            # Lấy Subtotal
            subtotal_elem = driver.find_element(By.CSS_SELECTOR, 'span[data-at="bsk_total_merch"]')
            subtotal_text = subtotal_elem.text.strip().replace('$', '').replace(',', '')
            subtotal = float(subtotal_text)
            
            # Lấy Gift Card Redeemed
            try:
                redeemed_elem = driver.find_element(By.CSS_SELECTOR, 'span[data-at="total_gc_amt"]')
                redeemed_text = redeemed_elem.text.strip().replace('$', '').replace(',', '').replace('-', '')
                redeemed = float(redeemed_text)
            except:
                # Không có Gift Card Redeemed
                print("[INFO] No Gift Card Redeemed found")
                return False, 0, subtotal
            
            print(f"[INFO] Subtotal: ${subtotal}, Gift Card Redeemed: ${redeemed}")
            
            # Check if sufficient
            is_sufficient = (redeemed >= subtotal)
            
            return is_sufficient, redeemed, subtotal
            
        except Exception as e:
            print(f"[ERROR] Failed to check Gift Card Redeemed: {e}")
            return False, 0, 0
    
    def click_place_order(self, driver):
        """
        ✅ V1.7.2: Click Place Order button (chọn button visible)
        """
        try:
            # Tìm tất cả Place Order buttons
            buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-at="place_order_btn"]')
            
            if not buttons:
                print("[ERROR] No Place Order button found")
                return False
            
            # Click button visible
            for btn in buttons:
                if btn.is_displayed():
                    print(f"[INFO] Clicking Place Order button...")
                    btn.click()
                    time.sleep(3)
                    return True
            
            print("[ERROR] No visible Place Order button found")
            return False
            
        except Exception as e:
            print(f"[ERROR] Failed to click Place Order: {e}")
            return False
    
    def check_verification_popup(self, driver):
        """
        ✅ V1.7.2: Kiểm tra popup Verification Required
        Returns: True nếu có popup Verification
        """
        try:
            # ✅ Check ANY popup/dialog (modal2Dialog, modal4Dialog, etc.)
            popup = driver.find_element(By.CSS_SELECTOR, 'div[role="dialog"][id*="Dialog"]')
            
            # Check if visible
            if not popup.is_displayed():
                return False
            
            # Check text "Verification Required"
            popup_text = popup.text
            if "Verification Required" in popup_text or "verification" in popup_text.lower():
                popup_id = popup.get_attribute('id')
                print(f"[WARNING] Verification Required popup detected! (ID: {popup_id})")
                return True
            
            return False
            
        except:
            # Không có popup
            return False
    
    def extract_order_info(self, driver):
        """
        ✅ V1.7.6: Extract Order ID và Total $ từ order confirmation page
        Returns: (order_id, order_total) hoặc (None, None) nếu không tìm thấy
        """
        try:
            order_id = None
            order_total = None
            
            # Extract Order ID
            try:
                order_num_elem = driver.find_element(
                    By.CSS_SELECTOR, 
                    'p[data-at="pickup_order_number_title"] a[data-at="confirmation_order_number"]'
                )
                order_id = order_num_elem.text.strip()
                print(f"[SUCCESS] Order ID extracted: {order_id}")
            except Exception as e:
                print(f"[WARNING] Could not extract Order ID: {e}")
            
            # Extract Total $
            try:
                total_elem = driver.find_element(
                    By.CSS_SELECTOR, 
                    'div.css-w3rm48 span[data-at="confirmation_order_total"]'
                )
                order_total_raw = total_elem.text.strip()
                # ✅ V1.7.5: Clean format (bỏ $, đổi . thành ,)
                order_total = clean_order_total(order_total_raw)
                print(f"[SUCCESS] Order Total extracted: {order_total_raw} → {order_total}")
            except Exception as e:
                print(f"[WARNING] Could not extract Order Total: {e}")
            
            return order_id, order_total
            
        except Exception as e:
            print(f"[ERROR] Failed to extract order info: {e}")
            return None, None
    
    def get_order_total_from_page(self, driver):
        """
        ✅ V1.9.1: Lấy tổng tiền đơn hàng từ span[data-at="bsk_total_cc"]
        ✅ CRITICAL FIX: Giữ nguyên phần lẻ (float), KHÔNG convert sang int
        ✅ Element: <span data-at="bsk_total_cc" aria-label="Final total: $21.60">$21.60</span>
        Returns: order_total (string float) hoặc None nếu không lấy được
        """
        try:
            # ✅ Selector chính xác cho total cuối cùng
            total_selector = 'span[data-at="bsk_total_cc"]'
            
            print(f"[INFO] Looking for order total with selector: {total_selector}")
            
            # Find element
            element = driver.find_element(By.CSS_SELECTOR, total_selector)
            print(f"[INFO] Element found: {element.tag_name}")
            
            # Try to get text first
            total_text = element.text.strip()
            print(f"[DEBUG] Element.text = '{total_text}'")
            
            # ✅ Nếu text trống hoặc không có $, lấy từ aria-label
            if not total_text or '$' not in total_text:
                aria_label = element.get_attribute('aria-label')
                print(f"[DEBUG] aria-label = '{aria_label}'")
                
                if aria_label:
                    # Parse: "Final total: $21.60" -> "$21.60"
                    if ':' in aria_label and '$' in aria_label:
                        total_text = aria_label.split(':')[1].strip()
                        print(f"[INFO] Extracted from aria-label: '{total_text}'")
            
            if not total_text:
                print(f"[ERROR] Could not extract total from element")
                return None
            
            # Remove $ and convert to number
            # Format: "$21.60" -> "21.60"
            total_text = total_text.replace('$', '').replace(',', '').strip()
            print(f"[DEBUG] After removing $: '{total_text}'")
            
            # ✅ V1.9.1: CRITICAL FIX - GIỮ NGUYÊN FLOAT, KHÔNG convert sang int
            # Convert to float để validate, nhưng GIỮ NGUYÊN phần lẻ
            try:
                total_float = float(total_text)
                print(f"[DEBUG] Parsed as float: {total_float}")
                
                # Nếu là số nguyên (21.0), format thành "21"
                # Nếu có phần lẻ (21.6), giữ nguyên "21.6"
                if total_float == int(total_float):
                    total_text = str(int(total_float))
                    print(f"[INFO] Integer detected: ${total_text}")
                else:
                    total_text = str(total_float)
                    print(f"[INFO] Decimal detected: ${total_text}")
            except ValueError as ve:
                print(f"[ERROR] Failed to parse as float: {ve}")
                return None
            
            print(f"[SUCCESS] Order total extracted: ${total_text}")
            return total_text
            
        except Exception as e:
            print(f"[ERROR] Failed to get order total: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ==================== END GIFTCARD FUNCTIONS ====================
    
    def run_automation(self):
        """Chạy automation"""
        function = self.function_var.get()
        if function == "--Chọn chức năng":
            messagebox.showerror("❌ Lỗi", "Hãy chọn chức năng!")
            return
        
        if not self.accounts:
            messagebox.showerror("❌ Lỗi", "Chưa có account nào!")
            return
        
        # ✅ NEW v1.2.6: Sephora Order workflow
        if function == "Sephora Order":
            self.run_sephora_order()
        else:
            messagebox.showinfo("ℹ️ Demo", 
                              f"Chức năng: {function}\n\n"
                              f"Workflow automation đang được phát triển!\n"
                              f"Hiện tại tool đã có đầy đủ UI và quản lý accounts.")
    
    def run_sephora_order(self):
        """
        ✅ NEW v1.2.6: Sephora Order workflow với TopCashback
        ✅ V1.3.4: Start/Stop button
        """
        # Check if running -> Stop
        if self.is_running:
            self.stop_flag = True
            self.run_button.configure(text="⏸ Stopping...", state="disabled")
            return
        
        # Kiểm tra region
        if not self.region_usa.get() and not self.region_can.get():
            messagebox.showerror("❌ Lỗi", "Hãy chọn USA hoặc CAN!")
            return
        
        region = "USA" if self.region_usa.get() else "CAN"
        
        # ✅ V1.5.8: CHECK Item 1 bắt buộc phải nhập
        item1 = self.item1_entry.get().strip()
        if not item1:
            messagebox.showerror("❌ Lỗi", "Item 1 là bắt buộc!\nVui lòng nhập link sản phẩm vào Item 1.")
            return
        
        # ✅ V1.10.6: CHECK Total Item bắt buộc phải nhập
        total_item_str = self.total_item_entry.get().strip()
        if not total_item_str:
            messagebox.showerror("❌ Lỗi", "Total Item là bắt buộc!\nVui lòng nhập số lượng items (1-20) vào ô Total Item.")
            return
        
        # Validate Total Item là số hợp lệ
        try:
            total_item = int(total_item_str)
            if total_item < 1 or total_item > 20:
                messagebox.showerror("❌ Lỗi", "Total Item phải từ 1 đến 20!")
                return
        except ValueError:
            messagebox.showerror("❌ Lỗi", "Total Item phải là số nguyên!")
            return
        
        # Get selected accounts
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("❌ Lỗi", "Hãy chọn account!")
            return
        
        # ✅ V1.3.4: Lấy email list thay vì item_id (tránh lỗi khi refresh_table)
        email_list = []
        for item_id in selected:
            values = self.tree.item(item_id)['values']
            email = values[3]  # Email ở cột 4
            email_list.append(email)
        
        print(f"[INFO] Selected emails: {email_list}")
        
        # ✅ V1.6.5: CHECK nếu account chưa chọn kho thì không cho chạy
        accounts_without_warehouse = []
        for email in email_list:
            for acc in self.accounts:
                if acc.email == email:
                    # Check warehouse từ account hoặc dropdown
                    has_warehouse = False
                    
                    # Check account warehouse
                    if hasattr(acc, 'warehouse_name') and acc.warehouse_name:
                        # Verify warehouse tồn tại
                        for wh in self.warehouses:
                            if wh.name == acc.warehouse_name:
                                has_warehouse = True
                                break
                    
                    # Fallback check dropdown
                    if not has_warehouse and hasattr(self, 'warehouse_selected') and self.warehouse_selected:
                        has_warehouse = True
                    
                    if not has_warehouse:
                        accounts_without_warehouse.append(email)
                    break
        
        if accounts_without_warehouse:
            messagebox.showerror(
                "❌ Lỗi - Chưa chọn kho!", 
                f"Các account sau chưa được gán kho:\n\n" +
                "\n".join(f"• {email}" for email in accounts_without_warehouse[:10]) +
                (f"\n... và {len(accounts_without_warehouse) - 10} account khác" if len(accounts_without_warehouse) > 10 else "") +
                "\n\n🏪 Hãy right-click vào account → Chọn Kho\nhoặc chọn kho từ dropdown bên trên!"
            )
            return
        
        # Set running & change button
        self.is_running = True
        self.stop_flag = False
        self.run_button.configure(text="⏹ Stop", fg_color="#d32f2f")
        
        # Run in thread với email list
        thread = threading.Thread(target=self._sephora_order_thread, args=(email_list, region))
        thread.daemon = True
        thread.start()
    
    def _sephora_order_thread(self, email_list, region):
        """
        ✅ V1.8.0: Thread xử lý Sephora Order với multi-threading
        ✅ Support: Số luồng từ UI, Delay giữa các lần mở profile
        """
        print(f"[INFO] Starting automation for {len(email_list)} accounts...")
        
        # ✅ V1.8.0: Lấy số luồng và delay từ UI
        try:
            max_workers = int(self.threads_entry.get())
            if max_workers < 1:
                max_workers = 1
        except:
            max_workers = 1
            print("[WARNING] Invalid threads value, using 1 thread")
        
        try:
            delay_between = float(self.delay_entry.get())
            if delay_between < 0:
                delay_between = 0
        except:
            delay_between = 0
            print("[WARNING] Invalid delay value, using 0 delay")
        
        print(f"[INFO] Using {max_workers} thread(s) with {delay_between}s delay between starts")
        
        # ✅ V1.8.0: Nested function để xử lý 1 account
        def process_single_account(idx, email):
            """Process một account - nested function"""
            print(f"\n[INFO] ========== Processing account {idx}/{len(email_list)} ==========")
            
            # ✅ V1.3.4: Check stop flag
            if self.stop_flag:
                print("[INFO] Stop flag detected, stopping...")
                return None
            
            print(f"[INFO] Account email: {email}")
            
            # Tìm account
            account = None
            for acc in self.accounts:
                if acc.email == email:
                    account = acc
                    break
            
            if not account:
                return None
            
            try:
                # Update status
                account.status = "Starting..."
                self.refresh_table()
                
                # ✅ V1.3.4: Check profile (including PENDING_/LOCAL_)
                needs_new_profile = (
                    not account.id or
                    (isinstance(account.id, str) and (
                        not account.id.strip() or
                        account.id.startswith("PENDING_") or
                        account.id.startswith("LOCAL_")
                    ))
                )
                
                if needs_new_profile:
                    # Tạo profile mới
                    account.status = "Creating Profile..."
                    self.refresh_table()

                    # ✅ V1.10.9: Thêm timestamp vào profile name để tránh tái sử dụng profile cũ
                    profile_id, profile_path = self.gpm_api.create_profile(
                        f"{email.split('@')[0]}_{int(time.time())}",
                        0,
                        account.proxy,
                        self.config
                    )
                    
                    if profile_id:
                        account.id = profile_id
                        
                        # ✅ Save ngay
                        self.save_accounts()
                        
                        account.status = "GPM Profile Created"
                        self.refresh_table()
                        
                        # ⏰ V1.3.4: Chờ 3s để GPM khởi tạo
                        time.sleep(3)
                    else:
                        account.status = "Create Failed"
                        self.save_accounts()
                        self.refresh_table()
                        return None
                else:
                    # Profile đã có, update proxy nếu có
                    if account.proxy:
                        self.gpm_api.update_profile(account.id, account.proxy, self.config)
                
                # Mở profile with scale config
                account.status = "Opening Profile..."
                self.refresh_table()
                
                # ✅ V1.10.0: Sắp xếp 4 CỘT - CHỈ TRÊN 1 MÀN CHÍNH
                win_pos = None
                try:
                    # Bước 1: Lấy kích thước 1 MÀN CHÍNH (không phải tổng 2 màn)
                    # Giả định 1 màn = 1920 (Full HD) hoặc 2560 (2K)
                    try:
                        total_width = self.winfo_screenwidth()
                        # Nếu > 2560 → có 2 màn, chia đôi
                        if total_width > 2560:
                            screen_width = total_width // 2
                            print(f"[INFO] Detected 2 screens, using 1 screen: {screen_width}")
                        else:
                            screen_width = total_width
                            print(f"[INFO] Detected 1 screen: {screen_width}")
                        screen_height = self.winfo_screenheight()
                    except:
                        screen_width = 1920  # Default 1 màn Full HD
                        screen_height = 1080
                        print(f"[INFO] Using default screen: {screen_width}x{screen_height}")
                    
                    # Bước 2: Lấy kích thước window từ Settings (TRƯỚC scale)
                    config_width = int(self.config.get('screen_width', 1920))
                    config_height = int(self.config.get('screen_height', 1080))
                    scale = float(self.config.get('device_scale_factor', 0.75))
                    
                    # Bước 3: Tính kích thước THỰC TẾ (sau scale)
                    actual_width = int(config_width * scale)
                    actual_height = int(config_height * scale)
                    
                    # ✅ V1.10.3: Check Auto Detect mode
                    auto_detect_4cols = self.config.get('auto_detect_4cols', False)
                    
                    if auto_detect_4cols:
                        # AUTO MODE: Force 4 columns với spacing đơn giản
                        cols = 4
                        # ✅ V1.10.4 FIX: Đơn giản hóa - chia đều màn hình cho 4 cột
                        spacing_width = screen_width // cols  # 1920 / 4 = 480
                        spacing_height = actual_height + 10
                        
                        print(f"[INFO] Window: {config_width}x{config_height} (before scale)")
                        print(f"[INFO] Actual size: {actual_width}x{actual_height} (after scale {scale})")
                        print(f"[INFO] AUTO MODE: Forced {cols} columns")
                        print(f"[INFO] Auto-calculated spacing: {spacing_width}x{spacing_height}")
                        print(f"[INFO] Each column width: {spacing_width}px (fit: {actual_width}px window)")
                    else:
                        # MANUAL MODE: Tính số cột dựa trên actual size
                        margin = 10
                        max_cols = screen_width // (actual_width + margin)
                        cols = min(4, max_cols) if max_cols > 0 else 1
                        spacing_width = actual_width + margin
                        spacing_height = actual_height + margin
                        
                        print(f"[INFO] Window: {config_width}x{config_height} (before scale)")
                        print(f"[INFO] Actual size: {actual_width}x{actual_height} (after scale {scale})")
                        print(f"[INFO] MANUAL MODE: {cols} columns (max: {max_cols})")
                        print(f"[INFO] Spacing: {spacing_width}x{spacing_height}")
                    
                    # Bước 5: Tính vị trí
                    profile_idx = idx - 1
                    row = profile_idx // cols
                    col = profile_idx % cols
                    
                    # Tính vị trí theo screen pixels
                    x_screen = col * spacing_width
                    y_screen = row * spacing_height
                    
                    # ✅ V1.10.5 FIX: Convert về config coordinates (TRƯỚC scale)
                    # GPM API cần tọa độ theo resolution config, không phải screen pixels
                    x_config = int(x_screen / scale)
                    y_config = int(y_screen / scale)
                    
                    win_pos = f"{x_config},{y_config}"
                    print(f"[INFO] Profile {idx}/{len(email_list)}: Position {win_pos} (Row {row+1}, Col {col+1}/{cols})")
                    print(f"[DEBUG] Screen pixels: ({x_screen},{y_screen}) → Config coords: ({x_config},{y_config})")
                except Exception as e:
                    print(f"[WARNING] Failed to calculate window position: {e}")
                    import traceback
                    traceback.print_exc()
                    win_pos = None
                
                profile_data = self.gpm_api.start_profile(account.id, self.config, win_pos)
                
                if not profile_data:
                    account.status = "Open Failed - Check logs"
                    self.save_accounts()
                    self.refresh_table()
                    return None
                
                account.status = "Profile Opened"
                self.refresh_table()
                
                # ⏰ Chờ browser - chỉ 2s
                account.status = "Browser Starting (2s)..."
                self.refresh_table()
                time.sleep(2)
                
                # Setup Selenium với GPM browser
                remote_debugging_address = profile_data.get('remote_debugging_address')
                driver_path = profile_data.get('driver_path')
                
                if not remote_debugging_address:
                    account.status = "No Debug Address"
                    self.save_accounts()
                    self.refresh_table()
                    return None
                
                account.status = "Connecting Browser..."
                self.refresh_table()
                
                print(f"[DEBUG] Profile ID: {account.id}")
                print(f"[DEBUG] Debug Address: {remote_debugging_address}")
                print(f"[DEBUG] Driver Path: {driver_path}")
                
                # ✅ Chrome options với debuggerAddress
                chrome_options = ChromeOptions()
                chrome_options.add_experimental_option("debuggerAddress", remote_debugging_address)
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                
                # Initialize driver với Service (Selenium 4.x)
                try:
                    if driver_path and os.path.exists(driver_path):
                        service = ChromeService(executable_path=driver_path)
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                    else:
                        # Fallback: dùng system chromedriver
                        driver = webdriver.Chrome(options=chrome_options)
                    
                    print(f"[DEBUG] Driver initialized successfully")
                    
                    # ✅ V1.3.4: Chờ browser ready
                    time.sleep(3)
                    
                except Exception as driver_error:
                    error_msg = str(driver_error)
                    print(f"[ERROR] Driver initialization failed: {error_msg}")
                    account.status = f"Driver Err: {error_msg[:40]}"
                    self.save_accounts()
                    self.refresh_table()
                    return None
                
                # ✅ V1.4.9: Navigate to TopCashback with custom URL from config
                account.status = "Loading TopCashback..."
                self.refresh_table()
                
                # Get TopCashback URL from config (mỗi user có link riêng)
                default_tcb_url = "https://www.topcashback.com/EmailAuthentication/?g=N0k1Unk2ZmZiQUEwV0JlKzJIaytrMWJmU09PYUhhU3lYR2hHSGovOXpIdE5tVG9Nbm9oUUd3PT0%3d&u=OTcyNDRtZW1rdFhrSHcwSWxxcVR3ZzhuM2tmSTE4L3A%3d&wl=1&utm_source=ACEEmail9&utm_medium=email&utm_campaign=TCB%20Account%20Emails"
                tcb_url = self.config.get('topcashback_url', default_tcb_url)
                
                print(f"[INFO] Using TopCashback URL: {tcb_url[:80]}...")
                
                # Tìm main window (không phải extension)
                all_windows = driver.window_handles
                print(f"[DEBUG] Windows: {len(all_windows)}")
                
                main_window = None
                for wh in all_windows:
                    driver.switch_to.window(wh)
                    url = driver.current_url
                    print(f"[DEBUG] Window: {url[:50]}")
                    if not url.startswith("chrome-extension://") and not url.startswith("devtools://"):
                        main_window = wh
                        break
                
                if not main_window:
                    main_window = all_windows[-1]
                    driver.switch_to.window(main_window)
                
                # Navigate
                driver.get(tcb_url)
                time.sleep(4)
                
                # Verify
                current = driver.current_url
                print(f"[DEBUG] Current: {current[:50]}")
                if "topcashback" not in current.lower():
                    driver.get(tcb_url)
                    time.sleep(4)
                
                driver.get(tcb_url)
                
                # Wait and search for Sephora
                account.status = "Searching Sephora..."
                self.refresh_table()
                
                wait = WebDriverWait(driver, 15)
                search_input = wait.until(EC.presence_of_element_located(
                    (By.ID, "ctl00_ctl29_Search_SiteSearchText")
                ))
                search_input.clear()
                search_input.send_keys("Sephora")
                
                # Click search button
                search_button = driver.find_element(By.ID, "ctl00_ctl29_Search_SiteSearchButton")
                search_button.click()
                
                # Wait for results and click appropriate region
                account.status = f"Selecting {region}..."
                self.refresh_table()
                
                time.sleep(2)  # Wait for results
                
                if region == "USA":
                    sephora_link = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//a[@href='/sephora']")
                    ))
                else:  # CAN
                    sephora_link = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//a[@href='/sephora-canada']")
                    ))
                
                sephora_link.click()
                time.sleep(3)
                
                # Click "Get Cash Back" button
                account.status = "Clicking Get Cash Back..."
                self.refresh_table()
                
                if region == "USA":
                    cashback_btn = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//a[@id='cashback-button' and contains(@href, 'mpurl=sephora&')]")
                    ))
                else:  # CAN
                    cashback_btn = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//a[@id='cashback-button' and contains(@href, 'mpurl=sephora-canada')]")
                    ))
                
                cashback_btn.click()
                
                # ✅ V1.4.2: Đợi lâu hơn để Sephora load
                account.status = "Loading Sephora..."
                self.refresh_table()
                time.sleep(10)  # Tăng từ 5s lên 10s
                
                # Switch to new tab if opened
                all_windows = driver.window_handles
                if len(all_windows) > 1:
                    driver.switch_to.window(all_windows[-1])
                
                # ✅ V1.4.2: Đợi page load xong
                try:
                    WebDriverWait(driver, 20).until(  # ✅ Tăng từ 15s lên 20s
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    print("[INFO] Page loaded completely")
                except:
                    print("[WARNING] Page load timeout, continuing...")
                
                time.sleep(5)  # ✅ Tăng từ 2s lên 5s để popup xuất hiện đầy đủ
                
                # ✅ V1.4.2: Close popup với retry (có thể phải click 2 lần)
                account.status = "Closing popup..."
                self.refresh_table()
                
                popup_closed = False
                for attempt in range(3):  # ✅ Tăng từ 2 lên 3 lần retry
                    try:
                        close_btn = WebDriverWait(driver, 10).until(  # ✅ Tăng từ 8s lên 10s
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Close modal']"))
                        )
                        close_btn.click()
                        time.sleep(2.5)  # ✅ Tăng từ 1s lên 2.5s
                        print(f"[INFO] Popup closed (attempt {attempt + 1})")
                        popup_closed = True
                        
                        # Check nếu popup vẫn còn
                        try:
                            driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close modal']")
                            print("[INFO] Popup still exists, trying again...")
                            continue  # ✅ FIX: continue thay vì return None để retry
                        except:
                            print("[INFO] Popup confirmed closed")
                            break
                    except:
                        if attempt == 0:
                            print("[INFO] No popup found on first attempt")
                        else:
                            print("[INFO] No popup on retry")
                        break
                
                # ✅ V1.4.5: Click Sign In 2 lần để popup hiện
                account.status = "Opening login..."
                self.refresh_table()
                
                signin_span = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "span[data-at='sign_in_header']")
                ))
                
                # Click lần 1
                signin_span.click()
                time.sleep(1)
                print("[INFO] Clicked Sign In (1st time)")
                
                # Click lần 2
                signin_span.click()
                time.sleep(2)
                print("[INFO] Clicked Sign In (2nd time) - popup should appear")
                
                # ✅ V1.4.6: Enter credentials
                account.status = "Entering credentials..."
                self.refresh_table()
                
                # Lấy email và password từ account
                user_email = account.email
                user_password = account.password
                
                email_input = wait.until(EC.presence_of_element_located(
                    (By.ID, "signin_username")
                ))
                email_input.click()  # Focus vào field
                email_input.clear()
                time.sleep(0.5)
                email_input.send_keys(user_email)
                time.sleep(1)
                
                # Enter password
                password_input = wait.until(EC.presence_of_element_located(
                    (By.ID, "signin_password")
                ))
                password_input.click()  # Focus vào field (trigger React)
                time.sleep(0.5)
                password_input.clear()
                time.sleep(0.5)
                password_input.send_keys(user_password)
                time.sleep(1)
                
                print(f"[DEBUG] Entered credentials for {user_email}")
                
                # Click Sign In
                signin_submit = driver.find_element(By.CSS_SELECTOR, "button[data-at='sign_in_button']")
                signin_submit.click()
                
                # ✅ V1.4.8: Check for errors với WebDriverWait
                account.status = "Checking login..."
                self.refresh_table()
                
                # Đợi để xem có error xuất hiện không (10s)
                time.sleep(3)
                
                has_error = False
                try:
                    # Try to find error message với wait
                    error_msg = WebDriverWait(driver, 7).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-at='sign_in_error']"))
                    )
                    error_text = error_msg.text.strip()
                    print(f"[ERROR] Login error detected: {error_text}")
                    has_error = True
                    
                    # Check SPAM trước (Oops! Something went wrong)
                    if "Oops!" in error_text or "Something went wrong" in error_text:
                        account.status = "SPAM"
                        print(f"[ERROR] Account {user_email} is SPAM")
                        self.save_accounts()  # ✅ Save trước khi continue
                        self.refresh_table()
                        # Close profile
                        if account.id:
                            self.gpm_api.stop_profile(account.id)
                        return None
                    
                    # Check Sai pass (There is an error with your email and/or password)
                    elif "error with your email" in error_text or "password" in error_text.lower():
                        account.status = "Sai pass"
                        print(f"[ERROR] Account {user_email} wrong password")
                        self.save_accounts()  # ✅ Save trước khi continue
                        self.refresh_table()
                        # Close profile
                        if account.id:
                            self.gpm_api.stop_profile(account.id)
                        return None
                    
                    # Unknown error
                    else:
                        account.status = f"Error: {error_text[:30]}"
                        print(f"[ERROR] Account {user_email} unknown error: {error_text}")
                        self.save_accounts()  # ✅ Save trước khi continue
                        self.refresh_table()
                        if account.id:
                            self.gpm_api.stop_profile(account.id)
                        return None
                        
                except Exception as e:
                    print(f"[INFO] No error message found - checking login success: {e}")
                    has_error = False
                
                # Nếu không có error, check login success
                if not has_error:
                    try:
                        success_element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//button[@id='account_drop_trigger']//strong"))
                        )
                        account.status = "✅ Logged In"
                        print(f"[SUCCESS] Account {user_email} logged in successfully")
                        
                        # ✅ V1.5.8: CLEAR BASKET trước khi ADD TO CART
                        account.status = "Opening basket to clear old items..."
                        self.refresh_table()
                        print(f"[INFO] Navigating to basket to clear old items...")
                        
                        driver.get("https://www.sephora.com/basket")
                        time.sleep(3)
                        
                        # ✅ V1.5.9: Check login khi vào basket
                        account.status = "Checking login status in basket..."
                        self.refresh_table()
                        
                        try:
                            # Check xem đã login chưa
                            login_check = driver.find_element(By.XPATH, "//button[@id='account_drop_trigger']/span/span/strong")
                            print(f"[INFO] Already logged in, basket ready")
                        except:
                            # Chưa login → Login lại
                            print(f"[WARNING] Not logged in basket, retrying login...")
                            account.status = "Retry login (basket not logged in)..."
                            self.refresh_table()
                            
                            # Click Sign In lần 1
                            signin_span = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "span[data-at='sign_in_header']"))
                            )
                            signin_span.click()
                            time.sleep(1)
                            print("[INFO] Clicked Sign In (basket retry - 1st time)")
                            
                            # Click Sign In lần 2
                            signin_span.click()
                            time.sleep(2)
                            print("[INFO] Clicked Sign In (basket retry - 2nd time)")
                            
                            # Enter email
                            email_input = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.ID, "signin_username"))
                            )
                            email_input.click()
                            email_input.clear()
                            time.sleep(0.5)
                            email_input.send_keys(user_email)
                            time.sleep(1)
                            
                            # Enter password
                            password_input = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.ID, "signin_password"))
                            )
                            password_input.click()
                            password_input.clear()
                            time.sleep(0.5)
                            password_input.send_keys(user_password)
                            time.sleep(1)
                            
                            # Click Sign In
                            signin_submit = driver.find_element(By.CSS_SELECTOR, "button[data-at='sign_in_button']")
                            signin_submit.click()
                            time.sleep(3)
                            
                            # Check login error
                            basket_retry_has_error = False
                            try:
                                basket_retry_error = WebDriverWait(driver, 7).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-at='sign_in_error']"))
                                )
                                error_text = basket_retry_error.text.strip()
                                print(f"[ERROR] Basket retry login error: {error_text}")
                                basket_retry_has_error = True
                                
                                if "Oops!" in error_text or "Something went wrong" in error_text:
                                    account.status = "SPAM (basket retry)"
                                    self.save_accounts()
                                    self.refresh_table()
                                    if account.id:
                                        self.gpm_api.stop_profile(account.id)
                                    return None
                                elif "error with your email" in error_text or "password" in error_text.lower():
                                    account.status = "Sai pass (basket retry)"
                                    self.save_accounts()
                                    self.refresh_table()
                                    if account.id:
                                        self.gpm_api.stop_profile(account.id)
                                    return None
                                else:
                                    account.status = f"Error: {error_text[:30]}"
                                    self.save_accounts()
                                    self.refresh_table()
                                    if account.id:
                                        self.gpm_api.stop_profile(account.id)
                                    return None
                            except:
                                print(f"[INFO] No error after basket retry login")
                                basket_retry_has_error = False
                            
                            # Check login success
                            if not basket_retry_has_error:
                                try:
                                    basket_retry_success = WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.XPATH, "//button[@id='account_drop_trigger']//strong"))
                                    )
                                    print(f"[SUCCESS] Basket retry login successful!")
                                    account.status = "✅ Logged In (basket retry)"
                                    self.refresh_table()
                                    
                                    # Reload basket để items hiện ra
                                    print(f"[INFO] Reloading basket after login...")
                                    driver.get("https://www.sephora.com/basket")
                                    time.sleep(3)
                                    
                                except Exception as basket_check_error:
                                    print(f"[ERROR] Basket retry login check failed: {basket_check_error}")
                                    account.status = "Login failed (basket retry)"
                                    self.save_accounts()
                                    self.refresh_table()
                                    if account.id:
                                        self.gpm_api.stop_profile(account.id)
                                    return None
                        
                        # SAU KHI ĐÃ LOGIN → Xóa items cũ trong basket
                        account.status = "Clearing old items..."
                        self.refresh_table()
                        
                        # Loop để xóa tất cả items cũ trong basket
                        removed_count = 0
                        max_attempts = 20  # Giới hạn để tránh infinite loop
                        attempt = 0
                        
                        while attempt < max_attempts:
                            try:
                                # Tìm tất cả nút remove
                                buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-at="bsk_sku_remove"]')
                                # Filter chỉ lấy visible buttons
                                visible_buttons = [b for b in buttons if b.is_displayed()]
                                
                                if len(visible_buttons) == 0:
                                    print(f"[INFO] Basket cleared! Removed {removed_count} old item(s)")
                                    break
                                
                                # Click button đầu tiên
                                visible_buttons[0].click()
                                removed_count += 1
                                print(f"[INFO] Removed item {removed_count}")
                                time.sleep(2)
                                
                                # ✅ V1.6.0: Check popup warning "Promo/Reward Code Warning"
                                # Popup này xuất hiện khi xóa items chính nhưng còn samples
                                try:
                                    # Tìm nút OK trong popup warning
                                    popup_ok_btn = WebDriverWait(driver, 3).until(
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.css-1tjizbm[data-comp="BaseComponent "]'))
                                    )
                                    popup_ok_btn.click()
                                    print(f"[INFO] Closed promo/reward warning popup")
                                    time.sleep(1)
                                except:
                                    # Không có popup → OK, tiếp tục
                                    pass
                                
                                attempt += 1
                                
                            except Exception as clear_error:
                                print(f"[WARNING] Error clearing basket: {clear_error}")
                                break
                        
                        if removed_count > 0:
                            print(f"[SUCCESS] Basket cleared: {removed_count} old item(s) removed")
                        else:
                            print(f"[INFO] Basket was already empty")
                        
                        account.status = "Basket cleared, adding new items..."
                        self.refresh_table()
                        time.sleep(1)
                        
                        # ✅ V1.5.5: ADD TO CART WORKFLOW - Lấy từ UI
                        # Get items và quantities TRỰC TIẾP từ UI
                        items = [
                            (self.item1_entry.get().strip(), self.qty1_entry.get().strip()),
                            (self.item2_entry.get().strip(), self.qty2_entry.get().strip()),
                            (self.item3_entry.get().strip(), self.qty3_entry.get().strip())
                        ]
                        
                        print(f"[DEBUG] Items from UI: {items}")
                        
                        added_count = 0
                        out_of_stock_count = 0
                        
                        for idx, (item_url, qty) in enumerate(items, 1):
                            # Skip nếu item rỗng
                            if not item_url or not item_url.strip():
                                print(f"[INFO] Item {idx} empty, skipping...")
                                continue  # ✅ FIX: continue thay vì return None
                            
                            # ✅ V1.7.2: Default qty = 1 nếu trống
                            if not qty or not qty.strip():
                                qty = "1"
                                print(f"[INFO] Item {idx} qty empty, defaulting to 1")
                            
                            try:
                                # Navigate to product
                                account.status = f"Loading Item {idx}..."
                                self.refresh_table()
                                print(f"[INFO] Opening Item {idx}: {item_url[:50]}...")
                                
                                driver.get(item_url)
                                time.sleep(4)
                                
                                # Check out of stock
                                account.status = f"Checking stock Item {idx}..."
                                self.refresh_table()
                                
                                try:
                                    out_of_stock_btn = driver.find_element(By.CSS_SELECTOR, "button[data-at='out_of_stock_btn']")
                                    print(f"[WARNING] Item {idx} is OUT OF STOCK")
                                    
                                    # ✅ V1.9.2: Set status và đóng profile ngay
                                    account.status = f"Item {idx} out of stock"
                                    self.refresh_table()
                                    self.save_accounts()
                                    
                                    # Đóng profile
                                    if account.id:
                                        self.gpm_api.stop_profile(account.id)
                                        print(f"[INFO] Profile closed due to Item {idx} out of stock")
                                    
                                    return None  # Dừng ngay
                                except:
                                    print(f"[INFO] Item {idx} is in stock")
                                
                                # ✅ V1.5.5: SKIP select quantity nếu qty = 1
                                if qty != "1":
                                    # Select quantity
                                    account.status = f"Selecting qty {qty} for Item {idx}..."
                                    self.refresh_table()
                                    
                                    try:
                                        qty_select = WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located((By.CSS_SELECTOR, "select[data-at='sku_qty']"))
                                        )
                                        
                                        # Select quantity bằng Select class của Selenium
                                        from selenium.webdriver.support.ui import Select
                                        select = Select(qty_select)
                                        select.select_by_value(qty)
                                        print(f"[INFO] Selected quantity: {qty}")
                                        time.sleep(2)
                                        
                                    except Exception as qty_error:
                                        print(f"[WARNING] Cannot select quantity for Item {idx}: {qty_error}")
                                        # Tiếp tục với quantity mặc định
                                else:
                                    print(f"[INFO] Quantity is 1, skipping select...")
                                
                                # Click Add to Basket
                                account.status = f"Adding Item {idx} to cart..."
                                self.refresh_table()
                                
                                add_to_cart_btn = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-at='add_to_basket_btn']"))
                                )
                                add_to_cart_btn.click()
                                print(f"[SUCCESS] Added Item {idx} to cart!")
                                added_count += 1
                                time.sleep(3)
                                
                            except Exception as item_error:
                                print(f"[ERROR] Failed to add Item {idx}: {item_error}")
                                
                                # ✅ V1.9.3: Set status và đóng profile khi add to basket error
                                account.status = "Add to Basket Error"
                                self.refresh_table()
                                self.save_accounts()
                                
                                # Đóng profile
                                if account.id:
                                    self.gpm_api.stop_profile(account.id)
                                    print(f"[INFO] Profile closed due to Add to Basket Error")
                                
                                return None  # Dừng ngay
                        
                        # Navigate to basket
                        print(f"[DEBUG] Loop finished. added_count={added_count}, out_of_stock_count={out_of_stock_count}")
                        
                        if added_count > 0:
                            account.status = f"Opening basket ({added_count} items)..."
                            self.refresh_table()
                            print(f"[INFO] Opening basket with {added_count} item(s)...")
                            
                            driver.get("https://www.sephora.com/basket")
                            time.sleep(3)
                            
                            # ✅ V1.9.4: Áp dụng Coupon nếu có
                            coupon_code = self.coupon_entry.get().strip()
                            if coupon_code:
                                try:
                                    account.status = "Checking login..."
                                    self.refresh_table()
                                    
                                    # ✅ Step 1: Check đăng nhập trước
                                    try:
                                        login_check = driver.find_element(By.XPATH, "//button[@id='account_drop_trigger']//strong")
                                        print(f"[INFO] Đã đăng nhập: {login_check.text}")
                                    except:
                                        print(f"[WARNING] Chưa đăng nhập, đang đăng nhập lại...")
                                        account.status = "Logging in..."
                                        self.refresh_table()
                                        
                                        # RETRY LOGIN
                                        signin_span = WebDriverWait(driver, 10).until(
                                            EC.element_to_be_clickable((By.CSS_SELECTOR, "span[data-at='sign_in_header']"))
                                        )
                                        signin_span.click()
                                        time.sleep(1)
                                        signin_span.click()
                                        time.sleep(2)
                                        
                                        email_input = WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located((By.ID, "signin_username"))
                                        )
                                        email_input.click()
                                        email_input.clear()
                                        time.sleep(0.5)
                                        email_input.send_keys(user_email)
                                        time.sleep(1)
                                        
                                        password_input = WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located((By.ID, "signin_password"))
                                        )
                                        password_input.click()
                                        password_input.clear()
                                        time.sleep(0.5)
                                        password_input.send_keys(user_password)
                                        time.sleep(1)
                                        
                                        signin_submit = driver.find_element(By.CSS_SELECTOR, "button[data-at='sign_in_button']")
                                        signin_submit.click()
                                        time.sleep(3)
                                        
                                        # Check login thành công
                                        try:
                                            login_check = driver.find_element(By.XPATH, "//button[@id='account_drop_trigger']//strong")
                                            print(f"[SUCCESS] Đăng nhập thành công!")
                                        except:
                                            print(f"[ERROR] Đăng nhập thất bại")
                                    
                                    # ✅ Step 2: Apply coupon
                                    account.status = "Applying coupon..."
                                    self.refresh_table()
                                    print(f"[INFO] Applying coupon: {coupon_code}")
                                    
                                    promo_input = WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.ID, "promoInput"))
                                    )
                                    promo_input.clear()
                                    promo_input.send_keys(coupon_code)
                                    time.sleep(1)

                                    # ✅ V1.10.7: Chỉ click Apply coupon (type="submit"), tránh nhầm với Apply 500 points (type="button")
                                    apply_btn = driver.find_element(By.CSS_SELECTOR, "button[data-at='apply_btn'][type='submit']")
                                    apply_btn.click()
                                    time.sleep(3)
                                    
                                    # ✅ Step 3: Check errors
                                    try:
                                        error_msg = driver.find_element(By.CSS_SELECTOR, "p.css-oxeibp[role='alert']")
                                        error_text = error_msg.text.strip()
                                        print(f"[WARNING] Coupon error: {error_text}")
                                        
                                        if "does not exist" in error_text:
                                            # Coupon invalid
                                            account.status = "Coupon invalid"
                                            self.refresh_table()
                                            self.save_accounts()
                                            
                                            if account.id:
                                                self.gpm_api.stop_profile(account.id)
                                                print(f"[INFO] Profile closed due to Coupon invalid")
                                            
                                            return None
                                        
                                        elif "expired or has run out of inventory" in error_text:
                                            # ✅ V1.9.5: Coupon hết hạn
                                            account.status = "Coupon hết hạn"
                                            self.refresh_table()
                                            self.save_accounts()
                                            
                                            if account.id:
                                                self.gpm_api.stop_profile(account.id)
                                                print(f"[INFO] Profile closed due to Coupon hết hạn")
                                            
                                            return None
                                        
                                        elif "exceeded the number of redemptions" in error_text:
                                            # ✅ V1.9.6: Acc đã dùng coupon
                                            account.status = "Acc đã dùng coupon"
                                            self.refresh_table()
                                            self.save_accounts()
                                            
                                            if account.id:
                                                self.gpm_api.stop_profile(account.id)
                                                print(f"[INFO] Profile closed due to Acc đã dùng coupon")
                                            
                                            return None
                                        
                                        elif "Must be logged into" in error_text or "Beauty Insider" in error_text:
                                            # Đã đăng nhập nhưng vẫn lỗi → Kiểm tra Coupon
                                            account.status = "Kiểm tra Coupon or login fail"
                                            self.refresh_table()
                                            self.save_accounts()
                                            
                                            if account.id:
                                                self.gpm_api.stop_profile(account.id)
                                                print(f"[INFO] Profile closed - Kiểm tra Coupon or login fail")
                                            
                                            return None
                                    except:
                                        # Không có error → Coupon OK
                                        pass
                                    
                                    # ✅ Step 4: Check popup chọn quà
                                    coupon_items = [
                                        self.coupon_item1_entry.get().strip(),
                                        self.coupon_item2_entry.get().strip(),
                                        self.coupon_item3_entry.get().strip(),
                                        self.coupon_item4_entry.get().strip()
                                    ]
                                    
                                    # Filter chỉ lấy items có giá trị
                                    coupon_items = [item for item in coupon_items if item]
                                    
                                    if coupon_items:
                                        # Có popup items
                                        print(f"[INFO] Coupon có popup, chọn {len(coupon_items)} item(s)")
                                        account.status = f"Selecting {len(coupon_items)} promo items..."
                                        self.refresh_table()
                                        time.sleep(2)
                                        
                                        for item_name in coupon_items:
                                            try:
                                                print(f"[INFO] Searching for promo item: {item_name}...")
                                                
                                                # ✅ V1.9.7: Tìm theo brand hoặc product name
                                                result = driver.execute_script("""
                                                    const searchText = arguments[0];
                                                    const items = document.querySelectorAll('[data-at="promo_item"]');
                                                    
                                                    for (let item of items) {
                                                        const brand = item.querySelector('[data-at="sku_item_brand"]')?.textContent || '';
                                                        const name = item.querySelector('[data-at="sku_item_name"]')?.textContent || '';
                                                        
                                                        if (brand.toLowerCase().includes(searchText.toLowerCase()) || 
                                                            name.toLowerCase().includes(searchText.toLowerCase())) {
                                                            const addBtn = item.querySelector('[data-at="promo_item_add_button"]');
                                                            if (addBtn) {
                                                                addBtn.click();
                                                                return true;
                                                            }
                                                        }
                                                    }
                                                    return false;
                                                """, item_name)
                                                
                                                if result:
                                                    print(f"[SUCCESS] Clicked promo item: {item_name}")
                                                else:
                                                    # ✅ V1.9.8: Item không tìm thấy → Dừng ngay
                                                    print(f"[WARNING] Promo item not found: {item_name}")
                                                    account.status = f"Hết {item_name}"
                                                    self.refresh_table()
                                                    self.save_accounts()
                                                    
                                                    if account.id:
                                                        self.gpm_api.stop_profile(account.id)
                                                        print(f"[INFO] Profile closed - Hết {item_name}")
                                                    
                                                    return None
                                                
                                                time.sleep(1.5)
                                            except Exception as item_err:
                                                print(f"[WARNING] Failed to click promo item '{item_name}': {item_err}")
                                        
                                        # Click Done button
                                        try:
                                            done_btn = driver.find_element(By.CSS_SELECTOR, "button[data-at='done_button']")
                                            done_btn.click()
                                            print(f"[SUCCESS] Clicked Done button!")
                                            time.sleep(2)
                                            
                                            # ✅ V1.9.5: Check error sau Done
                                            try:
                                                error_after_done = driver.find_element(By.CSS_SELECTOR, "p.css-oxeibp[role='alert']")
                                                error_done_text = error_after_done.text.strip()
                                                
                                                if "expired or has run out of inventory" in error_done_text:
                                                    print(f"[WARNING] Item coupon hết hàng: {error_done_text}")
                                                    account.status = "Item coupon hết hàng"
                                                    self.refresh_table()
                                                    self.save_accounts()
                                                    
                                                    if account.id:
                                                        self.gpm_api.stop_profile(account.id)
                                                        print(f"[INFO] Profile closed due to Item coupon hết hàng")
                                                    
                                                    return None
                                            except:
                                                # Không có error → OK
                                                print(f"[SUCCESS] Popup items applied successfully!")
                                            
                                        except Exception as done_err:
                                            print(f"[WARNING] Failed to click Done: {done_err}")
                                    else:
                                        # Không có popup
                                        print(f"[SUCCESS] Coupon applied (no popup)!")
                                    
                                except Exception as coupon_error:
                                    print(f"[ERROR] Failed to apply coupon: {coupon_error}")

                            # ✅ V1.10.7: Apply discount code (Giảm 10$ hoặc 20$)
                            discount_code = None
                            if self.discount_10_var.get():
                                discount_code = "cbr_10_500"
                            elif self.discount_20_var.get():
                                discount_code = "cbr_20_1000"

                            if discount_code:
                                try:
                                    account.status = f"Applying {discount_code}..."
                                    self.refresh_table()
                                    print(f"[INFO] Applying discount code: {discount_code}")

                                    # Nhập code vào input coupon
                                    promo_input = WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.ID, "promoInput"))
                                    )
                                    promo_input.clear()
                                    promo_input.send_keys(discount_code)
                                    time.sleep(1)

                                    # Click Apply button (type="submit")
                                    apply_btn = driver.find_element(By.CSS_SELECTOR, "button[data-at='apply_btn'][type='submit']")
                                    apply_btn.click()
                                    time.sleep(2)

                                    # ✅ V1.10.8: Kiểm tra lỗi "You do not have enough current points"
                                    try:
                                        error_msg = driver.find_element(By.CSS_SELECTOR, 'p.css-oxeibp[role="alert"][data-comp="InputMsg BaseComponent "]')
                                        error_text = error_msg.text

                                        if "You do not have enough current points" in error_text:
                                            # Xác định loại discount
                                            discount_type = "10$" if self.discount_10_var.get() else "20$"
                                            account.status = f"Không đủ points giảm {discount_type}"
                                            self.refresh_table()
                                            self.save_accounts()
                                            print(f"[ERROR] {account.status}")

                                            if account.id:
                                                self.gpm_api.stop_profile(account.id)
                                                print(f"[INFO] Profile closed - {account.status}")

                                            return None
                                    except:
                                        # Không có lỗi, tiếp tục
                                        pass

                                    print(f"[SUCCESS] Applied {discount_code}!")

                                except Exception as discount_error:
                                    print(f"[WARNING] Failed to apply {discount_code}: {discount_error}")

                            # ✅ V1.9.9: Chọn Sample nếu có (theo tên)
                            sample1 = self.sample1_entry.get().strip()
                            sample2 = self.sample2_entry.get().strip()
                            
                            if sample1 or sample2:
                                try:
                                    account.status = "Selecting samples..."
                                    self.refresh_table()
                                    print(f"[INFO] Selecting samples: Sample1={sample1}, Sample2={sample2}")
                                    
                                    # Click button "Add up to 2 Free Samples"
                                    sample_btn = WebDriverWait(driver, 10).until(
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-comp="FreeSamples BaseComponent "]'))
                                    )
                                    sample_btn.click()
                                    time.sleep(2)
                                    print(f"[INFO] Sample popup opened")
                                    
                                    # Chọn Sample 1
                                    if sample1:
                                        print(f"[INFO] Searching for Sample 1: {sample1}...")
                                        result = driver.execute_script("""
                                            const searchText = arguments[0];
                                            const items = document.querySelectorAll('[data-at="sample_item"]');
                                            
                                            for (let item of items) {
                                                const name = item.querySelector('[data-at="sku_item_name"]')?.textContent || '';
                                                
                                                if (name.toLowerCase().includes(searchText.toLowerCase())) {
                                                    const addBtn = item.querySelector('[data-at="add_to_basket_btn"]');
                                                    if (addBtn) {
                                                        addBtn.click();
                                                        return true;
                                                    }
                                                }
                                            }
                                            return false;
                                        """, sample1)
                                        
                                        if result:
                                            print(f"[SUCCESS] Selected Sample 1: {sample1}")
                                            time.sleep(7)
                                        else:
                                            # ✅ V1.9.9: Sample không tìm thấy → Dừng ngay
                                            print(f"[WARNING] Sample not found: {sample1}")
                                            account.status = f"Hết {sample1}"
                                            self.refresh_table()
                                            self.save_accounts()
                                            
                                            if account.id:
                                                self.gpm_api.stop_profile(account.id)
                                                print(f"[INFO] Profile closed - Hết {sample1}")
                                            
                                            return None
                                    
                                    # Chọn Sample 2
                                    if sample2:
                                        print(f"[INFO] Searching for Sample 2: {sample2}...")
                                        result = driver.execute_script("""
                                            const searchText = arguments[0];
                                            const items = document.querySelectorAll('[data-at="sample_item"]');
                                            
                                            for (let item of items) {
                                                const name = item.querySelector('[data-at="sku_item_name"]')?.textContent || '';
                                                
                                                if (name.toLowerCase().includes(searchText.toLowerCase())) {
                                                    const addBtn = item.querySelector('[data-at="add_to_basket_btn"]');
                                                    if (addBtn) {
                                                        addBtn.click();
                                                        return true;
                                                    }
                                                }
                                            }
                                            return false;
                                        """, sample2)
                                        
                                        if result:
                                            print(f"[SUCCESS] Selected Sample 2: {sample2}")
                                            time.sleep(2)
                                        else:
                                            # ✅ V1.9.9: Sample không tìm thấy → Dừng ngay
                                            print(f"[WARNING] Sample not found: {sample2}")
                                            account.status = f"Hết {sample2}"
                                            self.refresh_table()
                                            self.save_accounts()
                                            
                                            if account.id:
                                                self.gpm_api.stop_profile(account.id)
                                                print(f"[INFO] Profile closed - Hết {sample2}")
                                            
                                            return None
                                    
                                    # Click Done
                                    done_btn = driver.find_element(By.CSS_SELECTOR, "button.css-u1lgrz")
                                    done_btn.click()
                                    time.sleep(2)
                                    print(f"[SUCCESS] Samples selected!")
                                    
                                except Exception as sample_error:
                                    print(f"[ERROR] Failed to select samples: {sample_error}")

                            # ✅ V1.10.7: Chọn Point Rewards (nếu có)
                            point_items = [
                                self.point1_entry.get().strip(),
                                self.point2_entry.get().strip(),
                                self.point3_entry.get().strip(),
                                self.point4_entry.get().strip(),
                                self.point5_entry.get().strip()
                            ]
                            point_items = [p for p in point_items if p]  # Lọc bỏ empty

                            if point_items:
                                try:
                                    account.status = "Selecting Point items..."
                                    self.refresh_table()
                                    print(f"[INFO] Selecting {len(point_items)} Point item(s): {point_items}")

                                    # Click "Apply Points for Bazaar Items" button
                                    point_btn = WebDriverWait(driver, 10).until(
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.css-bgk68u[data-comp="BaseComponent "]'))
                                    )
                                    point_btn.click()
                                    time.sleep(2)
                                    print(f"[INFO] Point popup opened")

                                    # Loop qua từng Point item
                                    for idx, point_name in enumerate(point_items, 1):
                                        print(f"[INFO] Searching for Point {idx}: {point_name}...")

                                        # Tìm product theo tên trong popup
                                        result = driver.execute_script("""
                                            const searchText = arguments[0];
                                            const items = document.querySelectorAll('a[data-at="product_item_container"]');

                                            for (let item of items) {
                                                const brandElem = item.querySelector('span[data-at="product_brand_label"]');
                                                const nameElem = item.querySelector('span[data-at="product_name_label"]');
                                                const brand = brandElem ? brandElem.textContent : '';
                                                const name = nameElem ? nameElem.textContent : '';
                                                const fullName = brand + ' ' + name;

                                                if (fullName.toLowerCase().includes(searchText.toLowerCase())) {
                                                    const addBtn = item.querySelector('button[data-comp="AddToBasketButton BaseComponent "]');
                                                    if (addBtn) {
                                                        // Check if button is disabled
                                                        if (addBtn.hasAttribute('disabled')) {
                                                            return 'disabled';
                                                        }
                                                        addBtn.click();
                                                        return true;
                                                    }
                                                }
                                            }
                                            return false;
                                        """, point_name)

                                        if result == 'disabled':
                                            print(f"[ERROR] Not enough points for: {point_name}")
                                            account.status = "Không đủ points"
                                            self.refresh_table()
                                            self.save_accounts()

                                            if account.id:
                                                self.gpm_api.stop_profile(account.id)
                                                print(f"[INFO] Profile closed - Không đủ points")

                                            return None
                                        elif result:
                                            print(f"[SUCCESS] Clicked Add for Point {idx}: {point_name}")
                                            time.sleep(2)

                                            # Click Confirm button
                                            try:
                                                confirm_btn = WebDriverWait(driver, 5).until(
                                                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-at="change_method_modal_confirm_btn"]'))
                                                )
                                                confirm_btn.click()
                                                print(f"[SUCCESS] Confirmed Point {idx}")
                                                time.sleep(2)
                                            except Exception as confirm_error:
                                                print(f"[WARNING] No confirm button for Point {idx}: {confirm_error}")
                                        else:
                                            print(f"[WARNING] Point item not found: {point_name}")

                                    # Click Done để đóng popup
                                    done_btn = driver.find_element(By.CSS_SELECTOR, "button.css-1ab2xd")
                                    done_btn.click()
                                    time.sleep(2)
                                    print(f"[SUCCESS] Point items selected!")

                                except Exception as point_error:
                                    print(f"[ERROR] Failed to select Point items: {point_error}")

                            account.status = f"✅ Added {added_count} items"
                            if out_of_stock_count > 0:
                                account.status += f" ({out_of_stock_count} OOS)"
                            
                            # ✅ V1.10.6: Check basket items count
                            try:
                                expected_total = int(self.config.get('total_item', '3'))
                                print(f"[INFO] Expected total items: {expected_total}")
                                
                                account.status = "Checking basket count..."
                                self.refresh_table()
                                time.sleep(2)
                                
                                actual_count = self.check_basket_items_count(driver)
                                
                                if actual_count is None:
                                    print(f"[WARNING] Could not get basket items count, continuing anyway...")
                                elif actual_count < expected_total:
                                    print(f"[ERROR] Basket items ({actual_count}) < Expected ({expected_total})")
                                    account.status = "Add thiếu Item"
                                    self.refresh_table()
                                    self.save_accounts()
                                    
                                    # Close profile
                                    if account.id:
                                        self.gpm_api.stop_profile(account.id)
                                        print("[INFO] Profile closed - Add thiếu Item")
                                    
                                    return None
                                elif actual_count > expected_total:
                                    print(f"[ERROR] Basket items ({actual_count}) > Expected ({expected_total})")
                                    account.status = "Add thừa item"
                                    self.refresh_table()
                                    self.save_accounts()
                                    
                                    # Close profile
                                    if account.id:
                                        self.gpm_api.stop_profile(account.id)
                                        print("[INFO] Profile closed - Add thừa item")
                                    
                                    return None
                                else:
                                    print(f"[SUCCESS] Basket items count matches: {actual_count} = {expected_total}")
                            except ValueError:
                                print(f"[WARNING] Invalid total_item config, skipping validation")
                            except Exception as check_error:
                                print(f"[WARNING] Failed to validate basket count: {check_error}")
                            
                            # ✅ V1.6.1: Click Checkout button
                            account.status = "Clicking Checkout..."
                            self.refresh_table()
                            print(f"[INFO] Clicking Checkout button...")
                            time.sleep(2)
                            
                            try:
                                # Tìm tất cả checkout buttons
                                checkout_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-at="basket_checkout_btn"]')
                                # Filter chỉ lấy visible button
                                visible_checkout = [btn for btn in checkout_buttons if btn.is_displayed()]
                                
                                if len(visible_checkout) > 0:
                                    visible_checkout[0].click()
                                    print(f"[SUCCESS] Clicked Checkout button")
                                    time.sleep(3)
                                    account.status = "In Checkout..."
                                    self.refresh_table()
                                    
                                    # ✅ V1.6.5: Ưu tiên warehouse từ account, fallback về dropdown
                                    selected_warehouse = None
                                    
                                    # Check account warehouse first
                                    if hasattr(account, 'warehouse_name') and account.warehouse_name:
                                        # Tìm warehouse theo name
                                        for wh in self.warehouses:
                                            if wh.name == account.warehouse_name:
                                                selected_warehouse = wh
                                                print(f"[INFO] Using warehouse from account: {wh.name}")
                                                break
                                    
                                    # Fallback to dropdown selection
                                    if not selected_warehouse and hasattr(self, 'warehouse_selected') and self.warehouse_selected:
                                        selected_warehouse = self.warehouse_selected
                                        print(f"[INFO] Using warehouse from dropdown: {selected_warehouse.name}")
                                    
                                    if selected_warehouse:
                                        try:
                                            wh = selected_warehouse
                                            account.status = "Filling shipping address..."
                                            self.refresh_table()
                                            print(f"[INFO] Auto-filling shipping address from warehouse: {wh.name}")
                                            
                                            time.sleep(2)
                                            
                                            # Check case 1: Chưa có địa chỉ (form hiện sẵn)
                                            # hoặc case 2: Đã có địa chỉ (cần click Change -> Add shipping address)
                                            has_change_button = False
                                            try:
                                                change_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Change Deliver To"]')
                                                has_change_button = True
                                                print(f"[INFO] Found Change button - Case 2: Đã có địa chỉ")
                                            except:
                                                print(f"[INFO] No Change button - Case 1: Chưa có địa chỉ")
                                            
                                            # Case 2: Đã có địa chỉ -> Click Change -> Edit first address
                                            if has_change_button:
                                                print(f"[INFO] Clicking Change button...")
                                                change_btn.click()
                                                time.sleep(2)
                                                
                                                # ✅ V1.7.2: Click Edit address (first one) instead of Add new
                                                print(f"[INFO] Clicking Edit address (first address)...")
                                                try:
                                                    edit_addr_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Edit address"]')
                                                    if len(edit_addr_buttons) > 0:
                                                        edit_addr_buttons[0].click()
                                                        time.sleep(2)
                                                        print(f"[SUCCESS] Clicked Edit address")
                                                    else:
                                                        # Fallback: Add new address if no edit button
                                                        print(f"[WARNING] No Edit button found, adding new address...")
                                                        add_addr_btn = WebDriverWait(driver, 10).until(
                                                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-at="addAddress"]'))
                                                        )
                                                        add_addr_btn.click()
                                                        time.sleep(2)
                                                except Exception as edit_error:
                                                    print(f"[ERROR] Failed to click Edit address: {edit_error}")
                                                    # Fallback: Add new address
                                                    print(f"[INFO] Falling back to Add shipping address...")
                                                    add_addr_btn = WebDriverWait(driver, 10).until(
                                                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-at="addAddress"]'))
                                                    )
                                                    add_addr_btn.click()
                                                    time.sleep(2)
                                            
                                            # Nhập thông tin (cả 2 case đều giống nhau)
                                            print(f"[INFO] Filling First Name: {wh.first_name}")
                                            first_name_input = WebDriverWait(driver, 10).until(
                                                EC.presence_of_element_located((By.ID, "firstName"))
                                            )
                                            # ✅ V1.7.2: Clear tốt hơn - select all + delete
                                            first_name_input.click()
                                            time.sleep(0.2)
                                            first_name_input.send_keys(Keys.CONTROL + "a")
                                            time.sleep(0.1)
                                            first_name_input.send_keys(Keys.DELETE)
                                            time.sleep(0.2)
                                            first_name_input.send_keys(wh.first_name)
                                            time.sleep(0.5)
                                            
                                            print(f"[INFO] Filling Last Name: {wh.last_name}")
                                            last_name_input = driver.find_element(By.ID, "lastName")
                                            last_name_input.click()
                                            time.sleep(0.2)
                                            last_name_input.send_keys(Keys.CONTROL + "a")
                                            time.sleep(0.1)
                                            last_name_input.send_keys(Keys.DELETE)
                                            time.sleep(0.2)
                                            last_name_input.send_keys(wh.last_name)
                                            time.sleep(0.5)
                                            
                                            print(f"[INFO] Filling Phone: {wh.phone}")
                                            phone_input = driver.find_element(By.ID, "phone")
                                            phone_input.click()
                                            time.sleep(0.2)
                                            phone_input.send_keys(Keys.CONTROL + "a")
                                            time.sleep(0.1)
                                            phone_input.send_keys(Keys.DELETE)
                                            time.sleep(0.2)
                                            phone_input.send_keys(wh.phone)
                                            time.sleep(0.5)
                                            
                                            print(f"[INFO] Filling Address: {wh.address}")
                                            address_input = driver.find_element(By.ID, "avs_input")
                                            address_input.click()
                                            time.sleep(0.2)
                                            address_input.send_keys(Keys.CONTROL + "a")
                                            time.sleep(0.1)
                                            address_input.send_keys(Keys.DELETE)
                                            time.sleep(0.2)
                                            address_input.send_keys(wh.address)
                                            time.sleep(0.5)
                                            
                                            print(f"[INFO] Filling Zipcode: {wh.zip}")
                                            zip_input = driver.find_element(By.ID, "postalCode")
                                            zip_input.click()
                                            time.sleep(0.2)
                                            zip_input.send_keys(Keys.CONTROL + "a")
                                            time.sleep(0.1)
                                            zip_input.send_keys(Keys.DELETE)
                                            time.sleep(0.2)
                                            zip_input.send_keys(wh.zip)
                                            time.sleep(2)  # Wait for City & State auto-fill
                                            
                                            # Nếu case 2, check checkbox "Set as default"
                                            if has_change_button:
                                                try:
                                                    print(f"[INFO] Checking 'Set as default' checkbox...")
                                                    
                                                    # ✅ V1.6.5: Thử nhiều cách click checkbox
                                                    checkbox_checked = False
                                                    
                                                    # Cách 1: Tìm input checkbox
                                                    try:
                                                        default_checkbox = driver.find_element(By.CSS_SELECTOR, 'input[name="is_default"]')
                                                        if not default_checkbox.is_selected():
                                                            # Thử click trực tiếp
                                                            try:
                                                                default_checkbox.click()
                                                                checkbox_checked = True
                                                                print(f"[SUCCESS] Clicked checkbox directly")
                                                            except:
                                                                # Nếu không click được, thử JavaScript
                                                                driver.execute_script("arguments[0].click();", default_checkbox)
                                                                checkbox_checked = True
                                                                print(f"[SUCCESS] Clicked checkbox via JavaScript")
                                                        else:
                                                            checkbox_checked = True
                                                            print(f"[INFO] Checkbox already checked")
                                                    except Exception as input_error:
                                                        print(f"[WARNING] Could not find input checkbox: {input_error}")
                                                    
                                                    # Cách 2: Nếu chưa check được, thử click vào label
                                                    if not checkbox_checked:
                                                        try:
                                                            # ✅ V1.7.2: Check xem đã selected chưa trước khi click label
                                                            default_checkbox = driver.find_element(By.CSS_SELECTOR, 'input[name="is_default"]')
                                                            
                                                            if not default_checkbox.is_selected():
                                                                # Chưa tích, click label
                                                                label = driver.find_element(By.CSS_SELECTOR, 'label[data-comp*="Checkbox"]')
                                                                label.click()
                                                                checkbox_checked = True
                                                                print(f"[SUCCESS] Clicked checkbox label")
                                                            else:
                                                                # Đã tích rồi
                                                                checkbox_checked = True
                                                                print(f"[INFO] Checkbox already selected (via label check)")
                                                                
                                                        except Exception as label_error:
                                                            print(f"[WARNING] Could not click label: {label_error}")
                                                    
                                                    # Cách 3: Nếu vẫn chưa được, dùng JavaScript để set checked
                                                    if not checkbox_checked:
                                                        try:
                                                            driver.execute_script("""
                                                                var checkbox = document.querySelector('input[name="is_default"]');
                                                                if (checkbox) {
                                                                    checkbox.checked = true;
                                                                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                                                }
                                                            """)
                                                            print(f"[SUCCESS] Set checkbox via JavaScript property")
                                                        except Exception as js_error:
                                                            print(f"[WARNING] JavaScript set failed: {js_error}")
                                                    
                                                    time.sleep(0.5)
                                                    
                                                except Exception as cb_error:
                                                    print(f"[WARNING] Could not check default checkbox: {cb_error}")
                                            
                                            # Click Save & Continue
                                            print(f"[INFO] Clicking Save & Continue...")
                                            save_btn = WebDriverWait(driver, 10).until(
                                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-at="save_continue_btn"]'))
                                            )
                                            save_btn.click()
                                            time.sleep(3)
                                            
                                            print(f"[SUCCESS] Shipping address filled and saved!")
                                            account.status = "✅ Shipping address saved"
                                            self.refresh_table()
                                            
                                            # ========== V1.7.1: GIFTCARD LOGIC ==========
                                            gift1 = None
                                            gift2 = None
                                            backup_balances = None
                                            
                                            try:
                                                # Wait for page to load after saving address
                                                time.sleep(3)
                                                
                                                # Step 1: Get order total
                                                account.status = "Getting order total..."
                                                self.refresh_table()
                                                print("[INFO] Getting order total...")
                                                
                                                order_total = self.get_order_total_from_page(driver)
                                                
                                                if order_total:
                                                    # ✅ V1.8.5: Convert to float for comparison
                                                    try:
                                                        order_total = float(order_total)
                                                    except:
                                                        print(f"[ERROR] Invalid order total: {order_total}")
                                                        account.status = "❌ Invalid order total"
                                                        self.refresh_table()
                                                        self.gpm_api.stop_profile(account.id)
                                                        return None
                                                    
                                                    print(f"[INFO] Order total: ${order_total}")
                                                    
                                                    # ✅ V1.9.1: Filter gifts có balance > 0 trước khi check
                                                    available_gifts = [gc for gc in self.giftcards 
                                                                      if self.normalize_balance(gc.balance) >= 0.01]
                                                    
                                                    if len(available_gifts) == 0:
                                                        print(f"[ERROR] No giftcards available!")
                                                        account.status = "Hết tiền"
                                                        self.refresh_table()
                                                        self.gpm_api.stop_profile(account.id)
                                                        return None
                                                    
                                                    # ✅ Check 2 gift cards LỚN NHẤT có đủ không (vì chỉ dùng max 2 gift)
                                                    sorted_gifts = sorted(available_gifts, key=lambda x: self.normalize_balance(x.balance), reverse=True)
                                                    
                                                    # Lấy 2 gift lớn nhất
                                                    max_balance = self.normalize_balance(sorted_gifts[0].balance)
                                                    if len(sorted_gifts) >= 2:
                                                        max_balance += self.normalize_balance(sorted_gifts[1].balance)
                                                    
                                                    print(f"[INFO] Max possible balance (top 2 gifts): ${max_balance}")
                                                    
                                                    if max_balance < order_total:
                                                        print(f"[ERROR] Not enough! Max 2 gifts: ${max_balance} < Order: ${order_total}")
                                                        account.status = "Thiếu $"
                                                        self.refresh_table()
                                                        self.gpm_api.stop_profile(account.id)
                                                        return None
                                                    
                                                    # Step 2: Select giftcards (TRỪ BALANCE NGAY)
                                                    account.status = "Selecting giftcards..."
                                                    self.refresh_table()
                                                    
                                                    gift1, gift2, backup_balances = self.select_giftcards_for_order(account, order_total)
                                                    
                                                    if gift1 is None:
                                                        print("[ERROR] Not enough giftcards!")
                                                        account.status = "❌ Not enough giftcards"
                                                        self.refresh_table()
                                                        
                                                        # Close profile
                                                        self.gpm_api.stop_profile(account.id)
                                                        return None
                                                    
                                                    # Step 3: Gán giftcard vào account (balance đã trừ)
                                                    account.status = "Assigning giftcards..."
                                                    self.refresh_table()
                                                    
                                                    success = self.assign_giftcards_to_account(account, gift1, gift2, backup_balances)
                                                    
                                                    if not success:
                                                        print("[ERROR] Failed to assign giftcards")
                                                        account.status = "❌ Assign gift failed"
                                                        self.refresh_table()
                                                        
                                                        # Restore balances
                                                        self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                                        return None
                                                    
                                                    # ✅ Step 4: Apply giftcards vào form
                                                    account.status = "Applying giftcards..."
                                                    self.refresh_table()
                                                    
                                                    apply_success = self.apply_giftcards_to_checkout(driver, gift1, gift2)
                                                    
                                                    if not apply_success:
                                                        print("[ERROR] Failed to apply giftcards to checkout")
                                                        account.status = "❌ Apply gift failed"
                                                        self.refresh_table()
                                                        
                                                        # Restore balances
                                                        self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                                        return None
                                                    
                                                    print(f"[SUCCESS] Giftcards applied successfully!")
                                                    account.status = "✅ Gifts applied"
                                                    self.refresh_table()
                                                    
                                                    # Refresh table để hiển thị Gift 1, Gift 2
                                                    time.sleep(1)
                                                    self.refresh_table()
                                                    
                                                    # ========== V1.8.9: VERIFY GIFTCARDS APPLIED ==========
                                                    account.status = "Verifying giftcards..."
                                                    self.refresh_table()
                                                    
                                                    expected_gift_count = 1 if not gift2 else 2
                                                    verify_success, actual_count = self.verify_giftcards_applied(driver, expected_gift_count)
                                                    
                                                    if not verify_success:
                                                        print(f"[ERROR] Giftcard verification FAILED! Expected {expected_gift_count}, got {actual_count}")
                                                        print(f"[ERROR] This usually means SPAM or proxy issue!")
                                                        
                                                        # Restore balances
                                                        print("[INFO] Restoring giftcard balances...")
                                                        self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                                        
                                                        # Set status
                                                        account.status = f"❌ Gift apply failed ({actual_count}/{expected_gift_count}) - SPAM?"
                                                        self.save_accounts()
                                                        self.refresh_table()
                                                        
                                                        # Stop profile
                                                        if account.id:
                                                            self.gpm_api.stop_profile(account.id)
                                                            print("[INFO] Closed profile due to giftcard verification failure")
                                                        
                                                        return None
                                                    
                                                    print(f"[SUCCESS] Giftcard verification PASSED! {actual_count}/{expected_gift_count} gifts applied")
                                                    # ========== END VERIFY GIFTCARDS APPLIED ==========
                                                    
                                                    # ========== V1.7.2: CHECK GIFT CARD REDEEMED & PLACE ORDER ==========
                                                    try:
                                                        # Wait for page update
                                                        time.sleep(2)
                                                        
                                                        # Check Gift Card Redeemed
                                                        account.status = "Checking gift balance..."
                                                        self.refresh_table()
                                                        
                                                        is_sufficient, redeemed, subtotal = self.check_gift_card_redeemed(driver)
                                                        
                                                        if is_sufficient:
                                                            print(f"[SUCCESS] Gift Card Redeemed (${redeemed}) >= Subtotal (${subtotal})")
                                                            
                                                            # Click Place Order
                                                            account.status = "Placing order..."
                                                            self.refresh_table()
                                                            
                                                            place_order_success = self.click_place_order(driver)
                                                            
                                                            if place_order_success:
                                                                # Wait for response
                                                                time.sleep(3)
                                                                
                                                                # Check Verification popup
                                                                if self.check_verification_popup(driver):
                                                                    print("[WARNING] Verification Required!")
                                                                    
                                                                    # ✅ V1.7.2: Restore balances khi Verification
                                                                    print("[INFO] Restoring giftcard balances due to Verification...")
                                                                    self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                                                    
                                                                    account.status = "⚠️ Verification"
                                                                    self.refresh_table()
                                                                    
                                                                    # Close profile
                                                                    if account.id:
                                                                        self.gpm_api.stop_profile(account.id)
                                                                        print("[INFO] Closed profile due to Verification")
                                                                    
                                                                    return None
                                                                else:
                                                                    print("[SUCCESS] Order placed successfully!")
                                                                    account.status = "✅ Order Placed"
                                                                    self.refresh_table()
                                                                    
                                                                    # ✅ V1.7.4: Extract Order ID và Total $
                                                                    try:
                                                                        order_id, order_total = self.extract_order_info(driver)
                                                                        
                                                                        if order_id:
                                                                            account.order_id = order_id
                                                                            print(f"[INFO] Set Order ID: {order_id}")
                                                                        
                                                                        if order_total:
                                                                            account.order_total = order_total
                                                                            print(f"[INFO] Set Order Total: {order_total}")
                                                                        
                                                                        # ✅ V1.7.3: Set status Order success
                                                                        account.status = "Order success"
                                                                        
                                                                        # Save và refresh
                                                                        self.save_accounts()
                                                                        self.refresh_table()
                                                                        
                                                                        # ✅ V1.7.3: Close profile
                                                                        if account.id:
                                                                            self.gpm_api.stop_profile(account.id)
                                                                            print("[INFO] Profile closed after order success")
                                                                        
                                                                    except Exception as extract_error:
                                                                        print(f"[WARNING] Failed to extract order info: {extract_error}")
                                                            else:
                                                                print("[ERROR] Failed to click Place Order")
                                                                account.status = "❌ Place Order failed"
                                                                self.refresh_table()
                                                        else:
                                                            print(f"[WARNING] Gift Card Redeemed (${redeemed}) < Subtotal (${subtotal})")
                                                            account.status = f"⚠️ Gift insufficient (${redeemed}/${subtotal})"
                                                            self.refresh_table()
                                                    
                                                    except Exception as place_order_error:
                                                        print(f"[ERROR] Place order process failed: {place_order_error}")
                                                        account.status = "❌ Place order error"
                                                        self.refresh_table()
                                                    # ========== END CHECK GIFT & PLACE ORDER ==========
                                                    
                                                else:
                                                    print("[WARNING] Could not get order total, skipping giftcard")
                                                    account.status = "⚠️ No total found"
                                                    self.refresh_table()
                                                
                                            except Exception as giftcard_error:
                                                print(f"[ERROR] Giftcard process failed: {giftcard_error}")
                                                account.status = "❌ Giftcard error"
                                                self.refresh_table()
                                                
                                                # Restore balances nếu đã chọn gift
                                                if gift1 and backup_balances:
                                                    self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                            # ========== END GIFTCARD LOGIC ==========
                                            
                                        except Exception as shipping_error:
                                            print(f"[ERROR] Failed to fill shipping address: {shipping_error}")
                                            account.status = "Shipping address failed"
                                            self.refresh_table()
                                    else:
                                        print(f"[INFO] No warehouse assigned (account or dropdown), skipping shipping address")
                                        account.status = "No warehouse"
                                        self.refresh_table()
                                else:
                                    print(f"[WARNING] No visible checkout button found")
                                    account.status = "No checkout button"
                            except Exception as checkout_error:
                                print(f"[ERROR] Failed to click checkout: {checkout_error}")
                                account.status = "Checkout failed"
                        else:
                            print(f"[WARNING] added_count is 0, not navigating to basket")
                            account.status = "❌ No items added"
                            if out_of_stock_count > 0:
                                account.status += f" (All OOS)"
                        
                    except Exception as login_check_error:
                        # ✅ V1.5.4: RETRY - Open new tab TopCashback Sephora
                        print(f"[INFO] Login check failed, retrying with new tab...")
                        account.status = "Retry: Opening TopCashback..."
                        self.refresh_table()
                        
                        try:
                            # Determine TopCashback Sephora URL based on region
                            if region == "USA":
                                tcb_sephora_url = "https://www.topcashback.com/sephora/"
                            else:  # CAN
                                tcb_sephora_url = "https://www.topcashback.com/sephora-canada/"
                            
                            print(f"[INFO] Opening new tab: {tcb_sephora_url}")
                            
                            # Open new tab với JavaScript
                            driver.execute_script(f"window.open('{tcb_sephora_url}', '_blank');")
                            time.sleep(2)
                            
                            # Switch to new tab
                            driver.switch_to.window(driver.window_handles[-1])
                            time.sleep(3)
                            
                            # Click "Get Cash Back" button
                            account.status = f"Clicking Get Cash Back ({region})..."
                            self.refresh_table()
                            
                            cashback_btn = WebDriverWait(driver, 15).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "a#cashback-button"))
                            )
                            cashback_btn.click()
                            
                            # Wait for Sephora to load
                            account.status = "Loading Sephora..."
                            self.refresh_table()
                            time.sleep(8)
                            
                            # Switch to Sephora tab if opened in new window
                            if len(driver.window_handles) > 1:
                                driver.switch_to.window(driver.window_handles[-1])
                            
                            time.sleep(2)
                            
                            # ✅ V1.5.6: Close popup nếu có (retry)
                            account.status = "Closing popup (retry)..."
                            self.refresh_table()
                            
                            popup_closed = False
                            for attempt in range(3):  # ✅ Tăng từ 2 lên 3 lần retry
                                try:
                                    close_btn = WebDriverWait(driver, 10).until(  # ✅ Tăng từ 8s lên 10s
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Close modal']"))
                                    )
                                    close_btn.click()
                                    time.sleep(2)  # ✅ Tăng từ 1s lên 2s
                                    print(f"[INFO] Popup closed (retry attempt {attempt + 1})")
                                    popup_closed = True
                                    
                                    # Check nếu popup vẫn còn
                                    try:
                                        driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close modal']")
                                        print("[INFO] Popup still exists, trying again...")
                                        continue  # ✅ FIX: continue thay vì return None để retry
                                    except:
                                        print("[INFO] Popup confirmed closed (retry)")
                                        break
                                except:
                                    if attempt == 0:
                                        print("[INFO] No popup found on first attempt (retry)")
                                    else:
                                        print("[INFO] No popup on retry (retry)")
                                    break
                            
                            print(f"[INFO] Retry successful, continuing to add items...")
                            
                            # ✅ V1.5.8: CLEAR BASKET trước khi ADD TO CART (retry)
                            account.status = "Opening basket to clear old items (retry)..."
                            self.refresh_table()
                            print(f"[INFO] Navigating to basket to clear old items (retry)...")
                            
                            driver.get("https://www.sephora.com/basket")
                            time.sleep(3)
                            
                            # ✅ V1.5.9: Check login khi vào basket (retry)
                            account.status = "Checking login status in basket (retry)..."
                            self.refresh_table()
                            
                            try:
                                # Check xem đã login chưa
                                login_check = driver.find_element(By.XPATH, "//button[@id='account_drop_trigger']/span/span/strong")
                                print(f"[INFO] Already logged in, basket ready (retry)")
                            except:
                                # Chưa login → Login lại
                                print(f"[WARNING] Not logged in basket, retrying login (retry)...")
                                account.status = "Retry login (basket not logged in - retry)..."
                                self.refresh_table()
                                
                                # Click Sign In lần 1
                                signin_span = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, "span[data-at='sign_in_header']"))
                                )
                                signin_span.click()
                                time.sleep(1)
                                
                                # Click Sign In lần 2
                                signin_span.click()
                                time.sleep(2)
                                
                                # Enter email
                                email_input = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.ID, "signin_username"))
                                )
                                email_input.click()
                                email_input.clear()
                                time.sleep(0.5)
                                email_input.send_keys(user_email)
                                time.sleep(1)
                                
                                # Enter password
                                password_input = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.ID, "signin_password"))
                                )
                                password_input.click()
                                password_input.clear()
                                time.sleep(0.5)
                                password_input.send_keys(user_password)
                                time.sleep(1)
                                
                                # Click Sign In
                                signin_submit = driver.find_element(By.CSS_SELECTOR, "button[data-at='sign_in_button']")
                                signin_submit.click()
                                time.sleep(3)
                                
                                # Check login error
                                basket_retry_has_error = False
                                try:
                                    basket_retry_error = WebDriverWait(driver, 7).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-at='sign_in_error']"))
                                    )
                                    error_text = basket_retry_error.text.strip()
                                    print(f"[ERROR] Basket retry login error (retry): {error_text}")
                                    basket_retry_has_error = True
                                    
                                    if "Oops!" in error_text or "Something went wrong" in error_text:
                                        account.status = "SPAM (basket retry - retry)"
                                        self.save_accounts()
                                        self.refresh_table()
                                        if account.id:
                                            self.gpm_api.stop_profile(account.id)
                                        # CRITICAL: Return để dừng xử lý account này
                                        return None
                                    elif "error with your email" in error_text or "password" in error_text.lower():
                                        account.status = "Sai pass (basket retry - retry)"
                                        self.save_accounts()
                                        self.refresh_table()
                                        if account.id:
                                            self.gpm_api.stop_profile(account.id)
                                        return None
                                    else:
                                        account.status = f"Error: {error_text[:30]}"
                                        self.save_accounts()
                                        self.refresh_table()
                                        if account.id:
                                            self.gpm_api.stop_profile(account.id)
                                        return None
                                except:
                                    basket_retry_has_error = False
                                
                                # Check login success
                                if not basket_retry_has_error:
                                    try:
                                        basket_retry_success = WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located((By.XPATH, "//button[@id='account_drop_trigger']//strong"))
                                        )
                                        print(f"[SUCCESS] Basket retry login successful (retry)!")
                                        account.status = "✅ Logged In (basket retry - retry)"
                                        self.refresh_table()
                                        
                                        # Reload basket để items hiện ra
                                        print(f"[INFO] Reloading basket after login (retry)...")
                                        driver.get("https://www.sephora.com/basket")
                                        time.sleep(3)
                                        
                                    except Exception as basket_check_error:
                                        print(f"[ERROR] Basket retry login check failed (retry): {basket_check_error}")
                                        account.status = "Login failed (basket retry - retry)"
                            
                            # SAU KHI ĐÃ LOGIN → Xóa items cũ trong basket
                            account.status = "Clearing old items (retry)..."
                            self.refresh_table()
                            
                            # Loop để xóa tất cả items cũ trong basket
                            removed_count = 0
                            max_attempts = 20  # Giới hạn để tránh infinite loop
                            attempt = 0
                            
                            while attempt < max_attempts:
                                try:
                                    # Tìm tất cả nút remove
                                    buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-at="bsk_sku_remove"]')
                                    # Filter chỉ lấy visible buttons
                                    visible_buttons = [b for b in buttons if b.is_displayed()]
                                    
                                    if len(visible_buttons) == 0:
                                        print(f"[INFO] Basket cleared (retry)! Removed {removed_count} old item(s)")
                                        break
                                    
                                    # Click button đầu tiên
                                    visible_buttons[0].click()
                                    removed_count += 1
                                    print(f"[INFO] Removed item {removed_count} (retry)")
                                    time.sleep(2)
                                    
                                    # ✅ V1.6.0: Check popup warning "Promo/Reward Code Warning" (retry)
                                    try:
                                        # Tìm nút OK trong popup warning
                                        popup_ok_btn = WebDriverWait(driver, 3).until(
                                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.css-1tjizbm[data-comp="BaseComponent "]'))
                                        )
                                        popup_ok_btn.click()
                                        print(f"[INFO] Closed promo/reward warning popup (retry)")
                                        time.sleep(1)
                                    except:
                                        # Không có popup → OK, tiếp tục
                                        pass
                                    
                                    attempt += 1
                                    
                                except Exception as clear_error:
                                    print(f"[WARNING] Error clearing basket (retry): {clear_error}")
                                    break
                            
                            if removed_count > 0:
                                print(f"[SUCCESS] Basket cleared (retry): {removed_count} old item(s) removed")
                            else:
                                print(f"[INFO] Basket was already empty (retry)")
                            
                            account.status = "Basket cleared, adding new items (retry)..."
                            self.refresh_table()
                            time.sleep(1)
                            
                            # ✅ V1.5.5: ADD TO CART WORKFLOW (retry) - Lấy từ UI
                            # Get items và quantities TRỰC TIẾP từ UI
                            items = [
                                (self.item1_entry.get().strip(), self.qty1_entry.get().strip()),
                                (self.item2_entry.get().strip(), self.qty2_entry.get().strip()),
                                (self.item3_entry.get().strip(), self.qty3_entry.get().strip())
                            ]
                            
                            print(f"[DEBUG] Items from UI (retry): {items}")
                            
                            added_count = 0
                            out_of_stock_count = 0
                            
                            for idx, (item_url, qty) in enumerate(items, 1):
                                # Skip nếu item rỗng
                                if not item_url or not item_url.strip():
                                    print(f"[INFO] Item {idx} empty, skipping...")
                                    continue  # ✅ FIX: continue thay vì return None
                                
                                # ✅ V1.7.2: Default qty = 1 nếu trống
                                if not qty or not qty.strip():
                                    qty = "1"
                                    print(f"[INFO] Item {idx} qty empty, defaulting to 1")
                                
                                try:
                                    # Navigate to product
                                    account.status = f"Loading Item {idx}..."
                                    self.refresh_table()
                                    print(f"[INFO] Opening Item {idx}: {item_url[:50]}...")
                                    
                                    driver.get(item_url)
                                    time.sleep(3)
                                    
                                    # Check out of stock
                                    account.status = f"Checking stock Item {idx}..."
                                    self.refresh_table()
                                    
                                    try:
                                        out_of_stock_btn = driver.find_element(By.CSS_SELECTOR, "button[data-at='out_of_stock_btn']")
                                        print(f"[WARNING] Item {idx} is OUT OF STOCK (retry)")
                                        
                                        # ✅ V1.9.2: Set status và đóng profile ngay
                                        account.status = f"Item {idx} out of stock"
                                        self.refresh_table()
                                        self.save_accounts()
                                        
                                        # Đóng profile
                                        if account.id:
                                            self.gpm_api.stop_profile(account.id)
                                            print(f"[INFO] Profile closed due to Item {idx} out of stock (retry)")
                                        
                                        return None  # Dừng ngay
                                    except:
                                        print(f"[INFO] Item {idx} is in stock")
                                    
                                    # ✅ V1.5.5: SKIP select quantity nếu qty = 1
                                    if qty != "1":
                                        # Select quantity
                                        account.status = f"Selecting qty {qty} for Item {idx}..."
                                        self.refresh_table()
                                        
                                        try:
                                            qty_select = WebDriverWait(driver, 10).until(
                                                EC.presence_of_element_located((By.CSS_SELECTOR, "select[data-at='sku_qty']"))
                                            )
                                            
                                            # Select quantity bằng Select class của Selenium
                                            from selenium.webdriver.support.ui import Select
                                            select = Select(qty_select)
                                            select.select_by_value(qty)
                                            print(f"[INFO] Selected quantity: {qty}")
                                            time.sleep(1)
                                            
                                        except Exception as qty_error:
                                            print(f"[WARNING] Cannot select quantity for Item {idx}: {qty_error}")
                                            # Tiếp tục với quantity mặc định
                                    else:
                                        print(f"[INFO] Quantity is 1, skipping select...")
                                    
                                    # Click Add to Basket
                                    account.status = f"Adding Item {idx} to cart..."
                                    self.refresh_table()
                                    
                                    add_to_cart_btn = WebDriverWait(driver, 10).until(
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-at='add_to_basket_btn']"))
                                    )
                                    add_to_cart_btn.click()
                                    print(f"[SUCCESS] Added Item {idx} to cart!")
                                    added_count += 1
                                    time.sleep(2)
                                    
                                except Exception as item_error:
                                    print(f"[ERROR] Failed to add Item {idx} (retry): {item_error}")
                                    
                                    # ✅ V1.9.3: Set status và đóng profile khi add to basket error
                                    account.status = "Add to Basket Error"
                                    self.refresh_table()
                                    self.save_accounts()
                                    
                                    # Đóng profile
                                    if account.id:
                                        self.gpm_api.stop_profile(account.id)
                                        print(f"[INFO] Profile closed due to Add to Basket Error (retry)")
                                    
                                    return None  # Dừng ngay
                            
                            # Navigate to basket
                            print(f"[DEBUG] Loop finished (retry). added_count={added_count}, out_of_stock_count={out_of_stock_count}")
                            
                            if added_count > 0:
                                account.status = f"Opening basket ({added_count} items)..."
                                self.refresh_table()
                                print(f"[INFO] Opening basket with {added_count} item(s)...")
                                
                                driver.get("https://www.sephora.com/basket")
                                time.sleep(3)
                                
                                # ✅ V1.9.4: Áp dụng Coupon nếu có (retry)
                                coupon_code = self.coupon_entry.get().strip()
                                if coupon_code:
                                    try:
                                        account.status = "Checking login (retry)..."
                                        self.refresh_table()
                                        
                                        # ✅ Step 1: Check đăng nhập trước
                                        try:
                                            login_check = driver.find_element(By.XPATH, "//button[@id='account_drop_trigger']//strong")
                                            print(f"[INFO] Đã đăng nhập (retry): {login_check.text}")
                                        except:
                                            print(f"[WARNING] Chưa đăng nhập (retry), đang đăng nhập lại...")
                                            account.status = "Logging in (retry)..."
                                            self.refresh_table()
                                            
                                            # RETRY LOGIN
                                            signin_span = WebDriverWait(driver, 10).until(
                                                EC.element_to_be_clickable((By.CSS_SELECTOR, "span[data-at='sign_in_header']"))
                                            )
                                            signin_span.click()
                                            time.sleep(1)
                                            signin_span.click()
                                            time.sleep(2)
                                            
                                            email_input = WebDriverWait(driver, 10).until(
                                                EC.presence_of_element_located((By.ID, "signin_username"))
                                            )
                                            email_input.click()
                                            email_input.clear()
                                            time.sleep(0.5)
                                            email_input.send_keys(user_email)
                                            time.sleep(1)
                                            
                                            password_input = WebDriverWait(driver, 10).until(
                                                EC.presence_of_element_located((By.ID, "signin_password"))
                                            )
                                            password_input.click()
                                            password_input.clear()
                                            time.sleep(0.5)
                                            password_input.send_keys(user_password)
                                            time.sleep(1)
                                            
                                            signin_submit = driver.find_element(By.CSS_SELECTOR, "button[data-at='sign_in_button']")
                                            signin_submit.click()
                                            time.sleep(3)
                                            
                                            # Check login thành công
                                            try:
                                                login_check = driver.find_element(By.XPATH, "//button[@id='account_drop_trigger']//strong")
                                                print(f"[SUCCESS] Đăng nhập thành công (retry)!")
                                            except:
                                                print(f"[ERROR] Đăng nhập thất bại (retry)")
                                        
                                        # ✅ Step 2: Apply coupon
                                        account.status = "Applying coupon (retry)..."
                                        self.refresh_table()
                                        print(f"[INFO] Applying coupon (retry): {coupon_code}")
                                        
                                        promo_input = WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located((By.ID, "promoInput"))
                                        )
                                        promo_input.clear()
                                        promo_input.send_keys(coupon_code)
                                        time.sleep(1)

                                        # ✅ V1.10.7: Chỉ click Apply coupon (type="submit"), tránh nhầm với Apply 500 points (type="button")
                                        apply_btn = driver.find_element(By.CSS_SELECTOR, "button[data-at='apply_btn'][type='submit']")
                                        apply_btn.click()
                                        time.sleep(3)

                                        # ✅ Step 3: Check errors
                                        try:
                                            error_msg = driver.find_element(By.CSS_SELECTOR, "p.css-oxeibp[role='alert']")
                                            error_text = error_msg.text.strip()
                                            print(f"[WARNING] Coupon error (retry): {error_text}")
                                            
                                            if "does not exist" in error_text:
                                                # Coupon invalid
                                                account.status = "Coupon invalid"
                                                self.refresh_table()
                                                self.save_accounts()
                                                
                                                if account.id:
                                                    self.gpm_api.stop_profile(account.id)
                                                    print(f"[INFO] Profile closed due to Coupon invalid (retry)")
                                                
                                                return None
                                            
                                            elif "expired or has run out of inventory" in error_text:
                                                # ✅ V1.9.5: Coupon hết hạn
                                                account.status = "Coupon hết hạn"
                                                self.refresh_table()
                                                self.save_accounts()
                                                
                                                if account.id:
                                                    self.gpm_api.stop_profile(account.id)
                                                    print(f"[INFO] Profile closed due to Coupon hết hạn (retry)")
                                                
                                                return None
                                            
                                            elif "exceeded the number of redemptions" in error_text:
                                                # ✅ V1.9.6: Acc đã dùng coupon
                                                account.status = "Acc đã dùng coupon"
                                                self.refresh_table()
                                                self.save_accounts()
                                                
                                                if account.id:
                                                    self.gpm_api.stop_profile(account.id)
                                                    print(f"[INFO] Profile closed due to Acc đã dùng coupon (retry)")
                                                
                                                return None
                                            
                                            elif "Must be logged into" in error_text or "Beauty Insider" in error_text:
                                                # Đã đăng nhập nhưng vẫn lỗi → Kiểm tra Coupon
                                                account.status = "Kiểm tra Coupon or login fail"
                                                self.refresh_table()
                                                self.save_accounts()
                                                
                                                if account.id:
                                                    self.gpm_api.stop_profile(account.id)
                                                    print(f"[INFO] Profile closed - Kiểm tra Coupon or login fail (retry)")
                                                
                                                return None
                                        except:
                                            # Không có error → Coupon OK
                                            pass
                                        
                                        # ✅ Step 4: Check popup chọn quà
                                        coupon_items = [
                                            self.coupon_item1_entry.get().strip(),
                                            self.coupon_item2_entry.get().strip(),
                                            self.coupon_item3_entry.get().strip(),
                                            self.coupon_item4_entry.get().strip()
                                        ]
                                        
                                        # Filter chỉ lấy items có giá trị
                                        coupon_items = [item for item in coupon_items if item]
                                        
                                        if coupon_items:
                                            # Có popup items
                                            print(f"[INFO] Coupon có popup (retry), chọn {len(coupon_items)} item(s)")
                                            account.status = f"Selecting {len(coupon_items)} promo items (retry)..."
                                            self.refresh_table()
                                            time.sleep(2)
                                            
                                            for item_name in coupon_items:
                                                try:
                                                    print(f"[INFO] Searching for promo item (retry): {item_name}...")
                                                    
                                                    # ✅ V1.9.7: Tìm theo brand hoặc product name
                                                    result = driver.execute_script("""
                                                        const searchText = arguments[0];
                                                        const items = document.querySelectorAll('[data-at="promo_item"]');
                                                        
                                                        for (let item of items) {
                                                            const brand = item.querySelector('[data-at="sku_item_brand"]')?.textContent || '';
                                                            const name = item.querySelector('[data-at="sku_item_name"]')?.textContent || '';
                                                            
                                                            if (brand.toLowerCase().includes(searchText.toLowerCase()) || 
                                                                name.toLowerCase().includes(searchText.toLowerCase())) {
                                                                const addBtn = item.querySelector('[data-at="promo_item_add_button"]');
                                                                if (addBtn) {
                                                                    addBtn.click();
                                                                    return true;
                                                                }
                                                            }
                                                        }
                                                        return false;
                                                    """, item_name)
                                                    
                                                    if result:
                                                        print(f"[SUCCESS] Clicked promo item (retry): {item_name}")
                                                    else:
                                                        # ✅ V1.9.8: Item không tìm thấy → Dừng ngay
                                                        print(f"[WARNING] Promo item not found (retry): {item_name}")
                                                        account.status = f"Hết {item_name}"
                                                        self.refresh_table()
                                                        self.save_accounts()
                                                        
                                                        if account.id:
                                                            self.gpm_api.stop_profile(account.id)
                                                            print(f"[INFO] Profile closed - Hết {item_name} (retry)")
                                                        
                                                        return None
                                                    
                                                    time.sleep(1.5)
                                                except Exception as item_err:
                                                    print(f"[WARNING] Failed to click promo item '{item_name}' (retry): {item_err}")
                                            
                                            # Click Done button
                                            try:
                                                done_btn = driver.find_element(By.CSS_SELECTOR, "button[data-at='done_button']")
                                                done_btn.click()
                                                print(f"[SUCCESS] Clicked Done button (retry)!")
                                                time.sleep(2)
                                                
                                                # ✅ V1.9.5: Check error sau Done
                                                try:
                                                    error_after_done = driver.find_element(By.CSS_SELECTOR, "p.css-oxeibp[role='alert']")
                                                    error_done_text = error_after_done.text.strip()
                                                    
                                                    if "expired or has run out of inventory" in error_done_text:
                                                        print(f"[WARNING] Item coupon hết hàng (retry): {error_done_text}")
                                                        account.status = "Item coupon hết hàng"
                                                        self.refresh_table()
                                                        self.save_accounts()
                                                        
                                                        if account.id:
                                                            self.gpm_api.stop_profile(account.id)
                                                            print(f"[INFO] Profile closed due to Item coupon hết hàng (retry)")
                                                        
                                                        return None
                                                except:
                                                    # Không có error → OK
                                                    print(f"[SUCCESS] Popup items applied successfully (retry)!")
                                                
                                            except Exception as done_err:
                                                print(f"[WARNING] Failed to click Done (retry): {done_err}")
                                        else:
                                            # Không có popup
                                            print(f"[SUCCESS] Coupon applied (retry - no popup)!")

                                    except Exception as coupon_error:
                                        print(f"[ERROR] Failed to apply coupon (retry): {coupon_error}")

                                # ✅ V1.10.7: Apply discount code (retry - Giảm 10$ hoặc 20$)
                                discount_code = None
                                if self.discount_10_var.get():
                                    discount_code = "cbr_10_500"
                                elif self.discount_20_var.get():
                                    discount_code = "cbr_20_1000"

                                if discount_code:
                                    try:
                                        account.status = f"Applying {discount_code} (retry)..."
                                        self.refresh_table()
                                        print(f"[INFO] Applying discount code (retry): {discount_code}")

                                        # Nhập code vào input coupon
                                        promo_input = WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located((By.ID, "promoInput"))
                                        )
                                        promo_input.clear()
                                        promo_input.send_keys(discount_code)
                                        time.sleep(1)

                                        # Click Apply button (type="submit")
                                        apply_btn = driver.find_element(By.CSS_SELECTOR, "button[data-at='apply_btn'][type='submit']")
                                        apply_btn.click()
                                        time.sleep(2)

                                        # ✅ V1.10.8: Kiểm tra lỗi "You do not have enough current points"
                                        try:
                                            error_msg = driver.find_element(By.CSS_SELECTOR, 'p.css-oxeibp[role="alert"][data-comp="InputMsg BaseComponent "]')
                                            error_text = error_msg.text

                                            if "You do not have enough current points" in error_text:
                                                # Xác định loại discount
                                                discount_type = "10$" if self.discount_10_var.get() else "20$"
                                                account.status = f"Không đủ points giảm {discount_type}"
                                                self.refresh_table()
                                                self.save_accounts()
                                                print(f"[ERROR] {account.status} (retry)")

                                                if account.id:
                                                    self.gpm_api.stop_profile(account.id)
                                                    print(f"[INFO] Profile closed - {account.status} (retry)")

                                                return None
                                        except:
                                            # Không có lỗi, tiếp tục
                                            pass

                                        print(f"[SUCCESS] Applied {discount_code} (retry)!")

                                    except Exception as discount_error:
                                        print(f"[WARNING] Failed to apply {discount_code} (retry): {discount_error}")

                                # ✅ V1.9.9: Chọn Sample nếu có (retry - theo tên)
                                sample1 = self.sample1_entry.get().strip()
                                sample2 = self.sample2_entry.get().strip()
                                
                                if sample1 or sample2:
                                    try:
                                        account.status = "Selecting samples (retry)..."
                                        self.refresh_table()
                                        print(f"[INFO] Selecting samples (retry): Sample1={sample1}, Sample2={sample2}")
                                        
                                        # Click button "Add up to 2 Free Samples"
                                        sample_btn = WebDriverWait(driver, 10).until(
                                            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-comp="FreeSamples BaseComponent "]'))
                                        )
                                        sample_btn.click()
                                        time.sleep(2)
                                        print(f"[INFO] Sample popup opened (retry)")
                                        
                                        # Chọn Sample 1
                                        if sample1:
                                            print(f"[INFO] Searching for Sample 1 (retry): {sample1}...")
                                            result = driver.execute_script("""
                                                const searchText = arguments[0];
                                                const items = document.querySelectorAll('[data-at="sample_item"]');
                                                
                                                for (let item of items) {
                                                    const name = item.querySelector('[data-at="sku_item_name"]')?.textContent || '';
                                                    
                                                    if (name.toLowerCase().includes(searchText.toLowerCase())) {
                                                        const addBtn = item.querySelector('[data-at="add_to_basket_btn"]');
                                                        if (addBtn) {
                                                            addBtn.click();
                                                            return true;
                                                        }
                                                    }
                                                }
                                                return false;
                                            """, sample1)
                                            
                                            if result:
                                                print(f"[SUCCESS] Selected Sample 1 (retry): {sample1}")
                                                time.sleep(7)
                                            else:
                                                # ✅ V1.9.9: Sample không tìm thấy → Dừng ngay
                                                print(f"[WARNING] Sample not found (retry): {sample1}")
                                                account.status = f"Hết {sample1}"
                                                self.refresh_table()
                                                self.save_accounts()
                                                
                                                if account.id:
                                                    self.gpm_api.stop_profile(account.id)
                                                    print(f"[INFO] Profile closed - Hết {sample1} (retry)")
                                                
                                                return None
                                        
                                        # Chọn Sample 2
                                        if sample2:
                                            print(f"[INFO] Searching for Sample 2 (retry): {sample2}...")
                                            result = driver.execute_script("""
                                                const searchText = arguments[0];
                                                const items = document.querySelectorAll('[data-at="sample_item"]');
                                                
                                                for (let item of items) {
                                                    const name = item.querySelector('[data-at="sku_item_name"]')?.textContent || '';
                                                    
                                                    if (name.toLowerCase().includes(searchText.toLowerCase())) {
                                                        const addBtn = item.querySelector('[data-at="add_to_basket_btn"]');
                                                        if (addBtn) {
                                                            addBtn.click();
                                                            return true;
                                                        }
                                                    }
                                                }
                                                return false;
                                            """, sample2)
                                            
                                            if result:
                                                print(f"[SUCCESS] Selected Sample 2 (retry): {sample2}")
                                                time.sleep(2)
                                            else:
                                                # ✅ V1.9.9: Sample không tìm thấy → Dừng ngay
                                                print(f"[WARNING] Sample not found (retry): {sample2}")
                                                account.status = f"Hết {sample2}"
                                                self.refresh_table()
                                                self.save_accounts()
                                                
                                                if account.id:
                                                    self.gpm_api.stop_profile(account.id)
                                                    print(f"[INFO] Profile closed - Hết {sample2} (retry)")
                                                
                                                return None
                                        
                                        # Click Done
                                        done_btn = driver.find_element(By.CSS_SELECTOR, "button.css-u1lgrz")
                                        done_btn.click()
                                        time.sleep(2)
                                        print(f"[SUCCESS] Samples selected (retry)!")
                                        
                                    except Exception as sample_error:
                                        print(f"[ERROR] Failed to select samples (retry): {sample_error}")

                                # ✅ V1.10.7: Chọn Point Rewards (retry - nếu có)
                                point_items = [
                                    self.point1_entry.get().strip(),
                                    self.point2_entry.get().strip(),
                                    self.point3_entry.get().strip(),
                                    self.point4_entry.get().strip(),
                                    self.point5_entry.get().strip()
                                ]
                                point_items = [p for p in point_items if p]  # Lọc bỏ empty

                                if point_items:
                                    try:
                                        account.status = "Selecting Point items (retry)..."
                                        self.refresh_table()
                                        print(f"[INFO] Selecting {len(point_items)} Point item(s) (retry): {point_items}")

                                        # Click "Apply Points for Bazaar Items" button
                                        point_btn = WebDriverWait(driver, 10).until(
                                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.css-bgk68u[data-comp="BaseComponent "]'))
                                        )
                                        point_btn.click()
                                        time.sleep(2)
                                        print(f"[INFO] Point popup opened (retry)")

                                        # Loop qua từng Point item
                                        for idx, point_name in enumerate(point_items, 1):
                                            print(f"[INFO] Searching for Point {idx} (retry): {point_name}...")

                                            # Tìm product theo tên trong popup
                                            result = driver.execute_script("""
                                                const searchText = arguments[0];
                                                const items = document.querySelectorAll('a[data-at="product_item_container"]');

                                                for (let item of items) {
                                                    const brandElem = item.querySelector('span[data-at="product_brand_label"]');
                                                    const nameElem = item.querySelector('span[data-at="product_name_label"]');
                                                    const brand = brandElem ? brandElem.textContent : '';
                                                    const name = nameElem ? nameElem.textContent : '';
                                                    const fullName = brand + ' ' + name;

                                                    if (fullName.toLowerCase().includes(searchText.toLowerCase())) {
                                                        const addBtn = item.querySelector('button[data-comp="AddToBasketButton BaseComponent "]');
                                                        if (addBtn) {
                                                            // Check if button is disabled
                                                            if (addBtn.hasAttribute('disabled')) {
                                                                return 'disabled';
                                                            }
                                                            addBtn.click();
                                                            return true;
                                                        }
                                                    }
                                                }
                                                return false;
                                            """, point_name)

                                            if result == 'disabled':
                                                print(f"[ERROR] Not enough points for (retry): {point_name}")
                                                account.status = "Không đủ points"
                                                self.refresh_table()
                                                self.save_accounts()

                                                if account.id:
                                                    self.gpm_api.stop_profile(account.id)
                                                    print(f"[INFO] Profile closed - Không đủ points (retry)")

                                                return None
                                            elif result:
                                                print(f"[SUCCESS] Clicked Add for Point {idx} (retry): {point_name}")
                                                time.sleep(2)

                                                # Click Confirm button
                                                try:
                                                    confirm_btn = WebDriverWait(driver, 5).until(
                                                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-at="change_method_modal_confirm_btn"]'))
                                                    )
                                                    confirm_btn.click()
                                                    print(f"[SUCCESS] Confirmed Point {idx} (retry)")
                                                    time.sleep(2)
                                                except Exception as confirm_error:
                                                    print(f"[WARNING] No confirm button for Point {idx} (retry): {confirm_error}")
                                            else:
                                                print(f"[WARNING] Point item not found (retry): {point_name}")

                                        # Click Done để đóng popup
                                        done_btn = driver.find_element(By.CSS_SELECTOR, "button.css-1ab2xd")
                                        done_btn.click()
                                        time.sleep(2)
                                        print(f"[SUCCESS] Point items selected (retry)!")

                                    except Exception as point_error:
                                        print(f"[ERROR] Failed to select Point items (retry): {point_error}")

                                account.status = f"✅ Added {added_count} items (Retry)"
                                if out_of_stock_count > 0:
                                    account.status += f" ({out_of_stock_count} OOS)"
                                
                                # ✅ V1.6.1: Click Checkout button (retry)
                                account.status = "Clicking Checkout (retry)..."
                                self.refresh_table()
                                print(f"[INFO] Clicking Checkout button (retry)...")
                                time.sleep(2)
                                
                                try:
                                    # Tìm tất cả checkout buttons
                                    checkout_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-at="basket_checkout_btn"]')
                                    # Filter chỉ lấy visible button
                                    visible_checkout = [btn for btn in checkout_buttons if btn.is_displayed()]
                                    
                                    if len(visible_checkout) > 0:
                                        visible_checkout[0].click()
                                        print(f"[SUCCESS] Clicked Checkout button (retry)")
                                        time.sleep(3)
                                        account.status = "In Checkout (retry)..."
                                        self.refresh_table()
                                        
                                        # ✅ V1.6.6: RETRY - Auto nhập shipping address
                                        selected_warehouse = None
                                        
                                        # Check account warehouse first
                                        if hasattr(account, 'warehouse_name') and account.warehouse_name:
                                            for wh in self.warehouses:
                                                if wh.name == account.warehouse_name:
                                                    selected_warehouse = wh
                                                    print(f"[INFO] (Retry) Using warehouse from account: {wh.name}")
                                                    break
                                        
                                        # Fallback to dropdown
                                        if not selected_warehouse and hasattr(self, 'warehouse_selected') and self.warehouse_selected:
                                            selected_warehouse = self.warehouse_selected
                                            print(f"[INFO] (Retry) Using warehouse from dropdown: {selected_warehouse.name}")
                                        
                                        if selected_warehouse:
                                            try:
                                                wh = selected_warehouse
                                                account.status = "Filling shipping (retry)..."
                                                self.refresh_table()
                                                print(f"[INFO] (Retry) Auto-filling shipping address: {wh.name}")
                                                
                                                time.sleep(2)
                                                
                                                # Check case 1 or 2
                                                has_change_button = False
                                                try:
                                                    change_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Change Deliver To"]')
                                                    has_change_button = True
                                                    print(f"[INFO] (Retry) Case 2: Đã có địa chỉ")
                                                except:
                                                    print(f"[INFO] (Retry) Case 1: Chưa có địa chỉ")
                                                
                                                # Case 2: Click Change -> Edit first address
                                                if has_change_button:
                                                    print(f"[INFO] (Retry) Clicking Change...")
                                                    change_btn.click()
                                                    time.sleep(2)
                                                    
                                                    # ✅ V1.7.2: Click Edit address (first one) instead of Add new
                                                    print(f"[INFO] (Retry) Clicking Edit address (first address)...")
                                                    try:
                                                        edit_addr_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Edit address"]')
                                                        if len(edit_addr_buttons) > 0:
                                                            edit_addr_buttons[0].click()
                                                            time.sleep(2)
                                                            print(f"[SUCCESS] (Retry) Clicked Edit address")
                                                        else:
                                                            # Fallback: Add new address if no edit button
                                                            print(f"[WARNING] (Retry) No Edit button found, adding new address...")
                                                            add_addr_btn = WebDriverWait(driver, 10).until(
                                                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-at="addAddress"]'))
                                                            )
                                                            add_addr_btn.click()
                                                            time.sleep(2)
                                                    except Exception as edit_error:
                                                        print(f"[ERROR] (Retry) Failed to click Edit address: {edit_error}")
                                                        # Fallback: Add new address
                                                        print(f"[INFO] (Retry) Falling back to Add shipping address...")
                                                        add_addr_btn = WebDriverWait(driver, 10).until(
                                                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-at="addAddress"]'))
                                                        )
                                                        add_addr_btn.click()
                                                        time.sleep(2)
                                                
                                                # Fill form
                                                print(f"[INFO] (Retry) Filling First Name: {wh.first_name}")
                                                first_name_input = WebDriverWait(driver, 10).until(
                                                    EC.presence_of_element_located((By.ID, "firstName"))
                                                )
                                                # ✅ V1.7.2: Clear tốt hơn - select all + delete
                                                first_name_input.click()
                                                time.sleep(0.2)
                                                first_name_input.send_keys(Keys.CONTROL + "a")
                                                time.sleep(0.1)
                                                first_name_input.send_keys(Keys.DELETE)
                                                time.sleep(0.2)
                                                first_name_input.send_keys(wh.first_name)
                                                time.sleep(0.5)
                                                
                                                print(f"[INFO] (Retry) Filling Last Name: {wh.last_name}")
                                                last_name_input = driver.find_element(By.ID, "lastName")
                                                last_name_input.click()
                                                time.sleep(0.2)
                                                last_name_input.send_keys(Keys.CONTROL + "a")
                                                time.sleep(0.1)
                                                last_name_input.send_keys(Keys.DELETE)
                                                time.sleep(0.2)
                                                last_name_input.send_keys(wh.last_name)
                                                time.sleep(0.5)
                                                
                                                print(f"[INFO] (Retry) Filling Phone: {wh.phone}")
                                                phone_input = driver.find_element(By.ID, "phone")
                                                phone_input.click()
                                                time.sleep(0.2)
                                                phone_input.send_keys(Keys.CONTROL + "a")
                                                time.sleep(0.1)
                                                phone_input.send_keys(Keys.DELETE)
                                                time.sleep(0.2)
                                                phone_input.send_keys(wh.phone)
                                                time.sleep(0.5)
                                                
                                                print(f"[INFO] (Retry) Filling Address: {wh.address}")
                                                address_input = driver.find_element(By.ID, "avs_input")
                                                address_input.click()
                                                time.sleep(0.2)
                                                address_input.send_keys(Keys.CONTROL + "a")
                                                time.sleep(0.1)
                                                address_input.send_keys(Keys.DELETE)
                                                time.sleep(0.2)
                                                address_input.send_keys(wh.address)
                                                time.sleep(0.5)
                                                
                                                print(f"[INFO] (Retry) Filling Zipcode: {wh.zip}")
                                                zip_input = driver.find_element(By.ID, "postalCode")
                                                zip_input.click()
                                                time.sleep(0.2)
                                                zip_input.send_keys(Keys.CONTROL + "a")
                                                time.sleep(0.1)
                                                zip_input.send_keys(Keys.DELETE)
                                                time.sleep(0.2)
                                                zip_input.send_keys(wh.zip)
                                                time.sleep(2)
                                                
                                                # Check checkbox if Case 2
                                                if has_change_button:
                                                    try:
                                                        print(f"[INFO] (Retry) Checking 'Set as default'...")
                                                        checkbox_checked = False
                                                        
                                                        try:
                                                            default_checkbox = driver.find_element(By.CSS_SELECTOR, 'input[name="is_default"]')
                                                            if not default_checkbox.is_selected():
                                                                try:
                                                                    default_checkbox.click()
                                                                    checkbox_checked = True
                                                                    print(f"[SUCCESS] (Retry) Clicked checkbox")
                                                                except:
                                                                    driver.execute_script("arguments[0].click();", default_checkbox)
                                                                    checkbox_checked = True
                                                                    print(f"[SUCCESS] (Retry) Clicked via JS")
                                                            else:
                                                                # ✅ V1.7.2: Đã tích rồi
                                                                checkbox_checked = True
                                                                print(f"[INFO] (Retry) Checkbox already checked")
                                                        except:
                                                            pass
                                                        
                                                        if not checkbox_checked:
                                                            try:
                                                                # ✅ V1.7.2: Check xem đã selected chưa trước khi click label
                                                                default_checkbox = driver.find_element(By.CSS_SELECTOR, 'input[name="is_default"]')
                                                                
                                                                if not default_checkbox.is_selected():
                                                                    # Chưa tích, click label
                                                                    label = driver.find_element(By.CSS_SELECTOR, 'label[data-comp*="Checkbox"]')
                                                                    label.click()
                                                                    checkbox_checked = True
                                                                    print(f"[SUCCESS] (Retry) Clicked label")
                                                                else:
                                                                    # Đã tích rồi
                                                                    checkbox_checked = True
                                                                    print(f"[INFO] (Retry) Checkbox already selected")
                                                            except:
                                                                pass
                                                        
                                                        time.sleep(0.5)
                                                    except Exception as cb_error:
                                                        print(f"[WARNING] (Retry) Checkbox error: {cb_error}")
                                                
                                                # Click Save & Continue
                                                print(f"[INFO] (Retry) Clicking Save & Continue...")
                                                save_btn = WebDriverWait(driver, 10).until(
                                                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-at="save_continue_btn"]'))
                                                )
                                                save_btn.click()
                                                time.sleep(3)
                                                
                                                print(f"[SUCCESS] (Retry) Shipping address saved!")
                                                account.status = "✅ Shipping saved (Retry)"
                                                self.refresh_table()
                                                
                                                # ========== V1.7.2: GIFTCARD LOGIC (RETRY FLOW) ==========
                                                gift1 = None
                                                gift2 = None
                                                backup_balances = None
                                                
                                                try:
                                                    # Wait for page to load after saving address
                                                    time.sleep(3)
                                                    
                                                    # Step 1: Get order total
                                                    account.status = "Getting order total (retry)..."
                                                    self.refresh_table()
                                                    print("[INFO] (Retry) Getting order total...")
                                                    
                                                    order_total = self.get_order_total_from_page(driver)
                                                    
                                                    if order_total:
                                                        # ✅ V1.8.5: Convert to float for comparison
                                                        try:
                                                            order_total = float(order_total)
                                                        except:
                                                            print(f"[ERROR] (Retry) Invalid order total: {order_total}")
                                                            account.status = "❌ Invalid order total (Retry)"
                                                            self.refresh_table()
                                                            self.gpm_api.stop_profile(account.id)
                                                        
                                                        print(f"[INFO] (Retry) Order total: ${order_total}")
                                                        
                                                        # ✅ V1.9.1: Filter gifts có balance > 0 trước khi check (retry)
                                                        available_gifts = [gc for gc in self.giftcards 
                                                                          if self.normalize_balance(gc.balance) >= 0.01]
                                                        
                                                        if len(available_gifts) == 0:
                                                            print(f"[ERROR] (Retry) No giftcards available!")
                                                            account.status = "Hết tiền"
                                                            self.refresh_table()
                                                            self.gpm_api.stop_profile(account.id)
                                                            # Skip phần còn lại, nhưng ở retry flow không dùng continue
                                                        
                                                        # ✅ Check 2 gift cards LỚN NHẤT có đủ không (vì chỉ dùng max 2 gift)
                                                        sorted_gifts = sorted(available_gifts, key=lambda x: self.normalize_balance(x.balance), reverse=True)
                                                        
                                                        # Lấy 2 gift lớn nhất
                                                        if len(sorted_gifts) > 0:
                                                            max_balance = self.normalize_balance(sorted_gifts[0].balance)
                                                            if len(sorted_gifts) >= 2:
                                                                max_balance += self.normalize_balance(sorted_gifts[1].balance)
                                                            
                                                            print(f"[INFO] (Retry) Max possible balance (top 2 gifts): ${max_balance}")
                                                            
                                                            if max_balance < order_total:
                                                                print(f"[ERROR] (Retry) Not enough! Max 2 gifts: ${max_balance} < Order: ${order_total}")
                                                                account.status = "Thiếu $"
                                                                self.refresh_table()
                                                                self.gpm_api.stop_profile(account.id)
                                                            else:
                                                                # Step 2: Select giftcards (TRỪ BALANCE NGAY)
                                                                account.status = "Selecting giftcards (retry)..."
                                                                self.refresh_table()
                                                        
                                                                gift1, gift2, backup_balances = self.select_giftcards_for_order(account, order_total)
                                                        
                                                                if gift1 is None:
                                                                    print("[ERROR] (Retry) Not enough giftcards!")
                                                                    account.status = "❌ Not enough giftcards (Retry)"
                                                                    self.refresh_table()
                                                                else:
                                                                    # Step 3: Gán giftcard vào account (balance đã trừ)
                                                                    account.status = "Assigning giftcards (retry)..."
                                                                    self.refresh_table()
                                                                    
                                                                    success = self.assign_giftcards_to_account(account, gift1, gift2, backup_balances)
                                                                    
                                                                    if not success:
                                                                        print("[ERROR] (Retry) Failed to assign giftcards")
                                                                        account.status = "❌ Assign gift failed (Retry)"
                                                                        self.refresh_table()
                                                                        
                                                                        # Restore balances
                                                                        self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                                                    else:
                                                                        # ✅ Step 4: Apply giftcards vào form
                                                                        account.status = "Applying giftcards (retry)..."
                                                                        self.refresh_table()
                                                                        
                                                                        apply_success = self.apply_giftcards_to_checkout(driver, gift1, gift2)
                                                                        
                                                                        if not apply_success:
                                                                            print("[ERROR] (Retry) Failed to apply giftcards to checkout")
                                                                            account.status = "❌ Apply gift failed (Retry)"
                                                                            self.refresh_table()
                                                                            
                                                                            # Restore balances
                                                                            self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                                                        else:
                                                                            print(f"[SUCCESS] (Retry) Giftcards applied successfully!")
                                                                            account.status = "✅ Gifts applied (Retry)"
                                                                            self.refresh_table()
                                                                            
                                                                            # Refresh table để hiển thị Gift 1, Gift 2
                                                                            time.sleep(1)
                                                                            self.refresh_table()
                                                                            
                                                                            # ========== V1.8.9: VERIFY GIFTCARDS APPLIED (RETRY) ==========
                                                                            account.status = "Verifying giftcards (retry)..."
                                                                            self.refresh_table()
                                                                            
                                                                            expected_gift_count = 1 if not gift2 else 2
                                                                            verify_success, actual_count = self.verify_giftcards_applied(driver, expected_gift_count)
                                                                            
                                                                            if not verify_success:
                                                                                print(f"[ERROR] (Retry) Giftcard verification FAILED! Expected {expected_gift_count}, got {actual_count}")
                                                                                print(f"[ERROR] (Retry) This usually means SPAM or proxy issue!")
                                                                                
                                                                                # Restore balances
                                                                                print("[INFO] (Retry) Restoring giftcard balances...")
                                                                                self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                                                                
                                                                                # Set status
                                                                                account.status = f"❌ Gift apply failed ({actual_count}/{expected_gift_count}) - SPAM? (Retry)"
                                                                                self.save_accounts()
                                                                                self.refresh_table()
                                                                                
                                                                                # Stop profile
                                                                                if account.id:
                                                                                    self.gpm_api.stop_profile(account.id)
                                                                                    print("[INFO] (Retry) Closed profile due to giftcard verification failure")
                                                                            else:
                                                                                print(f"[SUCCESS] (Retry) Giftcard verification PASSED! {actual_count}/{expected_gift_count} gifts applied")
                                                                            # ========== END VERIFY GIFTCARDS APPLIED (RETRY) ==========
                                                                            
                                                                            # ========== V1.7.2: CHECK GIFT & PLACE ORDER (RETRY) ==========
                                                                            try:
                                                                                # Wait for page update
                                                                                time.sleep(2)
                                                                                
                                                                                # Check Gift Card Redeemed
                                                                                account.status = "Checking gift balance (retry)..."
                                                                                self.refresh_table()
                                                                                
                                                                                is_sufficient, redeemed, subtotal = self.check_gift_card_redeemed(driver)
                                                                                
                                                                                if is_sufficient:
                                                                                    print(f"[SUCCESS] (Retry) Gift Card Redeemed (${redeemed}) >= Subtotal (${subtotal})")
                                                                                    
                                                                                    # Click Place Order
                                                                                    account.status = "Placing order (retry)..."
                                                                                    self.refresh_table()
                                                                                    
                                                                                    place_order_success = self.click_place_order(driver)
                                                                                    
                                                                                    if place_order_success:
                                                                                        # Wait for response
                                                                                        time.sleep(3)
                                                                                        
                                                                                        # Check Verification popup
                                                                                        if self.check_verification_popup(driver):
                                                                                            print("[WARNING] (Retry) Verification Required!")
                                                                                            
                                                                                            # ✅ V1.7.2: Restore balances khi Verification
                                                                                            print("[INFO] (Retry) Restoring giftcard balances due to Verification...")
                                                                                            self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                                                                            
                                                                                            account.status = "⚠️ Verification (Retry)"
                                                                                            self.refresh_table()
                                                                                            
                                                                                            # ✅ Close profile
                                                                                            if account.id:
                                                                                                self.gpm_api.stop_profile(account.id)
                                                                                                print("[INFO] (Retry) Closed profile due to Verification")
                                                                                            
                                                                                        else:
                                                                                            print("[SUCCESS] (Retry) Order placed successfully!")
                                                                                            account.status = "✅ Order Placed (Retry)"
                                                                                            self.refresh_table()
                                                                                            
                                                                                            # ✅ V1.7.4: Extract Order ID và Total $
                                                                                            try:
                                                                                                order_id, order_total = self.extract_order_info(driver)
                                                                                                
                                                                                                if order_id:
                                                                                                    account.order_id = order_id
                                                                                                    print(f"[INFO] (Retry) Set Order ID: {order_id}")
                                                                                                
                                                                                                if order_total:
                                                                                                    account.order_total = order_total
                                                                                                    print(f"[INFO] (Retry) Set Order Total: {order_total}")
                                                                                                
                                                                                                # ✅ V1.7.3: Set status Order success
                                                                                                account.status = "Order success"
                                                                                                
                                                                                                # Save và refresh
                                                                                                self.save_accounts()
                                                                                                self.refresh_table()
                                                                                                
                                                                                                # ✅ V1.7.3: Close profile
                                                                                                if account.id:
                                                                                                    self.gpm_api.stop_profile(account.id)
                                                                                                    print("[INFO] (Retry) Profile closed after order success")
                                                                                                
                                                                                            except Exception as extract_error:
                                                                                                print(f"[WARNING] (Retry) Failed to extract order info: {extract_error}")
                                                                                    else:
                                                                                        print("[ERROR] (Retry) Failed to click Place Order")
                                                                                        account.status = "❌ Place Order failed (Retry)"
                                                                                        self.refresh_table()
                                                                                else:
                                                                                    print(f"[WARNING] (Retry) Gift Card Redeemed (${redeemed}) < Subtotal (${subtotal})")
                                                                                    account.status = f"⚠️ Gift insufficient (${redeemed}/${subtotal}) (Retry)"
                                                                                    self.refresh_table()
                                                                            
                                                                            except Exception as place_order_error:
                                                                                print(f"[ERROR] (Retry) Place order process failed: {place_order_error}")
                                                                                account.status = "❌ Place order error (Retry)"
                                                                                self.refresh_table()
                                                                            # ========== END CHECK GIFT & PLACE ORDER (RETRY) ==========
                                                                            
                                                    else:
                                                        print("[WARNING] (Retry) Could not get order total, skipping giftcard")
                                                        account.status = "⚠️ No total found (Retry)"
                                                        self.refresh_table()
                                                    
                                                except Exception as giftcard_error:
                                                    print(f"[ERROR] (Retry) Giftcard error: {giftcard_error}")
                                                    account.status = "⚠️ Giftcard error (Retry)"
                                                    self.refresh_table()
                                                    
                                                    # Restore balances nếu có lỗi
                                                    if gift1 or gift2:
                                                        self.restore_giftcard_balances(account, gift1, gift2, backup_balances)
                                                # ========== END GIFTCARD LOGIC (RETRY FLOW) ==========
                                                
                                            except Exception as shipping_error:
                                                print(f"[ERROR] (Retry) Shipping failed: {shipping_error}")
                                                account.status = "Shipping failed (retry)"
                                                self.refresh_table()
                                        else:
                                            print(f"[INFO] (Retry) No warehouse")
                                            account.status = "No warehouse (retry)"
                                            self.refresh_table()
                                    else:
                                        print(f"[WARNING] No visible checkout button found (retry)")
                                        account.status = "No checkout button (retry)"
                                except Exception as checkout_error:
                                    print(f"[ERROR] Failed to click checkout (retry): {checkout_error}")
                                    account.status = "Checkout failed (retry)"
                            else:
                                print(f"[WARNING] added_count is 0 (retry), not navigating to basket")
                                account.status = "❌ No items added (Retry)"
                                if out_of_stock_count > 0:
                                    account.status += f" (All OOS)"
                            
                        except Exception as retry_error:
                            print(f"[ERROR] Retry failed: {retry_error}")
                            account.status = "Retry Failed"
                
                account.last_run = datetime.now().strftime("%H:%M %d/%m")
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"Error in Sephora Order: {e}")
                print(f"Full traceback:\n{error_detail}")
                account.status = f"Error: {str(e)[:40]}"
            finally:
                # Cleanup driver nếu đã khởi tạo
                try:
                    if 'driver' in locals():
                        driver.quit()
                except:
                    pass
            
            # ✅ V1.3.4: Safe save và refresh
            try:
                self.save_accounts()
                self.refresh_table()
                print(f"[INFO] Completed account: {email}")
            except Exception as save_error:
                print(f"[ERROR] Save/refresh failed: {save_error}")
            
            # Kết thúc xử lý 1 account
            return email
        
        # ✅ V1.8.0: Sử dụng ThreadPoolExecutor để chạy đa luồng
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            # Submit từng account với delay
            for idx, email in enumerate(email_list, 1):
                # Check stop flag trước khi submit
                if self.stop_flag:
                    print("[INFO] Stop flag detected before submission, stopping...")
                    break
                
                # Submit task
                future = executor.submit(process_single_account, idx, email)
                futures.append(future)
                
                print(f"[INFO] Submitted account {idx}/{len(email_list)}: {email}")
                
                # Delay trước khi submit account tiếp theo (trừ account cuối)
                if idx < len(email_list) and delay_between > 0:
                    time.sleep(delay_between)
            
            # Đợi tất cả tasks hoàn thành
            print(f"[INFO] Waiting for all {len(futures)} tasks to complete...")
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        print(f"[SUCCESS] Account completed: {result}")
                except Exception as e:
                    print(f"[ERROR] Account processing failed: {e}")
        
        # ✅ Reset button AFTER all accounts
        print(f"[INFO] All accounts processed, resetting button...")
        self.is_running = False
        self.stop_flag = False
        try:
            self.run_button.configure(text="▶ Chạy", fg_color="#1f6aa5", state="normal")
        except Exception as btn_error:
            print(f"[ERROR] Button reset failed: {btn_error}")
    
    def kill_all_drivers(self):
        """
        ✅ V1.9.0: Đóng tất cả profiles đang mở/chạy
        Fix: Detect profiles đang chạy automation, không chỉ status "Profile Opened"
        """
        # ✅ V1.9.0: List các status cho thấy profile đang hoạt động
        running_statuses = [
            "Profile Opened",
            "Browser Starting",
            "Starting...",
            "Creating Profile...",
            "GPM Profile Created",
            "Opening Profile...",
            "Connecting Browser...",
            "Loading TopCashback...",
            "Searching Sephora...",
            "Selecting USA...",
            "Selecting CAN...",
            "Clicking Get Cash Back...",
            "Loading Sephora...",
            "Closing popup...",
            "Opening login...",
            "Entering credentials...",
            "Checking login...",
            "Opening basket",
            "Clearing old items",
            "Loading Item",
            "Adding Item",
            "Applying coupon",
            "Applying samples",
            "Clicking checkout",
            "Checking shipping",
            "Filling shipping",
            "Getting order total",
            "Selecting giftcards",
            "Assigning giftcards",
            "Applying giftcards",
            "Verifying giftcards",
            "Checking gift balance",
            "Placing order"
        ]
        
        # ✅ V1.9.0: Tìm profiles đang chạy (check nhiều status)
        opened_profiles = []
        for acc in self.accounts:
            # Check exact match
            if acc.status in running_statuses:
                opened_profiles.append(acc)
            # Check partial match (cho các status có thêm thông tin, vd: "Loading Item 1...")
            elif any(status in acc.status for status in running_statuses):
                opened_profiles.append(acc)
        
        if not opened_profiles:
            messagebox.showinfo("ℹ️ Thông báo", "Không có profile nào đang mở!")
            return
        
        if messagebox.askyesno("⚠️ Xác nhận", f"Đóng {len(opened_profiles)} profile(s) đang mở?"):
            closed = 0
            failed = 0
            
            for acc in opened_profiles:
                if acc.id and self.gpm_api.stop_profile(acc.id):
                    acc.status = "Ready"
                    closed += 1
                else:
                    failed += 1
            
            self.save_accounts()
            self.refresh_table()
            
            # Thông báo kết quả
            if failed == 0:
                messagebox.showinfo("✅ OK", f"Đã đóng {closed} profile(s)!")
            else:
                messagebox.showwarning("⚠️ Cảnh báo", 
                                      f"✅ Đóng thành công: {closed}\n❌ Thất bại: {failed}")
    
    def save_accounts(self):
        """
        Lưu accounts
        ✅ V1.8.1: Thread-safe với lock
        """
        with self.save_lock:
            try:
                data = [acc.to_dict() for acc in self.accounts]
                with open("accounts.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving accounts: {e}")
    
    def load_accounts(self):
        """Load accounts"""
        try:
            with open("accounts.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    acc = Account(
                        item['email'],
                        item['password'],
                        item['id'],
                        item.get('proxy', ''),
                        item.get('note', ''),
                        item.get('folder', 'Default')
                    )
                    acc.phone = item.get('phone', '')
                    acc.create_time = item.get('create', '')
                    acc.last_run = item.get('last', '')
                    acc.status = item.get('status', 'Ready')
                    acc.name = item.get('name', '')
                    acc.warehouse_name = item.get('warehouse_name', '')  # ✅ V1.6.5
                    acc.order_id = item.get('order_id', '')  # ✅ V1.6.9
                    acc.order_total = item.get('order_total', '')  # ✅ V1.7.4
                    acc.gift1 = item.get('gift1', '')  # ✅ V1.6.9
                    acc.gift2 = item.get('gift2', '')  # ✅ V1.6.9
                    acc.gift1_used = item.get('gift1_used', 0.0)  # ✅ V1.7.8
                    acc.gift2_used = item.get('gift2_used', 0.0)  # ✅ V1.7.8
                    self.accounts.append(acc)
                
                self.refresh_table()
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error loading accounts: {e}")
    
    def save_warehouses(self):
        """Lưu warehouses"""
        try:
            data = [wh.to_dict() for wh in self.warehouses]
            with open("warehouses.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving warehouses: {e}")
    
    def load_warehouses(self):
        """Load warehouses"""
        try:
            with open("warehouses.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    wh = Warehouse(
                        first_name=item.get('first_name', ''),
                        last_name=item.get('last_name', ''),
                        address=item.get('address', ''),
                        city=item.get('city', ''),
                        state=item.get('state', ''),
                        zip_code=item.get('zip', ''),
                        phone=item.get('phone', ''),
                        name=item.get('name', '')
                    )
                    wh.create_time = item.get('create', '')
                    self.warehouses.append(wh)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error loading warehouses: {e}")
    
    def save_giftcards(self):
        """
        ✅ V1.6.8: Lưu giftcards
        ✅ V1.8.1: Thread-safe với lock
        """
        with self.save_lock:
            try:
                data = [gc.to_dict() for gc in self.giftcards]
                with open("giftcards.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving giftcards: {e}")
    
    def load_giftcards(self):
        """✅ V1.6.8: Load giftcards"""
        try:
            with open("giftcards.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    gc = Giftcard(
                        card_number=item.get('card_number', ''),
                        pin=item.get('pin', ''),
                        balance=item.get('balance', '')
                    )
                    gc.create_time = item.get('create', '')
                    self.giftcards.append(gc)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error loading giftcards: {e}")
    
    def save_config(self):
        """Lưu config"""
        try:
            self.config['folders'] = self.folders
            
            # ✅ V1.5.1: Lưu Items và Quantity riêng biệt
            self.config['item1'] = self.item1_entry.get()
            self.config['item2'] = self.item2_entry.get()
            self.config['item3'] = self.item3_entry.get()
            self.config['qty1'] = self.qty1_entry.get()
            self.config['qty2'] = self.qty2_entry.get()
            self.config['qty3'] = self.qty3_entry.get()
            
            # ✅ V1.5.7: Lưu Coupon và Sample
            self.config['coupon'] = self.coupon_entry.get()
            self.config['coupon_item1'] = self.coupon_item1_entry.get()  # ✅ V1.9.4
            self.config['coupon_item2'] = self.coupon_item2_entry.get()  # ✅ V1.9.4
            self.config['coupon_item3'] = self.coupon_item3_entry.get()  # ✅ V1.9.4
            self.config['coupon_item4'] = self.coupon_item4_entry.get()  # ✅ V1.9.4
            self.config['sample1'] = self.sample1_entry.get()
            self.config['sample2'] = self.sample2_entry.get()

            # ✅ V1.10.7: Lưu Point 1-5
            self.config['point1'] = self.point1_entry.get()
            self.config['point2'] = self.point2_entry.get()
            self.config['point3'] = self.point3_entry.get()
            self.config['point4'] = self.point4_entry.get()
            self.config['point5'] = self.point5_entry.get()

            # ✅ V1.8.6: Lưu Threads và Delay
            self.config['threads'] = self.threads_entry.get()
            self.config['delay'] = self.delay_entry.get()
            
            # ✅ V1.10.6: Lưu Total Item
            self.config['total_item'] = self.total_item_entry.get()

            # ✅ V1.10.7: Lưu Giảm 10$ và 20$ checkbox
            self.config['discount_10'] = self.discount_10_var.get()
            self.config['discount_20'] = self.discount_20_var.get()

            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def load_config(self):
        """Load config"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                if 'folders' in config:
                    loaded_folders = config['folders']
                    
                    # ✅ FIX: Remove duplicates và ensure chỉ có 1 "Default"
                    # Remove duplicates
                    self.folders = list(dict.fromkeys(loaded_folders))
                    
                    # Remove "Mặc định" nếu có
                    if "Mặc định" in self.folders:
                        self.folders.remove("Mặc định")
                    
                    # Ensure "Default" luôn có mặt và ở đầu
                    if "Default" not in self.folders:
                        self.folders.insert(0, "Default")
                    else:
                        # Move "Default" lên đầu
                        self.folders.remove("Default")
                        self.folders.insert(0, "Default")
                return config
        except:
            return {}
    
    def on_closing(self):
        """Khi đóng app"""
        self.save_accounts()
        self.save_warehouses()
        self.save_config()
        self.destroy()


# ==================== MAIN ====================
if __name__ == "__main__":
    app = SephoraAutoTool()
    app.mainloop()

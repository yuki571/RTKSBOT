# PC Parts Data for Enhanced Mining System
import random
from typing import Dict, List, Tuple

class PCPartsData:
    """実際のPCパーツデータベース"""
    
    # GPUデータ（実際の製品）
    GPUS = {
        # NVIDIA RTX 40シリーズ
        "RTX 4090": {
            "hash_rate": 120,  # MH/s (仮想)
            "power": 450,      # W
            "price": 2000000,  # 仮想通貨
            "tier": "legendary",
            "brand": "NVIDIA",
            "series": "RTX 40",
            "memory": "24GB GDDR6X"
        },
        "RTX 4080": {
            "hash_rate": 95,
            "power": 320,
            "price": 1500000,
            "tier": "epic",
            "brand": "NVIDIA",
            "series": "RTX 40",
            "memory": "16GB GDDR6X"
        },
        "RTX 4070 Ti": {
            "hash_rate": 75,
            "power": 285,
            "price": 1000000,
            "tier": "rare",
            "brand": "NVIDIA",
            "series": "RTX 40",
            "memory": "12GB GDDR6X"
        },
        "RTX 4070": {
            "hash_rate": 65,
            "power": 200,
            "price": 800000,
            "tier": "rare",
            "brand": "NVIDIA",
            "series": "RTX 40",
            "memory": "12GB GDDR6X"
        },
        "RTX 4060 Ti": {
            "hash_rate": 50,
            "power": 165,
            "price": 600000,
            "tier": "uncommon",
            "brand": "NVIDIA",
            "series": "RTX 40",
            "memory": "8GB GDDR6"
        },
        "RTX 4060": {
            "hash_rate": 40,
            "power": 115,
            "price": 450000,
            "tier": "uncommon",
            "brand": "NVIDIA",
            "series": "RTX 40",
            "memory": "8GB GDDR6"
        },
        
        # NVIDIA RTX 30シリーズ
        "RTX 3090": {
            "hash_rate": 110,
            "power": 350,
            "price": 1800000,
            "tier": "legendary",
            "brand": "NVIDIA",
            "series": "RTX 30",
            "memory": "24GB GDDR6X"
        },
        "RTX 3080": {
            "hash_rate": 85,
            "power": 320,
            "price": 1200000,
            "tier": "epic",
            "brand": "NVIDIA",
            "series": "RTX 30",
            "memory": "10GB GDDR6X"
        },
        "RTX 3070": {
            "hash_rate": 70,
            "power": 220,
            "price": 800000,
            "tier": "rare",
            "brand": "NVIDIA",
            "series": "RTX 30",
            "memory": "8GB GDDR6"
        },
        "RTX 3060 Ti": {
            "hash_rate": 60,
            "power": 200,
            "price": 600000,
            "tier": "rare",
            "brand": "NVIDIA",
            "series": "RTX 30",
            "memory": "8GB GDDR6"
        },
        "RTX 3060": {
            "hash_rate": 45,
            "power": 170,
            "price": 500000,
            "tier": "uncommon",
            "brand": "NVIDIA",
            "series": "RTX 30",
            "memory": "12GB GDDR6"
        },
        
        # AMD RX 7000シリーズ
        "RX 7900 XTX": {
            "hash_rate": 105,
            "power": 355,
            "price": 1600000,
            "tier": "legendary",
            "brand": "AMD",
            "series": "RX 7000",
            "memory": "24GB GDDR6"
        },
        "RX 7900 XT": {
            "hash_rate": 90,
            "power": 300,
            "price": 1300000,
            "tier": "epic",
            "brand": "AMD",
            "series": "RX 7000",
            "memory": "20GB GDDR6"
        },
        "RX 7800 XT": {
            "hash_rate": 75,
            "power": 263,
            "price": 900000,
            "tier": "rare",
            "brand": "AMD",
            "series": "RX 7000",
            "memory": "16GB GDDR6"
        },
        "RX 7700 XT": {
            "hash_rate": 60,
            "power": 245,
            "price": 700000,
            "tier": "rare",
            "brand": "AMD",
            "series": "RX 7000",
            "memory": "12GB GDDR6"
        },
        "RX 7600": {
            "hash_rate": 45,
            "power": 165,
            "price": 450000,
            "tier": "uncommon",
            "brand": "AMD",
            "series": "RX 7000",
            "memory": "8GB GDDR6"
        },
        
        # 旧世代・エントリー
        "GTX 1660 Super": {
            "hash_rate": 30,
            "power": 125,
            "price": 300000,
            "tier": "common",
            "brand": "NVIDIA",
            "series": "GTX 16",
            "memory": "6GB GDDR6"
        },
        "GTX 1650": {
            "hash_rate": 18,
            "power": 75,
            "price": 200000,
            "tier": "common",
            "brand": "NVIDIA",
            "series": "GTX 16",
            "memory": "4GB GDDR6"
        }
    }
    
    # CPUデータ
    CPUS = {
        # Intel 13世代
        "i9-13900K": {
            "hash_rate": 25,
            "power": 125,
            "price": 800000,
            "tier": "legendary",
            "brand": "Intel",
            "series": "13th Gen",
            "cores": "24コア32スレッド"
        },
        "i7-13700K": {
            "hash_rate": 20,
            "power": 125,
            "price": 600000,
            "tier": "epic",
            "brand": "Intel",
            "series": "13th Gen",
            "cores": "16コア24スレッド"
        },
        "i5-13600K": {
            "hash_rate": 15,
            "power": 125,
            "price": 450000,
            "tier": "rare",
            "brand": "Intel",
            "series": "13th Gen",
            "cores": "14コア20スレッド"
        },
        
        # AMD Ryzen 7000
        "Ryzen 9 7950X": {
            "hash_rate": 28,
            "power": 170,
            "price": 900000,
            "tier": "legendary",
            "brand": "AMD",
            "series": "Ryzen 7000",
            "cores": "16コア32スレッド"
        },
        "Ryzen 7 7700X": {
            "hash_rate": 22,
            "power": 105,
            "price": 550000,
            "tier": "epic",
            "brand": "AMD",
            "series": "Ryzen 7000",
            "cores": "8コア16スレッド"
        },
        "Ryzen 5 7600X": {
            "hash_rate": 18,
            "power": 105,
            "price": 400000,
            "tier": "rare",
            "brand": "AMD",
            "series": "Ryzen 7000",
            "cores": "6コア12スレッド"
        }
    }
    
    # マザーボード
    MOTHERBOARDS = {
        "ASUS ROG MAXIMUS Z790 HERO": {
            "max_gpus": 4,
            "price": 800000,
            "tier": "legendary",
            "brand": "ASUS",
            "socket": "LGA1700",
            "features": ["Wi-Fi 6E", "10Gb LAN", "PCIe 5.0"]
        },
        "MSI MAG B650 TOMAHAWK": {
            "max_gpus": 3,
            "price": 350000,
            "tier": "rare",
            "brand": "MSI",
            "socket": "AM5",
            "features": ["Wi-Fi 6", "2.5Gb LAN", "PCIe 4.0"]
        },
        "ASRock B550M PRO4": {
            "max_gpus": 2,
            "price": 150000,
            "tier": "common",
            "brand": "ASRock",
            "socket": "AM4",
            "features": ["PCIe 4.0", "M.2スロット"]
        }
    }
    
    # 電源ユニット
    PSUS = {
        "Corsair AX1600i": {
            "wattage": 1600,
            "efficiency": "80+ Titanium",
            "price": 600000,
            "tier": "legendary",
            "modular": True
        },
        "Seasonic Focus GX-850": {
            "wattage": 850,
            "efficiency": "80+ Gold",
            "price": 200000,
            "tier": "rare",
            "modular": True
        },
        "EVGA 600 W1": {
            "wattage": 600,
            "efficiency": "80+ White",
            "price": 80000,
            "tier": "common",
            "modular": False
        }
    }
    
    # レア度別の排出確率
    RARITY_RATES = {
        "common": 50.0,      # 50%
        "uncommon": 30.0,    # 30%
        "rare": 15.0,        # 15%
        "epic": 4.0,         # 4%
        "legendary": 1.0     # 1%
    }
    
    # レア度別の色（Discord埋め込み用）
    RARITY_COLORS = {
        "common": 0x999999,      # グレー
        "uncommon": 0x00ff00,    # 緑
        "rare": 0x0080ff,        # 青
        "epic": 0x8000ff,        # 紫
        "legendary": 0xffaa00    # オレンジ
    }
    
    # レア度別の絵文字
    RARITY_EMOJIS = {
        "common": "⚪",
        "uncommon": "🟢",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟠"
    }

    @classmethod
    def get_random_part(cls, part_type: str) -> Tuple[str, Dict]:
        """指定されたパーツタイプからランダムに選択"""
        parts_dict = getattr(cls, part_type.upper())
        
        # レア度による重み付け抽選
        weights = []
        items = []
        
        for name, data in parts_dict.items():
            tier = data["tier"]
            weight = cls.RARITY_RATES[tier]
            weights.append(weight)
            items.append((name, data))
        
        selected_item = random.choices(items, weights=weights, k=1)[0]
        return selected_item[0], selected_item[1]
    
    @classmethod
    def calculate_total_hash_rate(cls, user_parts: Dict) -> int:
        """ユーザーのパーツ構成から総ハッシュレートを計算"""
        total_hash_rate = 0
        
        # GPU
        if "gpus" in user_parts:
            for gpu_name, quantity in user_parts["gpus"].items():
                if gpu_name in cls.GPUS:
                    total_hash_rate += cls.GPUS[gpu_name]["hash_rate"] * quantity
        
        # CPU
        if "cpu" in user_parts and user_parts["cpu"] in cls.CPUS:
            total_hash_rate += cls.CPUS[user_parts["cpu"]]["hash_rate"]
        
        return total_hash_rate
    
    @classmethod
    def calculate_power_consumption(cls, user_parts: Dict) -> int:
        """ユーザーのパーツ構成から消費電力を計算"""
        total_power = 0
        
        # GPU
        if "gpus" in user_parts:
            for gpu_name, quantity in user_parts["gpus"].items():
                if gpu_name in cls.GPUS:
                    total_power += cls.GPUS[gpu_name]["power"] * quantity
        
        # CPU
        if "cpu" in user_parts and user_parts["cpu"] in cls.CPUS:
            total_power += cls.CPUS[user_parts["cpu"]]["power"]
        
        return total_power
    
    @classmethod
    def is_build_valid(cls, user_parts: Dict) -> Tuple[bool, str]:
        """PC構成が有効かチェック"""
        # マザーボードのGPU制限チェック
        if "motherboard" in user_parts and "gpus" in user_parts:
            mb_name = user_parts["motherboard"]
            if mb_name in cls.MOTHERBOARDS:
                max_gpus = cls.MOTHERBOARDS[mb_name]["max_gpus"]
                total_gpus = sum(user_parts["gpus"].values())
                
                if total_gpus > max_gpus:
                    return False, f"マザーボード {mb_name} は最大{max_gpus}枚のGPUしかサポートしていません"
        
        # 電源容量チェック
        if "psu" in user_parts:
            psu_name = user_parts["psu"]
            if psu_name in cls.PSUS:
                psu_wattage = cls.PSUS[psu_name]["wattage"]
                total_power = cls.calculate_power_consumption(user_parts)
                
                if total_power > psu_wattage * 0.8:  # 80%ルール
                    return False, f"電源容量が不足しています ({total_power}W > {int(psu_wattage * 0.8)}W)"
        
        return True, "構成は有効です"
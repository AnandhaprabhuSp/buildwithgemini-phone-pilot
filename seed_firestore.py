"""Seed script for PhonePilot Firestore database.

Populates initial catalog of smartphones.
"""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-7d222e5d4be1"

PHONES = [
    {
        "id": "pixel-11-pro",
        "model_name": "Google Pixel 11 Pro",
        "brand": "Google",
        "price": 999.0,
        "display": "6.3-inch Super Actua LTPO OLED (1-120Hz, 3000 nits peak)",
        "processor": "Google Tensor G5 with Titan M3 security coprocessor",
        "camera_system": "Triple: 50MP main (f/1.68 OIS), 48MP ultrawide with Macro Focus, 48MP 5x telephoto (up to 30x Super Res Zoom), 42MP front camera with autofocus",
        "battery": "4700 mAh, up to 100 hours with Extreme Battery Saver, 30W fast charge, Qi2 wireless",
        "colors": ["Obsidian", "Porcelain", "Hazel", "Rose Quartz"],
        "storage_options": ["128GB", "256GB", "512GB", "1TB"],
        "trade_in_value_base": 450.0,
        "features": [
            "Next-gen Tensor G5 on-device Gemini Nano multimodal intelligence",
            "Pro camera system with 8K Video Boost and generative Zoom Enhance",
            "Pixel Studio for on-device text-to-image and generative editing",
            "7 years of OS, security upgrades, and new Pixel Feature Drops",
            "Call Assist with Pixel Call Screen and AI Scam Detection"
        ],
        "in_stock": True
    },
    {
        "id": "pixel-10-pro",
        "model_name": "Google Pixel 10 Pro",
        "brand": "Google",
        "price": 899.0,
        "display": "6.3-inch Actua LTPO OLED (1-120Hz, 2700 nits peak)",
        "processor": "Google Tensor G4 with Titan M2 security coprocessor",
        "camera_system": "Triple: 50MP main, 48MP ultrawide, 48MP 5x telephoto, 10.5MP front camera",
        "battery": "4500 mAh, 27W fast charge, Qi wireless",
        "colors": ["Obsidian", "Porcelain", "Hazel"],
        "storage_options": ["128GB", "256GB", "512GB"],
        "trade_in_value_base": 380.0,
        "features": [
            "Tensor G4 with Gemini Live integration",
            "Super Res Zoom up to 30x with Add Me camera feature",
            "7 years of Android OS and feature updates",
            "IP68 dust and water resistance"
        ],
        "in_stock": True
    },
    {
        "id": "galaxy-s25-ultra",
        "model_name": "Samsung Galaxy S25 Ultra",
        "brand": "Samsung",
        "price": 1299.0,
        "display": "6.8-inch Dynamic AMOLED 2X (1-120Hz, 2600 nits peak, Gorilla Armor anti-reflective)",
        "processor": "Snapdragon 8 Elite for Galaxy",
        "camera_system": "Quad: 200MP main, 50MP 5x periscope, 10MP 3x telephoto, 50MP ultrawide, 12MP front",
        "battery": "5000 mAh, 45W wired, 15W wireless",
        "colors": ["Titanium Black", "Titanium Gray", "Titanium Violet", "Titanium Yellow"],
        "storage_options": ["256GB", "512GB", "1TB"],
        "trade_in_value_base": 550.0,
        "features": [
            "Snapdragon 8 Elite flagship mobile processor",
            "Built-in S Pen stylus support",
            "200MP detail enhancer with Galaxy AI photography suite",
            "7 generations of OS and security upgrades"
        ],
        "in_stock": True
    },
    {
        "id": "iphone-16-pro",
        "model_name": "Apple iPhone 16 Pro",
        "brand": "Apple",
        "price": 999.0,
        "display": "6.3-inch Super Retina XDR OLED (1-120Hz ProMotion, 2000 nits peak)",
        "processor": "Apple A18 Pro chip with 6-core GPU and 16-core Neural Engine",
        "camera_system": "Triple: 48MP Fusion, 48MP ultrawide, 12MP 5x telephoto, 12MP TrueDepth front",
        "battery": "3582 mAh, 25W MagSafe wireless, USB-C 3.0",
        "colors": ["Black Titanium", "White Titanium", "Natural Titanium", "Desert Titanium"],
        "storage_options": ["128GB", "256GB", "512GB", "1TB"],
        "trade_in_value_base": 480.0,
        "features": [
            "A18 Pro with hardware-accelerated ray tracing and Apple Intelligence",
            "Dedicated Camera Control physical touch sensor button",
            "ProRAW, ProRes 4K 120 fps video capture",
            "Grade 5 Titanium design with Ceramic Shield front"
        ],
        "in_stock": True
    }
]

def seed_database():
    print(f"Connecting to Firestore for project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    phones_ref = db.collection("phones")
    
    for phone in PHONES:
        doc_id = phone["id"]
        doc_ref = phones_ref.document(doc_id)
        doc_ref.set(phone)
        print(f"  ✓ Seeded phone: {phone['model_name']} (ID: {doc_id})")
        
    print("\nDatabase seeded successfully!")

if __name__ == "__main__":
    seed_database()

"""Seed AwesomeGear products"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.products import Product


AWESOME_PRODUCTS = [
    # Apparel
    {"name": "AwesomeBot Classic T-Shirt", "category": "apparel", "description": "100% organic cotton t-shirt with AwesomeBot logo. Available in black, white, and blue.", "price": 24.99, "stock": 150},
    {"name": "AwesomeBot Hoodie", "category": "apparel", "description": "Cozy fleece hoodie with embroidered AwesomeBot logo. Perfect for coding sessions.", "price": 49.99, "stock": 75},
    {"name": "AwesomeBot Baseball Cap", "category": "apparel", "description": "Adjustable cotton cap with AwesomeBot emblem. One size fits all.", "price": 19.99, "stock": 200},
    {"name": "AwesomeBot Tech Polo", "category": "apparel", "description": "Professional polo shirt with subtle AwesomeBot branding. Moisture-wicking fabric.", "price": 34.99, "stock": 100},
    
    # Drinkware
    {"name": "AwesomeBot Coffee Mug", "category": "drinkware", "description": "Ceramic 12oz mug with AwesomeBot logo. Microwave and dishwasher safe.", "price": 14.99, "stock": 300},
    {"name": "AwesomeBot Insulated Tumbler", "category": "drinkware", "description": "Stainless steel 20oz tumbler. Keeps drinks cold for 24hrs, hot for 12hrs.", "price": 29.99, "stock": 150},
    {"name": "AwesomeBot Water Bottle", "category": "drinkware", "description": "BPA-free 32oz water bottle with flip-top lid. Perfect for staying hydrated while coding.", "price": 19.99, "stock": 250},
    {"name": "AwesomeBot Travel Mug", "category": "drinkware", "description": "Leak-proof 16oz travel mug with AwesomeBot design. Fits most cup holders.", "price": 24.99, "stock": 180},
    
    # Accessories
    {"name": "AwesomeBot Sticker Pack", "category": "accessories", "description": "Set of 10 vinyl stickers featuring AwesomeBot and AI-themed designs. Waterproof.", "price": 7.99, "stock": 500},
    {"name": "AwesomeBot Keychain", "category": "accessories", "description": "Metal keychain with AwesomeBot logo. Durable and stylish.", "price": 9.99, "stock": 400},
    {"name": "AwesomeBot Laptop Sticker", "category": "accessories", "description": "Large 6-inch vinyl sticker perfect for laptops. Show your AwesomeBot pride!", "price": 4.99, "stock": 600},
    {"name": "AwesomeBot Tote Bag", "category": "accessories", "description": "Canvas tote bag with AwesomeBot print. Great for carrying tech gear.", "price": 16.99, "stock": 120},
    {"name": "AwesomeBot Backpack", "category": "accessories", "description": "Durable backpack with padded laptop compartment and AwesomeBot embroidery.", "price": 59.99, "stock": 60},
    
    # Tech
    {"name": "AwesomeBot Mouse Pad", "category": "tech", "description": "Large gaming mouse pad with AwesomeBot design. Non-slip rubber base.", "price": 12.99, "stock": 200},
    {"name": "AwesomeBot USB Drive", "category": "tech", "description": "32GB USB 3.0 flash drive with AwesomeBot logo. Fast data transfer.", "price": 19.99, "stock": 150},
    {"name": "AwesomeBot Wireless Charger", "category": "tech", "description": "Qi-compatible wireless charging pad with AwesomeBot design. 10W fast charging.", "price": 29.99, "stock": 100},
    {"name": "AwesomeBot Phone Stand", "category": "tech", "description": "Adjustable phone stand with AwesomeBot logo. Perfect for video calls.", "price": 15.99, "stock": 180},
    
    # Office
    {"name": "AwesomeBot Notebook", "category": "office", "description": "Hardcover notebook with 200 pages. AwesomeBot logo on cover. Perfect for notes and sketches.", "price": 12.99, "stock": 250},
    {"name": "AwesomeBot Pen Set", "category": "office", "description": "Set of 3 premium ballpoint pens with AwesomeBot branding. Smooth writing.", "price": 9.99, "stock": 300},
    {"name": "AwesomeBot Desk Mat", "category": "office", "description": "Large desk mat with AwesomeBot design. Protects desk and provides smooth surface.", "price": 24.99, "stock": 100},
    {"name": "AwesomeBot Sticky Notes", "category": "office", "description": "Pack of 6 sticky note pads with AwesomeBot logo. Various colors.", "price": 6.99, "stock": 400},
]


async def seed_products(db: AsyncSession):
    """Seed products if they don't exist"""
    
    # Check if products already exist
    result = await db.execute(select(Product).limit(1))
    if result.scalar_one_or_none():
        print("✅ Products already seeded")
        return
    
    # Add all products
    for product_data in AWESOME_PRODUCTS:
        product = Product(
            id=str(uuid.uuid4()),
            **product_data
        )
        db.add(product)
    
    await db.commit()
    print(f"✅ Seeded {len(AWESOME_PRODUCTS)} AwesomeGear products")



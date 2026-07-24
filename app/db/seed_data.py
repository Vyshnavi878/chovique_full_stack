"""
Database seed script.

Populates the database with initial data matching the frontend mockData.ts.
Idempotent: checks if data exists before inserting.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.product_repository import ProductRepository
from app.repositories.banner_repository import BannerRepository
from app.repositories.testimonial_repository import TestimonialRepository
from app.repositories.site_config_repository import SiteConfigRepository

logger = logging.getLogger(__name__)


# ==========================================================
# Seed Products
# ==========================================================

SEED_PRODUCTS = [
    {
        "id": "p1",
        "name": "Belgian Dark Truffle Bar",
        "slug": "belgian-dark-truffle-bar",
        "category": "dark",
        "price": 849,
        "original_price": 1199,
        "weight": "100g",
        "badge": "Bestseller",
        "image": "https://images.unsplash.com/photo-1548907040-4d42b52115ca?auto=format&fit=crop&w=600&q=80",
        "hover_image": "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "ratings_count": 148,
        "description": "72% single-origin cocoa from Ghana, cold-pressed with Tahitian vanilla and dusted with gold leaf. Expect a rich, complex cocoa profile with notes of dried fruit and warm spice.",
        "ingredients": "Ghanaian Cocoa Mass, Cocoa Butter, Organic Cane Sugar, Tahitian Vanilla Bean Extract, Edible 24k Gold Leaf, Soy Lecithin (emulsifier).",
        "nutrition": {
            "calories": "560 kcal",
            "totalFat": "38g",
            "saturatedFat": "23g",
            "cholesterol": "0mg",
            "sodium": "15mg",
            "totalCarb": "48g",
            "protein": "7.5g",
        },
        "sort_order": 1,
    },
    {
        "id": "p2",
        "name": "Royal Truffle Collection",
        "slug": "royal-truffle-collection",
        "category": "gift",
        "price": 2499,
        "original_price": 3299,
        "weight": "300g",
        "badge": "New",
        "image": "https://images.unsplash.com/photo-1549007994-cb92caebd54b?auto=format&fit=crop&w=600&q=80",
        "hover_image": "https://images.unsplash.com/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "ratings_count": 92,
        "description": "An exquisite 24-piece assortment of hand-rolled truffles in dark, milk, and white chocolate. Flavors include Salted Caramel, Dark Espresso, Rose Raspberry, and Pistachio Saffron.",
        "ingredients": "Cocoa Mass, Cocoa Butter, Whole Milk Powder, Dairy Cream, Butter, Sugar, Natural Flavourings (Raspberry, Coffee, Pistachio, Saffron), Soy Lecithin.",
        "nutrition": {
            "calories": "525 kcal",
            "totalFat": "34g",
            "saturatedFat": "20g",
            "cholesterol": "18mg",
            "sodium": "45mg",
            "totalCarb": "52g",
            "protein": "6.2g",
        },
        "sort_order": 2,
    },
    {
        "id": "p3",
        "name": "Gold Leaf Pralines",
        "slug": "gold-leaf-pralines",
        "category": "dark",
        "price": 1649,
        "original_price": 2199,
        "weight": "180g",
        "badge": "Premium",
        "image": "https://images.unsplash.com/photo-1526081347589-7fa3cb36b312?auto=format&fit=crop&w=600&q=80",
        "hover_image": "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=600&q=80",
        "rating": 5.0,
        "ratings_count": 74,
        "description": "Premium pistachio cream and caramelized hazelnut wrapped in 64% dark chocolate, finished with edible 24k gold. A harmonious blend of nutty creaminess and rich dark chocolate.",
        "ingredients": "Cocoa Mass, Cocoa Butter, Sugar, Roasted Hazelnuts, Iranian Pistachios, Milk Solid Cream, Edible Gold flakes, Lecithin, Natural Vanilla.",
        "nutrition": {
            "calories": "575 kcal",
            "totalFat": "41g",
            "saturatedFat": "18g",
            "cholesterol": "4mg",
            "sodium": "35mg",
            "totalCarb": "45g",
            "protein": "8.8g",
        },
        "sort_order": 3,
    },
    {
        "id": "p4",
        "name": "Hazelnut Crunch",
        "slug": "hazelnut-crunch",
        "category": "milk",
        "price": 699,
        "original_price": 899,
        "weight": "150g",
        "badge": None,
        "image": "https://images.unsplash.com/photo-1542841791-1925b02a2bcd?auto=format&fit=crop&w=600&q=80",
        "hover_image": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "ratings_count": 110,
        "description": "Creamy milk chocolate crafted from premium Madagascan cocoa, combined with double-roasted, caramelized Turkish hazelnuts for the ultimate crunch.",
        "ingredients": "Milk Chocolate (Madagascan Cocoa 38%, Whole Milk Powder, Sugar, Cocoa Butter), Turkish Hazelnuts, Caramelized Sugar, Natural Vanilla Flavor.",
        "nutrition": {
            "calories": "585 kcal",
            "totalFat": "39g",
            "saturatedFat": "16g",
            "cholesterol": "15mg",
            "sodium": "60mg",
            "totalCarb": "50g",
            "protein": "8.0g",
        },
        "sort_order": 4,
    },
    {
        "id": "p5",
        "name": "Salted Caramel Bonbons",
        "slug": "salted-caramel-bonbons",
        "category": "dark",
        "price": 999,
        "original_price": 1299,
        "weight": "120g",
        "badge": None,
        "image": "https://images.unsplash.com/photo-1581798459219-318e76aecc7b?auto=format&fit=crop&w=600&q=80",
        "hover_image": "https://images.unsplash.com/photo-1534706936160-d5be8023c345?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "ratings_count": 88,
        "description": "Exquisite 8-piece bonbon shell containing rich, hand-cooked fleur de sel liquid caramel that oozes out in every bite. Encased in a beautiful glassmorphic sliding case.",
        "ingredients": "Dark Chocolate Shell (Ecuadorian Cocoa 60%), Caramel Fill (Glucose Syrup, Butter, Heavy Cream, Sea Salt (Fleur de Sel)), Emulsifier.",
        "nutrition": {
            "calories": "495 kcal",
            "totalFat": "28g",
            "saturatedFat": "17g",
            "cholesterol": "25mg",
            "sodium": "190mg",
            "totalCarb": "58g",
            "protein": "4.2g",
        },
        "sort_order": 5,
    },
    {
        "id": "p6",
        "name": "White Macadamia Bar",
        "slug": "white-macadamia-bar",
        "category": "white",
        "price": 749,
        "original_price": 949,
        "weight": "100g",
        "badge": None,
        "image": "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=600&q=80",
        "hover_image": "https://images.unsplash.com/photo-1548907040-4d42b52115ca?auto=format&fit=crop&w=600&q=80",
        "rating": 4.6,
        "ratings_count": 56,
        "description": "Velvety, slow-churned white chocolate packed with buttery Queensland macadamia nuts. Mildly sweet, highlighting the premium cocoa butter quality.",
        "ingredients": "Deodorized Cocoa Butter, Whole Milk Solids, Icing Sugar, Roasted Macadamia Nuts, Pure Vanilla Extract, Soy Lecithin.",
        "nutrition": {
            "calories": "610 kcal",
            "totalFat": "44g",
            "saturatedFat": "24g",
            "cholesterol": "20mg",
            "sodium": "70mg",
            "totalCarb": "47g",
            "protein": "7.0g",
        },
        "sort_order": 6,
    },
    {
        "id": "p7",
        "name": "Dipped Strawberries",
        "slug": "dipped-strawberries",
        "category": "gift",
        "price": 1299,
        "original_price": 1699,
        "weight": "12 Pieces",
        "badge": "Limited",
        "image": "https://images.unsplash.com/photo-1518635017498-87f514b751ba?auto=format&fit=crop&w=600&q=80",
        "hover_image": "https://images.unsplash.com/photo-1587314168485-3236d6710814?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "ratings_count": 63,
        "description": "Handpicked fresh Mahabaleshwar strawberries dipped in premium Ecuadorian dark and milk chocolate, drizzled with white chocolate stripes.",
        "ingredients": "Fresh Strawberries, Dark Chocolate (Ecuadorian Cocoa 55%), Milk Chocolate (Cocoa 36%), White Chocolate Drizzle.",
        "nutrition": {
            "calories": "280 kcal",
            "totalFat": "14g",
            "saturatedFat": "9g",
            "cholesterol": "5mg",
            "sodium": "20mg",
            "totalCarb": "36g",
            "protein": "3.0g",
        },
        "sort_order": 7,
    },
    {
        "id": "p8",
        "name": "Velvet Hot Chocolate",
        "slug": "velvet-hot-chocolate",
        "category": "beverage",
        "price": 599,
        "original_price": 799,
        "weight": "250g",
        "badge": None,
        "image": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=600&q=80",
        "hover_image": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "ratings_count": 120,
        "description": "A luxurious shaving blend of 68% chocolate flakes, ready to melt in hot milk. Formulated to create a thick, frothy hot beverage like the Parisian cafes.",
        "ingredients": "Shaved Chocolate Flakes (Ghanaian Cocoa mass 68%, Sugar, Cocoa Butter, Vanilla), Cocoa Powder, Cornstarch (thickener).",
        "nutrition": {
            "calories": "450 kcal",
            "totalFat": "26g",
            "saturatedFat": "16g",
            "cholesterol": "0mg",
            "sodium": "10mg",
            "totalCarb": "53g",
            "protein": "6.8g",
        },
        "sort_order": 8,
    },
]


# ==========================================================
# Seed Banners
# ==========================================================

SEED_BANNERS = [
    {
        "title": "The Art of Fine Chocolate",
        "subtitle": "Handcrafted from the world's finest single-origin cocoa beans, every Chovique creation is a masterpiece of flavor and elegance.",
        "tag": "Est. 2020 · Premium Handmade Chocolates",
        "image": "/assets/hero-1.jpg",
        "button_text": "Explore Collection",
        "link": "#popular",
        "sort_order": 0,
    },
    {
        "title": "Festive Season Sale — 40% Off",
        "subtitle": "Indulge in our curated gift boxes, truffles, and pralines. Perfect for gifting or savoring the finest moments.",
        "tag": "Limited Time Offer",
        "image": "/assets/hero-2.jpg",
        "button_text": "Shop Deals",
        "link": "#store",
        "sort_order": 1,
    },
    {
        "title": "Crafted with Passion & Precision",
        "subtitle": "From sourcing the rarest cocoa beans to tempering by hand, we pour love into every single piece.",
        "tag": "Bean to Bar · Handcrafted",
        "image": "/assets/hero-3.jpg",
        "button_text": "Discover Our Process",
        "link": "/our-story",
        "sort_order": 2,
    },
    {
        "title": "Gift the Joy of Luxury Chocolate",
        "subtitle": "Our premium gift hampers and bespoke packaging make every occasion unforgettable.",
        "tag": "Luxury Gifting · Worldwide Delivery",
        "image": "/assets/hero-4.jpg",
        "button_text": "View Gift Sets",
        "link": "#store",
        "sort_order": 3,
    },
]


# ==========================================================
# Seed Testimonials
# ==========================================================

SEED_TESTIMONIALS = [
    {
        "author": "Vikram Kapoor",
        "title": "Food Critic, Mumbai",
        "text": "I've tried chocolates from Belgium, Switzerland, and France — but Chovique genuinely stands apart. The depth of flavor in their single-origin bars is extraordinary.",
        "rating": 5.0,
        "initials": "VK",
        "sort_order": 0,
    },
    {
        "author": "Neha Patel",
        "title": "Loyal Customer, Delhi",
        "text": "Ordered a bespoke gift box for my mother's birthday. The presentation was flawless, and the chocolates were even better. Chovique turned a gift into a memory.",
        "rating": 5.0,
        "initials": "NP",
        "sort_order": 1,
    },
    {
        "author": "Chef Ravi Joshi",
        "title": "Pastry Chef, Bangalore",
        "text": "As a pastry chef, I'm incredibly particular about chocolate. Chovique's cocoa is consistent, rich, and tempers beautifully. It's my go-to for all premium work.",
        "rating": 5.0,
        "initials": "RJ",
        "sort_order": 2,
    },
]


# ==========================================================
# Seed Site Config
# ==========================================================

SEED_CONFIGS = {
    "stats": {
        "happy_customers": 50000,
        "unique_flavors": 120,
        "countries_shipped": 15,
        "five_star_reviews_percent": 98,
    },
    "contact": {
        "email": "hello@chovique.com",
        "phone": "+91 98765 43210",
        "address": "Chovique Chocolatier, Sector 15, Mumbai, Maharashtra 400053",
        "instagram": "https://instagram.com/chovique",
        "facebook": "https://facebook.com/chovique",
        "twitter": "https://twitter.com/chovique",
    },
}


SEED_COUPONS = [
    {
        "code": "CHOVIQUE10",
        "description": "10% off your order",
        "discount_percent": 10.0,
        "discount_amount": 0.0,
    },
    {
        "code": "NEWUSER50",
        "description": "₹50 flat off for new users",
        "discount_percent": 0.0,
        "discount_amount": 50.0,
    },
    {
        "code": "FESTIVE25",
        "description": "25% off festive collection",
        "discount_percent": 25.0,
        "discount_amount": 0.0,
    },
    {
        "code": "FESTIVE40",
        "description": "40% off festive season sale",
        "discount_percent": 40.0,
        "discount_amount": 0.0,
    },
]

SEED_CATEGORIES = [
    {"name": "Dark Chocolate", "slug": "dark", "description": "Rich 60%-85% cocoa single-origin dark chocolate.", "sort_order": 1},
    {"name": "Milk Chocolate", "slug": "milk", "description": "Creamy, smooth milk chocolate delicacies.", "sort_order": 2},
    {"name": "White Chocolate", "slug": "white", "description": "Velvety cocoa butter white chocolate creations.", "sort_order": 3},
    {"name": "Gift Hampers", "slug": "gift", "description": "Luxurious corporate and celebration gift boxes.", "sort_order": 4},
    {"name": "Beverages", "slug": "beverage", "description": "Parisian style hot chocolate shavings and cocoa.", "sort_order": 5},
]

SEED_FAQS = [
    {
        "question": "Where are Chovique chocolates made?",
        "answer": "All our chocolates are handcrafted in our state-of-the-art atelier in Mumbai using cocoa beans directly sourced from Ghana, Ecuador, and Madagascar.",
        "category": "General",
        "sort_order": 1,
    },
    {
        "question": "How should I store Chovique chocolates?",
        "answer": "Keep them in a cool, dry place between 15°C - 18°C away from direct sunlight and strong odors.",
        "category": "Storage",
        "sort_order": 2,
    },
    {
        "question": "What is the estimated delivery time?",
        "answer": "Standard delivery takes 2-4 business days. Temperature-controlled express shipping delivers within 24-48 hours.",
        "category": "Shipping",
        "sort_order": 3,
    },
]


# ==========================================================
# Run Seeder
# ==========================================================

async def seed_database(db: AsyncSession) -> None:
    """
    Seed the database with initial data.
    Idempotent: skips if data already exists.
    """
    from app.repositories.coupon_repository import CouponRepository
    from app.repositories.reel_repository import ReelRepository

    product_repo = ProductRepository(db)
    banner_repo = BannerRepository(db)
    testimonial_repo = TestimonialRepository(db)
    config_repo = SiteConfigRepository(db)
    coupon_repo = CouponRepository(db)
    reel_repo = ReelRepository(db)

    # --- Products ---
    product_count = await product_repo.count()
    if product_count == 0:
        logger.info("Seeding %d products...", len(SEED_PRODUCTS))
        for data in SEED_PRODUCTS:
            await product_repo.create(**data)
        logger.info("Products seeded successfully.")
    else:
        logger.info("Products already seeded (%d found). Skipping.", product_count)

    # --- Banners ---
    banner_count = await banner_repo.count()
    if banner_count == 0:
        logger.info("Seeding %d banners...", len(SEED_BANNERS))
        for data in SEED_BANNERS:
            await banner_repo.create(**data)
        logger.info("Banners seeded successfully.")
    else:
        logger.info("Banners already seeded (%d found). Skipping.", banner_count)

    # --- Testimonials ---
    testimonial_count = await testimonial_repo.count()
    if testimonial_count == 0:
        logger.info("Seeding %d testimonials...", len(SEED_TESTIMONIALS))
        for data in SEED_TESTIMONIALS:
            await testimonial_repo.create(**data)
        logger.info("Testimonials seeded successfully.")
    else:
        logger.info(
            "Testimonials already seeded (%d found). Skipping.",
            testimonial_count,
        )

    # --- Site Config ---
    config_count = await config_repo.count()
    if config_count == 0:
        logger.info("Seeding site config...")
        for key, value in SEED_CONFIGS.items():
            await config_repo.set(key, value)
        logger.info("Site config seeded successfully.")
    else:
        logger.info(
            "Site config already seeded (%d found). Skipping.",
            config_count,
        )

    # --- Coupons ---
    coupon_count = await coupon_repo.count()
    if coupon_count == 0:
        logger.info("Seeding %d coupons...", len(SEED_COUPONS))
        for data in SEED_COUPONS:
            await coupon_repo.create(**data)
        logger.info("Coupons seeded successfully.")

    # --- Categories ---
    from app.repositories.category_repository import CategoryRepository
    from app.repositories.faq_repository import FAQRepository

    cat_repo = CategoryRepository(db)
    faq_repo = FAQRepository(db)

    cat_count = await cat_repo.count()
    if cat_count == 0:
        logger.info("Seeding %d categories...", len(SEED_CATEGORIES))
        for data in SEED_CATEGORIES:
            await cat_repo.create(**data)
        logger.info("Categories seeded successfully.")

    # --- FAQs ---
    faq_count = await faq_repo.count()
    if faq_count == 0:
        logger.info("Seeding %d FAQs...", len(SEED_FAQS))
        for data in SEED_FAQS:
            await faq_repo.create(**data)
        logger.info("FAQs seeded successfully.")

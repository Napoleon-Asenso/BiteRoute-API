"""Deterministic and idempotent database seeding script for BiteRoute API.

Usage:
    python scripts/seed.py [--clean]
    python -m scripts.seed [--clean]
"""

import argparse
import hashlib
import random
import sys
import uuid
from decimal import Decimal
from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem
from app.models.restaurant import Restaurant

SEED: int = 42
TOTAL_RESTAURANTS: int = 100
ITEMS_PER_RESTAURANT: int = 10
TOTAL_ORDERS: int = 200

CUISINE_CATEGORIES: list[str] = [
    "Pizza",
    "Sushi",
    "Burgers",
    "Bakery",
    "Vegan",
    "Italian",
    "Mexican",
    "Japanese",
    "American",
    "Mediterranean",
]

ITEM_TEMPLATES: dict[str, list[dict[str, str | int]]] = {
    "Pizza": [
        {"name": "Margherita D.O.P.", "category": "Mains", "price": 1650},
        {"name": "Pepperoni Classico", "category": "Mains", "price": 1850},
        {"name": "Quattro Formaggi", "category": "Mains", "price": 1950},
        {"name": "Truffle Mushroom Pizza", "category": "Mains", "price": 2200},
        {"name": "Garlic Dough Bites", "category": "Appetizers", "price": 750},
        {"name": "Caesar Salad", "category": "Appetizers", "price": 950},
        {"name": "Classic Tiramisu", "category": "Desserts", "price": 850},
        {"name": "Nutella Calzone", "category": "Desserts", "price": 900},
        {"name": "San Pellegrino Limonata", "category": "Beverages", "price": 400},
        {"name": "Acqua Panna Still Water", "category": "Beverages", "price": 350},
    ],
    "Sushi": [
        {"name": "Salmon Nigiri (2pc)", "category": "Mains", "price": 850},
        {"name": "Tuna Sashimi (5pc)", "category": "Mains", "price": 1650},
        {"name": "Dragon Specialty Roll", "category": "Mains", "price": 1750},
        {"name": "Spicy Tuna Crunch Roll", "category": "Mains", "price": 1450},
        {"name": "Steamed Edamame", "category": "Appetizers", "price": 600},
        {"name": "Agedashi Tofu", "category": "Appetizers", "price": 750},
        {"name": "Miso Soup", "category": "Sides", "price": 450},
        {"name": "Green Tea Mochi (3pc)", "category": "Desserts", "price": 700},
        {"name": "Japanese Iced Green Tea", "category": "Beverages", "price": 400},
        {"name": "Ramune Soda", "category": "Beverages", "price": 450},
    ],
    "Burgers": [
        {"name": "Classic Cheeseburger", "category": "Mains", "price": 1350},
        {"name": "Double Bacon Truffle Burger", "category": "Mains", "price": 1850},
        {"name": "Crispy Buttermilk Chicken Sandwich", "category": "Mains", "price": 1500},
        {"name": "Smash Patty Melt", "category": "Mains", "price": 1400},
        {"name": "Truffle Parmesan Fries", "category": "Sides", "price": 750},
        {"name": "Beer Battered Onion Rings", "category": "Sides", "price": 650},
        {"name": "Loaded Cheddar Tots", "category": "Appetizers", "price": 850},
        {"name": "Salted Caramel Milkshake", "category": "Desserts", "price": 750},
        {"name": "Vanilla Bean Shake", "category": "Desserts", "price": 700},
        {"name": "Craft Root Beer", "category": "Beverages", "price": 450},
    ],
    "Bakery": [
        {"name": "Artisan Sourdough Loaf", "category": "Mains", "price": 950},
        {"name": "Prosciutto & Gruyere Baguette", "category": "Mains", "price": 1300},
        {"name": "Almond Croissant", "category": "Bakery", "price": 550},
        {"name": "Pain au Chocolat", "category": "Bakery", "price": 500},
        {"name": "Avocado Tartine", "category": "Mains", "price": 1150},
        {"name": "Cinnamon Brioche Roll", "category": "Bakery", "price": 600},
        {"name": "Lemon Curd Tartlet", "category": "Desserts", "price": 650},
        {"name": "Matcha Scone", "category": "Bakery", "price": 450},
        {"name": "Oat Milk Flat White", "category": "Beverages", "price": 550},
        {"name": "Cold Brew Reserve", "category": "Beverages", "price": 500},
    ],
    "Vegan": [
        {"name": "Truffle Cashew Mac & Cheese", "category": "Mains", "price": 1650},
        {"name": "Smoked Tempeh Bowl", "category": "Mains", "price": 1550},
        {"name": "Crispy Oyster Mushroom Po'Boy", "category": "Mains", "price": 1450},
        {"name": "Rainbow Quinoa Glow Salad", "category": "Mains", "price": 1350},
        {"name": "Buffalo Cauliflower Wings", "category": "Appetizers", "price": 950},
        {"name": "Charred Shishito Peppers", "category": "Sides", "price": 800},
        {"name": "Sweet Potato Hummus Plate", "category": "Appetizers", "price": 850},
        {"name": "Raw Cacao Avocado Tart", "category": "Desserts", "price": 800},
        {"name": "Organic Cold-Pressed Green Juice", "category": "Beverages", "price": 850},
        {"name": "Lavender Kombucha", "category": "Beverages", "price": 600},
    ],
}


def deterministic_uuid(natural_key: str) -> uuid.UUID:
    """Generate a deterministic and valid UUIDv4 identifier from a natural key."""
    digest = hashlib.sha256(natural_key.encode("utf-8")).digest()
    raw = bytearray(digest[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40  # Set version 4
    raw[8] = (raw[8] & 0x3F) | 0x80  # Set variant RFC 4122
    return uuid.UUID(bytes=bytes(raw), version=4)


def slugify(text: str) -> str:
    """Convert string text into a URL-friendly hyphenated slug."""
    clean = "".join(c if c.isalnum() or c.isspace() else "" for c in text.lower())
    return "-".join(clean.split())


def clean_database(session: Session) -> None:
    """Safely delete all existing records in cascading order."""
    print("Purging existing records (--clean requested)...")
    session.query(OrderItem).delete(synchronize_session=False)
    session.query(Order).delete(synchronize_session=False)
    session.query(MenuItem).delete(synchronize_session=False)
    session.query(Restaurant).delete(synchronize_session=False)
    session.commit()
    print("Database cleared.")


def seed_database(clean: bool = False) -> None:
    """Seed the database with deterministic restaurants, menu items, and orders."""
    # Ensure database schema tables exist
    Base.metadata.create_all(bind=engine)

    # Initialize fixed seeds
    random.seed(SEED)
    fake = Faker()
    fake.seed_instance(SEED)

    with Session(engine) as session:
        if clean:
            clean_database(session)

        # Check existing restaurant count
        existing_restaurants_count = session.scalar(select(func.count(Restaurant.id))) or 0
        existing_items_count = session.scalar(select(func.count(MenuItem.id))) or 0
        existing_orders_count = session.scalar(select(func.count(Order.id))) or 0

        if existing_restaurants_count >= TOTAL_RESTAURANTS and not clean:
            print(
                f"Database already seeded ({existing_restaurants_count} restaurants, "
                f"{existing_items_count} menu items, {existing_orders_count} orders). "
                f"Idempotent check passed: 0 duplicate rows created."
            )
            return

        print(f"Beginning deterministic seed (Seed: {SEED})...")

        # Load existing IDs to avoid insertion conflicts
        existing_restaurant_ids: set[uuid.UUID] = set(session.scalars(select(Restaurant.id)).all())
        existing_item_ids: set[uuid.UUID] = set(session.scalars(select(MenuItem.id)).all())
        existing_order_ids: set[uuid.UUID] = set(session.scalars(select(Order.id)).all())

        new_restaurants: list[Restaurant] = []
        new_menu_items: list[MenuItem] = []
        all_created_restaurants: list[Restaurant] = []
        restaurant_menu_map: dict[uuid.UUID, list[MenuItem]] = {}

        # 1. Seed Restaurants
        for i in range(TOTAL_RESTAURANTS):
            cuisine = CUISINE_CATEGORIES[i % len(CUISINE_CATEGORIES)]
            company_name = f"{fake.company()} {cuisine}"
            slug = slugify(f"{company_name}-{i + 1}")
            rest_id = deterministic_uuid(f"restaurant:{slug}")

            # 90% active, 10% inactive
            is_active = i % 10 != 0
            rating = Decimal(f"{(350 + (i * 17 % 145)) / 100:.2f}")
            price_tier = (i % 4) + 1
            delivery_fee_cents = 199 + ((i * 37) % 400)
            delivery_minutes = 20 + ((i * 5) % 45)

            restaurant = Restaurant(
                name=company_name,
                slug=slug,
                description=fake.catch_phrase(),
                cuisine_type=cuisine,
                price_tier=price_tier,
                rating=rating,
                is_active=is_active,
                address_street=fake.street_address(),
                address_city="San Francisco",
                address_postal_code="94103",
                delivery_fee_cents=delivery_fee_cents,
                estimated_delivery_minutes=delivery_minutes,
            )
            restaurant.id = rest_id
            all_created_restaurants.append(restaurant)
            restaurant_menu_map[rest_id] = []

            if rest_id not in existing_restaurant_ids:
                new_restaurants.append(restaurant)

            # 2. Seed Menu Items for this restaurant
            templates = ITEM_TEMPLATES.get(cuisine, ITEM_TEMPLATES["Burgers"])
            for item_idx in range(ITEMS_PER_RESTAURANT):
                template = templates[item_idx % len(templates)]
                item_id = deterministic_uuid(f"menu_item:{slug}:{item_idx + 1}")
                # 90% available, 10% unavailable
                is_available = item_idx % 10 != 9

                item = MenuItem(
                    restaurant_id=rest_id,
                    name=str(template["name"]),
                    description=fake.sentence(nb_words=8),
                    category=str(template["category"]),
                    price_cents=int(template["price"]),
                    is_available=is_available,
                    image_url=f"https://images.biteroute.io/{cuisine.lower()}/{item_idx + 1}.jpg",
                )
                item.id = item_id
                restaurant_menu_map[rest_id].append(item)

                if item_id not in existing_item_ids:
                    new_menu_items.append(item)

        if new_restaurants:
            session.add_all(new_restaurants)
            session.flush()

        if new_menu_items:
            session.add_all(new_menu_items)
            session.flush()

        print(
            f"Seeded {len(new_restaurants)} new restaurants and "
            f"{len(new_menu_items)} new menu items."
        )

        # 3. Seed Orders & Order Items
        statuses = [
            "DELIVERED",
            "OUT_FOR_DELIVERY",
            "PREPARING",
            "CONFIRMED",
            "PENDING",
            "CANCELLED",
        ]
        active_restaurants = [r for r in all_created_restaurants if r.is_active]
        new_orders: list[Order] = []
        new_order_items: list[OrderItem] = []

        for o_idx in range(TOTAL_ORDERS):
            order_id = deterministic_uuid(f"order:{o_idx + 1}")
            if order_id in existing_order_ids:
                continue

            chosen_rest = active_restaurants[o_idx % len(active_restaurants)]
            rest_items = [
                it for it in restaurant_menu_map[chosen_rest.id] if it.is_available
            ] or restaurant_menu_map[chosen_rest.id]

            # Choose 1 to 3 items
            selected_items = rest_items[: max(1, (o_idx % 3) + 1)]
            status = statuses[o_idx % len(statuses)]

            subtotal_cents = 0
            order_item_records: list[OrderItem] = []

            for item_idx, itm in enumerate(selected_items):
                oi_id = deterministic_uuid(f"order_item:{order_id}:{item_idx + 1}")
                qty = 1 if (o_idx + item_idx) % 2 == 0 else 2
                line_total = itm.price_cents * qty
                subtotal_cents += line_total

                oi = OrderItem(
                    order_id=order_id,
                    menu_item_id=itm.id,
                    item_name=itm.name,
                    unit_price_cents=itm.price_cents,
                    quantity=qty,
                    line_total_cents=line_total,
                )
                oi.id = oi_id
                order_item_records.append(oi)

            delivery_fee_cents = chosen_rest.delivery_fee_cents
            tax_cents = round(subtotal_cents * 0.0875)
            total_cents = subtotal_cents + delivery_fee_cents + tax_cents

            order = Order(
                restaurant_id=chosen_rest.id,
                customer_name=fake.name(),
                customer_email=fake.email(),
                customer_phone=fake.phone_number()[:32],
                delivery_address=fake.address().replace("\n", ", "),
                status=status,
                subtotal_cents=subtotal_cents,
                delivery_fee_cents=delivery_fee_cents,
                tax_cents=tax_cents,
                total_cents=total_cents,
                special_instructions="Leave with concierge." if o_idx % 4 == 0 else None,
            )
            order.id = order_id
            new_orders.append(order)
            new_order_items.extend(order_item_records)

        if new_orders:
            session.add_all(new_orders)
            session.flush()

        if new_order_items:
            session.add_all(new_order_items)
            session.flush()

        session.commit()

        # Final counts
        final_restaurants = session.scalar(select(func.count(Restaurant.id)))
        final_items = session.scalar(select(func.count(MenuItem.id)))
        final_orders = session.scalar(select(func.count(Order.id)))
        final_order_items = session.scalar(select(func.count(OrderItem.id)))

        print(
            f"Seeding completed successfully: {final_restaurants} restaurants, "
            f"{final_items} menu items, {final_orders} orders, "
            f"{final_order_items} order items."
        )


def main() -> None:
    """CLI entrypoint for database seeding."""
    parser = argparse.ArgumentParser(description="Deterministic seed script for BiteRoute API.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Purge all tables prior to re-seeding.",
    )
    args = parser.parse_args()
    seed_database(clean=args.clean)


if __name__ == "__main__":
    main()

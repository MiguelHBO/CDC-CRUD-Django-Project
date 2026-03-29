"""
management/commands/seed.py
---------------------------
Populates the database with demo data so a recruiter can open the app
and immediately see the CRUD + audit pipeline in action.

Run: python manage.py seed
"""
import random
from django.core.management.base import BaseCommand
from ecommerce.models import Product, Order

PRODUCTS = [
    ("Wireless Headphones", "ELEC-001", 129.99, 45, "Electronics"),
    ("Mechanical Keyboard", "ELEC-002", 89.99, 30, "Electronics"),
    ("USB-C Hub 7-in-1",   "ELEC-003", 49.99, 80, "Electronics"),
    ("Standing Desk Mat",  "FURN-001", 34.99, 60, "Furniture"),
    ("Ergonomic Chair",    "FURN-002", 299.99, 12, "Furniture"),
    ("Notebook A5 Pack",   "STAT-001", 14.99, 200, "Stationery"),
    ("Ballpoint Pens 10x", "STAT-002", 7.99, 350, "Stationery"),
    ("Cable Organizer",    "ELEC-004", 19.99, 95, "Electronics"),
]

CUSTOMERS = [
    ("Alice Johnson", "alice@example.com"),
    ("Bob Smith",     "bob@example.com"),
    ("Carol White",   "carol@example.com"),
    ("David Brown",   "david@example.com"),
    ("Eva Martinez",  "eva@example.com"),
]

STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]


class Command(BaseCommand):
    help = "Seed database with demo products and orders"

    def handle(self, *args, **options):
        self.stdout.write("Seeding products…")
        products = []
        for name, sku, price, stock, cat in PRODUCTS:
            p, created = Product.objects.get_or_create(
                sku=sku,
                defaults={"name": name, "price": price, "stock": stock, "category": cat},
            )
            products.append(p)
            if created:
                self.stdout.write(f"  + {p.name}")

        self.stdout.write("Seeding orders…")
        if Order.objects.count() == 0:
            for i in range(12):
                product = random.choice(products)
                customer = random.choice(CUSTOMERS)
                Order.objects.create(
                    product=product,
                    customer_name=customer[0],
                    customer_email=customer[1],
                    quantity=random.randint(1, 5),
                    unit_price=product.price,
                    status=random.choice(STATUSES),
                )
            self.stdout.write("  + 12 orders created")

        self.stdout.write("Simulating a few updates to populate audit trail…")
        if products:
            p = products[0]
            old_stock = p.stock
            p.stock = old_stock + 10
            p.save()
            p.stock = old_stock
            p.save()

        orders = list(Order.objects.filter(status="pending")[:2])
        for o in orders:
            o.status = "processing"
            o.save()

        self.stdout.write(self.style.SUCCESS(
            "\nDone! Open http://localhost:8000 to explore the demo."
        ))

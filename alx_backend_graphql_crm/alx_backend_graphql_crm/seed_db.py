import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql_crm.settings")
django.setup()

from crm.models import Customer, Product

Customer.objects.create(name="Test User", email="test@example.com", phone="+1234567890")
Product.objects.create(name="Phone", price=199.99, stock=20)
Product.objects.create(name="Tablet", price=299.99, stock=15)

print("Database seeded successfully")

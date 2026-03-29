from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("sku", models.CharField(max_length=50, unique=True)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("stock", models.PositiveIntegerField(default=0)),
                ("category", models.CharField(blank=True, max_length=100)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_name", models.CharField(max_length=200)),
                ("customer_email", models.EmailField(max_length=254)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("processing", "Processing"),
                        ("shipped", "Shipped"),
                        ("delivered", "Delivered"),
                        ("cancelled", "Cancelled"),
                    ],
                    default="pending",
                    max_length=20,
                )),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="orders",
                    to="ecommerce.product",
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

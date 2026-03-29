from django import forms
from ecommerce.models import Product, Order


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "sku", "price", "stock", "category", "active"]
        widgets = {
            "name":     forms.TextInput(attrs={"class": "form-input", "placeholder": "Product name"}),
            "sku":      forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. PROD-001"}),
            "price":    forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "stock":    forms.NumberInput(attrs={"class": "form-input"}),
            "category": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Electronics"}),
            "active":   forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["product", "customer_name", "customer_email", "quantity", "status", "notes"]
        widgets = {
            "product":        forms.Select(attrs={"class": "form-select"}),
            "customer_name":  forms.TextInput(attrs={"class": "form-input"}),
            "customer_email": forms.EmailInput(attrs={"class": "form-input"}),
            "quantity":       forms.NumberInput(attrs={"class": "form-input", "min": "1"}),
            "status":         forms.Select(attrs={"class": "form-select"}),
            "notes":          forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

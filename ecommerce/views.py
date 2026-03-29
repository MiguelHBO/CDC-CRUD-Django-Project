from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from ecommerce.models import Product, Order
from ecommerce.forms import ProductForm, OrderForm


# ── Products ──────────────────────────────────────────────────────────────────

def product_list(request):
    q = request.GET.get("q", "").strip()
    products = Product.objects.all()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(category__icontains=q))
    return render(request, "ecommerce/product_list.html", {"products": products, "q": q})


def product_create(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        product = form.save()
        messages.success(request, f'Product "{product.name}" created.')
        return redirect("product_list")
    return render(request, "ecommerce/product_form.html", {"form": form, "title": "New Product"})


def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        form.save()
        messages.success(request, f'Product "{product.name}" updated.')
        return redirect("product_list")
    return render(request, "ecommerce/product_form.html", {"form": form, "title": "Edit Product", "object": product})


def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
        return redirect("product_list")
    return render(request, "ecommerce/confirm_delete.html", {"object": product, "type": "Product"})


# ── Orders ────────────────────────────────────────────────────────────────────

def order_list(request):
    q = request.GET.get("q", "").strip()
    orders = Order.objects.select_related("product").all()
    if q:
        orders = orders.filter(
            Q(customer_name__icontains=q) | Q(customer_email__icontains=q) | Q(product__name__icontains=q)
        )
    return render(request, "ecommerce/order_list.html", {"orders": orders, "q": q})


def order_create(request):
    form = OrderForm(request.POST or None)
    if form.is_valid():
        order = form.save(commit=False)
        order.unit_price = order.product.price
        order.save()
        messages.success(request, f"Order #{order.pk} created.")
        return redirect("order_list")
    return render(request, "ecommerce/order_form.html", {"form": form, "title": "New Order"})


def order_edit(request, pk):
    order = get_object_or_404(Order, pk=pk)
    form = OrderForm(request.POST or None, instance=order)
    if form.is_valid():
        form.save()
        messages.success(request, f"Order #{order.pk} updated.")
        return redirect("order_list")
    return render(request, "ecommerce/order_form.html", {"form": form, "title": "Edit Order", "object": order})


def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        oid = order.pk
        order.delete()
        messages.success(request, f"Order #{oid} deleted.")
        return redirect("order_list")
    return render(request, "ecommerce/confirm_delete.html", {"object": order, "type": "Order"})

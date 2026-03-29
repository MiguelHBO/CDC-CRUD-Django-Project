from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "audit"
    verbose_name = "CDC Audit"

    def ready(self):
        """Wire up Django signals to the CDC handlers once the app is loaded."""
        from django.db.models.signals import pre_save, post_save, post_delete
        from ecommerce.models import Product, Order
        from audit.cdc import handle_pre_save, handle_post_save, handle_post_delete

        for model in (Product, Order):
            pre_save.connect(handle_pre_save, sender=model, weak=False)
            post_save.connect(handle_post_save, sender=model, weak=False)
            post_delete.connect(handle_post_delete, sender=model, weak=False)

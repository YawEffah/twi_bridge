from django.db import models
from django.contrib.auth.models import User

class TranslationHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    source_text = models.TextField()
    translated_text = models.TextField()
    direction = models.CharField(max_length=10)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_str = self.user.username if self.user else f"Guest ({self.ip_address})"
        return f"{user_str} - {self.source_text[:20]}"


class RateLimitSetting(models.Model):
    max_requests = models.PositiveIntegerField(default=50, help_text="Number of requests allowed")
    window_hours = models.PositiveIntegerField(default=1, help_text="Time window in hours")
    enabled = models.BooleanField(default=True, help_text="Enable or disable rate limiting")

    class Meta:
        verbose_name = "Rate Limit Setting"
        verbose_name_plural = "Rate Limit Settings"

    def __str__(self):
        return f"Limit: {self.max_requests} reqs / {self.window_hours}h ({'Enabled' if self.enabled else 'Disabled'})"

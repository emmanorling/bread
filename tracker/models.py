from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class BreadMachine(models.Model):
    name = models.CharField(max_length=100)  # e.g., "Kitchen Panasonic"
    
    def __str__(self):
        return self.name

class Loaf(models.Model):
    machine = models.ForeignKey(BreadMachine, on_delete=models.CASCADE, related_name='loaves')
    bread_type = models.CharField(max_length=100)  # e.g., "Sourdough"
    started_at = models.DateTimeField(default=timezone.now)
    ready_at = models.DateTimeField()
    
    @property
    def is_active(self):
        return self.ready_at > timezone.now()

    class Meta:
        verbose_name = "Loaf"
        verbose_name_plural = "Loaves"  # <-- Fixes "Loafs" -> "Loaves"

    def __str__(self):
        return f"{self.bread_type} in {self.machine.name}"

class Comment(models.Model):
    loaf = models.ForeignKey('Loaf', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loaf_comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.loaf}"

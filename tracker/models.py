from django.db import models
from django.utils import timezone

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

    def __str__(self):
        return f"{self.bread_type} in {self.machine.name}"


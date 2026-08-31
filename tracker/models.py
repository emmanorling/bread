### models.ps - all the models in one handy spot:
###    * BreadMachine
###    * Loaf
###    * Comment
###    * SiteSettings

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from PIL import Image

# BreadMachine has a name (which will be displayed on the dashboard),
# an optional image (ideally, a photo of said machine), and
# a list of notes (can be empty)
class BreadMachine(models.Model):
    name = models.CharField(max_length=100)  # e.g., "Kitchen Panasonic"
    image = models.ImageField(upload_to='machines/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Save the model first so the file exists on disk
        super().save(*args, **kwargs)

        # If an image was uploaded, check its dimensions
        # Only want a small image on the display, so don't
        # save a large one!
        if self.image:
            img_path = self.image.path
            img = Image.open(img_path)

            # Define max dimensions (Width, Height)
            max_size = (200, 200)

            # Resize if either width or height exceeds the limit
            if img.width > 200 or img.height > 200:
                # thumbnail() resizes in-place while keeping the original aspect ratio
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(self.image.path)

# Loaf records which machine it's baked in
# what type of bread it is
# what time it was started
# what time it is/was ready
# who entered this information
# whether or not the loaf is still in the machine
class Loaf(models.Model):
    machine = models.ForeignKey(BreadMachine, on_delete=models.CASCADE, related_name='loaves')
    bread_type = models.CharField(max_length=100)  # e.g., "Sourdough"
    started_at = models.DateTimeField(default=timezone.now)
    ready_at = models.DateTimeField()
    STATUS_CHOICES = [
        ('baking_in_machine', 'Baking in Machine'),
        ('proving', 'Proving'),
        ('baking_in_oven', 'Baking in Oven'),
        ('finished', 'Finished'),
    ]

    # Track the baker who created the loaf
    # Use this to warn others if they go to edit it
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='loaves'
    )

    is_removed = models.BooleanField(
        default=False, 
        help_text="Designates whether the bread has been taken out of the machine."
    )

    is_dough_only = models.BooleanField(
        default=False, 
        verbose_name="Dough only (requires proving & oven bake)"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='baking_in_machine'
    )

    # Timestamps for stage tracking (for dough only in machine)
    removed_from_machine_at = models.DateTimeField(null=True, blank=True)
    started_oven_bake_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    @property
    def minutes_proving(self):
        if self.removed_from_machine_at:
            # Prefer started_oven_bake_at, then finished_at, then fallback to timezone.now()
            end_time = self.started_oven_bake_at or self.finished_at or timezone.now()
            delta = end_time - self.removed_from_machine_at
            return int(delta.total_seconds() // 60)
        return 0

    @property
    def minutes_baking(self):
        if self.started_oven_bake_at:
            # Freeze calculation at finished_at if available instead of calling timezone.now()
            end_time = self.finished_at or timezone.now()
            delta = end_time - self.started_oven_bake_at
            return int(delta.total_seconds() // 60)
        return 0

    @property
    def minutes_until_ready(self):
        if self.ready_at and self.ready_at > timezone.now():
            delta = self.ready_at - timezone.now()
            return int(delta.total_seconds() // 60)
        return 0
        
    @property
    def is_active(self):
        return self.ready_at > timezone.now()

    @property
    def is_finished(self):
        return timezone.now() >= self.ready_at

    @property
    def completed_at(self):
        """
        Returns the final completed timestamp.
        For dough-only loaves with a recorded completion timestamp, return finished_at.
        Otherwise, return ready_at.
        """
        # Use stored finished_at timestamp when present
        if self.is_dough_only and self.finished_at:
            return self.finished_at
        return self.ready_at

    class Meta:
        verbose_name = "Loaf"
        verbose_name_plural = "Loaves"  # <-- Fixes "Loafs" -> "Loaves"

    def __str__(self):
        return f"{self.bread_type} in {self.machine.name}"

# Comment records which loaf it's associated with
# who wrote the comment
# what the comment was
# when the comment was created
class Comment(models.Model):
    loaf = models.ForeignKey('Loaf', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loaf_comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.loaf}"


class SiteSetting(models.Model):
    show_dough_section = models.BooleanField(
        default=True,
        verbose_name="Show 'Dough in Progress' section on dashboard"
    )

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Global Site Settings"

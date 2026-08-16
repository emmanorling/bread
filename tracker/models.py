### models.ps - all the models in one handy spot:
###    * BreadMachine
###    * Loaf
###    * Comment

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
class Loaf(models.Model):
    machine = models.ForeignKey(BreadMachine, on_delete=models.CASCADE, related_name='loaves')
    bread_type = models.CharField(max_length=100)  # e.g., "Sourdough"
    started_at = models.DateTimeField(default=timezone.now)
    ready_at = models.DateTimeField()

    # Track the baker who created the loaf
    # Use this to warn others if they go to edit it
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='loaves'
    )
    
    @property
    def is_active(self):
        return self.ready_at > timezone.now()

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

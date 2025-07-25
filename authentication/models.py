from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    """
    Model representing a user profile.
    
    Attributes:
        user (User): One-to-one link to Django User model.
        profile_pic (ImageField): User's profile picture.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True, help_text="User's profile picture")

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'

    def __str__(self):
        return f"{self.user.username}'s Profile"
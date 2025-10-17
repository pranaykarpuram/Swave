from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import json


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser"""
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # User preferences
    display_name = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.username or self.email


class ProviderToken(models.Model):
    """Store OAuth tokens for music providers (Spotify, Apple Music, etc.)"""
    PROVIDER_CHOICES = [
        ('spotify', 'Spotify'),
        ('apple', 'Apple Music'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provider_tokens')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    
    # OAuth tokens
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    token_type = models.CharField(max_length=50, default='Bearer')
    expires_at = models.DateTimeField()
    
    # Provider-specific data
    provider_user_id = models.CharField(max_length=100, blank=True)
    scope = models.TextField(blank=True)  # JSON string of granted scopes
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'provider']
    
    def is_expired(self):
        return timezone.now() >= self.expires_at
    
    def get_scopes(self):
        """Parse scope JSON string into list"""
        if not self.scope:
            return []
        try:
            return json.loads(self.scope)
        except json.JSONDecodeError:
            return []
    
    def set_scopes(self, scopes):
        """Set scopes as JSON string"""
        self.scope = json.dumps(scopes)
    
    def __str__(self):
        return f"{self.user.username} - {self.provider}"


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Music preferences
    favorite_genres = models.JSONField(default=list, blank=True)
    favorite_artists = models.JSONField(default=list, blank=True)
    
    # App settings
    auto_play_previews = models.BooleanField(default=True)
    swipe_sensitivity = models.FloatField(default=0.5)  # 0.0 to 1.0
    
    # Statistics
    total_swipes = models.PositiveIntegerField(default=0)
    total_likes = models.PositiveIntegerField(default=0)
    total_rejects = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

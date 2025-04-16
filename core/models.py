from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    in_game_currency = models.PositiveIntegerField(default=settings.INITIAL_USER_CURRENCY)
    last_login_bonus = models.DateField(null=True, blank=True, help_text="The date the user last received a daily login bonus.")

    def __str__(self):
        return f"{self.user.username}'s Profile"

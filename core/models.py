from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class Pokemon(models.Model):
    pokedex_id = models.IntegerField(unique=True, primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    type1 = models.CharField(max_length=50)
    type2 = models.CharField(max_length=50, blank=True, null=True)
    RARITY_CHOICES = [
        ('Common', 'Common'),
        ('Uncommon', 'Uncommon'),
        ('Rare', 'Rare'),
        ('Mythic', 'Mythic'),
    ]
    rarity = models.CharField(max_length=10, choices=RARITY_CHOICES, default='Common')
    image_url = models.URLField(max_length=300, blank=True, null=True)

    def __str__(self):
        return f"#{self.pokedex_id}: {self.name.capitalize()}"

    class Meta:
        ordering = ['pokedex_id']
        verbose_name_plural = "Pokemon"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    in_game_currency = models.PositiveIntegerField(default=settings.INITIAL_USER_CURRENCY)
    last_login_bonus = models.DateField(null=True, blank=True, help_text="The date the user last received a daily login bonus.")

    def __str__(self):
        return f"{self.user.username}'s Profile"



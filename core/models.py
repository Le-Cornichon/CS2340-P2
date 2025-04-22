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

class TransactionHistory(models.Model):
    TRANSACTION_MARKET = 'Market Purchase'
    TRANSACTION_TRADE = 'Trade'
    TRANSACTION_DAILY_REWARD = 'Daily Reward'
    TRANSACTION_PACK_PURCHASE = 'Pack Purchase'
    TRANSACTION_CURRENCY_PURCHASE = 'Currency Purchase'
    TRANSACTION_TYPES = [
        (TRANSACTION_MARKET, 'Market Purchase'),
        (TRANSACTION_TRADE, 'Trade'),
        (TRANSACTION_DAILY_REWARD, 'Daily Reward'),
        (TRANSACTION_PACK_PURCHASE, 'Pack Purchase'),
        (TRANSACTION_CURRENCY_PURCHASE, 'Currency Purchase'),
    ]

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(default=timezone.now)
    user_profile = models.ForeignKey(UserProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    seller = models.ForeignKey(UserProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name='sales')
    collection_item = models.ForeignKey(CollectionItem, null=True, blank=True, on_delete=models.SET_NULL)
    pokemon = models.ForeignKey(Pokemon, null=True, blank=True, on_delete=models.SET_NULL, help_text="Primary Pokemon species involved (if applicable)")
    price = models.PositiveIntegerField(null=True, blank=True)
    trade_offer = models.ForeignKey(TradeOffer, null=True, blank=True, on_delete=models.SET_NULL, related_name='history_entry')
    pack_purchased = models.ForeignKey(PokemonPack, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        if self.transaction_type == self.TRANSACTION_TRADE and self.trade_offer:
            return f"Trade Completed: Offer {self.trade_offer.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
        elif self.transaction_type == self.TRANSACTION_MARKET and self.pokemon and self.user_profile:
            return f"Market Purchase by {self.user_profile.user.username}: {self.pokemon.name.capitalize()} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
        elif self.transaction_type == self.TRANSACTION_PACK_PURCHASE and self.pack_purchased and self.user_profile:
             return f"Pack Purchase by {self.user_profile.user.username}: {self.pack_purchased.name} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
        elif self.transaction_type == self.TRANSACTION_DAILY_REWARD and self.user_profile:
            return f"Daily Reward for {self.user_profile.user.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
        else:
            return f"{self.transaction_type} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Transaction Histories"

class Notification(models.Model):
    recipient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    related_url = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Notification for {self.recipient.user.username} ({'Read' if self.is_read else 'Unread'})"

    class Meta:
        ordering = ['-timestamp']


class PackRarityOdds(models.Model):
    pack = models.ForeignKey(PokemonPack, on_delete=models.CASCADE, related_name='rarity_odds')
    rarity = models.CharField(max_length=10, choices=Pokemon.RARITY_CHOICES)
    probability = models.FloatField(help_text="Probability (0.0 to 1.0) of drawing this rarity. Sum for a pack should ideally be 1.0")

    def __str__(self):
        return f"{self.pack.name} - {self.rarity}: {self.probability:.2%}"

    class Meta:
        unique_together = ('pack', 'rarity')
        ordering = ['pack', 'rarity']
        verbose_name_plural = "Pack Rarity Odds"



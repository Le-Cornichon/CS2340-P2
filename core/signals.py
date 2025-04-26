from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
import random

from .models import UserProfile, Pokemon, CollectionItem, TradeOffer, MarketplaceListing, Notification

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        profile = UserProfile.objects.create(user=instance)
        print(f"Created profile for {instance.username} with {profile.in_game_currency} currency.")

        try:
            all_pokemon = list(Pokemon.objects.all())
            if len(all_pokemon) >= settings.STARTER_POKEMON_COUNT:
                common_uncommon = list(Pokemon.objects.filter(rarity__in=['Common', 'Uncommon']))
                if len(common_uncommon) >= settings.STARTER_POKEMON_COUNT:
                   starters_pool = common_uncommon
                else:
                   starters_pool = all_pokemon

                starter_pokemon_species = random.sample(starters_pool, settings.STARTER_POKEMON_COUNT)

                for species in starter_pokemon_species:
                    CollectionItem.objects.create(owner=profile, pokemon=species)
                    print(f"Assigned {species.name.capitalize()} to {instance.username}")
            else:
                print(f"Warning: Not enough Pokémon species ({len(all_pokemon)}) in DB to assign {settings.STARTER_POKEMON_COUNT} starters.")

        except Pokemon.DoesNotExist:
            print("Warning: Pokemon table seems empty. Cannot assign starter Pokemon.")
        except Exception as e:
            print(f"Error assigning starter Pokemon to {instance.username}: {e}")

@receiver(post_save, sender=TradeOffer)
def notify_trade_offer_update(sender, instance, created, **kwargs):
    recipient = None
    message = None
    related_url = reverse('core:view_trade_offer', args=[instance.id])

    if created and instance.status == TradeOffer.STATUS_PENDING:
        recipient = instance.receiver
        sender_name = instance.sender.user.username
        message = f"You have received a new trade offer from {sender_name} for {instance.requested_pokemon.name.capitalize()}."
    elif not created:
        if instance.status == TradeOffer.STATUS_ACCEPTED:
            recipient = instance.sender
            receiver_name = instance.receiver.user.username
            message = f"Your trade offer with {receiver_name} for {instance.requested_pokemon.name.capitalize()} has been accepted!"
        elif instance.status == TradeOffer.STATUS_REJECTED:
             recipient = instance.sender
             receiver_name = instance.receiver.user.username
             message = f"Your trade offer with {receiver_name} for {instance.requested_pokemon.name.capitalize()} was rejected."
        elif instance.status == TradeOffer.STATUS_CANCELLED:
             recipient = instance.receiver
             sender_name = instance.sender.user.username
             message = f"The trade offer from {sender_name} for {instance.requested_pokemon.name.capitalize()} was cancelled."

    if recipient and message:
        try:
            Notification.objects.create(
                recipient=recipient,
                message=message,
                related_url=related_url
            )
            print(f"Notification created for {recipient.user.username}: {message}")
        except Exception as e:
             print(f"Error creating trade notification: {e}")


@receiver(post_save, sender=MarketplaceListing)
def notify_marketplace_update(sender, instance, created, **kwargs):
    """Send notification when a marketplace item is sold."""
    recipient = None
    message = None
    related_url = reverse('core:view_listing_detail', args=[instance.id])

    if not created and instance.status == MarketplaceListing.STATUS_SOLD:
        recipient = instance.seller
        item_name = instance.item.pokemon.name.capitalize()
        price = instance.price
        message = f"Your {item_name} has been sold on the marketplace for {price} Coins!"

    if recipient and message:
        try:
            Notification.objects.create(
                recipient=recipient,
                message=message,
                related_url=related_url
            )
            print(f"Notification created for {recipient.user.username}: {message}")
        except Exception as e:
             print(f"Error creating marketplace notification: {e}")

from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from .models import UserProfile, Notification, TransactionHistory
import logging 

logger = logging.getLogger(__name__)

class DailyLoginBonusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            try:
                profile = UserProfile.objects.select_related('user').select_for_update().get(user=request.user)
                today = timezone.localdate()

                if profile.last_login_bonus is None or profile.last_login_bonus < today:
                    reward_amount = settings.DAILY_LOGIN_REWARD
                    with transaction.atomic():
                        profile_in_txn = UserProfile.objects.select_for_update().get(user=request.user)
                        profile_in_txn.in_game_currency += reward_amount
                        profile_in_txn.last_login_bonus = today
                        profile_in_txn.save()

                        try:
                            TransactionHistory.objects.create(
                                transaction_type=TransactionHistory.TRANSACTION_DAILY_REWARD,
                                user_profile=profile_in_txn,
                                price=reward_amount,
                                timestamp=timezone.now()
                            )
                        except Exception as hist_e:
                            logger.error(f"Failed to create TransactionHistory for daily bonus - User: {profile_in_txn.user.username}, Error: {hist_e}")

                        try:
                            Notification.objects.create(
                                recipient=profile_in_txn,
                                message=f"You received your daily login bonus of {reward_amount} Coins!",
                            )
                        except Exception as notif_e:
                            logger.error(f"Failed to create Notification for daily bonus - User: {profile_in_txn.user.username}, Error: {notif_e}")

                    messages.success(request, f"Welcome back! You received your daily login bonus of {reward_amount} Coins.")

            except UserProfile.DoesNotExist:
                pass
            except Exception as e:
                logger.error(f"Error processing daily bonus middleware for {request.user.username}: {e}")
                pass 

        response = self.get_response(request)
        return response
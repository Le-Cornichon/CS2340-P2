from .models import Notification, TradingEvent

def unread_notifications_count(request):
    """Adds the count of unread notifications to the context for logged-in users."""
    count = 0
    if request.user.is_authenticated:
        try:
            profile = getattr(request.user, 'profile', None)
            if profile:
                 count = Notification.objects.filter(recipient=profile, is_read=False).count()
        except Exception:
            count = 0
    return {'unread_notifications_count': count}


def active_trading_events(request):
    """Adds currently active trading events to the template context."""
    active_events = TradingEvent.objects.get_active_events()
    first_active_event = active_events.first()
    return {'active_event': first_active_event}
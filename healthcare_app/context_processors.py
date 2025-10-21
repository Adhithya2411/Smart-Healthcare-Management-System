from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(is_read=False)
        unread_count = unread_notifications.count()
        return {
            'unread_notifications': unread_notifications,
            'unread_count': unread_count,
        }
    return {}
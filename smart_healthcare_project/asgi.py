# In smart_healthcare_project/asgi.py

import os
from django.core.asgi import get_asgi_application

# Set the environment variable for Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_healthcare_project.settings')

# Initialize Django ASGI application early to ensure the AppRegistry is populated
django_asgi_app = get_asgi_application()

# Now that Django is initialized, we can safely import our Channels components
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import healthcare_app.routing

application = ProtocolTypeRouter({
    # Use the initialized Django application for all standard HTTP requests
    "http": django_asgi_app,
    
    # Use our custom routing for WebSocket connections
    "websocket": AuthMiddlewareStack(
        URLRouter(
            healthcare_app.routing.websocket_urlpatterns
        )
    ),
})
"""
Keeps urls for viewsets related to authentication, user
"""
from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from apps.auth_.views import (UserViewSet, ActivationViewSet,
                              TokenView, RefreshTokenView)
from apps.auth_.views.user import UserDetail

jwt_token = TokenView.as_view()
refresh_jwt_token = RefreshTokenView.as_view()

app_name = 'auth_'

urlpatterns = [
    url(r'^api-token-auth/', jwt_token),
    url(r'^api-token-refresh/', refresh_jwt_token),
    url(r'^user/info/(?P<code>[\w-]+)', UserDetail.as_view()),
]

router = DefaultRouter()
router.register(r'users', UserViewSet, base_name='user')
router.register(r'activations', ActivationViewSet, base_name='activation')
urlpatterns += router.urls

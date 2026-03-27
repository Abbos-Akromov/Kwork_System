from django.contrib.auth.backends import ModelBackend
from Client.models import User


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get('email')
        if not email:
            return None
        try:
            user = User.objects.get(email=email)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            return None

    def user_can_authenticate(self, user):
        if user.is_blocked:
            return False
        return super().user_can_authenticate(user)
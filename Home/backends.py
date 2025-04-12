from django.contrib.auth.backends import ModelBackend
from .models import EmployeeSignup

class EmployeeSignupBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = EmployeeSignup.objects.get(email=email)
        except EmployeeSignup.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

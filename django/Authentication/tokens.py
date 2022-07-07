from django.contrib.auth.tokens import PasswordResetTokenGenerator
# pip install django-utils-six
from django.utils import six

"""
Here is to generate a hash token for activating accounts
"""


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
                six.text_type(user.pk) + six.text_type(timestamp) +
                six.text_type(user.profile.signup_confirmation)
        )


activation_token = AccountActivationTokenGenerator()

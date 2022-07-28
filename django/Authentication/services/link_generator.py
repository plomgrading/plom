from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def generate_link(request, user):
    http_protocol = 'http://'
    domain = get_current_site(request).domain
    url_path = '/reset/'
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    forward_slash = '/'
    link = http_protocol + domain + url_path + uid + forward_slash + token
    return link

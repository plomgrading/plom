# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.contrib.auth.models import User, Group
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from random_username.generate import generate_username


class AuthenticationServices:
    @transaction.atomic
    def generate_list_of_basic_usernames(self, group_name, num_users_wanted):
        user_list = []
        username_number = 0

        while len(user_list) < num_users_wanted:
            username_number += 1
            try:
                user = self.create_user_and_add_to_group(
                    username=group_name.capitalize() + str(username_number),
                    group_name=group_name,
                )
                user_list.append(user)
            except:
                pass

        return user_list

    @transaction.atomic
    def create_user_and_add_to_group(self, username, group_name):
        group = Group.objects.get(name=group_name)
        User.objects.create_user(
            username=username, email=None, password=None
        ).groups.add(group)
        user = User.objects.get(username=username)
        user.is_active = False
        user.save()

        return user.username

    def generate_list_of_funky_usernames(self, group_name, num_users_wanted):
        funky_username_list = generate_username(num_users_wanted)
        user_list = []
        for username in funky_username_list:
            new_user = self.check_and_create_funky_usernames(
                username=username, group_name=group_name
            )
            user_list.append(new_user)
        return user_list

    def check_and_create_funky_usernames(self, username, group_name):
        if User.objects.filter(username=username).exists():
            new_username = generate_username(1)
            return self.check_and_create_funky_usernames(
                username=new_username, group_name=group_name
            )
        else:
            user = self.create_user_and_add_to_group(
                username=username, group_name=group_name
            )
            return user

    @transaction.atomic
    def generate_password_reset_links_dict(self, request, username_list):
        # change this when plom_server is deploy
        http_protocol = "http://"
        domain = get_current_site(request).domain
        url_path = "/reset/"
        forward_slash = "/"
        links_dict = {}
        for username in username_list:
            user = User.objects.get(username=username)
            uid = uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = http_protocol + domain + url_path + uid + forward_slash + token
            links_dict[username] = link

        return links_dict

    @transaction.atomic
    def generate_link(request, user):
        http_protocol = "http://"
        domain = get_current_site(request).domain
        url_path = "/reset/"
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        forward_slash = "/"
        link = http_protocol + domain + url_path + uid + forward_slash + token
        return link

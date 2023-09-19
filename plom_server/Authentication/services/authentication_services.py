# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.contrib.auth.models import User, Group
from django.db import transaction
from random_username.generate import generate_username


class AuthenticationServices:
    def generate_list_of_basic_usernames(self, group_name, num_users):
        user_list = []
        if group_name == 'scanner':
            for indx in range(1, num_users + 1):
                scanner_name = "Scanner" + str(indx)
                new_user = self.check_and_create_basic_usernames(username=scanner_name, indx=indx, group_name=group_name)
                user_list.append(new_user)
        elif group_name == 'marker':
            pass
        
        return user_list
    
    def check_and_create_basic_usernames(self, username, indx, group_name):
        
        if User.objects.filter(username=username).exists():
            new_indx = indx + 1
            new_basic_username = group_name.capitalize() + str(new_indx)
            return self.check_and_create_basic_usernames(username=new_basic_username, indx=new_indx, group_name=group_name)
        else:
            user = self.create_user_and_add_to_group(username=username, group_name=group_name)
            return user
        
    @transaction.atomic
    def create_user_and_add_to_group(self, username, group_name):
        group = Group.objects.get(name=group_name)
        User.objects.create_user(username=username, email=None, password=None).groups.add(group)
        user = User.objects.get(username=username)
        user.is_active = False
        user.save()

        return user.username
    
    def generate_list_of_funky_usernames(self, num_users):
        return generate_username(num_users)

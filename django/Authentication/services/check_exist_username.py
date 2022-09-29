from random_username.generate import generate_username


def check_username(username, exist_list, new_list) -> str:
    if username not in exist_list + new_list:
        return username
    else:
        username = generate_username()
        username = "".join(username)
        return check_username(username, exist_list, new_list)

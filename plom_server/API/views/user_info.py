from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status
from plom_server.UserManagement.services import get_users_groups_info


# GET /info/users/
class UsersInfo(APIView):
    def get(self, request: Request) -> Response:
        """Get a dictionary mapping all users' username to their groups."""
        userInfo = get_users_groups_info()
        return Response(userInfo, status=status.HTTP_200_OK)

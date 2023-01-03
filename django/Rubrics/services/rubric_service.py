from django.contrib.auth.models import User

from Rubrics.serializers import RubricSerializer


class RubricService:
    """
    Class to encapsulate functions for creating and modifying rubrics.
    """

    def create_rubric(self, rubric_data):
        """
        Create a rubric using data submitted by a marker.

        Args:
            rubric_data: (dict) data for a rubric submitted by a web request.

        Returns:
            Rubric: the created and saved rubric instance.
        """

        username = rubric_data.pop("username")
        user = User.objects.get(username=username)
        rubric_data["user"] = user.pk

        serializer = RubricSerializer(data=rubric_data)
        serializer.is_valid()
        print(serializer.errors)
        serializer.save()

        rubric = serializer.instance
        return rubric

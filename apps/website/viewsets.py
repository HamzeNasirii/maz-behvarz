from rest_framework import permissions, viewsets

from .models import MembershipApplication
from .serializers import MembershipApplicationCreateSerializer


class MembershipApplicationViewSet(viewsets.mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    فقط create — این endpoint عمومی است (بدون نیاز به احراز هویت)،
    دقیقاً معادل فرم HTML درخواست عضویت در گام ۱۲.
    """

    queryset = MembershipApplication.objects.all()
    serializer_class = MembershipApplicationCreateSerializer
    permission_classes = [permissions.AllowAny]
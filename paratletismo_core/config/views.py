from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Discipline, Sex, Category, FunctionalClassification, EventType
from .serializers import DisciplineSerializer, SexSerializer, CategorySerializer, FunctionalClassificationSerializer, EventTypeSerializer
from paratletismo_core.users.permissions import IsSuperAdmin


class PublicListMixin:
    pagination_class = None

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsSuperAdmin()]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DisciplineView(PublicListMixin, generics.ListCreateAPIView):
    serializer_class = DisciplineSerializer
    queryset = Discipline.objects.all()


class DisciplineDetailView(PublicListMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DisciplineSerializer
    queryset = Discipline.objects.all()


class SexView(PublicListMixin, generics.ListCreateAPIView):
    serializer_class = SexSerializer
    queryset = Sex.objects.all()


class SexDetailView(PublicListMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SexSerializer
    queryset = Sex.objects.all()


class CategoryView(PublicListMixin, generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


class CategoryDetailView(PublicListMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


class FunctionalClassificationView(PublicListMixin, generics.ListCreateAPIView):
    serializer_class = FunctionalClassificationSerializer

    def get_queryset(self):
        qs = FunctionalClassification.objects.all()
        discipline = self.request.query_params.get('discipline')
        if discipline:
            qs = qs.filter(discipline_id=discipline)
        return qs


class FunctionalClassificationDetailView(PublicListMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FunctionalClassificationSerializer
    queryset = FunctionalClassification.objects.all()


class EventTypeView(PublicListMixin, generics.ListCreateAPIView):
    serializer_class = EventTypeSerializer
    queryset = EventType.objects.all()


class EventTypeDetailView(PublicListMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EventTypeSerializer
    queryset = EventType.objects.all()

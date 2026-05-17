from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import Institution, InstitutionUser, Coach, Athlete, Tournament, TournamentEvent
from .serializers import (
    InstitutionSerializer, InstitutionCreateSerializer, InstitutionUserSerializer,
    CoachSerializer, CoachCreateSerializer, AthleteSerializer, AthleteCreateSerializer,
    TournamentSerializer, TournamentCreateSerializer, TournamentEventSerializer, TournamentEventBulkCreateSerializer
)
from paratletismo_core.users.models import RoleChoices
from paratletismo_core.users.permissions import IsSuperAdmin


class InstitutionListView(generics.ListCreateAPIView):
    serializer_class = InstitutionSerializer

    def get_queryset(self):
        return Institution.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        InstitutionUser.objects.create(
            institution=instance,
            user=self.request.user,
            position='Administrador'
        )


class InstitutionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = InstitutionSerializer

    def get_queryset(self):
        return Institution.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


class InstitutionAthletesView(generics.ListAPIView):
    serializer_class = AthleteSerializer

    def get_queryset(self):
        return Athlete.objects.filter(institution_id=self.kwargs['pk']).select_related('user', 'sex', 'functional_classification')

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class InstitutionCoachesView(generics.ListAPIView):
    serializer_class = CoachSerializer

    def get_queryset(self):
        return Coach.objects.filter(institution_id=self.kwargs['pk']).select_related('user')

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class CoachListView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CoachCreateSerializer
        return CoachSerializer

    def get_queryset(self):
        qs = Coach.objects.select_related('user')
        institution = self.request.query_params.get('institution')
        if institution:
            qs = qs.filter(institution_id=institution)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class CoachDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CoachSerializer
    queryset = Coach.objects.select_related('user')

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class AthleteListView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AthleteCreateSerializer
        return AthleteSerializer

    def get_queryset(self):
        qs = Athlete.objects.select_related('user', 'institution', 'coach')
        institution = self.request.query_params.get('institution')
        coach = self.request.query_params.get('coach')
        if institution:
            qs = qs.filter(institution_id=institution)
        if coach:
            qs = qs.filter(coach_id=coach)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class AthleteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AthleteSerializer

    def get_queryset(self):
        return Athlete.objects.select_related('user', 'institution', 'coach')

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class TournamentListView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TournamentCreateSerializer
        return TournamentSerializer

    def get_queryset(self):
        qs = Tournament.objects.prefetch_related('disciplines', 'sexes', 'categories')
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


class TournamentDetailView(generics.RetrieveAPIView):
    serializer_class = TournamentSerializer

    def get_queryset(self):
        return Tournament.objects.prefetch_related('disciplines', 'sexes', 'categories')

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        tournament = self.get_object()
        if tournament.admin_user != request.user:
            return Response({'error': 'No tenes permisos para editar este torneo'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        tournament = self.get_object()
        if tournament.admin_user != request.user:
            return Response({'error': 'No tenes permisos para eliminar este torneo'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class TournamentUpdateStatusView(generics.UpdateAPIView):
    serializer_class = TournamentSerializer
    queryset = Tournament.objects.all()

    def update(self, request, *args, **kwargs):
        tournament = self.get_object()
        if tournament.admin_user != request.user:
            return Response({'error': 'No tenes permisos para cambiar el estado de este torneo'}, status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get('status')
        if new_status not in dict(Tournament.STATUS_CHOICES):
            return Response({'error': 'Estado invalido'}, status=status.HTTP_400_BAD_REQUEST)
        tournament.status = new_status
        tournament.save()
        return Response(TournamentSerializer(tournament).data)


class TournamentEventsView(generics.ListCreateAPIView):
    serializer_class = TournamentEventSerializer

    def get_queryset(self):
        return TournamentEvent.objects.filter(tournament_id=self.kwargs['pk'])

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        tournament = Tournament.objects.get(id=self.kwargs['pk'])
        if tournament.admin_user != request.user:
            return Response({'error': 'No tenes permisos para gestionar pruebas de este torneo'}, status=status.HTTP_403_FORBIDDEN)
        if 'event_types' in request.data:
            serializer = TournamentEventBulkCreateSerializer(
                data={**request.data, 'tournament': self.kwargs['pk']},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            events = serializer.save()
            output = TournamentEventSerializer(events, many=True)
            return Response({'message': f'{len(events)} pruebas creadas', 'events': output.data}, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)


class TournamentEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TournamentEventSerializer
    queryset = TournamentEvent.objects.all()

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class MyInstitutionView(generics.RetrieveAPIView):
    serializer_class = InstitutionSerializer

    def get_object(self):
        user = self.request.user
        if user.role == RoleChoices.INSTITUTION:
            return InstitutionUser.objects.get(user=user).institution
        elif user.role == RoleChoices.COACH:
            coach = Coach.objects.get(user=user)
            if coach.institution:
                return coach.institution
        return None


class AvailableInstitutionsView(generics.ListAPIView):
    serializer_class = InstitutionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Institution.objects.all()


class CoachSetInstitutionView(generics.UpdateAPIView):
    serializer_class = CoachSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        coach = Coach.objects.get(user=request.user)
        institution_id = request.data.get('institution')
        if not institution_id:
            return Response({'error': 'institution es obligatorio'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            institution = Institution.objects.get(id=institution_id)
            coach.institution = institution
            coach.save()
            return Response(CoachSerializer(coach).data)
        except Institution.DoesNotExist:
            return Response({'error': 'Institucion no encontrada'}, status=status.HTTP_404_NOT_FOUND)


class MyAthletesView(generics.ListAPIView):
    serializer_class = AthleteSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == RoleChoices.COACH:
            coach = Coach.objects.get(user=user)
            return Athlete.objects.filter(coach=coach).select_related('user', 'sex', 'functional_classification')
        elif user.role == RoleChoices.INSTITUTION:
            institution = InstitutionUser.objects.get(user=user).institution
            return Athlete.objects.filter(institution=institution).select_related('user', 'sex', 'functional_classification')
        return Athlete.objects.none()

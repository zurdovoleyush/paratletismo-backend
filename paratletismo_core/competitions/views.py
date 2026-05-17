from rest_framework import generics, status, permissions
from rest_framework.response import Response
from .models import Registration, AthleteEvent, JudgeAssignment, Result, FinalResult
from .serializers import (
    RegistrationSerializer, RegistrationCreateSerializer,
    AthleteEventSerializer, JudgeAssignmentSerializer,
    ResultSerializer, FinalResultSerializer,
    AthleteEventRegistrationSerializer
)
from paratletismo_core.tournaments.models import TournamentEvent, Athlete
from paratletismo_core.users.models import RoleChoices


class RegistrationListView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RegistrationCreateSerializer
        return RegistrationSerializer

    def get_queryset(self):
        qs = Registration.objects.select_related('athlete', 'tournament', 'institution')
        tournament = self.request.query_params.get('tournament')
        athlete = self.request.query_params.get('athlete')
        institution = self.request.query_params.get('institution')
        status_param = self.request.query_params.get('status')
        if tournament:
            qs = qs.filter(tournament_id=tournament)
        if athlete:
            qs = qs.filter(athlete_id=athlete)
        if institution:
            qs = qs.filter(institution_id=institution)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class RegistrationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = RegistrationSerializer
    queryset = Registration.objects.all()

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class RegistrationApproveView(generics.UpdateAPIView):
    serializer_class = RegistrationSerializer
    queryset = Registration.objects.all()

    def update(self, request, *args, **kwargs):
        registration = self.get_object()
        registration.status = 'approved'
        registration.save()
        return Response(RegistrationSerializer(registration).data)


class RegistrationRejectView(generics.UpdateAPIView):
    serializer_class = RegistrationSerializer
    queryset = Registration.objects.all()

    def update(self, request, *args, **kwargs):
        registration = self.get_object()
        registration.status = 'rejected'
        registration.save()
        return Response(RegistrationSerializer(registration).data)


class MyRegistrationsView(generics.ListAPIView):
    serializer_class = RegistrationSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == RoleChoices.ATHLETE:
            athlete = Athlete.objects.get(user=user)
            return Registration.objects.filter(athlete=athlete)
        elif user.role == RoleChoices.COACH:
            from paratletismo_core.tournaments.models import Coach
            coach = Coach.objects.get(user=user)
            return Registration.objects.filter(athlete__coach=coach)
        elif user.role == RoleChoices.INSTITUTION:
            from paratletismo_core.tournaments.models import InstitutionUser
            institution = InstitutionUser.objects.get(user=user).institution
            return Registration.objects.filter(institution=institution)
        return Registration.objects.none()


class AthleteRegistrationOptionsView(generics.RetrieveAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        athlete_id = kwargs.get('pk')
        athlete = Athlete.objects.select_related('sex', 'functional_classification').get(id=athlete_id)

        from paratletismo_core.tournaments.models import Tournament, TournamentEvent
        tournaments = Tournament.objects.filter(status__in=['registration_open', 'in_progress']).prefetch_related('events')
        result = []
        for t in tournaments:
            is_registered = Registration.objects.filter(tournament=t, athlete=athlete).exists()
            eligible_events = []
            for event in t.events.all():
                if event.status == 'cancelled':
                    continue
                eligible = True
                if event.sex and athlete.sex and event.sex.id != athlete.sex.id:
                    eligible = False
                if event.functional_classification and athlete.functional_classification and event.functional_classification.id != athlete.functional_classification.id:
                    eligible = False
                if event.functional_classification and not athlete.functional_classification:
                    eligible = False
                is_in_event = AthleteEvent.objects.filter(tournament_event=event, registration__athlete=athlete).exists()
                if eligible:
                    eligible_events.append({
                        'id': event.id,
                        'name': event.name,
                        'event_type_name': event.event_type.name,
                        'sex_name': event.sex.name if event.sex else 'Libre',
                        'category_name': event.category.name if event.category else '',
                        'classification_code': event.functional_classification.code if event.functional_classification else None,
                        'scheduled_date': event.scheduled_date,
                        'is_registered': is_in_event,
                    })

            result.append({
                'tournament': {
                    'id': t.id,
                    'name': t.name,
                    'city': t.city,
                    'status': t.status,
                    'registration_opens': t.registration_opens,
                    'registration_closes': t.registration_closes,
                },
                'is_registered_in_tournament': is_registered,
                'eligible_events': eligible_events,
            })

        return Response({'athlete': athlete_id, 'tournaments': result})


class AthleteEventListView(generics.ListAPIView):
    serializer_class = AthleteEventSerializer

    def get_queryset(self):
        return AthleteEvent.objects.filter(tournament_event_id=self.kwargs['event_pk'])

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class EventRegistrationView(generics.CreateAPIView):
    serializer_class = AthleteEventRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        athlete_id = request.data.get('athlete')
        event_id = request.data.get('tournament_event')

        if not athlete_id or not event_id:
            return Response({'error': 'athlete y tournament_event son obligatorios'}, status=status.HTTP_400_BAD_REQUEST)

        from paratletismo_core.tournaments.models import Athlete
        from paratletismo_core.competitions.models import Registration

        athlete = Athlete.objects.get(id=athlete_id)
        registration = Registration.objects.filter(
            athlete=athlete,
            status__in=['approved', 'pending']
        ).order_by('-registered_at').first()

        if not registration:
            return Response({'error': 'El atleta debe estar inscrito en el torneo primero'}, status=status.HTTP_400_BAD_REQUEST)

        from .serializers import AthleteEventRegistrationSerializer
        serializer = AthleteEventRegistrationSerializer(data={
            'athlete': athlete_id,
            'tournament_event': event_id,
        })
        serializer.is_valid(raise_exception=True)

        existing = AthleteEvent.objects.filter(
            tournament_event_id=event_id,
            registration=registration
        ).exists()
        if existing:
            return Response({'error': 'El atleta ya esta inscrito en esta prueba'}, status=status.HTTP_400_BAD_REQUEST)

        athlete_event = AthleteEvent.objects.create(
            tournament_event_id=event_id,
            registration=registration,
            bib_number=None,
            lane=None,
        )
        output = AthleteEventSerializer(athlete_event)
        return Response(output.data, status=status.HTTP_201_CREATED)


class AthleteEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AthleteEventSerializer
    queryset = AthleteEvent.objects.all()


class JudgeAssignmentListView(generics.ListCreateAPIView):
    serializer_class = JudgeAssignmentSerializer

    def get_queryset(self):
        qs = JudgeAssignment.objects.all()
        event_pk = self.kwargs.get('event_pk')
        if event_pk:
            qs = qs.filter(tournament_event_id=event_pk)
        judge = self.request.query_params.get('judge')
        if judge:
            qs = qs.filter(judge_id=judge)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class JudgeAssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JudgeAssignmentSerializer
    queryset = JudgeAssignment.objects.all()


class MyJudgeAssignmentsView(generics.ListAPIView):
    serializer_class = JudgeAssignmentSerializer

    def get_queryset(self):
        return JudgeAssignment.objects.filter(judge=self.request.user)


class ResultListView(generics.ListCreateAPIView):
    serializer_class = ResultSerializer

    def get_queryset(self):
        qs = Result.objects.all()
        athlete_event = self.request.query_params.get('athlete_event')
        if athlete_event:
            qs = qs.filter(athlete_event_id=athlete_event)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class ResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ResultSerializer
    queryset = Result.objects.all()


class FinalResultListView(generics.ListCreateAPIView):
    serializer_class = FinalResultSerializer

    def get_queryset(self):
        qs = FinalResult.objects.all()
        tournament_event = self.request.query_params.get('tournament_event')
        if tournament_event:
            qs = qs.filter(tournament_event_id=tournament_event)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get(self, request, *args, **kwargs):
        if not request.query_params.get('tournament_event'):
            return Response({'error': 'tournament_event parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        return super().get(request, *args, **kwargs)


class FinalResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FinalResultSerializer
    queryset = FinalResult.objects.all()


class EventResultsPublicView(generics.ListAPIView):
    serializer_class = FinalResultSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return FinalResult.objects.filter(tournament_event_id=self.kwargs['event_pk']).order_by('rank')

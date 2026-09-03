from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse
import re
from .models import Registration, AthleteEvent, JudgeAssignment, Result, FinalResult
from .serializers import (
    RegistrationSerializer, RegistrationCreateSerializer,
    AthleteEventSerializer, JudgeAssignmentSerializer,
    ResultSerializer, FinalResultSerializer,
    AthleteEventRegistrationSerializer
)
from paratletismo_core.tournaments.models import TournamentEvent, Athlete, Tournament
from paratletismo_core.users.models import RoleChoices
from django.db import transaction


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


class RegistrationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RegistrationSerializer
    queryset = Registration.objects.all()

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        registration = self.get_object()
        user = request.user
        is_reviewer = (
            user.is_superuser
            or user.role in (RoleChoices.SUPERADMIN, RoleChoices.ADMIN)
            or registration.tournament.admin_user_id == user.id
        )
        protected = ['status', 'payment_status', 'rejection_reason']
        if any(field in request.data for field in protected) and not is_reviewer:
            return Response(
                {'error': 'No tienes permiso para modificar el estado de la inscripcion'},
                status=status.HTTP_403_FORBIDDEN,
            )
        was_rejected = registration.status == 'rejected'
        uploaded_doc = bool(request.FILES.get('medical_certificate') or request.FILES.get('payment_receipt'))
        response = super().update(request, *args, **kwargs)
        if was_rejected and uploaded_doc:
            registration.refresh_from_db()
            registration.status = 'pending'
            registration.rejection_reason = ''
            registration.save(update_fields=['status', 'rejection_reason'])
            return Response(RegistrationSerializer(registration).data)
        return response

    def destroy(self, request, *args, **kwargs):
        registration = self.get_object()
        user = request.user
        can_delete = user.is_superuser or user.role == RoleChoices.SUPERADMIN
        if not can_delete:
            from paratletismo_core.tournaments.models import Athlete, Coach, InstitutionUser
            if user.role == RoleChoices.INSTITUTION:
                try:
                    inst = InstitutionUser.objects.get(user=user).institution
                    can_delete = inst.id == registration.institution_id
                except InstitutionUser.DoesNotExist:
                    can_delete = False
            elif user.role == RoleChoices.COACH:
                try:
                    coach = Coach.objects.get(user=user)
                    can_delete = registration.athlete.coach_id == coach.id
                except Coach.DoesNotExist:
                    can_delete = False
            elif user.role == RoleChoices.ATHLETE:
                can_delete = Athlete.objects.filter(user=user, id=registration.athlete_id).exists()
        if not can_delete:
            return Response({'error': 'No tienes permiso para cancelar esta inscripcion'}, status=status.HTTP_403_FORBIDDEN)
        registration.delete()
        return Response({'detail': 'Inscripcion cancelada'}, status=status.HTTP_204_NO_CONTENT)


class RegistrationApproveView(generics.UpdateAPIView):
    serializer_class = RegistrationSerializer
    queryset = Registration.objects.all()

    def _can_review(self, request, registration):
        user = request.user
        if user.is_superuser or user.role in (RoleChoices.SUPERADMIN, RoleChoices.ADMIN):
            return True
        return registration.tournament.admin_user_id == user.id

    def update(self, request, *args, **kwargs):
        registration = self.get_object()
        if not self._can_review(request, registration):
            return Response({'error': 'No tienes permiso para aprobar inscripciones de este torneo'}, status=status.HTTP_403_FORBIDDEN)
        registration.status = 'approved'
        registration.rejection_reason = ''
        registration.save()
        return Response(RegistrationSerializer(registration).data)


class RegistrationRejectView(generics.UpdateAPIView):
    serializer_class = RegistrationSerializer
    queryset = Registration.objects.all()

    def _can_review(self, request, registration):
        user = request.user
        if user.is_superuser or user.role in (RoleChoices.SUPERADMIN, RoleChoices.ADMIN):
            return True
        return registration.tournament.admin_user_id == user.id

    def update(self, request, *args, **kwargs):
        registration = self.get_object()
        if not self._can_review(request, registration):
            return Response({'error': 'No tienes permiso para rechazar inscripciones de este torneo'}, status=status.HTTP_403_FORBIDDEN)
        reason = request.data.get('reason', request.data.get('rejection_reason', ''))
        registration.status = 'rejected'
        registration.rejection_reason = reason
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
        athlete = Athlete.objects.select_related('sex', 'functional_classification', 'track_classification', 'field_classification').get(id=athlete_id)

        from paratletismo_core.tournaments.models import Tournament, TournamentEvent
        tournaments = Tournament.objects.filter(
            status__in=['registration_open', 'in_progress'],
            payment_status='paid',
            is_active=True,
        ).prefetch_related('events')
        result = []
        for t in tournaments:
            registration = Registration.objects.filter(tournament=t, athlete=athlete).first()
            is_registered = registration is not None

            athlete_events = list(AthleteEvent.objects.filter(
                registration__athlete=athlete,
                registration__tournament=t,
            ))
            ae_by_event = {ae.tournament_event_id: ae for ae in athlete_events}
            events_confirmed = any(ae.status == 'confirmed' for ae in athlete_events)
            registered_event_count = sum(1 for ae in athlete_events if ae.status in ['pending', 'confirmed'])
            max_events = t.max_events_per_athlete
            limit_reached = bool(max_events and max_events > 0 and registered_event_count >= max_events)
            eligible_events = []
            for event in t.events.all():
                if event.status == 'cancelled':
                    continue
                eligible = True
                if athlete.sex:
                    event_sexes = list(event.sexes.all()) if event.sexes.exists() else ([event.sex] if event.sex else [])
                    if event_sexes and athlete.sex not in event_sexes:
                        eligible = False
                if athlete.sex and event.functional_classifications.exists():
                    is_track = event.uses_track_classification()
                    athlete_fc = athlete.track_classification if is_track else athlete.field_classification
                    if athlete_fc and athlete_fc not in event.functional_classifications.all():
                        eligible = False
                    elif not athlete_fc:
                        eligible = False
                elif event.functional_classification:
                    is_track = event.uses_track_classification()
                    if is_track:
                        if athlete.track_classification and event.functional_classification.id != athlete.track_classification.id:
                            eligible = False
                        elif not athlete.track_classification:
                            eligible = False
                    else:
                        if athlete.field_classification and event.functional_classification.id != athlete.field_classification.id:
                            eligible = False
                        elif not athlete.field_classification:
                            eligible = False
                event_cats = list(event.categories.all()) if event.categories.exists() else ([event.category] if event.category else [])
                if event_cats:
                    from datetime import date
                    ref_year = t.tournament_start.year if t.tournament_start else date.today().year
                    athlete_age = athlete.category_age(ref_year)
                    age_ok = False
                    for cat in event_cats:
                        if cat.min_age and athlete_age < cat.min_age:
                            continue
                        if cat.max_age and athlete_age > cat.max_age:
                            continue
                        age_ok = True
                        break
                    if not age_ok:
                        eligible = False
                if eligible:
                    ae = ae_by_event.get(event.id)
                    is_track_label = event.event_type and event.event_type.is_time_based
                    sex_names = ', '.join(s.name for s in event.sexes.all()) or (event.sex.name if event.sex else 'Libre')
                    cat_names = ', '.join(c.name for c in event.categories.all()) or (event.category.name if event.category else '')
                    classif_codes = ', '.join(fc.code for fc in event.functional_classifications.all()) or (event.functional_classification.code if event.functional_classification else '')
                    eligible_events.append({
                        'id': event.id,
                        'name': event.name,
                        'event_type_name': event.event_type.name if event.event_type else '',
                        'sex_name': sex_names,
                        'category_name': cat_names,
                        'classification_code': classif_codes,
                        'is_track': is_track_label,
                        'scheduled_date': event.scheduled_date,
                        'is_registered': ae is not None,
                        'athlete_event_id': ae.id if ae else None,
                        'athlete_event_status': ae.status if ae else None,
                        'is_disabled': limit_reached,
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
                'registration_id': registration.id if is_registered else None,
                'registration_status': registration.status if is_registered else None,
                'medical_certificate': registration.medical_certificate.url if is_registered and registration.medical_certificate else None,
                'payment_receipt': registration.payment_receipt.url if is_registered and registration.payment_receipt else None,
                'rejection_reason': registration.rejection_reason if is_registered else '',
                'max_events_per_athlete': max_events,
                'registered_event_count': registered_event_count,
                'limit_reached': limit_reached,
                'events_confirmed': events_confirmed,
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
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        athlete_id = request.data.get('athlete')
        event_id = request.data.get('tournament_event')

        if not athlete_id or not event_id:
            return Response({'error': 'athlete y tournament_event son obligatorios'}, status=status.HTTP_400_BAD_REQUEST)

        from paratletismo_core.tournaments.models import Athlete
        from paratletismo_core.competitions.models import Registration

        athlete = Athlete.objects.get(id=athlete_id)

        try:
            event = TournamentEvent.objects.get(id=event_id)
        except TournamentEvent.DoesNotExist:
            return Response({'error': 'Prueba no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        registration = Registration.objects.filter(
            athlete=athlete,
            tournament=event.tournament,
            status__in=['approved', 'pending']
        ).order_by('-registered_at').first()

        if not registration:
            return Response({'error': 'El atleta debe estar inscrito en este torneo primero'}, status=status.HTTP_400_BAD_REQUEST)

        if AthleteEvent.objects.filter(registration=registration, status='confirmed').exists():
            return Response(
                {'error': 'La inscripcion del atleta ya fue confirmada, no se pueden agregar mas pruebas'},
                status=status.HTTP_400_BAD_REQUEST
            )

        max_events = event.tournament.max_events_per_athlete
        if max_events and max_events > 0:
            current_count = AthleteEvent.objects.filter(
                registration=registration,
                status__in=['pending', 'confirmed']
            ).count()
            if current_count >= max_events:
                return Response(
                    {'error': f'El atleta alcanzo el maximo de {max_events} pruebas por atleta en este torneo'},
                    status=status.HTTP_400_BAD_REQUEST
                )

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

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        athlete = instance.registration.athlete

        can_delete = user.is_superuser or user.role == RoleChoices.SUPERADMIN
        if not can_delete:
            from paratletismo_core.tournaments.models import Coach, InstitutionUser
            if user.role == RoleChoices.INSTITUTION:
                try:
                    inst = InstitutionUser.objects.get(user=user).institution
                    can_delete = inst.id == athlete.institution_id
                except InstitutionUser.DoesNotExist:
                    can_delete = False
            elif user.role == RoleChoices.COACH:
                try:
                    coach = Coach.objects.get(user=user)
                    can_delete = athlete.coach_id == coach.id
                except Coach.DoesNotExist:
                    can_delete = False
            elif user.role == RoleChoices.ATHLETE:
                can_delete = Athlete.objects.filter(user=user, id=athlete.id).exists()

        if not can_delete:
            return Response({'error': 'No tienes permiso para anular esta inscripcion'}, status=status.HTTP_403_FORBIDDEN)

        if instance.status == 'confirmed':
            return Response({'error': 'No se puede anular una inscripcion ya confirmada'}, status=status.HTTP_400_BAD_REQUEST)

        instance.delete()
        return Response({'detail': 'Inscripcion anulada'}, status=status.HTTP_200_OK)


class RegistrationConfirmEventsView(generics.RetrieveUpdateAPIView):
    queryset = Registration.objects.all()

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        registration = self.get_object()
        user = request.user

        can_confirm = user.is_superuser or user.role == RoleChoices.SUPERADMIN
        if not can_confirm:
            from paratletismo_core.tournaments.models import Coach, InstitutionUser
            if user.role == RoleChoices.INSTITUTION:
                try:
                    inst = InstitutionUser.objects.get(user=user).institution
                    can_confirm = inst.id == registration.institution_id
                except InstitutionUser.DoesNotExist:
                    can_confirm = False
            elif user.role == RoleChoices.COACH:
                try:
                    coach = Coach.objects.get(user=user)
                    can_confirm = registration.athlete.coach_id == coach.id
                except Coach.DoesNotExist:
                    can_confirm = False
            elif user.role == RoleChoices.ATHLETE:
                can_confirm = Athlete.objects.filter(user=user, id=registration.athlete_id).exists()

        if not can_confirm:
            return Response({'error': 'No tienes permiso para confirmar estas inscripciones'}, status=status.HTTP_403_FORBIDDEN)

        if AthleteEvent.objects.filter(registration=registration, status='pending').exists():
            count = AthleteEvent.objects.filter(registration=registration, status='pending').update(status='confirmed')
            return Response({'message': f'{count} inscripciones confirmadas'})

        if AthleteEvent.objects.filter(registration=registration, status='confirmed').exists():
            return Response({'message': 'Las inscripciones ya estaban confirmadas'})

        return Response({'error': 'No hay pruebas pendientes para confirmar'}, status=status.HTTP_400_BAD_REQUEST)


class AssignLanesView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        event_pk = kwargs.get('event_pk')
        lanes_data = request.data.get('lanes', [])

        if not lanes_data:
            return Response({'error': 'lanes data is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tournament_event = TournamentEvent.objects.get(id=event_pk)
        except TournamentEvent.DoesNotExist:
            return Response({'error': 'Prueba no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        updated = []
        errors = []
        for item in lanes_data:
            athlete_event_id = item.get('athlete_event_id')
            lane = item.get('lane')
            if not athlete_event_id or lane is None:
                errors.append({'athlete_event_id': athlete_event_id, 'error': 'athlete_event_id y lane son obligatorios'})
                continue
            try:
                ae = AthleteEvent.objects.get(id=athlete_event_id, tournament_event_id=event_pk)
                ae.lane = lane
                ae.save()
                updated.append(ae)
            except AthleteEvent.DoesNotExist:
                errors.append({'athlete_event_id': athlete_event_id, 'error': 'Atleta no encontrado en esta prueba'})

        output = AthleteEventSerializer(updated, many=True)
        return Response({
            'message': f'{len(updated)} carriles asignados',
            'athlete_events': output.data,
            'errors': errors,
        })

    def get(self, request, *args, **kwargs):
        event_pk = kwargs.get('event_pk')
        athlete_events = AthleteEvent.objects.filter(
            tournament_event_id=event_pk
        ).select_related(
            'registration__athlete__user',
            'registration__institution',
            'registration__athlete__functional_classification',
            'registration__athlete__sex',
        ).order_by('lane', 'bib_number', 'registration__athlete__user__last_name')

        output = AthleteEventSerializer(athlete_events, many=True)
        return Response({'athlete_events': output.data})


class BulkResultCreateView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        event_pk = kwargs.get('event_pk')
        results_data = request.data.get('results', [])

        if not results_data:
            return Response({'error': 'results data is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tournament_event = TournamentEvent.objects.get(id=event_pk)
        except TournamentEvent.DoesNotExist:
            return Response({'error': 'Prueba no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        created = []
        errors = []
        for item in results_data:
            athlete_event_id = item.get('athlete_event')
            if not athlete_event_id:
                errors.append({'error': 'athlete_event es obligatorio', 'item': item})
                continue

            try:
                ae = AthleteEvent.objects.get(id=athlete_event_id, tournament_event_id=event_pk)
            except AthleteEvent.DoesNotExist:
                errors.append({'athlete_event_id': athlete_event_id, 'error': 'Atleta no encontrado en esta prueba'})
                continue

            attempt = item.get('attempt_number', 1)
            mark = item.get('mark', '')
            value = item.get('value')
            if value is None or value == '':
                value = parse_time_mark(mark)
            elif isinstance(value, str):
                value = parse_time_mark(value)

            result, was_created = Result.objects.update_or_create(
                athlete_event=ae,
                attempt_number=attempt,
                defaults={
                    'value': value,
                    'mark': mark,
                    'is_valid': item.get('is_valid', True),
                    'wind': item.get('wind'),
                    'notes': item.get('notes', ''),
                    'recorded_by': request.user,
                }
            )
            created.append(result)

        output = ResultSerializer(created, many=True)
        return Response({
            'message': f'{len(created)} resultados guardados',
            'results': output.data,
            'errors': errors,
        })


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


class MyResultsView(generics.ListAPIView):
    serializer_class = FinalResultSerializer

    def get_queryset(self):
        user = self.request.user
        qs = FinalResult.objects.select_related(
            'athlete__user', 'athlete__functional_classification',
            'tournament_event__tournament', 'tournament_event__event_type',
        ).order_by('-tournament_event__scheduled_date', 'rank')
        if user.role == RoleChoices.ATHLETE:
            athlete = Athlete.objects.filter(user=user).first()
            if not athlete:
                return FinalResult.objects.none()
            return qs.filter(athlete=athlete)
        elif user.role == RoleChoices.COACH:
            from paratletismo_core.tournaments.models import Coach
            coach = Coach.objects.filter(user=user).first()
            if not coach:
                return FinalResult.objects.none()
            return qs.filter(athlete__coach=coach)
        elif user.role == RoleChoices.INSTITUTION:
            from paratletismo_core.tournaments.models import InstitutionUser
            inst_user = InstitutionUser.objects.filter(user=user).first()
            if not inst_user:
                return FinalResult.objects.none()
            return qs.filter(athlete__institution=inst_user.institution)
        return FinalResult.objects.none()

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class FinalResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FinalResultSerializer
    queryset = FinalResult.objects.all()


class EventResultsPublicView(generics.ListAPIView):
    serializer_class = FinalResultSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return FinalResult.objects.filter(tournament_event_id=self.kwargs['event_pk']).order_by('rank')


class TournamentPublicResultsView(generics.GenericAPIView):
    """Resultados publicos de un torneo (en progreso o completado), sin autenticacion."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        from django.db.models import Count
        try:
            tournament = Tournament.objects.get(
                id=kwargs.get('tournament_pk'),
                payment_status='paid',
                is_active=True,
            )
        except Tournament.DoesNotExist:
            return Response({'error': 'Torneo no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        if tournament.status not in ('in_progress', 'completed'):
            return Response({'error': 'Este torneo no tiene resultados publicos aun'}, status=status.HTTP_200_OK)

        events = (
            TournamentEvent.objects
            .filter(tournament=tournament)
            .annotate(n_athletes=Count('athlete_events', distinct=True))
            .filter(n_athletes__gt=0)
            .select_related('event_type', 'sex', 'category')
            .prefetch_related('final_results', 'functional_classifications')
            .order_by('scheduled_date', 'name')
        )

        events_data = []
        for event in events:
            events_data.append({
                'id': str(event.id),
                'name': event.name,
                'event_type_name': event.event_type.name if event.event_type else '',
                'sex_name': event.sex.name if event.sex else 'Multiple',
                'category_name': event.category.name if event.category else 'Multiple',
                'scheduled_date': event.scheduled_date,
                'status': event.status,
                'is_track': bool(event.event_type and event.event_type.is_time_based),
                'functional_classifications': list(event.functional_classifications.values_list('code', flat=True)),
                'final_results': FinalResultSerializer(
                    event.final_results.all().order_by('rank'), many=True
                ).data,
            })

        return Response({
            'id': str(tournament.id),
            'name': tournament.name,
            'venue': tournament.venue,
            'city': tournament.city,
            'province': tournament.province,
            'status': tournament.status,
            'tournament_start': tournament.tournament_start,
            'tournament_end': tournament.tournament_end,
            'events': events_data,
        })


class AthletePublicHistoryView(APIView):
    """Historial publico de un atleta: marcas y resultados en todos los torneos visibles."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            athlete = Athlete.objects.get(id=kwargs.get('pk'))
        except Athlete.DoesNotExist:
            return Response({'error': 'Atleta no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        results = (
            FinalResult.objects
            .filter(athlete=athlete)
            .filter(tournament_event__tournament__payment_status='paid')
            .filter(tournament_event__tournament__is_active=True)
            .filter(tournament_event__tournament__status__in=['in_progress', 'completed'])
            .select_related(
                'tournament_event__tournament',
                'tournament_event__event_type',
                'tournament_event__sex',
                'tournament_event__category',
            )
            .order_by('-tournament_event__tournament__tournament_start', 'tournament_event__name')
        )

        rows = []
        for fr in results:
            te = fr.tournament_event
            wind = None
            ae = te.athlete_events.filter(registration__athlete=athlete, status='confirmed').first()
            if ae is not None:
                res = ae.results.filter(attempt_number=1).first()
                if res is not None and res.wind is not None:
                    wind = res.wind
            rows.append({
                'tournament_id': str(te.tournament.id),
                'tournament_name': te.tournament.name,
                'tournament_city': te.tournament.city,
                'tournament_date': te.tournament.tournament_start,
                'event_id': str(te.id),
                'event_name': te.name,
                'event_type_name': te.event_type.name if te.event_type else '',
                'sex_name': te.sex.name if te.sex else '',
                'category_name': te.category.name if te.category else '',
                'is_track': bool(te.event_type and te.event_type.is_time_based),
                'rank': fr.rank,
                'best_mark': fr.best_mark,
                'points': fr.points,
                'wind': wind,
                'record_type': fr.record_type or '',
                'is_dnf': fr.is_dnf,
                'is_dns': fr.is_dns,
                'is_dq': fr.is_dq,
            })

        return Response({
            'id': str(athlete.id),
            'athlete_name': athlete.user.get_full_name() or athlete.user.email,
            'institution': athlete.institution.name if athlete.institution else '',
            'classification': athlete.functional_classification.code if athlete.functional_classification else '',
            'results': rows,
        })


def _es_salto(et):
    """Una prueba de salto (Salto Largo / Salto Alto) muestra clasificacion T,
    segun la convencion internacional del World Para Athletics."""
    return bool(et and (et.name or '').strip().lower().startswith('salto'))


def _records_compute(limit=3, filters=None):
    """Mejores marcas por (tipo de prueba, sexo, categoria, clasificacion) y torneo.

    Se conserva la mejor marca de cada atleta por prueba y torneo, de modo que un
    mismo atleta que fue el mejor en varios torneos figura una vez por cada torneo
    donde su marca es la mejor de ese torneo."""
    filters = filters or {}
    qs = (
        Result.objects
        .filter(is_valid=True, value__isnull=False)
        .filter(athlete_event__status='confirmed')
        .filter(athlete_event__tournament_event__tournament__payment_status='paid')
        .filter(athlete_event__tournament_event__tournament__is_active=True)
        .filter(athlete_event__tournament_event__tournament__status__in=['in_progress', 'completed'])
        .select_related(
            'athlete_event__tournament_event__tournament',
            'athlete_event__tournament_event__event_type__discipline',
            'athlete_event__tournament_event__sex',
            'athlete_event__tournament_event__category',
            'athlete_event__tournament_event__functional_classification',
            'athlete_event__registration__athlete__user',
            'athlete_event__registration__athlete__institution',
            'athlete_event__registration__athlete__functional_classification',
        )
    )

    best_map = {}
    key_meta = {}
    for r in qs.iterator():
        te = r.athlete_event.tournament_event
        et = te.event_type if te else None
        if te is None or et is None:
            continue
        val = float(r.value)
        athlete = r.athlete_event.registration.athlete
        direction = 'min' if et.is_time_based else 'max'
        ev_code = te.functional_classification.code if te.functional_classification else ''
        ath_code = athlete.functional_classification.code if athlete.functional_classification else ''
        code = ((ev_code or ath_code) or '').upper()
        key = (str(et.id), str(te.sex_id or ''), str(te.category_id or ''), code)

        if key not in key_meta:
            key_meta[key] = {
                'discipline_id': str(et.discipline_id) if et.discipline_id else '',
                'discipline_name': et.discipline.name if et.discipline else '',
                'event_type_id': str(et.id),
                'event_type_name': et.name,
                'sex_name': te.sex.name if te.sex else '',
                'category_name': te.category.name if te.category else '',
                'is_time_based': bool(et.is_time_based),
                'is_track': bool(et.is_time_based or _es_salto(et)),
                'unit': et.unit or 'segundos',
                'direction': direction,
                'codes': {code} if code else set(),
            }
        else:
            if code:
                key_meta[key]['codes'].add(code)

        bkey = (key, str(te.tournament_id) if te.tournament_id else '')
        cand = {
            'value': val,
            'mark': r.mark,
            'wind': float(r.wind) if r.wind is not None else None,
            'athlete_id': str(athlete.id),
            'athlete_name': athlete.user.get_full_name() or athlete.user.email,
            'institution': athlete.institution.name if athlete.institution else '',
            'classification': ath_code.upper(),
            'event_id': str(te.id),
            'event_name': te.name,
            'tournament_name': te.tournament.name,
            'tournament_date': te.tournament.tournament_start,
        }
        cur = best_map.get(bkey)
        if cur is None:
            best_map[bkey] = cand
        else:
            better = cand['value'] < cur['value'] if direction == 'min' else cand['value'] > cur['value']
            if better:
                best_map[bkey] = cand

    by_key = {}
    for (key, _aid), b in best_map.items():
        by_key.setdefault(key, []).append(b)

    all_groups = []
    for key, lst in by_key.items():
        meta = key_meta[key]
        ordered = sorted(lst, key=lambda b: (b['value'], b['athlete_name']), reverse=(meta['direction'] == 'max'))
        for i, b in enumerate(ordered):
            b['rank'] = i + 1
        all_groups.append({
            'key': '__'.join(key),
            'discipline_id': meta['discipline_id'],
            'discipline_name': meta['discipline_name'],
            'event_type_id': meta['event_type_id'],
            'event_type_name': meta['event_type_name'],
            'sex_name': meta['sex_name'] or 'Mixto',
            'category_name': meta['category_name'] or 'Sin categoria',
            'is_time_based': meta['is_time_based'],
            'is_track': meta['is_track'],
            'unit': meta['unit'],
            'class_codes': sorted(meta['codes']),
            'total': len(ordered),
            'top': ordered[:limit],
        })

    options = {
        'disciplines': sorted({(g['event_type_name'], g['event_type_id']) for g in all_groups}, key=lambda x: (x[0] or '').lower()),
        'sexes': sorted({g['sex_name'] for g in all_groups}),
        'categories': sorted({g['category_name'] for g in all_groups}, key=lambda x: x.lower()),
        'classifications': sorted({c for g in all_groups for c in g['class_codes']}),
    }

    f_discipline = (filters.get('discipline') or '').strip().lower()
    f_sex = (filters.get('sex') or '').strip().lower()
    f_category = (filters.get('category') or '').strip().lower()
    f_class = (filters.get('classification') or '').strip().upper()

    selected = []
    for g in all_groups:
        if f_discipline not in ('', 'all') and f_discipline not in (g['event_type_name'].lower(), g['event_type_id'].lower()):
            continue
        if f_sex not in ('', 'all') and f_sex != g['sex_name'].lower():
            continue
        if f_category not in ('', 'all') and f_category != g['category_name'].lower():
            continue
        if f_class not in ('', 'all') and f_class not in g['class_codes']:
            continue
        selected.append(g)

    return {'groups': selected, 'options': options}


class RecordsView(APIView):
    """Records publicos: top marcas por disciplina, categoria, sexo y clasificacion funcional."""
    permission_classes = [permissions.AllowAny]
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        try:
            top = int(request.query_params.get('top', 3))
        except (TypeError, ValueError):
            top = 3
        top = max(1, min(top, 10))
        filters = {
            'discipline': request.query_params.get('discipline', ''),
            'sex': request.query_params.get('sex', ''),
            'category': request.query_params.get('category', ''),
            'classification': request.query_params.get('classification', ''),
        }
        data = _records_compute(limit=top, filters=filters)
        options = data['options']
        return Response({
            'filters': {
                'disciplines': [{'id': i, 'name': n} for n, i in options['disciplines']],
                'sexes': options['sexes'],
                'categories': options['categories'],
                'classifications': options['classifications'],
            },
            'summary': {'groups': len(data['groups'])},
            'groups': data['groups'],
        })


class AthleteBestMarksView(APIView):
    """Mejor marca del atleta por disciplina participada, con su posicion entre los records."""
    permission_classes = [permissions.AllowAny]
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        try:
            athlete = Athlete.objects.get(id=kwargs.get('pk'))
        except Athlete.DoesNotExist:
            return Response({'error': 'Atleta no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        data = _records_compute(limit=10000, filters={})
        bests = []
        aid = str(athlete.id)
        for g in data.get('groups', []):
            row = next((b for b in g['top'] if b['athlete_id'] == aid), None)
            if row is None:
                continue
            bests.append({
                'discipline_name': g['discipline_name'],
                'event_type_id': g['event_type_id'],
                'event_type_name': g['event_type_name'],
                'sex_name': g['sex_name'],
                'category_name': g['category_name'],
                'class_codes': g['class_codes'],
                'is_time_based': g['is_time_based'],
                'unit': g['unit'],
                'mark': row['mark'],
                'value': row['value'],
                'wind': row['wind'],
                'rank': row['rank'],
                'total': g['total'],
                'event_name': row['event_name'],
                'tournament_name': row['tournament_name'],
                'tournament_date': row['tournament_date'],
            })
        bests.sort(key=lambda b: (b['discipline_name'].lower(), b['event_type_name'].lower(),
                                  b['sex_name'].lower(), b['category_name'].lower()))
        return Response({
            'athlete_id': aid,
            'athlete_name': athlete.user.get_full_name() or athlete.user.email,
            'bests': bests,
        })


def parse_time_mark(mark):
    if mark is None or mark == '':
        return None
    try:
        return float(mark)
    except (ValueError, TypeError):
        pass
    try:
        parts = mark.replace(',', '.').split(':')
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except (ValueError, TypeError):
        pass
    return None


class CalculateFinalResultsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        tournament_event_id = request.data.get('tournament_event')
        if not tournament_event_id:
            return Response({'error': 'tournament_event es obligatorio'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tournament_event = TournamentEvent.objects.get(id=tournament_event_id)
        except TournamentEvent.DoesNotExist:
            return Response({'error': 'Prueba no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        athlete_events = AthleteEvent.objects.filter(
            tournament_event=tournament_event,
        ).select_related('registration__athlete')

        if not athlete_events.exists():
            return Response({'error': 'No hay atletas inscriptos en esta prueba'}, status=status.HTTP_400_BAD_REQUEST)

        is_time_based = tournament_event.event_type and tournament_event.event_type.is_time_based
        results_data = []

        for ae in athlete_events:
            athlete = ae.registration.athlete

            if ae.status == 'dnf':
                results_data.append({
                    'athlete': athlete,
                    'best_value': float('inf') if is_time_based else float('-inf'),
                    'best_mark': 'DNF',
                    'is_dnf': True, 'is_dns': False, 'is_dq': False,
                })
                continue
            if ae.status == 'dq':
                results_data.append({
                    'athlete': athlete,
                    'best_value': float('inf') if is_time_based else float('-inf'),
                    'best_mark': 'DQ',
                    'is_dnf': False, 'is_dns': False, 'is_dq': True,
                })
                continue
            if ae.status == 'withdrawn':
                results_data.append({
                    'athlete': athlete,
                    'best_value': float('inf') if is_time_based else float('-inf'),
                    'best_mark': 'DNS',
                    'is_dnf': False, 'is_dns': True, 'is_dq': False,
                })
                continue

            results = Result.objects.filter(athlete_event=ae, is_valid=True)
            if not results.exists():
                results_data.append({
                    'athlete': athlete,
                    'best_value': float('inf') if is_time_based else float('-inf'),
                    'best_mark': 'DNS',
                    'is_dnf': False, 'is_dns': True, 'is_dq': False,
                })
                continue

            if is_time_based:
                best = min(results, key=lambda r: r.value if r.value is not None else float('inf'))
            else:
                best = max(results, key=lambda r: r.value if r.value is not None else float('-inf'))

            best_value = best.value
            if best_value is None and best.mark:
                best_value = parse_time_mark(best.mark)

            results_data.append({
                'athlete': athlete,
                'best_value': best_value if best_value is not None else (float('inf') if is_time_based else float('-inf')),
                'best_mark': best.mark or str(best.value) if best.value else best.mark,
                'is_dnf': False, 'is_dns': False, 'is_dq': False,
            })

        results_data.sort(key=lambda r: r['best_value'], reverse=not is_time_based)

        created = []
        for i, data in enumerate(results_data):
            rank = i + 1
            is_infinite = data['best_value'] in (float('inf'), float('-inf'))
            final, _ = FinalResult.objects.update_or_create(
                tournament_event=tournament_event,
                athlete=data['athlete'],
                defaults={
                    'rank': None if is_infinite else rank,
                    'best_mark': data['best_mark'],
                    'is_dnf': data['is_dnf'],
                    'is_dns': data['is_dns'],
                    'is_dq': data['is_dq'],
                }
            )
            created.append(final)

        output = FinalResultSerializer(created, many=True)
        return Response({'message': f'{len(created)} posiciones calculadas', 'results': output.data}, status=status.HTTP_200_OK)


def _safe_filename(name, prefix):
    safe = re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_') or 'documento'
    return f'{prefix}_{safe}.pdf'


class EventStartListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .pdf import build_event_start_list_pdf
        event_pk = kwargs.get('event_pk')
        try:
            event = TournamentEvent.objects.select_related('tournament').get(id=event_pk)
        except TournamentEvent.DoesNotExist:
            return Response({'error': 'Prueba no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        pdf_bytes = build_event_start_list_pdf(event)
        if pdf_bytes is None:
            return Response({'error': 'Esta prueba no tiene atletas inscriptos para generar el Start List'}, status=status.HTTP_400_BAD_REQUEST)

        filename = _safe_filename(event.name, 'start_list')
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class EventFinalListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .pdf import build_final_list_pdf
        event_pk = kwargs.get('event_pk')
        try:
            event = TournamentEvent.objects.select_related('tournament').get(id=event_pk)
        except TournamentEvent.DoesNotExist:
            return Response({'error': 'Prueba no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        pdf_bytes = build_final_list_pdf(event)
        if pdf_bytes is None:
            return Response({'error': 'Esta prueba no tiene resultados finales para generar el PDF'}, status=status.HTTP_400_BAD_REQUEST)

        filename = _safe_filename(event.name, 'resultados_finales')
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

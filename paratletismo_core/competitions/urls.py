from django.urls import path
from . import views

urlpatterns = [
    path('registrations/', views.RegistrationListView.as_view(), name='registration_list'),
    path('registrations/<uuid:pk>/', views.RegistrationDetailView.as_view(), name='registration_detail'),
    path('registrations/<uuid:pk>/approve/', views.RegistrationApproveView.as_view(), name='registration_approve'),
    path('registrations/<uuid:pk>/reject/', views.RegistrationRejectView.as_view(), name='registration_reject'),
    path('registrations/my/', views.MyRegistrationsView.as_view(), name='my_registrations'),
    path('athlete/<uuid:pk>/registration-options/', views.AthleteRegistrationOptionsView.as_view(), name='athlete_registration_options'),
    path('events/<uuid:event_pk>/athlete-events/', views.AthleteEventListView.as_view(), name='athlete_event_list'),
    path('events/<uuid:event_pk>/register-athlete/', views.EventRegistrationView.as_view(), name='event_register_athlete'),
    path('events/<uuid:event_pk>/athlete-events/<uuid:pk>/', views.AthleteEventDetailView.as_view(), name='athlete_event_detail'),
    path('events/<uuid:event_pk>/judges/', views.JudgeAssignmentListView.as_view(), name='judge_assignment_list'),
    path('judges/<uuid:pk>/', views.JudgeAssignmentDetailView.as_view(), name='judge_assignment_detail'),
    path('judges/my/', views.MyJudgeAssignmentsView.as_view(), name='my_judge_assignments'),
    path('results/', views.ResultListView.as_view(), name='result_list'),
    path('results/<uuid:pk>/', views.ResultDetailView.as_view(), name='result_detail'),
    path('final-results/', views.FinalResultListView.as_view(), name='final_result_list'),
    path('final-results/<uuid:pk>/', views.FinalResultDetailView.as_view(), name='final_result_detail'),
    path('events/<uuid:event_pk>/final-results/public/', views.EventResultsPublicView.as_view(), name='event_results_public'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('disciplines/', views.DisciplineView.as_view(), name='discipline_list'),
    path('disciplines/<uuid:pk>/', views.DisciplineDetailView.as_view(), name='discipline_detail'),
    path('sexes/', views.SexView.as_view(), name='sex_list'),
    path('sexes/<uuid:pk>/', views.SexDetailView.as_view(), name='sex_detail'),
    path('categories/', views.CategoryView.as_view(), name='category_list'),
    path('categories/<uuid:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('classifications/', views.FunctionalClassificationView.as_view(), name='classification_list'),
    path('classifications/<uuid:pk>/', views.FunctionalClassificationDetailView.as_view(), name='classification_detail'),
    path('event-types/', views.EventTypeView.as_view(), name='event_type_list'),
    path('event-types/<uuid:pk>/', views.EventTypeDetailView.as_view(), name='event_type_detail'),
]

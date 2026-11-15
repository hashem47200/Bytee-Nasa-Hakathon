from django.urls import path
from . import views

urlpatterns = [
    # Multi-page views
    path('', views.home_view, name='home'),
    path('database/', views.missions_database_view, name='dataset_explorer'),
    path('vehicle/<slug:slug>/', views.vehicle_detail_view, name='vehicle_detail'),
    path('vehicle/<slug:slug>/quiz/', views.vehicle_quiz_view, name='vehicle_quiz'),
    path('certificate/', views.certificate_view, name='certificate'),
    path('certificate/<str:code>/download/', views.certificate_download_view, name='certificate_download'),
    path('certificate/<str:code>/rename/', views.certificate_rename_view, name='certificate_rename'),

    # Authentication views
    path('login/', views.crew_login_view, name='login'),
    path('register/', views.crew_register_view, name='register'),
    path('logout/', views.crew_logout_view, name='logout'),

    # Static data endpoint
    path('data.json', views.data_json_view, name='data_json'),
    path('api/data.json', views.data_json_view, name='api_data_json'),

    # Auth REST endpoints
    path('api/auth/csrf/', views.get_csrf_token, name='api_auth_csrf'),
    path('api/auth/register/', views.register_view, name='api_auth_register'),
    path('api/auth/login/', views.login_view, name='api_auth_login'),
    path('api/auth/logout/', views.logout_view, name='api_auth_logout'),
    path('api/auth/me/', views.current_user_view, name='api_auth_me'),

    # Educational content REST endpoints
    path('api/planets/', views.planets_list_view, name='api_planets_list'),
    path('api/categories/', views.planets_list_view, name='api_categories_list'),
    path('api/planets/<str:planet_identifier>/vehicles/', views.planet_vehicles_view, name='api_planet_vehicles'),
    path('api/categories/<str:planet_identifier>/vehicles/', views.planet_vehicles_view, name='api_category_vehicles'),
    path('api/vehicles/<int:vehicle_id>/story/', views.vehicle_story_view, name='api_vehicle_story'),
    path('api/vehicles/<int:vehicle_id>/questions/', views.vehicle_questions_view, name='api_vehicle_questions'),

    # Quiz submission REST endpoints
    path('api/questions/<int:question_id>/submit/', views.submit_answer_view, name='api_question_submit'),
    path('api/submit-answer/', views.submit_answer_view, name='api_submit_answer_generic'),

    # Progress REST endpoints
    path('api/user/achievements/', views.user_achievements_view, name='api_user_achievements'),
    path('api/user/progress/', views.user_progress_view, name='api_user_progress'),
]

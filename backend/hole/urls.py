from django.urls import path, include, re_path
from .views import *

urlpatterns = [
    path('logout', logout),
    path('login', LoginApi.as_view()),
    path("register", RegisterApi.as_view()),
    path("verify/<str:method>", VerifyApi.as_view()),
    path('email/<str:type>', EmailApi.as_view()),
    path("hole", HolesApi.as_view()),
    path("hole/<int:hole_id>", HolesApi.as_view()),
    path('floors', FloorsApi.as_view()),
    path('floors/<int:floor_id>', FloorsApi.as_view()),
    path('user/favorites', FavoritesApi.as_view()),
    path('reports', ReportsApi.as_view()),
    path('reports/<int:report_id>', ReportsApi.as_view()),
    path('images', upload_image),
    path('messages', MessagesApi.as_view()),
    path('messages/<int:message_id>', MessagesApi.as_view()),
    path('users/<int:user_id>', UsersApi.as_view()),
    path('users', UsersApi.as_view()),
    path('users/push-tokens', PushTokensAPI.as_view()),
    path('divisions', DivisionsApi.as_view()),
    path('divisions/<int:division_id>', DivisionsApi.as_view()),
    path('penalty', PenaltyApi.as_view()),
    path('penalty/<int:floor_id>', PenaltyApi.as_view()),
    path('siteinfo/active-user', get_active_user),
]


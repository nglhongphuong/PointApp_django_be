from django.contrib import admin
from django.urls import path, include
from . import views
from .admin import admin_site
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('user', views.UserViewSet, basename='user')
router.register('student', views.StudentViewSet, basename='student')
router.register('class_student', views.ClassStudentViewSet, basename='class_student')
router.register('major', views.MajorViewSet,basename='major')
router.register('faculty', views.FacultyViewSet, basename='faculty')
router.register('academic_year', views.AcademicYearViewSet, basename='academic_year')
router.register('semester', views.SemesterViewSet, basename='semester')
router.register('criteria', views.CriteriaViewSet, basename='criteria')
router.register('advisor', views.AdvisorViewSet, basename='advisor')
router.register('assistant', views.AssistantViewSet, basename='assistant')
router.register('extract_activity', views.ExtractActivityViewSet, basename='extract_activity')
router.register('comments', views.CommentViewSet, basename='comment')
router.register('detail_extract_activity',views.DetailExtractActivityViewSet, basename='detail_extract_activity')
router.register('register_extract_activity', views.RegisterDetailViewSet, basename='register_extract_activity')
router.register(r'stats', views.StatsViewSet, basename='stats')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', admin_site.urls),
]
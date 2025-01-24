from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import *

class UserSerializer(ModelSerializer):
    avatar = serializers.FileField(required=False)
    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        u.set_password(u.password)
        u.save()

        return u

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatar.url if instance.avatar else ''
        return data

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'avatar']
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

class FacultySerializer(ModelSerializer):
    class Meta:
        model = Faculty
        fields = ["name"]

class MajorSerializer(ModelSerializer):
    class Meta:
        model = Major
        fields = ["name"]

class ClassStudentSerializer(ModelSerializer):
    class Meta:
        model = ClassStudent
        fields = ["name"]

class StudentSerializer(ModelSerializer):
    class Meta:
        model = Student
        fields = ["id", "name", "user_info", "email", "gender", "dob"]

class UserDetailSerializer(UserSerializer):
    student = StudentSerializer(read_only=True)

    class Meta:
        model = UserSerializer.Meta.model
        fields = UserSerializer.Meta.fields + ['student']

class AcademicYearSerializer(ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ["year"]

class SemesterSerializer(ModelSerializer):
    class Meta:
        model = Semester
        fields = '__all__'

class CriteriaSerializer(ModelSerializer):
    class Meta:
        model = Criteria
        fields = '__all__'

class ExtractActivitySerializer(ModelSerializer):
    criteria = CriteriaSerializer(read_only=True)
    class Meta:
        model = ExtractActivity
        fields = '__all__'


class DetailExtractActivitySerializer(ModelSerializer):
    extract_activity = ExtractActivitySerializer(read_only=True)
    class Meta:
        model = DetailExtractActivity
        fields = '__all__'

class RegisterDetailExtractActivitySerializer(ModelSerializer):
    detail_extract_activity = DetailExtractActivitySerializer(read_only=True)
    class Meta:
        model = RegisterDetailExtractActivity
        fields = '__all__'


class AdvisorSerializer(ModelSerializer):
    user_info = UserSerializer(read_only=True)
    class Meta:
        model = Advisor
        fields = '__all__'

class AssistantSerializer(ModelSerializer):
    user_info = UserDetailSerializer(read_only=True)
    class Meta:
        model = Assistant
        fields = '__all__'


class CommentSerializer(ModelSerializer):
    user = UserSerializer()
    class Meta:
        model = Comment
        fields = ['id', 'content', 'created_date', 'updated_date', 'user']


class LikeSerializer(ModelSerializer):
    user = UserSerializer()
    class Meta:
        model = Like
        fields = ['id', 'user', 'extract_activity']
from django.db import models
from cloudinary.models import CloudinaryField
# Create your models here.

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", 'student'
        ASSISTANT = "ASSISTANT", 'assistant'
        ADVISOR = "ADVISOR", 'advisor'

    avatar = CloudinaryField('avatar', null=True)
    role = models.CharField(max_length=50, choices=Role, default=Role.STUDENT)
    created = models.DateField(auto_now_add=True)

    def str(self):
        return self.username

class Student(models.Model):
    user_info = models.OneToOneField(User, related_name="student", null=True, on_delete=models.SET_NULL)
    dob = models.DateField(null=True)
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=[('MALE','male'),('FEMALE', 'female')])
    email = models.CharField(max_length=255, null=False)
    class_student = models.ForeignKey('ClassStudent', related_name='students', on_delete=models.CASCADE, null=True)


    def __str__(self):
        return self.name

class Assistant(models.Model):
    user_info = models.OneToOneField(User, related_name="assistant", null=False, on_delete=models.CASCADE, primary_key=True)
    student_info = models.OneToOneField(Student, related_name="assistant", null=False, on_delete=models.CASCADE)

    def __str__(self):
        return  f"Assistant: {self.student_info.name}"

class Advisor(models.Model):
    user_info = models.OneToOneField(User, related_name="advisor", null=False, on_delete=models.CASCADE, primary_key=True)
    def __str__(self):
        return f"Advisor: {self.user_info.username}"


class ClassStudent(models.Model):
    name = models.CharField(max_length=50, null=False)
    major = models.ForeignKey('Major', related_name='classes', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Major(models.Model):
    name = models.CharField(max_length=100, null=False)
    faculty = models.ForeignKey('Faculty', related_name='major', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name

class Faculty(models.Model):
    name = models.CharField(max_length=100, null=False)

    def __str__(self):
        return self.name

class AcademicYear(models.Model):
    year = models.CharField(max_length=10)

    def __str__(self):
        return f"Acedemic Year {self.year}"

class Semester(models.Model):
    name = models.CharField(max_length=3)
    academic_year = models.ForeignKey('AcademicYear', related_name='semester', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'academic_year')

    def __str__(self):
        return f"Học kỳ {self.name} - {self.academic_year}"

class Criteria(models.Model):
    name = models.CharField(max_length=3)
    max_point = models.PositiveIntegerField(default=25)
    semester = models.ForeignKey('Semester', related_name="criteria", on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'semester')

    def __str__(self):
        return f"Điều {self.name} - {self.semester}"

class BaseModel(models.Model):
    created_date = models.DateField(auto_now_add=True, null=True)
    updated_date = models.DateField(auto_now=True, null=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True

class ExtractActivity(BaseModel):
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.CharField(max_length=255)
    criteria = models.ForeignKey('Criteria', related_name='extract_activity', on_delete=models.CASCADE)

    def __str__(self):
        return (f'Activity {self.name} \n'
                f'Start date {self.start_date} \n'
                f'End date {self.end_date} \n'
                f'Description {self.description} \n')


class Interaction(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    extract_activity = models.ForeignKey(ExtractActivity, on_delete=models.CASCADE)
    class Meta:
        abstract = True

class Comment(Interaction):
    content = models.CharField(max_length=255, null=False)
    def __str__(self):
        return self.content

class Like(Interaction):
    class Meta:
        unique_together = ('user', 'extract_activity')
    def __str__(self):
        return f'user: {self.user} - extract_activity: {self.extract_activity}'

class DetailExtractActivity(BaseModel):
    name = models.CharField(max_length=255)
    point = models.IntegerField(default=5)
    extract_activity = models.ForeignKey('ExtractActivity', related_name = 'detail_extract_activity', on_delete=models.CASCADE)
    students = models.ManyToManyField('Student', through='RegisterDetailExtractActivity', related_name='activities')


    def __str__(self):
        return f"id:{self.id} tên:{self.name} cộng:{self.point}đrl từ {self.extract_activity}"


class RegisterDetailExtractActivity(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", 'pending'
        CONFIRMED = "CONFIRMED", 'confirmed'
        CANCELED = "CANCELED", 'canceled'
    status = models.CharField(max_length=50, choices=Status, default=Status.PENDING)
    evidence = models.CharField(max_length=255, null=True)
    is_report_missing = models.BooleanField(default=False)


    student = models.ForeignKey('Student', related_name="student", on_delete=models.CASCADE)
    detail_extract_activity = models.ForeignKey('DetailExtractActivity', related_name="detail_activity",
                                                on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student.name} - {self.detail_extract_activity.name} - {self.status}"


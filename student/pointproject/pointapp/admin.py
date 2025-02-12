from django.contrib import admin
from django.shortcuts import render
from django.contrib.auth.models import Group, Permission
from .models import *
from django import forms
from django.utils.html import mark_safe, format_html
from django.urls import path
from django.db.models import Avg, Count, Sum
from . import perms


class PointAdminSite(admin.AdminSite):
    site_header = 'Hệ thống quản lý điểm rèn luyện sinh viên'

    def get_urls(self):
        return [
            path('point-stats/', self.point_stats),
        ] + super().get_urls()
    def point_stats(self,request):
        #Thong ke cho faculty
        faculties = Faculty.objects.all()
        faculty_stats = []
        for faculty in faculties:
            majors = faculty.major.all()
            classes = ClassStudent.objects.filter(major__in=majors)
            students = Student.objects.filter(class_student__in=classes)
            register_details = RegisterDetailExtractActivity.objects.filter(
                student__in=students,
                status=RegisterDetailExtractActivity.Status.CONFIRMED
            )
            total_points_all_students = 0
            #tinh tong diem tung sinh vien
            for student in students:
                total_points = register_details.filter(student=student).aggregate(
                    total_points=Sum('detail_extract_activity__point')
                )['total_points'] or 0
                total_points_all_students += total_points
            avg_points = 0
            num_students = len(students)
            if num_students > 0:
                avg_points = total_points_all_students / num_students
            faculty_stats.append({
                'faculty': faculty,
                'avg_points': avg_points,
            })
        faculty_data = [
                {"name": faculty['faculty'].name, "avg_points": faculty['avg_points'] or 0}
                for faculty in faculty_stats
        ]
        #Thong ke cho lop sinh vien
        classes = ClassStudent.objects.all()
        class_stats = []
        for c in classes:
            s = Student.objects.filter(class_student=c)
            register_details = RegisterDetailExtractActivity.objects.filter(
                student__in=s,
                status=RegisterDetailExtractActivity.Status.CONFIRMED
            )
            total_points_all_students = 0
            # tinh tong diem tung sinh vien
            for student in s:
                total_points = register_details.filter(student=student).aggregate(
                    total_points=Sum('detail_extract_activity__point')
                )['total_points'] or 0
                total_points_all_students += total_points
            avg_points = 0
            num_students = len(s)
            if num_students > 0:
                avg_points = total_points_all_students / num_students
            class_stats.append({
                'class':c,
                'avg_points': avg_points,
            })
            #Tính điểm rèn luyện trung bình từng lớp
        class_data = [
            {"name": c['class'].name, "avg_points": c['avg_points'] or 0}
            for c in class_stats
        ]

        #tinh diem ren luyen theo thanh tich:
        classifications = {
                    "Xuất sắc": 0,
                    "Tốt": 0,
                    "Khá": 0,
                    "Trung bình": 0,
                    "Yếu": 0,
                    "Kém": 0,
                }
        students = Student.objects.all()
        register_details = RegisterDetailExtractActivity.objects.filter(
            student__in=students,
            status=RegisterDetailExtractActivity.Status.CONFIRMED
        )
        for student in students:
            total_points = register_details.filter(student=student).aggregate(
                total_points=Sum('detail_extract_activity__point')
            )['total_points'] or 0
            # Phân loại theo tổng điểm
            classification = perms.classify_points(total_points)
            classifications[classification] += 1

        context = {
                'faculty_data': faculty_data,
                'class_data': class_data,
                'classifications': classifications,
            }
        return render(request, 'admin/point-stats.html', context)

admin_site = PointAdminSite(name='myadmin')

class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "is_active", "role"]
    search_fields = ["email"]

    def save_model(self, request, obj, form, change):
        if "password" in form.changed_data:
            obj.set_password(obj.password)

        super().save_model(request, obj, form, change)
        if obj.role == User.Role.ADVISOR:
            Advisor.objects.get_or_create(user_info=obj)
            Assistant.objects.filter(user_info=obj).delete()
        elif obj.role == User.Role.ASSISTANT:
            student_info = Student.objects.filter(user_info=obj).first()
            if student_info:
                Assistant.objects.get_or_create(user_info=obj, student_info=student_info)
            else:
                self.message_user(request, f"User {obj.email} không liên kết với Student nào. Không thể tạo Assistant.", level="error")

            Advisor.objects.filter(user_info=obj).delete()
        else:
            Advisor.objects.filter(user_info=obj).delete()
            Assistant.objects.filter(user_info=obj).delete()

    def delete_model(self, request, obj):
        Advisor.objects.filter(user_info=obj).delete()
        Assistant.objects.filter(user_info=obj).delete()
        super().delete_model(request, obj)


class StudentAdminForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = "__all__"

    # Đặt `user_info` không bắt buộc
    user_info = forms.ModelChoiceField(
        queryset=Student._meta.get_field('user_info').related_model.objects.all(),
        required=False,
    )

class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
    list_display = ["id","name", "email"]
    search_fields = ["name", "email", "id"]

    def Avatar_preview(self, obj):
        return format_html('<img src="{url}" />'.format(url=obj.avatar.url))

    Avatar_preview.short_description = 'Avatar'

class CriteriaAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "max_point", "semester_details"]

    def semester_details(self, obj):
        # Truy cập vào đối tượng semester và năm học liên quan
        return f"Học kỳ {obj.semester.name} Năm học - {obj.semester.academic_year.year}"
    semester_details.short_description = 'Học kỳ và năm học'


admin_site.register(AcademicYear)
admin_site.register(Semester)
admin_site.register(Criteria, CriteriaAdmin)
admin_site.register(User,UserAdmin)
admin_site.register(Faculty)
admin_site.register(Major)
admin_site.register(ClassStudent)
admin_site.register(Student, StudentAdmin)
admin_site.register(ExtractActivity)
admin_site.register(DetailExtractActivity)
admin_site.register(RegisterDetailExtractActivity)
admin_site.register(Assistant)
admin_site.register(Advisor)
admin_site.register(Group)
admin_site.register(Permission)
admin_site.register(Comment)
admin_site.register(Like)
# Register your models here.

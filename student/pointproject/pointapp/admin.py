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

    def point_stats(self, request):
        # Thống kê điểm theo khoa
        faculty_stats = (
            Faculty.objects.annotate(
                avg_points=Avg('major__classes__students__activities__point')
            )
        )

        # Chuẩn bị danh sách tên khoa và điểm trung bình
        faculty_data = [
            {"name": faculty.name, "avg_points": faculty.avg_points or 0}
            for faculty in faculty_stats
        ]

        # Tương tự với thống kê lớp
        class_stats = (
            ClassStudent.objects.annotate(
                avg_points=Avg('students__activities__point')
            )
        )

        class_data = [
            {"name": class_student.name, "avg_points": class_student.avg_points or 0}
            for class_student in class_stats
        ]

        # Chuẩn bị dữ liệu xếp loại
        student_points = (
            Student.objects.annotate(
                total_points=Sum('activities__point')
            )
        )
        classifications = {
            "Xuất sắc": 0,
            "Tốt": 0,
            "Khá": 0,
            "Trung bình": 0,
            "Yếu": 0,
            "Kém": 0,
        }

        # Đếm số lượng sinh viên theo từng loại
        for student in student_points:
            classification = perms.classify_points(student.total_points)
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
        # Lưu User trước
        super().save_model(request, obj, form, change)
        if obj.role == User.Role.ADVISOR:
            Advisor.objects.get_or_create(user_info=obj)
            # Xóa Assistant nếu tồn tại
            Assistant.objects.filter(user_info=obj).delete()
        elif obj.role == User.Role.ASSISTANT:
            # Kiểm tra xem User có liên kết với Student không
            student_info = Student.objects.filter(user_info=obj).first()
            if student_info:
                Assistant.objects.get_or_create(user_info=obj, student_info=student_info)
            else:
                self.message_user(request, f"User {obj.email} không liên kết với Student nào. Không thể tạo Assistant.", level="error")
            # Xóa Advisor nếu tồn tại
            Advisor.objects.filter(user_info=obj).delete()
        else:
            # Nếu role không phải Advisor hoặc Assistant, xóa bản ghi liên quan
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

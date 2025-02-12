from django.db.models import Sum
from rest_framework import viewsets, permissions, generics, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.viewsets import ViewSet
from urllib3 import request
from collections import defaultdict
from .models import *
from django.contrib.auth.models import Group
from .serializers import *
import cloudinary.uploader
from . import perms, utils


# Create your views here.

class UserViewSet(viewsets.ViewSet,
                  generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True).all()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.FileUploadParser)
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['register_user']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
        # return [permissions.AllowAny()]

    @action(methods=['get'], url_path='current-user', url_name='current-user', detail=False)
    def current_user(self, request):
        return Response(data=UserSerializer(request.user).data)

    @action(methods=['post'], url_path='register', detail=False)
    def register_user(self, request):
        try:
            data = request.data

            # Lấy email từ request
            email = request.data.get("email")
            if not email:
                return Response({"error": "Email không được để trống."}, status=status.HTTP_400_BAD_REQUEST)

            # Kiểm tra email trong bảng Student
            student = Student.objects.filter(email=email).first()
            if not student:
                return Response({"error": "Email không tồn tại trong danh sách sinh viên."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Kiểm tra xem Student đã được liên kết với tài khoản User chưa
            if student.user_info:
                return Response({"error": "Sinh viên này đã có tài khoản."}, status=status.HTTP_400_BAD_REQUEST)

            avatar = request.data.get("avatar")
            # new_avatar = cloudinary.uploader.upload(avatar, folder='PointApp_user/') if avatar else None

            new_user = User.objects.create_user(
                username=data.get("email"),
                email=data.get("email"),
                password=data.get("password"),
                avatar=avatar
                # new_avatar.get('secure_url') if new_avatar else None,
            )
            # Liên kết tài khoản User với Student
            student.user_info = new_user
            student.save()
            # Thêm vào nhóm phân quyền
            Group.objects.get(name='STUDENT').user_set.add(new_user)

            return Response(data=UserSerializer(new_user, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(dict(error=e.__str__()), status=status.HTTP_403_FORBIDDEN)

    @action(methods=['patch'], url_path='update', url_name='update', detail=True)
    def update_user(self, request, pk):
        try:
            user_before = self.get_object()
            avatar_file = request.data.get("avatar")
            passw = request.data.get("password")
            for fields, value in request.data.items():
                setattr(user_before, fields, value)
            # user_before.avatar = avatar_file
            # user_before.password = passw
            user_before.save()
            return Response(data=UserSerializer(user_before, context={'request': request}).data,
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response(dict(error=e.__str__()), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], url_path='profile', detail=True)
    def profile(self, request, pk):
        try:
            user = self.get_object()
            detail_user = UserDetailSerializer(user, context={'request': request}).data
            return Response(data=detail_user, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(dict(error=e.__str__()), status=status.HTTP_403_FORBIDDEN)


class StudentViewSet(viewsets.ViewSet,
                     generics.CreateAPIView,
                     generics.UpdateAPIView,
                     generics.ListAPIView,
                     generics.RetrieveAPIView):
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_permissions(self):
        if self.action in ['list_register']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    # xem danh sách điểm rèn luyện của 1 sinh viên đã đăng ký.
    @action(methods=['get'], url_path='list_register', detail=True)
    def list_register(self, request, pk):
        try:
            student = Student.objects.filter(user_info=request.user).first()

            register_details = RegisterDetailExtractActivity.objects.filter(status="PENDING", student=student)
            return Response(RegisterDetailExtractActivitySerializer(register_details, many=True).data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # xem thành tích 1 sinh viên
    @action(methods=['get'], url_path='list_point', detail=True)
    def list_point(self, request, pk):
        try:

            student = Student.objects.filter(pk=pk).first()
            if not student:
                return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)


            register_details = RegisterDetailExtractActivity.objects.filter(
                status="CONFIRMED", student=student
            )
# tổng điểm rèn luyện của sinh viên thuộc điều đó vd điều 3 - sinh viên A  : 30d
            criteria_points = defaultdict(int)
            for register_detail in register_details:
                detail = register_detail.detail_extract_activity # lấy chi tiết từ form đăng ký vd -> tham gia : 5 d
                criteria = detail.extract_activity.criteria# lấy "điều" từ chi tiết -> dieu 3

                criteria_points[criteria.id] += detail.point # tong điểm[điều được chọn] += tham gia:5 đ
                # tongDiem{ 'id_Dieu3':30 } > điều theo quy chế = 10 -> chọn 10
                # tongDiem{ 'id_Dieu4 :40 } < điều theo quy chế = 50 -> chọn 40
                # => total_points : 10+40=50 -> tổng điểm rèn luyên của sinh viên
            total_points = 0
            for criteria_id, points in criteria_points.items():
                criteria = Criteria.objects.get(id=criteria_id)  # Lấy `Criteria` để lấy `max_point`
                total_points += min(points, criteria.max_point)

            classification = perms.classify_points(total_points)

            response_data = {
                "student_id": student.id,
                "student_name": student.name,
                "total_points": total_points,
                "classification": classification,
                "activities": RegisterDetailExtractActivitySerializer(register_details, many=True).data,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # xem danh sách báo thiếu 1 sinh viên
    @action(methods=['get'], url_path='get_list_missing', detail=True)
    def get_list_missing(self, request, pk):
        try:
            student = Student.objects.filter(pk=pk).first()
            register_details = RegisterDetailExtractActivity.objects.filter(is_report_missing=True, student=student)
            return Response(RegisterDetailExtractActivitySerializer(register_details, many=True).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ClassStudentViewSet(viewsets.ViewSet,
                          generics.CreateAPIView,
                          generics.UpdateAPIView,
                          generics.ListAPIView,
                          generics.RetrieveAPIView):
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)
    queryset = ClassStudent.objects.all()
    serializer_class = ClassStudentSerializer
    permission_classes = [perms.ReadOnlyPermission]


class MajorViewSet(viewsets.ViewSet,
                   generics.CreateAPIView,
                   generics.UpdateAPIView,
                   generics.ListAPIView,
                   generics.RetrieveAPIView):
    queryset = Major.objects.all()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)
    serializer_class = MajorSerializer
    permission_classes = [perms.ReadOnlyPermission]


class FacultyViewSet(viewsets.ViewSet,
                     generics.CreateAPIView,
                     generics.UpdateAPIView,
                     generics.ListAPIView,
                     generics.RetrieveAPIView):
    queryset = Major.objects.all()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)
    serializer_class = FacultySerializer
    permission_classes = [perms.ReadOnlyPermission]

    @action(methods=['get'], url_path='get_list_missing', detail=True)
    def get_list_missing(self, request, pk):
        try:
            faculty = Faculty.objects.get(pk=pk)
            majors = Major.objects.filter(faculty=faculty)
            classes = ClassStudent.objects.filter(major__in=majors)
            student = Student.objects.filter(class_student__in=classes)

            student_id = request.query_params.get('student', None)

            register_details = RegisterDetailExtractActivity.objects.filter(is_report_missing=True, student__in=student)
            if student_id:
                register_details = register_details.filter(student_id=student_id)

            return Response(RegisterDetailExtractActivitySerializer(register_details, many=True).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AcademicYearViewSet(viewsets.ViewSet,
                          generics.CreateAPIView,
                          generics.UpdateAPIView,
                          generics.ListAPIView,
                          generics.RetrieveAPIView):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [perms.ReadOnlyPermission]

class SemesterViewSet(viewsets.ViewSet,
                      generics.CreateAPIView,
                      generics.UpdateAPIView,
                      generics.ListAPIView,
                      generics.RetrieveAPIView):
    queryset = Semester.objects.all()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)
    serializer_class = SemesterSerializer

    def get_permissions(self):
        if self.action in ['get_criteria', 'update', 'partial_update', 'create'] and self.request.method.__eq__('POST'):
            return [perms.IsInRole(allowed_roles=['ADVISOR', 'ASSISTANT'])]
        return [permissions.AllowAny()]

    @action(methods=['post', 'get'], url_path='get_criteria', detail=True)
    def get_criteria(self, request, pk):
        if request.method.__eq__('POST'):
            data = request.data
            c = Criteria.objects.create(
                name=data.get("name"),
                max_point=data.get("max_point"),
                semester=self.get_object()
            )
            return Response(CriteriaSerializer(c).data)
        else:
            a = self.get_object().criteria
            return Response(CriteriaSerializer(a, many=True).data)


class CriteriaViewSet(viewsets.ViewSet,
                      generics.UpdateAPIView,
                      generics.ListAPIView,
                      generics.RetrieveAPIView,
                      generics.DestroyAPIView):
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)
    queryset = Criteria.objects.all()
    serializer_class = CriteriaSerializer

    def get_permissions(self):
        if self.action in ['get_activity', 'update', 'partial_update'] and self.request.method.__eq__('POST'):
            return [perms.IsInRole(allowed_roles=['ADVISOR', 'ASSISTANT'])]
        return [permissions.AllowAny()]

    @action(methods=['post', 'get'], url_path='get_activity', detail=True)
    def get_activity(self, request, pk):
        if not self.get_object():
            return Response({"error": "Chua co data."}, status=status.HTTP_400_BAD_REQUEST)
        if request.method.__eq__('POST'):
            data = request.data
            new_extract_activity = ExtractActivity.objects.create(
                name=data.get("name"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                description=data.get("description"),
                criteria=self.get_object()
            )
            return Response(ExtractActivitySerializer(new_extract_activity).data)
        else:
            a = self.get_object().extract_activity.filter(active=True)
            return Response(ExtractActivitySerializer(a, many=True).data)

# danh sách điểm của các chi tiết hoạt đông thuộc điều ...
    @action(methods=['get'], url_path='detail_training_point', detail=True)
    def detail_training_point(self, request, pk=None):
        criteria = self.get_object()
        if not criteria:
            return Response({"error": "Chưa có dữ liệu cho điều kiện này."}, status=status.HTTP_400_BAD_REQUEST)
        extract_activities = criteria.extract_activity.filter(active=True)
        response_data = {
            "ten_dieu": criteria.name,
            "hoat_dong": []
        }

        for activity in extract_activities:
            activity_data = {
                "ten_hoat_dong": activity.name,
                "ngay_bat_dau": activity.start_date,
                "ngay_ket_thuc": activity.end_date,
                "mo_ta": activity.description,
                "chi_tiet_hoat_dong": []
            }


            for detail in activity.detail_extract_activity.all():
                detail_data = {
                    "ten_hoat_dong": detail.name,
                    "diem_tham_gia": detail.point,
                }

                activity_data["chi_tiet_hoat_dong"].append(detail_data)

            # Thêm hoạt động vào danh sách kết quả
            response_data["hoat_dong"].append(activity_data)

        return Response(response_data)
class ExtractActivityViewSet(viewsets.ViewSet,
                             generics.ListAPIView,
                             generics.DestroyAPIView,
                             generics.UpdateAPIView,
                             generics.RetrieveAPIView):
    queryset = ExtractActivity.objects.all()
    serializer_class = ExtractActivitySerializer
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)

    def get_queryset(self):
        queryset = ExtractActivity.objects.all()
        criteria = self.request.query_params.get('criteria', None)
        if criteria is not None:
            queryset = queryset.filter(criteria=criteria)
        q = self.request.query_params.get('q', None)
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset

    def get_permissions(self):
        if self.action in ['get_comments', 'get_like', 'get_detail_activity'] and self.request.method in ['POST']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [perms.IsInRole(allowed_roles=['ADVISOR', 'ASSISTANT'])]
        return [permissions.AllowAny()]

    @action(methods=['get', 'post'], url_path='comments', detail=True)
    def get_comments(self, request, pk):
        if request.method.__eq__('POST'):
            content = request.data.get('content')
            c = Comment.objects.create(content=content, user=request.user, extract_activity=self.get_object())

            return Response(CommentSerializer(c).data)
        else:
            comments = self.get_object().comment_set.select_related('user').filter(active=True)

            return Response(CommentSerializer(comments, many=True).data)

    @action(methods=['get', 'post'], url_path='likes', detail=True)
    def get_like(self, request, pk):
        if request.method.__eq__('POST'):
            l = Like.objects.create(user=request.user, extract_activity=self.get_object())
            return Response(LikeSerializer(l).data)
        else:
            l = self.get_object().like_set.select_related('user').filter(active=True)
            likes_count = l.count()  # Đếm số lượt thích
            return Response({
                'likes_count': likes_count,
                'likes': LikeSerializer(l, many=True).data  # Nếu bạn muốn trả về chi tiết các lượt thích
            })

    @action(methods=['get', 'post'], url_path='detail_activity', detail=True)
    def get_detail_activity(self, request, pk):
        if request.method.__eq__('POST'):
            data = request.data
            d = DetailExtractActivity.objects.create(
                name=data.get("name"),
                point=data.get("point"),
                extract_activity=self.get_object()
            )
            return Response(DetailExtractActivitySerializer(d).data)
        else:
            a = self.get_object().detail_extract_activity
            return Response(DetailExtractActivitySerializer(a, many=True).data)
# lay toan bo danh sach sinh vien can diem danh - pending dua tren hoat dong do
    @action(methods=['get'], url_path='get_register_detail_activity', detail=True)
    def get_register_detail_activity(self, request,pk):
        extract_activity = self.get_object()
        pending_list = RegisterDetailExtractActivity.objects.filter(
            detail_extract_activity__extract_activity=extract_activity,
            status=RegisterDetailExtractActivity.Status.PENDING
        )
        serializer = RegisterDetailExtractActivitySerializer(pending_list, many=True)
        return Response(serializer.data)


class DetailExtractActivityViewSet(viewsets.ViewSet,
                                   generics.ListAPIView,
                                   generics.DestroyAPIView,
                                   generics.UpdateAPIView,
                                   generics.RetrieveAPIView):
    queryset = DetailExtractActivity.objects.all()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)
    serializer_class = DetailExtractActivitySerializer

    def get_permissions(self):
        if self.action in ['register_detail_activity', 'missing_detail_activity'] and self.request.method in ['POST']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'create', 'partial_update', 'destroy']:
            return [perms.IsInRole(allowed_roles=['ADVISOR', 'ASSISTANT'])]
        return [permissions.AllowAny()]

    # đăng ký hoạt động của sinh viên
    @action(methods=['post'], url_path='register_detail_activity', detail=True)
    def register_detail_activity(self, request, pk):
        try:
            # Lấy dữ liệu từ request
            if request.user.is_superuser:
                return Response(
                    {"error": "Superusers are not allowed to register for activities."},
                    status=status.HTTP_403_FORBIDDEN
                )
            data = request.data

            # Lấy Student từ user hiện tại
            try:
                student = Student.objects.filter(
                    user_info=request.user).first()  # Đảm bảo 'user' là trường liên kết đến user
            except Student.DoesNotExist:
                return Response(
                    {"error": "Student not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            print(f'ok nha: {self.get_object().extract_activity}\n'
                  f'student: {student}')
            extract_activity = self.get_object().extract_activity
            # Kiểm tra xem student đã từng đăng ký DetailExtractActivity nào thuộc ExtractActivity này chưa
            has_registered = DetailExtractActivity.objects.filter(
                extract_activity=extract_activity,
                students=student  # Đảm bảo sử dụng student.id
            ).first()

            if has_registered:
                return Response(
                    {"error": "Bạn đã đăng ký một chi tiết hoạt động trong hoạt động này rồi!."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            register = RegisterDetailExtractActivity.objects.create(
                evidence=data.get("evidence"),
                student=student,
                detail_extract_activity=self.get_object()
            )
            return Response({"message": "Đăng ký thành công."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    # báo thiếu của 1 sinh viên
    @action(methods=['post'], url_path='missing_detail_activity', detail=True)
    def missing_detail_activity(self, request, pk):
        try:
            # Lấy dữ liệu từ request
            if request.user.is_superuser:
                return Response(
                    {"error": "Superusers are not allowed to register for activities."},
                    status=status.HTTP_403_FORBIDDEN
                )
            data = request.data

            # Lấy Student từ user hiện tại
            try:
                student = Student.objects.filter(
                    user_info=request.user).first()
            except Student.DoesNotExist:
                return Response(
                    {"error": "Student not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            exist_register = RegisterDetailExtractActivity.objects.filter(
                student=student,
                detail_extract_activity=self.get_object(),
            ).first()
            if exist_register and exist_register.status != "CONFIRMED":
                exist_register.evidence = data.get("evidence")
                exist_register.status = "PENDING"
                exist_register.is_report_missing = True
                exist_register.save()
            else:
                register = RegisterDetailExtractActivity.objects.create(
                    evidence=data.get("evidence"),
                    student=student,
                    detail_extract_activity=self.get_object(),
                    is_report_missing=True
                )
            return Response({"message": "Đăng ký thành công."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    # xem danh sách báo thiếu
    @action(methods=['get'], url_path='get_list_missing', detail=True)
    def get_list_missing(self, request, pk):
        try:
            register_details = RegisterDetailExtractActivity.objects.filter(detail_extract_activity=self.get_object(),
                                                                            is_report_missing=True)
            return Response(RegisterDetailExtractActivitySerializer(register_details, many=True).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RegisterDetailViewSet(viewsets.ViewSet,
                            generics.RetrieveAPIView,
                            generics.UpdateAPIView,
                            generics.ListAPIView,
                            generics.DestroyAPIView):
    queryset = RegisterDetailExtractActivity.objects.all()
    serializer_class = RegisterDetailExtractActivitySerializer
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), perms.IsInRole(allowed_roles=['STUDENT'])]
        elif self.action in [
            'update',
            'destroy',
            'partial_update',
            'confirm_register_detail_activity',
            'cancel_register_detail_activity'
        ]:
            return [permissions.IsAuthenticated(), perms.IsInRole(allowed_roles=['ADVISOR', 'ASSISTANT'])]
        return [permissions.IsAuthenticated()]

    @action(methods=['post'], url_path='confirm_register_detail_activity', detail=True)
    def confirm_register_detail_activity(self, request, pk):
        try:
            register_detail = self.get_object()
            if register_detail.status != "CONFIRMED":
                register_detail.status = "CONFIRMED"
                register_detail.save()
                return Response({'message': 'Xác nhận thành công'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Trạng thái không phải là PENDING, không thể xác nhận!'},
                                status=status.HTTP_400_BAD_REQUEST)
        except RegisterDetailExtractActivity.DoesNotExist:
            return Response({'error': 'Không tìm thấy chi tiết đăng ký'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['post'], url_path='cancel_register_detail_activity', detail=True)
    def cancel_register_detail_activity(self, request, pk):
        try:
            register_detail = self.get_object()
            # Kiểm tra trạng thái của đối tượng
            if register_detail.status != "CONFIRMED":
                register_detail.status = "CANCELED"
                register_detail.is_report_missing = "False"
                register_detail.save()
                return Response({'message': 'Xác nhận thành công'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Trạng thái không phải là PENDING, không thể xác nhận!'},
                                status=status.HTTP_400_BAD_REQUEST)
        except RegisterDetailExtractActivity.DoesNotExist:
            return Response({'error': 'Không tìm thấy chi tiết đăng ký'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommentViewSet(viewsets.ViewSet, generics.DestroyAPIView,
                     generics.UpdateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        if request.user == self.get_object().creator:
            return super().destroy(request, *args, **kwargs)

        return Response(status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, *args, **kwargs):
        if request.user == self.get_object().creator:
            return super().partial_update(request, *args, **kwargs)

        return Response(status=status.HTTP_403_FORBIDDEN)


class AdvisorViewSet(viewsets.ViewSet,
                     generics.CreateAPIView,
                     generics.UpdateAPIView,
                     generics.ListAPIView,
                     generics.RetrieveAPIView
                     ):
    queryset = Advisor.objects.all()
    serializer_class = AdvisorSerializer
    permission_classes = [perms.ReadOnlyPermission]


class AssistantViewSet(viewsets.ViewSet,
                       generics.CreateAPIView,
                       generics.UpdateAPIView,
                       generics.ListAPIView,
                       generics.RetrieveAPIView
                       ):
    queryset = Assistant.objects.all()
    serializer_class = AssistantSerializer
    permission_classes = [perms.ReadOnlyPermission]

class StatsViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in ['stats_faculty']:
            return [perms.IsInRole(allowed_roles=['ADVISOR'])]
        return [perms.IsInRole(allowed_roles=['ADVISOR', 'ASSISTANT'])]
    @action(methods=['get'], url_path='stats_faculty', detail=False)
    def stats_faculty(self, request):
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

            student_criteria_points = defaultdict(lambda: defaultdict(int))
            for register_detail in register_details:
                student_id = register_detail.student.id
                detail = register_detail.detail_extract_activity
                criteria_id = detail.extract_activity.criteria.id
                student_criteria_points[student_id][criteria_id] += detail.point

            student_points, total_points_all_students = utils.calculate_student_points(students, register_details)

            # Tính điểm trung bình
            avg_points = 0
            num_students = len(students)#số lượng sinh viên khoa được chọn
            if num_students > 0:
                avg_points = total_points_all_students / num_students

            # Thêm vào danh sách thống kê
            faculty_stats.append({
                'name': faculty.name,
                'avg_points': round(avg_points, 2),
            })
        return Response(faculty_stats, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='stats_class', detail=False)
    def stats_class(self, request):
        # Thống kê theo class
        classes = ClassStudent.objects.all()
        class_stats = []
        for c in classes:
            students = Student.objects.filter(class_student=c)
            register_details = RegisterDetailExtractActivity.objects.filter(
                student__in=students,
                status=RegisterDetailExtractActivity.Status.CONFIRMED
            )
            student_points, total_points_all_students = utils.calculate_student_points(students, register_details)
            avg_points = total_points_all_students / len(students) if students else 0
            class_stats.append({
                'class_name': c.name,
                'avg_points': avg_points,
            })
        return Response(class_stats, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='stats_rank', detail=False)
    def stats_rank(self, request):
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
        student_points, _ = utils.calculate_student_points(students, register_details)

        # Phân loại sinh viên theo tổng điểm
        for student_id, total_points in student_points.items():
            classification = perms.classify_points(total_points)
            classifications[classification] += 1
        result = [
            {"rank": rank, "count": count}
            for rank, count in classifications.items()
        ]
        return Response(result, status=status.HTTP_200_OK)

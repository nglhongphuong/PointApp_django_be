from collections import defaultdict
from django.db.models import Sum
from .models import *


def calculate_student_points(students, register_details):
    student_criteria_points = defaultdict(lambda: defaultdict(int))

    # Gom nhóm điểm theo sinh viên và tiêu chí
    for register_detail in register_details:
        student_id = register_detail.student.id
        detail = register_detail.detail_extract_activity
        criteria_id = detail.extract_activity.criteria.id
        student_criteria_points[student_id][criteria_id] += detail.point
#tổng điểm rèn luyện theo chi tiết hoạt động của sinh viên mã ID và theo tiêu chí ( vd: sinh viên A - điều 1: 50 đ)

    student_points = {}
    total_points_all_students = 0 #tính tổng toàn bộ để lấy giá trị chia trung bình toàn thể sinh viên được chọn
    for student in students:
        total_points = 0
        for criteria_id, points in student_criteria_points[student.id].items():
            criteria = Criteria.objects.get(id=criteria_id)
            total_points += min(points, criteria.max_point)
# (nếu điểm vươtj quá tiêu chí quy định sẽ lấy min của cột đó) vd điều 1: 20 -> nhưng sinh viên 30đ -> lấy min (20,30) => 20d

        student_points[student.id] = total_points
        total_points_all_students += total_points

    return student_points, total_points_all_students

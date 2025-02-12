from django.test import TestCase
from django.contrib.auth.models import Group

class GroupTestCase(TestCase):
    def setUp(self):
        # Tạo các nhóm trong cơ sở dữ liệu trước khi chạy test
        self.advisor_group = Group.objects.create(name='Advisor')
        self.assistant_group = Group.objects.create(name='Assistant')
        self.student_group = Group.objects.create(name='Student')

    def test_groups_creation(self):
        # Kiểm tra xem các nhóm có được tạo thành công không
        self.assertEqual(Group.objects.filter(name='Advisor').exists(), True)
        self.assertEqual(Group.objects.filter(name='Assistant').exists(), True)
        self.assertEqual(Group.objects.filter(name='Student').exists(), True)

    # Các test khác có thể sử dụng các nhóm đã tạo ở trên

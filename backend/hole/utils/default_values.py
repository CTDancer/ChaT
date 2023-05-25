"""
数据库默认值生成函数
"""
from datetime import datetime, timedelta

from django.conf import settings


def now():
    return datetime.now(settings.TIMEZONE)


def default_active_user_date():
    return now() - timedelta(days=1)


def default_permission():
    """
    silent 字典
        index：分区id （string） django的JSONField会将字典的int索引转换成str
        value：禁言解除时间
    """
    return {
        'superuser': '1970-01-01T00:00:00+00:00', #管理员权限：到期时间
        'admin': '1970-01-01T00:00:00+00:00',  # 超级管理员权限：到期时间
        'silent': {},  # 禁言
        'offense_count': 0
    }

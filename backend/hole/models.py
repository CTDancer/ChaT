from datetime import datetime

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils.dateparse import parse_datetime
from rest_framework.authtoken.models import Token
from .utils.auth import encrypt_email, many_hashes
from .utils.default_values import default_active_user_date, default_permission

class Division(models.Model):
    div = models.CharField(max_length=32, unique=True, default='校园生活')
    sec = models.CharField(max_length=32, unique=True, default='日常')
    description = models.TextField(null=True)
    pinned = models.JSONField(default=list)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'division'

# 帖子
class Hole(models.Model):
    poster = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    time_created = models.DateTimeField(auto_now_add=True, db_index=True)
    division = models.IntegerField(default=0, help_text="分区")
    likes = models.JSONField(default=list, help_text="点赞列表")
    favourites = models.JSONField(default=list, help_text="收藏列表")
    reply = models.IntegerField(db_index=True, default=0, help_text="楼层数")
    content = models.TextField(help_text="帖子内容", null='true')

    def __str__(self):
        return f'树洞#{self.pk}'

    class Meta:
        db_table = 'hole'


class Floor(models.Model):
    hole = models.ForeignKey(Hole, on_delete=models.CASCADE)
    content = models.TextField()
    shadow_text = models.TextField(default='')  # 去除markdown关键字的文本，方便搜索
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE)
    mention = models.ManyToManyField('self', blank=True, symmetrical=False,
                                     related_name='mentioned_by')
    time_created = models.DateTimeField(auto_now_add=True)
    time_updated = models.DateTimeField(auto_now=True)
    likes = models.JSONField(default=list)  # 点赞记录，主键列表
    deleted = models.BooleanField(default=False)  # 仅作为前端是否显示删除按钮的依据
    storey = models.IntegerField(default=0)  # 楼层数

    def __str__(self):
        return f"{self.content[:50]}"

    class Meta:
        db_table = 'floor'


class Report(models.Model):
    hole = models.ForeignKey(Hole, on_delete=models.CASCADE)
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE)
    reason = models.TextField()
    time_created = models.DateTimeField(auto_now_add=True)
    time_updated = models.DateTimeField(auto_now=True)
    dealed = models.BooleanField(default=False, db_index=True)
    dealed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  null=True)

    def __str__(self):
        return f"{self.hole}, 帖子{self.floor}\n理由: {self.reason}"

    class Meta:
        db_table = 'report'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Args:
            email: 明文
            password: 明文
        Returns:
            user
        """
        user = self.model(
            email = email,
            password = password,
            **extra_fields
        )
        # user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        user = self.create_user(email, password, **extra_fields)
        user.permission['superuser'] = settings.VERY_LONG_TIME
        user.save()
        return user

    def create_admin(self, email, password=None, **extra_fields):
        user = self.create_user(email, password, **extra_fields)
        user.permission['admin'] = settings.VERY_LONG_TIME
        user.save()
        return user


class User(AbstractBaseUser):
    email = models.CharField(max_length=1000, unique=True)
    password = models.CharField(max_length=128) 
    joined_time = models.DateTimeField(auto_now_add=True)
    nickname = models.CharField(max_length=32, blank=True)
    favorites = models.ManyToManyField(Hole, related_name='favored_by', blank=True)
    permission = models.JSONField(default=default_permission)
    following = models.ManyToManyField("self", blank=True)
    avatar = models.TextField(blank=True, null=True)
    bio = models.CharField(max_length=500, blank=True, default='这个人很懒，什么都没留下')

    USERNAME_FIELD = 'email'

    objects = UserManager()


    @property
    def is_superuser(self):
        now = datetime.now(settings.TIMEZONE)
        expire_time = parse_datetime(self.permission['superuser'])
        return expire_time > now

    @property
    def is_admin(self):
        now = datetime.now(settings.TIMEZONE)
        expire_time = parse_datetime(self.permission['admin'])
        return expire_time > now

    def is_silenced(self, division_id):
        now = datetime.now(settings.TIMEZONE)
        silent = self.permission['silent']
        division = str(division_id)  # JSON 序列化会将字典的 int 索引转换成 str
        if not silent.get(division):  # 未设置禁言，返回 False
            return False
        else:
            expire_time = parse_datetime(silent.get(division))
            return expire_time > now

    def __str__(self):
        return f"用户#{self.pk}"

    class Meta:
        db_table = 'user'


class Message(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="message_to", on_delete=models.CASCADE,
        db_index=True
    )
    message = models.TextField(default='')
    code = models.CharField(max_length=30, default='')
    data = models.JSONField(default=dict)
    has_read = models.BooleanField(default=False)
    time_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message

    class Meta:
        db_table = 'message'


class PushToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='push_tokens')
    service = models.CharField(max_length=16, db_index=True)  # apns or mipush
    device_id = models.CharField(max_length=128, unique=True)
    token = models.CharField(max_length=128)

    class Meta:
        db_table = 'push_token'


class OldUserFavorites(models.Model):
    uid = models.CharField(max_length=11)
    favorites = models.JSONField()


class ActiveUser(models.Model):
    date = models.DateField(default=default_active_user_date, unique=True)
    dau = models.IntegerField(default=0)  # 日活
    mau = models.IntegerField(default=0)  # 月活

    class Meta:
        db_table = 'active_user'

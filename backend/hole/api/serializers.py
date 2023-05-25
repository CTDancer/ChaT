from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.db.models import Case, When
from rest_framework import serializers

from ..models import Division, Hole, Floor, Report, Message, PushToken, ActiveUser, User
from ..utils.apis import find_mentions
from ..utils.auth import many_hashes
from ..utils.decorators import cache_function_call
from ..utils.default_values import now
from ..utils.exception import BadRequest, Forbidden, ServerError

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = User
        fields = ['user_id', 'nickname', 'favorites', 'permission', 'avatar', 'bio',
                  'joined_time', 'is_admin']

    def validate_permission(self, permission):
        for s in ['admin', 'silent']:
            if s not in permission:
                raise serializers.ValidationError(f'字段 {s} 不存在')
        return permission

    def validate_config(self, config):
        for s in ['show_folded', 'notify']:
            if s not in config:
                raise serializers.ValidationError(f'字段 {s} 不存在')
        return config


class PushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushToken
        fields = ['service', 'device_id', 'token']

    def validate_service(self, service):
        li = ['apns', 'mipush']
        if service not in li:
            raise serializers.ValidationError(f'字段需在 {li} 中')
        return service

    def create(self, validated_data):
        return PushToken.objects.create(**validated_data)


class BaseEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    nickname = serializers.CharField(required=False)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class EmailSerializer(BaseEmailSerializer):

    def validate_email(self, email):
        domain = email[email.find("@") + 1:]
        # 检查邮箱是否在白名单内
        if domain not in settings.EMAIL_WHITELIST:
            raise serializers.ValidationError('邮箱不在白名单内')
        return email


class RegisterSerializer(EmailSerializer):
    password = serializers.CharField()
    password2 = serializers.CharField()
    captcha = serializers.CharField(max_length=6, min_length=6)

    def validate_email(self, email):
        return email

    # # 判断密码是否合法
    # def validate_password(self, password):
    #     validate_password(password)
    #     return password

    # # 核实验证码
    # def validate(self, data):
    #     email = data['email']
    #     verification = data['verification']
    #     if not cache.get(email) or not cache.get(email) == verification:
    #         raise serializers.ValidationError('验证码错误')
    #     return data

    # 创建用户，并检查用户是否已经存在
    def create(self, validated_data):
        nickname = validated_data.get('nickname')
        email = validated_data.get('email')
        password = validated_data.get('password')
        # 校验用户名是否已存在
        if User.objects.filter(email=email).exists():
            raise BadRequest(detail='该用户已注册！如果忘记密码，请使用忘记密码功能找回')
        user = User.objects.create_user(nickname=nickname ,email=email, password=password)
        assert isinstance(user, User)
        cache.delete(email)  # 注册成功后验证码失效
        return user

    # 更新密码
    def update(self, instance, validated_data):
        instance.set_password(validated_data.get('password'))
        instance.save()
        return instance


class AdminAccountChangeSerializer(EmailSerializer):
    password = serializers.CharField()

    def validate_password(self, password):
        validate_password(password)
        return password

    def validate(self, data):
        email = data['email']
        return data

    def create(self, validated_data):
        nickname = validated_data.get('nickname')
        email = validated_data.get('email')
        password = validated_data.get('password')
        # 校验用户名是否已存在
        if User.objects.filter(email=email).exists():
            raise BadRequest(detail='该用户已注册！如果忘记密码，请使用忘记密码功能找回')
        user = User.objects.create_user(nickname=nickname, email=email, password=password)
        cache.delete(email)  # 注册成功后验证码失效
        return user

    def update(self, instance, validated_data):
        instance.set_password(validated_data.get('password'))
        instance.save()
        return instance


class DivisionSerializer(serializers.ModelSerializer):
    division_id = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = Division
        fields = ['division_id', 'div', 'sec', 'description', 'pinned']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        order = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(instance.pinned)]
        )  # Holes 按 pinned 的顺序排序
        holes_data = HoleSerializer(
            Hole.objects.filter(id__in=instance.pinned).order_by(order),
            many=True,
            context={'user': self.context.get('user')}
        ).data
        data['pinned'] = holes_data
        return data

    def update(self, instance, validated_data):
        instance.div = validated_data.get('div', instance.div)
        instance.sec = validated_data.get('sec', instance.sec)
        instance.description = validated_data.get('description', instance.description)
        instance.pinned = validated_data.get('pinned', instance.pinned)
        instance.save()
        return instance


class FloorGetSerializer(serializers.Serializer):
    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    hole_id = serializers.IntegerField(required=False, write_only=True, default=1)
    s = serializers.CharField(required=False, write_only=True)
    length = serializers.IntegerField(
        required=False, write_only=True,
        default=settings.PAGE_SIZE,
        max_value=settings.MAX_PAGE_SIZE,
        min_value=0
    )
    start_floor = serializers.IntegerField(
        required=False, write_only=True,
        default=0
    )
    reverse = serializers.BooleanField(default=False)


# 不序列化 mention 字段
class SimpleFloorSerializer(serializers.ModelSerializer):
    floor_id = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = Floor
        fields = ['floor_id', 'hole_id', 'content', 'nickname', 'avatar', 'time_updated',
                  'time_created', 'deleted', 'likes', 'storey']
        read_only_fields = ['floor_id', 'nickname', 'avatar', 'storey']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data

    @staticmethod
    def get_queryset(queryset):
        return queryset


class FloorSerializer(SimpleFloorSerializer):
    mention = SimpleFloorSerializer(many=True, read_only=True)

    class Meta:
        model = Floor
        fields = ['floor_id', 'hole_id', 'content', 'mention', 'nickname', 'avatar',
                  'time_updated', 'time_created', 'deleted', 'likes', 'storey']
        read_only_fields = ['floor_id', 'history', 'nickname', 'avatar', 'storey']

    @staticmethod
    def get_queryset(queryset):
        return queryset.prefetch_related('mention')

    def get_user(self):
        user = self.context.get('user')
        if not isinstance(user, get_user_model()):
            raise ServerError('FloorSerializer 实例化时应提供参数 context={"user": request.user}')
        return user

    def validate_special_tag(self, special_tag):
        user = self.get_user()
        if not user or not user.is_admin:
            raise Forbidden()
        return special_tag

    def validate_anonyname(self, anonyname):
        user = self.get_user()
        if not user.is_admin:
            raise Forbidden()
        return anonyname

    def create(self, validated_data):
        content = validated_data.get('content', '')
        special_tag = validated_data.get('special_tag', '')
        mentions = find_mentions(content)
        user = self.context.get('user')
        hole = self.context.get('hole')
        if not user or not hole:
            raise BadRequest(detail='创建floor需要在context中提供user和hole')
        nickname = user.nickname
        avatar = user.avatar
        hole.reply += 1
        hole.save()
        floor = Floor.objects.create(hole=hole, content=content, nickname=nickname, avatar=avatar,
                                     user=user, special_tag=special_tag, storey=hole.reply)
        floor.mention.set(mentions)
        return floor

    def to_representation(self, instance):
        # floor 使用缓存效果不好
        # @cache_function_call(f'floor#{instance.id}', settings.FLOOR_CACHE_SECONDS)
        def _inner_to_representation(self, instance):
            return super().to_representation(instance)

        data = _inner_to_representation(self, instance)
        user = self.context.get('user')
        if not user:
            print('[W] FloorSerializer 实例化时应提供参数 context={"user": request.user}')
        else:
            data['is_me'] = True if instance.user_id == user.id else False
            data['liked'] = True if user.id in instance.like_data else False
        return data


class FloorUpdateSerializer(FloorSerializer):
    like = serializers.CharField(required=False)

    class Meta:
        model = Floor
        fields = ['content', 'anonyname', 'fold', 'like', 'special_tag']
        extra_kwargs = {
            'content': {'required': False},
            'anonyname': {'required': False}
        }


class HoleSerializer(serializers.ModelSerializer):
    hole_id = serializers.IntegerField(source='id', read_only=True)
    division_id = serializers.IntegerField(default=1)
    length = serializers.IntegerField(
        required=False, write_only=True,
        default=settings.PAGE_SIZE,
        max_value=settings.MAX_PAGE_SIZE,
        min_value=1
    )
    start_time = serializers.DateTimeField(
        required=False, write_only=True,
        default=now  # 使用函数返回值，否则指向的是同一个对象
    )

    class Meta:
        model = Hole
        fields = ['hole_id', 'division_id', 'time_created', 'content',
                  'reply', 'length', 'start_time']

    # def to_representation(self, instance):
    #     """
    #     context 中传入 simple 字段，
    #         若为 True 则使用缓存并不返回所有与用户有关的数据
    #         若为 False 则不使用缓存，返回所有数据
    #     """

    #     def _inner_to_representation(self, instance):
    #         data = super().to_representation(instance)
    #         user = self.context.get('user')
    #         prefetch_length = self.context.get('prefetch_length',
    #                                            settings.FLOOR_PREFETCH_LENGTH)
    #         if not user:
    #             print('[W] HoleSerializer 实例化时应提供参数 context={"user": request.user}')
    #         else:
    #             # serializer
    #             serializer = SimpleFloorSerializer if simple else FloorSerializer
    #             context = None if simple else {'user': user}

    #             # prefetch_data
    #             queryset = instance.floor_set.order_by('id')[:prefetch_length]
    #             queryset = serializer.get_queryset(queryset)
    #             prefetch_data = serializer(queryset, many=True, context=context).data

    #             # first_floor_data
    #             first_floor_data = prefetch_data[0] if len(prefetch_data) > 0 else None

    #             # last_floor_data
    #             queryset = serializer.get_queryset(instance.floor_set)
    #             last_floor_data = serializer(queryset.last(), context=context).data

    #             data['floors'] = {
    #                 'first_floor': first_floor_data,
    #                 'last_floor': last_floor_data,
    #                 'prefetch': prefetch_data,
    #             }
    #         return data

    #     @cache_function_call(str(instance), settings.HOLE_CACHE_SECONDS)
    #     def _cached(self, instance):
    #         return _inner_to_representation(self, instance)

    #     simple = self.context.get('simple', False)
    #     if simple:
    #         return _cached(self, instance)
    #     else:
    #         return _inner_to_representation(self, instance)

    # @staticmethod
    # def get_queryset(queryset):
    #     return queryset.prefetch_related('tags')

    # def validate_division_id(self, division_id):
    #     @cache_function_call(division_id, 86400)
    #     def division_exists(division_id):
    #         return Division.objects.filter(pk=division_id).exists()

    #     if not division_exists(division_id):
    #         raise serializers.ValidationError('分区不存在', 400)
    #     else:
    #         return division_id

    # def update(self, instance, validated_data):
    #     instance.view = validated_data.get('view', instance.view)
    #     instance.division_id = validated_data.get('division_id', instance.division_id)
    #     instance.save()
    #     return instance


class HoleCreateSerializer(HoleSerializer):
    def create(self, validated_data):
        # 在添加外键前要保存 hole，否则没有id
        hole = Hole.objects.create(division_id=validated_data.get('division_id'))
        self.context.update({'hole': hole})
        floor_serializer = FloorSerializer(
            data=self.context.get('request_data'),
            context=self.context
        )
        floor_serializer.is_valid(raise_exception=True)
        floor_serializer.save()

        self.context.get('user').favorites.add(hole)  # 自动收藏自己发的树洞
        return hole


class ReportSerializer(serializers.ModelSerializer):
    report_id = serializers.IntegerField(source='id', read_only=True)
    floor = FloorSerializer()

    class Meta:
        model = Report
        fields = ['report_id', 'hole_id', 'floor', 'reason', 'time_created',
                  'time_updated', 'dealed']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['dealed_by'] = instance.dealed_by.nickname if instance.dealed_by else None
        return data


class MessageSerializer(serializers.ModelSerializer):
    message_id = serializers.IntegerField(source='id', read_only=True)
    clear_all = serializers.BooleanField(default=False, write_only=True)
    not_read = serializers.BooleanField(default=True, write_only=True)
    start_time = serializers.DateTimeField(default=now, write_only=True)

    class Meta:
        model = Message
        fields = ['message_id', 'message', 'code', 'data', 'has_read', 'time_created',
                  'clear_all', 'not_read', 'start_time']

    def update(self, instance, validated_data):
        instance.message = validated_data.get('message', instance.message)
        instance.has_read = validated_data.get('has_read', instance.has_read)
        instance.code = validated_data.get('code', instance.code)
        instance.data = validated_data.get('data', instance.data)
        instance.save()
        return instance


class ActiveUserSerializer(serializers.ModelSerializer):
    start_date = serializers.DateField(default=now, write_only=True)
    end_date = serializers.DateField(default='1970-01-01', write_only=True)

    class Meta:
        model = ActiveUser
        fields = ['date', 'dau', 'mau', 'start_date', 'end_date']

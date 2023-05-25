import asyncio
import base64
import binascii
import json
import secrets
from datetime import datetime, timedelta
from json import JSONDecodeError

import httpx
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.db import transaction, IntegrityError
from django.db.models import Case, When, Max, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Hole, Floor, Report, User, Message, Division, \
    PushToken, ActiveUser
from .api.serializers import HoleSerializer, FloorSerializer, \
    ReportSerializer, MessageSerializer, \
    UserSerializer, DivisionSerializer, FloorGetSerializer, RegisterSerializer, \
    EmailSerializer, BaseEmailSerializer, HoleCreateSerializer, \
    PushTokenSerializer, FloorUpdateSerializer, ActiveUserSerializer, AdminAccountChangeSerializer
from .api.tasks import send_email
from .utils.apis import find_mentions, exists_or_404
from .utils.auth import check_api_key, many_hashes
from .utils.permissions import OnlyAdminCanModify, OwnerOrAdminCanModify, \
    NotSilentOrAdminCanPost, AdminOrReadOnly, \
    AdminOrPostOnly, OwenerOrAdminCanSee, AdminOnly, IsAuthenticatedEx, SuperuserOnly
from .ws.utils import async_send_websocket_message_to_group

@api_view(["GET"])
@permission_classes([IsAuthenticatedEx])
def logout(request):
    request.auth.delete()
    Token.objects.create(user=request.user)
    return Response({"message": "登出成功"})

class VerifyApi(APIView):
    throttle_scope = 'email'

    @staticmethod
    def _set_verification_code(email: str) -> str:
        """
        设置验证码并返回
        """
        verification = secrets.randbelow(1000000)
        verification = str(verification).zfill(6)
        cache.set(email, verification, settings.VALIDATION_CODE_EXPIRE_TIME * 60)
        return verification

    def get(self, request, **kwargs):
        method = kwargs.get("method")

        serializer = EmailSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        nickname = serializer.validated_data.get('nickname')

        if method == "email":
            # 设置验证码并发送验证邮件
            verification = self._set_verification_code(email)
            base_content = (
                f'您的验证码是: {verification}\r\n'
                f'验证码的有效期为 {settings.VALIDATION_CODE_EXPIRE_TIME} 分钟\r\n'
                '如果您意外地收到了此邮件，请忽略它'
            )
            if not User.objects.filter(email=email).exists():
                # 用户不存在，注册邮件
                send_email.delay(
                    subject=f'{settings.SITE_NAME} 注册验证',
                    content=f'欢迎注册 {settings.SITE_NAME}，{base_content}',
                    receivers=[email],
                    nickname=nickname
                )
            else:  # 用户存在，重置密码
                send_email.delay(
                    subject=f'{settings.SITE_NAME} 重置密码',
                    content=f'您正在重置密码，{base_content}',
                    receivers=[email],
                    nickname=nickname
                )
            return Response({'message': '处理中'}, 202)
        elif method == "apikey":
            apikey = request.query_params.get("apikey")
            check_register = request.query_params.get("check_register")
            if not check_api_key(apikey):
                return Response({"message": "API Key 不正确！"}, 403)
            if not User.objects.filter(email=email).exists():
                if check_register:
                    return Response({"message": "用户未注册！"}, 200)
                else:
                    verification = self._set_verification_code(email)
                    return Response({'message': '验证成功', 'code': verification}, 200)
            return Response({'message': '用户已注册'}, 409)
        else:
            return Response({}, 404)


class LoginApi(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        username = request.data.get("nickname")

        user = None

        print('username:',username)

        if username and user is None:
            try:
                user = User.objects.get(nickname=username)
            except User.DoesNotExist:
                print("here")
                return Response({"message": "用户不存在！"}, 404)

        if email and user is None:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"message": "用户不存在！"}, 404)

        if password == user.password:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "message": "登录成功！",
                "userInfo": {"nickname": user.nickname, "email": user.email}
            })
        else:
            return Response({"message": "邮箱或密码错误！"}, 401)


class RegisterApi(APIView):
    def post(self, request):
        # print(request.data)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password = serializer.validated_data.get('password')
        email = serializer.validated_data.get('email')
        nickname = serializer.validated_data.get('nickname')

        if User.objects.filter(nickname=nickname).exists():
            return Response({"message": "用户名已存在！"}, 409)
        
        user = serializer.save()
        # assert isinstance(user, User)
        token = Token.objects.get_or_create(user=user)[0].key
        print(serializer.validated_data)

        return Response({'message': '注册成功', 'token': token}, 201)

    def put(self, request):
        email = request.data.get('email')
        user = get_object_or_404(User, email=email)
        serializer = RegisterSerializer(instance=user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "已重置密码"}, 200)

    def patch(self, request, **kwargs):
        user_id = request.data.get('user_id')
        email = request.data.get('email')
        # Identify the user in this order: user_id, email, then requester himself.
        if user_id:
            user = get_object_or_404(User, pk=user_id)
        elif email:
            user = get_object_or_404(User, email=email)
        else:
            user = request.user

        # Reject all requests from non-admin
        if not request.user.is_admin:
            return Response({"message": "无管理权限，不能重置密码"}, 401)

        self.check_object_permissions(request, user)

        # Validate the syntax
        serializer = AdminAccountChangeSerializer(instance=user, data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save the new password
        serializer.save()

        return Response({"message": "用户密码已被重置", "user_id": user.pk}, 200)


class EmailApi(APIView):
    throttle_scope = 'email'

    def post(self, request, **kwargs):
        serializer = BaseEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        nickname = serializer.validated_data.get('nickname')

        if kwargs.get('type') == 'password':
            password = request.data.get('password')
            if not password:
                return Response({'message': 'password 字段不存在'}, 400)
            send_email.delay(
                subject=f'{settings.SITE_NAME} 密码存档',
                content=(
                    f'您已成功注册{settings.SITE_NAME}，您选择了随机设置密码，密码如下：'
                    f'\r\n\r\n{password}\r\n\r\n'
                    '提示：服务器中仅存储加密后的密码，无须担心安全问题'
                ),
                receivers=[email],
                nickname=nickname
            )
            return Response({'message': '处理中'}, 202)
        else:
            raise Http404()


class DivisionsApi(APIView):
    permission_classes = [IsAuthenticatedEx, AdminOrReadOnly]

    def get(self, request, **kwargs):
        division_id = kwargs.get('division_id')
        if division_id:
            query_set = get_object_or_404(Division, id=division_id)
        else:
            query_set = Division.objects.all()

        serializer = DivisionSerializer(
            query_set,
            many=not division_id,
            context={'user': request.user}
        )
        return Response(serializer.data)

    @transaction.atomic
    def put(self, request, **kwargs):
        division_id = kwargs.get('division_id')
        division = get_object_or_404(Division, id=division_id)
        serializer = DivisionSerializer(division, data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class HolesApi(APIView):
    permission_classes = [NotSilentOrAdminCanPost]

    def get(self, request):
        # 获取单个帖子
        if request.query_params.get('id'):
            hole_id = int(request.query_params.get('id'))
            current_user = request.query_params.get('currentname')
            hole = get_object_or_404(Hole, id=hole_id)
            nickname = hole.poster.nickname
            avatar = hole.poster.avatar
            content = hole.content
            time_created = hole.time_created
            likes = hole.likes
            favourites = hole.favourites
            reply = Floor.objects.filter(hole__id=hole_id).count()
            isRed1 = 1 if current_user in likes else 0
            isRed2 = 1 if current_user in favourites else 0
            return Response({'id': hole_id, 'nickname': nickname, 'avatar': avatar, 'content': content, 'time_created': time_created, 
                            'likes': likes, 'favourites': favourites, 'reply': reply, 'isRed1': isRed1, 'isRed2': isRed2})
        

        index = int(request.query_params.get('index'))
        start_index = index*10
        end_index = (index + 1)*10

        current_user = request.query_params.get('currentname')
        
        if request.query_params.get('message') is not None:
            message = request.query_params.get('message')
            total = Hole.objects.filter(content__contains=message).count()
            Page = Hole.objects.filter(content__contains=message).order_by('-time_created')[start_index : end_index]
        elif request.query_params.get('division_id') is None:
            # 获取某个用户的所有帖子
            if request.query_params.get('favourite') is None:
                total = Hole.objects.filter(poster__nickname=current_user).count()
                Page = Hole.objects.filter(poster__nickname=current_user).order_by('-time_created')[start_index : end_index]
            # 获取某个用户收藏的所有帖子
            else:
                total = Hole.objects.filter(favourites__contains=[current_user]).count()
                Page = Hole.objects.filter(favourites__contains=[current_user]).order_by('-time_created')[start_index : end_index]
        # 获取某个分区的所有帖子
        else:
            division_id = int(request.query_params.get('division_id'))
            total = Hole.objects.filter(division=division_id).count()
            Page = Hole.objects.filter(division=division_id).order_by('-time_created')[start_index : end_index]

        if end_index > total:
            end_index = total
            allLoaded = True
        else:
            allLoaded = False

        posts = []

        for i in range(0, end_index-start_index):
            hole = Page[i]
            id = hole.id
            nickname = hole.poster.nickname
            avatar = hole.poster.avatar
            content = hole.content
            likes = hole.likes
            favourites = hole.favourites
            time_created = hole.time_created
            reply = Floor.objects.filter(hole__id=id).count()
            isRed1 = 1 if current_user in likes else 0
            isRed2 = 1 if current_user in favourites else 0
            post = {'id': id, 'nickname': nickname, 'avatar': avatar, 'content': content, 'likes': likes, 
                    'favourites': favourites, 'time_created': time_created, 'reply': reply,
                    'isRed1': isRed1, 'isRed2': isRed2}
            posts.append(post)

        return Response({'posts': posts, 'allLoaded': allLoaded}, 200)

    @transaction.atomic
    def post(self, request):
        content = request.data.get('content')
        nickname = request.data.get('nickname')
        user = get_object_or_404(User, nickname=nickname)
        division = request.data.get('division_id')

        hole = Hole.objects.create(poster=user, content=content, division=division)

        avatar = hole.poster.avatar

        total = Hole.objects.filter(division=division).count()
        print("total: ", total)
        print("index: ", request.data.get('index'))
        if (request.data.get('index') + 1)*10 < total:
            allLoaded = False
        else:
            allLoaded = True
        
        return Response({'message': '发表成功！', 'id': hole.id, 'allLoaded':allLoaded, 'avatar': avatar }, 201)

    @transaction.atomic
    def put(self, request):
        hole_id = request.data.get('id')
        print("hole_id: ", hole_id)
        hole = get_object_or_404(Hole, id=hole_id)

        likes = request.data.get('likes')
        favourites = request.data.get('favourites')
        content = request.data.get('content')

        print("likes: ", likes)
        print("favourites: ", favourites)

        if likes != None and (len(likes) != len(hole.likes)):
            print("likes: ", likes)
            print("hole.likes: ", hole.likes)
            hole.likes = likes
            print("hole.likes: ", hole.likes)
        if favourites != None and (len(favourites) != len(hole.favourites)):
            print("favourites: ", favourites)
            print("hole.favourites: ", hole.favourites)
            hole.favourites = favourites
            print("hole.favourites: ", hole.favourites)
        if content:
            hole.content = content

        hole.save()

        serializer = HoleSerializer(hole)
        return Response(serializer.data)

    # def delete(self, request, **kwargs):
    #     Hole.objects.filter(id=kwargs.get('hole_id', 1)).update(hidden=True)
    #     return Response({'message': '已隐藏'}, 200)

    def patch(self, request, **kwargs):
        hole_id = kwargs.get('hole_id')
        if hole_id:
            exists_or_404(Hole, pk=hole_id)
            key = f'hole_viewed_{hole_id}'
            value = cache.get(key, 0)
            cache.set(key, value + 1, 60)
            return Response({'message': '处理中'}, 202)
        return Response(None, 404)


class FloorsApi(APIView):
    permission_classes = [NotSilentOrAdminCanPost, OwnerOrAdminCanModify]

    def get(self, request):
        hole_id = request.query_params.get('hole_id')
        division_id = request.query_params.get('division_id')
        index = int(request.query_params.get('index'))
        current_user = request.query_params.get('currentname')
        start_index = index*10
        end_index = (index + 1)*10
        total = Floor.objects.filter(hole_id=hole_id).count()

        Page = Floor.objects.filter(hole_id=hole_id).order_by('time_created')[start_index : end_index]

        if end_index > total:
            end_index = total
            allLoaded = True
        else:
            allLoaded = False

        floors = []

        for i in range(0, end_index-start_index):
            floor = Page[i]
            id = floor.id
            nickname = floor.user.nickname
            avatar = floor.user.avatar
            content = floor.content
            storey = floor.storey
            time_created = floor.time_created
            deleted = floor.deleted
            likes = floor.likes
            isRed = 1 if current_user in likes else 0
            floor = {'id': id, 'nickname': nickname, 'avatar': avatar, 
                    'content': content, 'likes': likes, 
                    'deleted': deleted, 'time_created': time_created, 
                    'isRed': isRed, 'storey': storey}
            floors.append(floor)

        return Response({'floors': floors, 'allLoaded': allLoaded}, 200)

    @transaction.atomic
    def post(self, request):
        hole_id = int(request.data.get('hole_id'))
        division_id = int(request.data.get('division_id'))
        nickname = request.data.get('nickname')
        index = int(request.data.get('index'))

        total = Floor.objects.filter(hole__id=hole_id).count()
 
        if (index + 1)*10 < total:
            allLoaded = False
        else:
            allLoaded = True

        hole = get_object_or_404(Hole, id=hole_id)
        user = get_object_or_404(User, nickname=nickname)
        avatar = user.avatar

        hole.reply = Floor.objects.filter(hole__id=hole_id).count()
        print("reply:",hole.reply)
        hole.reply += 1

        max_storey = Floor.objects.filter(hole__id=hole_id, hole__division=division_id).aggregate(max_storey=Max('storey'))['max_storey']
        if max_storey is None:
            max_storey = 0

        floor = Floor.objects.create(hole=hole, user=user, content=request.data.get('content'), storey=max_storey+1)

        return Response({'message': '发表成功！', 'id': floor.id, 'allLoaded':allLoaded, 'avatar': avatar, 'storey': floor.storey }, 201)

    @transaction.atomic
    def put(self, request):
        floor_id = request.data.get('id')
        print("floor_id: ", floor_id)
        floor = get_object_or_404(Floor, id=floor_id)

        likes = request.data.get('likes')
        content = request.data.get('content')

        if likes != None and (len(likes) != len(floor.likes)):
            print("likes: ", likes)
            print("floor.likes: ", floor.likes)
            floor.likes = likes
            print("floor.likes: ", floor.likes)
        if content:
            print("content: ", content)
            floor.content = content
            print("floor content: ", floor.content)

        floor.save()

        serializer = HoleSerializer(floor)
        return Response(serializer.data)

        # floor_id = kwargs.get('floor_id')
        # floor = get_object_or_404(Floor, pk=floor_id)
        # serializer = FloorUpdateSerializer(data=request.data, context={'user': request.user})
        # serializer.is_valid(raise_exception=True)
        # data = serializer.validated_data

        # # 不检查权限
        # like = data.pop('like', '')
        # if like:
        #     if like == 'add' and request.user.pk not in floor.like_data:
        #         floor.like_data.append(request.user.pk)
        #     elif like == 'cancel' and request.user.pk in floor.like_data:
        #         floor.like_data.remove(request.user.pk)
        #     else:
        #         pass
        #     floor.like = len(floor.like_data)

        # # 属主或管理员
        # if data:
        #     self.check_object_permissions(request, floor)
        # content = data.pop('content', '')
        # if content:
        #     # 只允许管理员修改已删除的帖子
        #     if floor.deleted and not request.user.is_admin:
        #         return Response({"message": "不能修改已删除的帖子，目前只允许管理员修改它们"}, 403)
        #     floor.history.append({
        #         'content': floor.content,
        #         'altered_by': request.user.id,
        #         'altered_time': datetime.now(settings.TIMEZONE).isoformat()
        #     })
        #     floor.content = content
        #     mentions = find_mentions(content)
        #     floor.mention.set(mentions)
        # floor.fold = data.pop('fold', floor.fold)

        # # anonyname 和 special_tag 已在序列化器中校验
        # floor.anonyname = data.pop('anonyname', floor.anonyname)
        # floor.special_tag = data.pop('special_tag', floor.special_tag)

        # floor.save()

        # return Response(FloorSerializer(floor, context={'user': request.user}).data)

    @transaction.atomic
    def delete(self, request, **kwargs):
        floor_id = kwargs.get('floor_id')
        delete_reason = request.data.get('delete_reason')
        floor = get_object_or_404(Floor, pk=floor_id)
        self.check_object_permissions(request, floor)
        floor.history.append({
            'content': floor.content,
            'altered_by': request.user.pk,
            'altered_time': datetime.now(settings.TIMEZONE).isoformat()
        })
        if request.user == floor.user:  # 作者删除
            floor.content = '该内容已被作者删除'
        else:  # 管理员删除
            floor.content = delete_reason if delete_reason else '该内容因违反社区规范被删除'
        floor.deleted = True
        floor.save()
        serializer = FloorSerializer(floor, context={"user": request.user})
        return Response(serializer.data, 200)


class FavoritesApi(APIView):
    permission_classes = [IsAuthenticatedEx]

    def get(self, request):
        query_set = request.user.favorites.all()
        serializer = HoleSerializer(
            query_set, many=True,
            context={"user": request.user, 'simple': True}
        )
        return Response(serializer.data)

    def post(self, request):
        hole_id = request.data.get('hole_id')
        hole = get_object_or_404(Hole, pk=hole_id)
        request.user.favorites.add(hole)
        return Response({
            'message': '收藏成功',
            'data': request.user.favorites.values_list('id', flat=True)
        }, 201)

    def put(self, request):
        hole_ids = request.data.get('hole_ids')
        holes = Hole.objects.filter(pk__in=hole_ids)
        request.user.favorites.set(holes)
        return Response({
            'message': '修改成功',
            'data': request.user.favorites.values_list('id', flat=True)
        }, 200)

    def delete(self, request):
        hole_id = request.data.get('hole_id')
        hole = get_object_or_404(Hole, pk=hole_id)
        request.user.favorites.remove(hole)
        return Response({
            'message': '删除成功',
            'data': request.user.favorites.values_list('id', flat=True)
        }, 200)


class ReportsApi(APIView):
    permission_classes = [IsAuthenticatedEx, AdminOrPostOnly]

    def post(self, request):
        floor_id = request.data.get('floor_id')
        reason = request.data.get('reason')
        floor = get_object_or_404(Floor, pk=floor_id)
        if not reason or not reason.strip():
            return Response({'message': '举报原因不能为空'}, 400)
        report = Report.objects.create(
            hole_id=floor.hole_id,
            floor_id=floor_id,
            reason=reason
        )
        serializer = ReportSerializer(report)
        return Response(serializer.data, 201)

    def get(self, request, **kwargs):
        start_report = int(request.query_params.get('start_report', '0'))
        length = int(request.query_params.get('length', '0'))
        # 获取单个
        report_id = kwargs.get('report_id')
        if report_id:
            report = get_object_or_404(Report, pk=report_id)
            serializer = ReportSerializer(report)
            return Response(serializer.data)
        # 获取多个
        category = request.query_params.get('category', default='not_dealed')
        if category == 'not_dealed':
            queryset = Report.objects.filter(dealed=False)
        elif category == 'dealed':
            queryset = Report.objects.filter(dealed=True)
        elif category == 'all':
            queryset = Report.objects.all()
        else:
            return Response({'message': 'category 参数不正确'})
        queryset = queryset.order_by('-id')

        if length == 0:
            queryset = queryset[start_report:]
        else:
            queryset = queryset[start_report: start_report + length]

        serializer = ReportSerializer(queryset, many=True)
        return Response(serializer.data)

    def delete(self, request, **kwargs):
        report_id = kwargs.get('report_id')
        report = get_object_or_404(Report, pk=report_id)
        floor = report.floor

        if request.data.get('not_deal'):
            pass
        if request.data.get('fold'):
            floor.fold = request.data.get('fold')
        if request.data.get('delete'):
            delete_reason = request.data.get('delete')
            floor.history.append({
                'content': floor.content,
                'altered_by': request.user.pk,
                'altered_time': datetime.now(settings.TIMEZONE).isoformat()
            })
            floor.content = delete_reason
            floor.deleted = True
        if request.data.get('silent'):
            permission = floor.user.permission
            current_time_str = permission['silent'].get(
                str(floor.hole.division_id), '1970-01-01T00:00:00+00:00')
            current_time = parse_datetime(current_time_str)
            expected_time = \
                datetime.now(settings.TIMEZONE) + \
                timedelta(days=request.data.get('silent'))
            permission['silent'][str(floor.hole.division_id)] = max(
                current_time, expected_time).isoformat()
            floor.user.save()

        floor.save()
        report.dealed_by = request.user
        report.dealed = True
        report.save()
        return Response({'message': '举报处理成功'}, 200)

    def put(self, request):
        pass


class MessagesApi(APIView):
    permission_classes = [IsAuthenticatedEx, OwnerOrAdminCanModify, OwenerOrAdminCanSee]

    def post(self, request):
        floor = get_object_or_404(Floor, pk=request.data.get('to'))
        to_id = floor.user.pk

        if request.data.get('share_email'):
            code = 'share_email'
            message = f'用户看到了你发布的帖子\n{str(floor)}\n希望与你取得联系，TA的邮箱为：{request.user.email} '
        elif request.data.get('message'):
            code = 'message'
            message = request.data.get('message').strip()
            if not request.user.is_admin:
                return Response(None, 403)
            if not message:
                return Response({'message': 'message不能为空'}, 400)
        else:
            return Response(None, 400)

        Message.objects.create(user_id=to_id, message=message, code=code)
        return Response({'message': f'已发送通知，内容为：{message}'}, 201)

    def get(self, request, **kwargs):
        serializer = MessageSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        not_read = serializer.validated_data.get('not_read')
        start_time = serializer.validated_data.get('start_time')
        message_id = kwargs.get('message_id')
        # 获取单个
        if message_id:
            message = get_object_or_404(Message, pk=message_id)
            self.check_object_permissions(request, message)
            serializer = MessageSerializer(message)
            return Response(serializer.data)
        # 获取多个
        else:
            query_set = Message.objects.filter(user=request.user,
                                               time_created__lt=start_time).order_by('-pk')
            if not_read:
                query_set = query_set.filter(has_read=False)
            serializer = MessageSerializer(query_set, many=True)
            return Response(serializer.data)

    def put(self, request, **kwargs):
        message_id = kwargs.get('message_id')
        if message_id:
            instance = get_object_or_404(Message, pk=message_id)
            self.check_object_permissions(request, instance)
            serializer = MessageSerializer(instance=instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        else:
            serializer = MessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if serializer.validated_data.get('clear_all'):
                Message.objects.filter(user=request.user).update(has_read=True)
                return Response({'message': '已全部设为已读'}, 200)
        return Response({'message': '需要指定操作'}, 400)


class UsersApi(APIView):
    permission_classes = [OwnerOrAdminCanModify, OwenerOrAdminCanSee]

    def get(self, request, **kwargs):
        # 获得除admin以外的所有用户
        if request.query_params.get('all') is not None:
            users = User.objects.filter(Q(permission__admin='1970-01-01T00:00:00+00:00'))
            user_list = []
            for user in users:
                nickname = user.nickname
                if nickname == '该账号已注销':
                    continue
                avatar = user.avatar
                permission = 'user'
                if user.permission.get('superuser') != '1970-01-01T00:00:00+00:00':
                    permission = 'superuser'
                user_list.append({'nickname': nickname, 'avatar': avatar, 'permission': permission})
            return Response({'users': user_list}, 200)

        user_id = kwargs.get('user_id')
        if user_id:
            user = get_object_or_404(User, pk=user_id)
            self.check_object_permissions(request, user)
        else:
            nickname = request.query_params.get('nickname')
            user = get_object_or_404(User, nickname=nickname)
        email = user.email
        serializer = UserSerializer(user)
        print('permission: ', serializer.data['permission'])
        permission = 'user'
        if serializer.data['permission']['superuser'] != '1970-01-01T00:00:00+00:00':
            permission = 'superuser'
        if serializer.data['permission']['admin'] != '1970-01-01T00:00:00+00:00':
            permission = 'admin'
        print(permission)
        return Response({'data': serializer.data, 'permission': permission, 'email': email}, 200)

    def put(self, request, **kwargs):
        user_id = kwargs.get('user_id')
        if user_id:
            user = get_object_or_404(User, pk=user_id)
            self.check_object_permissions(request, user)
        else:
            print('originalname', request.data.get('originalname'))
            if request.data.get('originalname') is not None:
                nickname = request.data.get('originalname')
            else:
                nickname = request.data.get('nickname')
            print(nickname)
            user = get_object_or_404(User, nickname=nickname)

        if request.data.get('cancellation') is not None:
            user.nickname = '该账号已注销'
            user.avatar = None
            user.bio = '这个人很懒，什么也没留下'
            user.permission['superuser'] = '1970-01-01T00:00:00+00:00'
            user.password = 'null'

            user.save()
            serializer = UserSerializer(user)
            return Response(serializer.data)

        nickname = request.data.get('nickname')
        favorites = request.data.get('favorites')
        config = request.data.get('config')
        permission = request.data.get('permission')
        avatar = request.data.get('avatar')
        bio = request.data.get('bio')
        email = request.data.get('email')
        password = request.data.get('password')

        # 个人中心修改信息
        if request.data.get('originalname') is not None:
            if nickname:
                user.nickname = nickname
            if email:
                user.email = email
            if bio:
                user.bio = bio

        if permission:
            if permission == 'user':
                user.permission['superuser'] = '1970-01-01T00:00:00+00:00'
            else:
                user.permission['superuser'] = '9999-12-31T00:00:00+00:00'
        if favorites:
            user.favorites.set(favorites)
        if config:
            user.config = config
        if nickname:
            user.nickname = nickname
        if avatar:
            user.avatar = avatar
        if password:
            user.password = password

        user.save()

        serializer = UserSerializer(user)
        return Response(serializer.data)

    def follow(self, request, **kwargs):
        user = get_object_or_404(User, pk=kwargs.get('user_id'))    # 被关注的用户
        follower = request.user     # 当前用户
        if user.id != follower.id:
            follower.following.set(user)
        follower.save()
        serialzer = UserSerializer(follower)
        return Response(serialzer.data)


class PushTokensAPI(APIView):
    permission_classes = [IsAuthenticatedEx]

    def get(self, request):
        if not request.user.is_admin:
            return Response(None, 403)
        if request.query_params.get('user_id'):
            user = get_object_or_404(User, pk=request.query_params.get('user_id'))
        else:
            user = request.user
        tokens = PushToken.objects.filter(user=user)
        service = request.query_params.get('service')
        if service:
            tokens = PushToken.objects.filter(service=service)
        return Response(PushTokenSerializer(tokens, many=True).data)

    def put(self, request):
        device_id = request.data.get('device_id', '')
        service = request.data.get('service', '')
        token = request.data.get('token', '')
        push_token = PushToken.objects.filter(device_id=device_id,
                                              user=request.user).first()
        if not push_token:
            push_token = PushToken.objects.create(
                device_id=device_id,
                service=service,
                token=token,
                user=request.user
            )
            code = 201
        else:
            push_token.token = token or push_token.token
            push_token.service = service or push_token.service
            push_token.save()
            code = 200
        serializer = PushTokenSerializer(push_token)
        return Response(serializer.data, code)

    def delete(self, request):
        device_id = request.data.get('device_id', '')
        PushToken.objects.filter(user=request.user, device_id=device_id).delete()
        return Response(None, 204)


class PenaltyApi(APIView):
    permission_classes = [SuperuserOnly]

    def post(self, request, **kwargs):
        self.check_object_permissions(request, request.user)
        floor = get_object_or_404(Floor, pk=kwargs.get('floor_id'))
        user = floor.user

        try:
            penalty_level = int(request.data.get('penalty_level'))
            division_id = request.data.get('division_id')
        except (ValueError, TypeError):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if penalty_level > 0:
            penalty_multiplier = {
                1: 1,
                2: 5,
                3: 999
            }.get(penalty_level, 1)

            offense_count = user.permission.get('offense_count', 0)
            offense_count += 1
            user.permission['offense_count'] = offense_count

            new_penalty_date = \
                datetime.now(settings.TIMEZONE) + \
                timedelta(days=offense_count * penalty_multiplier)
            user.permission['silent'][str(division_id)] = new_penalty_date.isoformat()

        user.save(update_fields=['permission'])
        serializer = UserSerializer(user)
        return Response(serializer.data)

class Promote_DegradeAPI(APIView):
    permission_classes = [AdminOnly]

    def promote(self, request, **kwargs):
        self.check_object_permissions(request, request.user)
        user = get_object_or_404(User, pk=kwargs.get('user_id'))
        user.permission['superuser'] = settings.VERY_LONG_TIME
        user.save()

        serializer = UserSerializer(user)
        return Response(serializer.data)

    def degrade(self, request, **kwargs):
        self.check_object_permissions(request, request.user)
        user = get_object_or_404(User, pk=kwargs.get('user_id'))
        user.permission['superuser'] = '1970-01-01T00:00:00+00:00'
        user.save()

        serializer = UserSerializer(user)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedEx])
def get_active_user(request):
    serializer = ActiveUserSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    queryset = ActiveUser.objects.filter(
        date__gte=data['end_date'], date__lte=data['start_date']
    ).order_by('-id')
    serializer = ActiveUserSerializer(queryset, many=True)
    return Response(serializer.data)


async def upload_image(request):
    image_b64 = json.loads(request.body.decode()).get('image')
    if not image_b64:
        return JsonResponse({'message': 'image 字段不能为空'}, status=400)
    try:
        image = base64.b64decode(image_b64)
    except binascii.Error:
        return JsonResponse({'message': 'base64 格式有误'}, status=400)
    if len(image) > settings.MAX_IMAGE_SIZE * 1024 * 1024:
        return JsonResponse({'message': f'图片大小不能超过 {settings.MAX_IMAGE_SIZE} MB'}, status=400)

    if not settings.CHEVERETO_URL:
        return JsonResponse({'message': '暂不支持图片上传'}, status=501)

    try:
        async with httpx.AsyncClient(timeout=10, proxies=settings.HTTP_PROXY) as client:
            li = await asyncio.gather(
                async_send_websocket_message_to_group(
                    f'user-{request.user.id}',
                    {'message': '处理中'}
                ),
                client.post(
                    url=settings.CHEVERETO_URL,
                    files={'source': image},
                    data={'key': settings.CHEVERETO_TOKEN}
                )
            )
    except httpx.RequestError as e:
        return JsonResponse({'message': f'网络错误: {e}'}, status=500)
    r = li[1]
    if r.status_code == 200:
        r = r.json()['image']
        return JsonResponse({
            'message': '上传成功',
            'url': r['url'],
            'medium': r.get('medium', {}).get('url', r['url']),
            'thumb': r.get('thumb', {}).get('url', r['url'])
        })
    else:
        try:
            message = r.json()['error']['message']
        except:
            message = '上传失败'
        return JsonResponse({'message': message}, status=500)

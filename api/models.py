import uuid  # UUID 생성용

from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.db import models


class UserManager(BaseUserManager):
    """
    Custom UserManager for handling Kakao-based login and superuser creation
    """
    def create_user(self, kakao_id, username, email=None):
        if not kakao_id:
            raise ValueError("카카오 ID는 필수입니다.")
        # if not username:
        #     raise ValueError("사용자 이름은 필수입니다.")
        
        user = self.model(
            kakao_id=kakao_id,
            nickname=nickname,
            connected_at=connected_at,
            # email=self.normalize_email(email),
            # username=username,
        )
        user.save(using=self._db)
        return user

    def create_superuser(self, kakao_id):
        # if not email:
        #     raise ValueError("관리자 이메일은 필수입니다.")
        # if not username:
        #     raise ValueError("관리자 이름은 필수입니다.")
        # if not password:
        #     raise ValueError("관리자 계정을 생성하려면 비밀번호가 필요합니다.")
        if not kakao_id:
            raise ValueError("관리자 계정을 생성하려면 카카오 ID가 필요합니다.")

        user = self.create_user(
            kakao_id=kakao_id,
            nickname=nickname,
            connected_at=connected_at,
        )
        # user.set_password(password)  # 관리자 계정은 비밀번호를 사용함
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    카카오 소셜 로그인 전용 사용자 모델
    """
    kakao_id = models.BigIntegerField(unique=True, null=True, blank=True)  # 카카오 고유 사용자 ID
    nickname = models.CharField(max_length=100, null=True, blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)  # 가입 날짜
    is_active = models.BooleanField(default=True)  # 계정 활성화 여부
    is_admin = models.BooleanField(default=False)  # 관리자 여부

    objects = UserManager()  # 커스텀 UserManager 적용

    USERNAME_FIELD = 'kakao_id'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.kakao_id if self.kakao_id else "No Kakao ID"

    @property
    def is_staff(self):
        return self.is_admin

    # 그룹과 권한 관련 필드에 related_name을 설정하여 충돌 방지
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='api_user_groups',  # 충돌을 피하기 위한 related_name 추가
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='api_user_permissions',  # 충돌을 피하기 위한 related_name 추가
        blank=True
    )

class Diary(models.Model):
    """
    일기 모델
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='diaries')
    title = models.CharField(max_length=255)  # 일기 제목
    content = models.TextField()  # 일기 내용
    sentiment = models.CharField(max_length=50, blank=True, null=True) # 감정 저장
    created_at = models.DateTimeField(auto_now_add=True)  # 작성일
    updated_at = models.DateTimeField(auto_now=True)  # 수정일
    
    def __str__(self):
        return self.title


# class ChatSession(models.Model):
#     """
#     채팅 세션 모델 (AI와의 대화 데이터 저장)
#     """
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
#     session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # UUID 자동 생성
#     conversation_data = models.TextField()  # 대화 내용 (JSON 형식으로 저장 가능)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Session {self.session_id} for {self.user}"


class SentimentAnalysis(models.Model):
    """
    감정 분석 결과 모델 (일기와 1:1 관계)
    """
    diary = models.OneToOneField(Diary, on_delete=models.CASCADE, related_name='sentiment_analysis')
    sentiment = models.CharField(max_length=50)  # 예: "긍정", "부정" 등
    score = models.DecimalField(max_digits=5, decimal_places=2)  # 예: 0.85
    created_at = models.DateTimeField(auto_now_add=True)  # 감정 분석이 수행된 시점

    def __str__(self):
        return f"Sentiment for {self.diary.title}: {self.sentiment} ({self.score})"

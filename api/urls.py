from django.urls import include, path
from rest_framework.routers import DefaultRouter
# from rest_framework_simplejwt.views import (
#     TokenObtainPairView,
#     TokenRefreshView,
# )

from .views import (KakaoLoginCallbackView, DiaryViewSet,
                    SentimentAnalysisViewSet, UserViewSet)

# DefaultRouter를 사용하여 ViewSet을 자동으로 라우팅
router = DefaultRouter()
router.register(r'users', UserViewSet)  # 유저 관련 API
router.register(r'diaries', DiaryViewSet)  # 일기 관련 API
router.register(r'sentimentanalysis', SentimentAnalysisViewSet)  # 감정 분석 API

# URL 패턴
urlpatterns = [
    path('', include(router.urls)),  # 등록된 ViewSet 라우팅을 포함
    path('accounts/kakao/login/callback/', KakaoLoginCallbackView.as_view(), name='kakao-login-callback'),
    path('chat/end/', DiaryViewSet.as_view({'post': 'create'}), name='chat-end'),  # 채팅 종료 후 일기 생성 API
    path('chat/diary/save/', DiaryViewSet.as_view({'post': 'save_diary'}), name='diary-save'),  # 일기 저장 API
    path('diary/list/', DiaryViewSet.as_view({'get': 'list'}), name='diary-list'),  # 일기 목록 API
    path('diary/<int:pk>/', DiaryViewSet.as_view({'get': 'retrieve', 'post': 'update'}), name='diary-detail'),  # 특정 일기 열람, 편집 및 저장 API
    path('analytic/sentiment/', SentimentAnalysisViewSet.as_view({'get': 'list'}), name='sentiment-analysis'),  # 감정 분석 결과 조회 API
]
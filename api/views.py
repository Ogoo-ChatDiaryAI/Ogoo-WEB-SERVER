import requests
import os
import logging
import json

from django.shortcuts import redirect
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.auth import get_user_model, login
from dotenv import load_dotenv
import google.generativeai as genai

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.authentication import (BasicAuthentication,
                                           SessionAuthentication)
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import (AllowAny, IsAuthenticated) # 테스트 시 AllowAny 추가
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Diary, SentimentAnalysis, User
from .serializers import (DiarySerializer,
                          SentimentAnalysisSerializer, UserSerializer)

load_dotenv()
logger = logging.getLogger(__name__)

User = get_user_model()

# 나의 잘못된 이해로 인한 코드
# class KakaoLoginStartView(APIView):
#     permission_classes = [AllowAny]
#     def get(self, request, *args, **kwargs):
#         kakao_auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={settings.KAKAO_CLIENT_ID}&redirect_uri={settings.KAKAO_REDIRECT_URI}&response_type=code"
#         return redirect(kakao_auth_url)

@method_decorator(csrf_exempt, name='dispatch')
class KakaoLoginCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.debug(f"Incoming request path: {request.path}")
        logger.debug(f"Incoming request method: {request.method}")

        code = request.data.get('code')
        logger.debug(f"Receuved code: {code}")
        if not code:
            return Response({"error": "Authorization code not provided"}, status=status.HTTP_400_BAD_REQUEST)

    # 이 또한 나의 오해로 인해 생긴 코드
    # def get(self, request, *args, **kwargs):
    #     code = request.query_params.get('code')
    #     logger.debug(f"Authorization code: {code}")

    #     if not code:
    #         return Response({"error": "Authorization code not provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Get the access token from Kakao
        token_url = "https://kauth.kakao.com/oauth/token"

        data = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_CLIENT_ID,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
        }
        headers = {
            "Content-type": "application/x-www-form-urlencoded;charset=utf-8"
        }
        token_response = requests.post(token_url, data=data, headers=headers)
        token_json = token_response.json()
        logger.debug(f"Token response: {token_json}")

        if token_response.status_code != 200:
            return Response({"error": "Failed to get access token", "details": token_json}, status=status.HTTP_400_BAD_REQUEST)

        access_token = token_json.get("access_token")
        if not access_token:
            return Response({"error": "Access token not found in response"}, status=status.HTTP_400_BAD_REQUEST)

        logger.debug(f"Access token: {access_token}")

        # Step 2: Get the user's Kakao ID (회원번호) using the access token
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info_json = user_info_response.json()
        logger.debug(f"User info: {user_info_json}")

        if user_info_response.status_code != 200:
            return Response({"error": "Failed to fetch user info", "details": user_info_json}, status=status.HTTP_400_BAD_REQUEST)

        # Extract the Kakao user ID
        kakao_id = user_info_json.get("id")  # 회원번호
        if not kakao_id:
            return Response({"error": "Kakao ID not found"}, status=status.HTTP_400_BAD_REQUEST)

        kakao_account = user_info_json.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        nickname = profile.get("nickname")
        if not nickname:
            return Response({"error": "Nickname not found in user profile"}, status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.update_or_create(
            kakao_id=kakao_id,
            defaults={
                "nickname": nickname,
                "connected_at": timezone.now()
            }
        )
        logger.debug(f"User created or retrieved: {user}, created: {created}")

        request.user = user

        # Respond with the Kakao ID
        return Response({
            "message": "Login successful", 
            "access_token": access_token, 
            "kakao_id": kakao_id,
            "nickname": nickname,
        }, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
    사용자 관련 작업을 처리하는 뷰셋
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # 테스트용 인증
    # permission_classes = [AllowAny]  # 인증 없이 접근 가능
    # 테스트 이후 아래 주석 사용
    permission_classes = [AllowAny]


# class ChatSessionViewSet(viewsets.ModelViewSet):
#     """
#     채팅 세션을 기록하는 뷰셋 (프론트에서 GPT와의 대화 내용을 기록)
#     """
#     queryset = ChatSession.objects.all()
#     serializer_class = ChatSessionSerializer
#     # 테스트용 인증
#     # permission_classes = [AllowAny]  # 인증 없이 접근 가능
#     # 테스트 이후 아래 주석 사용
#     permission_classes = [IsAuthenticated]

#     def create(self, request, *args, **kwargs):
#         """
#         프론트엔드에서 GPT와의 대화 내용을 받아서 채팅 세션으로 저장
#         """
#         conversation_data = request.data.get("conversation_data")

#         if not conversation_data:
#             return Response({"error": "대화 내용이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
#         # 임시로 인증된 사용자 설정 (테스트용)
#         # if request.user.is_anonymous:
#         #     user = User.objects.first()  # 첫 번째 유저를 사용 (테스트용으로 적절한 유저를 선택)
#         # else:
#         #     user = request.user

#         # ChatSession 생성 및 대화 내용 저장
#         chat_session = ChatSession.objects.create(
#             # 테스트용
#             # user=user,
#             # 테스트 이후 아래 주석 사용
#             user=request.user,
#             conversation_data=conversation_data
#         )

#         serializer = self.get_serializer(chat_session)
#         return Response(serializer.data, status=status.HTTP_201_CREATED)

class KakaoAccessTokenAuthentication(BasicAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        
        token = auth_header.split(" ")[1]
        user_info = self.get_user_info(token)

        if user_info is None:
            raise AuthenticationFailed('Invalid or expired token.')

        kakao_id = user_info.get('id')
        user, _ = User.objects.get_or_create(kakao_id=kakao_id)

        return (user, None)

    def get_user_info(self, token):
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        response = requests.get(user_info_url, headers=headers)

        if response.status_code != 200:
            return None

        return response.json()  

class SentimentAnalysisViewSet(viewsets.ModelViewSet):
    """
    Clova API로 생성된 일기를 전송하여 감정 분석 요청
    """
    queryset = SentimentAnalysis.objects.all()
    serializer_class = SentimentAnalysisSerializer
    # permission_classes = [AllowAny]  # 인증 없이 접근 가능
    # 테스트 이후 사용 (실제 환경에서는 인증 필요)
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        """
        생성된 일기의 감정 분석 요청
        """
        diary_id = request.data.get('diary_id')
        try:
            diary = Diary.objects.get(id=diary_id, user=request.user)
        except Diary.DoesNotExist:
            return Response({"error": "해당 일기를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # Mock된 응답 (Clova API 호출 대신 임시 데이터 반환)
        # mock_sentiment_response = {
        #     "sentiment": "positive",
        #     "confidence": 0.95
        # }

        # Mock된 데이터를 사용하여 감정 분석 결과 저장
        # sentiment_analysis = SentimentAnalysis.objects.create(
        #     diary=diary,
        #     sentiment=mock_sentiment_response['sentiment'],
        #     score=mock_sentiment_response['confidence']
        # )

        # serializer = self.get_serializer(sentiment_analysis)
        # return Response({
        #     "message": "Mocked Clova API로 감정 분석 완료",
        #     "analysis": serializer.data
        # }, status=status.HTTP_201_CREATED)

        # 실제 API 호출 (테스트 이후 사용)
        clova_api_url = "https://naveropenapi.apigw.ntruss.com/sentiment-analysis/v1/analyze"
        headers = {
            "X-NCP-APIGW-API-KEY-ID": os.getenv('CLOVA_API_KEY_ID'),
            "X-NCP-APIGW-API-KEY": os.getenv('CLOVA_API_KEY'),
            "Content-Type": "application/json"
        }

        data = {
            "content": diary.content,
            "config": {
                "negativeClassification": True
            }
        }

        response = requests.post(clova_api_url, headers=headers, json=data)

        if response.status_code == 200:
            sentiment_result = response.json()

            sentiment = sentiment_result.get('document', {}).get('sentiment', 'neutral')
            classified_sentiment = self.classified_sentiment(sentiment, 'neutral')
            
            sentiment_analysis = SentimentAnalysis.objects.create(
                diary=diary,
                sentiment=sentiment,
                score=1.0
            )

            serializer = self.get_serializer(sentiment_analysis)
            return Response({
                "message": "Clova 감정 분석 완료",
                "analysis": serializer.data,
                "sentiment": classified_sentiment,
                "emoji": classified_sentiment,
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": "Clova 감정 분석 실패"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def classified_sentiment(self, sentiment):
        if sentiment == "positive":
            return "happy"
        elif sentiment == "anger":
            return "anger"
        elif sentiment == "sad":
            return "sad"
        elif sentiment == "fear":
            return "fear"
        else:
            return "neutral"

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
class DiaryViewSet(viewsets.ModelViewSet):
    """
    GPT와의 대화 내용을 기반으로 Gemini에 일기 생성을 요청하는 뷰셋
    """
    queryset = Diary.objects.all()
    serializer_class = DiarySerializer
    # permission_classes = [AllowAny]  # 인증 없이 접근 가능
    # 테스트 이후 사용 (실제 환경에서는 인증 필요)
    authentication_classes = [KakaoAccessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User must be authenticated."}, status=status.HTTP_403_FORBIDDEN)
        
        """채팅 세션의 대화 내용을 받아 Gemini에 일기 생성 요청"""
        conversation_data = request.data.get("conversation")
        if not conversation_data:
            return Response({"error": "Conversation data is required."}, status=status.HTTP_400_BAD_REQUEST)

        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

        diary_creation_prompt = (
            f"다음 대화를 바탕으로 User의 입장에서 일기 항목을 작성해 주세요. "
            f"일기에는 제목이 포함되어야 하며 User의 경험과 대화에 대한 생각을 서술해야 합니다. "
            f"결과를 다음 형식으로 작성해 주세요: {{ \"title\": \"일기 제목\", \"content\": \"일기 내용\" }}\n\n"
            f"{json.dumps(conversation_data, ensure_ascii=False)}"
        )

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(diary_creation_prompt)

        # Log the full response for debugging
        logger.debug(f"Gemini API response: {response}")

        # Check the response structure
        if response:
            logger.debug(f"Response type: {type(response)}")  # Log the type of response
            logger.debug(f"Full Response: {response}")  # Log the entire response object

            # Check for candidates in the response directly
            if hasattr(response, 'candidates') and response.candidates:
                diary_data = response.candidates[0].content.parts[0].text
                
                # Log the raw diary data
                logger.debug(f"Raw diary data from Gemini: {diary_data}")

                # Clean the response to remove markdown formatting
                cleaned_data = diary_data.replace("```json\n", "").replace("```", "").strip()
                logger.debug(f"Cleaned diary data: {cleaned_data}")  # Log the cleaned data

                try:
                    # Attempt to parse the cleaned JSON string
                    diary_info = json.loads(cleaned_data)
                    title = diary_info.get('title', '제목없음')
                    content = diary_info.get('content', '')
                except json.JSONDecodeError as e:
                    logger.error(f"JSON Decode Error: {str(e)} with data: {cleaned_data}")
                    return Response({"error": f"Failed to parse diary data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # Create the diary entry
                diary = Diary.objects.create(
                    user=request.user,
                    title=title,
                    content=content
                )

            clova_api_url = "https://naveropenapi.apigw.ntruss.com/sentiment-analysis/v1/analyze"
            headers = {
                "X-NCP-APIGW-API-KEY-ID": os.getenv('CLOVA_API_KEY_ID'),
                "X-NCP-APIGW-API-KEY": os.getenv('CLOVA_API_KEY'),
                "Content-Type": "application/json"
            }

            data = {
                "content": content,
                "config": {
                    "negativeClassification": True
                }
            }

            response = requests.post(clova_api_url, headers=headers, json=data)

            if response.status_code == 200:
                sentiment_result = response.json()
                sentiment = sentiment_result.get('document', {}).get('sentiment', 'neutral')
                
                # Check if negative sentiment exists
                negative_sentiment = sentiment_result.get('sentences', [{}])[0].get('negativeSentiment', {}).get('sentiment', None)
                if negative_sentiment:
                    sentiment = negative_sentiment

                confidence_scores = sentiment_result.get('document', {}).get('confidence', {})
                positive_confidence = confidence_scores.get('positive', 0)
                negative_confidence = confidence_scores.get('negative', 0)
                neutral_confidence = confidence_scores.get('neutral', 0)

                emoji = self.classified_sentiment(sentiment)

                # Save the sentiment analysis result
                sentiment_analysis, created = SentimentAnalysis.objects.update_or_create(
                    diary=diary,
                    defaults={
                        'sentiment': sentiment,
                        'score': max(positive_confidence, negative_confidence, neutral_confidence)
                    }
                )

                return Response({
                    "code": 200,
                    "message": "Chat ended and diary created",
                    "diaryTitle": title,
                    "diaryContent": content,
                    "emoji": emoji,
                    "sentiment_analysis": {
                        "sentiment": sentiment,
                        "score": max(positive_confidence, negative_confidence, neutral_confidence),
                        "negativeSentiment": negative_sentiment if negative_sentiment else "None"  # Include negative sentiment
                    },
                    "diaryId": diary.id
                }, status=status.HTTP_201_CREATED)
            else:
                logger.error("No candidates found in the response.")
                return Response({"error": "No candidates returned from Gemini."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.error("No response received from Gemini API.")
            return Response({"error": "Failed to generate diary from Gemini"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def classified_sentiment(self, sentiment):
        if sentiment == "positive":
            return "happy"
        elif sentiment == "angry":
            return "angry"
        elif sentiment == "sad":
            return "sad"
        elif sentiment == "fear":
            return "fear"
        else:
            return "neutral"

    @action(detail=False, methods=['post'], url_path='save')
    def save_diary(self, request):
        diary_id = request.data.get('diary_id')
        title = request.data.get('title')
        content = request.data.get('diaryContent')

        try:
            diary = Diary.objects.get(id=diary_id, user=request.user)
        except Diary.DoesNotExist:
            return Response({"error": "Diary not found"}, status=status.HTTP_404_NOT_FOUND)

        # Prepare the updated diary data
        diary_data = {
            "title": title,
            "content": content
        }

        serializer = self.get_serializer(diary, data=diary_data, partial=True)
        if serializer.is_valid():
            # Save the diary updates
            serializer.save()

            # Now perform sentiment analysis on the updated content
            clova_api_url = "https://naveropenapi.apigw.ntruss.com/sentiment-analysis/v1/analyze"
            headers = {
                "X-NCP-APIGW-API-KEY-ID": os.getenv('CLOVA_API_KEY_ID'),
                "X-NCP-APIGW-API-KEY": os.getenv('CLOVA_API_KEY'),
                "Content-Type": "application/json"
            }
            data = {
                "content": content,
                "config": {
                    "negativeClassification": True
                }
            }
            response = requests.post(clova_api_url, headers=headers, json=data)

            if response.status_code == 200:
                sentiment_result = response.json()
                sentiment = sentiment_result.get('document', {}).get('sentiment', 'neutral')

                negative_sentiment = sentiment_result.get('sentences', [{}])[0].get('negativeSentiment', {}).get('sentiment', None)
                if negative_sentiment:
                    sentiment = negative_sentiment

                confidence_scores = sentiment_result.get('document', {}).get('confidence', {})
                positive_confidence = confidence_scores.get('positive', 0)
                negative_confidence = confidence_scores.get('negative', 0)
                neutral_confidence = confidence_scores.get('neutral', 0)

                emoji = self.classified_sentiment(sentiment)

                # Check if a SentimentAnalysis entry already exists for this diary
                sentiment_analysis, created = SentimentAnalysis.objects.update_or_create(
                    diary=diary,
                    defaults={
                        'sentiment': sentiment,
                        'score': max(positive_confidence, negative_confidence, neutral_confidence)
                    }
                )

                return Response({
                    "message": "Diary saved successfully",
                    "diary": serializer.data,
                    "sentiment_analysis": {
                        "sentiment": sentiment,
                        "score": max(positive_confidence, negative_confidence, neutral_confidence),
                        "emoji": emoji,
                        "negativeSentimnet": negative_sentiment
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Clova sentiment analysis failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        diaries_data = []

        for diary in serializer.data:
            diary_data = {
                "diaryId": diary['id'],
                "title": diary['title'],
                "date": diary['created_at'].split("T")[0],
                "content": diary['content'],
            }

            sentiment_analysis = SentimentAnalysis.objects.filter(diary=diary['id']).first()
            if sentiment_analysis:
                sentiment = sentiment_analysis.sentiment
                emoji = self.classified_sentiment(sentiment)
            else:
                sentiment = 'neutral'
                emoji = 'neutral'

            diary_data['emoji'] = emoji
            diaries_data.append(diary_data)
        return Response({
            "code": 200,
            "diaries": diaries_data
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):        
        instance = self.get_object()        
        serializer = self.get_serializer(instance)        
        return Response(serializer.data)    
    
    def update(self, request, *args, **kwargs):        
        partial = kwargs.pop('partial', False)        
        instance = self.get_object()        
        serializer = self.get_serializer(instance, data=request.data, partial=True)        
        if serializer.is_valid():            
            serializer.save()            
            return Response(serializer.data)        
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


        # Mock된 응답 (Gemini API 호출 대신 임시 데이터 반환)
        # mock_gemini_response = {
        #     "title": "Mock Diary Title",
        #     "content": f"Mock Diary Content based on conversation: {conversation_data}"
        # }

        # 임시로 사용자 설정 (테스트용)
        # user = request.user if request.user.is_authenticated else User.objects.first()  # 인증된 사용자가 없으면 첫 번째 유저로

        # Mock된 데이터를 사용하여 일기 생성
        # diary = Diary.objects.create(
        #     user=user,
        #     title=mock_gemini_response['title'],
        #     content=mock_gemini_response['content']
        # )

        # diary_serializer = DiarySerializer(diary)
        # return Response({
        #     "message": "Mocked Gemini API로 생성된 일기입니다.",
        #     "diary": diary_serializer.data
        # }, status=status.HTTP_201_CREATED)
from rest_framework import serializers

from .models import  Diary, SentimentAnalysis, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['kakao_id']
        
class SentimentAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentAnalysis
        fields = ['id', 'diary', 'sentiment', 'score', 'created_at']
        read_only_fields = ['created_at']

class DiarySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # 사용자 정보 포함
    sentiment_analysis = SentimentAnalysisSerializer(read_only=True, source='sentiment_analysis')
    
    class Meta:
        model = Diary
        fields = ['kakao_id', 'title', 'content', 'sentiment_analysis', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        return Diary.objects.create(user=user, **validated_data)

# class ChatSessionSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)

#     class Meta:
#         model = ChatSession
#         fields = ['id', 'user', 'session_id', 'conversation_data', 'created_at']
#         read_only_fields = ['user', 'created_at']

#     def create(self, validated_data):
#         request = self.context.get('request')
#         user = request.user if request else None
#         return ChatSession.objects.create(user=user, **validated_data)

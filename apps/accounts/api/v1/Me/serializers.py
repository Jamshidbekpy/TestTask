from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class MeSerializer(serializers.ModelSerializer):
    bio = serializers.SerializerMethodField(source="bio")
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "bio")
        
        
    def get_bio(self, obj):
        return {
            "bio_uz": obj.bio_uz,
            "bio_ru": obj.bio_ru,
            "bio_en": obj.bio_en
        }
        
        
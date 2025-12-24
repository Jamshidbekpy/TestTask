from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class BioSerializer(serializers.Serializer):
    bio_uz = serializers.CharField(allow_blank=True, required=False)
    bio_ru = serializers.CharField(allow_blank=True, required=False)
    bio_en = serializers.CharField(allow_blank=True, required=False)

class UpdateInfoSerializer(serializers.ModelSerializer):
    bio = BioSerializer(required=False)
    bio_response = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["first_name", "last_name", "avatar", "bio", "bio_response"]

    def update(self, instance, validated_data):
        bio_data = validated_data.pop("bio", {})
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        if "avatar" in validated_data:
            instance.avatar = validated_data.get("avatar", instance.avatar)

        for field in ["bio_uz", "bio_ru", "bio_en"]:
            if field in bio_data:
                setattr(instance, field, bio_data[field])

        instance.save()
        return instance

    def get_bio_response(self, obj):
        return {
            "bio_uz": obj.bio_uz,
            "bio_ru": obj.bio_ru,
            "bio_en": obj.bio_en
        }

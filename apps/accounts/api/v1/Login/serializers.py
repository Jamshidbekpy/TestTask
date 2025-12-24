from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate

User = get_user_model()

class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                raise serializers.ValidationError("❌ Noto‘g‘ri email yoki parol")
            if not user.is_active:
                raise serializers.ValidationError("❌ Akkaunt faollashtirilmagan")
        else:
            raise serializers.ValidationError("❌ Email va parol kiritilishi shart")

        attrs["user"] = user
        return attrs

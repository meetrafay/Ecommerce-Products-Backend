from rest_framework import serializers
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate
from .models import Profile
from django.db import transaction


# class ProfileSerializer(serializers.ModelSerializer):
#     """
#     Serializer for the Profile model.
#     """
#     class Meta:
#         model = Profile
#         fields = ['profile_pic']

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model, including profile.
    """
    # profile = ProfileSerializer()
    profile_pic = serializers.ImageField(allow_null=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'profile_pic']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        print(validated_data)
        """
        Create a user with a profile and assign to 'Inventory Managers' group.
        """
        with transaction.atomic():                    
            profile_data = validated_data.pop('profile_pic')
            user = User.objects.create_user(
                first_name=validated_data['username'],
                username=validated_data['email'],
                email=validated_data['email'],
                password=validated_data['password']
            )
            Profile.objects.create(user=user, profile_pic=profile_data)
            # Assign user to Inventory Managers group
            # inventory_group, _ = Group.objects.get_or_create(name='Inventory Managers')
            # user.groups.add(inventory_group)
            return user

class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """
        Validate user credentials.
        """
        user = authenticate(username=data['email'], password=data['password'])
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")
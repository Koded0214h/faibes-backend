from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import User, EmergencyContact

class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ['id', 'name', 'phone', 'relationship', 'is_primary']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    next_of_kin = serializers.DictField(child=serializers.CharField(), required=False)
    medical_info = serializers.DictField(child=serializers.CharField(), required=False)
    safety_network = serializers.ListField(
        child=serializers.CharField(), 
        required=False
    )

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone', 'email', 'password', 'password_confirm',
            'next_of_kin_name', 'next_of_kin_phone', 'medical_info', 
            'safety_network', 'safe_word'
        ]

    def validate(self, attrs):
        # Check password confirmation
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({"password": "Passwords don't match."})
        
        # Validate email format
        try:
            validate_email(attrs.get('email'))
        except ValidationError:
            raise serializers.ValidationError({"email": "Enter a valid email address."})
        
        # Process next_of_kin data
        next_of_kin = attrs.pop('next_of_kin', {})
        if next_of_kin:
            attrs['next_of_kin_name'] = next_of_kin.get('name', '')
            attrs['next_of_kin_phone'] = next_of_kin.get('phone', '')
        
        # Remove password_confirm from validated data
        attrs.pop('password_confirm', None)
        
        return attrs

    def create(self, validated_data):
        # Extract safety_network if provided
        safety_network = validated_data.pop('safety_network', [])
        
        user = User.objects.create_user(**validated_data)
        
        # Set safety network
        if safety_network:
            user.safety_network = safety_network
            user.save()
        
        return user

class UserLoginSerializer(serializers.Serializer):
    phone_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        phone_or_email = attrs.get('phone_or_email')
        password = attrs.get('password')
        
        # Try to authenticate by phone or email
        user = None
        
        # Check if input is email
        try:
            validate_email(phone_or_email)
            user = authenticate(email=phone_or_email, password=password)
        except ValidationError:
            # Input is phone number
            user = authenticate(phone=phone_or_email, password=password)
        
        if not user:
            raise serializers.ValidationError('Invalid credentials')
        
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled')
        
        attrs['user'] = user
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone', 'email', 'next_of_kin_name', 
            'next_of_kin_phone', 'medical_info', 'safety_network', 
            'safe_word', 'voice_trigger_enabled', 'date_joined', 
            'emergency_contacts'
        ]
        read_only_fields = ['id', 'date_joined']

class SafetyNetworkSerializer(serializers.Serializer):
    safety_network = serializers.ListField(
        child=serializers.CharField(),
        min_length=1
    )
    
    def validate_safety_network(self, value):
        # Validate phone numbers format (basic validation)
        for phone in value:
            if not phone.startswith('+'):
                raise serializers.ValidationError(
                    "Phone numbers must include country code (e.g., +2348012345678)"
                )
            if len(phone) < 10:
                raise serializers.ValidationError(
                    "Phone numbers must be at least 10 characters"
                )
        return value

class MedicalInfoSerializer(serializers.Serializer):
    medical_info = serializers.DictField(required=True)
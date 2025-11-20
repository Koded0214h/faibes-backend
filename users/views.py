from django.shortcuts import render

# Create your views here.
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.db import transaction

from .models import User, EmergencyContact
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    SafetyNetworkSerializer, MedicalInfoSerializer, EmergencyContactSerializer
)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user(request):
    """User registration endpoint"""
    try:
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                user = serializer.save()
                
                # Create emergency contact from next_of_kin if provided
                if user.next_of_kin_name and user.next_of_kin_phone:
                    EmergencyContact.objects.create(
                        user=user,
                        name=user.next_of_kin_name,
                        phone=user.next_of_kin_phone,
                        relationship='Next of Kin',
                        is_primary=True
                    )
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'User registered successfully',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_user(request):
    """User login endpoint"""
    try:
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT'])
def user_profile(request):
    """Get or update user profile"""
    try:
        user = request.user
        
        if request.method == 'GET':
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        
        elif request.method == 'PUT':
            serializer = UserProfileSerializer(
                user, 
                data=request.data, 
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Profile updated successfully',
                    'user': serializer.data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
def update_safety_network(request):
    """Update user's safety network"""
    try:
        user = request.user
        serializer = SafetyNetworkSerializer(data=request.data)
        
        if serializer.is_valid():
            user.safety_network = serializer.validated_data['safety_network']
            user.save()
            
            return Response({
                'message': 'Safety network updated successfully',
                'safety_network': user.safety_network
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
def update_medical_info(request):
    """Update user's medical information"""
    try:
        user = request.user
        serializer = MedicalInfoSerializer(data=request.data)
        
        if serializer.is_valid():
            user.medical_info = serializer.validated_data['medical_info']
            user.save()
            
            return Response({
                'message': 'Medical information updated successfully',
                'medical_info': user.medical_info
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'POST'])
def emergency_contacts(request):
    """List and create emergency contacts"""
    try:
        user = request.user
        
        if request.method == 'GET':
            contacts = user.emergency_contacts.all()
            serializer = EmergencyContactSerializer(contacts, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = EmergencyContactSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT', 'DELETE'])
def emergency_contact_detail(request, contact_id):
    """Update or delete emergency contact"""
    try:
        user = request.user
        
        try:
            contact = user.emergency_contacts.get(id=contact_id)
        except EmergencyContact.DoesNotExist:
            return Response(
                {'error': 'Emergency contact not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if request.method == 'PUT':
            serializer = EmergencyContactSerializer(
                contact, 
                data=request.data, 
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            contact.delete()
            return Response(
                {'message': 'Emergency contact deleted successfully'}, 
                status=status.HTTP_204_NO_CONTENT
            )
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
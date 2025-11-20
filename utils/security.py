import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta
import jwt
from django.conf import settings
from django.core.exceptions import ValidationError
import phonenumbers
from phonenumbers import NumberParseException
from logging import logger

class SecurityUtils:
    """Security-related utility functions"""
    
    @staticmethod
    def generate_secure_token(length=32):
        """Generate a cryptographically secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def hash_data(data, salt=None):
        """Hash data with optional salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        data_str = str(data) + salt
        return hashlib.sha256(data_str.encode()).hexdigest(), salt
    
    @staticmethod
    def verify_hash(data, hash_value, salt):
        """Verify hashed data"""
        new_hash, _ = SecurityUtils.hash_data(data, salt)
        return hmac.compare_digest(new_hash, hash_value)
    
    @staticmethod
    def generate_journey_code():
        """Generate a unique 6-digit journey code"""
        import random
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def validate_phone_number(phone_number, country='NG'):
        """
        Validate phone number format
        Returns: (is_valid: bool, formatted_number: str, error_message: str)
        """
        try:
            parsed_number = phonenumbers.parse(phone_number, country)
            
            if not phonenumbers.is_valid_number(parsed_number):
                return False, None, "Invalid phone number"
            
            formatted = phonenumbers.format_number(
                parsed_number, 
                phonenumbers.PhoneNumberFormat.E164
            )
            return True, formatted, None
            
        except NumberParseException as e:
            return False, None, f"Phone number parse error: {str(e)}"
    
    @staticmethod
    def create_location_signature(lat, lng, timestamp, secret_key):
        """Create signature for location data to prevent tampering"""
        data = f"{lat},{lng},{timestamp}"
        signature = hmac.new(
            secret_key.encode(), 
            data.encode(), 
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def verify_location_signature(lat, lng, timestamp, signature, secret_key):
        """Verify location data signature"""
        expected_signature = SecurityUtils.create_location_signature(
            lat, lng, timestamp, secret_key
        )
        return hmac.compare_digest(expected_signature, signature)
    
    @staticmethod
    def sanitize_user_input(text, max_length=1000):
        """Sanitize user input to prevent XSS and other attacks"""
        if not text:
            return ""
        
        # Truncate to max length
        text = text[:max_length]
        
        # Basic HTML escaping (in production, use a proper sanitizer)
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '&': '&amp;',
        }
        
        for unsafe, safe in replacements.items():
            text = text.replace(unsafe, safe)
        
        return text

class RateLimiter:
    """Simple rate limiting utility"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def is_rate_limited(self, key, max_requests, window_seconds):
        """
        Check if a key is rate limited
        Returns: (is_limited: bool, remaining: int, reset_time: int)
        """
        try:
            current = int(datetime.now().timestamp())
            window_start = current - window_seconds
            
            # Remove old requests
            self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            request_count = self.redis.zcard(key)
            
            if request_count >= max_requests:
                # Get oldest request to calculate reset time
                oldest = self.redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = int(oldest[0][1]) + window_seconds
                    remaining = 0
                else:
                    reset_time = current + window_seconds
                    remaining = 0
                
                return True, remaining, reset_time
            
            # Add current request
            self.redis.zadd(key, {str(current): current})
            self.redis.expire(key, window_seconds)
            
            remaining = max_requests - request_count - 1
            return False, remaining, current + window_seconds
            
        except Exception as e:
            # If Redis fails, allow the request (fail open)
            logger.error(f"Rate limiting error: {str(e)}")
            return False, max_requests, 0

# Global security instance
security_utils = SecurityUtils()
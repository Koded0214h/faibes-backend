import re
from datetime import datetime
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import phonenumbers

class CustomValidators:
    """Custom validators for Django models and serializers"""
    
    @staticmethod
    def validate_phone_number(value):
        """Validate phone number format"""
        try:
            parsed = phonenumbers.parse(value, None)
            if not phonenumbers.is_valid_number(parsed):
                raise ValidationError(_('Enter a valid phone number.'))
        except phonenumbers.NumberParseException:
            raise ValidationError(_('Enter a valid phone number.'))
        
        return value
    
    @staticmethod
    def validate_nigerian_phone_number(value):
        """Validate Nigerian phone number specifically"""
        if not value.startswith('+234'):
            raise ValidationError(_('Nigerian numbers must start with +234'))
        
        return CustomValidators.validate_phone_number(value)
    
    @staticmethod
    def validate_safe_word(value):
        """Validate safe word (alphanumeric, 3-20 characters)"""
        if not re.match(r'^[a-zA-Z0-9]{3,20}$', value):
            raise ValidationError(_('Safe word must be 3-20 alphanumeric characters.'))
        return value
    
    @staticmethod
    def validate_coordinates(value):
        """Validate latitude/longitude coordinates"""
        try:
            float_value = float(value)
            if not (-180 <= float_value <= 180):
                raise ValidationError(_('Coordinates must be between -180 and 180.'))
        except (ValueError, TypeError):
            raise ValidationError(_('Enter a valid coordinate.'))
        
        return value
    
    @staticmethod
    def validate_latitude(value):
        """Validate latitude (-90 to 90)"""
        try:
            lat = float(value)
            if not (-90 <= lat <= 90):
                raise ValidationError(_('Latitude must be between -90 and 90.'))
        except (ValueError, TypeError):
            raise ValidationError(_('Enter a valid latitude.'))
        
        return value
    
    @staticmethod
    def validate_longitude(value):
        """Validate longitude (-180 to 180)"""
        try:
            lng = float(value)
            if not (-180 <= lng <= 180):
                raise ValidationError(_('Longitude must be between -180 and 180.'))
        except (ValueError, TypeError):
            raise ValidationError(_('Enter a valid longitude.'))
        
        return value
    
    @staticmethod
    def validate_future_date(value):
        """Validate that date is in the future"""
        if value and value < datetime.now().date():
            raise ValidationError(_('Date must be in the future.'))
        return value
    
    @staticmethod
    def validate_json_schema(value, schema=None):
        """Basic JSON schema validation"""
        if not isinstance(value, (dict, list)):
            raise ValidationError(_('Value must be a valid JSON object or array.'))
        
        # Add custom schema validation here if needed
        return value
    
    @staticmethod
    def validate_safety_network(value):
        """Validate safety network list"""
        if not isinstance(value, list):
            raise ValidationError(_('Safety network must be a list.'))
        
        for phone in value:
            try:
                CustomValidators.validate_phone_number(phone)
            except ValidationError:
                raise ValidationError(_(f'Invalid phone number in safety network: {phone}'))
        
        if len(value) > 10:
            raise ValidationError(_('Safety network cannot exceed 10 members.'))
        
        return value

# Convenience functions
def validate_phone_number(value):
    return CustomValidators.validate_phone_number(value)

def validate_nigerian_phone_number(value):
    return CustomValidators.validate_nigerian_phone_number(value)

def validate_safe_word(value):
    return CustomValidators.validate_safe_word(value)

def validate_coordinates(value):
    return CustomValidators.validate_coordinates(value)
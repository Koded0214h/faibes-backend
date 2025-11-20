import math
from typing import Tuple, Optional
from geopy.distance import geodesic
from geopy.point import Point
import logging

logger = logging.getLogger(__name__)

class LocationUtils:
    """Location and geography utility functions"""
    
    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points in kilometers
        Uses Haversine formula for great-circle distance
        """
        try:
            point1 = (lat1, lng1)
            point2 = (lat2, lng2)
            return geodesic(point1, point2).kilometers
        except Exception as e:
            logger.error(f"Distance calculation error: {str(e)}")
            return 0.0
    
    @staticmethod
    def calculate_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate bearing (direction) from point1 to point2 in degrees
        Returns: 0-360 degrees from North
        """
        try:
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            lng_diff_rad = math.radians(lng2 - lng1)
            
            x = math.sin(lng_diff_rad) * math.cos(lat2_rad)
            y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lng_diff_rad)
            
            bearing_rad = math.atan2(x, y)
            bearing_deg = math.degrees(bearing_rad)
            
            # Normalize to 0-360
            return (bearing_deg + 360) % 360
            
        except Exception as e:
            logger.error(f"Bearing calculation error: {str(e)}")
            return 0.0
    
    @staticmethod
    def is_point_in_geofence(lat: float, lng: float, geofence_points: list) -> bool:
        """
        Check if a point is inside a geofence (polygon)
        Uses ray casting algorithm
        """
        if len(geofence_points) < 3:
            return False
        
        inside = False
        j = len(geofence_points) - 1
        
        for i in range(len(geofence_points)):
            point_i = geofence_points[i]
            point_j = geofence_points[j]
            
            if ((point_i[1] > lng) != (point_j[1] > lng)) and \
               (lat < (point_j[0] - point_i[0]) * (lng - point_i[1]) / (point_j[1] - point_i[1]) + point_i[0]):
                inside = not inside
            j = i
        
        return inside
    
    @staticmethod
    def calculate_speed(distance_km: float, time_hours: float) -> float:
        """Calculate speed in km/h"""
        if time_hours <= 0:
            return 0.0
        return distance_km / time_hours
    
    @staticmethod
    def estimate_arrival_time(current_lat: float, current_lng: float, 
                            dest_lat: float, dest_lng: float, 
                            current_speed: float) -> Optional[float]:
        """
        Estimate arrival time in hours
        Returns: hours until arrival or None if cannot calculate
        """
        try:
            distance = LocationUtils.calculate_distance(current_lat, current_lng, dest_lat, dest_lng)
            
            if current_speed <= 0:
                return None
            
            return distance / current_speed
            
        except Exception as e:
            logger.error(f"Arrival time estimation error: {str(e)}")
            return None
    
    @staticmethod
    def is_route_deviation(planned_route: list, current_lat: float, current_lng: float, 
                         max_deviation_km: float = 2.0) -> Tuple[bool, float]:
        """
        Check if current location deviates significantly from planned route
        Returns: (is_deviated: bool, deviation_distance: float)
        """
        if len(planned_route) < 2:
            return False, 0.0
        
        # Find closest point on route
        min_distance = float('inf')
        
        for i in range(len(planned_route) - 1):
            point1 = planned_route[i]
            point2 = planned_route[i + 1]
            
            # Calculate distance from current point to line segment
            distance = LocationUtils._point_to_line_distance(
                current_lat, current_lng, point1[0], point1[1], point2[0], point2[1]
            )
            
            if distance < min_distance:
                min_distance = distance
        
        return min_distance > max_deviation_km, min_distance
    
    @staticmethod
    def _point_to_line_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate distance from point to line segment"""
        # Vector from line start to end
        line_vec_x = x2 - x1
        line_vec_y = y2 - y1
        
        # Vector from line start to point
        point_vec_x = px - x1
        point_vec_y = py - y1
        
        # Length of line segment squared
        line_len_sq = line_vec_x * line_vec_x + line_vec_y * line_vec_y
        
        # Calculate projection of point onto line
        if line_len_sq == 0:
            return math.sqrt(point_vec_x * point_vec_x + point_vec_y * point_vec_y)
        
        t = max(0, min(1, (point_vec_x * line_vec_x + point_vec_y * line_vec_y) / line_len_sq))
        
        # Calculate closest point on line
        closest_x = x1 + t * line_vec_x
        closest_y = y1 + t * line_vec_y
        
        # Calculate distance to closest point
        dx = px - closest_x
        dy = py - closest_y
        
        return math.sqrt(dx * dx + dy * dy)
    
    @staticmethod
    def decode_google_maps_url(url: str) -> Optional[Tuple[float, float]]:
        """
        Extract coordinates from Google Maps URL
        Returns: (lat, lng) or None
        """
        try:
            import re
            
            # Pattern for Google Maps URLs
            patterns = [
                r'@(-?\d+\.\d+),(-?\d+\.\d+)',
                r'q=(-?\d+\.\d+),(-?\d+\.\d+)',
                r'll=(-?\d+\.\d+),(-?\d+\.\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    lat = float(match.group(1))
                    lng = float(match.group(2))
                    return lat, lng
            
            return None
            
        except Exception as e:
            logger.error(f"Google Maps URL decoding error: {str(e)}")
            return None

# Global location utils instance
location_utils = LocationUtils()
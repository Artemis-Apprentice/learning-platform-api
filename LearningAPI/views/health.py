"""
Health check endpoint for deployment verification
"""
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Simple health check endpoint that verifies:
    1. Django is running
    2. Database connection is working
    
    Returns:
        200 OK if healthy
        503 Service Unavailable if unhealthy
    """
    try:
        # Check database connection
        connection.ensure_connection()
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)

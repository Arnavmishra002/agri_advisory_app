from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

def home(request):
    """Main frontend page view"""
    return render(request, 'index.html')

@csrf_exempt
@require_http_methods(["POST"])
def api_test(request):
    """Simple API test endpoint"""
    try:
        data = json.loads(request.body)
        return JsonResponse({
            'status': 'success',
            'message': 'API is working!',
            'received_data': data
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

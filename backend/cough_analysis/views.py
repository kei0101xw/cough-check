from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .exceptions import InvalidAudioError, ModelUnavailableError
from .service import analyze_uploaded_audio


@csrf_exempt
@require_POST
def analyze_cough(request):
    uploaded = request.FILES.get("audio")
    if uploaded is None:
        return JsonResponse({"error": "audio file is required"}, status=400)
    if uploaded.size > settings.COUGH_MAX_UPLOAD_BYTES:
        return JsonResponse({"error": "audio file is too large"}, status=413)
    if Path(uploaded.name).suffix.lower() not in settings.COUGH_ALLOWED_EXTENSIONS:
        return JsonResponse({"error": "unsupported audio file extension"}, status=415)
    try:
        return JsonResponse(analyze_uploaded_audio(uploaded))
    except InvalidAudioError as exc:
        return JsonResponse({"error": str(exc)}, status=422)
    except ModelUnavailableError as exc:
        return JsonResponse({"error": str(exc)}, status=503)

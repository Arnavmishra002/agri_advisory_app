"""Language support API — returns all supported languages and auto-detects from state."""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ...services.language_service import (
    SUPPORTED_LANGUAGES,
    get_language_for_state,
    normalise_language_code,
)


class LanguageViewSet(viewsets.ViewSet):
    """Returns the list of supported languages and state→language mapping."""

    permission_classes = [AllowAny]

    def list(self, request):
        """Return all supported languages as an ordered list."""
        langs = []
        for code, info in SUPPORTED_LANGUAGES.items():
            langs.append({
                "code": code,
                "bcp47": info["bcp47"],
                "name_english": info["name_english"],
                "name_native": info["name_native"],
                "script": info["script"],
            })
        return Response({
            "status": "success",
            "total": len(langs),
            "languages": langs,
        })

    @action(detail=False, methods=["get"])
    def detect(self, request):
        """Detect the best language for a given state name."""
        state = request.query_params.get("state", "")
        lang_code = get_language_for_state(state) if state else "hi"
        info = SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES["hi"])
        return Response({
            "state": state,
            "language_code": lang_code,
            "language": info["name_english"],
            "language_native": info["name_native"],
            "bcp47": info["bcp47"],
        })

    @action(detail=False, methods=["get"])
    def normalise(self, request):
        """Normalise an arbitrary language string to our internal code."""
        raw = request.query_params.get("lang", "hi")
        code = normalise_language_code(raw)
        info = SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES["hi"])
        return Response({
            "input": raw,
            "normalised": code,
            "language": info["name_english"],
            "language_native": info["name_native"],
        })

from assistant.services.predict_services import get_prediction
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponseBadRequest
from .services.orchestrator import FinancialAssistant
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from dotenv import load_dotenv
from openai import OpenAI
import instructor
import logging
import json
import os

load_dotenv("./.env", override=True)
logger = logging.getLogger(__name__)

client = instructor.patch(OpenAI(api_key=os.getenv("OPEN_AI_KEY")))
fmp_api_key = os.getenv("FMP_API_KEY")
fh_api_key = os.getenv("FINNHUB_API_KEY")

assistant = FinancialAssistant(
    client=client,
    fmp_api_key=fmp_api_key,
    fh_api_key=fh_api_key
)

@require_http_methods(["GET"])
def predict_price(request):
    ticker = request.GET.get("ticker")
    if not ticker:
        return HttpResponseBadRequest("Ticker parameter is required.")

    try:
        prediction_data = get_prediction(ticker, fmp_api_key)
        return JsonResponse(prediction_data, status=200)

    except ValueError as e:
        logger.warning(f"Prediction failed for ticker '{ticker}': {e}")
        return HttpResponseBadRequest(f"Error processing ticker '{ticker}': {str(e)}")

    except Exception as e:
        # Catch any other unexpected server errors
        logger.error(f"An unexpected error occurred for ticker '{ticker}': {e}")
        return JsonResponse({'error': 'An internal server error occurred.'}, status=500)

def index(request):
    """
    Renders the main homepage from the index.html template.
    """
    return render(request, 'assistant/index.html')

# Use this for development to allow POST requests without a CSRF token
@csrf_exempt 
def analyze_query(request):
    """
    Handles the POST request from the frontend, runs the query through the assistant,
    and returns the analysis as JSON.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query')

            if not query:
                return JsonResponse({'error': 'Query not provided'}, status=400)

            result = assistant.run(query)
            return JsonResponse(result, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"An error occurred: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
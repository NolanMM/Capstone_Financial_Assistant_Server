from .services.orchestrator import FinancialAssistant
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from dotenv import load_dotenv
from openai import OpenAI
import instructor
import json
import os

load_dotenv("./.env", override=True)

client = instructor.patch(OpenAI(api_key=os.getenv("OPEN_AI_KEY")))
fmp_api_key = os.getenv("FMP_API_KEY")
fh_api_key = os.getenv("FINNHUB_API_KEY")

assistant = FinancialAssistant(
    client=client,
    fmp_api_key=fmp_api_key,
    fh_api_key=fh_api_key
)

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
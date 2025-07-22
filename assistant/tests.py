from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json
import pandas as pd
import numpy as np
from assistant.services.orchestrator import FinancialAssistant
from assistant.entities.user_intent import UserIntent
from assistant.services.financial_analysis import FinancialAnalysisService
from assistant.entities.ticker_info import TickerInfo
from assistant.entities.financial_analysis import FinancialAnalysis
from assistant.services.general_knowledge import GeneralKnowledgeServices
from assistant.entities.general_knowledge import GeneralKnowledgeResponse
from assistant.services.investment_advice import InvestmentAdviceService
from assistant.entities.investment_advice import InvestmentAdviceResponse
from assistant.services.predict_services import get_prediction
from assistant.services.retrieve_data import RetrieveDataServices
from assistant.services.route_query import RouteQueryService

class AssistantViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('assistant.views.get_prediction')
    def test_predict_price_success(self, mock_get_prediction):
        # Mock the get_prediction function to return a successful prediction
        mock_get_prediction.return_value = {'prediction': 150.0}
        
        # Make a GET request to the predict_price view with a valid ticker
        response = self.client.get(reverse('predict_price'), {'ticker': 'AAPL'})
        
        # Assert that the response is a JsonResponse with a 200 status code
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'prediction': 150.0})

    def test_predict_price_missing_ticker(self):
        # Make a GET request to the predict_price view without a ticker
        response = self.client.get(reverse('predict_price'))
        
        # Assert that the response is an HttpResponseBadRequest with a 400 status code
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode(), "Ticker parameter is required.")

    @patch('assistant.views.get_prediction')
    def test_predict_price_invalid_ticker(self, mock_get_prediction):
        # Mock the get_prediction function to raise a ValueError
        mock_get_prediction.side_effect = ValueError("Invalid ticker")
        
        # Make a GET request to the predict_price view with an invalid ticker
        response = self.client.get(reverse('predict_price'), {'ticker': 'INVALID'})
        
        # Assert that the response is an HttpResponseBadRequest with a 400 status code
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode(), "Error processing ticker 'INVALID': Invalid ticker")

    @patch('assistant.views.get_prediction')
    def test_predict_price_server_error(self, mock_get_prediction):
        # Mock the get_prediction function to raise a generic Exception
        mock_get_prediction.side_effect = Exception("Server error")
        
        # Make a GET request to the predict_price view
        response = self.client.get(reverse('predict_price'), {'ticker': 'AAPL'})
        
        # Assert that the response is a JsonResponse with a 500 status code
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {'error': 'An internal server error occurred.'})

    def test_index_view(self):
        # Make a GET request to the index view
        response = self.client.get(reverse('index'))
        
        # Assert that the response has a 200 status code and uses the correct template
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'assistant/index.html')

    @patch('assistant.views.FinancialAssistant.run')
    def test_analyze_query_success(self, mock_run):
        # Mock the FinancialAssistant.run method to return a successful analysis
        mock_run.return_value = {'analysis': 'This is a test analysis.'}
        
        # Make a POST request to the analyze_query view with a valid query
        response = self.client.post(reverse('analyze_query'), json.dumps({'query': 'Test query'}), content_type='application/json')
        
        # Assert that the response is a JsonResponse with a 200 status code
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'analysis': 'This is a test analysis.'})

    def test_analyze_query_missing_query(self):
        # Make a POST request to the analyze_query view without a query
        response = self.client.post(reverse('analyze_query'), json.dumps({}), content_type='application/json')
        
        # Assert that the response is a JsonResponse with a 400 status code
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Query not provided'})

    def test_analyze_query_invalid_json(self):
        # Make a POST request to the analyze_query view with invalid JSON
        response = self.client.post(reverse('analyze_query'), 'invalid json', content_type='application/json')
        
        # Assert that the response is a JsonResponse with a 400 status code
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Invalid JSON'})

    def test_analyze_query_not_post(self):
        # Make a GET request to the analyze_query view
        response = self.client.get(reverse('analyze_query'))
        
        # Assert that the response is a JsonResponse with a 405 status code
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {'error': 'Only POST method is allowed'})

    @patch('assistant.views.FinancialAssistant.run')
    def test_analyze_query_server_error(self, mock_run):
        # Mock the FinancialAssistant.run method to raise a generic Exception
        mock_run.side_effect = Exception("Server error")
        
        # Make a POST request to the analyze_query view
        response = self.client.post(reverse('analyze_query'), json.dumps({'query': 'Test query'}), content_type='application/json')
        
        # Assert that the response is a JsonResponse with a 500 status code
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {'error': 'Server error'})

class FinancialAssistantTestCase(TestCase):
    def setUp(self):
        self.client_mock = MagicMock()
        self.fmp_api_key = "test_fmp_key"
        self.fh_api_key = "test_fh_key"
        self.assistant = FinancialAssistant(self.client_mock, self.fmp_api_key, self.fh_api_key)

    @patch('assistant.services.orchestrator.RouteQueryService')
    @patch('assistant.services.orchestrator.FinancialAnalysisService')
    def test_run_ticker_analysis(self, mock_financial_analysis_service, mock_route_query_service):
        # Mock the route query service to return TICKER_ANALYSIS intent
        mock_route_query_service.return_value.route_query.return_value = MagicMock(intent=UserIntent.TICKER_ANALYSIS)
        
        # Mock the financial analysis service to return a successful analysis
        mock_financial_analysis_service.return_value.create_financial_analysis.return_value = MagicMock(dict=lambda: {'analysis': 'ticker analysis'})
        
        result = self.assistant.run("Analyze AAPL")
        
        self.assertEqual(result['type'], 'ticker_analysis')
        self.assertEqual(result['data'], {'analysis': 'ticker analysis'})

    @patch('assistant.services.orchestrator.RouteQueryService')
    @patch('assistant.services.orchestrator.GeneralKnowledgeServices')
    def test_run_general_knowledge(self, mock_general_knowledge_service, mock_route_query_service):
        # Mock the route query service to return GENERAL_KNOWLEDGE intent
        mock_route_query_service.return_value.route_query.return_value = MagicMock(intent=UserIntent.GENERAL_KNOWLEDGE)
        
        # Mock the general knowledge service to return a successful response
        mock_general_knowledge_service.return_value.handle_general_question.return_value = MagicMock(dict=lambda: {'response': 'general knowledge'})
        
        result = self.assistant.run("What is a stock?")
        
        self.assertEqual(result['type'], 'general_knowledge')
        self.assertEqual(result['data'], {'response': 'general knowledge'})

    @patch('assistant.services.orchestrator.RouteQueryService')
    @patch('assistant.services.orchestrator.InvestmentAdviceService')
    def test_run_investment_advice(self, mock_investment_advice_service, mock_route_query_service):
        # Mock the route query service to return INVESTMENT_ADVICE intent
        mock_route_query_service.return_value.route_query.return_value = MagicMock(intent=UserIntent.INVESTMENT_ADVICE)
        
        # Mock the investment advice service to return successful advice
        mock_investment_advice_service.return_value.provide_investment_advice.return_value = MagicMock(dict=lambda: {'advice': 'investment advice'})
        
        result = self.assistant.run("Should I invest in stocks?")
        
        self.assertEqual(result['type'], 'investment_advice')
        self.assertEqual(result['data'], {'advice': 'investment advice'})

    @patch('assistant.services.orchestrator.RouteQueryService')
    def test_run_unknown_intent(self, mock_route_query_service):
        # Mock the route query service to return an unknown intent
        mock_route_query_service.return_value.route_query.return_value = MagicMock(intent="UNKNOWN")
        
        result = self.assistant.run("Some random query")
        
        self.assertEqual(result['type'], 'error')
        self.assertEqual(result['data']['message'], 'Could not determine user intent.')

class FinancialAnalysisServiceTestCase(TestCase):
    def setUp(self):
        self.client_mock = MagicMock()
        self.fmp_api_key = "test_fmp_key"
        self.fh_api_key = "test_fh_key"

    @patch('assistant.services.financial_analysis.RetrieveDataServices')
    def test_create_financial_analysis_success(self, mock_retrieve_data_service):
        # Instantiate the service with the mocked client
        service = FinancialAnalysisService(self.client_mock, self.fmp_api_key, self.fh_api_key)

        # Mock the client's chat completions create method
        self.client_mock.chat.completions.create.side_effect = [
            TickerInfo(ticker="AAPL"),
            FinancialAnalysis(
                company_name="Apple Inc.",
                ticker_symbol="AAPL",
                stock_price=150.0,
                market_cap=2500000000000,
                industry="Technology",
                summary_52_week="52-week high of $175 and low of $125.",
                recommendation="Buy",
                confidence_score=0.85,
                sentiment_analysis="Bullish",
                key_themes=["iPhone sales", "Services growth"],
                key_insights=["Strong brand loyalty", "High profit margins"]
            )
        ]

        # Mock the retrieve data service
        mock_retrieve_data_service.return_value.get_fmp_data.return_value = {
            'profile': 'Apple Inc. profile',
            'historical_summary': 'Apple Inc. historical summary'
        }
        mock_retrieve_data_service.return_value.get_finnhub_news.return_value = "Apple Inc. news"

        analysis = service.create_financial_analysis("Analyze Apple")

        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.company_name, "Apple Inc.")
        self.assertEqual(analysis.ticker_symbol, "AAPL")

    @patch('assistant.services.financial_analysis.RetrieveDataServices')
    def test_create_financial_analysis_no_fmp_data(self, mock_retrieve_data_service):
        # Instantiate the service with the mocked client
        service = FinancialAnalysisService(self.client_mock, self.fmp_api_key, self.fh_api_key)

        # Mock the client's chat completions create method
        self.client_mock.chat.completions.create.return_value = TickerInfo(ticker="AAPL")

        # Mock the retrieve data service to return no FMP data
        mock_retrieve_data_service.return_value.get_fmp_data.return_value = None

        analysis = service.create_financial_analysis("Analyze Apple")

        self.assertIsNone(analysis)

    @patch('assistant.services.financial_analysis.RetrieveDataServices')
    def test_create_financial_analysis_no_news(self, mock_retrieve_data_service):
        # Instantiate the service with the mocked client
        service = FinancialAnalysisService(self.client_mock, self.fmp_api_key, self.fh_api_key)

        # Mock the client's chat completions create method
        self.client_mock.chat.completions.create.side_effect = [
            TickerInfo(ticker="AAPL"),
            FinancialAnalysis(
                company_name="Apple Inc.",
                ticker_symbol="AAPL",
                stock_price=150.0,
                market_cap=2500000000000,
                industry="Technology",
                summary_52_week="52-week high of $175 and low of $125.",
                recommendation="Buy",
                confidence_score=0.85,
                sentiment_analysis="Bullish",
                key_themes=["iPhone sales", "Services growth"],
                key_insights=["Strong brand loyalty", "High profit margins"]
            )
        ]

        # Mock the retrieve data service
        mock_retrieve_data_service.return_value.get_fmp_data.return_value = {
            'profile': 'Apple Inc. profile',
            'historical_summary': 'Apple Inc. historical summary'
        }
        mock_retrieve_data_service.return_value.get_finnhub_news.return_value = None

        analysis = service.create_financial_analysis("Analyze Apple")

        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.company_name, "Apple Inc.")
        self.assertEqual(analysis.ticker_symbol, "AAPL")

class GeneralKnowledgeServiceTestCase(TestCase):
    def setUp(self):
        self.client_mock = MagicMock()
        self.service = GeneralKnowledgeServices(self.client_mock)

    def test_handle_general_question_success(self):
        # Mock the client's chat completions create method
        self.client_mock.chat.completions.create.return_value = GeneralKnowledgeResponse(
            concept_name="Stock",
            definition="A stock is a type of security that signifies ownership in a corporation and represents a claim on part of the corporation's assets and earnings.",
            importance="Stocks are a way for companies to raise capital and for investors to grow their wealth.",
            example="If you buy a stock of Apple, you own a small piece of the company."
        )

        response = self.service.handle_general_question("What is a stock?")

        self.assertIsNotNone(response)
        self.assertEqual(response.concept_name, "Stock")

class InvestmentAdviceServiceTestCase(TestCase):
    def setUp(self):
        self.client_mock = MagicMock()
        self.service = InvestmentAdviceService(self.client_mock)

    def test_provide_investment_advice_success(self):
        # Mock the client's chat completions create method
        self.client_mock.chat.completions.create.return_value = InvestmentAdviceResponse(
            question="Should I invest in stocks?",
            advice_summary="Investing in stocks can be a rewarding experience, but it comes with risks.",
            reasoning=["Potential for high returns", "Ownership in a company"],
            potential_risks=["Market volatility", "Risk of losing principal"],
            disclaimer="This is not financial advice. Consult with a financial professional before making any investment decisions."
        )

        response = self.service.provide_investment_advice("Should I invest in stocks?")

        self.assertIsNotNone(response)
        self.assertEqual(response.disclaimer, "This is not financial advice. Consult with a financial professional before making any investment decisions.")

class RouteQueryServiceTestCase(TestCase):
    def setUp(self):
        self.client_mock = MagicMock()
        self.service = RouteQueryService(self.client_mock)

    def test_route_query_ticker_analysis(self):
        self.client_mock.chat.completions.create.return_value = MagicMock(intent=UserIntent.TICKER_ANALYSIS)
        intent = self.service.route_query("Analyze AAPL")
        self.assertEqual(intent.intent, UserIntent.TICKER_ANALYSIS)

    def test_route_query_general_knowledge(self):
        self.client_mock.chat.completions.create.return_value = MagicMock(intent=UserIntent.GENERAL_KNOWLEDGE)
        intent = self.service.route_query("What is inflation?")
        self.assertEqual(intent.intent, UserIntent.GENERAL_KNOWLEDGE)

    def test_route_query_investment_advice(self):
        self.client_mock.chat.completions.create.return_value = MagicMock(intent=UserIntent.INVESTMENT_ADVICE)
        intent = self.service.route_query("Should I buy Google stock?")
        self.assertEqual(intent.intent, UserIntent.INVESTMENT_ADVICE)

    def test_route_query_unknown_intent(self):
        self.client_mock.chat.completions.create.return_value = MagicMock(intent="UNKNOWN")
        intent = self.service.route_query("Some random query")
        self.assertEqual(intent.intent, "UNKNOWN")
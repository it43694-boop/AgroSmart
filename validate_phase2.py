#!/usr/bin/env python
"""
VALIDATION COMPLÈTE PHASE 2 - AgroSmart
Vérifie que toutes les implémentations sont fonctionnelles
"""

import sys
import json
import traceback
from datetime import datetime

def colored(text, color):
    """Print colored text"""
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    return f"{colors.get(color, '')}{text}{colors['end']}"

class Phase2Validator:
    def __init__(self):
        self.results = {
            "computer_vision": {},
            "blockchain": {},
            "mobile_money": {},
            "reports": {},
            "models": {},
            "saga": {},
            "ml": {}
        }
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def test_computer_vision(self):
        """Valider Computer Vision"""
        print(f"\n{colored('🎯 COMPUTER VISION VALIDATION', 'blue')}")
        tests = [
            self._test_cv_imports,
            self._test_cv_analyzer,
            self._test_cv_fallback,
            self._test_cv_disease_detection
        ]
        
        for test in tests:
            try:
                test()
                self.total_tests += 1
                self.passed_tests += 1
            except Exception as e:
                self.total_tests += 1
                self.failed_tests += 1
                print(f"{colored('✗', 'red')} {test.__doc__}: {str(e)}")

    def _test_cv_imports(self):
        """Test CV imports"""
        from services.computer_vision_service import DroneImageAnalyzer, analyze_drone_image
        print(f"{colored('✓', 'green')} Computer Vision imports")

    def _test_cv_analyzer(self):
        """Test CV analyzer init"""
        from services.computer_vision_service import DroneImageAnalyzer
        analyzer = DroneImageAnalyzer()
        assert analyzer is not None
        print(f"{colored('✓', 'green')} DroneImageAnalyzer initialization")

    def _test_cv_fallback(self):
        """Test CV fallback mode"""
        import numpy as np
        from services.computer_vision_service import DroneImageAnalyzer
        analyzer = DroneImageAnalyzer()
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = analyzer._fallback_analysis(img_array)
        assert result is not None
        assert "diseases" in result
        print(f"{colored('✓', 'green')} CV fallback analysis")

    def _test_cv_disease_detection(self):
        """Test disease detection"""
        from services.computer_vision_service import DroneImageAnalyzer
        analyzer = DroneImageAnalyzer()
        diseases = [
            {"type": "leaf_spot", "confidence": 0.85, "location": [50, 50]},
            {"type": "rust", "confidence": 0.92, "location": [75, 75]}
        ]
        severity = analyzer._calculate_severity(diseases)
        assert severity in ["none", "low", "medium", "high", "critical"]
        print(f"{colored('✓', 'green')} Disease severity calculation")

    def test_blockchain(self):
        """Valider Blockchain Adapter"""
        print(f"\n{colored('🔗 BLOCKCHAIN VALIDATION', 'blue')}")
        tests = [
            self._test_blockchain_imports,
            self._test_blockchain_mock_adapter,
            self._test_blockchain_trace,
            self._test_blockchain_escrow,
            self._test_blockchain_nft
        ]
        
        for test in tests:
            try:
                test()
                self.total_tests += 1
                self.passed_tests += 1
            except Exception as e:
                self.total_tests += 1
                self.failed_tests += 1
                print(f"{colored('✗', 'red')} {test.__doc__}: {str(e)}")

    def _test_blockchain_imports(self):
        """Test Blockchain imports"""
        from services.blockchain_adapter import (
            BlockchainAdapter, MockBlockchainAdapter, Web3BlockchainAdapter
        )
        print(f"{colored('✓', 'green')} Blockchain adapter imports")

    def _test_blockchain_mock_adapter(self):
        """Test Mock adapter"""
        from services.blockchain_adapter import MockBlockchainAdapter
        adapter = MockBlockchainAdapter()
        assert adapter is not None
        print(f"{colored('✓', 'green')} MockBlockchainAdapter initialization")

    def _test_blockchain_trace(self):
        """Test trace functionality"""
        from services.blockchain_adapter import MockBlockchainAdapter
        adapter = MockBlockchainAdapter()
        
        # Add trace
        tx = adapter.add_trace_on_chain("PROD-001", "Mali", "Organic", 1000)
        assert tx is not None
        
        # Get trace
        trace = adapter.get_trace_from_chain("PROD-001")
        assert trace is not None
        assert trace["origin"] == "Mali"
        
        print(f"{colored('✓', 'green')} Blockchain trace operations")

    def _test_blockchain_escrow(self):
        """Test escrow contract"""
        from services.blockchain_adapter import MockBlockchainAdapter
        adapter = MockBlockchainAdapter()
        
        contract = adapter.deploy_escrow_contract("0xBuyer", "0xSeller", 100.0, {})
        assert contract is not None
        
        fund_tx = adapter.fund_escrow_contract(contract, 100.0)
        assert fund_tx is not None
        
        release_tx = adapter.release_escrow_funds(contract, "delivered")
        assert release_tx is not None
        
        print(f"{colored('✓', 'green')} Blockchain escrow contracts")

    def _test_blockchain_nft(self):
        """Test NFT minting"""
        from services.blockchain_adapter import MockBlockchainAdapter
        adapter = MockBlockchainAdapter()
        
        contract = adapter.deploy_nft_contract("AgroNFT", "AGRO")
        assert contract is not None
        
        mint_tx = adapter.mint_agricultural_nft(contract, "0xOwner", 1, "ipfs://QmXxx")
        assert mint_tx is not None
        
        transfer = adapter.transfer_agricultural_nft(contract, 1, "0xOwner", "0xNew")
        assert transfer is True
        
        print(f"{colored('✓', 'green')} Blockchain NFT operations")

    def test_mobile_money(self):
        """Valider Mobile Money Service"""
        print(f"\n{colored('💳 MOBILE MONEY VALIDATION', 'blue')}")
        tests = [
            self._test_mm_imports,
            self._test_mm_adapter,
            self._test_mm_payment,
            self._test_mm_verification
        ]
        
        for test in tests:
            try:
                test()
                self.total_tests += 1
                self.passed_tests += 1
            except Exception as e:
                self.total_tests += 1
                self.failed_tests += 1
                print(f"{colored('✗', 'red')} {test.__doc__}: {str(e)}")

    def _test_mm_imports(self):
        """Test Mobile Money imports"""
        from services.mobile_money_service import (
            MobileMoneyAdapter, LocalMobileMoneyAdapter, MobileMoneyService
        )
        print(f"{colored('✓', 'green')} Mobile Money imports")

    def _test_mm_adapter(self):
        """Test local adapter"""
        from services.mobile_money_service import LocalMobileMoneyAdapter
        adapter = LocalMobileMoneyAdapter()
        assert adapter is not None
        print(f"{colored('✓', 'green')} LocalMobileMoneyAdapter initialization")

    def _test_mm_payment(self):
        """Test payment creation"""
        from services.mobile_money_service import LocalMobileMoneyAdapter
        adapter = LocalMobileMoneyAdapter()
        payment = adapter.create_payment(100.0, "XOF")
        assert payment["success"] is True
        assert "provider_transaction_id" in payment
        print(f"{colored('✓', 'green')} Mobile Money payment creation")

    def _test_mm_verification(self):
        """Test transaction verification"""
        from services.mobile_money_service import LocalMobileMoneyAdapter
        adapter = LocalMobileMoneyAdapter()
        verified = adapter.verify_transaction("TX-123", 100.0, "XOF")
        assert verified is True
        print(f"{colored('✓', 'green')} Mobile Money verification")

    def test_reports(self):
        """Valider Report Service"""
        print(f"\n{colored('📄 REPORTS VALIDATION', 'blue')}")
        tests = [
            self._test_reports_imports,
            self._test_reports_service,
            self._test_pdf_generation,
            self._test_excel_generation
        ]
        
        for test in tests:
            try:
                test()
                self.total_tests += 1
                self.passed_tests += 1
            except Exception as e:
                self.total_tests += 1
                self.failed_tests += 1
                print(f"{colored('✗', 'red')} {test.__doc__}: {str(e)}")

    def _test_reports_imports(self):
        """Test Report imports"""
        from services.report_service import ReportService, report_service
        print(f"{colored('✓', 'green')} Report Service imports")

    def _test_reports_service(self):
        """Test report service init"""
        from services.report_service import report_service
        assert report_service is not None
        print(f"{colored('✓', 'green')} ReportService initialization")

    def _test_pdf_generation(self):
        """Test PDF generation"""
        from services.report_service import report_service
        user_data = {
            "name": "Test Farmer",
            "region": "Bamako",
            "crop_recommendations": [],
            "weather_forecast": []
        }
        pdf = report_service.generate_farmer_report_pdf(user_data)
        assert pdf is not None
        assert len(pdf) > 0
        print(f"{colored('✓', 'green')} PDF generation")

    def _test_excel_generation(self):
        """Test Excel generation"""
        from services.report_service import report_service
        region_data = {
            "Bamako": {
                "farmers_count": 100,
                "area_ha": 2000,
                "avg_yield": 5.0,
                "issues_count": 10,
                "recommendations": "Test"
            }
        }
        excel = report_service.generate_government_report_excel(region_data)
        assert excel is not None
        assert len(excel) > 0
        print(f"{colored('✓', 'green')} Excel generation")

    def test_models(self):
        """Valider modèles"""
        print(f"\n{colored('🗄️ MODELS VALIDATION', 'blue')}")
        tests = [
            self._test_escrow_model,
            self._test_nft_model
        ]
        
        for test in tests:
            try:
                test()
                self.total_tests += 1
                self.passed_tests += 1
            except Exception as e:
                self.total_tests += 1
                self.failed_tests += 1
                print(f"{colored('✗', 'red')} {test.__doc__}: {str(e)}")

    def _test_escrow_model(self):
        """Test EscrowContract model"""
        import models
        assert hasattr(models, "EscrowContract")
        assert models.EscrowContract.__tablename__ == "escrow_contracts"
        print(f"{colored('✓', 'green')} EscrowContract model")

    def _test_nft_model(self):
        """Test AgriculturalNFT model"""
        import models
        assert hasattr(models, "AgriculturalNFT")
        assert models.AgriculturalNFT.__tablename__ == "agricultural_nfts"
        print(f"{colored('✓', 'green')} AgriculturalNFT model")

    def test_ml(self):
        """Valider modèles ML"""
        print(f"\n{colored('🤖 ML VALIDATION', 'blue')}")
        tests = [
            self._test_ml_imports,
            self._test_ml_prediction
        ]
        
        for test in tests:
            try:
                test()
                self.total_tests += 1
                self.passed_tests += 1
            except Exception as e:
                self.total_tests += 1
                self.failed_tests += 1
                print(f"{colored('✗', 'red')} {test.__doc__}: {str(e)}")

    def _test_ml_imports(self):
        """Test ML imports"""
        from ml_model import predict_action
        print(f"{colored('✓', 'green')} ML model imports")

    def _test_ml_prediction(self):
        """Test ML prediction"""
        from ml_model import predict_action
        test_data = {
            "temperature": 28.0,
            "humidity": 65.0,
            "rainfall": 2.5,
            "ndvi": 0.65,
            "soil_moisture": 50.0
        }
        result = predict_action(test_data)
        assert result is not None
        print(f"{colored('✓', 'green')} ML predictions")

    def generate_report(self):
        """Générer rapport final"""
        print(f"\n{colored('=' * 60, 'blue')}")
        print(f"{colored('PHASE 2 IMPLEMENTATION VALIDATION REPORT', 'blue')}")
        print(f"{colored('=' * 60, 'blue')}\n")
        
        print(f"Total Tests: {self.total_tests}")
        print(f"{colored(f'✓ Passed: {self.passed_tests}', 'green')}")
        print(f"{colored(f'✗ Failed: {self.failed_tests}', 'red' if self.failed_tests > 0 else 'green')}\n")
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        print(f"Success Rate: {colored(f'{success_rate:.1f}%', 'green' if success_rate >= 90 else 'yellow')}\n")
        
        if self.failed_tests == 0:
            print(colored("✅ ALL TESTS PASSED - Phase 2 Implementation Complete!", 'green'))
        else:
            print(colored(f"⚠️ {self.failed_tests} test(s) failed - Review needed", 'yellow'))
        
        print(f"{colored('=' * 60, 'blue')}\n")

    def run_all(self):
        """Exécuter toutes les validations"""
        self.test_computer_vision()
        self.test_blockchain()
        self.test_mobile_money()
        self.test_reports()
        self.test_models()
        self.test_ml()
        self.generate_report()
        
        return self.failed_tests == 0


if __name__ == "__main__":
    validator = Phase2Validator()
    success = validator.run_all()
    sys.exit(0 if success else 1)

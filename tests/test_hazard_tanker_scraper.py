#!/usr/bin/env python3
"""
Tests for hazard_tanker_scraper.py

Simple tests to validate core functionality without requiring external dependencies.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add the scripts directory to the path to import the scraper
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from hazard_tanker_scraper import (
    AccidentReport, 
    HazardousScenarioScraper, 
    ProxyRotator, 
    RateLimiter
)


class TestAccidentReport(unittest.TestCase):
    """Test the AccidentReport dataclass."""
    
    def test_accident_report_creation(self):
        """Test creating an AccidentReport instance."""
        report = AccidentReport(
            date="2024-01-15",
            location="Highway 95, CA",
            hazardous_materials="Petroleum products",
            causes="Mechanical failure",
            consequences="Road closure",
            response_measures="Fire department response",
            source_url="https://example.com/report",
            title="Test Accident"
        )
        
        self.assertEqual(report.date, "2024-01-15")
        self.assertEqual(report.location, "Highway 95, CA")
        self.assertEqual(report.title, "Test Accident")
        self.assertFalse(report.translated)


class TestProxyRotator(unittest.TestCase):
    """Test the ProxyRotator class."""
    
    def test_empty_proxy_list(self):
        """Test behavior with no proxies."""
        rotator = ProxyRotator([])
        self.assertIsNone(rotator.get_proxy())
        
    def test_proxy_rotation(self):
        """Test proxy rotation functionality."""
        proxies = ["http://proxy1:8080", "http://proxy2:8080"]
        rotator = ProxyRotator(proxies)
        
        # First call should return first proxy
        proxy1 = rotator.get_proxy()
        self.assertEqual(proxy1['http'], "http://proxy1:8080")
        
        # Second call should return second proxy
        proxy2 = rotator.get_proxy()
        self.assertEqual(proxy2['http'], "http://proxy2:8080")
        
        # Third call should wrap around to first proxy
        proxy3 = rotator.get_proxy()
        self.assertEqual(proxy3['http'], "http://proxy1:8080")


class TestRateLimiter(unittest.TestCase):
    """Test the RateLimiter class."""
    
    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(min_delay=1.0, max_delay=2.0)
        self.assertEqual(limiter.min_delay, 1.0)
        self.assertEqual(limiter.max_delay, 2.0)
        self.assertEqual(limiter.last_request_time, 0)


class TestHazardousScenarioScraper(unittest.TestCase):
    """Test the main scraper class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.scraper = HazardousScenarioScraper(output_dir=self.temp_dir)
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_scraper_initialization(self):
        """Test scraper initialization."""
        self.assertEqual(self.scraper.output_dir, Path(self.temp_dir))
        self.assertTrue(self.scraper.output_dir.exists())
        self.assertIsInstance(self.scraper.proxy_rotator, ProxyRotator)
        self.assertIsInstance(self.scraper.rate_limiter, RateLimiter)
        
    def test_extract_date(self):
        """Test date extraction from content."""
        content = "The accident occurred on 2024-03-15 at approximately 3 PM."
        date = self.scraper.extract_date(content)
        self.assertEqual(date, "2024-03-15")
        
        content_no_date = "This content has no date information."
        date_no_match = self.scraper.extract_date(content_no_date)
        self.assertEqual(date_no_match, "Date not found")
        
    def test_extract_location(self):
        """Test location extraction from content."""
        content = "The accident occurred in downtown Los Angeles, CA."
        location = self.scraper.extract_location(content)
        # Should extract the location mentioned
        self.assertIn("Los Angeles", location)
        
        content_no_location = "This text has no clear location."
        location_no_match = self.scraper.extract_location(content_no_location)
        self.assertEqual(location_no_match, "Location not found")
        
    def test_extract_materials(self):
        """Test hazardous materials extraction."""
        content = "The tanker was carrying chemical solvents and fuel."
        materials = self.scraper.extract_materials(content)
        self.assertIn("chemical", materials)
        self.assertIn("fuel", materials)
        
    def test_filter_reports(self):
        """Test report filtering functionality."""
        reports = [
            AccidentReport(
                date="2024-01-15", location="CA", hazardous_materials="chemical solvents",
                causes="test", consequences="test", response_measures="test",
                source_url="test", title="Test 1"
            ),
            AccidentReport(
                date="2024-07-15", location="TX", hazardous_materials="petroleum products",
                causes="test", consequences="test", response_measures="test",
                source_url="test", title="Test 2"
            ),
            AccidentReport(
                date="2024-02-15", location="FL", hazardous_materials="chemical acids",
                causes="test", consequences="test", response_measures="test",
                source_url="test", title="Test 3"
            )
        ]
        
        # Test date range filtering
        filtered = self.scraper.filter_reports(reports, date_range=("2024-01-01", "2024-06-30"))
        self.assertEqual(len(filtered), 2)  # Should exclude July report
        
        # Test material type filtering
        filtered = self.scraper.filter_reports(reports, material_type="chemical")
        self.assertEqual(len(filtered), 2)  # Should include both chemical reports
        
    def test_save_as_text(self):
        """Test text file export."""
        reports = [
            AccidentReport(
                date="2024-01-15", location="Test Location", hazardous_materials="Test Materials",
                causes="Test Causes", consequences="Test Consequences", 
                response_measures="Test Response", source_url="https://example.com",
                title="Test Report", scrape_timestamp="2024-01-01T00:00:00"
            )
        ]
        
        filename = "test_report.txt"
        self.scraper.save_as_text(reports, filename)
        
        output_file = self.scraper.output_dir / filename
        self.assertTrue(output_file.exists())
        
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("HAZARDOUS TANKER TRUCK ACCIDENT REPORTS", content)
            self.assertIn("Test Report", content)
            self.assertIn("Test Location", content)
            
    def test_save_as_csv(self):
        """Test CSV file export."""
        reports = [
            AccidentReport(
                date="2024-01-15", location="Test Location", hazardous_materials="Test Materials",
                causes="Test Causes", consequences="Test Consequences", 
                response_measures="Test Response", source_url="https://example.com",
                title="Test Report", scrape_timestamp="2024-01-01T00:00:00"
            )
        ]
        
        filename = "test_report.csv"
        self.scraper.save_as_csv(reports, filename)
        
        output_file = self.scraper.output_dir / filename
        self.assertTrue(output_file.exists())
        
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("title,date,location", content)  # Header
            self.assertIn("Test Report", content)
            self.assertIn("Test Location", content)


class TestCommandLineIntegration(unittest.TestCase):
    """Test command line integration."""
    
    def test_help_output(self):
        """Test that help output is generated correctly."""
        import subprocess
        result = subprocess.run([
            sys.executable, 
            os.path.join(os.path.dirname(__file__), '..', 'scripts', 'hazard_tanker_scraper.py'),
            '--help'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Scrape hazardous tanker truck accident reports", result.stdout)
        self.assertIn("--keywords", result.stdout)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
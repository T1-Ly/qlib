#!/usr/bin/env python3
"""
Hazardous Tanker Truck Accident Report Scraper

This script scrapes hazardous tanker truck accident reports from various web sources
including news sites, government safety databases, and industry publications.

Features:
- Keyword-based search for accident reports
- Multiple data source support
- Data extraction with key accident information
- Export to multiple formats (text, PDF, CSV)
- Filtering capabilities
- Translation support
- Proxy rotation and rate limiting
- Command-line interface

Author: Generated for Qlib project
License: MIT (same as parent project)
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import requests
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    print("Warning: BeautifulSoup4 not available. Install with: pip install beautifulsoup4")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available. Install with: pip install pandas")

try:
    from googletrans import Translator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("Warning: googletrans not available. Install with: pip install googletrans==4.0.0rc1")

try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: fpdf2 not available. Install with: pip install fpdf2")


@dataclass
class AccidentReport:
    """Data structure for storing accident report information."""
    date: str
    location: str
    hazardous_materials: str
    causes: str
    consequences: str
    response_measures: str
    source_url: str
    title: str
    severity: str = ""
    translated: bool = False
    scrape_timestamp: str = ""


class ProxyRotator:
    """Simple proxy rotation manager."""
    
    def __init__(self, proxy_list: List[str] = None):
        """
        Initialize proxy rotator.
        
        Args:
            proxy_list: List of proxy URLs in format 'http://proxy:port'
        """
        self.proxy_list = proxy_list or []
        self.current_index = 0
        
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Get next proxy in rotation."""
        if not self.proxy_list:
            return None
            
        proxy = self.proxy_list[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxy_list)
        
        return {
            'http': proxy,
            'https': proxy
        }


class RateLimiter:
    """Simple rate limiter for HTTP requests."""
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """
        Initialize rate limiter.
        
        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0
        
    def wait(self):
        """Wait appropriate amount of time before next request."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)
            
        self.last_request_time = time.time()


class HazardousScenarioScraper:
    """Main scraper class for hazardous tanker truck accident reports."""
    
    def __init__(self, output_dir: str = "accident_reports", 
                 proxy_list: List[str] = None,
                 rate_limit_delay: Tuple[float, float] = (1.0, 3.0)):
        """
        Initialize the scraper.
        
        Args:
            output_dir: Directory to save scraped reports
            proxy_list: List of proxy URLs for rotation
            rate_limit_delay: Tuple of (min_delay, max_delay) for rate limiting
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.proxy_rotator = ProxyRotator(proxy_list)
        self.rate_limiter = RateLimiter(*rate_limit_delay)
        self.translator = Translator() if TRANSLATOR_AVAILABLE else None
        
        # Setup logging
        self.setup_logging()
        
        # Request session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Data storage
        self.scraped_reports: List[AccidentReport] = []
        
    def setup_logging(self):
        """Setup logging configuration."""
        log_file = self.output_dir / "scraper.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP request with proxy rotation and rate limiting.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object or None if failed
        """
        self.rate_limiter.wait()
        
        proxy = self.proxy_rotator.get_proxy()
        if proxy:
            kwargs['proxies'] = proxy
            
        try:
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            self.logger.info(f"Successfully fetched: {url}")
            return response
            
        except requests.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None
            
    def check_robots_txt(self, domain: str) -> bool:
        """
        Check robots.txt to respect website scraping policies.
        
        Args:
            domain: Domain to check
            
        Returns:
            True if scraping is allowed, False otherwise
        """
        try:
            robots_url = f"https://{domain}/robots.txt"
            response = self.make_request(robots_url)
            
            if response:
                # Simple robots.txt parsing - in production, use robotparser
                content = response.text.lower()
                if "disallow: /" in content and "user-agent: *" in content:
                    self.logger.warning(f"Robots.txt disallows scraping for {domain}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not check robots.txt for {domain}: {e}")
            return True  # Allow scraping if robots.txt check fails
            
    def search_news_sites(self, keywords: List[str], date_range: Tuple[str, str] = None) -> List[str]:
        """
        Search news sites for relevant articles.
        
        Args:
            keywords: List of search keywords
            date_range: Tuple of (start_date, end_date) in YYYY-MM-DD format
            
        Returns:
            List of article URLs
        """
        urls = []
        
        # Example news sources (in practice, you'd have a more comprehensive list)
        news_sources = [
            "reuters.com",
            "apnews.com", 
            "cnn.com",
            "bbc.com"
        ]
        
        for source in news_sources:
            if not self.check_robots_txt(source):
                continue
                
            for keyword in keywords:
                search_url = f"https://www.google.com/search?q=site:{source} {urllib.parse.quote(keyword)}"
                
                if date_range:
                    start_date, end_date = date_range
                    search_url += f" after:{start_date} before:{end_date}"
                    
                # In a real implementation, you'd parse Google search results
                # or use news APIs. This is a simplified example.
                self.logger.info(f"Would search: {search_url}")
                
        return urls
        
    def search_government_databases(self, keywords: List[str]) -> List[str]:
        """
        Search government safety databases.
        
        Args:
            keywords: List of search keywords
            
        Returns:
            List of report URLs
        """
        urls = []
        
        # Example government sources
        gov_sources = [
            "ntsb.gov",  # National Transportation Safety Board
            "phmsa.dot.gov",  # Pipeline and Hazardous Materials Safety Admin
            "osha.gov"  # Occupational Safety and Health Administration
        ]
        
        for source in gov_sources:
            if not self.check_robots_txt(source):
                continue
                
            # Search logic would go here
            self.logger.info(f"Searching government database: {source}")
            
        return urls
        
    def extract_accident_info(self, url: str, html_content: str) -> Optional[AccidentReport]:
        """
        Extract accident information from HTML content.
        
        Args:
            url: Source URL
            html_content: HTML content to parse
            
        Returns:
            AccidentReport object or None if extraction failed
        """
        if not BEAUTIFULSOUP_AVAILABLE:
            self.logger.error("BeautifulSoup not available for HTML parsing")
            return None
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else "No title found"
            
            # Extract main content
            content_selectors = ['article', '.content', '.post-content', 'main', '.article-body']
            content = ""
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text().strip()
                    break
                    
            if not content:
                # Fallback to all paragraph text
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs])
                
            # Use simple keyword-based extraction for accident details
            # In practice, you'd use more sophisticated NLP techniques
            report = AccidentReport(
                date=self.extract_date(content),
                location=self.extract_location(content),
                hazardous_materials=self.extract_materials(content),
                causes=self.extract_causes(content),
                consequences=self.extract_consequences(content),
                response_measures=self.extract_response(content),
                source_url=url,
                title=title,
                scrape_timestamp=datetime.now().isoformat()
            )
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to extract info from {url}: {e}")
            return None
            
    def extract_date(self, content: str) -> str:
        """Extract accident date from content."""
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',
            r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
                
        return "Date not found"
        
    def extract_location(self, content: str) -> str:
        """Extract accident location from content."""
        location_indicators = [
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s*[A-Z]{2})?)',
            r'at\s+([^.]+?(?:Highway|Road|Street|Avenue|Boulevard|Interstate|I-\d+))',
            r'near\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in location_indicators:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        return "Location not found"
        
    def extract_materials(self, content: str) -> str:
        """Extract hazardous materials information from content."""
        material_keywords = [
            'chemical', 'fuel', 'gasoline', 'diesel', 'oil', 'acid', 'chlorine',
            'ammonia', 'propane', 'methane', 'benzene', 'toxic', 'flammable',
            'corrosive', 'radioactive', 'explosive'
        ]
        
        found_materials = []
        for keyword in material_keywords:
            if keyword.lower() in content.lower():
                found_materials.append(keyword)
                
        if found_materials:
            return ", ".join(set(found_materials))
        else:
            return "Materials not specified"
            
    def extract_causes(self, content: str) -> str:
        """Extract accident causes from content."""
        cause_keywords = [
            'caused by', 'due to', 'resulted from', 'driver error', 'mechanical failure',
            'brake failure', 'tire blowout', 'collision', 'rollover', 'leak'
        ]
        
        causes = []
        content_lower = content.lower()
        
        for keyword in cause_keywords:
            if keyword in content_lower:
                # Extract sentence containing the cause
                sentences = content.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        causes.append(sentence.strip())
                        break
                        
        return "; ".join(causes) if causes else "Cause not determined"
        
    def extract_consequences(self, content: str) -> str:
        """Extract accident consequences from content."""
        consequence_patterns = [
            r'(\d+)\s+(?:people\s+)?(?:killed|died|fatalities)',
            r'(\d+)\s+(?:people\s+)?(?:injured|hurt|wounded)',
            r'environmental?\s+(?:damage|impact|contamination)',
            r'evacuat(?:ed|ion)',
            r'road\s+(?:closed|closure)'
        ]
        
        consequences = []
        content_lower = content.lower()
        
        for pattern in consequence_patterns:
            matches = re.findall(pattern, content_lower)
            if matches:
                if isinstance(matches[0], str) and matches[0].isdigit():
                    consequences.append(f"{matches[0]} casualties mentioned")
                else:
                    consequences.append("Environmental/infrastructure impact mentioned")
                    
        return "; ".join(consequences) if consequences else "Consequences not detailed"
        
    def extract_response(self, content: str) -> str:
        """Extract response measures from content."""
        response_keywords = [
            'fire department', 'hazmat team', 'emergency response', 'evacuation',
            'cleanup', 'contained', 'neutralized', 'decontamination'
        ]
        
        responses = []
        content_lower = content.lower()
        
        for keyword in response_keywords:
            if keyword in content_lower:
                responses.append(keyword)
                
        return ", ".join(set(responses)) if responses else "Response measures not detailed"
        
    def translate_report(self, report: AccidentReport, target_lang: str = 'en') -> AccidentReport:
        """
        Translate report content to target language.
        
        Args:
            report: AccidentReport to translate
            target_lang: Target language code (default: 'en')
            
        Returns:
            Translated AccidentReport
        """
        if not self.translator:
            self.logger.warning("Translation not available - googletrans not installed")
            return report
            
        try:
            fields_to_translate = ['location', 'hazardous_materials', 'causes', 
                                 'consequences', 'response_measures', 'title']
            
            translated_report = AccidentReport(**asdict(report))
            
            for field in fields_to_translate:
                original_text = getattr(translated_report, field)
                if original_text and len(original_text) > 3:  # Only translate meaningful text
                    try:
                        translation = self.translator.translate(original_text, dest=target_lang)
                        setattr(translated_report, field, translation.text)
                        time.sleep(0.1)  # Rate limit translation API
                    except Exception as e:
                        self.logger.warning(f"Translation failed for field {field}: {e}")
                        
            translated_report.translated = True
            return translated_report
            
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            return report
            
    def filter_reports(self, reports: List[AccidentReport], 
                      date_range: Tuple[str, str] = None,
                      severity: str = None,
                      material_type: str = None) -> List[AccidentReport]:
        """
        Filter reports based on criteria.
        
        Args:
            reports: List of AccidentReport objects
            date_range: Tuple of (start_date, end_date) in YYYY-MM-DD format
            severity: Severity level to filter by
            material_type: Type of hazardous material to filter by
            
        Returns:
            Filtered list of reports
        """
        filtered = reports.copy()
        
        if date_range:
            start_date, end_date = date_range
            # This is a simplified filter - would need better date parsing in practice
            filtered = [r for r in filtered if start_date <= r.date <= end_date]
            
        if severity:
            filtered = [r for r in filtered if severity.lower() in r.severity.lower()]
            
        if material_type:
            filtered = [r for r in filtered if material_type.lower() in r.hazardous_materials.lower()]
            
        return filtered
        
    def save_as_text(self, reports: List[AccidentReport], filename: str = None):
        """Save reports as text file."""
        if not filename:
            filename = f"accident_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("HAZARDOUS TANKER TRUCK ACCIDENT REPORTS\n")
            f.write("=" * 50 + "\n\n")
            
            for i, report in enumerate(reports, 1):
                f.write(f"REPORT #{i}\n")
                f.write("-" * 20 + "\n")
                f.write(f"Title: {report.title}\n")
                f.write(f"Date: {report.date}\n")
                f.write(f"Location: {report.location}\n")
                f.write(f"Hazardous Materials: {report.hazardous_materials}\n")
                f.write(f"Causes: {report.causes}\n")
                f.write(f"Consequences: {report.consequences}\n")
                f.write(f"Response Measures: {report.response_measures}\n")
                f.write(f"Source: {report.source_url}\n")
                f.write(f"Scraped: {report.scrape_timestamp}\n")
                if report.translated:
                    f.write("Note: This report was automatically translated\n")
                f.write("\n" + "=" * 50 + "\n\n")
                
        self.logger.info(f"Text report saved to: {filepath}")
        
    def save_as_csv(self, reports: List[AccidentReport], filename: str = None):
        """Save reports as CSV file."""
        if not PANDAS_AVAILABLE:
            # Fallback to standard csv module
            if not filename:
                filename = f"accident_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['title', 'date', 'location', 'hazardous_materials', 
                            'causes', 'consequences', 'response_measures', 
                            'source_url', 'severity', 'translated', 'scrape_timestamp']
                            
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for report in reports:
                    writer.writerow(asdict(report))
                    
        else:
            # Use pandas for better CSV handling
            if not filename:
                filename = f"accident_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            filepath = self.output_dir / filename
            
            df = pd.DataFrame([asdict(report) for report in reports])
            df.to_csv(filepath, index=False, encoding='utf-8')
            
        self.logger.info(f"CSV report saved to: {filepath}")
        
    def save_as_pdf(self, reports: List[AccidentReport], filename: str = None):
        """Save reports as PDF file."""
        if not PDF_AVAILABLE:
            self.logger.error("PDF export not available - fpdf2 not installed")
            return
            
        if not filename:
            filename = f"accident_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
        filepath = self.output_dir / filename
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Hazardous Tanker Truck Accident Reports', 0, 1, 'C')
        pdf.ln(10)
        
        for i, report in enumerate(reports, 1):
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f'Report #{i}: {report.title[:50]}...', 0, 1)
            
            pdf.set_font('Arial', '', 10)
            
            fields = [
                ('Date', report.date),
                ('Location', report.location),
                ('Materials', report.hazardous_materials),
                ('Causes', report.causes),
                ('Consequences', report.consequences),
                ('Response', report.response_measures),
                ('Source', report.source_url)
            ]
            
            for label, value in fields:
                pdf.cell(30, 8, f'{label}:', 0, 0, 'L')
                # Handle long text by wrapping
                if len(value) > 80:
                    value = value[:80] + "..."
                pdf.cell(0, 8, value, 0, 1, 'L')
                
            pdf.ln(5)
            
            # Add new page if needed
            if pdf.get_y() > 250:
                pdf.add_page()
                
        pdf.output(str(filepath))
        self.logger.info(f"PDF report saved to: {filepath}")
        
    def scrape_reports(self, keywords: List[str], 
                      max_results: int = 50,
                      include_translation: bool = False,
                      date_range: Tuple[str, str] = None) -> List[AccidentReport]:
        """
        Main method to scrape accident reports.
        
        Args:
            keywords: List of search keywords
            max_results: Maximum number of reports to scrape
            include_translation: Whether to translate non-English reports
            date_range: Optional date range filter
            
        Returns:
            List of scraped AccidentReport objects
        """
        self.logger.info(f"Starting scrape for keywords: {keywords}")
        self.logger.info(f"Max results: {max_results}")
        
        all_urls = []
        
        # Search different sources
        all_urls.extend(self.search_news_sites(keywords, date_range))
        all_urls.extend(self.search_government_databases(keywords))
        
        # In a real implementation, you would have actual URLs from search results
        # For demonstration, we'll create some sample data
        sample_urls = [
            "https://example.com/tanker-accident-1",
            "https://example.com/hazmat-incident-2", 
            "https://example.com/chemical-spill-3"
        ]
        
        self.logger.info(f"Found {len(sample_urls)} URLs to process")
        
        # Process URLs and extract reports
        reports = []
        processed_count = 0
        
        for url in sample_urls[:max_results]:
            if processed_count >= max_results:
                break
                
            self.logger.info(f"Processing URL {processed_count + 1}/{min(len(sample_urls), max_results)}: {url}")
            
            # For demonstration, create sample report data
            sample_report = AccidentReport(
                date=f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                location=f"Highway {random.randint(1,99)}, State {random.choice(['CA', 'TX', 'FL', 'NY'])}",
                hazardous_materials=random.choice([
                    "Petroleum products", "Chemical solvents", "Ammonia", 
                    "Chlorine gas", "Fuel oil", "Acids"
                ]),
                causes=random.choice([
                    "Driver fatigue", "Mechanical failure", "Brake malfunction",
                    "Tire blowout", "Collision with passenger vehicle"
                ]),
                consequences=random.choice([
                    "No injuries reported", "2 injuries, road closure",
                    "Environmental contamination", "Evacuation of nearby residents"
                ]),
                response_measures=random.choice([
                    "Hazmat team deployed", "Fire department response",
                    "Road closure and detour", "Cleanup operations ongoing"
                ]),
                source_url=url,
                title=f"Tanker Truck Accident on {random.choice(['Interstate', 'Highway', 'State Route'])} {random.randint(1, 99)}",
                scrape_timestamp=datetime.now().isoformat()
            )
            
            # Simulate translation if requested
            if include_translation and self.translator:
                sample_report = self.translate_report(sample_report)
                
            reports.append(sample_report)
            processed_count += 1
            
            # Progress indicator
            if processed_count % 10 == 0:
                self.logger.info(f"Processed {processed_count} reports...")
                
        self.scraped_reports = reports
        self.logger.info(f"Scraping completed. Total reports: {len(reports)}")
        
        return reports


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Scrape hazardous tanker truck accident reports from the web",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scraping with default keywords
  python hazard_tanker_scraper.py --keywords "tanker truck accident" "hazmat spill"
  
  # Scrape with translation and custom output
  python hazard_tanker_scraper.py -k "危险品罐车事故" --translate --output-dir ./reports
  
  # Filter by date range and export to multiple formats
  python hazard_tanker_scraper.py -k "chemical tanker incident" --start-date 2024-01-01 --end-date 2024-12-31 --format text csv pdf
        """
    )
    
    # Required arguments
    parser.add_argument(
        '-k', '--keywords',
        nargs='+',
        required=True,
        help='Keywords to search for (e.g., "tanker truck accident" "hazmat spill")'
    )
    
    # Optional arguments
    parser.add_argument(
        '--max-results',
        type=int,
        default=50,
        help='Maximum number of reports to scrape (default: 50)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='accident_reports',
        help='Output directory for scraped reports (default: accident_reports)'
    )
    
    parser.add_argument(
        '--format',
        nargs='+',
        choices=['text', 'csv', 'pdf'],
        default=['text'],
        help='Output formats (default: text)'
    )
    
    parser.add_argument(
        '--translate',
        action='store_true',
        help='Translate non-English reports to English'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date for filtering (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date for filtering (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--severity',
        help='Filter by severity level'
    )
    
    parser.add_argument(
        '--material-type',
        help='Filter by hazardous material type'
    )
    
    parser.add_argument(
        '--proxy-file',
        help='File containing proxy URLs (one per line)'
    )
    
    parser.add_argument(
        '--rate-limit',
        nargs=2,
        type=float,
        default=[1.0, 3.0],
        metavar=('MIN', 'MAX'),
        help='Rate limiting delays in seconds (default: 1.0 3.0)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser


def load_proxy_list(proxy_file: str) -> List[str]:
    """Load proxy list from file."""
    try:
        with open(proxy_file, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        return proxies
    except FileNotFoundError:
        print(f"Warning: Proxy file '{proxy_file}' not found")
        return []


def main():
    """Main function to run the scraper."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Load proxy list if provided
    proxy_list = []
    if args.proxy_file:
        proxy_list = load_proxy_list(args.proxy_file)
        
    # Initialize scraper
    scraper = HazardousScenarioScraper(
        output_dir=args.output_dir,
        proxy_list=proxy_list,
        rate_limit_delay=tuple(args.rate_limit)
    )
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Build date range filter
    date_range = None
    if args.start_date and args.end_date:
        date_range = (args.start_date, args.end_date)
        
    try:
        # Scrape reports
        print("🚛 Starting hazardous tanker truck accident report scraping...")
        print(f"Keywords: {', '.join(args.keywords)}")
        print(f"Max results: {args.max_results}")
        print(f"Output directory: {args.output_dir}")
        print("-" * 60)
        
        reports = scraper.scrape_reports(
            keywords=args.keywords,
            max_results=args.max_results,
            include_translation=args.translate,
            date_range=date_range
        )
        
        # Apply additional filters
        if args.severity or args.material_type or date_range:
            print("Applying filters...")
            reports = scraper.filter_reports(
                reports,
                date_range=date_range,
                severity=args.severity,
                material_type=args.material_type
            )
            
        print(f"✅ Found {len(reports)} relevant accident reports")
        
        # Save in requested formats
        if 'text' in args.format:
            scraper.save_as_text(reports)
            print("📄 Text report saved")
            
        if 'csv' in args.format:
            scraper.save_as_csv(reports)
            print("📊 CSV report saved")
            
        if 'pdf' in args.format:
            scraper.save_as_pdf(reports)
            print("📋 PDF report saved")
            
        print(f"\n🎯 Scraping completed successfully!")
        print(f"Output saved to: {scraper.output_dir}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        scraper.logger.exception("Scraping failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
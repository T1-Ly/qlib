#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Report Scraper Tool

A Python script that searches and scrapes reports related to keywords from the web.
Features:
- Web search for reports based on keywords
- Extract and save relevant information
- Save as PDF or text file options
- Error handling and rate limiting
- Robots.txt compliance
- Command-line interface
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

import requests

# Set up logger
logger = logging.getLogger(__name__)

# Add parent directory to path to import utils
sys.path.append(str(Path(__file__).parent.parent))

# Simple retry decorator since we can't import from utils
def deco_retry(max_retry: int = 5, sleep_time: float = 1):
    """Simple retry decorator"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retry):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retry - 1:
                        raise e
                    time.sleep(sleep_time * (attempt + 1))
            return None
        return wrapper
    return decorator

# Default headers to mimic a real browser
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36"
}

# Search engines and their query formats
SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={query}+filetype:pdf",
    "bing": "https://www.bing.com/search?q={query}+filetype:pdf",
    "duckduckgo": "https://duckduckgo.com/?q={query}+filetype:pdf"
}

# Common report file extensions
REPORT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.html', '.htm']


class RobotChecker:
    """Handle robots.txt compliance"""
    
    def __init__(self):
        self._robots_cache = {}
    
    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched according to robots.txt"""
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url not in self._robots_cache:
                robots_url = f"{base_url}/robots.txt"
                rp = urllib.robotparser.RobotFileParser()
                rp.set_url(robots_url)
                try:
                    rp.read()
                    self._robots_cache[base_url] = rp
                except Exception:
                    # If robots.txt can't be read, assume fetching is allowed
                    self._robots_cache[base_url] = None
            
            robots_parser = self._robots_cache[base_url]
            if robots_parser is None:
                return True
            
            return robots_parser.can_fetch(user_agent, url)
        except Exception:
            # If there's any error, assume fetching is allowed
            return True


class ReportScraper:
    """Main class for scraping reports based on keywords"""
    
    def __init__(self, delay: float = 1.0, max_retries: int = 3):
        """
        Initialize the report scraper
        
        Args:
            delay: Delay between requests in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.delay = delay
        self.max_retries = max_retries
        self.robot_checker = RobotChecker()
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        
    @deco_retry(max_retry=3, sleep_time=1)
    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """Make a HTTP request with retry logic"""
        response = self.session.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response
    
    def search_reports(self, keyword: str, search_engine: str = "google", max_results: int = 10) -> List[Dict]:
        """
        Search for reports related to a keyword
        
        Args:
            keyword: Search keyword
            search_engine: Search engine to use ('google', 'bing', 'duckduckgo')
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing report information
        """
        if search_engine not in SEARCH_ENGINES:
            raise ValueError(f"Unsupported search engine: {search_engine}")
        
        # Prepare search query
        query = urllib.parse.quote_plus(f"{keyword} report")
        search_url = SEARCH_ENGINES[search_engine].format(query=query)
        
        logger.info(f"Searching for '{keyword}' reports using {search_engine}")
        
        try:
            # Check robots.txt compliance
            if not self.robot_checker.can_fetch(search_url):
                logger.warning(f"Robots.txt disallows fetching {search_url}")
                return []
            
            response = self._make_request(search_url)
            time.sleep(self.delay)  # Rate limiting
            
            # Extract links from search results (simplified implementation)
            results = self._extract_search_results(response.text, search_engine, max_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching for reports: {e}")
            return []
    
    def _extract_search_results(self, html_content: str, search_engine: str, max_results: int) -> List[Dict]:
        """Extract search result URLs from HTML content"""
        results = []
        
        try:
            # Simple regex patterns for different search engines
            if search_engine == "google":
                # Google search result pattern
                pattern = r'<a[^>]+href="(/url\?q=|)(https?://[^"&]+)'
            elif search_engine == "bing":
                # Bing search result pattern  
                pattern = r'<a[^>]+href="(https?://[^"]+)"'
            else:
                # DuckDuckGo and generic pattern
                pattern = r'<a[^>]+href="(https?://[^"]+)"'
            
            matches = re.findall(pattern, html_content)
            
            for match in matches[:max_results]:
                url = match[1] if isinstance(match, tuple) and len(match) > 1 else match[0] if isinstance(match, tuple) else match
                
                # Filter for report-like URLs
                if any(ext in url.lower() for ext in REPORT_EXTENSIONS):
                    results.append({
                        'url': url,
                        'title': self._extract_title_from_url(url),
                        'type': self._get_file_type(url),
                        'found_at': datetime.now().isoformat()
                    })
                    
                    if len(results) >= max_results:
                        break
                        
        except Exception as e:
            logger.error(f"Error extracting search results: {e}")
        
        return results
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from URL"""
        # Simple title extraction from URL
        parsed = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed.path)
        if filename:
            return os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
        return parsed.netloc
    
    def _get_file_type(self, url: str) -> str:
        """Get file type from URL"""
        for ext in REPORT_EXTENSIONS:
            if ext in url.lower():
                return ext.upper().lstrip('.')
        return 'UNKNOWN'
    
    def download_report(self, report_info: Dict) -> Optional[bytes]:
        """
        Download a report file
        
        Args:
            report_info: Dictionary containing report information
            
        Returns:
            Report content as bytes or None if download failed
        """
        url = report_info['url']
        
        try:
            # Check robots.txt compliance
            if not self.robot_checker.can_fetch(url):
                logger.warning(f"Robots.txt disallows fetching {url}")
                return None
            
            logger.info(f"Downloading report: {report_info['title']}")
            response = self._make_request(url)
            time.sleep(self.delay)  # Rate limiting
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error downloading report {url}: {e}")
            return None
    
    def save_report(self, content: bytes, filename: str, output_format: str = "original") -> bool:
        """
        Save report content to file
        
        Args:
            content: Report content as bytes
            filename: Output filename
            output_format: Format to save ('original', 'txt', 'pdf')
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            output_path = Path(filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if output_format == "original":
                # Save as original format
                with open(output_path, 'wb') as f:
                    f.write(content)
            elif output_format == "txt":
                # Convert to text (simplified)
                text_content = self._extract_text_content(content)
                with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
                    f.write(text_content)
            elif output_format == "pdf":
                # Save as PDF (would require reportlab)
                logger.warning("PDF conversion not implemented - saving as original format")
                with open(output_path, 'wb') as f:
                    f.write(content)
            
            logger.info(f"Report saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            return False
    
    def _extract_text_content(self, content: bytes) -> str:
        """Extract text content from various file formats"""
        try:
            # Try to decode as text first
            text = content.decode('utf-8', errors='ignore')
            
            # Simple HTML tag removal if content appears to be HTML
            if '<html' in text.lower() or '<body' in text.lower():
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception:
            return "Could not extract text content"
    
    def generate_report_summary(self, reports: List[Dict], keyword: str) -> Dict:
        """Generate a summary of found reports"""
        summary = {
            'keyword': keyword,
            'total_reports': len(reports),
            'report_types': {},
            'search_timestamp': datetime.now().isoformat(),
            'reports': reports
        }
        
        # Count report types
        for report in reports:
            report_type = report.get('type', 'UNKNOWN')
            summary['report_types'][report_type] = summary['report_types'].get(report_type, 0) + 1
        
        return summary


def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(
        description="Search and scrape reports related to keywords from the web",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python report_scraper.py --keyword "financial report" --max-results 5
  python report_scraper.py --keyword "climate change" --output-dir ./reports --format txt
  python report_scraper.py --keyword "market analysis" --search-engine bing --delay 2.0
        """
    )
    
    parser.add_argument(
        '--keyword', '-k',
        required=True,
        help='Keyword to search for reports'
    )
    
    parser.add_argument(
        '--search-engine', '-s',
        choices=['google', 'bing', 'duckduckgo'],
        default='google',
        help='Search engine to use (default: google)'
    )
    
    parser.add_argument(
        '--max-results', '-m',
        type=int,
        default=10,
        help='Maximum number of results to fetch (default: 10)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='./scraped_reports',
        help='Output directory for saved reports (default: ./scraped_reports)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['original', 'txt', 'pdf'],
        default='original',
        help='Output format (default: original)'
    )
    
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--download',
        action='store_true',
        help='Download the actual report files (default: False, only list URLs)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Initialize scraper
    scraper = ReportScraper(delay=args.delay)
    
    try:
        # Search for reports
        logger.info(f"Starting search for keyword: '{args.keyword}'")
        reports = scraper.search_reports(
            keyword=args.keyword,
            search_engine=args.search_engine,
            max_results=args.max_results
        )
        
        if not reports:
            logger.warning("No reports found")
            return
        
        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate and save summary
        summary = scraper.generate_report_summary(reports, args.keyword)
        summary_file = output_dir / f"{args.keyword.replace(' ', '_')}_summary.json"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Summary saved to: {summary_file}")
        
        # Print results
        print(f"\nFound {len(reports)} reports for keyword '{args.keyword}':")
        print("-" * 80)
        
        for i, report in enumerate(reports, 1):
            print(f"{i}. {report['title']}")
            print(f"   URL: {report['url']}")
            print(f"   Type: {report['type']}")
            print()
        
        # Download reports if requested
        if args.download:
            logger.info("Starting report downloads...")
            
            for i, report in enumerate(reports, 1):
                try:
                    content = scraper.download_report(report)
                    if content:
                        filename = f"{args.keyword.replace(' ', '_')}_report_{i}"
                        scraper.save_report(content, str(output_dir / filename), args.format)
                except Exception as e:
                    logger.error(f"Failed to download report {i}: {e}")
                    continue
        
        logger.info("Report scraping completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
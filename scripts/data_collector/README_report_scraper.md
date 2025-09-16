# Report Scraper Tool

A Python script that searches and scrapes reports related to keywords from the web. This tool provides a command-line interface for finding, analyzing, and downloading reports from various sources while respecting robots.txt rules and implementing proper rate limiting.

## Features

- **Keyword-based search**: Search for reports using keywords across multiple search engines
- **Multiple search engines**: Support for Google, Bing, and DuckDuckGo
- **File format detection**: Automatically detect and categorize different report formats (PDF, DOC, HTML, TXT, etc.)
- **Rate limiting**: Configurable delays between requests to avoid being blocked
- **Robots.txt compliance**: Respects robots.txt rules for ethical web scraping
- **Multiple output formats**: Save reports in original format, text, or PDF
- **Comprehensive logging**: Detailed logging with configurable verbosity
- **Report summarization**: Generate JSON summaries of found reports
- **Error handling**: Robust error handling for network issues and parsing errors

## Requirements

- Python 3.8+
- `requests` library
- Standard Python libraries (urllib, json, logging, etc.)

## Installation

The script is designed to work with the existing qlib environment. No additional installation is required beyond the standard qlib dependencies.

## Usage

### Basic Usage

```bash
# Search for financial reports
python report_scraper.py --keyword "financial report" --max-results 5

# Search with a specific search engine
python report_scraper.py --keyword "climate change" --search-engine bing

# Download reports and save as text files
python report_scraper.py --keyword "market analysis" --download --format txt
```

### Advanced Usage

```bash
# Comprehensive search with custom settings
python report_scraper.py \
    --keyword "annual sustainability report" \
    --search-engine google \
    --max-results 10 \
    --output-dir ./my_reports \
    --format original \
    --delay 2.0 \
    --download \
    --verbose

# Quick search with short options
python report_scraper.py -k "AI research" -m 3 -s duckduckgo -v
```

### Command Line Options

- `--keyword, -k`: **Required**. Keyword to search for reports
- `--search-engine, -s`: Search engine to use (google, bing, duckduckgo). Default: google
- `--max-results, -m`: Maximum number of results to fetch. Default: 10
- `--output-dir, -o`: Output directory for saved reports. Default: ./scraped_reports
- `--format, -f`: Output format (original, txt, pdf). Default: original
- `--delay, -d`: Delay between requests in seconds. Default: 1.0
- `--download`: Download the actual report files. Default: False (only list URLs)
- `--verbose, -v`: Enable verbose logging
- `--help, -h`: Show help message

## Output

The script generates several types of output:

### 1. Console Output
Displays found reports with titles, URLs, and file types:

```
Found 5 reports for keyword 'financial report':
--------------------------------------------------------------------------------
1. Annual Financial Report 2023
   URL: https://example.com/reports/annual_financial_report_2023.pdf
   Type: PDF

2. Quarterly Earnings Q4 2023
   URL: https://investor.example.com/quarterly_earnings_q4_2023.pdf
   Type: PDF
```

### 2. JSON Summary
Creates a comprehensive summary file with metadata:

```json
{
  "keyword": "financial report",
  "total_reports": 5,
  "report_types": {
    "PDF": 3,
    "HTML": 1,
    "TXT": 1
  },
  "search_timestamp": "2024-01-15T10:30:00",
  "reports": [
    {
      "url": "https://example.com/report.pdf",
      "title": "Annual Report 2023",
      "type": "PDF",
      "found_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### 3. Downloaded Files
When `--download` is specified, the script downloads and saves report files to the specified output directory.

## Technical Features

### Robots.txt Compliance
The script automatically checks and respects robots.txt files:
- Caches robots.txt files to avoid repeated requests
- Skips URLs that are disallowed by robots.txt
- Gracefully handles missing or invalid robots.txt files

### Rate Limiting
Configurable delays between requests to avoid overloading servers:
- Default 1-second delay between requests
- Exponential backoff for retry attempts
- Respects server response times

### Error Handling
Comprehensive error handling for:
- Network connectivity issues
- HTTP errors (404, 403, etc.)
- Parsing errors
- File I/O errors
- Invalid URLs

### Content Processing
- Automatic file type detection based on URL patterns
- Basic HTML tag removal for text extraction
- Title extraction from URLs and content
- Support for various report formats

## Architecture

The script is organized into several key classes:

### `RobotChecker`
Handles robots.txt compliance and caching.

### `ReportScraper`
Main class containing:
- Search functionality
- Report downloading
- Content processing
- Summary generation

### Search Engines
Supports multiple search engines with different URL patterns and result parsing.

## Limitations

1. **Search Result Parsing**: The script uses simplified regex patterns for parsing search results. More sophisticated parsing could be implemented with HTML parsing libraries.

2. **Content Extraction**: Text extraction is basic and works best with simple HTML content. Advanced document parsing would require additional libraries.

3. **PDF Generation**: PDF output format requires additional libraries (reportlab) which are not included by default.

4. **Dynamic Content**: The script doesn't handle JavaScript-rendered content. Selenium could be added for dynamic content scraping.

## Best Practices

1. **Use appropriate delays**: Set reasonable delays (1-2 seconds) to be respectful to servers
2. **Limit result counts**: Don't request too many results in a single run
3. **Monitor robots.txt**: The script respects robots.txt, but manual verification is recommended
4. **Handle errors gracefully**: The script includes error handling, but monitor logs for issues
5. **Use specific keywords**: More specific keywords yield better, more relevant results

## Examples

### Example 1: Basic Financial Report Search
```bash
python report_scraper.py --keyword "annual financial report 2023" --max-results 5
```

### Example 2: Academic Research Papers
```bash
python report_scraper.py \
    --keyword "machine learning research" \
    --search-engine duckduckgo \
    --max-results 10 \
    --verbose
```

### Example 3: Corporate Sustainability Reports
```bash
python report_scraper.py \
    --keyword "sustainability report ESG" \
    --download \
    --format txt \
    --output-dir ./sustainability_reports \
    --delay 2.0
```

## Integration with Qlib

This script follows qlib's architecture patterns:
- Uses similar error handling patterns as other data collectors
- Follows the project's coding standards
- Integrates with the existing scripts/data_collector structure
- Uses compatible logging and configuration approaches

## License

This script is part of the qlib project and is licensed under the MIT License.
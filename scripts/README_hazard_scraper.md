# Hazardous Tanker Truck Accident Report Scraper

A Python script for scraping and analyzing hazardous tanker truck accident reports from various web sources.

## Overview

This script searches for and collects relevant accident reports from multiple sources including news sites, government safety databases, and industry publications. It extracts key information about accidents and exports the data in multiple formats for analysis.

## Features

- **Keyword-based Search**: Search for accidents using specific keywords in multiple languages
- **Multiple Data Sources**: Support for news sites, government databases, and industry publications
- **Data Extraction**: Extracts key accident information including:
  - Date and location of accidents
  - Types of hazardous materials involved
  - Accident causes and consequences
  - Emergency response measures taken
- **Export Formats**: Save data as text files, CSV, or PDF reports
- **Filtering**: Filter results by date range, severity, or material type
- **Translation**: Translate non-English reports to English (requires googletrans)
- **Web Scraping Best Practices**: 
  - Respects robots.txt
  - Rate limiting between requests
  - Proxy rotation support
  - Proper HTTP headers

## Installation

1. Install additional dependencies:
```bash
pip install -r scripts/scraper_requirements.txt
```

2. Make the script executable:
```bash
chmod +x scripts/hazard_tanker_scraper.py
```

## Usage

### Basic Usage

```bash
python scripts/hazard_tanker_scraper.py --keywords "tanker truck accident" "hazmat spill"
```

### Advanced Usage

```bash
# Search with translation and custom output directory
python scripts/hazard_tanker_scraper.py \
    --keywords "危险品罐车事故" "chemical tanker incident" \
    --translate \
    --output-dir ./accident_reports \
    --max-results 100

# Filter by date range and export to multiple formats
python scripts/hazard_tanker_scraper.py \
    --keywords "hazardous materials tanker accident" \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --format text csv pdf \
    --severity high

# Use proxy rotation and custom rate limiting
python scripts/hazard_tanker_scraper.py \
    --keywords "tanker truck accident" \
    --proxy-file proxies.txt \
    --rate-limit 2.0 5.0 \
    --verbose
```

## Command Line Options

- `--keywords` / `-k`: Search keywords (required)
- `--max-results`: Maximum number of reports to scrape (default: 50)
- `--output-dir`: Output directory for reports (default: accident_reports)
- `--format`: Output formats: text, csv, pdf (default: text)
- `--translate`: Translate non-English reports to English
- `--start-date`: Start date for filtering (YYYY-MM-DD)
- `--end-date`: End date for filtering (YYYY-MM-DD)
- `--severity`: Filter by severity level
- `--material-type`: Filter by hazardous material type
- `--proxy-file`: File containing proxy URLs (one per line)
- `--rate-limit`: Rate limiting delays in seconds (min max)
- `--verbose`: Enable verbose logging

## Sample Keywords

### English Keywords
- "tanker truck accident"
- "hazardous materials tanker accident"
- "chemical tanker truck incident"
- "fuel tanker rollover"
- "hazmat spill highway"

### Chinese Keywords
- "危险品罐车事故"
- "油罐车事故"
- "化学品运输事故"

### Spanish Keywords
- "accidente camión cisterna"
- "derrame materiales peligrosos"

## Output Formats

### Text Format
Human-readable reports with all extracted information organized by sections.

### CSV Format
Structured data suitable for analysis with tools like Excel or pandas:
- title, date, location, hazardous_materials, causes, consequences, response_measures, source_url, severity, translated, scrape_timestamp

### PDF Format
Professional-looking reports suitable for sharing or archiving.

## Configuration

### Proxy Configuration
Create a `proxies.txt` file with one proxy URL per line:
```
http://proxy1.example.com:8080
http://proxy2.example.com:8080
http://proxy3.example.com:8080
```

### Rate Limiting
The script includes built-in rate limiting to be respectful to websites:
- Default: 1-3 seconds between requests
- Configurable via `--rate-limit` option
- Random delays to avoid detection

## Data Sources

The scraper is designed to work with various types of sources:

### News Sites
- Reuters, AP News, CNN, BBC
- Local news stations
- Industry publications

### Government Databases
- NTSB (National Transportation Safety Board)
- PHMSA (Pipeline and Hazardous Materials Safety Administration)
- OSHA (Occupational Safety and Health Administration)
- DOT (Department of Transportation)

### Industry Sources
- Chemical industry publications
- Transportation safety organizations
- Environmental agencies

## Legal and Ethical Considerations

- Always respect robots.txt files
- Use reasonable rate limiting
- Don't overload servers with requests
- Follow website terms of service
- Consider data privacy implications
- Verify accuracy of scraped information

## Troubleshooting

### Common Issues

1. **Import Errors**: Install missing dependencies
   ```bash
   pip install -r scripts/scraper_requirements.txt
   ```

2. **Translation Errors**: Check internet connection and googletrans version
   ```bash
   pip install googletrans==4.0.0rc1
   ```

3. **PDF Generation Errors**: Install fpdf2
   ```bash
   pip install fpdf2
   ```

4. **Connection Issues**: Try using proxies or adjusting rate limits

### Logging

All activities are logged to:
- Console output
- Log file in output directory: `accident_reports/scraper.log`

Use `--verbose` flag for detailed logging.

## Examples

### Example 1: Basic Accident Search
```bash
python scripts/hazard_tanker_scraper.py \
    --keywords "tanker truck accident" \
    --max-results 25 \
    --format text csv
```

### Example 2: Multi-language Search with Translation
```bash
python scripts/hazard_tanker_scraper.py \
    --keywords "危险品罐车事故" "accidente camión cisterna" \
    --translate \
    --format pdf
```

### Example 3: Filtered Search
```bash
python scripts/hazard_tanker_scraper.py \
    --keywords "chemical tanker incident" \
    --start-date 2024-01-01 \
    --end-date 2024-06-30 \
    --material-type "chemical" \
    --format csv
```

## Contributing

To add support for new data sources:

1. Add the source to the appropriate search method (`search_news_sites`, `search_government_databases`)
2. Implement source-specific parsing in `extract_accident_info`
3. Test with sample data
4. Update documentation

## License

This script is part of the Qlib project and follows the same MIT license.

## Disclaimer

This tool is for research and educational purposes. Always verify the accuracy of scraped information and respect website terms of service. The authors are not responsible for how this tool is used or the accuracy of the data it collects.
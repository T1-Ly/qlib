#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危险品罐车事故报告收集器
Hazardous Materials Tanker Accident Report Collector

这个脚本用于动态发现和收集危险品罐车事故报告。它使用搜索引擎API和网络爬虫技术
来查找相关内容，提取关键信息，并以多种格式保存结果。

This script is designed to dynamically discover and collect hazardous materials
tanker accident reports using search engine APIs and web crawling techniques.
"""

import os
import re
import csv
import json
import time
import random
import logging
import datetime
import argparse
import urllib.request
import urllib.parse
import urllib.robotparser
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 设置中文日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hazmat_collector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class AccidentReport:
    """事故报告数据结构"""
    date: str = ""              # 事故发生日期
    location: str = ""          # 事故地点
    materials: str = ""         # 涉及的危险品类型
    cause: str = ""             # 事故原因
    consequences: str = ""      # 后果（人员伤亡、环境影响）
    measures: str = ""          # 采取的应对措施
    source_url: str = ""        # 信息来源URL
    title: str = ""             # 报告标题
    content: str = ""           # 完整内容
    severity: str = ""          # 严重程度
    scraped_at: str = ""        # 抓取时间


class ProxyRotator:
    """代理轮换器"""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxy_list = proxy_list or []
        self.current_index = 0
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """获取当前代理"""
        if not self.proxy_list:
            return None
        
        proxy = self.proxy_list[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxy_list)
        
        return {
            'http': proxy,
            'https': proxy
        }


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0
    
    def wait(self):
        """等待适当的时间间隔"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            logger.debug(f"等待 {sleep_time:.2f} 秒以遵守速率限制")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class RobotsChecker:
    """robots.txt 检查器"""
    
    def __init__(self):
        self.robots_cache = {}
    
    def can_fetch(self, url: str, user_agent: str = '*') -> bool:
        """检查是否允许抓取指定URL"""
        try:
            # 解析URL获取基础域名
            parsed = urllib.parse.urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = f"{base_url}/robots.txt"
            
            # 检查缓存
            if robots_url not in self.robots_cache:
                try:
                    rp = urllib.robotparser.RobotFileParser()
                    rp.set_url(robots_url)
                    rp.read()
                    self.robots_cache[robots_url] = rp
                except Exception as e:
                    logger.warning(f"无法读取 robots.txt {robots_url}: {e}")
                    # 如果无法读取robots.txt，假设允许抓取
                    return True
            
            robots_parser = self.robots_cache.get(robots_url)
            if robots_parser:
                return robots_parser.can_fetch(user_agent, url)
            else:
                return True
                
        except Exception as e:
            logger.warning(f"检查robots.txt时出错: {e}")
            return True


class BaseSearchEngine(ABC):
    """搜索引擎基础类"""
    
    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """
        搜索指定查询词
        
        Args:
            query: 搜索查询词
            num_results: 返回结果数量
            
        Returns:
            包含 'title', 'url', 'snippet' 的字典列表
        """
        pass


class DuckDuckGoSearchEngine(BaseSearchEngine):
    """DuckDuckGo 搜索引擎实现"""
    
    def __init__(self, session: requests.Session):
        self.session = session
        self.base_url = "https://html.duckduckgo.com/html/"
    
    def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """使用DuckDuckGo搜索"""
        try:
            # DuckDuckGo HTML搜索参数
            params = {
                'q': query,
                'b': '',  # 页面偏移
                'kl': 'cn-zh',  # 中文
            }
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            # 简单的HTML解析来提取搜索结果
            # 注意：实际生产环境中应该使用BeautifulSoup或类似库
            results = []
            content = response.text
            
            # 这里使用简单的正则表达式来提取结果
            # 在真实环境中，建议使用HTML解析器
            url_pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
            matches = re.findall(url_pattern, content)
            
            for url, title in matches[:num_results]:
                if url.startswith('http') and '事故' in title:
                    results.append({
                        'title': title.strip(),
                        'url': url,
                        'snippet': ''  # DuckDuckGo HTML版本较难提取摘要
                    })
            
            logger.info(f"DuckDuckGo搜索 '{query}' 返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo搜索失败: {e}")
            return []


class WebScraper:
    """网页内容抓取器"""
    
    def __init__(self, proxy_rotator: ProxyRotator, rate_limiter: RateLimiter, robots_checker: RobotsChecker):
        self.proxy_rotator = proxy_rotator
        self.rate_limiter = rate_limiter
        self.robots_checker = robots_checker
        
        # 配置会话
        self.session = requests.Session()
        
        # 设置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置真实浏览器头信息
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def fetch_page_content(self, url: str) -> Optional[str]:
        """抓取网页内容"""
        try:
            # 检查robots.txt
            if not self.robots_checker.can_fetch(url):
                logger.info(f"robots.txt 禁止抓取: {url}")
                return None
            
            # 应用速率限制
            self.rate_limiter.wait()
            
            # 设置代理（如果有）
            proxy = self.proxy_rotator.get_proxy()
            
            # 发送请求
            response = self.session.get(url, proxies=proxy, timeout=15)
            response.raise_for_status()
            
            # 尝试检测编码
            response.encoding = response.apparent_encoding or 'utf-8'
            
            logger.info(f"成功抓取: {url}")
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"抓取失败 {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"抓取过程中出现未知错误 {url}: {e}")
            return None


class AccidentDataExtractor:
    """事故数据提取器"""
    
    def __init__(self):
        # 关键词模式
        self.date_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}/\d{1,2}/\d{1,2})',
            r'(\d{1,2}月\d{1,2}日)',
        ]
        
        self.location_patterns = [
            r'([\u4e00-\u9fa5]+省[\u4e00-\u9fa5]+市)',
            r'([\u4e00-\u9fa5]+市[\u4e00-\u9fa5]+区)',
            r'([\u4e00-\u9fa5]+县)',
            r'在([\u4e00-\u9fa5]+)发生',
            r'([\u4e00-\u9fa5]+高速)',
        ]
        
        self.material_keywords = [
            '汽油', '柴油', '液化气', '天然气', '丙烷', '甲烷', '乙烯', '苯',
            '甲苯', '二甲苯', '丙酮', '乙醇', '甲醇', '硫酸', '盐酸', '硝酸',
            '氨水', '烧碱', '液氯', '液氨', '氯气', '危险品', '化学品',
            '易燃液体', '易燃气体', '有毒物质', '腐蚀性物质'
        ]
        
        self.cause_keywords = [
            '追尾', '侧翻', '爆胎', '制动失效', '疲劳驾驶', '超速', '违规超车',
            '设备故障', '管道破裂', '阀门失效', '密封不良', '超载', '违章操作',
            '天气恶劣', '路面湿滑', '雾天', '暴雨'
        ]
        
        self.consequence_keywords = [
            '死亡', '受伤', '失踪', '中毒', '烧伤', '爆炸', '火灾', '泄漏',
            '污染', '疏散', '封路', '停产', '环境污染', '水源污染', '土壤污染'
        ]
    
    def extract_accident_info(self, content: str, url: str = "", title: str = "") -> AccidentReport:
        """从内容中提取事故信息"""
        report = AccidentReport()
        report.source_url = url
        report.title = title
        report.content = content[:1000]  # 保存前1000字符
        report.scraped_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 提取日期
        for pattern in self.date_patterns:
            matches = re.findall(pattern, content)
            if matches:
                report.date = matches[0]
                break
        
        # 提取地点
        for pattern in self.location_patterns:
            matches = re.findall(pattern, content)
            if matches:
                report.location = matches[0]
                break
        
        # 提取涉及材料
        found_materials = []
        for keyword in self.material_keywords:
            if keyword in content:
                found_materials.append(keyword)
        report.materials = ", ".join(found_materials[:5])  # 限制为前5个
        
        # 提取事故原因
        found_causes = []
        for keyword in self.cause_keywords:
            if keyword in content:
                found_causes.append(keyword)
        report.cause = ", ".join(found_causes[:3])  # 限制为前3个
        
        # 提取后果
        found_consequences = []
        for keyword in self.consequence_keywords:
            if keyword in content:
                found_consequences.append(keyword)
        report.consequences = ", ".join(found_consequences[:5])  # 限制为前5个
        
        # 简单的严重程度评估
        if any(kw in content for kw in ['死亡', '爆炸', '重大']):
            report.severity = "严重"
        elif any(kw in content for kw in ['受伤', '泄漏', '火灾']):
            report.severity = "中等"
        else:
            report.severity = "轻微"
        
        return report
    
    def is_relevant_content(self, content: str) -> bool:
        """判断内容是否与危险品事故相关"""
        # 必须包含的关键词组合
        required_combinations = [
            ['危险品', '事故'],
            ['化学品', '事故'],
            ['罐车', '事故'],
            ['液化气', '爆炸'],
            ['化工', '泄漏'],
            ['运输', '危险品', '事故']
        ]
        
        content_lower = content.lower()
        
        for combination in required_combinations:
            if all(keyword in content for keyword in combination):
                return True
        
        return False


class HazmatAccidentCollector:
    """危险品事故收集器主类"""
    
    def __init__(self, 
                 output_dir: str = "hazmat_reports", 
                 proxy_list: List[str] = None,
                 min_delay: float = 1.0,
                 max_delay: float = 3.0):
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 初始化组件
        self.proxy_rotator = ProxyRotator(proxy_list)
        self.rate_limiter = RateLimiter(min_delay, max_delay)
        self.robots_checker = RobotsChecker()
        self.web_scraper = WebScraper(self.proxy_rotator, self.rate_limiter, self.robots_checker)
        self.data_extractor = AccidentDataExtractor()
        
        # 初始化搜索引擎
        self.search_engines = {
            'duckduckgo': DuckDuckGoSearchEngine(self.web_scraper.session)
        }
        
        # 存储收集的报告
        self.reports: List[AccidentReport] = []
    
    def search_accident_reports(self, keywords: List[str], num_results_per_query: int = 10) -> List[Dict[str, str]]:
        """搜索事故报告"""
        all_results = []
        
        for keyword in keywords:
            logger.info(f"正在搜索关键词: {keyword}")
            
            # 使用多个搜索引擎
            for engine_name, engine in self.search_engines.items():
                try:
                    results = engine.search(keyword, num_results_per_query)
                    logger.info(f"从 {engine_name} 获得 {len(results)} 个结果")
                    all_results.extend(results)
                    
                    # 在搜索引擎请求之间添加延迟
                    time.sleep(random.uniform(2, 5))
                    
                except Exception as e:
                    logger.error(f"搜索引擎 {engine_name} 出错: {e}")
        
        # 去重
        unique_results = []
        seen_urls = set()
        for result in all_results:
            if result['url'] not in seen_urls:
                unique_results.append(result)
                seen_urls.add(result['url'])
        
        logger.info(f"总共找到 {len(unique_results)} 个唯一结果")
        return unique_results
    
    def collect_reports(self, search_results: List[Dict[str, str]]) -> List[AccidentReport]:
        """收集事故报告"""
        reports = []
        
        for i, result in enumerate(search_results, 1):
            logger.info(f"正在处理第 {i}/{len(search_results)} 个结果: {result['title']}")
            
            try:
                # 抓取网页内容
                content = self.web_scraper.fetch_page_content(result['url'])
                if not content:
                    continue
                
                # 检查内容相关性
                if not self.data_extractor.is_relevant_content(content):
                    logger.info(f"内容不相关，跳过: {result['url']}")
                    continue
                
                # 提取事故信息
                report = self.data_extractor.extract_accident_info(
                    content, result['url'], result['title']
                )
                
                # 验证提取的信息质量
                if report.date or report.location or report.materials:
                    reports.append(report)
                    logger.info(f"成功提取事故信息: {report.title[:50]}...")
                else:
                    logger.info(f"提取的信息不完整，跳过: {result['url']}")
                
            except Exception as e:
                logger.error(f"处理结果时出错 {result['url']}: {e}")
                continue
        
        return reports
    
    def filter_reports(self, reports: List[AccidentReport], 
                      date_range: Tuple[str, str] = None,
                      severity_filter: str = None,
                      material_filter: str = None) -> List[AccidentReport]:
        """过滤报告"""
        filtered = reports
        
        # 日期范围过滤
        if date_range:
            start_date, end_date = date_range
            # 这里简化处理，实际应该解析日期进行比较
            filtered = [r for r in filtered if start_date <= r.date <= end_date]
        
        # 严重程度过滤
        if severity_filter:
            filtered = [r for r in filtered if r.severity == severity_filter]
        
        # 材料类型过滤
        if material_filter:
            filtered = [r for r in filtered if material_filter in r.materials]
        
        logger.info(f"过滤后剩余 {len(filtered)} 个报告")
        return filtered
    
    def save_reports(self, reports: List[AccidentReport], enable_pdf: bool = True):
        """保存报告到多种格式"""
        if not reports:
            logger.warning("没有报告需要保存")
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存为CSV格式
        csv_file = self.output_dir / f"hazmat_accidents_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'date', 'location', 'materials', 'cause', 'consequences', 
                'measures', 'source_url', 'title', 'severity', 'scraped_at'
            ])
            writer.writeheader()
            for report in reports:
                writer.writerow({
                    'date': report.date,
                    'location': report.location,
                    'materials': report.materials,
                    'cause': report.cause,
                    'consequences': report.consequences,
                    'measures': report.measures,
                    'source_url': report.source_url,
                    'title': report.title,
                    'severity': report.severity,
                    'scraped_at': report.scraped_at
                })
        
        logger.info(f"CSV报告已保存到: {csv_file}")
        
        # 保存为JSON格式
        json_file = self.output_dir / f"hazmat_accidents_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(report) for report in reports], f, 
                     ensure_ascii=False, indent=2)
        
        logger.info(f"JSON报告已保存到: {json_file}")
        
        # 保存为结构化文本格式
        txt_file = self.output_dir / f"hazmat_accidents_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("危险品罐车事故报告汇总\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"报告总数: {len(reports)}\n\n")
            
            for i, report in enumerate(reports, 1):
                f.write(f"报告 #{i}\n")
                f.write("-" * 30 + "\n")
                f.write(f"标题: {report.title}\n")
                f.write(f"日期: {report.date}\n")
                f.write(f"地点: {report.location}\n")
                f.write(f"涉及材料: {report.materials}\n")
                f.write(f"事故原因: {report.cause}\n")
                f.write(f"后果: {report.consequences}\n")
                f.write(f"严重程度: {report.severity}\n")
                f.write(f"信息来源: {report.source_url}\n")
                f.write(f"抓取时间: {report.scraped_at}\n\n")
        
        logger.info(f"文本报告已保存到: {txt_file}")
        
        # 保存为PDF格式（如果启用且可用）
        if enable_pdf:
            try:
                from pdf_exporter import PDFExporter
                pdf_file = self.output_dir / f"hazmat_accidents_{timestamp}.pdf"
                pdf_exporter = PDFExporter()
                pdf_exporter.create_pdf_report(reports, str(pdf_file))
                logger.info(f"PDF报告已保存到: {pdf_file}")
            except ImportError:
                logger.warning("PDF功能需要安装reportlab库: pip install reportlab")
            except Exception as e:
                logger.error(f"生成PDF时出错: {e}")
    
    def run(self, keywords: List[str], **kwargs):
        """运行收集器"""
        logger.info("开始危险品事故报告收集...")
        
        # 搜索阶段
        search_results = self.search_accident_reports(keywords, 
                                                    kwargs.get('num_results_per_query', 10))
        
        if not search_results:
            logger.warning("没有找到相关搜索结果")
            return
        
        # 收集阶段
        reports = self.collect_reports(search_results)
        
        if not reports:
            logger.warning("没有成功提取到事故报告")
            return
        
        # 过滤阶段
        filtered_reports = self.filter_reports(
            reports,
            date_range=kwargs.get('date_range'),
            severity_filter=kwargs.get('severity_filter'),
            material_filter=kwargs.get('material_filter')
        )
        
        # 保存阶段
        self.save_reports(filtered_reports, enable_pdf=not kwargs.get('no_pdf', False))
        
        logger.info(f"收集完成！共收集 {len(filtered_reports)} 份有效报告")
        return filtered_reports


def create_cli():
    """创建命令行界面"""
    parser = argparse.ArgumentParser(
        description="危险品罐车事故报告收集器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本使用
  python collector.py --keywords "危险品罐车事故" "化学品泄漏事故"
  
  # 指定输出目录和结果数量
  python collector.py --keywords "危险品运输事故" --output-dir reports --num-results 20
  
  # 使用代理和自定义延迟
  python collector.py --keywords "化学品事故" --proxy-list proxy1.txt --min-delay 2 --max-delay 5
  
  # 过滤特定严重程度
  python collector.py --keywords "危险品事故" --severity-filter 严重
        """
    )
    
    # 基本参数
    parser.add_argument('--keywords', nargs='+', 
                       default=["危险品罐车事故", "化学品泄漏事故", "危险品运输事故"],
                       help='搜索关键词列表 (默认: 危险品罐车事故 化学品泄漏事故 危险品运输事故)')
    
    parser.add_argument('--output-dir', default='hazmat_reports',
                       help='输出目录 (默认: hazmat_reports)')
    
    parser.add_argument('--num-results', type=int, default=10,
                       help='每个关键词的搜索结果数量 (默认: 10)')
    
    # 代理和速率限制
    parser.add_argument('--proxy-list',
                       help='代理列表文件路径 (每行一个代理)')
    
    parser.add_argument('--min-delay', type=float, default=1.0,
                       help='最小请求间隔 (秒, 默认: 1.0)')
    
    parser.add_argument('--max-delay', type=float, default=3.0,
                       help='最大请求间隔 (秒, 默认: 3.0)')
    
    # 过滤参数
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'),
                       help='日期范围过滤 (格式: YYYY-MM-DD YYYY-MM-DD)')
    
    parser.add_argument('--severity-filter', choices=['轻微', '中等', '严重'],
                       help='按严重程度过滤')
    
    parser.add_argument('--material-filter',
                       help='按材料类型过滤 (如: 汽油, 液化气)')
    
    # 调试参数
    parser.add_argument('--verbose', action='store_true',
                       help='详细输出')
    
    parser.add_argument('--log-file', default='hazmat_collector.log',
                       help='日志文件路径 (默认: hazmat_collector.log)')
    
    parser.add_argument('--no-pdf', action='store_true',
                       help='禁用PDF输出 (默认: 启用PDF)')
    
    return parser


def load_proxy_list(proxy_file: str) -> List[str]:
    """从文件加载代理列表"""
    try:
        with open(proxy_file, 'r', encoding='utf-8') as f:
            proxies = [line.strip() for line in f if line.strip()]
        logger.info(f"加载了 {len(proxies)} 个代理")
        return proxies
    except Exception as e:
        logger.error(f"加载代理列表失败: {e}")
        return []


def main():
    """主函数"""
    parser = create_cli()
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 加载代理列表
    proxy_list = None
    if args.proxy_list:
        proxy_list = load_proxy_list(args.proxy_list)
    
    # 创建收集器
    collector = HazmatAccidentCollector(
        output_dir=args.output_dir,
        proxy_list=proxy_list,
        min_delay=args.min_delay,
        max_delay=args.max_delay
    )
    
    # 准备过滤参数
    filter_kwargs = {}
    if args.date_range:
        filter_kwargs['date_range'] = tuple(args.date_range)
    if args.severity_filter:
        filter_kwargs['severity_filter'] = args.severity_filter
    if args.material_filter:
        filter_kwargs['material_filter'] = args.material_filter
    
    try:
        # 运行收集器
        collector.run(
            keywords=args.keywords,
            num_results_per_query=args.num_results,
            no_pdf=args.no_pdf,
            **filter_kwargs
        )
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.error(f"运行过程中出现错误: {e}")
        raise


if __name__ == "__main__":
    main()
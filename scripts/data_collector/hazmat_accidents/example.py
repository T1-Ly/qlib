#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危险品事故收集器示例脚本
Example script for the hazmat accident collector
"""

import sys
import os
from pathlib import Path

# 添加collector模块到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from collector import HazmatAccidentCollector, AccidentReport, AccidentDataExtractor

def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建收集器实例
    collector = HazmatAccidentCollector(
        output_dir="example_reports",
        min_delay=0.5,  # 示例中使用较短延迟
        max_delay=1.0
    )
    
    # 使用少量关键词进行测试
    test_keywords = ["危险品事故", "化学品泄漏"]
    
    print(f"搜索关键词: {test_keywords}")
    
    try:
        # 运行收集器
        reports = collector.run(
            keywords=test_keywords,
            num_results_per_query=3  # 少量结果用于测试
        )
        
        if reports:
            print(f"成功收集 {len(reports)} 份报告")
            for i, report in enumerate(reports[:2], 1):  # 显示前2个
                print(f"\n报告 {i}:")
                print(f"  标题: {report.title[:50]}...")
                print(f"  日期: {report.date}")
                print(f"  地点: {report.location}")
                print(f"  材料: {report.materials}")
                print(f"  严重程度: {report.severity}")
        else:
            print("没有收集到报告")
            
    except Exception as e:
        print(f"运行出错: {e}")


def example_data_extraction():
    """数据提取示例"""
    print("\n=== 数据提取示例 ===")
    
    # 创建数据提取器
    extractor = AccidentDataExtractor()
    
    # 模拟的事故报告内容
    sample_content = """
    2023年3月15日，在山东省济南市历下区某化工园区发生一起危险品运输事故。
    一辆运输液化气的罐车在行驶过程中发生侧翻，导致部分液化气泄漏。
    事故原因初步调查为车辆超速行驶，路面湿滑导致车辆失控。
    事故造成2人轻伤，无人员死亡。当地消防部门立即展开应急处置，
    疏散了周边居民约500人，封锁了事故路段3小时。
    环保部门监测显示，此次泄漏未对周边环境造成明显污染。
    """
    
    # 提取事故信息
    report = extractor.extract_accident_info(
        content=sample_content,
        url="http://example.com/news/123",
        title="济南化工园区液化气罐车侧翻事故"
    )
    
    print("提取的事故信息:")
    print(f"  日期: {report.date}")
    print(f"  地点: {report.location}")
    print(f"  材料: {report.materials}")
    print(f"  原因: {report.cause}")
    print(f"  后果: {report.consequences}")
    print(f"  严重程度: {report.severity}")
    
    # 测试相关性检查
    is_relevant = extractor.is_relevant_content(sample_content)
    print(f"  内容相关性: {'相关' if is_relevant else '不相关'}")


def example_with_filters():
    """过滤功能示例"""
    print("\n=== 过滤功能示例 ===")
    
    # 创建一些示例报告
    reports = [
        AccidentReport(
            date="2023-01-15",
            location="北京市",
            materials="汽油",
            severity="严重",
            title="北京汽油罐车爆炸事故"
        ),
        AccidentReport(
            date="2023-02-20", 
            location="上海市",
            materials="液化气",
            severity="中等",
            title="上海液化气泄漏事故"
        ),
        AccidentReport(
            date="2023-03-10",
            location="广州市", 
            materials="柴油",
            severity="轻微",
            title="广州柴油罐车追尾事故"
        )
    ]
    
    collector = HazmatAccidentCollector()
    
    print(f"原始报告数量: {len(reports)}")
    
    # 按严重程度过滤
    serious_reports = collector.filter_reports(reports, severity_filter="严重")
    print(f"严重事故数量: {len(serious_reports)}")
    
    # 按材料类型过滤
    gas_reports = collector.filter_reports(reports, material_filter="汽油")
    print(f"汽油相关事故: {len(gas_reports)}")
    
    # 按日期范围过滤
    feb_reports = collector.filter_reports(reports, date_range=("2023-02-01", "2023-02-28"))
    print(f"2月份事故: {len(feb_reports)}")


def example_cli_usage():
    """命令行使用示例"""
    print("\n=== 命令行使用示例 ===")
    
    examples = [
        "# 基本使用",
        "python collector.py",
        "",
        "# 自定义关键词",
        'python collector.py --keywords "危险品罐车事故" "化学品泄漏事故"',
        "",
        "# 指定输出目录和结果数量",
        "python collector.py --output-dir my_reports --num-results 20",
        "",
        "# 使用代理和自定义延迟", 
        "python collector.py --proxy-list proxies.txt --min-delay 2 --max-delay 5",
        "",
        "# 过滤功能",
        'python collector.py --severity-filter 严重 --material-filter 汽油',
        "",
        "# 详细输出",
        "python collector.py --verbose"
    ]
    
    for example in examples:
        print(example)


def main():
    """运行所有示例"""
    print("危险品事故收集器 - 使用示例")
    print("=" * 50)
    
    # 运行示例
    example_data_extraction()
    example_with_filters() 
    example_cli_usage()
    
    # 注意：基本使用示例需要网络连接，在demo中跳过
    print("\n注意：要运行完整的网络收集示例，请执行：")
    print("python example.py --run-network-demo")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--run-network-demo":
        example_basic_usage()


if __name__ == "__main__":
    main()
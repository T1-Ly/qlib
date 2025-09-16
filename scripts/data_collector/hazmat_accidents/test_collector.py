#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危险品事故收集器测试脚本
Test script for the hazmat accident collector
"""

import sys
import tempfile
from pathlib import Path

# 添加collector模块到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from collector import (
    AccidentReport, 
    AccidentDataExtractor, 
    ProxyRotator,
    RateLimiter,
    RobotsChecker,
    HazmatAccidentCollector
)

def test_accident_report():
    """测试事故报告数据结构"""
    print("测试 AccidentReport...")
    
    report = AccidentReport(
        date="2023-03-15",
        location="山东省济南市",
        materials="液化气, 汽油",
        cause="超速, 侧翻",
        consequences="泄漏, 疏散",
        severity="严重",
        title="测试事故报告"
    )
    
    assert report.date == "2023-03-15"
    assert report.location == "山东省济南市"
    assert "液化气" in report.materials
    assert report.severity == "严重"
    print("✓ AccidentReport 测试通过")


def test_proxy_rotator():
    """测试代理轮换器"""
    print("测试 ProxyRotator...")
    
    # 测试无代理情况
    rotator = ProxyRotator()
    assert rotator.get_proxy() is None
    
    # 测试有代理情况
    proxy_list = ["http://proxy1:8080", "http://proxy2:8080"]
    rotator = ProxyRotator(proxy_list)
    
    proxy1 = rotator.get_proxy()
    proxy2 = rotator.get_proxy()
    proxy3 = rotator.get_proxy()  # 应该回到第一个
    
    assert proxy1['http'] == "http://proxy1:8080"
    assert proxy2['http'] == "http://proxy2:8080"
    assert proxy3['http'] == "http://proxy1:8080"  # 轮换
    print("✓ ProxyRotator 测试通过")


def test_rate_limiter():
    """测试速率限制器"""
    print("测试 RateLimiter...")
    
    import time
    
    limiter = RateLimiter(min_delay=0.1, max_delay=0.2)
    
    start_time = time.time()
    limiter.wait()
    limiter.wait()
    end_time = time.time()
    
    # 第二次调用应该有延迟
    elapsed = end_time - start_time
    assert elapsed >= 0.1  # 至少有最小延迟
    print("✓ RateLimiter 测试通过")


def test_data_extractor():
    """测试数据提取器"""
    print("测试 AccidentDataExtractor...")
    
    extractor = AccidentDataExtractor()
    
    # 测试样本内容
    sample_content = """
    2023年3月15日，在山东省济南市历下区发生危险品运输事故。
    一辆运输液化气的罐车发生侧翻，导致液化气泄漏。
    事故原因为车辆超速行驶。事故造成2人受伤，周边居民被疏散。
    """
    
    report = extractor.extract_accident_info(
        content=sample_content,
        url="http://test.com",
        title="测试事故"
    )
    
    # 验证提取结果
    assert "2023年3月15日" in report.date
    assert "山东省济南市" in report.location  
    assert "液化气" in report.materials
    assert "超速" in report.cause
    assert "受伤" in report.consequences
    assert report.severity in ["轻微", "中等", "严重"]
    
    # 测试相关性检查
    assert extractor.is_relevant_content(sample_content) == True
    
    # 测试不相关内容
    irrelevant_content = "今天天气很好，适合出行。"
    assert extractor.is_relevant_content(irrelevant_content) == False
    
    print("✓ AccidentDataExtractor 测试通过")


def test_collector_filtering():
    """测试收集器过滤功能"""
    print("测试 HazmatAccidentCollector 过滤功能...")
    
    collector = HazmatAccidentCollector()
    
    # 创建测试报告
    reports = [
        AccidentReport(
            date="2023-01-15",
            location="北京市",
            materials="汽油",
            severity="严重"
        ),
        AccidentReport(
            date="2023-02-20",
            location="上海市", 
            materials="液化气",
            severity="中等"
        ),
        AccidentReport(
            date="2023-03-10",
            location="广州市",
            materials="柴油",
            severity="轻微"
        )
    ]
    
    # 测试严重程度过滤
    serious_reports = collector.filter_reports(reports, severity_filter="严重")
    assert len(serious_reports) == 1
    assert serious_reports[0].severity == "严重"
    
    # 测试材料过滤
    gas_reports = collector.filter_reports(reports, material_filter="汽油")
    assert len(gas_reports) == 1
    assert "汽油" in gas_reports[0].materials
    
    print("✓ HazmatAccidentCollector 过滤功能测试通过")


def test_output_saving():
    """测试输出保存功能"""
    print("测试输出保存功能...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        collector = HazmatAccidentCollector(output_dir=temp_dir)
        
        # 创建测试报告
        reports = [
            AccidentReport(
                date="2023-01-15",
                location="北京市",
                materials="汽油",
                cause="追尾",
                consequences="火灾",
                severity="严重",
                title="测试报告1",
                source_url="http://test1.com",
                scraped_at="2023-01-15 10:00:00"
            )
        ]
        
        # 保存报告 (禁用PDF以避免依赖问题)
        collector.save_reports(reports, enable_pdf=False)
        
        # 检查文件是否生成
        output_path = Path(temp_dir)
        csv_files = list(output_path.glob("*.csv"))
        json_files = list(output_path.glob("*.json"))
        txt_files = list(output_path.glob("*.txt"))
        
        assert len(csv_files) == 1
        assert len(json_files) == 1
        assert len(txt_files) == 1
        
        # 检查CSV内容
        import csv
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]['location'] == "北京市"
            assert rows[0]['materials'] == "汽油"
        
        print("✓ 输出保存功能测试通过")


def run_all_tests():
    """运行所有测试"""
    print("开始运行危险品事故收集器测试...")
    print("=" * 50)
    
    try:
        test_accident_report()
        test_proxy_rotator()
        test_rate_limiter()
        test_data_extractor()
        test_collector_filtering()
        test_output_saving()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
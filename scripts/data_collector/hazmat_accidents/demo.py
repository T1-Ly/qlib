#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危险品事故收集器完整演示
Complete demonstration of the hazmat accident collector

这个演示脚本展示了危险品事故收集器的所有功能，包括：
1. 搜索引擎集成
2. 数据提取和过滤
3. 多格式输出
4. 代理轮换和速率限制
5. 错误处理

This demonstration script shows all features of the hazmat collector.
"""

import sys
import json
import tempfile
from pathlib import Path
from typing import List

# 添加collector模块到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from collector import HazmatAccidentCollector, AccidentReport

def demo_comprehensive_usage():
    """完整功能演示"""
    print("=" * 60)
    print("危险品事故收集器 - 完整功能演示")
    print("=" * 60)
    
    # 创建临时输出目录
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"输出目录: {temp_dir}")
        
        # 配置收集器
        collector = HazmatAccidentCollector(
            output_dir=temp_dir,
            min_delay=0.1,  # 演示用较短延迟
            max_delay=0.2
        )
        
        print("\n1. 创建演示数据...")
        # 创建一些演示数据来展示功能
        demo_reports = create_demo_reports()
        
        print(f"创建了 {len(demo_reports)} 个演示报告")
        
        print("\n2. 测试过滤功能...")
        demonstrate_filtering(collector, demo_reports)
        
        print("\n3. 测试输出功能...")
        demonstrate_output_formats(collector, demo_reports, temp_dir)
        
        print("\n4. 展示统计信息...")
        demonstrate_statistics(demo_reports)


def create_demo_reports() -> List[AccidentReport]:
    """创建演示报告"""
    return [
        AccidentReport(
            date="2023年3月15日",
            location="山东省济南市历下区化工园区",
            materials="液化气, 丙烷, 危险品",
            cause="侧翻, 超速, 路面湿滑",
            consequences="泄漏, 疏散, 封路",
            measures="消防处置, 人员疏散, 环境监测",
            severity="严重",
            title="济南化工园区液化气罐车侧翻重大事故",
            source_url="http://example.com/news/incident-001",
            content="2023年3月15日凌晨2时许，济南市历下区某化工园区内发生一起液化气罐车侧翻事故。事故车辆载有20吨液化石油气，侧翻后发生大量泄漏...",
            scraped_at="2023-03-16 08:30:00"
        ),
        AccidentReport(
            date="2023年2月20日",
            location="上海市浦东新区临港新城",
            materials="汽油, 易燃液体",
            cause="追尾, 制动失效",
            consequences="火灾, 爆炸, 死亡",
            measures="灭火救援, 医疗救护, 道路封闭",
            severity="严重",
            title="上海临港汽油罐车追尾爆炸特大事故",
            source_url="http://example.com/news/incident-002",
            content="上海浦东临港新城发生一起汽油罐车与货车追尾事故，引发爆炸和火灾，造成重大人员伤亡...",
            scraped_at="2023-02-21 10:15:00"
        ),
        AccidentReport(
            date="2023年1月10日",
            location="广东省深圳市龙岗区",
            materials="柴油",
            cause="疲劳驾驶",
            consequences="轻微泄漏",
            measures="现场清理, 交通疏导",
            severity="轻微",
            title="深圳龙岗柴油罐车单方事故",
            source_url="http://example.com/news/incident-003",
            content="深圳龙岗区一柴油罐车因驾驶员疲劳驾驶冲出路面，造成少量柴油泄漏...",
            scraped_at="2023-01-11 14:20:00"
        ),
        AccidentReport(
            date="2023年4月05日",
            location="江苏省南京市江宁区",
            materials="硫酸, 腐蚀性物质",
            cause="违章超车, 设备故障",
            consequences="泄漏, 污染, 中毒",
            measures="专业处置, 环境治理, 医疗救治",
            severity="中等",
            title="南京江宁硫酸罐车泄漏环境污染事故",
            source_url="http://example.com/news/incident-004",
            content="江苏南京江宁区发生硫酸罐车泄漏事故，造成土壤和水源污染，多人出现中毒症状...",
            scraped_at="2023-04-06 09:45:00"
        ),
        AccidentReport(
            date="2023年5月12日",
            location="四川省成都市双流区",
            materials="液氨, 有毒物质",
            cause="阀门失效, 密封不良",
            consequences="泄漏, 疏散",
            measures="堵漏处置, 人员疏散, 医疗观察",
            severity="中等",
            title="成都双流液氨罐车泄漏事故",
            source_url="http://example.com/news/incident-005",
            content="成都双流区一液氨运输车辆发生泄漏，现场有刺激性气味，周边居民紧急疏散...",
            scraped_at="2023-05-13 16:30:00"
        )
    ]


def demonstrate_filtering(collector: HazmatAccidentCollector, reports: List[AccidentReport]):
    """演示过滤功能"""
    print("原始报告数量:", len(reports))
    
    # 按严重程度过滤
    severe_reports = collector.filter_reports(reports, severity_filter="严重")
    print(f"严重事故: {len(severe_reports)} 起")
    
    medium_reports = collector.filter_reports(reports, severity_filter="中等")
    print(f"中等事故: {len(medium_reports)} 起")
    
    mild_reports = collector.filter_reports(reports, severity_filter="轻微")
    print(f"轻微事故: {len(mild_reports)} 起")
    
    # 按材料类型过滤
    liquid_gas_reports = collector.filter_reports(reports, material_filter="液化气")
    print(f"涉及液化气事故: {len(liquid_gas_reports)} 起")
    
    gasoline_reports = collector.filter_reports(reports, material_filter="汽油")
    print(f"涉及汽油事故: {len(gasoline_reports)} 起")
    
    # 按日期范围过滤
    q1_reports = collector.filter_reports(reports, date_range=("2023-01-01", "2023-03-31"))
    print(f"第一季度事故: {len(q1_reports)} 起")


def demonstrate_output_formats(collector: HazmatAccidentCollector, reports: List[AccidentReport], output_dir: str):
    """演示输出格式"""
    # 保存所有格式
    collector.save_reports(reports, enable_pdf=False)  # 禁用PDF避免依赖问题
    
    # 检查生成的文件
    output_path = Path(output_dir)
    csv_files = list(output_path.glob("*.csv"))
    json_files = list(output_path.glob("*.json"))
    txt_files = list(output_path.glob("*.txt"))
    
    print(f"生成文件:")
    print(f"  CSV文件: {len(csv_files)} 个")
    print(f"  JSON文件: {len(json_files)} 个")
    print(f"  文本文件: {len(txt_files)} 个")
    
    # 显示JSON内容预览
    if json_files:
        with open(json_files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"\nJSON文件预览 (前1个记录):")
            print(json.dumps(data[0], ensure_ascii=False, indent=2)[:300] + "...")


def demonstrate_statistics(reports: List[AccidentReport]):
    """演示统计信息"""
    print("事故统计分析:")
    
    # 按严重程度统计
    severity_stats = {}
    for report in reports:
        severity = report.severity or "未知"
        severity_stats[severity] = severity_stats.get(severity, 0) + 1
    
    print("\n严重程度分布:")
    for severity, count in severity_stats.items():
        percentage = count / len(reports) * 100
        print(f"  {severity}: {count} 起 ({percentage:.1f}%)")
    
    # 按地区统计
    location_stats = {}
    for report in reports:
        if report.location:
            # 提取省份
            for province in ['山东省', '上海市', '广东省', '江苏省', '四川省']:
                if province in report.location:
                    location_stats[province] = location_stats.get(province, 0) + 1
                    break
    
    print("\n地区分布:")
    for location, count in sorted(location_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(reports) * 100
        print(f"  {location}: {count} 起 ({percentage:.1f}%)")
    
    # 按材料类型统计
    material_stats = {}
    for report in reports:
        if report.materials:
            materials = [m.strip() for m in report.materials.split(',')]
            for material in materials:
                if material and material != "危险品":  # 排除通用词
                    material_stats[material] = material_stats.get(material, 0) + 1
    
    print("\n涉及材料统计:")
    for material, count in sorted(material_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(reports) * 100
        print(f"  {material}: {count} 起 ({percentage:.1f}%)")


def demo_cli_examples():
    """演示命令行使用示例"""
    print("\n" + "=" * 60)
    print("命令行使用示例")
    print("=" * 60)
    
    examples = [
        ("基本搜索", 'python collector.py'),
        ("自定义关键词", 'python collector.py --keywords "危险品罐车事故" "化学品泄漏"'),
        ("指定输出目录", 'python collector.py --output-dir ./reports --num-results 20'),
        ("使用代理", 'python collector.py --proxy-list proxies.txt --min-delay 2'),
        ("按严重程度过滤", 'python collector.py --severity-filter 严重'),
        ("按材料过滤", 'python collector.py --material-filter 汽油'),
        ("按日期过滤", 'python collector.py --date-range 2023-01-01 2023-12-31'),
        ("详细输出", 'python collector.py --verbose'),
        ("禁用PDF", 'python collector.py --no-pdf'),
    ]
    
    for desc, cmd in examples:
        print(f"\n{desc}:")
        print(f"  {cmd}")


def demo_best_practices():
    """演示最佳实践"""
    print("\n" + "=" * 60)
    print("爬虫最佳实践指南")
    print("=" * 60)
    
    practices = [
        "✓ 遵守robots.txt规则",
        "✓ 使用真实浏览器User-Agent",
        "✓ 实现请求间随机延迟",
        "✓ 处理网络错误和重试",
        "✓ 尊重网站服务条款",
        "✓ 避免过度频繁请求",
        "✓ 使用代理轮换（如需要）",
        "✓ 记录详细日志便于调试",
        "✓ 验证提取数据的准确性",
        "✓ 合理使用抓取的数据"
    ]
    
    for practice in practices:
        print(f"  {practice}")
    
    print("\n注意事项:")
    print("  • 本工具仅用于合法研究和分析目的")
    print("  • 使用前请了解目标网站的服务条款")
    print("  • 遵守当地法律法规和数据保护规定")
    print("  • 合理控制爬取频率，避免对服务器造成压力")


def main():
    """主演示函数"""
    try:
        # 运行完整演示
        demo_comprehensive_usage()
        
        # 显示CLI示例
        demo_cli_examples()
        
        # 显示最佳实践
        demo_best_practices()
        
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        print("要运行实际的网络收集，请使用:")
        print("  python collector.py --keywords \"危险品事故\" --num-results 5 --verbose")
        
    except Exception as e:
        print(f"演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
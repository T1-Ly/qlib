#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF导出器
PDF Exporter for hazmat accident reports
"""

import os
from pathlib import Path
from typing import List
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

try:
    from collector import AccidentReport
except ImportError:
    # 如果无法导入，创建简单的数据类
    from dataclasses import dataclass
    @dataclass
    class AccidentReport:
        date: str = ""
        location: str = ""
        materials: str = ""
        cause: str = ""
        consequences: str = ""
        measures: str = ""
        source_url: str = ""
        title: str = ""
        content: str = ""
        severity: str = ""
        scraped_at: str = ""


class PDFExporter:
    """PDF导出器"""
    
    def __init__(self):
        # 尝试注册中文字体
        self.setup_chinese_fonts()
        
        # 创建样式
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_chinese_fonts(self):
        """设置中文字体"""
        try:
            # 尝试使用系统中文字体
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',  # macOS
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
                'C:/Windows/Fonts/simhei.ttf',  # Windows
                'C:/Windows/Fonts/simsun.ttc',  # Windows
            ]
            
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Chinese', font_path))
                        font_registered = True
                        break
                    except:
                        continue
            
            if not font_registered:
                # 如果没有找到中文字体，使用默认字体
                print("警告：未找到中文字体，将使用默认字体")
                
        except Exception as e:
            print(f"字体设置警告: {e}")
    
    def setup_custom_styles(self):
        """设置自定义样式"""
        # 标题样式
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # 居中
            textColor=colors.darkblue
        )
        
        # 章节标题样式
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.darkred
        )
        
        # 正文样式
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=20
        )
        
        # 摘要样式
        self.summary_style = ParagraphStyle(
            'Summary',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            leftIndent=10,
            textColor=colors.darkgreen
        )
    
    def create_pdf_report(self, reports: List[AccidentReport], output_file: str):
        """创建PDF报告"""
        doc = SimpleDocTemplate(
            output_file,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # 构建文档内容
        story = []
        
        # 添加标题页
        story.extend(self._create_title_page(reports))
        
        # 添加摘要统计
        story.extend(self._create_summary_section(reports))
        
        # 添加详细报告
        story.extend(self._create_detailed_reports(reports))
        
        # 构建PDF
        doc.build(story)
        print(f"PDF报告已生成: {output_file}")
    
    def _create_title_page(self, reports: List[AccidentReport]) -> List:
        """创建标题页"""
        story = []
        
        # 主标题
        title = Paragraph("危险品罐车事故报告汇总", self.title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # 生成信息
        import datetime
        now = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        
        info_text = f"""
        <b>报告生成时间:</b> {now}<br/>
        <b>报告总数:</b> {len(reports)}份<br/>
        <b>报告类型:</b> 危险品运输事故分析报告<br/>
        <b>数据来源:</b> 网络公开信息
        """
        
        info = Paragraph(info_text, self.summary_style)
        story.append(info)
        story.append(Spacer(1, 40))
        
        return story
    
    def _create_summary_section(self, reports: List[AccidentReport]) -> List:
        """创建摘要统计章节"""
        story = []
        
        # 章节标题
        heading = Paragraph("摘要统计", self.heading_style)
        story.append(heading)
        
        # 统计信息
        stats = self._calculate_statistics(reports)
        
        # 创建统计表格
        table_data = [
            ['统计项目', '数量', '占比'],
            ['总事故数', str(len(reports)), '100%'],
            ['严重事故', str(stats['severe_count']), f"{stats['severe_ratio']:.1f}%"],
            ['中等事故', str(stats['medium_count']), f"{stats['medium_ratio']:.1f}%"],
            ['轻微事故', str(stats['mild_count']), f"{stats['mild_ratio']:.1f}%"],
        ]
        
        # 添加材料统计
        for material, count in stats['top_materials'][:5]:
            table_data.append([f'涉及{material}', str(count), f"{count/len(reports)*100:.1f}%"])
        
        table = Table(table_data, colWidths=[2*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_detailed_reports(self, reports: List[AccidentReport]) -> List:
        """创建详细报告章节"""
        story = []
        
        # 章节标题
        heading = Paragraph("详细事故报告", self.heading_style)
        story.append(heading)
        story.append(Spacer(1, 12))
        
        for i, report in enumerate(reports, 1):
            # 事故标题
            report_title = Paragraph(f"事故报告 #{i}: {report.title}", 
                                   self.heading_style)
            story.append(report_title)
            
            # 事故详情表格
            detail_data = [
                ['事故日期', report.date or '未知'],
                ['事故地点', report.location or '未知'],
                ['涉及材料', report.materials or '未知'],
                ['事故原因', report.cause or '未知'],
                ['事故后果', report.consequences or '未知'],
                ['严重程度', report.severity or '未知'],
                ['信息来源', report.source_url or '未知'],
                ['抓取时间', report.scraped_at or '未知'],
            ]
            
            detail_table = Table(detail_data, colWidths=[1.5*inch, 4*inch])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            story.append(detail_table)
            
            # 添加内容摘要（如果有）
            if report.content and len(report.content.strip()) > 0:
                content_text = f"<b>内容摘要:</b><br/>{report.content[:200]}..."
                content_para = Paragraph(content_text, self.body_style)
                story.append(Spacer(1, 6))
                story.append(content_para)
            
            story.append(Spacer(1, 20))
        
        return story
    
    def _calculate_statistics(self, reports: List[AccidentReport]) -> dict:
        """计算统计信息"""
        total = len(reports)
        if total == 0:
            return {
                'severe_count': 0, 'severe_ratio': 0,
                'medium_count': 0, 'medium_ratio': 0,
                'mild_count': 0, 'mild_ratio': 0,
                'top_materials': []
            }
        
        # 按严重程度统计
        severe_count = sum(1 for r in reports if r.severity == '严重')
        medium_count = sum(1 for r in reports if r.severity == '中等')
        mild_count = sum(1 for r in reports if r.severity == '轻微')
        
        # 材料统计
        material_counts = {}
        for report in reports:
            if report.materials:
                materials = [m.strip() for m in report.materials.split(',')]
                for material in materials:
                    if material:
                        material_counts[material] = material_counts.get(material, 0) + 1
        
        top_materials = sorted(material_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'severe_count': severe_count,
            'severe_ratio': severe_count / total * 100,
            'medium_count': medium_count,
            'medium_ratio': medium_count / total * 100,
            'mild_count': mild_count,
            'mild_ratio': mild_count / total * 100,
            'top_materials': top_materials
        }


def create_sample_pdf():
    """创建示例PDF"""
    # 创建一些示例数据
    sample_reports = [
        AccidentReport(
            date="2023年3月15日",
            location="山东省济南市历下区",
            materials="液化气, 丙烷",
            cause="侧翻, 超速",
            consequences="泄漏, 疏散",
            severity="严重",
            title="济南液化气罐车侧翻事故",
            source_url="http://example.com/news/1",
            content="2023年3月15日，济南市发生一起液化气罐车侧翻事故，导致液化气泄漏...",
            scraped_at="2023-03-16 10:30:00"
        ),
        AccidentReport(
            date="2023年2月20日",
            location="上海市浦东新区",
            materials="汽油",
            cause="追尾",
            consequences="火灾",
            severity="中等",
            title="上海汽油罐车追尾起火事故",
            source_url="http://example.com/news/2",
            content="上海浦东发生汽油罐车追尾事故，引发火灾...",
            scraped_at="2023-02-21 08:15:00"
        ),
        AccidentReport(
            date="2023年1月10日",
            location="广东省深圳市",
            materials="柴油",
            cause="制动失效",
            consequences="轻微泄漏",
            severity="轻微",
            title="深圳柴油罐车制动失效事故",
            source_url="http://example.com/news/3",
            content="深圳一柴油罐车制动失效，造成轻微泄漏...",
            scraped_at="2023-01-11 14:20:00"
        )
    ]
    
    # 创建PDF
    exporter = PDFExporter()
    output_file = "sample_hazmat_report.pdf"
    exporter.create_pdf_report(sample_reports, output_file)
    print(f"示例PDF已生成: {output_file}")


if __name__ == "__main__":
    try:
        create_sample_pdf()
    except ImportError as e:
        print(f"PDF功能需要安装reportlab库: pip install reportlab")
        print(f"错误详情: {e}")
    except Exception as e:
        print(f"生成PDF时出错: {e}")
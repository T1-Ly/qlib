# 危险品事故收集器 - 使用指南

## 快速开始

### 1. 基本使用
```bash
# 使用默认关键词搜索
python collector.py

# 自定义关键词搜索
python collector.py --keywords "危险品罐车事故" "化学品泄漏事故"
```

### 2. 指定输出选项
```bash
# 指定输出目录和搜索数量
python collector.py --output-dir ./my_reports --num-results 20

# 禁用PDF输出（如果没有安装reportlab）
python collector.py --no-pdf
```

### 3. 使用过滤功能
```bash
# 按严重程度过滤
python collector.py --severity-filter 严重

# 按材料类型过滤  
python collector.py --material-filter 汽油

# 按日期范围过滤
python collector.py --date-range 2023-01-01 2023-12-31
```

### 4. 网络配置
```bash
# 使用代理轮换
python collector.py --proxy-list proxies.txt

# 自定义请求延迟
python collector.py --min-delay 2.0 --max-delay 5.0

# 详细输出用于调试
python collector.py --verbose
```

## 输出文件说明

运行后会在输出目录生成以下文件：

### CSV格式 (`hazmat_accidents_YYYYMMDD_HHMMSS.csv`)
- 适合Excel打开和数据分析
- 包含所有字段的结构化数据
- 便于导入数据库或分析工具

### JSON格式 (`hazmat_accidents_YYYYMMDD_HHMMSS.json`)
- 适合程序化处理
- 完整保留所有信息
- 便于与其他系统集成

### 文本格式 (`hazmat_accidents_YYYYMMDD_HHMMSS.txt`)
- 人类可读的报告格式
- 包含汇总统计信息
- 便于直接阅读和打印

### PDF格式 (`hazmat_accidents_YYYYMMDD_HHMMSS.pdf`)
- 专业报告格式（需要安装reportlab）
- 包含统计图表和详细信息
- 适合正式报告和存档

## 代理配置

创建代理列表文件 `proxies.txt`：
```
http://proxy1.example.com:8080
http://proxy2.example.com:8080
socks5://proxy3.example.com:1080
```

然后使用：
```bash
python collector.py --proxy-list proxies.txt
```

## 常见问题

### Q: 搜索结果为空怎么办？
A: 
1. 检查网络连接
2. 尝试不同的关键词
3. 查看日志文件了解详细错误信息
4. 考虑使用代理

### Q: 抓取失败怎么办？
A:
1. 检查目标网站是否可访问
2. 调整延迟参数 `--min-delay` 和 `--max-delay`
3. 使用 `--verbose` 查看详细错误信息
4. 检查robots.txt是否允许抓取

### Q: 如何提高数据质量？
A:
1. 使用更具体的关键词
2. 增加搜索结果数量 `--num-results`
3. 定期运行收集器获取最新数据
4. 手动验证重要事故信息

### Q: PDF生成失败怎么办？
A:
1. 安装PDF依赖：`pip install reportlab`
2. 或者使用 `--no-pdf` 禁用PDF输出
3. 检查系统是否有中文字体

## 数据字段说明

| 字段 | 描述 | 示例 |
|------|------|------|
| date | 事故发生日期 | 2023年3月15日 |
| location | 事故地点 | 山东省济南市 |
| materials | 涉及的危险品 | 液化气, 汽油 |
| cause | 事故原因 | 超速, 侧翻 |
| consequences | 事故后果 | 泄漏, 疏散 |
| measures | 应对措施 | 消防处置, 环境监测 |
| severity | 严重程度 | 严重/中等/轻微 |
| title | 报告标题 | 完整的新闻标题 |
| source_url | 信息来源 | 原始网页链接 |
| scraped_at | 抓取时间 | 2023-03-16 10:30:00 |

## 高级用法

### 组合过滤条件
```bash
# 查找2023年涉及汽油的严重事故
python collector.py \
  --date-range 2023-01-01 2023-12-31 \
  --material-filter 汽油 \
  --severity-filter 严重
```

### 大规模数据收集
```bash
# 使用更多关键词和结果进行大规模收集
python collector.py \
  --keywords "危险品事故" "化学品泄漏" "罐车事故" "运输事故" \
  --num-results 50 \
  --proxy-list proxies.txt \
  --min-delay 3 \
  --max-delay 8 \
  --verbose
```

### 定时任务设置
```bash
# 使用cron定时运行（每天凌晨2点）
# 0 2 * * * /usr/bin/python /path/to/collector.py --output-dir /var/reports
```

## 法律和道德指南

### ✅ 推荐做法
- 仅用于学术研究和安全分析
- 遵守网站服务条款
- 合理控制访问频率
- 尊重数据版权
- 保护个人隐私信息

### ❌ 禁止行为
- 商业牟利
- 恶意攻击网站
- 传播虚假信息
- 侵犯版权
- 违反法律法规

## 技术支持

### 查看详细日志
```bash
# 查看日志文件
tail -f hazmat_collector.log

# 实时详细输出
python collector.py --verbose
```

### 测试基本功能
```bash
# 运行内置测试
python test_collector.py

# 运行功能演示
python demo.py

# 查看使用示例
python example.py
```

### 性能优化建议
1. 使用SSD存储输出文件
2. 在网络状况良好时运行
3. 合理设置并发数（目前为单线程）
4. 定期清理日志文件
5. 使用高质量的代理服务

## 扩展开发

### 添加新搜索引擎
继承 `BaseSearchEngine` 类：
```python
class NewSearchEngine(BaseSearchEngine):
    def search(self, query: str, num_results: int = 10):
        # 实现搜索逻辑
        pass
```

### 自定义数据提取
修改 `AccidentDataExtractor` 类的模式：
```python
# 添加新的提取模式
self.custom_patterns = [
    r'新的正则表达式',
    # ...
]
```

### 集成到其他系统
```python
from hazmat_accidents import HazmatAccidentCollector

# 程序化使用
collector = HazmatAccidentCollector()
reports = collector.run(keywords=["事故关键词"])
```
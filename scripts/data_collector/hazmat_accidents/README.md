# 危险品罐车事故报告收集器

## 概述

这是一个专门用于收集危险品罐车事故报告的灵活Python脚本。与固定网站列表不同，该脚本使用搜索引擎API和网络爬虫技术来动态发现相关内容，提取关键信息，并以多种格式保存结果。

## 主要特性

### 🔍 动态内容发现
- 不依赖固定网站列表
- 使用搜索引擎API动态发现相关内容
- 支持多种搜索引擎（目前支持DuckDuckGo）
- 用户可输入自定义关键词进行搜索

### 📊 智能信息提取
- 自动提取事故发生日期和地点
- 识别涉及的危险品类型
- 分析事故原因（如果有）
- 记录后果（人员伤亡、环境影响）
- 收集采取的应对措施

### 💾 多格式输出
- **文本文件**：结构化数据，便于阅读
- **CSV格式**：便于数据分析和Excel处理
- **JSON格式**：便于程序化处理和API集成

### 🔧 高级功能
- **过滤功能**：按日期范围、严重程度或材料类型过滤报告
- **代理轮换**：避免IP被封，支持代理列表文件
- **速率限制**：实现随机延迟，尊重目标网站
- **robots.txt遵守**：自动检查并遵守robots.txt规则

### 🖥️ 用户友好界面
- 清晰的命令行界面
- 详细的使用说明和示例
- 进度指示器和实时状态更新
- 全中文输出信息

## 安装要求

```bash
# 基本依赖（大多数系统已包含）
- Python 3.7+
- requests
- urllib3

# 如果需要更好的HTML解析（可选）
pip install beautifulsoup4 lxml
```

## 快速开始

### 基本使用

```bash
# 使用默认关键词搜索
python collector.py

# 自定义关键词搜索
python collector.py --keywords "危险品罐车事故" "化学品泄漏事故" "液化气爆炸"

# 指定输出目录
python collector.py --output-dir /path/to/reports --num-results 20
```

### 高级使用

```bash
# 使用代理轮换
python collector.py --proxy-list proxies.txt --min-delay 2 --max-delay 5

# 按严重程度过滤
python collector.py --severity-filter 严重

# 按材料类型过滤
python collector.py --material-filter 汽油

# 按日期范围过滤
python collector.py --date-range 2023-01-01 2023-12-31

# 详细日志输出
python collector.py --verbose
```

## 配置文件

### 代理列表文件示例 (proxies.txt)
```
http://proxy1.example.com:8080
http://proxy2.example.com:8080
socks5://proxy3.example.com:1080
```

## 输出格式

### CSV格式字段
- `date`: 事故发生日期
- `location`: 事故地点  
- `materials`: 涉及的危险品类型
- `cause`: 事故原因
- `consequences`: 后果
- `measures`: 应对措施
- `source_url`: 信息来源URL
- `title`: 报告标题
- `severity`: 严重程度
- `scraped_at`: 抓取时间

### JSON格式
结构化JSON数组，包含所有字段的完整信息，便于程序化处理。

### 文本格式
人类可读的结构化文本报告，包含汇总统计和详细的事故信息。

## 最佳实践

### 爬虫道德规范
- 自动检查并遵守robots.txt规则
- 实现随机延迟避免过度请求
- 使用真实浏览器头信息
- 处理网络错误和重试机制

### 速率限制
- 默认请求间隔：1-3秒随机延迟
- 搜索引擎请求间隔：2-5秒
- 可通过参数自定义延迟范围

### 错误处理
- 网络超时和连接错误自动重试
- 页面解析错误优雅处理
- 详细的日志记录便于故障排除

## 扩展性

### 添加新搜索引擎
继承`BaseSearchEngine`类并实现`search`方法：

```python
class NewSearchEngine(BaseSearchEngine):
    def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        # 实现搜索逻辑
        pass
```

### 自定义数据提取
修改`AccidentDataExtractor`类中的模式和关键词：

```python
# 添加新的提取模式
self.custom_patterns = [
    r'(新的正则表达式模式)',
    # ...
]
```

## 命令行参数详解

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--keywords` | list | ["危险品罐车事故", "化学品泄漏事故", "危险品运输事故"] | 搜索关键词列表 |
| `--output-dir` | str | "hazmat_reports" | 输出目录路径 |
| `--num-results` | int | 10 | 每个关键词的搜索结果数量 |
| `--proxy-list` | str | None | 代理列表文件路径 |
| `--min-delay` | float | 1.0 | 最小请求间隔（秒） |
| `--max-delay` | float | 3.0 | 最大请求间隔（秒） |
| `--date-range` | str str | None | 日期范围过滤 |
| `--severity-filter` | str | None | 严重程度过滤 |
| `--material-filter` | str | None | 材料类型过滤 |
| `--verbose` | flag | False | 详细输出 |
| `--log-file` | str | "hazmat_collector.log" | 日志文件路径 |

## 日志记录

系统会生成详细的日志文件（默认：`hazmat_collector.log`），包含：
- 搜索进度和结果统计
- 网页抓取状态和错误
- 数据提取和过滤过程
- 文件保存操作

## 故障排除

### 常见问题

1. **搜索结果为空**
   - 检查网络连接
   - 尝试不同的关键词
   - 查看日志文件了解详细错误

2. **抓取失败**
   - 检查代理设置
   - 调整延迟参数
   - 查看robots.txt是否允许抓取

3. **信息提取不完整**
   - 这是正常现象，网页结构多样
   - 可以通过修改提取模式改进
   - 查看原始内容进行调试

### 调试模式

```bash
# 启用详细日志
python collector.py --verbose

# 减少结果数量进行测试
python collector.py --num-results 3 --verbose
```

## 法律声明

本工具仅用于合法的研究和分析目的。使用者需要：
- 遵守目标网站的服务条款
- 遵守当地法律法规
- 尊重数据版权
- 合理使用抓取的数据

## 技术架构

```
HazmatAccidentCollector
├── ProxyRotator          # 代理轮换管理
├── RateLimiter           # 速率限制控制
├── RobotsChecker         # robots.txt检查
├── WebScraper            # 网页内容抓取
├── AccidentDataExtractor # 事故信息提取
└── SearchEngines         # 搜索引擎接口
    └── DuckDuckGoSearchEngine
```

## 贡献指南

欢迎提交问题报告和改进建议：
1. 提交详细的错误报告
2. 建议新功能和改进
3. 贡献代码补丁
4. 改进文档

## 更新日志

### v1.0.0
- 初始版本发布
- 支持DuckDuckGo搜索
- 基本信息提取功能
- 多格式输出支持
- 代理轮换和速率限制
- robots.txt遵守机制
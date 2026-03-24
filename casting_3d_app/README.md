# 铸造行业2D到3D转换器

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/casting-industry/casting-2d3d-converter)
[![Python](https://img.shields.io/badge/python-3.8%2B-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

一款专为铸造行业设计的桌面应用程序，能够将铸造零件的2D图纸或照片自动转换为3D模型，并导出为STL、STEP、IGES等格式。

## 功能特性

### 核心功能
- **图像分析**：从2D图纸、照片中提取几何特征
- **3D建模**：基于OpenCASCADE内核构建参数化3D模型
- **铸造规则**：自动应用拔模斜度、圆角、壁厚检查等铸造工艺规则
- **多格式导出**：支持STL、STEP、IGES、BREP等CAD格式
- **质量检查**：生成铸造工艺可行性报告

### 支持的铸造工艺
- 砂型铸造 (Sand Casting)
- 压铸 (Die Casting)
- 熔模铸造 (Investment Casting)
- 离心铸造 (Centrifugal Casting)
- 金属型铸造 (Permanent Mold)

### 支持的材料
- 铝合金 (A356, ZL104等)
- 灰铸铁 (HT200, HT250等)
- 铸钢 (ZG270-500等)
- 锌合金
- 镁合金
- 铜合金

## 系统要求

### 最低配置
- **操作系统**: Windows 10/11, macOS 10.15+, Ubuntu 20.04+
- **Python**: 3.8 或更高版本
- **内存**: 4 GB RAM
- **显卡**: 支持OpenGL 3.0
- **磁盘空间**: 2 GB 可用空间

### 推荐配置
- **操作系统**: Windows 11, macOS 13+, Ubuntu 22.04+
- **Python**: 3.10 或更高版本
- **内存**: 8 GB RAM 或更多
- **显卡**: 支持OpenGL 4.5，推荐独立显卡
- **磁盘空间**: 5 GB 可用空间

## 安装

### 方式一：使用pip安装

```bash
# 克隆仓库
git clone https://github.com/casting-industry/casting-2d3d-converter.git
cd casting-2d3d-converter

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装应用程序
pip install -e .
```

### 方式二：使用conda安装

```bash
# 创建conda环境
conda create -n casting2d3d python=3.10
conda activate casting2d3d

# 安装依赖
conda install -c conda-forge opencv pythonocc-core numpy scipy
pip install PyQt6 Pillow scikit-image pandas pyyaml tqdm

# 安装应用程序
pip install -e .
```

### 方式三：使用预编译包

下载对应平台的预编译安装包：
- [Windows Installer](https://github.com/casting-industry/casting-2d3d-converter/releases)
- [macOS DMG](https://github.com/casting-industry/casting-2d3d-converter/releases)
- [Linux AppImage](https://github.com/casting-industry/casting-2d3d-converter/releases)

## 使用方法

### GUI模式

```bash
# 启动图形界面
python main.py

# 或
python -m casting_3d_app

# 或（安装后）
casting2d3d
```

### 命令行模式

```bash
# 基本用法
python main.py --no-gui --input drawing.jpg --output ./output --format stl

# 指定铸造工艺和材料
python main.py --no-gui \
    --input part.jpg \
    --output ./output \
    --format step \
    --process sand \
    --material A356

# 自定义工艺参数
python main.py --no-gui \
    --input part.jpg \
    --output ./output \
    --draft-external 1.5 \
    --draft-internal 2.0 \
    --fillet-radius 2.0 \
    --wall-thickness 3.0
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--no-gui` | 命令行模式 | False |
| `--input, -i` | 输入图像文件 | - |
| `--output, -o` | 输出目录 | ./output |
| `--format, -f` | 导出格式 (stl/step/iges/all) | stl |
| `--process, -p` | 铸造工艺 | sand |
| `--material, -m` | 材料代码 | A356 |
| `--draft-external` | 外表面拔模角度 | 1.5 |
| `--draft-internal` | 内表面拔模角度 | 2.0 |
| `--fillet-radius` | 圆角半径 | 2.0 |
| `--wall-thickness` | 最小壁厚 | 3.0 |
| `--quality-check` | 启用质量检查 | True |
| `--verbose, -V` | 详细输出 | False |
| `--config` | 配置文件路径 | - |

## 工作流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  1. 加载图像 │ -> │  2. 分析图像 │ -> │  3. 创建模型 │ -> │  4. 导出文件 │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼
  选择图像文件      提取几何特征      应用铸造规则      生成CAD文件
  (JPG/PNG/BMP)     (轮廓/圆/线)      (拔模/圆角)       (STL/STEP/IGES)
```

## 项目结构

```
casting_3d_app/
├── app/                    # 应用程序核心
│   ├── main_application.py # 主应用程序类
│   └── __init__.py
├── core/                   # 核心组件
│   ├── event_bus.py        # 事件总线
│   ├── workflow_manager.py # 工作流管理器
│   ├── config_manager.py   # 配置管理器
│   └── plugin_manager.py   # 插件管理器
├── gui/                    # 图形界面
│   ├── main_window.py      # 主窗口
│   └── __init__.py
├── plugins/                # 插件目录
├── resources/              # 资源文件
├── config/                 # 配置文件
├── main.py                 # 入口点
├── setup.py                # 安装脚本
├── requirements.txt        # 依赖列表
└── README.md               # 说明文档
```

## 配置

### 配置文件位置

- **Windows**: `%LOCALAPPDATA%\Casting3D\config.json`
- **macOS**: `~/Library/Application Support/Casting3D/config.json`
- **Linux**: `~/.config/casting3d/config.json`

### 配置示例

```json
{
  "image_analysis": {
    "denoise_method": "gaussian",
    "edge_method": "canny",
    "min_contour_area": 100.0
  },
  "modeling": {
    "default_extrusion_depth": 10.0,
    "auto_apply_fillets": true,
    "auto_apply_draft": true
  },
  "export": {
    "default_format": "stl_binary",
    "stl_tolerance": 0.01
  },
  "casting": {
    "default_process": "sand_casting",
    "default_material": "A356"
  },
  "ui": {
    "theme": "light",
    "language": "zh_CN"
  }
}
```

## 插件开发

### 创建自定义插件

```python
from casting_3d_app.core.plugin_manager import IImageProcessorPlugin

class MyImageProcessor(IImageProcessorPlugin):
    @property
    def name(self):
        return "MyImageProcessor"
    
    @property
    def version(self):
        return "1.0.0"
    
    def initialize(self, app_context):
        print(f"Initializing {self.name}")
        return True
    
    def shutdown(self):
        print(f"Shutting down {self.name}")
    
    def process(self, image):
        # 自定义图像处理逻辑
        return processed_image
```

### 插件安装

将插件文件放入插件目录：
- **Windows**: `%LOCALAPPDATA%\Casting3D\plugins\`
- **macOS**: `~/Library/Application Support/Casting3D/plugins/`
- **Linux**: `~/.config/casting3d/plugins/`

## 故障排除

### 常见问题

#### 1. OpenCV导入错误

```bash
# 重新安装OpenCV
pip uninstall opencv-python opencv-contrib-python
pip install opencv-python opencv-contrib-python
```

#### 2. OpenCASCADE导入错误

```bash
# 使用conda安装（推荐）
conda install -c conda-forge pythonocc-core

# 或使用pip
pip install pythonocc-core
```

#### 3. PyQt6导入错误

```bash
# 重新安装PyQt6
pip uninstall PyQt6 PyQt6-Qt6
pip install PyQt6
```

### 日志文件

日志文件位置：
- **Windows**: `%LOCALAPPDATA%\Casting3D\logs\`
- **macOS**: `~/Library/Application Support/Casting3D/logs/`
- **Linux**: `~/.config/casting3d/logs/`

### 获取帮助

- 查看日志文件了解详细错误信息
- 在[GitHub Issues](https://github.com/casting-industry/casting-2d3d-converter/issues)提交问题
- 发送邮件至 support@casting2d3d.com

## 开发

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/casting-industry/casting-2d3d-converter.git
cd casting-2d3d-converter

# 创建开发环境
python -m venv venv-dev
source venv-dev/bin/activate  # 或 venv-dev\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_image_analysis.py

# 生成覆盖率报告
pytest --cov=casting_3d_app --cov-report=html
```

### 代码规范

```bash
# 格式化代码
black casting_3d_app/

# 检查代码风格
flake8 casting_3d_app/

# 类型检查
mypy casting_3d_app/
```

## 贡献

我们欢迎各种形式的贡献！请阅读[CONTRIBUTING.md](CONTRIBUTING.md)了解如何参与项目。

### 贡献方式
- 提交Bug报告
- 提出新功能建议
- 提交代码改进
- 完善文档
- 翻译界面

## 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

```
MIT License

Copyright (c) 2024 Casting Industry Solutions

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 致谢

感谢以下开源项目的支持：
- [OpenCASCADE](https://www.opencascade.com/) - 3D建模内核
- [OpenCV](https://opencv.org/) - 计算机视觉库
- [PyQt](https://www.riverbankcomputing.com/software/pyqt/) - GUI框架
- [NumPy](https://numpy.org/) - 科学计算库

## 联系方式

- **项目主页**: https://github.com/casting-industry/casting-2d3d-converter
- **问题反馈**: https://github.com/casting-industry/casting-2d3d-converter/issues
- **邮箱**: support@casting2d3d.com

---

**注意**: 本项目仍在积极开发中，API可能会有变动。请关注发布说明了解最新更新。

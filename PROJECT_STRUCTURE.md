# 铸造行业2D到3D转换应用程序 - 项目结构

## 完整文件清单

```
/mnt/okcomputer/output/
│
├── 📁 casting_3d_app/                    # 【主应用程序】
│   │
│   ├── 📄 main.py                        # 应用程序入口点
│   ├── 📄 setup.py                       # 安装打包脚本
│   ├── 📄 requirements.txt               # Python依赖列表
│   ├── 📄 README.md                      # 项目说明文档
│   ├── 📄 ARCHITECTURE.md                # 技术架构文档
│   │
│   ├── 📁 app/                           # 应用程序核心
│   │   ├── __init__.py
│   │   └── main_application.py           # 主应用程序类
│   │
│   ├── 📁 core/                          # 核心组件
│   │   ├── __init__.py
│   │   ├── event_bus.py                  # 事件总线（发布-订阅模式）
│   │   ├── workflow_manager.py           # 工作流管理器（状态机模式）
│   │   ├── config_manager.py             # 配置管理器（多级配置）
│   │   ├── plugin_manager.py             # 插件管理器（插件架构）
│   │   └── module_adapter.py             # 模块适配器（模块整合）
│   │
│   ├── 📁 gui/                           # 图形界面
│   │   ├── __init__.py
│   │   └── main_window.py                # 主窗口（PyQt6）
│   │
│   ├── 📁 plugins/                       # 插件目录
│   │   └── example_plugin.py             # 示例插件
│   │
│   └── 📁 config/                        # 配置文件
│       └── default_config.json           # 默认配置
│
├── 📁 casting_3d_engine/                 # 【3D建模引擎模块】
│   │
│   ├── 📄 __init__.py
│   ├── 📄 README.md                      # 模块说明
│   ├── 📄 requirements.txt               # 依赖列表
│   │
│   ├── 📁 core/                          # 核心引擎
│   │   ├── __init__.py
│   │   ├── types.py                      # 基础数据类型
│   │   ├── geometry_kernel.py            # OpenCASCADE几何内核封装
│   │   ├── feature_base.py               # 特征基类和工厂
│   │   ├── features.py                   # 具体特征实现
│   │   ├── command_system.py             # 命令模式和撤销/重做
│   │   ├── feature_manager.py            # 特征管理器
│   │   ├── model_builder.py              # 模型构建器
│   │   └── casting_3d_engine.py          # 主引擎类
│   │
│   ├── 📁 io/                            # IO模块
│   │   ├── __init__.py
│   │   ├── export_manager.py             # 导出管理器
│   │   └── input_interface.py            # 输入接口
│   │
│   └── 📁 examples/                      # 示例代码
│       ├── __init__.py
│       ├── basic_usage.py                # 基本使用示例
│       ├── from_2d_example.py            # 2D到3D转换示例
│       └── plugin_example.py             # 插件开发示例
│
├── 📁 image_analysis_module/             # 【图像分析模块】
│   │
│   ├── 📄 __init__.py
│   ├── 📄 README.md                      # 模块说明
│   ├── 📄 TECHNICAL_DESIGN.md            # 技术设计文档
│   ├── 📄 requirements.txt               # 依赖列表
│   │
│   ├── 📁 core/                          # 核心模块
│   │   ├── __init__.py
│   │   ├── data_structures.py            # 数据结构定义
│   │   └── image_analyzer.py             # 主分析器类
│   │
│   ├── 📁 algorithms/                    # 算法模块
│   │   ├── __init__.py
│   │   └── shape_recognition.py          # 形状识别算法
│   │
│   ├── 📁 interfaces/                    # 接口模块
│   │   ├── __init__.py
│   │   └── model3d_interface.py          # 3D建模引擎接口
│   │
│   ├── 📁 utils/                         # 工具模块
│   │   ├── __init__.py
│   │   ├── config_loader.py              # 配置加载器
│   │   └── geometry_utils.py             # 几何计算工具
│   │
│   ├── 📁 config/                        # 配置文件
│   │   └── default_config.yaml           # 默认配置
│   │
│   └── 📁 examples/                      # 示例代码
│       └── basic_usage.py                # 使用示例
│
├── 📁 【独立模块文件】                    # 可独立使用的模块
│   │
│   ├── 📄 cad_exporter_base.py           # CAD导出基类
│   ├── 📄 stl_exporter.py                # STL格式导出器
│   ├── 📄 step_exporter.py               # STEP格式导出器
│   ├── 📄 iges_exporter.py               # IGES格式导出器
│   ├── 📄 cad_export_manager.py          # CAD导出管理器
│   │
│   ├── 📄 casting_data_models.py         # 铸造数据模型
│   ├── 📄 casting_rules_engine.py        # 铸造规则引擎
│   ├── 📄 casting_integration_interface.py # 集成接口
│   ├── 📄 casting_rules_config.json      # 可配置工艺规则
│   │
│   └── 📄 example_usage.py               # 使用示例
│
└── 📁 【设计文档】
    │
    ├── 📄 casting_3d_engine_architecture.md    # 3D引擎架构设计
    ├── 📄 CAD_EXPORT_MODULE_DESIGN.md          # CAD导出模块设计
    ├── 📄 casting_requirements_specification.md # 需求规格说明书
    └── 📄 casting_analysis_summary.md          # 分析总结报告
```

## 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户界面层 (GUI Layer)                      │
│                    casting_3d_app/gui/                          │
├─────────────────────────────────────────────────────────────────┤
│                      应用核心层 (Application Core)               │
│                    casting_3d_app/app/                          │
│                    casting_3d_app/core/                         │
├─────────────────────────────────────────────────────────────────┤
│                      业务逻辑层 (Business Logic)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 图像分析    │  │ 3D建模引擎  │  │ CAD导出     │              │
│  │ image_      │  │ casting_    │  │ *_exporter  │              │
│  │ analysis_   │  │ 3d_engine/  │  │ .py         │              │
│  │ module/     │  │             │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│  ┌─────────────┐                                                │
│  │ 铸造规则    │                                                │
│  │ casting_    │                                                │
│  │ rules_      │                                                │
│  │ engine.py   │                                                │
│  └─────────────┘                                                │
├─────────────────────────────────────────────────────────────────┤
│                      外部依赖层 (External Dependencies)          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ OpenCASCADE │  │ OpenCV      │  │ PyQt6       │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## 核心功能流程

```
2D图像 → 图像分析 → 特征提取 → 3D建模 → 铸造规则 → CAD导出
   │         │          │          │          │          │
   │    ┌────┴────┐    │     ┌────┴────┐    │     ┌────┴────┐
   │    │ 预处理  │    │     │ 拉伸    │    │     │ STL     │
   │    │ 边缘    │    │     │ 旋转    │    │     │ STEP    │
   │    │ 轮廓    │    │     │ 布尔    │    │     │ IGES    │
   │    └─────────┘    │     └─────────┘    │     └─────────┘
   │                   │                    │
   │              ┌────┴────┐          ┌────┴────┐
   │              │ 轮廓    │          │ 拔模    │
   │              │ 圆      │          │ 圆角    │
   │              │ 圆弧    │          │ 壁厚    │
   │              └─────────┘          └─────────┘
```

## 快速开始

### 1. 安装依赖
```bash
cd /mnt/okcomputer/output/casting_3d_app
pip install -r requirements.txt
```

### 2. 运行GUI模式
```bash
python main.py
```

### 3. 运行命令行模式
```bash
python main.py --no-gui --input drawing.jpg --output ./output --format stl
```

## 文件统计

- **Python源文件**: 50+
- **文档文件**: 10+
- **配置文件**: 5+
- **代码总行数**: 约15000+行
- **文档总字数**: 约50000+字


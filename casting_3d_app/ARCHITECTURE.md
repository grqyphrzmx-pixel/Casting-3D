# 铸造行业2D到3D转换应用程序 - 技术架构文档

## 1. 系统概述

### 1.1 项目背景
本应用程序专为铸造行业设计，能够将铸造零件的2D图纸或照片自动转换为3D模型，并导出为STL、STEP、IGES等格式。系统集成了图像分析、3D建模引擎、CAD导出和铸造工艺规则等多个模块。

### 1.2 核心功能
- **图像分析**：从2D图纸/照片中提取几何特征
- **3D建模**：基于OpenCASCADE内核构建参数化3D模型
- **铸造规则**：自动应用拔模斜度、圆角、壁厚检查等铸造工艺规则
- **多格式导出**：支持STL、STEP、IGES、BREP等CAD格式
- **质量检查**：生成铸造工艺可行性报告

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户界面层 (GUI Layer)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  主窗口     │  │  图像查看器  │  │  3D查看器   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│                      应用核心层 (Application Core)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 主应用类    │  │ 工作流管理器 │  │ 事件总线    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 配置管理器  │  │ 插件管理器  │  │ 日志系统    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│                      业务逻辑层 (Business Logic)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 图像分析模块 │  │ 3D建模引擎  │  │ CAD导出模块 │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │ 铸造规则引擎 │  │ 质量检查器  │                               │
│  └─────────────┘  └─────────────┘                               │
├─────────────────────────────────────────────────────────────────┤
│                      数据访问层 (Data Access)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 文件I/O     │  │ 配置存储    │  │ 缓存管理    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│                      外部依赖层 (External Dependencies)          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ OpenCASCADE │  │ OpenCV      │  │ PyQt6       │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块依赖关系

```
main.py
  └── MainApplication
        ├── MainWindow (GUI)
        │     ├── ImageViewer
        │     ├── Model3DViewer
        │     └── PropertyPanel
        ├── WorkflowManager
        │     ├── ImageAnalysisWorkflow
        │     ├── Model3DWorkflow
        │     └── ExportWorkflow
        ├── EventBus
        ├── ConfigManager
        ├── PluginManager
        └── Module Interfaces
              ├── ImageAnalyzer (图像分析模块)
              ├── Casting3DEngine (3D建模引擎)
              ├── CADExportManager (CAD导出模块)
              └── CastingRulesEngine (铸造规则引擎)
```

## 3. 核心组件设计

### 3.1 事件总线 (Event Bus)

**设计模式**: 发布-订阅模式 (Pub-Sub)

**核心功能**:
- 模块间松耦合通信
- 异步事件处理
- 事件优先级管理
- 事件日志记录

**事件类型**:
```python
EVENT_IMAGE_LOADED = "image.loaded"
EVENT_ANALYSIS_STARTED = "analysis.started"
EVENT_ANALYSIS_COMPLETED = "analysis.completed"
EVENT_MODEL_CREATED = "model.created"
EVENT_MODEL_UPDATED = "model.updated"
EVENT_EXPORT_STARTED = "export.started"
EVENT_EXPORT_COMPLETED = "export.completed"
EVENT_ERROR_OCCURRED = "error.occurred"
```

### 3.2 工作流管理器 (Workflow Manager)

**设计模式**: 状态机模式 (State Machine)

**工作流状态**:
```
IDLE → IMAGE_LOADED → ANALYZING → ANALYSIS_DONE → MODELING → MODEL_DONE → EXPORTING → COMPLETED
              ↓           ↓            ↓              ↓           ↓            ↓
           CANCELLED    FAILED       FAILED         FAILED      FAILED       FAILED
```

**工作流类型**:
1. **完整工作流**: 图像 → 分析 → 建模 → 导出
2. **分析工作流**: 图像 → 分析
3. **建模工作流**: 分析结果 → 3D模型
4. **导出工作流**: 3D模型 → CAD文件

### 3.3 插件管理器 (Plugin Manager)

**设计模式**: 插件架构模式 (Plugin Architecture)

**插件类型**:
- **图像处理插件**: 自定义图像预处理算法
- **特征识别插件**: 扩展形状识别能力
- **导出格式插件**: 支持新的CAD格式
- **铸造规则插件**: 自定义工艺规则

**插件接口**:
```python
class IPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def version(self) -> str: ...
    
    @abstractmethod
    def initialize(self, app_context) -> bool: ...
    
    @abstractmethod
    def shutdown(self) -> None: ...
```

### 3.4 配置管理器 (Config Manager)

**设计模式**: 单例模式 (Singleton)

**配置层级**:
1. 系统默认配置
2. 用户配置文件 (~/.casting3d/config.json)
3. 项目配置文件 (project.c3d/config.json)
4. 运行时配置覆盖

**配置分类**:
- 图像分析配置
- 3D建模配置
- 导出配置
- 铸造工艺配置
- UI配置

## 4. 数据流设计

### 4.1 2D到3D转换数据流

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  2D图像  │───→│ 图像分析 │───→│ 特征提取 │───→│ 3D建模   │───→│ CAD导出  │
│          │    │          │    │          │    │          │    │          │
│ - 图纸   │    │ - 预处理 │    │ - 轮廓   │    │ - 拉伸   │    │ - STL    │
│ - 照片   │    │ - 边缘   │    │ - 圆     │    │ - 旋转   │    │ - STEP   │
│ - 扫描件 │    │ - 轮廓   │    │ - 圆弧   │    │ - 布尔   │    │ - IGES   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                                     ↓
                                                              ┌──────────┐
                                                              │ 质量报告 │
                                                              └──────────┘
```

### 4.2 模块间数据交换格式

**图像分析输出**:
```python
AnalysisResult:
  - image_info: ImageInfo
  - contours: List[Contour]
  - features: List[GeometricFeature]
  - dimensions: List[Dimension]
  - scale_factor: float
```

**3D建模输入**:
```python
ModelBuildData:
  - base_profile: Profile2D
  - features: List[FeatureData]
  - dimensions: Dict[str, float]
  - casting_params: CastingParameters
```

**导出输入**:
```python
ExportData:
  - shape_id: str
  - format: ExportFormat
  - options: ExportOptions
  - metadata: ExportMetadata
```

## 5. GUI设计

### 5.1 主窗口布局

```
┌─────────────────────────────────────────────────────────────────┐
│  菜单栏  │  File  │  Edit  │  View  │  Tools  │  Help          │
├─────────────────────────────────────────────────────────────────┤
│  工具栏  │ [打开] [分析] [建模] [导出] [撤销] [重做] [设置]      │
├──────────────────┬──────────────────────────┬───────────────────┤
│                  │                          │                   │
│   项目面板       │      中央工作区          │    属性面板       │
│   (左侧面板)     │                          │    (右侧面板)     │
│                  │  ┌────────────────────┐  │                   │
│  - 图像列表      │  │    图像/3D视图     │  │  - 特征属性       │
│  - 特征树        │  │                    │  │  - 尺寸信息       │
│  - 历史记录      │  │   (标签页切换)     │  │  - 工艺参数       │
│                  │  │                    │  │  - 质量报告       │
│                  │  └────────────────────┘  │                   │
│                  │                          │                   │
├──────────────────┴──────────────────────────┴───────────────────┤
│  状态栏  │ 就绪 │ 缩放: 100% │ 坐标: (0, 0) │ 进度: [====]  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 视图组件

**图像视图**:
- 原始图像显示
- 分析结果叠加显示（轮廓、特征标记）
- 缩放、平移、测量工具

**3D视图**:
- 基于OpenCASCADE的3D可视化
- 旋转、缩放、平移
- 线框/实体/半透明显示模式
- 截面查看

## 6. 扩展性设计

### 6.1 插件扩展点

```python
# 图像处理扩展点
class IImageProcessor(IPlugin):
    def process(self, image: np.ndarray) -> np.ndarray: ...

# 特征识别扩展点
class IFeatureRecognizer(IPlugin):
    def recognize(self, contour: Contour) -> Optional[GeometricFeature]: ...

# 导出器扩展点
class IExporter(IPlugin):
    def export(self, shape_id: str, filepath: str) -> bool: ...

# 铸造规则扩展点
class ICastingRule(IPlugin):
    def check(self, part: CastingPart) -> List[QualityCheckItem]: ...
```

### 6.2 版本兼容性

**版本策略**:
- 主版本号：不兼容的API变更
- 次版本号：向后兼容的功能添加
- 修订号：向后兼容的问题修复

**兼容性保证**:
- 配置文件版本迁移
- 插件API版本检查
- 项目文件格式版本管理

## 7. 错误处理与日志

### 7.1 错误处理策略

**错误级别**:
- DEBUG: 调试信息
- INFO: 一般信息
- WARNING: 警告（可继续）
- ERROR: 错误（当前操作失败）
- CRITICAL: 严重错误（需要重启）

**错误恢复**:
- 自动重试机制
- 优雅降级
- 用户友好的错误提示

### 7.2 日志系统

**日志分类**:
- 应用日志 (app.log)
- 分析日志 (analysis.log)
- 建模日志 (modeling.log)
- 导出日志 (export.log)

**日志配置**:
```python
logging_config = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'console': {
            'class': 'logging.StreamHandler'
        }
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO'
    }
}
```

## 8. 性能优化

### 8.1 图像分析优化

- 多线程图像处理
- GPU加速（CUDA/OpenCL）
- 图像金字塔快速预览
- 智能ROI区域选择

### 8.2 3D建模优化

- 增量式模型重建
- 特征缓存
- LOD（细节层次）支持
- 延迟加载

### 8.3 内存管理

- 大图像分块处理
- 3D模型流式加载
- 自动垃圾回收
- 内存使用监控

## 9. 安全与稳定性

### 9.1 输入验证

- 图像格式验证
- 文件大小限制
- 路径安全检查
- 内存溢出防护

### 9.2 异常处理

- 全局异常捕获
- 崩溃报告生成
- 自动保存恢复点
- 会话状态恢复

## 10. 部署与分发

### 10.1 打包方案

**Windows**:
- PyInstaller打包为EXE
- NSIS安装程序
- 自动更新支持

**Linux**:
- AppImage格式
- DEB/RPM包
- Docker容器

**macOS**:
- APP Bundle
- DMG安装包
- 代码签名

### 10.2 依赖管理

```
requirements.txt:
- PyQt6 >= 6.4.0
- opencv-python >= 4.7.0
- numpy >= 1.24.0
- OpenCASCADE (pythonocc-core >= 7.7.0)
- Pillow >= 9.5.0
```

## 11. 开发规范

### 11.1 代码规范

- PEP 8编码规范
- 类型注解
- 文档字符串（Google风格）
- 单元测试覆盖率 > 80%

### 11.2 版本控制

- Git Flow工作流
- 语义化版本号
- 变更日志维护
- 代码审查流程

## 12. 未来扩展

### 12.1 计划功能

- AI辅助特征识别
- 云端协作
- VR/AR预览
- 批量处理
- API服务化

### 12.2 技术债务

- 逐步迁移到异步架构
- 优化大型模型性能
- 完善国际化支持
- 增强测试覆盖

---

**文档版本**: 1.0
**最后更新**: 2024年
**作者**: 软件架构师

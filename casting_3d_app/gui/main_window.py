"""
主窗口模块

铸造行业2D到3D转换应用程序的主窗口实现。
基于PyQt6构建，提供完整的用户界面。
"""

import sys
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

# PyQt6导入
try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QMenuBar, QToolBar, QStatusBar, QFileDialog,
        QMessageBox, QProgressBar, QLabel, QSplitter,
        QTreeWidget, QTreeWidgetItem, QDockWidget,
        QTabWidget, QTextEdit, QPushButton, QComboBox,
        QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout,
        QDialog, QDialogButtonBox, QApplication
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
    from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPixmap
    HAS_QT = True
except ImportError:
    HAS_QT = False
    # 创建一个假的QMainWindow用于类型提示
    class QMainWindow:
        pass

# 导入应用程序核心
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.main_application import MainApplication, ApplicationContext
from core.event_bus import EventBus
from core.workflow_manager import WorkflowManager, WorkflowType, WorkflowState
from core.config_manager import ConfigManager, ConfigLevel

logger = logging.getLogger(__name__)


class WorkflowThread(QThread):
    """工作流执行线程"""
    
    progress_updated = pyqtSignal(str, int)
    step_completed = pyqtSignal(str, bool)
    workflow_finished = pyqtSignal(bool, str)
    
    def __init__(self, workflow, parent=None):
        super().__init__(parent)
        self.workflow = workflow
        self._cancelled = False
    
    def run(self):
        """执行工作流"""
        try:
            # 这里实现具体的工作流执行逻辑
            # 实际执行由工作流管理器处理
            self.workflow_finished.emit(True, "")
        except Exception as e:
            self.workflow_finished.emit(False, str(e))
    
    def cancel(self):
        """取消工作流"""
        self._cancelled = True
        if self.workflow:
            self.workflow.cancel()


class ImageViewerWidget(QWidget):
    """图像查看器组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_image_path = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 图像显示标签
        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #2d2d2d; color: #ffffff;")
        layout.addWidget(self.image_label)
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.zoom_in_btn = QPushButton("Zoom In")
        self.zoom_out_btn = QPushButton("Zoom Out")
        self.fit_btn = QPushButton("Fit")
        self.original_btn = QPushButton("1:1")
        
        toolbar.addWidget(self.zoom_in_btn)
        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.fit_btn)
        toolbar.addWidget(self.original_btn)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
    
    def load_image(self, image_path: str):
        """加载图像"""
        self._current_image_path = image_path
        
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            # 缩放以适应显示区域
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText(f"Failed to load: {image_path}")
    
    def clear(self):
        """清除图像"""
        self._current_image_path = None
        self.image_label.setText("No image loaded")
        self.image_label.setPixmap(QPixmap())


class Model3DViewerWidget(QWidget):
    """3D模型查看器组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 3D视图占位符
        self.view_label = QLabel("3D View")
        self.view_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view_label.setStyleSheet("background-color: #1a1a1a; color: #ffffff;")
        layout.addWidget(self.view_label)
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.wireframe_btn = QPushButton("Wireframe")
        self.solid_btn = QPushButton("Solid")
        self.shaded_btn = QPushButton("Shaded")
        self.section_btn = QPushButton("Section")
        
        toolbar.addWidget(self.wireframe_btn)
        toolbar.addWidget(self.solid_btn)
        toolbar.addWidget(self.shaded_btn)
        toolbar.addWidget(self.section_btn)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
    
    def load_model(self, model_path: str):
        """加载3D模型"""
        # 这里集成OpenCASCADE或OpenGL渲染
        self.view_label.setText(f"3D Model: {model_path}")


class ProjectPanelWidget(QTreeWidget):
    """项目面板组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Project")
        self._setup_ui()
    
    def _setup_ui(self):
        # 添加根项目
        self.root_item = QTreeWidgetItem(self)
        self.root_item.setText(0, "Untitled Project")
        
        # 图像节点
        self.images_item = QTreeWidgetItem(self.root_item)
        self.images_item.setText(0, "Images")
        
        # 特征节点
        self.features_item = QTreeWidgetItem(self.root_item)
        self.features_item.setText(0, "Features")
        
        # 模型节点
        self.models_item = QTreeWidgetItem(self.root_item)
        self.models_item.setText(0, "Models")
        
        # 展开根节点
        self.root_item.setExpanded(True)
    
    def add_image(self, image_path: str):
        """添加图像"""
        item = QTreeWidgetItem(self.images_item)
        item.setText(0, Path(image_path).name)
        item.setData(0, Qt.ItemDataRole.UserRole, image_path)
    
    def add_feature(self, feature_name: str, feature_data: Any):
        """添加特征"""
        item = QTreeWidgetItem(self.features_item)
        item.setText(0, feature_name)
        item.setData(0, Qt.ItemDataRole.UserRole, feature_data)
    
    def clear_project(self):
        """清除项目"""
        self.images_item.takeChildren()
        self.features_item.takeChildren()
        self.models_item.takeChildren()


class PropertiesPanelWidget(QWidget):
    """属性面板组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 铸造工艺参数
        casting_group = QGroupBox("Casting Process")
        casting_layout = QFormLayout()
        
        self.process_combo = QComboBox()
        self.process_combo.addItems([
            "Sand Casting",
            "Die Casting",
            "Investment Casting",
            "Centrifugal Casting",
            "Permanent Mold"
        ])
        casting_layout.addRow("Process:", self.process_combo)
        
        self.material_combo = QComboBox()
        self.material_combo.addItems([
            "A356 (Aluminum)",
            "HT250 (Gray Iron)",
            "ZG270-500 (Steel)",
            "Zamak 3 (Zinc)"
        ])
        casting_layout.addRow("Material:", self.material_combo)
        
        casting_group.setLayout(casting_layout)
        layout.addWidget(casting_group)
        
        # 拔模斜度参数
        draft_group = QGroupBox("Draft Angle")
        draft_layout = QFormLayout()
        
        self.draft_external = QDoubleSpinBox()
        self.draft_external.setRange(0, 10)
        self.draft_external.setValue(1.5)
        self.draft_external.setSuffix("°")
        draft_layout.addRow("External:", self.draft_external)
        
        self.draft_internal = QDoubleSpinBox()
        self.draft_internal.setRange(0, 10)
        self.draft_internal.setValue(2.0)
        self.draft_internal.setSuffix("°")
        draft_layout.addRow("Internal:", self.draft_internal)
        
        draft_group.setLayout(draft_layout)
        layout.addWidget(draft_group)
        
        # 圆角参数
        fillet_group = QGroupBox("Fillet")
        fillet_layout = QFormLayout()
        
        self.fillet_radius = QDoubleSpinBox()
        self.fillet_radius.setRange(0, 50)
        self.fillet_radius.setValue(2.0)
        self.fillet_radius.setSuffix(" mm")
        fillet_layout.addRow("Radius:", self.fillet_radius)
        
        fillet_group.setLayout(fillet_layout)
        layout.addWidget(fillet_group)
        
        # 导出参数
        export_group = QGroupBox("Export")
        export_layout = QFormLayout()
        
        self.export_format = QComboBox()
        self.export_format.addItems(["STL", "STEP", "IGES", "All"])
        export_layout.addRow("Format:", self.export_format)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
    
    def get_casting_params(self) -> Dict[str, Any]:
        """获取铸造参数"""
        return {
            'process': self.process_combo.currentText(),
            'material': self.material_combo.currentText(),
            'draft_external': self.draft_external.value(),
            'draft_internal': self.draft_internal.value(),
            'fillet_radius': self.fillet_radius.value(),
            'export_format': self.export_format.currentText()
        }


class LogPanelWidget(QTextEdit):
    """日志面板组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(1000)
    
    def append_log(self, message: str, level: str = "INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {
            "DEBUG": "#808080",
            "INFO": "#000000",
            "WARNING": "#ff8c00",
            "ERROR": "#ff0000",
            "CRITICAL": "#8b0000"
        }.get(level, "#000000")
        
        html = f'<span style="color: #808080;">[{timestamp}]</span> '
        html += f'<span style="color: {color};">{level}: {message}</span>'
        
        self.append(html)


class MainWindow(QMainWindow):
    """
    主窗口类
    
    铸造行业2D到3D转换应用程序的主窗口。
    提供完整的用户界面和交互功能。
    """
    
    def __init__(self, app: MainApplication = None):
        if not HAS_QT:
            raise ImportError("PyQt6 is required for GUI")
        
        super().__init__()
        
        self._app = app
        self._current_project_path = None
        self._current_image_path = None
        self._workflow_thread = None
        
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_events()
        
        # 加载窗口状态
        self._load_window_state()
        
        logger.info("MainWindow initialized")
    
    def _setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle(f"{MainApplication.APP_NAME} v{MainApplication.VERSION}")
        self.setMinimumSize(1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板（项目面板）
        self.project_dock = QDockWidget("Project", self)
        self.project_panel = ProjectPanelWidget()
        self.project_dock.setWidget(self.project_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_dock)
        
        # 中央工作区
        self.central_tabs = QTabWidget()
        
        # 图像查看器
        self.image_viewer = ImageViewerWidget()
        self.central_tabs.addTab(self.image_viewer, "Image")
        
        # 3D查看器
        self.model_viewer = Model3DViewerWidget()
        self.central_tabs.addTab(self.model_viewer, "3D Model")
        
        # 日志面板
        self.log_panel = LogPanelWidget()
        self.central_tabs.addTab(self.log_panel, "Log")
        
        splitter.addWidget(self.central_tabs)
        
        # 右侧面板（属性面板）
        self.properties_dock = QDockWidget("Properties", self)
        self.properties_panel = PropertiesPanelWidget()
        self.properties_dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_dock)
    
    def _setup_menus(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # File菜单
        file_menu = menubar.addMenu("&File")
        
        self.open_action = QAction("&Open Image...", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.on_open_image)
        file_menu.addAction(self.open_action)
        
        self.open_project_action = QAction("Open &Project...", self)
        self.open_project_action.triggered.connect(self.on_open_project)
        file_menu.addAction(self.open_project_action)
        
        file_menu.addSeparator()
        
        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.on_save)
        file_menu.addAction(self.save_action)
        
        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self.on_save_as)
        file_menu.addAction(self.save_as_action)
        
        file_menu.addSeparator()
        
        self.export_action = QAction("&Export...", self)
        self.export_action.triggered.connect(self.on_export)
        file_menu.addAction(self.export_action)
        
        file_menu.addSeparator()
        
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)
        
        # Edit菜单
        edit_menu = menubar.addMenu("&Edit")
        
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.on_undo)
        edit_menu.addAction(self.undo_action)
        
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self.on_redo)
        edit_menu.addAction(self.redo_action)
        
        edit_menu.addSeparator()
        
        self.preferences_action = QAction("&Preferences...", self)
        self.preferences_action.triggered.connect(self.on_preferences)
        edit_menu.addAction(self.preferences_action)
        
        # Process菜单
        process_menu = menubar.addMenu("&Process")
        
        self.analyze_action = QAction("&Analyze Image", self)
        self.analyze_action.triggered.connect(self.on_analyze)
        process_menu.addAction(self.analyze_action)
        
        self.create_model_action = QAction("&Create 3D Model", self)
        self.create_model_action.triggered.connect(self.on_create_model)
        process_menu.addAction(self.create_model_action)
        
        self.apply_rules_action = QAction("&Apply Casting Rules", self)
        self.apply_rules_action.triggered.connect(self.on_apply_rules)
        process_menu.addAction(self.apply_rules_action)
        
        process_menu.addSeparator()
        
        self.full_workflow_action = QAction("&Full Workflow", self)
        self.full_workflow_action.triggered.connect(self.on_full_workflow)
        process_menu.addAction(self.full_workflow_action)
        
        # View菜单
        view_menu = menubar.addMenu("&View")
        
        self.show_project_action = QAction("&Project Panel", self)
        self.show_project_action.setCheckable(True)
        self.show_project_action.setChecked(True)
        self.show_project_action.triggered.connect(
            lambda: self.project_dock.setVisible(self.show_project_action.isChecked())
        )
        view_menu.addAction(self.show_project_action)
        
        self.show_properties_action = QAction("&Properties Panel", self)
        self.show_properties_action.setCheckable(True)
        self.show_properties_action.setChecked(True)
        self.show_properties_action.triggered.connect(
            lambda: self.properties_dock.setVisible(self.show_properties_action.isChecked())
        )
        view_menu.addAction(self.show_properties_action)
        
        # Help菜单
        help_menu = menubar.addMenu("&Help")
        
        self.about_action = QAction("&About", self)
        self.about_action.triggered.connect(self.on_about)
        help_menu.addAction(self.about_action)
    
    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.analyze_action)
        toolbar.addAction(self.create_model_action)
        toolbar.addAction(self.export_action)
        toolbar.addSeparator()
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
    
    def _setup_statusbar(self):
        """设置状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # 状态标签
        self.status_label = QLabel("Ready")
        self.statusbar.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.progress_bar)
        
        # 坐标标签
        self.coord_label = QLabel("X: 0, Y: 0")
        self.statusbar.addPermanentWidget(self.coord_label)
    
    def _connect_events(self):
        """连接事件"""
        if self._app and self._app.event_bus:
            # 订阅应用程序事件
            self._app.event_bus.subscribe(
                EventBus.EVENT_IMAGE_LOADED,
                self._on_image_loaded_event
            )
            self._app.event_bus.subscribe(
                EventBus.EVENT_IMAGE_ANALYSIS_PROGRESS,
                self._on_analysis_progress
            )
            self._app.event_bus.subscribe(
                EventBus.EVENT_EXPORT_PROGRESS,
                self._on_export_progress
            )
            self._app.event_bus.subscribe(
                EventBus.EVENT_ERROR_OCCURRED,
                self._on_error_occurred
            )
    
    def _load_window_state(self):
        """加载窗口状态"""
        if self._app and self._app.config_manager:
            width = self._app.config_manager.get('ui.window_width', 1400)
            height = self._app.config_manager.get('ui.window_height', 900)
            self.resize(width, height)
            
            if self._app.config_manager.get('ui.window_maximized', False):
                self.showMaximized()
    
    def _save_window_state(self):
        """保存窗口状态"""
        if self._app and self._app.config_manager:
            if not self.isMaximized():
                self._app.config_manager.set('ui.window_width', self.width(), ConfigLevel.USER)
                self._app.config_manager.set('ui.window_height', self.height(), ConfigLevel.USER)
            self._app.config_manager.set('ui.window_maximized', self.isMaximized(), ConfigLevel.USER)
    
    # ==================== 事件处理 ====================
    
    def _on_image_loaded_event(self, event):
        """图像加载事件处理"""
        data = event.data
        if data and 'path' in data:
            self.image_viewer.load_image(data['path'])
            self.project_panel.add_image(data['path'])
            self.status_label.setText(f"Loaded: {data['path']}")
    
    def _on_analysis_progress(self, event):
        """分析进度事件处理"""
        data = event.data
        if data:
            progress = data.get('progress', 0)
            message = data.get('message', '')
            self.progress_bar.setValue(progress)
            self.status_label.setText(message)
    
    def _on_export_progress(self, event):
        """导出进度事件处理"""
        data = event.data
        if data:
            progress = data.get('progress', 0)
            self.progress_bar.setValue(progress)
    
    def _on_error_occurred(self, event):
        """错误事件处理"""
        data = event.data
        if data:
            error_msg = str(data.get('message', 'Unknown error'))
            self.log_panel.append_log(error_msg, "ERROR")
            QMessageBox.critical(self, "Error", error_msg)
    
    # ==================== 槽函数 ====================
    
    def on_open_image(self):
        """打开图像"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;All Files (*)"
        )
        
        if file_path:
            self._current_image_path = file_path
            self.image_viewer.load_image(file_path)
            self.project_panel.add_image(file_path)
            
            # 发布事件
            if self._app:
                self._app.publish_event(EventBus.EVENT_IMAGE_LOADED, {'path': file_path})
            
            self.status_label.setText(f"Loaded: {file_path}")
    
    def on_open_project(self):
        """打开项目"""
        QMessageBox.information(self, "Info", "Open Project - Not implemented yet")
    
    def on_save(self):
        """保存"""
        QMessageBox.information(self, "Info", "Save - Not implemented yet")
    
    def on_save_as(self):
        """另存为"""
        QMessageBox.information(self, "Info", "Save As - Not implemented yet")
    
    def on_export(self):
        """导出"""
        if not self._current_image_path:
            QMessageBox.warning(self, "Warning", "Please load an image first")
            return
        
        # 获取导出参数
        params = self.properties_panel.get_casting_params()
        
        # 选择导出目录
        export_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if export_dir:
            self.status_label.setText("Exporting...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 发布导出事件
            if self._app:
                self._app.publish_event(EventBus.EVENT_EXPORT_STARTED, {
                    'directory': export_dir,
                    'params': params
                })
            
            self.status_label.setText("Export completed")
            self.progress_bar.setVisible(False)
    
    def on_undo(self):
        """撤销"""
        if self._app:
            self._app.publish_event(EventBus.EVENT_UNDO)
    
    def on_redo(self):
        """重做"""
        if self._app:
            self._app.publish_event(EventBus.EVENT_REDO)
    
    def on_preferences(self):
        """首选项"""
        QMessageBox.information(self, "Info", "Preferences - Not implemented yet")
    
    def on_analyze(self):
        """分析图像"""
        if not self._current_image_path:
            QMessageBox.warning(self, "Warning", "Please load an image first")
            return
        
        self.status_label.setText("Analyzing...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 发布分析事件
        if self._app:
            self._app.publish_event(EventBus.EVENT_IMAGE_ANALYSIS_STARTED, {
                'path': self._current_image_path
            })
        
        # 模拟分析完成
        self.progress_bar.setValue(100)
        self.status_label.setText("Analysis completed")
        self.progress_bar.setVisible(False)
    
    def on_create_model(self):
        """创建3D模型"""
        self.status_label.setText("Creating 3D model...")
        
        # 发布建模事件
        if self._app:
            self._app.publish_event(EventBus.EVENT_MODEL_CREATION_STARTED)
        
        self.status_label.setText("3D model created")
    
    def on_apply_rules(self):
        """应用铸造规则"""
        params = self.properties_panel.get_casting_params()
        self.status_label.setText("Applying casting rules...")
        
        # 这里调用铸造规则引擎
        
        self.status_label.setText("Casting rules applied")
    
    def on_full_workflow(self):
        """执行完整工作流"""
        if not self._current_image_path:
            QMessageBox.warning(self, "Warning", "Please load an image first")
            return
        
        # 获取参数
        params = self.properties_panel.get_casting_params()
        
        # 创建工作流
        if self._app:
            workflow = self._app.create_workflow(WorkflowType.FULL, {
                'image_path': self._current_image_path,
                'casting_params': params
            })
            
            if workflow:
                self._app.start_workflow(workflow)
                self.status_label.setText("Full workflow started")
    
    def on_about(self):
        """关于对话框"""
        QMessageBox.about(
            self,
            "About",
            f"<h2>{MainApplication.APP_NAME}</h2>"
            f"<p>Version: {MainApplication.VERSION}</p>"
            f"<p>A 2D to 3D conversion tool for the casting industry.</p>"
            f"<p>Supports automatic conversion of casting part drawings "
            f"and photos to 3D models.</p>"
        )
    
    # ==================== 重写方法 ====================
    
    def closeEvent(self, event):
        """关闭事件"""
        # 保存窗口状态
        self._save_window_state()
        
        # 关闭应用程序
        if self._app:
            self._app.shutdown()
        
        event.accept()


if __name__ == "__main__":
    # 测试代码
    if not HAS_QT:
        print("PyQt6 is required for GUI test")
        sys.exit(1)
    
    print("MainWindow Test")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    # 创建应用程序实例
    from app.main_application import create_application
    main_app = create_application()
    
    if main_app.initialize():
        # 创建主窗口
        window = MainWindow(main_app)
        window.show()
        
        print("MainWindow shown")
        
        # 运行应用程序
        sys.exit(app.exec())
    else:
        print("Application initialization failed")

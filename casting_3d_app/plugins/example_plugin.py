"""
示例插件

演示如何创建自定义插件。
"""

import logging
from typing import Any, List, Optional

# 导入插件接口
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.plugin_manager import IImageProcessorPlugin, ICastingRulePlugin

logger = logging.getLogger(__name__)


class ExampleImageProcessor(IImageProcessorPlugin):
    """
    示例图像处理器插件
    
    演示如何实现自定义图像处理插件。
    """
    
    @property
    def name(self) -> str:
        return "ExampleImageProcessor"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "An example image processor plugin that applies Gaussian blur"
    
    @property
    def author(self) -> str:
        return "Your Name"
    
    @property
    def processing_order(self) -> int:
        """处理顺序，数值越小越先执行"""
        return 50
    
    def initialize(self, app_context: Any) -> bool:
        """初始化插件"""
        logger.info(f"Initializing {self.name}")
        # 在这里进行插件初始化
        return True
    
    def shutdown(self) -> None:
        """关闭插件"""
        logger.info(f"Shutting down {self.name}")
        # 在这里进行清理工作
    
    def process(self, image: Any) -> Any:
        """
        处理图像
        
        Args:
            image: 输入图像 (numpy array)
            
        Returns:
            处理后的图像
        """
        try:
            import cv2
            import numpy as np
            
            # 应用高斯模糊作为示例
            processed = cv2.GaussianBlur(image, (5, 5), 1.0)
            
            logger.debug("Example image processing applied")
            return processed
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return image
    
    def get_config_schema(self) -> dict:
        """获取配置模式"""
        return {
            "blur_kernel_size": {
                "type": "integer",
                "default": 5,
                "description": "Gaussian blur kernel size"
            },
            "blur_sigma": {
                "type": "number",
                "default": 1.0,
                "description": "Gaussian blur sigma"
            }
        }
    
    def on_config_changed(self, key: str, value: Any):
        """配置变更回调"""
        logger.info(f"Config changed: {key} = {value}")


class ExampleCastingRule(ICastingRulePlugin):
    """
    示例铸造规则插件
    
    演示如何实现自定义铸造规则插件。
    """
    
    @property
    def name(self) -> str:
        return "ExampleCastingRule"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "An example casting rule plugin"
    
    @property
    def author(self) -> str:
        return "Your Name"
    
    @property
    def rule_category(self) -> str:
        return "example"
    
    @property
    def auto_fixable(self) -> bool:
        return False
    
    def initialize(self, app_context: Any) -> bool:
        """初始化插件"""
        logger.info(f"Initializing {self.name}")
        return True
    
    def shutdown(self) -> None:
        """关闭插件"""
        logger.info(f"Shutting down {self.name}")
    
    def check(self, part: Any) -> List[Any]:
        """
        检查零件
        
        Args:
            part: 零件数据
            
        Returns:
            检查结果列表
        """
        results = []
        
        # 示例检查逻辑
        # 实际实现中，这里应该包含具体的规则检查
        
        logger.info(f"Example casting rule check completed for {part}")
        return results


# 插件入口点
# 插件管理器会自动发现并加载这些类
PLUGIN_CLASSES = [
    ExampleImageProcessor,
    ExampleCastingRule
]


if __name__ == "__main__":
    # 测试代码
    print("Example Plugin Test")
    print("=" * 50)
    
    # 测试图像处理器
    processor = ExampleImageProcessor()
    print(f"Plugin: {processor.name} v{processor.version}")
    print(f"Description: {processor.description}")
    
    # 测试初始化
    if processor.initialize(None):
        print("Initialization successful")
    
    # 测试处理
    import numpy as np
    test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    result = processor.process(test_image)
    print(f"Image processed: {test_image.shape} -> {result.shape}")
    
    # 测试关闭
    processor.shutdown()
    print("Shutdown successful")
    
    print("\nTest completed!")

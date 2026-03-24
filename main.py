# 这是安卓 App 的入口文件
import sys
import os

# 让程序能找到你的核心代码
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入 Kivy 界面库（用来做手机 App 界面）
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

# 导入你已经写好的 STL 导出功能
from stl_exporter import STLExporter

class Casting3DApp(App):
    # 构建 App 界面
    def build(self):
        # 垂直布局：文字在上，按钮在下
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
        
        # 显示提示文字
        self.status_label = Label(
            text="点击下方按钮生成 3D 铸造模型",
            font_size=22
        )
        
        # 生成按钮
        self.generate_btn = Button(
            text="生成 STL 模型",
            font_size=28,
            size_hint=(1, 0.25),
            background_color=(0.2, 0.6, 1, 1)
        )
        # 按钮点击后执行 generate_model 函数
        self.generate_btn.bind(on_press=self.generate_model)
        
        layout.add_widget(self.status_label)
        layout.add_widget(self.generate_btn)
        return layout

    # 点击按钮后执行的核心逻辑
    def generate_model(self, instance):
        self.status_label.text = "正在生成中，请稍候..."
        try:
            # 调用你现有的 STL 导出器
            exporter = STLExporter()
            # 生成球体模型（你可以 later 改成其他形状）
            exporter.export_sphere("output/app_generated_model.stl")
            self.status_label.text = "✅ 生成成功！模型已保存到 output 文件夹"
        except Exception as e:
            self.status_label.text = f"❌ 生成失败：{str(e)}"

# 启动 App
if __name__ == "__main__":
    Casting3DApp().run()
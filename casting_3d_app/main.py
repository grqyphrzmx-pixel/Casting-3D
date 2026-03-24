#!/usr/bin/env python3
"""
铸造行业2D到3D转换应用程序 - 入口点

Casting Industry 2D to 3D Converter - Entry Point

Usage:
    python main.py [options]

Options:
    -h, --help          Show help message
    -v, --version       Show version information
    --no-gui            Run in command line mode
    --input FILE        Input image file
    --output DIR        Output directory
    --format FORMAT     Export format (stl, step, iges, all)
    --process TYPE      Casting process (sand, die, investment, etc.)
    --material CODE     Material code (A356, HT250, etc.)
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# 确保可以导入本地模块
sys.path.insert(0, str(Path(__file__).parent))

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Casting Industry 2D to 3D Converter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    # Run GUI mode
    python main.py

    # Run command line mode
    python main.py --no-gui --input drawing.jpg --output ./output --format stl

    # Specify casting process and material
    python main.py --input part.jpg --process sand --material A356
        '''
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    parser.add_argument(
        '--no-gui',
        action='store_true',
        help='Run in command line mode (no GUI)'
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Input image file path'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='./output',
        help='Output directory (default: ./output)'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['stl', 'step', 'iges', 'brep', 'all'],
        default='stl',
        help='Export format (default: stl)'
    )
    
    parser.add_argument(
        '--process', '-p',
        type=str,
        choices=['sand', 'die', 'investment', 'centrifugal', 'permanent'],
        default='sand',
        help='Casting process (default: sand)'
    )
    
    parser.add_argument(
        '--material', '-m',
        type=str,
        default='A356',
        help='Material code (default: A356)'
    )
    
    parser.add_argument(
        '--draft-external',
        type=float,
        default=1.5,
        help='External draft angle in degrees (default: 1.5)'
    )
    
    parser.add_argument(
        '--draft-internal',
        type=float,
        default=2.0,
        help='Internal draft angle in degrees (default: 2.0)'
    )
    
    parser.add_argument(
        '--fillet-radius',
        type=float,
        default=2.0,
        help='Fillet radius in mm (default: 2.0)'
    )
    
    parser.add_argument(
        '--wall-thickness',
        type=float,
        default=3.0,
        help='Minimum wall thickness in mm (default: 3.0)'
    )
    
    parser.add_argument(
        '--quality-check',
        action='store_true',
        default=True,
        help='Enable quality check (default: True)'
    )
    
    parser.add_argument(
        '--verbose', '-V',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file path'
    )
    
    return parser.parse_args()


def setup_logging(verbose: bool = False):
    """设置日志系统"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def run_gui_mode(args):
    """运行GUI模式"""
    try:
        from PyQt6.QtWidgets import QApplication
        from app.main_application import create_application
        from gui.main_window import MainWindow
        
        # 创建Qt应用程序
        qt_app = QApplication(sys.argv)
        qt_app.setApplicationName("Casting2D3DConverter")
        qt_app.setApplicationVersion("1.0.0")
        
        # 创建应用程序实例
        app = create_application()
        
        # 初始化应用程序
        if not app.initialize(vars(args)):
            print("Failed to initialize application", file=sys.stderr)
            return 1
        
        # 创建主窗口
        window = MainWindow(app)
        
        # 如果指定了输入文件，自动加载
        if args.input and os.path.exists(args.input):
            window.on_open_image()
        
        window.show()
        
        # 运行Qt事件循环
        return qt_app.exec()
        
    except ImportError as e:
        print(f"GUI mode requires PyQt6: {e}", file=sys.stderr)
        print("Please install PyQt6 or use --no-gui mode", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error in GUI mode: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def run_cli_mode(args):
    """运行命令行模式"""
    from app.main_application import create_application
    from core.workflow_manager import WorkflowType
    
    # 创建应用程序实例
    app = create_application()
    
    # 初始化应用程序
    if not app.initialize(vars(args)):
        print("Failed to initialize application", file=sys.stderr)
        return 1
    
    # 检查输入文件
    if not args.input:
        print("Error: Input file required in CLI mode", file=sys.stderr)
        print("Use --input to specify input image file", file=sys.stderr)
        return 1
    
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1
    
    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Casting 2D to 3D Converter v1.0.0")
    print(f"Input: {args.input}")
    print(f"Output: {output_dir.absolute()}")
    print(f"Format: {args.format}")
    print(f"Process: {args.process}")
    print(f"Material: {args.material}")
    print("-" * 50)
    
    # 创建工作流
    workflow = app.create_workflow(WorkflowType.FULL, {
        'image_path': args.input,
        'output_dir': str(output_dir),
        'export_format': args.format,
        'casting_process': args.process,
        'material': args.material,
        'draft_external': args.draft_external,
        'draft_internal': args.draft_internal,
        'fillet_radius': args.fillet_radius,
        'wall_thickness': args.wall_thickness,
        'quality_check': args.quality_check
    })
    
    if not workflow:
        print("Error: Failed to create workflow", file=sys.stderr)
        return 1
    
    # 启动工作流
    print("Starting conversion workflow...")
    
    if app.start_workflow(workflow):
        print("Workflow started successfully")
        
        # 等待工作流完成
        import time
        while workflow.is_running:
            time.sleep(0.1)
        
        if workflow.is_completed:
            print("Conversion completed successfully!")
            print(f"Output files saved to: {output_dir.absolute()}")
            return 0
        elif workflow.is_failed:
            print(f"Conversion failed: {workflow._error_message}", file=sys.stderr)
            return 1
        else:
            print("Conversion cancelled", file=sys.stderr)
            return 1
    else:
        print("Error: Failed to start workflow", file=sys.stderr)
        return 1


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Casting 2D to 3D Converter v1.0.0")
    
    # 根据模式运行
    if args.no_gui:
        logger.info("Running in CLI mode")
        return run_cli_mode(args)
    else:
        logger.info("Running in GUI mode")
        return run_gui_mode(args)


if __name__ == "__main__":
    sys.exit(main())

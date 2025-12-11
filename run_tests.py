"""
测试运行器 - 运行所有单元测试
"""

import sys
import unittest
from pathlib import Path
import importlib 


def run_all_tests(verbose=2):
    """
    运行所有测试

    Args:
        verbose: 详细程度 (0=静默, 1=正常, 2=详细)

    Returns:
        bool: 是否所有测试都通过
    """
    # 添加项目根目录到路径，确保能导入test模块
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    # 创建测试加载器
    loader = unittest.TestLoader()

    # 创建测试套件
    suite = unittest.TestSuite()

    # 测试模块列表 (在test目录下)
    test_modules = [
        'test.test_video_downloader',
        'test.test_audio_processor',
        'test.test_ai_services',
    ]
    
    print("=" * 70)
    print("视频翻译系统 - 单元测试套件")
    print("=" * 70)
    print()
    
    # 加载所有测试模块
    for module_name in test_modules:
        try:
            print(f"加载测试模块: {module_name}")
            module = importlib.import_module(module_name)
            loaded_tests = loader.loadTestsFromModule(module)
            print(f"加载了 {loaded_tests.countTestCases()} 个测试")
            suite.addTests(loaded_tests)
        except ImportError as e:
            print(f"无法加载 {module_name}: {e}")
            continue
    
    print()
    print(f"共加载 {suite.countTestCases()} 个测试用例")
    print("=" * 70)
    print()
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=verbose)
    result = runner.run(suite)
    
    # 输出测试摘要
    print()
    print("=" * 70)
    print("测试摘要")
    print("=" * 70)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    print("=" * 70)
    
    # 返回结果
    return result.wasSuccessful()


def run_specific_test(test_name, verbose=2):
    """
    运行特定的测试
    
    Args:
        test_name: 测试名称 (如: test_video_downloader.TestVideoDownloader)
        verbose: 详细程度
    """
    print(f"运行特定测试: {test_name}")
    print("=" * 70)
    print()
    
    # 加载并运行测试
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    
    runner = unittest.TextTestRunner(verbosity=verbose)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='运行视频翻译系统单元测试')
    parser.add_argument(
        '-v', '--verbose',
        type=int,
        default=2,
        choices=[0, 1, 2],
        help='详细程度: 0=静默, 1=正常, 2=详细 (默认: 2)'
    )
    parser.add_argument(
        '-t', '--test',
        type=str,
        help='运行特定测试 (如: test_video_downloader.TestVideoDownloader.test_is_bilibili_url_valid_bv)'
    )
    parser.add_argument(
        '-i', '--integration',
        action='store_true',
        help='启用集成测试 (需要网络和真实文件)'
    )
    
    args = parser.parse_args()
    
    # 设置集成测试环境变量
    if args.integration:
        import os
        os.environ['RUN_INTEGRATION_TESTS'] = '1'
        print("✓ 已启用集成测试")
        print()
    
    # 运行测试
    if args.test:
        success = run_specific_test(args.test, args.verbose)
    else:
        success = run_all_tests(args.verbose)
    
    # 退出
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

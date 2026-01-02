# 测试说明

## 测试结构

```
tests/
├── __init__.py                 # 测试模块初始化
├── conftest.py                 # pytest配置和fixtures
├── test_security.py            # 安全模块单元测试
├── test_config.py              # 配置模块单元测试
├── test_asr.py                 # ASR模块单元测试
├── test_translation.py         # 翻译模块单元测试
├── integration/
│   ├── __init__.py
│   └── test_workflow.py        # 集成测试
└── fixtures/
    ├── __init__.py
    ├── sample_audio.mp3        # 测试音频（需添加）
    └── sample_video.mp4        # 测试视频（需添加）
```

## 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定测试文件
```bash
pytest tests/test_security.py
```

### 运行特定测试类
```bash
pytest tests/test_security.py::TestPathSecurityValidator
```

### 运行特定测试方法
```bash
pytest tests/test_security.py::TestPathSecurityValidator::test_validate_path_in_project_valid_path
```

### 运行标记的测试
```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 只运行安全测试
pytest -m security

# 跳过慢速测试
pytest -m "not slow"

# 跳过需要网络的测试
pytest -m "not requires_network"
```

### 详细输出
```bash
# 显示print输出
pytest -s

# 更详细的输出
pytest -vv

# 显示测试覆盖率（需要安装pytest-cov）
pytest --cov=. --cov-report=html
```

## 测试标记说明

- `unit`: 单元测试（快速，不需要网络）
- `integration`: 集成测试（较慢，可能需要网络）
- `security`: 安全测试
- `slow`: 慢速测试（运行时间>5秒）
- `asr`: ASR相关测试
- `translation`: 翻译相关测试
- `requires_network`: 需要网络连接的测试

## 添加新测试

### 1. 单元测试示例

```python
# tests/test_my_module.py
import pytest

class TestMyModule:
    def test_function_valid_input(self):
        """测试有效输入"""
        from my_module import my_function
        result = my_function("valid input")
        assert result == "expected output"

    def test_function_invalid_input(self):
        """测试无效输入"""
        from my_module import my_function
        with pytest.raises(ValueError):
            my_function("invalid input")
```

### 2. 集成测试示例

```python
# tests/integration/test_my_feature.py
import pytest

@pytest.mark.integration
@pytest.mark.slow
class TestMyFeature:
    def test_full_workflow(self, mock_env_vars):
        """测试完整工作流"""
        # 测试代码
        pass
```

## Fixtures说明

### mock_env_vars
模拟环境变量，用于测试配置加载

```python
def test_my_config(mock_env_vars):
    import config
    assert config.DASHSCOPE_API_KEY == "test_api_key_12345"
```

### test_data_dir
测试数据目录路径

```python
def test_load_fixture(test_data_dir):
    fixture_file = test_data_dir / "sample_audio.mp3"
    assert fixture_file.exists()
```

### output_dir
测试输出目录，用于保存测试结果

```python
def test_save_result(output_dir):
    result_file = output_dir / "result.txt"
    result_file.write_text("test result")
```

## 持续集成

测试配置为在CI/CD流程中自动运行：

```yaml
# .github/workflows/test.yml 示例
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements-dev.txt
      - run: pytest -m "not requires_network" -v
```

## 注意事项

1. **环境变量**: 测试使用mock环境变量，不会影响真实环境
2. **网络测试**: 标记为`requires_network`的测试会被CI跳过
3. **清理**: 测试完成后会自动清理临时文件
4. **隔离**: 每个测试都是独立的，可以单独运行

## 下一步

- [ ] 添加更多单元测试（目标覆盖率：>80%）
- [ ] 添加性能测试
- [ ] 添加端到端测试
- [ ] 设置CI/CD自动测试
- [ ] 添加测试数据文件（sample_audio.mp3等）

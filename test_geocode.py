# Test imports (run with `pip install -e .[geocode]` then `python test_geocode.py`)
from geoffrey_llm.geocode.models.base import BaseModel, ModelConfig, ModelResponse
from geoffrey_llm.geocode.models.kimi import KimiProvider
from geoffrey_llm.geocode.tools.base import Tool, ToolInput, ToolResult
from geoffrey_llm.geocode.tools.file_read import FileReadTool
from geoffrey_llm.geocode.memory.store import MemoryStore
from geoffrey_llm.geocode.session.manager import SessionManager

# Test FileReadTool
tool = FileReadTool()
print(f'Tool name: {tool.name}')
print(f'Tool schema: {tool.get_schema()}')

# Test MemoryStore with temp dir
import tempfile
tmpdir = tempfile.mkdtemp()
store = MemoryStore(tmpdir)
print(f'MemoryStore dir: {store.memory_dir}')

# Test SessionManager
sess_manager = SessionManager()
session = sess_manager.create()
print(f'Session created: {session.id}')

# Test ModelConfig
config = ModelConfig(model_name='moonshot-v1-8k')
print(f'Model config: {config.model_name}')

print('All tests passed!')

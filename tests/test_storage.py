from pathlib import Path
from tempfile import TemporaryDirectory
from omemory.storage import MemoryStore

def test_crud_search_and_history():
    with TemporaryDirectory() as d:
        store = MemoryStore(Path(d) / '.omemory')
        item = store.create('knowledge', 'Payment provider', 'Use sandbox H2H', project='demo')
        assert store.search('sandbox payment', project='demo')[0]['id'] == item['id']
        store.update(item['id'], {'content': 'Use sandbox H2H for tests'})
        assert len(store.history_for(item['id'])) == 2
        assert store.doctor()['ok'] is True
        assert store.delete(item['id']) is True
        assert store.get(item['id']) is None

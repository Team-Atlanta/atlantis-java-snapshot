import pytest
import tempfile
import shutil
from libAgents.agents.deep_search_agent import DeepSearchAgent


class TestQueryCacheAPI:
    """Test cache functionality ONLY through the query API"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for cache testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_query_caching_behavior(self, temp_dir):
        """Test that query API caches results when cache is enabled"""
        # Create agent
        from libAgents.plugins import AnswerPlugin

        agent = DeepSearchAgent(plugins=[AnswerPlugin()])

        # Set up cache manually to avoid the project_bundle issue
        import diskcache

        agent.cache = diskcache.Cache(f"{temp_dir}/test_cache")

        # Patch the _save_cache method to handle the expire parameter
        original_save = agent._save_cache

        def patched_save_cache(key, value, expire=None):
            original_save(key, value)

        agent._save_cache = patched_save_cache

        question = "What is the test question?"

        # Track how many times the internal _query method is called
        query_call_count = 0

        async def tracked_query(*args, **kwargs):
            nonlocal query_call_count
            query_call_count += 1
            return {"result": {"answer": f"Answer #{query_call_count}"}}

        agent._query = tracked_query

        # First call should execute and cache
        result1 = await agent.query(question)
        assert result1 == "Answer #1"
        assert query_call_count == 1

        # Second call should return from cache without executing _query
        result2 = await agent.query(question)
        assert result2 == "Answer #1"  # Same answer
        assert query_call_count == 1  # Still 1, not called again

        # Different question should execute again
        result3 = await agent.query("Different question?")
        assert result3 == "Answer #2"
        assert query_call_count == 2

    @pytest.mark.asyncio
    async def test_query_no_caching_when_cache_none(self):
        """Test that query doesn't cache when cache is None"""
        from libAgents.plugins import AnswerPlugin

        agent = DeepSearchAgent(plugins=[AnswerPlugin()])

        # Ensure cache is None
        agent.cache = None

        # Also need to patch _save_cache to handle expire parameter
        original_save = agent._save_cache

        def patched_save_cache(key, value, expire=None):
            if agent.cache is not None:
                original_save(key, value)

        agent._save_cache = patched_save_cache

        question = "What is the test question?"

        # Track calls
        query_call_count = 0

        async def tracked_query(*args, **kwargs):
            nonlocal query_call_count
            query_call_count += 1
            return {"result": {"answer": f"Answer #{query_call_count}"}}

        agent._query = tracked_query

        # Both calls should execute _query
        result1 = await agent.query(question)
        assert result1 == "Answer #1"
        assert query_call_count == 1

        result2 = await agent.query(question)
        assert result2 == "Answer #2"  # Different answer
        assert query_call_count == 2  # Called again

    @pytest.mark.asyncio
    async def test_query_cache_includes_model_in_key(self, temp_dir):
        """Test that cache key includes model name"""
        from libAgents.plugins import AnswerPlugin

        agent = DeepSearchAgent(plugins=[AnswerPlugin()])

        import diskcache

        agent.cache = diskcache.Cache(f"{temp_dir}/test_cache")

        # Patch _save_cache
        original_save = agent._save_cache

        def patched_save_cache(key, value, expire=None):
            original_save(key, value)

        agent._save_cache = patched_save_cache

        question = "What is the test question?"

        # Track calls
        query_call_count = 0

        async def tracked_query(*args, **kwargs):
            nonlocal query_call_count
            query_call_count += 1
            return {"result": {"answer": f"Answer #{query_call_count}"}}

        agent._query = tracked_query

        # Query with default model
        result1 = await agent.query(question)
        assert result1 == "Answer #1"
        assert query_call_count == 1

        # Query with same question but different model should not use cache
        result2 = await agent.query(question, override_model="different-model")
        assert result2 == "Answer #2"  # New answer
        assert query_call_count == 2

        # Query again with first model should use cache
        result3 = await agent.query(question)
        assert result3 == "Answer #1"  # Cached answer
        assert query_call_count == 2  # No new call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

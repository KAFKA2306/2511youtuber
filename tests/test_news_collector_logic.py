
import pytest
from datetime import datetime
from src.steps.news import NewsCollector
from src.models import NewsItem
from src.utils.constants import QUERY_BUCKETS

class MockProvider:
    pass

@pytest.fixture
def collector():
    # Setup collector with minimal config
    return NewsCollector(
        run_id="test_run",
        run_dir="/tmp",
        providers=[],
        query_buckets=QUERY_BUCKETS,
        fetch_count=10,
        final_count=2,
        cooldown_hours=24
    )

def test_similarity(collector):
    # exact
    assert collector._calculate_similarity("Hello World", "Hello World") == 1.0
    # completely different
    assert collector._calculate_similarity("Hello World", "Foo Bar") == 0.0
    # similar
    s = collector._calculate_similarity("Asahi HD Earnings Delay", "Asahi Group Earnings Delayed")
    assert s > 0.4 # Should be high enough

def test_cluster_deduplication(collector):
    candidates = [
        NewsItem(title="A", url="http://a.com", summary="A", published_at=datetime.now()),
        NewsItem(title="A", url="http://a.com", summary="A copy", published_at=datetime.now()), # Same URL
        NewsItem(title="A", url="http://b.com", summary="A duplicate", published_at=datetime.now()), # Same Title
        NewsItem(title="B", url="http://c.com", summary="B", published_at=datetime.now()),
    ]
    
    clusters = collector._normalize_and_cluster(candidates)
    assert len(clusters) == 2 # A and B. (The 2nd A is URL dupe, 3rd A is Title dupe of 1st)
    assert len(clusters[0]) >= 1
    assert len(clusters[1]) == 1
    assert clusters[0][0].title == "A"
    assert clusters[1][0].title == "B"

def test_cooldown_filter(collector):
    clusters = [
        [NewsItem(title="Asahi HD Earnings", url="u1", summary="", published_at=datetime.now())],
        [NewsItem(title="New Topic X", url="u2", summary="", published_at=datetime.now())]
    ]
    recent_topics = [
        "Asahi HD Results Delayed", # Similar to first cluster
        "Something Else"
    ]
    
    allowed, log = collector._apply_cooldown(clusters, recent_topics)
    
    assert len(allowed) == 1
    assert allowed[0][0].title == "New Topic X"
    assert "Asahi HD Earnings" not in [c[0].title for c in allowed]
    print(log)

def test_bucket_selection(collector):
    # Test that bucket selection returns a valid bucket
    key, query = collector._select_bucket()
    assert key in QUERY_BUCKETS
    assert query == QUERY_BUCKETS[key]

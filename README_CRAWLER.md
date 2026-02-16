# Competitor Intelligence Crawler

Automated capability change feed for accounting/ERP competitors. Monitors release notes, product docs, API changelogs, and deprecation notices to detect and classify product changes.

## What It Does

The crawler continuously watches official documentation from competitors like NetSuite, SAP, Workday, Rillet, DualEntry, and others. When it detects changes, it:

1. **Extracts** content chunks from documentation pages
2. **Detects** what changed by comparing content hashes
3. **Classifies** changes by theme (AI, consolidation, reporting, etc.) and type (new capability, enhancement, deprecation)
4. **Summarizes** changes in beginner-friendly language for engineers without accounting backgrounds
5. **Stores** capability events with evidence citations for your team to review

## Why This Matters

- **New hire onboarding**: Engineers can quickly understand "what does this vendor actually do" and "what's new"
- **Competitive intel**: Stay informed about feature launches, deprecations, and market positioning
- **Product strategy**: Identify gaps and opportunities based on competitor movements
- **Defensible insights**: All events include exact evidence snippets and source URLs

## Quick Start

### 1. Run Unit Tests

```bash
python test_competitor_sources.py -v
```

### 2. Discover Sources

See what documentation the crawler will monitor:

```bash
python cli_crawler.py discover
```

### 3. Run a Test Crawl

Crawl top 5 competitors (limited to 5 URLs for testing):

```bash
python cli_crawler.py crawl --max-urls=5
```

### 4. View Results

```bash
python cli_crawler.py events --limit=10 -v
```

### 5. Check Status

```bash
python cli_crawler.py status
```

## Architecture

### Competitors (Priority System)

**Priority 1 (Top 5)** - Default crawl targets:
- NetSuite (traditional ERP leader)
- SAP (enterprise standard)
- Workday (finance + HR focus)
- Rillet (AI-native, complex revenue)
- DualEntry (AI-native, ML automation)

**Priority 2** - Mid-tier competitors:
- Oracle, Microsoft Dynamics 365, Sage Intacct, Digits, Puzzle

**Priority 3** - Additional coverage:
- Acumatica, SAP Business One, Odoo

### Source Discovery

The crawler automatically discovers high-signal URLs by:

1. Fetching competitor homepage
2. Extracting all internal links
3. Matching against patterns:
   - **Release notes**: "release notes", "what's new", "changelog", "product updates"
   - **Feature docs**: "features", "capabilities", "documentation"
   - **API changelogs**: "api changelog", "api updates", "developer changelog"
   - **Deprecation**: "deprecation", "sunset", "end-of-life"

### Change Detection

1. **Chunking**: Split page content by H2/H3 headings
2. **Hashing**: SHA-256 hash of (heading + text)
3. **Comparison**: Compare against last-seen hashes in database
4. **Event creation**: Changed chunks → IntelEvent records

### Capability Classification

Uses Gemini to classify each change:

**Themes**:
- ai, consolidation, reporting, integrations, procurement, automation
- revenue_recognition, accounts_payable, accounts_receivable, general_ledger, close_management

**Change Types**:
- new capability, enhancement, deprecation, limitation

**Output**:
- **Claim**: One-sentence summary in product language
- **Beginner summary**: 3 bullets in plain language
  1. What this means (avoid jargon)
  2. Why it matters
  3. Competitive insight

## CLI Reference

### `cli_crawler.py discover`

Show all discovered sources grouped by competitor.

```bash
# Top 5 competitors only (default)
python cli_crawler.py discover

# All competitors
python cli_crawler.py discover --priority=3
```

### `cli_crawler.py crawl`

Run a crawl and create capability events.

```bash
# Crawl top 5 competitors (full)
python cli_crawler.py crawl

# Test crawl (5 URLs only)
python cli_crawler.py crawl --max-urls=5

# Crawl all competitors
python cli_crawler.py crawl --priority=3
```

### `cli_crawler.py events`

Show recent capability events.

```bash
# Show last 20 events (default)
python cli_crawler.py events

# Show 50 events with full details
python cli_crawler.py events --limit=50 -v
```

### `cli_crawler.py status`

Show crawler statistics.

```bash
python cli_crawler.py status
```

### `cli_crawler.py competitors`

List all registered competitors with priority levels.

```bash
python cli_crawler.py competitors
```

## API Endpoints

### GET `/api/competitors/sources?priority=1`

Get discovered sources grouped by competitor.

**Query params**:
- `priority`: Max priority level (1=top 5, 2=mid-tier, 3=all)

### GET `/api/competitors/events?limit=50`

Get recent capability events.

**Query params**:
- `limit`: Number of events to return

### POST `/api/competitors/crawl?priority=1&max_urls=null`

Trigger a crawl.

**Query params**:
- `priority`: Max priority level
- `max_urls`: Optional limit for testing

**Response**:
```json
{
  "status": "ok",
  "events_created": 12,
  "sources_crawled": 23,
  "sources_failed": 2,
  "competitors": ["NetSuite", "SAP", "Workday", "Rillet", "DualEntry"],
  "duration_seconds": 45.2
}
```

## Deployment

### Option 1: Manual Trigger

Run the shell script manually:

```bash
./run_crawler.sh
```

Configure with environment variables:

```bash
export CRAWLER_API_URL="http://localhost:8000/api/competitors/crawl"
export CRAWLER_PRIORITY=1
export CRAWLER_LOG_DIR="./logs"
./run_crawler.sh
```

### Option 2: Cron Job

Add to crontab for scheduled execution:

```bash
# Run every 6 hours
0 */6 * * * cd /path/to/Kindling && ./run_crawler.sh >> /var/log/crawler.log 2>&1

# Run daily at 2 AM
0 2 * * * cd /path/to/Kindling && ./run_crawler.sh >> /var/log/crawler.log 2>&1
```

### Option 3: Render Cron Job

If deploying on Render, add a cron job service:

1. Create `render.yaml`:

```yaml
services:
  - type: web
    name: campfire-api
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn server:app --host 0.0.0.0 --port $PORT"

  - type: cron
    name: crawler
    env: python
    schedule: "0 */6 * * *"  # Every 6 hours
    buildCommand: "pip install -r requirements.txt"
    startCommand: "./run_crawler.sh"
    envVars:
      - key: CRAWLER_API_URL
        value: "https://your-app.onrender.com/api/competitors/crawl"
      - key: CRAWLER_PRIORITY
        value: "1"
```

2. Deploy via Render dashboard or `render.yaml`

## Monitoring

### Logs

Crawler logs are saved to `./logs/crawler_YYYYMMDD_HHMMSS.log`

Old logs are automatically cleaned up after 30 days.

### Database

Crawl state is stored in `SyncState` table with key `competitor_source_state`:

```python
{
  "https://www.netsuite.com/portal/resource/articles/erp/whats-new.shtml": {
    "AI Assistant": "abc123hash...",
    "Revenue Recognition": "def456hash..."
  }
}
```

Events are stored in `IntelEvent` table:

```sql
SELECT competitor, theme, change_type, claim, created_at
FROM intel_events
ORDER BY created_at DESC
LIMIT 10;
```

## Configuration

### Adding Competitors

Edit `competitor_sources.py`:

```python
_COMPETITORS: List[Competitor] = [
    # Add new competitor
    Competitor(
        "YourCompetitor",
        "https://yourcompetitor.com",
        "modern",
        "Description of what they do",
        priority=1,  # 1, 2, or 3
        enabled=True
    ),
    # ... existing competitors
]
```

### Disabling Competitors

Set `enabled=False`:

```python
Competitor("Oracle", "https://www.oracle.com", "traditional", "...", priority=2, enabled=False),
```

### Adjusting Themes

Edit the prompt in `_summarize_change()` to add/modify themes:

```python
theme_options = [
    "ai", "consolidation", "reporting", "integrations",
    "your_new_theme",  # Add here
]
```

## Troubleshooting

### No sources discovered

**Problem**: `discover` returns empty or very few sources

**Solutions**:
- Check competitor website is accessible
- Verify BeautifulSoup is installed: `pip install beautifulsoup4`
- Try accessing the website manually - may have anti-bot protection
- Add manual sources for that competitor

### Crawl creates duplicate events

**Problem**: Same events appearing multiple times

**Solutions**:
- Check `SyncState` table for `competitor_source_state` key
- Verify chunk hashing is working: `python test_competitor_sources.py`
- May need to clear state: delete row and re-crawl

### LLM classification failing

**Problem**: Events have `theme="unspecified"` or poor summaries

**Solutions**:
- Verify `GEMINI_API_KEY` is set in environment
- Check Gemini API quota/limits
- Review fallback logic in `_summarize_change()`

### Crawl is slow

**Problem**: Takes >5 minutes for top 5 competitors

**Solutions**:
- Reduce `max_sources` per competitor in `discover_sources()`
- Use `max_urls` parameter to limit crawl size
- Check network latency to competitor sites
- Consider running async crawl (future enhancement)

## Testing

### Run Unit Tests

```bash
# All tests
python test_competitor_sources.py

# Verbose output
python test_competitor_sources.py -v

# Specific test
python test_competitor_sources.py TestChunkExtraction.test_extract_chunks_with_headings
```

### Manual Testing

```bash
# 1. Discover sources (should find 10-15 per competitor)
python cli_crawler.py discover

# 2. Run limited crawl
python cli_crawler.py crawl --max-urls=3

# 3. Check events were created
python cli_crawler.py events -v

# 4. Verify database state
python cli_crawler.py status
```

## Roadmap

### Phase 1: Core Functionality ✅
- [x] Competitor registry with priorities
- [x] Automatic source discovery
- [x] Content chunking and hashing
- [x] Change detection
- [x] LLM-powered classification
- [x] Beginner-friendly summaries
- [x] Unit tests
- [x] CLI tool
- [x] Deployment script

### Phase 2: Enhancements (Future)
- [ ] Async/parallel crawling for speed
- [ ] Email/Slack notifications for high-priority changes
- [ ] Frontend filtering by theme/competitor
- [ ] Timeline view of capability evolution
- [ ] Export to PDF/CSV for presentations
- [ ] Automatic competitor discovery via web search
- [ ] Sentiment analysis (positive/negative positioning)
- [ ] Trend detection (topics heating up)

### Phase 3: Intelligence (Future)
- [ ] Competitive gap analysis
- [ ] Feature parity matrix
- [ ] Market positioning insights
- [ ] Recommendation engine for product strategy

## FAQ

### How often should I run the crawler?

**For active monitoring**: Every 6 hours (4x/day)
**For cost savings**: Daily at off-peak hours
**For testing**: On-demand via CLI

### What if a competitor blocks the crawler?

- Respect robots.txt and rate limits
- Add delays between requests
- Consider using official API if available
- Fall back to manual monitoring for that competitor

### Can I crawl competitors not in accounting/ERP?

Yes! The architecture is domain-agnostic. Just:
1. Add competitors to `_COMPETITORS`
2. Adjust theme classification in `_summarize_change()`
3. Update beginner summary prompt for your domain

### How much does this cost to run?

**Compute**: Minimal (runs on existing server)
**Storage**: ~1KB per event, ~1000 events/month = 1MB
**LLM calls**: ~$0.01 per event (Gemini Flash), ~$10/month for active monitoring

## Support

- **Issues**: Open a GitHub issue
- **Questions**: Ask in #engineering Slack channel
- **Docs**: This README + inline code comments

---

Built for Campfire.ai to make competitive intelligence continuous, defensible, and beginner-friendly.

# MovieLens Metadata Loader

This directory contains scripts to load MovieLens sample data into OpenSearch for testing and demonstration purposes.

> **Status:** ✅ **Data Successfully Loaded** - 84,661 MovieLens documents are currently indexed in `sts-movielens-metadata-index` on the production OpenSearch cluster.

## Files

- `load_movielens_metadata.py` - Main loader script
- `requirements.txt` - Python dependencies
- `README.md` - This documentation

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (same as MCP server):
```bash
export OPENSEARCH_USERNAME=your_username
export OPENSEARCH_PASSWORD=your_password
export OPENSEARCH_HOST=localhost
export OPENSEARCH_PORT=9200
# ... other optional settings
```

Or create a `.env` file in the parent directory with these values.

## Usage

Run the loader script:
```bash
python load_movielens_metadata.py
```

The script will:
1. Test connection to OpenSearch
2. Create the `sts-movielens-metadata-index` with optimized mapping
3. Load movie metadata from `../sample_data/metadata.json`
4. Verify the data was loaded correctly

## Index Details

**Index Name:** `sts-movielens-metadata-index`

**Document Structure:**
```json
{
  "title": "Movie Title (Year)",
  "directedBy": "Director Name",
  "starring": "Actor1, Actor2, Actor3",
  "dateAdded": null,
  "avgRating": 3.89,
  "imdbId": "0114709",
  "item_id": 1,
  "year": 1995
}
```

**Mapping Features:**
- Text analysis for title, director, and cast searching
- Keyword fields for exact matching
- Optimized for movie search use cases
- Automatic year extraction from titles

## Sample Queries

After loading, you can test with these OpenSearch queries:

### Search by title:
```json
{
  "query": {
    "match": {
      "title": "toy story"
    }
  }
}
```

### Search by director:
```json
{
  "query": {
    "match": {
      "directedBy": "john lasseter"
    }
  }
}
```

### Find high-rated movies:
```json
{
  "query": {
    "range": {
      "avgRating": {
        "gte": 4.0
      }
    }
  },
  "sort": [
    {
      "avgRating": {
        "order": "desc"
      }
    }
  ]
}
```

### Search by year:
```json
{
  "query": {
    "term": {
      "year": 1995
    }
  }
}
```

## Troubleshooting

### Connection Issues
- Verify OpenSearch is running and accessible
- Check credentials in environment variables
- Ensure network connectivity

### Data Issues
- Verify `../sample_data/metadata.json` exists
- Check file permissions
- Review error messages for specific failures

### Index Issues
- If index exists, the script will prompt to recreate
- Check cluster health and available disk space
- Verify mapping is created correctly